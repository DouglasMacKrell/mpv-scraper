from mpv_scraper.utils import normalize_rating
from mpv_scraper.tmdb import get_movie_details
from unittest.mock import patch


@patch("mpv_scraper.tmdb._get_from_cache", return_value=None)
@patch("mpv_scraper.tmdb._set_to_cache")
@patch("mpv_scraper.tmdb.requests.get")
def test_rating_normalization(mock_get, _set_cache, _get_cache, monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "dummy")

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"vote_average": 8.2}

    details = get_movie_details(123)
    assert details["vote_average"] == normalize_rating(8.2)


@patch("mpv_scraper.tmdb._get_from_cache", return_value=None)
@patch("mpv_scraper.tmdb._set_to_cache")
@patch("mpv_scraper.tmdb.requests.get")
def test_movie_description_fallback(mock_get, _set_cache, _get_cache, monkeypatch):
    """Ensure movies without an overview fall back to the tagline text."""
    monkeypatch.setenv("TMDB_API_KEY", "dummy")

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "vote_average": 7.0,
        "overview": "",
        "tagline": "Greatness awaits",
    }

    details = get_movie_details(555)

    assert details["overview"] == "Greatness awaits"
