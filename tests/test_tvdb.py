import pytest
from unittest.mock import patch, MagicMock

from mpv_scraper.tvdb import (
    authenticate_tvdb,
    search_show,
    disambiguate_show,
    CACHE_DIR,
)


@pytest.fixture
def mock_env_api_key(monkeypatch):
    """Fixture to set the TVDB_API_KEY environment variable."""
    monkeypatch.setenv("TVDB_API_KEY", "test_api_key")


@pytest.fixture(autouse=True)
def clear_cache():
    """Fixture to clear the cache before and after each test."""
    if CACHE_DIR.exists():
        for item in CACHE_DIR.iterdir():
            item.unlink()
    yield
    if CACHE_DIR.exists():
        for item in CACHE_DIR.iterdir():
            item.unlink()


def test_authenticate_raises_on_missing_key(monkeypatch):
    """
    Tests that authenticate_tvdb raises a ValueError if the API key is not set.
    """
    monkeypatch.delenv("TVDB_API_KEY", raising=False)
    with pytest.raises(ValueError, match="TVDB_API_KEY environment variable not set."):
        authenticate_tvdb()


@patch("requests.post")
def test_authenticate_success(mock_post, mock_env_api_key):
    """
    Tests that authenticate_tvdb returns a token on successful authentication
    and caches it.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"token": "fake_jwt_token"}}
    mock_post.return_value = mock_response

    # First call should hit the API
    token = authenticate_tvdb()
    assert token == "fake_jwt_token"
    mock_post.assert_called_once_with(
        "https://api4.thetvdb.com/v4/login", json={"apikey": "test_api_key"}, timeout=10
    )

    # Second call should use the cache
    mock_post.reset_mock()
    token2 = authenticate_tvdb()
    assert token2 == "fake_jwt_token"
    mock_post.assert_not_called()


@patch("requests.get")
def test_search_show_returns_candidates(mock_get, mock_env_api_key):
    """
    Tests that search_show returns a list of candidate shows and caches the result.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"tvdb_id": "123", "name": "Show A"},
            {"tvdb_id": "456", "name": "Show B"},
        ]
    }
    mock_get.return_value = mock_response

    # First call should hit the API
    results = search_show("Test Show", "fake_token")
    assert len(results) == 2
    assert results[0]["name"] == "Show A"
    mock_get.assert_called_once()

    # Second call should use the cache
    mock_get.reset_mock()
    results2 = search_show("Test Show", "fake_token")
    assert len(results2) == 2
    assert results2[0]["name"] == "Show A"
    mock_get.assert_not_called()


@patch("click.prompt")
def test_disambiguate_show_returns_correct_choice(mock_prompt):
    """Tests that the user's choice is correctly returned."""
    mock_prompt.return_value = 2
    results = [
        {"tvdb_id": "123", "name": "Show A", "year": "2000"},
        {"tvdb_id": "456", "name": "Show B", "year": "2010"},
    ]
    chosen = disambiguate_show(results)
    assert chosen is not None
    assert chosen["tvdb_id"] == "456"


@patch("click.prompt")
def test_disambiguate_show_returns_none_on_cancel(mock_prompt):
    """Tests that None is returned when the user cancels."""
    mock_prompt.return_value = 0
    results = [
        {"tvdb_id": "123", "name": "Show A", "year": "2000"},
        {"tvdb_id": "456", "name": "Show B", "year": "2010"},
    ]
    chosen = disambiguate_show(results)
    assert chosen is None


def test_disambiguate_show_returns_single_result_automatically():
    """Tests that a single result is returned without a prompt."""
    results = [{"tvdb_id": "123", "name": "Show A", "year": "2000"}]
    chosen = disambiguate_show(results)
    assert chosen is not None
    assert chosen["tvdb_id"] == "123"


def test_disambiguate_show_returns_none_for_empty_list():
    """Tests that None is returned for an empty list of results."""
    chosen = disambiguate_show([])
    assert chosen is None
