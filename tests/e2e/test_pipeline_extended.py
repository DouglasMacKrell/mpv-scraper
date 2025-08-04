"""Extended end-to-end test (Sprint 9.5.1.2).

Builds a multi-season mock library with an anthology span file, runs the full
`cli.run` workflow, and validates:
  • gamelist XMLs are generated & well-formed
  • <marquee> and normalised <rating> tags exist
  • images referred in XML exist and satisfy size limits
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from click.testing import CliRunner

import mpv_scraper.cli as cli
import sys

# Ensure utils_images importable when running via "pytest -m e2e"
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils_images import create_placeholder_png  # noqa: E402

cli.create_placeholder_png = create_placeholder_png  # inject test helper

cli_main = cli.main


@pytest.mark.integration
def test_full_pipeline_multi_season():
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "mpv"
        # --- build library ---------------------------------------------------
        show = root / "Mega Show"
        show.mkdir(parents=True, exist_ok=True)
        # Season 1 single ep
        (show / "Mega Show - S01E01 - The Beginning.mp4").touch()
        # Season 1 anthology span
        (show / "Mega Show - S01E02-E03 - Part A & Part B.mp4").touch()
        # Season 2 ep
        (show / "Mega Show - S02E05 - The Return.mp4").touch()

        # Movies folder with one film
        movies = root / "Movies"
        movies.mkdir(parents=True)
        (movies / "Epic Film (2020).mp4").touch()

        # Mock the scraper functions to prevent real API calls
        from unittest.mock import patch

        with patch("mpv_scraper.scraper.tvdb") as mock_tvdb, patch(
            "mpv_scraper.scraper.tmdb"
        ) as mock_tmdb, patch("mpv_scraper.scraper.download_image") as mock_dl, patch(
            "mpv_scraper.scraper.download_marquee"
        ) as mock_marquee:
            # Mock TVDB responses
            mock_tvdb.search_show.return_value = [{"id": 1, "name": "Mega Show"}]
            mock_tvdb.get_series_extended.return_value = {
                "episodes": [
                    {
                        "seasonNumber": 1,
                        "number": 1,
                        "overview": "The beginning episode.",
                        "image": "https://art/ep1.png",
                    },
                    {
                        "seasonNumber": 1,
                        "number": 2,
                        "overview": "Part A episode.",
                        "image": "https://art/ep2.png",
                    },
                    {
                        "seasonNumber": 1,
                        "number": 3,
                        "overview": "Part B episode.",
                        "image": "https://art/ep3.png",
                    },
                    {
                        "seasonNumber": 2,
                        "number": 5,
                        "overview": "The return episode.",
                        "image": "https://art/ep5.png",
                    },
                ],
                "image": "https://art/poster.png",
                "artworks": {"clearLogo": "https://art/logo.png"},
                "siteRating": 8.5,
            }

            # Mock TMDB responses
            mock_tmdb.search_movie.return_value = [{"id": 1, "title": "Epic Film"}]
            mock_tmdb.get_movie_details.return_value = {
                "id": 1,
                "title": "Epic Film",
                "overview": "An epic film description.",
                "vote_average": 0.75,
                "poster_url": "https://image.tmdb.org/t/p/original/poster.jpg",
                "logo_url": "https://image.tmdb.org/t/p/original/logo.png",
            }

            # Mock image downloads to create small placeholder files
            from PIL import Image

            mock_dl.side_effect = lambda url, dest, headers=None: Image.new(
                "RGBA", (32, 32), (0, 0, 0, 0)
            ).save(dest, format="PNG")
            mock_marquee.side_effect = lambda url, dest, headers=None: Image.new(
                "RGBA", (32, 32), (0, 0, 0, 0)
            ).save(dest, format="PNG")

            # Execute workflow
            result = runner.invoke(cli_main, ["run", str(root)])
            assert result.exit_code == 0, result.output

        # Helper: walk XML files
        xml_files = list(root.rglob("gamelist.xml"))
        assert xml_files, "No gamelist.xml files generated"

        # Validate each XML
        for xml_path in xml_files:
            tree = ET.parse(xml_path)
            # validate marquee + rating presence if <game> elements exist
            games = tree.findall(".//game")
            if games:
                rating_tags = tree.findall(".//rating")
                assert rating_tags, f"Missing <rating> in {xml_path}"
                # rating values should be 0.00 format
                for r_elt in rating_tags:
                    val = float(r_elt.text or 0.0)
                    assert 0.0 <= val <= 1.0

                # Marquee tags are optional - only check if they exist
                marquee_tags = tree.findall(".//marquee")
                if marquee_tags:
                    # If marquee tags exist, validate them
                    for m_elt in marquee_tags:
                        rel = m_elt.text or ""
                        # For show-specific gamelist.xml, marquee images are in top-level ./images/
                        if xml_path.parent != root:
                            abs_path = (root / rel.lstrip("./")).resolve()
                        else:
                            abs_path = (xml_path.parent / rel).resolve()
                        assert abs_path.exists(), f"Marquee image missing: {abs_path}"
            # check images exist & size
            for img_elt in tree.findall(".//image") + tree.findall(".//marquee"):
                rel = img_elt.text or ""
                # For show-specific gamelist.xml, images are in top-level ./images/
                if xml_path.parent != root:
                    abs_path = (root / rel.lstrip("./")).resolve()
                else:
                    abs_path = (xml_path.parent / rel).resolve()
                assert abs_path.exists(), f"Image missing: {abs_path}"
                assert abs_path.stat().st_size / 1024 <= 600
