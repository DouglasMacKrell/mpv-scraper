"""Simple scraper coverage tests for Sprint 18.5.

Tests basic scraper functionality to improve coverage from 65% to 80%+.
Focuses on error handling paths and edge cases without complex mocking.
"""

import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock


class TestScraperBasicCoverage:
    """Test basic scraper functionality to improve coverage."""

    def test_scraper_imports_and_structure(self):
        """Test that scraper module can be imported and has expected structure."""
        from mpv_scraper.scraper import (
            ParallelDownloadManager,
            DownloadTask,
        )

        # Test that classes can be instantiated
        download_manager = ParallelDownloadManager()
        assert download_manager.max_workers == 8

        # Test that DownloadTask can be created
        task = DownloadTask(
            url="http://example.com/image.jpg",
            dest_path=Path("/tmp/test.jpg"),
            source="TVDB",
            show_name="Test Show",
            episode_info="S01E01",
        )
        assert task.url == "http://example.com/image.jpg"
        assert task.source == "TVDB"

    def test_parallel_download_manager_basic_operations(self):
        """Test ParallelDownloadManager basic operations."""
        from mpv_scraper.scraper import ParallelDownloadManager, DownloadTask

        download_manager = ParallelDownloadManager(max_workers=2)

        # Test adding tasks
        task1 = DownloadTask(
            url="http://example.com/image1.jpg",
            dest_path=Path("/tmp/test1.jpg"),
            source="TVDB",
            show_name="Test Show",
            episode_info="S01E01",
        )
        task2 = DownloadTask(
            url="http://example.com/image2.jpg",
            dest_path=Path("/tmp/test2.jpg"),
            source="TMDB",
            show_name="Test Show",
            episode_info="S01E02",
        )

        download_manager.add_task(task1)
        download_manager.add_task(task2)
        download_manager.add_task(None)  # Shutdown signal

        # Test execution with mocked downloads
        with patch("mpv_scraper.scraper.download_image"):
            results = download_manager.execute_downloads()

        # Should have results for both tasks
        assert len(results) == 2
        assert all(isinstance(result, tuple) for result in results)
        assert all(len(result) == 3 for result in results)

    def test_parallel_download_manager_empty_queue(self):
        """Test ParallelDownloadManager with empty queue."""
        from mpv_scraper.scraper import ParallelDownloadManager

        download_manager = ParallelDownloadManager(max_workers=2)

        # Test execution with no tasks
        results = download_manager.execute_downloads()

        # Should return empty results
        assert results == []

    def test_parallel_download_manager_worker_error_handling(self):
        """Test ParallelDownloadManager handles worker errors gracefully."""
        from mpv_scraper.scraper import ParallelDownloadManager, DownloadTask

        download_manager = ParallelDownloadManager(max_workers=1)

        # Create a task that will fail
        task = DownloadTask(
            url="http://example.com/image.jpg",
            dest_path=Path("/nonexistent/path/image.jpg"),
            source="TVDB",
            show_name="Test Show",
            episode_info="S01E01",
        )

        download_manager.add_task(task)
        download_manager.add_task(None)  # Shutdown signal

        # Mock download_image to fail
        with patch(
            "mpv_scraper.scraper.download_image",
            side_effect=Exception("Download failed"),
        ):
            results = download_manager.execute_downloads()

        # Should have one result with failure
        assert len(results) == 1
        task, success, error = results[0]
        assert not success
        assert error is not None
        assert "Download failed" in error

    def test_scraper_with_top_images_dir(self):
        """Test scraper works with top-level images directory."""
        from mpv_scraper.scraper import scrape_tv_parallel

        with tempfile.TemporaryDirectory() as tmpdir:
            show_dir = Path(tmpdir) / "Test Show"
            show_dir.mkdir(parents=True, exist_ok=True)
            (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

            top_images_dir = Path(tmpdir) / "images"
            top_images_dir.mkdir(exist_ok=True)

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()

            # Mock the problematic search loop to avoid API calls
            with patch("mpv_scraper.scraper.tvdb") as mock_tvdb:
                mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
                mock_tvdb.get_series_extended.return_value = {
                    "episodes": [],
                    "image": None,
                    "artworks": {},
                    "siteRating": 8.5,
                }

                # This should work with top-level images directory
                result = scrape_tv_parallel(
                    show_dir, download_manager, top_images_dir=top_images_dir
                )

                # Should return a list of tasks
                assert isinstance(result, list)

                # Should create cache file in show directory
                cache_file = show_dir / ".scrape_cache.json"
                assert cache_file.exists()

    def test_movie_scraper_with_top_images_dir(self):
        """Test movie scraper works with top-level images directory."""
        from mpv_scraper.scraper import scrape_movie

        with tempfile.TemporaryDirectory() as tmpdir:
            movie_file = Path(tmpdir) / "Test Movie (2020).mp4"
            movie_file.touch()

            top_images_dir = Path(tmpdir) / "images"
            top_images_dir.mkdir(exist_ok=True)

            # Mock TMDB to avoid API calls
            with patch("mpv_scraper.scraper.tmdb") as mock_tmdb:
                mock_tmdb.search_movie.return_value = [{"id": 1, "title": "Test Movie"}]
                mock_tmdb.get_movie_details.return_value = {
                    "id": 1,
                    "title": "Test Movie",
                    "overview": "Test movie description",
                    "vote_average": 0.75,
                    "poster_url": None,
                    "logo_url": None,
                }

                # This should work with top-level images directory
                scrape_movie(movie_file, top_images_dir=top_images_dir)

                # Should create cache file in movie directory
                cache_file = movie_file.parent / ".scrape_cache.json"
                assert cache_file.exists()

    def test_scraper_with_transaction_logger(self):
        """Test scraper works with transaction logger."""
        from mpv_scraper.scraper import scrape_tv_parallel

        with tempfile.TemporaryDirectory() as tmpdir:
            show_dir = Path(tmpdir) / "Test Show"
            show_dir.mkdir(parents=True, exist_ok=True)
            (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

            # Mock transaction logger
            mock_logger = Mock()
            mock_logger.log_create = Mock()

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()

            # Mock the problematic search loop to avoid API calls
            with patch("mpv_scraper.scraper.tvdb") as mock_tvdb:
                mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
                mock_tvdb.get_series_extended.return_value = {
                    "episodes": [],
                    "image": None,
                    "artworks": {},
                    "siteRating": 8.5,
                }

                # This should work with transaction logger
                result = scrape_tv_parallel(
                    show_dir, download_manager, transaction_logger=mock_logger
                )

                # Should return a list of tasks
                assert isinstance(result, list)

                # Should call transaction logger
                assert mock_logger.log_create.called

    def test_movie_scraper_with_transaction_logger(self):
        """Test movie scraper works with transaction logger."""
        from mpv_scraper.scraper import scrape_movie

        with tempfile.TemporaryDirectory() as tmpdir:
            movie_file = Path(tmpdir) / "Test Movie (2020).mp4"
            movie_file.touch()

            # Mock transaction logger
            mock_logger = Mock()
            mock_logger.log_create = Mock()

            # Mock TMDB to avoid API calls
            with patch("mpv_scraper.scraper.tmdb") as mock_tmdb:
                mock_tmdb.search_movie.return_value = [{"id": 1, "title": "Test Movie"}]
                mock_tmdb.get_movie_details.return_value = {
                    "id": 1,
                    "title": "Test Movie",
                    "overview": "Test movie description",
                    "vote_average": 0.75,
                    "poster_url": None,
                    "logo_url": None,
                }

                # This should work with transaction logger
                scrape_movie(movie_file, transaction_logger=mock_logger)

                # Should call transaction logger
                assert mock_logger.log_create.called

    def test_scraper_cache_structure(self):
        """Test scraper creates proper cache structure."""
        from mpv_scraper.scraper import scrape_tv_parallel

        with tempfile.TemporaryDirectory() as tmpdir:
            show_dir = Path(tmpdir) / "Test Show"
            show_dir.mkdir(parents=True, exist_ok=True)
            (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()

            # Mock the problematic search loop to avoid API calls
            with patch("mpv_scraper.scraper.tvdb") as mock_tvdb:
                mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
                mock_tvdb.get_series_extended.return_value = {
                    "episodes": [
                        {
                            "seasonNumber": 1,
                            "number": 1,
                            "overview": "Test episode",
                            "image": "http://example.com/image.jpg",
                        }
                    ],
                    "image": "http://example.com/poster.jpg",
                    "artworks": {"clearLogo": "http://example.com/logo.jpg"},
                    "siteRating": 8.5,
                }

                # Run scraper
                scrape_tv_parallel(show_dir, download_manager)

                # Check cache file structure
                cache_file = show_dir / ".scrape_cache.json"
                assert cache_file.exists()

                cache_data = json.loads(cache_file.read_text())
                assert isinstance(cache_data, dict)
                assert "episodes" in cache_data
                assert isinstance(cache_data["episodes"], list)

    def test_movie_scraper_cache_structure(self):
        """Test movie scraper creates proper cache structure."""
        from mpv_scraper.scraper import scrape_movie

        with tempfile.TemporaryDirectory() as tmpdir:
            movie_file = Path(tmpdir) / "Test Movie (2020).mp4"
            movie_file.touch()

            # Mock TMDB to avoid API calls
            with patch("mpv_scraper.scraper.tmdb") as mock_tmdb:
                mock_tmdb.search_movie.return_value = [{"id": 1, "title": "Test Movie"}]
                mock_tmdb.get_movie_details.return_value = {
                    "id": 1,
                    "title": "Test Movie",
                    "overview": "Test movie description",
                    "vote_average": 0.75,
                    "poster_url": None,
                    "logo_url": None,
                }

                # Run movie scraper
                scrape_movie(movie_file)

                # Check cache file structure
                cache_file = movie_file.parent / ".scrape_cache.json"
                assert cache_file.exists()

                cache_data = json.loads(cache_file.read_text())
                assert isinstance(cache_data, dict)

    def test_scraper_with_mixed_file_types(self):
        """Test scraper handles mixed file types."""
        from mpv_scraper.scraper import scrape_tv_parallel

        with tempfile.TemporaryDirectory() as tmpdir:
            show_dir = Path(tmpdir) / "Test Show"
            show_dir.mkdir(parents=True, exist_ok=True)
            (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()
            (show_dir / "Test Show - S01E02 - Episode.mkv").touch()

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()

            # Mock the problematic search loop to avoid API calls
            with patch("mpv_scraper.scraper.tvdb") as mock_tvdb:
                mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
                mock_tvdb.get_series_extended.return_value = {
                    "episodes": [
                        {
                            "seasonNumber": 1,
                            "number": 1,
                            "overview": "Test episode 1",
                        },
                        {
                            "seasonNumber": 1,
                            "number": 2,
                            "overview": "Test episode 2",
                        },
                    ],
                    "image": None,
                    "artworks": {},
                    "siteRating": 8.5,
                }

                # This should work with mixed file types
                result = scrape_tv_parallel(show_dir, download_manager)

                # Should return a list of tasks
                assert isinstance(result, list)

                # Should create cache file
                cache_file = show_dir / ".scrape_cache.json"
                assert cache_file.exists()

    def test_scraper_rating_normalization(self):
        """Test scraper normalizes ratings properly."""
        from mpv_scraper.scraper import scrape_tv_parallel

        with tempfile.TemporaryDirectory() as tmpdir:
            show_dir = Path(tmpdir) / "Test Show"
            show_dir.mkdir(parents=True, exist_ok=True)
            (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()

            # Mock the problematic search loop to avoid API calls
            with patch("mpv_scraper.scraper.tvdb") as mock_tvdb:
                mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
                mock_tvdb.get_series_extended.return_value = {
                    "episodes": [],
                    "image": None,
                    "artworks": {},
                    "siteRating": 8.5,  # Should be normalized to 0.85
                }

                # Run scraper
                scrape_tv_parallel(show_dir, download_manager)

                # Check cache file for rating normalization
                cache_file = show_dir / ".scrape_cache.json"
                assert cache_file.exists()

                cache_data = json.loads(cache_file.read_text())
                assert cache_data["siteRating"] == 0.85

    def test_movie_scraper_error_handling_basic(self):
        """Test basic movie scraper error handling."""
        from mpv_scraper.scraper import scrape_movie

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with invalid movie name format
            movie_file = Path(tmpdir) / "Invalid Movie Name.mp4"
            movie_file.touch()

            # This should handle invalid movie name gracefully
            scrape_movie(movie_file, no_remote=True)

            # Should create cache file even with invalid name
            cache_file = movie_file.parent / ".scrape_cache.json"
            assert cache_file.exists()

    def test_scraper_download_task_creation(self):
        """Test scraper creates download tasks properly."""
        from mpv_scraper.scraper import scrape_tv_parallel

        with tempfile.TemporaryDirectory() as tmpdir:
            show_dir = Path(tmpdir) / "Test Show"
            show_dir.mkdir(parents=True, exist_ok=True)
            (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()

            # Mock the problematic search loop to avoid API calls
            with patch("mpv_scraper.scraper.tvdb") as mock_tvdb:
                mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
                mock_tvdb.get_series_extended.return_value = {
                    "episodes": [
                        {
                            "seasonNumber": 1,
                            "number": 1,
                            "overview": "Test episode",
                            "image": "http://example.com/image.jpg",
                        }
                    ],
                    "image": "http://example.com/poster.jpg",
                    "artworks": {"clearLogo": "http://example.com/logo.jpg"},
                    "siteRating": 8.5,
                }

                # Run scraper
                result = scrape_tv_parallel(show_dir, download_manager)

                # Should return a list of download tasks
                assert isinstance(result, list)
                assert len(result) > 0

                # Check that tasks have expected structure
                for task in result:
                    assert hasattr(task, "url")
                    assert hasattr(task, "dest_path")
                    assert hasattr(task, "source")
                    assert hasattr(task, "show_name")
                    assert hasattr(task, "episode_info")

    def test_scraper_image_download_error_handling(self):
        """Test scraper handles image download errors gracefully."""
        from mpv_scraper.scraper import scrape_tv_parallel

        with tempfile.TemporaryDirectory() as tmpdir:
            show_dir = Path(tmpdir) / "Test Show"
            show_dir.mkdir(parents=True, exist_ok=True)
            (show_dir / "Test Show - S01E01 - Pilot.mp4").touch()

            from mpv_scraper.scraper import ParallelDownloadManager

            download_manager = ParallelDownloadManager()

            # Mock the problematic search loop to avoid API calls
            with patch("mpv_scraper.scraper.tvdb") as mock_tvdb, patch(
                "mpv_scraper.scraper.download_image",
                side_effect=Exception("Download failed"),
            ), patch(
                "mpv_scraper.scraper.download_marquee",
                side_effect=Exception("Download failed"),
            ):
                mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
                mock_tvdb.get_series_extended.return_value = {
                    "episodes": [
                        {
                            "seasonNumber": 1,
                            "number": 1,
                            "overview": "Test episode",
                            "image": "http://example.com/image.jpg",
                        }
                    ],
                    "image": "http://example.com/poster.jpg",
                    "artworks": {"clearLogo": "http://example.com/logo.jpg"},
                    "siteRating": 8.5,
                }

                # This should not crash - should handle download failures gracefully
                result = scrape_tv_parallel(show_dir, download_manager)

                # Should return a list of tasks
                assert isinstance(result, list)

                # Should create cache file despite download failures
                cache_file = show_dir / ".scrape_cache.json"
                assert cache_file.exists()
