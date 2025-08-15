"""Test API coverage improvement for Sprint 18.7."""

import pytest
from unittest.mock import Mock, patch

from mpv_scraper.tvdb import authenticate_tvdb, search_show, get_series_extended
from mpv_scraper.tmdb import search_movie, get_movie_images, get_movie_details
from mpv_scraper.tvmaze import search_show as tvmaze_search_show, get_show_episodes
from mpv_scraper.omdb import (
    search_movie as omdb_search_movie,
    get_movie_details as omdb_get_movie_details,
)


class TestTVDBCoverageImprovement:
    """Test TVDB coverage improvement for missing lines."""

    def test_authenticate_tvdb_no_api_key(self):
        """Test authenticate_tvdb with no API key."""
        with patch("os.getenv", return_value=None):
            with pytest.raises(
                ValueError, match="TVDB_API_KEY environment variable not set"
            ):
                authenticate_tvdb()

    def test_search_show_cache_hit(self):
        """Test search_show with cache hit."""
        # First call to populate cache
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "data": [
                        {"id": 1, "seriesName": "Test Show", "firstAired": "2020-01-01"}
                    ]
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                results = search_show("Test Show", "test_token")
                assert len(results) > 0

        # Second call should hit cache
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                results = search_show("Test Show", "test_token")
                assert len(results) > 0
                # Should not make another API call
                mock_get.assert_not_called()

    def test_get_series_extended_basic(self):
        """Test get_series_extended basic functionality."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_series_response = Mock()
                mock_series_response.json.return_value = {
                    "data": {
                        "id": 1,
                        "seriesName": "Test Show",
                        "overview": "A test show",
                        "firstAired": "2020-01-01",
                    }
                }
                mock_series_response.status_code = 200

                mock_episodes_response = Mock()
                mock_episodes_response.json.return_value = {
                    "data": [
                        {
                            "id": 1,
                            "airedEpisodeNumber": 1,
                            "airedSeason": 1,
                            "episodeName": "Test Episode",
                        }
                    ]
                }
                mock_episodes_response.status_code = 200

                mock_get.side_effect = [mock_series_response, mock_episodes_response]

                result = get_series_extended(1, "test_token")

                assert result is not None
                assert "name" in result
                assert "episodes" in result


class TestTMDBCoverageImprovement:
    """Test TMDB coverage improvement for missing lines."""

    def test_search_movie_no_api_key(self):
        """Test search_movie with no API key."""
        with patch("os.getenv", return_value=None):
            with pytest.raises(
                ValueError, match="TMDB_API_KEY environment variable not set"
            ):
                search_movie("Test Movie", 2020)

    def test_get_movie_images_no_api_key(self):
        """Test get_movie_images with no API key."""
        with patch("os.getenv", return_value=None):
            with pytest.raises(
                ValueError, match="TMDB_API_KEY environment variable not set"
            ):
                get_movie_images(1)

    def test_get_movie_details_basic(self):
        """Test get_movie_details basic functionality."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "id": 1,
                    "title": "Test Movie",
                    "overview": "Test overview",
                    "vote_average": 8.5,
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                details = get_movie_details(1)

                assert details is not None
                assert "title" in details


class TestTVMazeCoverageImprovement:
    """Test TVMaze coverage improvement for missing lines."""

    def test_search_show_basic(self):
        """Test search_show basic functionality."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = [
                {
                    "show": {
                        "id": 1,
                        "name": "Test Show",
                        "summary": "A test show",
                        "premiered": "2020-01-01",
                    }
                }
            ]
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            results = tvmaze_search_show("Test Show")

            assert results is not None
            assert len(results) > 0

    def test_get_show_episodes_basic(self):
        """Test get_show_episodes basic functionality."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = [
                {
                    "id": 1,
                    "name": "Pilot",
                    "season": 1,
                    "number": 1,
                    "summary": "The pilot episode",
                }
            ]
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            episodes = get_show_episodes(1)

            assert episodes is not None
            assert len(episodes) > 0


class TestOMDBCoverageImprovement:
    """Test OMDB coverage improvement for missing lines."""

    def test_search_movie_no_api_key(self):
        """Test search_movie with no API key."""
        # Clear any cached results first
        from mpv_scraper.tvdb import _set_to_cache

        _set_to_cache("omdb_search_test_movie_2020", None)

        with patch("os.getenv", return_value=None):
            with pytest.raises(
                ValueError, match="OMDB_API_KEY environment variable not set"
            ):
                omdb_search_movie("Test Movie", 2020)

    def test_search_movie_basic(self):
        """Test search_movie basic functionality."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "Search": [
                        {
                            "Title": "Test Movie",
                            "Year": "2020",
                            "imdbID": "tt1234567",
                            "Type": "movie",
                        }
                    ],
                    "Response": "True",
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                results = omdb_search_movie("Test Movie", 2020)

                assert results is not None
                assert len(results) > 0

    def test_get_movie_details_no_api_key(self):
        """Test get_movie_details with no API key."""
        # Clear any cached results first
        from mpv_scraper.tvdb import _set_to_cache

        _set_to_cache("omdb_details_tt1234567", None)

        with patch("os.getenv", return_value=None):
            with pytest.raises(
                ValueError, match="OMDB_API_KEY environment variable not set"
            ):
                omdb_get_movie_details("tt1234567")

    def test_get_movie_details_basic(self):
        """Test get_movie_details basic functionality."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "Title": "Test Movie",
                    "Year": "2020",
                    "Plot": "Test plot",
                    "imdbRating": "8.5",
                    "Response": "True",
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                details = omdb_get_movie_details("tt1234567")

                assert details is not None
                assert "title" in details
                assert "vote_average" in details
