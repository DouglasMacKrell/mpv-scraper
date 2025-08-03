from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _set_keys(monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "dummy")
    monkeypatch.setenv("TVDB_API_KEY", "dummy")


@patch("mpv_scraper.tmdb.requests.get")
@patch("mpv_scraper.tmdb._set_to_cache")
@patch("mpv_scraper.tmdb._get_from_cache")
def test_tmdb_cache(mock_get_cache, _set_cache, mock_http):
    """Second call to get_movie_details should hit cache and skip HTTP."""
    from mpv_scraper.tmdb import get_movie_details

    # First call: no cache; Second call: cached dict returned
    mock_get_cache.side_effect = [None, {"vote_average": 7.5}]

    mock_http.return_value.status_code = 200
    mock_http.return_value.json.return_value = {"vote_average": 7.5}

    get_movie_details(123)
    get_movie_details(123)

    # HTTP GET only once due to cache
    mock_http.assert_called_once()


@patch("mpv_scraper.tvdb.requests.get")
@patch("mpv_scraper.tvdb._set_to_cache")
@patch("mpv_scraper.tvdb._get_from_cache")
@patch("mpv_scraper.tvdb.authenticate_tvdb", return_value="token")
def test_tvdb_cache(_auth, mock_get_cache, _set_cache, mock_http):
    """Second call to get_series_extended should use cache."""
    from mpv_scraper.tvdb import get_series_extended

    mock_get_cache.side_effect = [None, {"siteRating": 5.0}]
    mock_http.return_value.status_code = 200
    # Mock v3 API structure with artwork endpoint
    mock_http.return_value.json.side_effect = [
        {"data": {"id": 42, "seriesName": "Test Show", "siteRating": 5.0}},
        {"data": []},  # artwork
        {"data": []},  # episodes
    ]

    get_series_extended(42, "token")

    # Should be called three times: series, artwork, episodes
    assert mock_http.call_count == 3
