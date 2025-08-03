"""Integration tests for scrape_tv helper (Sprint 10.1).

All external HTTP is mocked with `responses` so tests remain offline.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


# The module to be created in Sprint 10.1
import importlib

scraper = importlib.import_module("mpv_scraper.scraper")  # type: ignore
images = importlib.import_module("mpv_scraper.images")  # type: ignore


@patch("mpv_scraper.scraper.download_marquee")
@patch("mpv_scraper.scraper.download_image")
@patch("mpv_scraper.scraper.tvdb")
def test_episode_metadata_downloaded(mock_tvdb, mock_dl, mock_marquee, tmp_path: Path):
    """scrape_tv should cache series + episode metadata JSON."""

    show_dir = tmp_path / "Test Show"
    show_dir.mkdir()
    # Create sample episode file S01E01
    (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

    # Mock TVDB helpers
    mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
    mock_tvdb.get_series_extended.return_value = {
        "episodes": [
            {
                "seasonNumber": 1,
                "number": 1,
                "overview": "The beginning…",
                "image": "https://art/ep.png",
            }
        ],
        "image": "https://art/poster.png",
        "artworks": {"clearLogo": "https://art/logo.png"},
        "siteRating": 8.0,
    }

    # Create proper PNG files for the mocks
    from PIL import Image

    mock_dl.side_effect = lambda url, dest: Image.new(
        "RGBA", (32, 32), (0, 0, 0, 0)
    ).save(dest, format="PNG")
    mock_marquee.side_effect = lambda url, dest: Image.new(
        "RGBA", (32, 32), (0, 0, 0, 0)
    ).save(dest, format="PNG")

    # Act
    scraper.scrape_tv(show_dir)

    # Assert episode image downloaded
    episode_img_path = show_dir / "images" / "S01E01-image.png"
    assert episode_img_path.exists(), "Episode image should be downloaded"

    # Assert series poster downloaded
    poster_path = show_dir / "images" / "poster.png"
    assert poster_path.exists(), "Series poster should be downloaded"

    # Assert cache written
    cache_path = show_dir / ".scrape_cache.json"
    assert cache_path.exists(), "Cache JSON should be saved"


@patch("mpv_scraper.scraper.download_marquee")
@patch("mpv_scraper.scraper.download_image")
@patch("mpv_scraper.scraper.tvdb")
def test_logo_saved(mock_tvdb, mock_dl, mock_marquee, tmp_path: Path):
    """scrape_tv should save clearLogo via download_marquee."""
    show_dir = tmp_path / "Logo Show"
    show_dir.mkdir()
    (show_dir / "Logo Show - S01E01 - Pilot.mp4").touch()

    mock_tvdb.search_show.return_value = [{"id": 2, "name": "Logo Show"}]
    mock_tvdb.get_series_extended.return_value = {
        "episodes": [],
        "artworks": {"clearLogo": "https://art/logo.png"},
    }

    # Create a proper PNG file for the mock
    from PIL import Image

    mock_marquee.side_effect = lambda url, dest: Image.new(
        "RGBA", (32, 32), (0, 0, 0, 0)
    ).save(dest, format="PNG")

    scraper.scrape_tv(show_dir)

    # Assert logo/marquee downloaded
    marquee_path = show_dir / "images" / "logo.png"
    assert marquee_path.exists(), "Logo/marquee should be downloaded"
