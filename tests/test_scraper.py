"""Unit tests for scraper error handling (Sprint 10.5)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch


from mpv_scraper.scraper import (
    scrape_tv_parallel,
    scrape_movie,
    _is_episode_scraped,
    _is_movie_scraped,
    _load_scrape_cache,
    _normalize_api_id,
    _validate_id_matches_filename,
    _prompt_for_resolution,
)


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


def test_is_episode_scraped_checks_cache():
    """Test that _is_episode_scraped correctly checks cache and image existence."""

    with tempfile.TemporaryDirectory() as tmpdir:
        show_dir = Path(tmpdir) / "Test Show"
        show_dir.mkdir(parents=True, exist_ok=True)
        images_dir = show_dir / "images"
        images_dir.mkdir()

        # Create cache with episode
        cache = {
            "episodes": [
                {
                    "seasonNumber": 1,
                    "number": 1,
                    "overview": "Test episode",
                }
            ],
            "siteRating": 8.5,
        }
        cache_file = show_dir / ".scrape_cache.json"
        cache_file.write_text(json.dumps(cache))

        # Create episode image
        img_path = images_dir / "Test Show - S01E01-image.png"
        img_path.touch()

        # Load cache and check
        loaded_cache = _load_scrape_cache(cache_file)
        assert _is_episode_scraped(
            show_dir, 1, 1, loaded_cache, images_dir, "Test Show"
        )

        # Episode not in cache
        assert not _is_episode_scraped(
            show_dir, 1, 2, loaded_cache, images_dir, "Test Show"
        )

        # Episode in cache but no image
        img_path.unlink()
        assert not _is_episode_scraped(
            show_dir, 1, 1, loaded_cache, images_dir, "Test Show"
        )


def test_is_movie_scraped_checks_cache():
    """Test that _is_movie_scraped correctly checks cache and image existence."""

    with tempfile.TemporaryDirectory() as tmpdir:
        movie_dir = Path(tmpdir)
        movie_path = movie_dir / "Clue (1985).mkv"
        movie_path.touch()
        images_dir = movie_dir / "images"
        images_dir.mkdir()

        # Create cache with movie
        cache = {
            "title": "Clue",
            "overview": "Test movie",
            "release_date": "1985-12-13",
        }
        cache_file = movie_dir / ".scrape_cache.json"
        cache_file.write_text(json.dumps(cache))

        # Create movie image
        img_path = images_dir / "Clue (1985)-image.png"
        img_path.touch()

        # Load cache and check
        loaded_cache = _load_scrape_cache(cache_file)
        assert _is_movie_scraped(movie_path, loaded_cache, images_dir)

        # No image
        img_path.unlink()
        assert not _is_movie_scraped(movie_path, loaded_cache, images_dir)

        # No cache
        assert not _is_movie_scraped(movie_path, None, images_dir)


def test_normalize_api_id():
    """Test that API ID normalization works correctly."""
    # Test dash separator
    assert _normalize_api_id("tvdb-70533") == ("tvdb", "70533")
    assert _normalize_api_id("TVDB-70533") == ("tvdb", "70533")  # Case insensitive
    assert _normalize_api_id("tmdb-15196") == ("tmdb", "15196")

    # Test colon separator
    assert _normalize_api_id("tvdb:70533") == ("tvdb", "70533")
    assert _normalize_api_id("TVDB:70533") == ("tvdb", "70533")

    # Test invalid formats
    assert _normalize_api_id("invalid-format") is None
    assert _normalize_api_id("unsupported-12345") is None
    assert _normalize_api_id("tvdb-abc") is None  # Non-numeric ID
    assert _normalize_api_id("just-text") is None


def test_validate_id_matches_filename():
    """Test that ID validation works correctly."""

    # Valid IDs
    is_valid, error = _validate_id_matches_filename("70533", "tvdb", "test.mkv", None)
    assert is_valid
    assert error is None

    # Invalid ID (non-numeric)
    is_valid, error = _validate_id_matches_filename("abc", "tvdb", "test.mkv", None)
    assert not is_valid
    assert error is not None


def test_prompt_on_ambiguity_multiple_results(monkeypatch):
    """Test that prompt works on ambiguous results."""
    from mpv_scraper.types import TVMeta

    search_results = [
        {"id": 1, "name": "Show A", "year": "2020"},
        {"id": 2, "name": "Show B", "year": "2021"},
    ]
    parsed_meta = TVMeta(show="Test Show", season=1, start_ep=1, end_ep=1)

    # Mock user input: select first result
    inputs = ["1"]
    monkeypatch.setattr("click.prompt", lambda *args, **kwargs: inputs.pop(0))

    result = _prompt_for_resolution(
        "Test Show - S01E01.mkv", search_results=search_results, parsed_meta=parsed_meta
    )
    assert result == "tvdb-1"  # Should return normalized API ID


def test_prompt_on_failure_no_results(monkeypatch):
    """Test that prompt works on search failure."""
    from mpv_scraper.types import MovieMeta

    parsed_meta = MovieMeta(title="Test Movie", year=2020)
    error = "Could not find metadata"

    # Mock user input: provide API ID
    inputs = ["tmdb-15196"]
    monkeypatch.setattr("click.prompt", lambda *args, **kwargs: inputs.pop(0))

    result = _prompt_for_resolution(
        "Test Movie (2020).mkv",
        search_results=None,
        error=error,
        parsed_meta=parsed_meta,
    )
    assert result == "tmdb-15196"


def test_prompt_skip_option(monkeypatch):
    """Test that skip option works correctly."""
    search_results = [{"id": 1, "name": "Show A"}]

    # Mock user input: skip
    inputs = ["skip"]
    monkeypatch.setattr("click.prompt", lambda *args, **kwargs: inputs.pop(0))

    result = _prompt_for_resolution("Test.mkv", search_results=search_results)
    assert result is None


def test_filename_tag_bypasses_search():
    """Test that filename API tags bypass search and use direct lookup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        show_dir = Path(tmpdir) / "Twin Peaks"
        show_dir.mkdir(parents=True, exist_ok=True)
        # Create episode file with API tag
        (show_dir / "Twin Peaks - S01E01 - Pilot {tvdb-70533}.mp4").touch()

        with patch("mpv_scraper.scraper.tvdb") as mock_tvdb, patch(
            "mpv_scraper.scraper.download_image"
        ), patch("mpv_scraper.scraper.download_marquee"):
            mock_tvdb.authenticate_tvdb.return_value = "token"
            # Mock direct lookup (should be called, not search)
            mock_tvdb.get_series_extended.return_value = {
                "episodes": [
                    {
                        "seasonNumber": 1,
                        "number": 1,
                        "overview": "Test episode",
                    }
                ],
                "image": "https://example.com/poster.png",
                "artworks": {},
                "siteRating": 8.5,
            }

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()
            scrape_tv_parallel(show_dir, download_manager)

            # Verify search was NOT called (direct lookup used instead)
            assert not mock_tvdb.search_show.called
            # Verify direct lookup WAS called
            assert mock_tvdb.get_series_extended.called
            assert mock_tvdb.get_series_extended.call_args[0][0] == 70533


def test_filename_tag_tvdb_direct_lookup():
    """Test that TVDB API tag performs direct lookup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        show_dir = Path(tmpdir) / "Test Show"
        show_dir.mkdir(parents=True, exist_ok=True)
        (show_dir / "Test Show - S01E01 - Pilot {tvdb-12345}.mp4").touch()

        with patch("mpv_scraper.scraper.tvdb") as mock_tvdb, patch(
            "mpv_scraper.scraper.download_image"
        ), patch("mpv_scraper.scraper.download_marquee"):
            mock_tvdb.authenticate_tvdb.return_value = "token"
            mock_tvdb.get_series_extended.return_value = {
                "episodes": [{"seasonNumber": 1, "number": 1}],
                "image": "https://example.com/poster.png",
                "artworks": {},
            }

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()
            scrape_tv_parallel(show_dir, download_manager)

            # Should call get_series_extended with ID 12345
            mock_tvdb.get_series_extended.assert_called_with(12345, "token")
            # Should NOT call search_show
            assert not mock_tvdb.search_show.called


def test_filename_tag_tmdb_direct_lookup():
    """Test that TMDB API tag performs direct lookup for movies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        movie_file = Path(tmpdir) / "Clue (1985) {tmdb-15196}.mkv"
        movie_file.touch()

        with patch("mpv_scraper.scraper.tmdb") as mock_tmdb, patch(
            "mpv_scraper.scraper.download_image"
        ), patch("mpv_scraper.scraper.download_marquee"):
            mock_tmdb.get_movie_details.return_value = {
                "id": 15196,
                "title": "Clue",
                "overview": "Test movie",
                "poster_url": "https://example.com/poster.png",
            }

            scrape_movie(movie_file)

            # Should call get_movie_details with ID 15196
            mock_tmdb.get_movie_details.assert_called_with(15196)
            # Should NOT call search_movie
            assert not mock_tmdb.search_movie.called


def test_filename_tag_fallback_providers():
    """Test that API tags work with fallback providers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        show_dir = Path(tmpdir) / "Test Show"
        show_dir.mkdir(parents=True, exist_ok=True)
        (show_dir / "Test Show - S01E01 - Pilot {tvmaze-12345}.mp4").touch()

        with patch("mpv_scraper.tvmaze.get_show_episodes") as mock_get_episodes, patch(
            "mpv_scraper.scraper.download_image"
        ), patch("mpv_scraper.scraper.download_marquee"):
            mock_get_episodes.return_value = [
                {"season": 1, "number": 1, "name": "Pilot"}
            ]

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()
            # Use fallback-only to trigger TVmaze path
            scrape_tv_parallel(show_dir, download_manager, fallback_only=True)

            # Should call get_show_episodes with ID 12345
            mock_get_episodes.assert_called_with(12345)


def test_episode_matching_with_none_season():
    """Test that episode matching works for shows with seasonNumber=None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        show_dir = Path(tmpdir) / "Test Show"
        show_dir.mkdir(parents=True, exist_ok=True)
        (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

        with patch("mpv_scraper.scraper.tvdb") as mock_tvdb, patch(
            "mpv_scraper.scraper.download_image"
        ) as mock_download_image, patch("mpv_scraper.scraper.download_marquee"):
            # Mock TVDB response with episode that has seasonNumber=None
            mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
            mock_tvdb.get_series_extended.return_value = {
                "id": 1,
                "name": "Test Show",
                "episodes": [
                    {
                        "id": 101,
                        "seasonNumber": None,  # Some shows don't have seasons
                        "number": 1,
                        "overview": "Pilot episode",
                        "image": "https://example.com/ep1.png",
                    }
                ],
                "image": "https://example.com/poster.png",
                "siteRating": 8.5,
            }
            mock_tvdb.authenticate_tvdb.return_value = "token"

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()
            scrape_tv_parallel(show_dir, download_manager)

            # Should match episode even with seasonNumber=None
            # The episode should be matched when target_season is 1 and episode number matches
            assert mock_download_image.called or len(download_manager.tasks) > 0
