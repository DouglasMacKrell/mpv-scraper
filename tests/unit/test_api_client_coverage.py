"""Test API client coverage for Sprint 18.7."""

import pytest
from unittest.mock import Mock, patch

from mpv_scraper.tvdb import authenticate_tvdb, search_show, get_series_extended
from mpv_scraper.tmdb import search_movie, get_movie_images, get_movie_details
from mpv_scraper.tvmaze import search_show as tvmaze_search_show, get_show_episodes
from mpv_scraper.omdb import (
    search_movie as omdb_search_movie,
    get_movie_details as omdb_get_movie_details,
)


class TestTVDBAPICoverage:
    """Test TVDB API functionality to improve coverage."""

    def test_authenticate_tvdb_success(self):
        """Test successful TVDB authentication."""
        # Clear any cached token first
        from mpv_scraper.tvdb import _set_to_cache

        _set_to_cache("tvdb_token", None)

        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {"token": "test_token"}
                mock_post.return_value = mock_response

                result = authenticate_tvdb()

                assert result is not None
                assert isinstance(result, str)
                mock_post.assert_called_once()

    def test_authenticate_tvdb_no_api_key(self):
        """Test TVDB authentication with no API key."""
        with patch("os.getenv", return_value=None):
            with pytest.raises(
                ValueError, match="TVDB_API_KEY environment variable not set"
            ):
                authenticate_tvdb()

    def test_search_show_basic(self):
        """Test basic series search functionality."""
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

                assert results is not None
                assert len(results) > 0

    def test_get_series_extended_basic(self):
        """Test basic series extended info retrieval."""
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
                            "episodeName": "Pilot",
                        }
                    ]
                }
                mock_episodes_response.status_code = 200

                mock_get.side_effect = [mock_series_response, mock_episodes_response]

                series_info = get_series_extended(1, "test_token")

                assert series_info is not None
                assert "name" in series_info


class TestTMDBAPICoverage:
    """Test TMDB API functionality to improve coverage."""

    def test_search_movie_basic(self):
        """Test basic movie search functionality."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "results": [
                        {
                            "id": 1,
                            "title": "Test Movie",
                            "release_date": "2020-01-01",
                            "vote_average": 8.5,
                        }
                    ]
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                results = search_movie("Test Movie", 2020)

                assert results is not None
                assert len(results) > 0

    def test_search_movie_no_api_key(self):
        """Test movie search with no API key."""
        with patch("os.getenv", return_value=None):
            with pytest.raises(
                ValueError, match="TMDB_API_KEY environment variable not set"
            ):
                search_movie("Test Movie", 2020)

    def test_get_movie_images_basic(self):
        """Test basic movie images retrieval."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "posters": [{"file_path": "/poster1.jpg", "vote_average": 8.5}],
                    "backdrops": [{"file_path": "/backdrop1.jpg", "vote_average": 8.0}],
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                images = get_movie_images(1)

                assert images is not None
                assert "posters" in images
                assert "backdrops" in images

    def test_get_movie_details_basic(self):
        """Test basic movie details retrieval."""
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


class TestTVMazeAPICoverage:
    """Test TVMaze API functionality to improve coverage."""

    def test_search_show_basic(self):
        """Test basic show search functionality."""
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
        """Test basic episode retrieval functionality."""
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


class TestOMDBAPICoverage:
    """Test OMDB API functionality to improve coverage."""

    def test_search_movie_basic(self):
        """Test basic movie search functionality."""
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
                    "totalResults": "1",
                    "Response": "True",
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                results = omdb_search_movie("Test Movie", 2020)

                assert results is not None
                assert len(results) > 0

    def test_search_movie_no_api_key(self):
        """Test movie search with no API key."""
        # Clear any cached results first
        from mpv_scraper.tvdb import _set_to_cache

        _set_to_cache("omdb_search_test_movie_2020", None)

        with patch("os.getenv", return_value=None):
            with pytest.raises(
                ValueError, match="OMDB_API_KEY environment variable not set"
            ):
                omdb_search_movie("Test Movie", 2020)

    def test_get_movie_details_basic(self):
        """Test basic movie details retrieval."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "Title": "Test Movie",
                    "Year": "2020",
                    "Plot": "A test movie",
                    "imdbRating": "8.5",
                    "Runtime": "120 min",
                    "Genre": "Action, Drama",
                    "Response": "True",
                }
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                details = omdb_get_movie_details("tt1234567")

                assert details is not None
                assert "title" in details
                assert "vote_average" in details
