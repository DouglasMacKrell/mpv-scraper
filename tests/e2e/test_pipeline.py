"""End-to-end integration test for the mpv-scraper CLI (Sprint 8.1).

The test creates a temporary copy of the `mocks/mpv` library, invokes the
`mpv-scraper run` command on it, and then validates that XML and image outputs
match the project constraints.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List
import xml.etree.ElementTree as ET

import pytest
from click.testing import CliRunner

import mpv_scraper.cli as cli
import sys

# Ensure test utilities are importable regardless of how tests are executed
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils_images import create_placeholder_png

# Inject test-only placeholder factory
cli.create_placeholder_png = create_placeholder_png

cli_main = cli.main


@pytest.mark.integration
def test_full_pipeline_generates_expected_files():
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        library_root = tmp_path / "mpv"

        # --- Build a minimal mock library ----------------------------------
        show_dir = library_root / "Test Show"
        show_dir.mkdir(parents=True, exist_ok=True)
        (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

        movies_dir = library_root / "Movies"
        movies_dir.mkdir(parents=True, exist_ok=True)
        (movies_dir / "Sample Movie (1999).mkv").touch()

        # Mock the scraper functions to prevent real API calls
        from unittest.mock import patch

        with patch("mpv_scraper.scraper.tvdb") as mock_tvdb, patch(
            "mpv_scraper.scraper.tmdb"
        ) as mock_tmdb, patch("mpv_scraper.scraper.download_image") as mock_dl, patch(
            "mpv_scraper.scraper.download_marquee"
        ) as mock_marquee:
            # Mock TVDB responses
            mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
            mock_tvdb.get_series_extended.return_value = {
                "episodes": [
                    {
                        "seasonNumber": 1,
                        "number": 1,
                        "overview": "Test episode description.",
                        "image": "https://art/ep.png",
                    }
                ],
                "image": "https://art/poster.png",
                "artworks": {"clearLogo": "https://art/logo.png"},
                "siteRating": 8.5,
            }

            # Mock TMDB responses
            mock_tmdb.search_movie.return_value = [{"id": 1, "title": "Sample Movie"}]
            mock_tmdb.get_movie_details.return_value = {
                "id": 1,
                "title": "Sample Movie",
                "overview": "Test movie description.",
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

            # Execute: mpv-scraper run <library>
            result = runner.invoke(cli_main, ["run", str(library_root)])
            assert result.exit_code == 0, result.output

        # --- Validation helpers --------------------------------------------------
        def _iter_xml_files(base: Path) -> List[Path]:
            return [p for p in base.rglob("gamelist.xml")]

        def _assert_xml_well_formed(xml_path: Path) -> ET.ElementTree:
            try:
                tree = ET.parse(xml_path)
            except ET.ParseError as exc:
                pytest.fail(f"Malformed XML: {xml_path}: {exc}")
            return tree

        # 1. Ensure we have a top-level gamelist (our current logic only creates top-level)
        xml_files = _iter_xml_files(library_root)
        assert (
            library_root / "gamelist.xml"
        ) in xml_files, "Missing top-level gamelist.xml"
        assert len(xml_files) >= 1, "Expected at least top-level gamelist.xml"

        # 2. Each XML must be well-formed and any <image> file it references must
        #    exist and satisfy the ≤600 KB constraint.
        for xml_path in xml_files:
            tree = _assert_xml_well_formed(xml_path)
            for img_elt in tree.findall(".//image"):
                rel_img_path = img_elt.text or ""
                # Paths are stored relative to the XML location.
                # For top-level gamelist.xml, images are in ./images/
                # For show-specific gamelist.xml, images are also in top-level ./images/
                if xml_path == library_root / "gamelist.xml":
                    # Top-level gamelist references images in ./images/
                    abs_img_path = (xml_path.parent / rel_img_path).resolve()
                else:
                    # Show-specific gamelist references images in top-level ./images/
                    abs_img_path = (library_root / rel_img_path.lstrip("./")).resolve()
                assert (
                    abs_img_path.exists()
                ), f"Image not found: {abs_img_path} (referenced in {xml_path})"
                size_kb = abs_img_path.stat().st_size / 1024
                assert (
                    size_kb <= 600
                ), f"Image exceeds size budget: {abs_img_path} ({size_kb:.1f} KB)"
