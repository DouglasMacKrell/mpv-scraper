"""Integration tests for scrape_movie helper (Sprint 10.2).

All external HTTP is mocked with `responses` so tests remain offline.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch


# The module to be created in Sprint 10.2
import importlib

scraper = importlib.import_module("mpv_scraper.scraper")  # type: ignore


@patch("mpv_scraper.scraper.download_marquee")
@patch("mpv_scraper.scraper.download_image")
@patch("mpv_scraper.scraper.tmdb")
def test_movie_metadata_downloaded(mock_tmdb, mock_dl, mock_marquee, tmp_path: Path):
    """scrape_movie should cache movie metadata JSON and download images."""

    # Create a movie file
    movie_file = tmp_path / "Back to the Future (1985).mp4"
    movie_file.touch()

    # Mock TMDB helpers
    mock_tmdb.search_movie.return_value = [{"id": 105, "title": "Back to the Future"}]
    mock_tmdb.get_movie_details.return_value = {
        "id": 105,
        "title": "Back to the Future",
        "overview": "A teenager is accidentally sent 30 years into the past...",
        "vote_average": 0.85,  # Already normalized
        "poster_url": "https://image.tmdb.org/t/p/original/poster.jpg",
        "logo_url": "https://image.tmdb.org/t/p/original/logo.png",
    }

    # Create proper PNG files for the mocks
    from PIL import Image

    mock_dl.side_effect = lambda url, dest, headers=None: Image.new(
        "RGBA", (32, 32), (0, 0, 0, 0)
    ).save(dest, format="PNG")
    mock_marquee.side_effect = lambda url, dest, headers=None: Image.new(
        "RGBA", (32, 32), (0, 0, 0, 0)
    ).save(dest, format="PNG")

    # Act
    scraper.scrape_movie(movie_file)

    # Assert cache written
    cache_path = movie_file.parent / ".scrape_cache.json"
    assert cache_path.exists(), "Cache JSON should be saved"

    # Assert images directory created
    images_dir = movie_file.parent / "images"
    assert images_dir.exists(), "Images directory should be created"

    # Assert poster downloaded
    poster_path = images_dir / "Back to the Future (1985).png"
    assert poster_path.exists(), "Poster should be downloaded"

    # Assert logo downloaded
    logo_path = images_dir / "Back to the Future (1985)-logo.png"
    assert logo_path.exists(), "Logo should be downloaded"

    # Verify TMDB was called correctly
    mock_tmdb.search_movie.assert_called_once_with("Back to the Future", 1985)
    mock_tmdb.get_movie_details.assert_called_once_with(105)


@patch("mpv_scraper.scraper.download_marquee")
@patch("mpv_scraper.scraper.download_image")
@patch("mpv_scraper.scraper.tmdb")
def test_movie_scraping_no_collection_logo(
    mock_tmdb, mock_dl, mock_marquee, tmp_path: Path
):
    """scrape_movie should handle movies without collection logos gracefully."""

    # Create a movie file
    movie_file = tmp_path / "The Matrix (1999).mp4"
    movie_file.touch()

    # Mock TMDB helpers - no collection
    mock_tmdb.search_movie.return_value = [{"id": 603, "title": "The Matrix"}]
    mock_tmdb.get_movie_details.return_value = {
        "id": 603,
        "title": "The Matrix",
        "overview": "A computer hacker learns from mysterious rebels...",
        "vote_average": 0.84,
        "poster_url": "https://image.tmdb.org/t/p/original/poster.jpg",
        # No logo_url
    }

    # Create proper PNG files for the mocks
    from PIL import Image

    mock_dl.side_effect = lambda url, dest, headers=None: Image.new(
        "RGBA", (32, 32), (0, 0, 0, 0)
    ).save(dest, format="PNG")

    # Act
    scraper.scrape_movie(movie_file)

    # Assert cache written
    cache_path = movie_file.parent / ".scrape_cache.json"
    assert cache_path.exists(), "Cache JSON should be saved"

    # Assert poster downloaded
    poster_path = movie_file.parent / "images" / "The Matrix (1999).png"
    assert poster_path.exists(), "Poster should be downloaded"

    # Assert logo was NOT downloaded (no collection)
    logo_path = movie_file.parent / "images" / "The Matrix (1999)-logo.png"
    assert not logo_path.exists(), "Logo should not be downloaded when no collection"

    # Verify download_marquee was not called
    mock_marquee.assert_not_called()


@patch("mpv_scraper.scraper.tmdb")
def test_movie_scraping_parse_failure(mock_tmdb, tmp_path: Path):
    """scrape_movie should raise RuntimeError for unparseable filenames."""

    # Create a file that looks like a TV episode (should not parse as movie)
    movie_file = tmp_path / "Show Name - S01E01 - Episode Title.mp4"
    movie_file.touch()

    # Act & Assert
    with pytest.raises(RuntimeError, match="Could not parse movie filename"):
        scraper.scrape_movie(movie_file)

    # Verify TMDB was not called
    mock_tmdb.search_movie.assert_not_called()
