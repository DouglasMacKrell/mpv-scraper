import pytest
from unittest.mock import patch, MagicMock

from mpv_scraper.tmdb import search_movie


@pytest.fixture
def mock_env_api_key(monkeypatch):
    """Fixture to set the TMDB_API_KEY environment variable."""
    monkeypatch.setenv("TMDB_API_KEY", "test_tmdb_api_key")


def test_search_movie_raises_on_missing_key(monkeypatch):
    """
    Tests that search_movie raises a ValueError if the TMDB_API_KEY is not set.
    """
    monkeypatch.delenv("TMDB_API_KEY", raising=False)
    with pytest.raises(ValueError, match="TMDB_API_KEY environment variable not set."):
        search_movie("Dune", 2021)


@patch("requests.get")
@patch("time.sleep", return_value=None)
def test_search_movie_by_title_year(mock_sleep, mock_get, mock_env_api_key):
    """
    Tests that search_movie correctly calls the TMDB API with title and year.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"id": 1, "title": "Dune"}]}
    mock_get.return_value = mock_response

    results = search_movie("Dune", 2021)
    assert results[0]["title"] == "Dune"

    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["query"] == "Dune"
    assert kwargs["params"]["year"] == 2021
    assert kwargs["params"]["api_key"] == "test_tmdb_api_key"
    mock_sleep.assert_called_once()


@patch("requests.get")
@patch("time.sleep", return_value=None)
@patch("mpv_scraper.tmdb._get_from_cache")
@patch("mpv_scraper.tmdb._set_to_cache")
def test_search_movie_caches_results(
    mock_set_cache, mock_get_cache, mock_sleep, mock_get, mock_env_api_key
):
    """
    Tests that movie search results are cached.
    """
    # Simulate cache miss on the first call
    mock_get_cache.return_value = None
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"id": 1, "title": "Dune"}]}
    mock_get.return_value = mock_response

    # First call should hit the API and set the cache
    search_movie("Dune", 2021)
    mock_get.assert_called_once()
    mock_set_cache.assert_called_once()

    # Simulate cache hit on the second call
    mock_get.reset_mock()
    mock_set_cache.reset_mock()
    mock_get_cache.return_value = [{"id": 1, "title": "Dune"}]

    # Second call should not hit the API
    search_movie("Dune", 2021)
    mock_get.assert_not_called()
    mock_set_cache.assert_not_called()
