from mpv_scraper.utils import normalize_rating
from mpv_scraper.tvdb import get_series_extended
from unittest.mock import patch, Mock


@patch("mpv_scraper.tvdb._get_from_cache", return_value=None)
@patch("mpv_scraper.tvdb._set_to_cache")
@patch("mpv_scraper.tvdb.requests.get")
@patch("mpv_scraper.tvdb.authenticate_tvdb", return_value="token")
def test_rating_normalization(mock_auth, mock_get, _set_cache, _get_cache, monkeypatch):
    """Test rating normalization with V4 API response format."""
    monkeypatch.setenv("TVDB_API_KEY2", "dummy")

    # Mock V4 API responses: series, episodes, artwork
    mock_series_response = Mock()
    mock_series_response.json.return_value = {
        "data": {"id": 42, "name": "Test Show", "score": 6.7}
    }
    mock_series_response.status_code = 200
    mock_series_response.raise_for_status = Mock()

    mock_episodes_response = Mock()
    mock_episodes_response.json.return_value = {"data": []}
    mock_episodes_response.status_code = 200
    mock_episodes_response.raise_for_status = Mock()

    mock_artwork_response = Mock()
    mock_artwork_response.status_code = 404

    mock_get.side_effect = [
        mock_series_response,
        mock_episodes_response,
        mock_artwork_response,
    ]

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
    monkeypatch.setenv("TVDB_API_KEY2", "dummy")

    # Mock V4 API responses: series, episodes, artwork
    mock_series_response = Mock()
    mock_series_response.json.return_value = {
        "data": {"id": 99, "name": "Test Show", "score": 5.0}
    }
    mock_series_response.status_code = 200
    mock_series_response.raise_for_status = Mock()

    mock_episodes_response = Mock()
    mock_episodes_response.json.return_value = {
        "data": [
            {
                "id": 1,
                "seasonNumber": 1,  # V4 field name
                "number": 1,  # V4 field name
                "overview": None,  # Explicitly None to test fallback
                "synopsis": "A short synopsis.",
            }
        ]
    }
    mock_episodes_response.status_code = 200
    mock_episodes_response.raise_for_status = Mock()

    mock_artwork_response = Mock()
    mock_artwork_response.status_code = 404

    mock_get.side_effect = [
        mock_series_response,
        mock_episodes_response,
        mock_artwork_response,
    ]

    record = get_series_extended(99, "token")
    assert record["episodes"][0]["overview"] == "A short synopsis."
