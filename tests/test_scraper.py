"""Unit tests for scraper error handling (Sprint 10.5)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch


from mpv_scraper.scraper import scrape_tv_parallel, scrape_movie


def test_missing_artwork_placeholder():
    """Test that scraper handles missing artwork gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        show_dir = Path(tmpdir) / "Test Show"
        show_dir.mkdir(parents=True, exist_ok=True)
        (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

        # Mock TVDB to return data but with missing artwork URLs
        with patch("mpv_scraper.scraper.tvdb") as mock_tvdb, patch(
            "mpv_scraper.scraper.download_image"
        ) as mock_download_image, patch(
            "mpv_scraper.scraper.download_marquee"
        ) as mock_download_marquee:
            # Mock successful TVDB responses but with missing artwork
            mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
            mock_tvdb.get_series_extended.return_value = {
                "episodes": [
                    {
                        "seasonNumber": 1,
                        "number": 1,
                        "overview": "Test episode",
                        # No image URL - should be handled gracefully
                    }
                ],
                "image": None,  # No poster URL
                "artworks": {},  # No logo URL
                "siteRating": 8.5,
            }

            # This should not crash - should handle missing artwork gracefully
            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()
            scrape_tv_parallel(show_dir, download_manager)

            # Verify that the scrape cache was still created despite missing artwork
            cache_file = show_dir / ".scrape_cache.json"
            assert (
                cache_file.exists()
            ), "Scrape cache should be created even with missing artwork"

            # Verify that download functions were NOT called since there are no URLs
            assert (
                not mock_download_image.called
            ), "download_image should not be called when no URLs exist"
            assert (
                not mock_download_marquee.called
            ), "download_marquee should not be called when no URLs exist"


def test_movie_missing_artwork_placeholder():
    """Test that movie scraper handles missing artwork gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        movie_file = Path(tmpdir) / "Test Movie (2020).mp4"
        movie_file.touch()

        # Mock TMDB to return data but with missing artwork URLs
        with patch("mpv_scraper.scraper.tmdb") as mock_tmdb, patch(
            "mpv_scraper.scraper.download_image"
        ) as mock_download_image, patch(
            "mpv_scraper.scraper.download_marquee"
        ) as mock_download_marquee:
            # Mock successful TMDB responses but with missing artwork
            mock_tmdb.search_movie.return_value = [{"id": 1, "title": "Test Movie"}]
            mock_tmdb.get_movie_details.return_value = {
                "id": 1,
                "title": "Test Movie",
                "overview": "Test movie description",
                "vote_average": 0.75,
                "poster_url": None,  # No poster URL
                "logo_url": None,  # No logo URL
            }

            # This should not crash - should handle missing artwork gracefully
            scrape_movie(movie_file)

            # Verify that the scrape cache was still created despite missing artwork
            cache_file = movie_file.parent / ".scrape_cache.json"
            assert (
                cache_file.exists()
            ), "Scrape cache should be created even with missing artwork"

            # Verify that download functions were NOT called since there are no URLs
            assert (
                not mock_download_image.called
            ), "download_image should not be called when no URLs exist"
            assert (
                not mock_download_marquee.called
            ), "download_marquee should not be called when no URLs exist"


def test_scraper_continues_on_partial_failures():
    """Test that scraper continues processing even when some operations fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        show_dir = Path(tmpdir) / "Test Show"
        show_dir.mkdir(parents=True, exist_ok=True)
        (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

        # Mock TVDB to return data with some artwork URLs
        with patch("mpv_scraper.scraper.tvdb") as mock_tvdb, patch(
            "mpv_scraper.scraper.download_image"
        ) as mock_download_image, patch(
            "mpv_scraper.scraper.download_marquee"
        ) as mock_download_marquee:
            # Mock successful TVDB responses with mixed artwork availability
            mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
            mock_tvdb.get_series_extended.return_value = {
                "episodes": [
                    {
                        "seasonNumber": 1,
                        "number": 1,
                        "overview": "Test episode",
                        "image": "https://example.com/episode.png",  # Has episode image
                    }
                ],
                "image": "https://example.com/poster.png",  # Has poster
                "artworks": {"clearLogo": "https://example.com/logo.png"},  # Has logo
                "siteRating": 8.5,
            }

            # Mock download functions to fail for some URLs but succeed for others
            def mock_download_side_effect(url, dest, headers=None):
                if "episode" in url:
                    raise Exception("Episode image failed")
                elif "logo" in url:
                    raise Exception("Logo failed")
                # Poster download succeeds
                return None

            mock_download_image.side_effect = mock_download_side_effect
            mock_download_marquee.side_effect = Exception("Logo download failed")

            # This should not crash - should handle partial failures gracefully
            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()
            tasks = scrape_tv_parallel(show_dir, download_manager)

            # Verify that the scrape cache was still created
            cache_file = show_dir / ".scrape_cache.json"
            assert (
                cache_file.exists()
            ), "Scrape cache should be created despite partial failures"

            # Verify that tasks were queued (parallel system queues instead of immediate execution)
            assert len(tasks) > 0, "Should queue download tasks for parallel processing"

            # Verify that poster download was attempted (this happens immediately)
            assert (
                mock_download_image.call_count >= 1
            ), "Should attempt to download poster image"
            assert (
                mock_download_marquee.called
            ), "Should attempt to download logo even if it fails"
