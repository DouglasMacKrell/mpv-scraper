"""End-to-end test for real scrape workflow (Sprint 10.4).

Tests that the full `cli.run` workflow (scan → scrape → generate) works with
real scrape cache data, ensuring that generate reads the cache and populates
<desc>, <rating>, <marquee> with actual metadata.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from click.testing import CliRunner
from unittest.mock import patch

import mpv_scraper.cli as cli
import sys

# Ensure utils_images importable when running via "pytest -m e2e"
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils_images import create_placeholder_png  # noqa: E402

cli.create_placeholder_png = create_placeholder_png  # inject test helper

cli_main = cli.main


@pytest.mark.integration
def test_run_full_real_flow():
    """Test that run command performs scan → scrape → generate with real data."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "mpv"

        # --- Build a minimal mock library ----------------------------------
        show_dir = root / "Test Show"
        show_dir.mkdir(parents=True, exist_ok=True)
        (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

        movies_dir = root / "Movies"
        movies_dir.mkdir(parents=True, exist_ok=True)
        (movies_dir / "Sample Movie (1999).mkv").touch()

        # Mock the scraper functions to create realistic cache data
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
                        "overview": "This is a test episode description.",
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
                "overview": "This is a test movie description.",
                "vote_average": 0.75,  # Already normalized
                "poster_url": "https://image.tmdb.org/t/p/original/poster.jpg",
                "logo_url": "https://image.tmdb.org/t/p/original/logo.png",
            }

            # Mock image downloads to create real files
            from PIL import Image

            mock_dl.side_effect = lambda url, dest, headers=None: Image.new(
                "RGBA", (32, 32), (0, 0, 0, 0)
            ).save(dest, format="PNG")
            mock_marquee.side_effect = lambda url, dest, headers=None: Image.new(
                "RGBA", (32, 32), (0, 0, 0, 0)
            ).save(dest, format="PNG")

            # Execute: mpv-scraper run <library>
            result = runner.invoke(cli_main, ["run", str(root)])
            assert result.exit_code == 0, result.output

        # --- Validate scrape cache was created -----------------------------
        show_cache = show_dir / ".scrape_cache.json"
        assert show_cache.exists(), "TV show scrape cache should be created"

        movies_cache = movies_dir / ".scrape_cache.json"
        assert movies_cache.exists(), "Movies scrape cache should be created"

        # --- Validate XML contains real metadata --------------------------
        show_gamelist = show_dir / "gamelist.xml"
        assert show_gamelist.exists(), "Show gamelist.xml should be created"

        movies_gamelist = movies_dir / "gamelist.xml"
        assert movies_gamelist.exists(), "Movies gamelist.xml should be created"

        # Parse and validate show XML
        show_tree = ET.parse(show_gamelist)
        show_games = show_tree.findall(".//game")
        assert len(show_games) == 1, "Should have one game entry for the episode"

        # Check for real metadata (not placeholder values)
        game = show_games[0]
        desc_elem = game.find("desc")
        rating_elem = game.find("rating")
        marquee_elem = game.find("marquee")

        assert desc_elem is not None, "Should have <desc> tag"
        assert (
            desc_elem.text == "This is a test episode description."
        ), "Should have real description"

        assert rating_elem is not None, "Should have <rating> tag"
        assert (
            float(rating_elem.text) == 0.85
        ), "Should have normalized rating (8.5/10 = 0.85)"

        assert marquee_elem is not None, "Should have <marquee> tag"
        assert (
            marquee_elem.text == "./images/Test Show-marquee.png"
        ), "Should reference show marquee image"

        # Parse and validate movies XML
        movies_tree = ET.parse(movies_gamelist)
        movies_games = movies_tree.findall(".//game")
        assert len(movies_games) == 1, "Should have one game entry for the movie"

        # Check for real metadata (not placeholder values)
        movie_game = movies_games[0]
        movie_desc_elem = movie_game.find("desc")
        movie_rating_elem = movie_game.find("rating")
        movie_marquee_elem = movie_game.find("marquee")

        assert movie_desc_elem is not None, "Should have <desc> tag"
        assert (
            movie_desc_elem.text == "This is a test movie description."
        ), "Should have real description"

        assert movie_rating_elem is not None, "Should have <rating> tag"
        assert (
            float(movie_rating_elem.text) == 0.75
        ), "Should have real rating from TMDB"

        # Marquee is optional - only check if it exists
        movie_marquee_elem = movie_game.find("marquee")
        if movie_marquee_elem is not None:
            assert (
                movie_marquee_elem.text == "./images/Sample Movie (1999)-marquee.png"
            ), "Should reference marquee image"

        # --- Validate images exist and are under size limit ----------------
        for xml_path in [show_gamelist, movies_gamelist]:
            tree = ET.parse(xml_path)
            for img_elt in tree.findall(".//image") + tree.findall(".//marquee"):
                rel_img_path = img_elt.text or ""
                # For show-specific gamelist.xml, images are in top-level ./images/
                if xml_path.parent != root:
                    abs_img_path = (root / rel_img_path.lstrip("./")).resolve()
                else:
                    abs_img_path = (xml_path.parent / rel_img_path).resolve()
                assert abs_img_path.exists(), f"Image not found: {abs_img_path}"
                size_kb = abs_img_path.stat().st_size / 1024
                assert (
                    size_kb <= 600
                ), f"Image exceeds size limit: {abs_img_path} ({size_kb:.1f} KB)"
