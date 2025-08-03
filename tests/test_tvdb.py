from mpv_scraper.utils import normalize_rating
from mpv_scraper.tvdb import get_series_extended
from unittest.mock import patch


@patch("mpv_scraper.tvdb._get_from_cache", return_value=None)
@patch("mpv_scraper.tvdb._set_to_cache")
@patch("mpv_scraper.tvdb.requests.get")
@patch("mpv_scraper.tvdb.authenticate_tvdb", return_value="token")
def test_rating_normalization(mock_auth, mock_get, _set_cache, _get_cache, monkeypatch):
    monkeypatch.setenv("TVDB_API_KEY", "dummy")

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"data": {"siteRating": 6.7}}

    record = get_series_extended(42, "token")
    assert record["siteRating"] == normalize_rating(6.7)


@patch("mpv_scraper.tvdb._get_from_cache", return_value=None)
@patch("mpv_scraper.tvdb._set_to_cache")
@patch("mpv_scraper.tvdb.requests.get")
@patch("mpv_scraper.tvdb.authenticate_tvdb", return_value="token")
def test_episode_description_fallback(
    mock_auth, mock_get, _set_cache, _get_cache, monkeypatch
):
    """Ensure episodes missing an overview fall back to the synopsis/shortDescription."""
    monkeypatch.setenv("TVDB_API_KEY", "dummy")

    mock_get.return_value.status_code = 200
    # Mock series, artwork, and episodes calls with v3 API structure
    mock_get.return_value.json.side_effect = [
        {"data": {"id": 99, "seriesName": "Test Show", "siteRating": 5.0}},
        {"data": [{"keyType": "poster", "fileName": "/poster.jpg"}]},
        {
            "data": [
                {
                    "id": 1,
                    "airedSeason": 1,
                    "airedEpisodeNumber": 1,
                    "overview": None,  # Explicitly None to test fallback
                    "synopsis": "A short synopsis.",
                }
            ]
        },
    ]

    record = get_series_extended(99, "token")
    assert record["episodes"][0]["overview"] == "A short synopsis."
