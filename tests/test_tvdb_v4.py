"""Test TVDB API V4 client functionality.

Tests verify that the client correctly uses TVDB API V4 endpoints,
handles V4 response formats, and supports both TVDB_API_KEY2 and
fallback to TVDB_API_KEY for backward compatibility.
"""

import pytest
from unittest.mock import Mock, patch
from mpv_scraper.tvdb import (
    authenticate_tvdb,
    search_show,
    get_series_extended,
    disambiguate_show,
    _set_to_cache,
)
from mpv_scraper.utils import normalize_rating


class TestTVDBV4Authentication:
    """Test TVDB V4 API authentication."""

    def test_authenticate_tvdb_v4_with_key2(self):
        """Test authentication using TVDB_API_KEY2 (V4 API key)."""
        # Clear cache
        _set_to_cache("tvdb_token_v4", None)

        with patch("os.getenv") as mock_getenv:
            # Mock TVDB_API_KEY2 being set
            mock_getenv.side_effect = lambda key: (
                "test_v4_api_key" if key == "TVDB_API_KEY2" else None
            )

            with patch("requests.post") as mock_post:
                mock_response = Mock()
                # V4 API returns {"data": {"token": "..."}}
                mock_response.json.return_value = {"data": {"token": "v4_bearer_token"}}
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response

                result = authenticate_tvdb()

                assert result == "v4_bearer_token"
                # Verify V4 endpoint was called
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[0][0] == "https://api4.thetvdb.com/v4/login"
                assert call_args[1]["json"]["apikey"] == "test_v4_api_key"
                assert "pin" not in call_args[1]["json"]

    def test_authenticate_tvdb_v4_with_pin(self):
        """Test authentication with PIN for user-supported keys."""
        _set_to_cache("tvdb_token_v4", None)

        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key: {
                "TVDB_API_KEY2": "test_v4_api_key",
                "TVDB_PIN": "1234",
            }.get(key)

            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {"data": {"token": "v4_bearer_token"}}
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response

                result = authenticate_tvdb()

                assert result == "v4_bearer_token"
                call_args = mock_post.call_args
                assert call_args[1]["json"]["apikey"] == "test_v4_api_key"
                assert call_args[1]["json"]["pin"] == "1234"

    def test_authenticate_tvdb_v4_fallback_to_key1(self):
        """Test fallback to TVDB_API_KEY when TVDB_API_KEY2 is not set."""
        _set_to_cache("tvdb_token_v4", None)

        with patch("os.getenv") as mock_getenv:
            # TVDB_API_KEY2 not set, but TVDB_API_KEY is
            mock_getenv.side_effect = lambda key: (
                "test_v3_api_key" if key == "TVDB_API_KEY" else None
            )

            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {"data": {"token": "v4_bearer_token"}}
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response

                result = authenticate_tvdb()

                assert result == "v4_bearer_token"
                call_args = mock_post.call_args
                assert call_args[1]["json"]["apikey"] == "test_v3_api_key"

    def test_authenticate_tvdb_v4_no_api_key(self):
        """Test authentication fails when no API key is set."""
        _set_to_cache("tvdb_token_v4", None)

        with patch("os.getenv", return_value=None):
            with pytest.raises(
                ValueError,
                match="TVDB_API_KEY2 or TVDB_API_KEY environment variable not set",
            ):
                authenticate_tvdb()

    def test_authenticate_tvdb_v4_token_caching(self):
        """Test that V4 tokens are cached separately from V3 tokens."""
        # Set a cached V4 token
        _set_to_cache("tvdb_token_v4", {"token": "cached_v4_token"})

        with patch("os.getenv", return_value="test_key"):
            with patch("requests.post") as mock_post:
                result = authenticate_tvdb()

                # Should return cached token without making API call
                assert result == "cached_v4_token"
                mock_post.assert_not_called()

    def test_authenticate_tvdb_v4_alternative_response_format(self):
        """Test handling of alternative V4 response format (token at root)."""
        _set_to_cache("tvdb_token_v4", None)

        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key: (
                "test_key" if key == "TVDB_API_KEY2" else None
            )

            with patch("requests.post") as mock_post:
                mock_response = Mock()
                # Some V4 responses might return token at root level
                mock_response.json.return_value = {"token": "root_level_token"}
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response

                result = authenticate_tvdb()

                assert result == "root_level_token"


class TestTVDBV4Search:
    """Test TVDB V4 API search functionality."""

    def test_search_show_v4_format(self):
        """Test search_show with V4 API response format."""
        _set_to_cache("search_test_show", None)

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            # V4 API search response format
            mock_response.json.return_value = {
                "data": [{"id": 1, "name": "Test Show", "firstAired": "2020-01-01"}]
            }
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = search_show("Test Show", "test_token")

            assert len(results) == 1
            assert results[0]["id"] == 1
            assert results[0]["name"] == "Test Show"
            # Verify V4 endpoint was called
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "api4.thetvdb.com/v4/search" in call_args[0][0]
            assert call_args[1]["params"]["query"] == "Test Show"
            assert call_args[1]["params"]["type"] == "series"

    def test_search_show_v4_nested_results(self):
        """Test search_show with nested V4 response format."""
        _set_to_cache("search_test_show_nested", None)

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            # V4 API might return nested results structure
            mock_response.json.return_value = {
                "data": {"results": [{"id": 1, "name": "Test Show", "year": "2020"}]}
            }
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = search_show("Test Show", "test_token")

            assert len(results) == 1
            assert results[0]["id"] == 1

    def test_search_show_v4_empty_results(self):
        """Test search_show with empty V4 response."""
        _set_to_cache("search_empty", None)

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"data": []}
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = search_show("Nonexistent Show", "test_token")

            assert results == []

    def test_search_show_v4_cache_hit(self):
        """Test search_show uses cache on second call."""
        # Set cache
        _set_to_cache("search_cached_show", [{"id": 1, "name": "Cached Show"}])

        with patch("requests.get") as mock_get:
            results = search_show("Cached Show", "test_token")

            assert len(results) == 1
            # Should not make API call
            mock_get.assert_not_called()


class TestTVDBV4SeriesExtended:
    """Test TVDB V4 API series extended information retrieval."""

    def test_get_series_extended_v4_format(self):
        """Test get_series_extended with V4 API response format."""
        _set_to_cache("series_1_extended", None)

        with patch("requests.get") as mock_get:
            # Mock series response
            mock_series_response = Mock()
            mock_series_response.json.return_value = {
                "data": {
                    "id": 1,
                    "name": "Test Show",
                    "overview": "A test show",
                    "firstAired": "2020-01-01",
                    "score": 8.5,
                }
            }
            mock_series_response.status_code = 200
            mock_series_response.raise_for_status = Mock()

            # Mock episodes response
            mock_episodes_response = Mock()
            mock_episodes_response.json.return_value = {
                "data": [
                    {
                        "id": 101,
                        "seasonNumber": 1,
                        "number": 1,
                        "name": "Pilot",
                        "overview": "The pilot episode",
                        "firstAired": "2020-01-01",
                    }
                ]
            }
            mock_episodes_response.status_code = 200
            mock_episodes_response.raise_for_status = Mock()

            # Mock artwork response (404 - no artwork)
            mock_artwork_response = Mock()
            mock_artwork_response.status_code = 404

            mock_get.side_effect = [
                mock_series_response,
                mock_episodes_response,
                mock_artwork_response,
            ]

            result = get_series_extended(1, "test_token")

            assert result is not None
            assert result["id"] == 1
            assert result["name"] == "Test Show"
            assert result["overview"] == "A test show"
            assert len(result["episodes"]) == 1
            assert result["episodes"][0]["seasonNumber"] == 1
            assert result["episodes"][0]["number"] == 1
            assert result["episodes"][0]["episodeName"] == "Pilot"

            # Verify V4 endpoints were called
            assert mock_get.call_count >= 2
            series_call = mock_get.call_args_list[0]
            assert "api4.thetvdb.com/v4/series/1" in series_call[0][0]

    def test_get_series_extended_v4_episodes_alternative_endpoint(self):
        """Test get_series_extended falls back to alternative episodes endpoint."""
        _set_to_cache("series_2_extended", None)

        with patch("requests.get") as mock_get:
            # Mock series response
            mock_series_response = Mock()
            mock_series_response.json.return_value = {
                "data": {"id": 2, "name": "Test Show 2"}
            }
            mock_series_response.status_code = 200
            mock_series_response.raise_for_status = Mock()

            # Mock episodes endpoint returning 404, then alternative endpoint
            mock_episodes_404 = Mock()
            mock_episodes_404.status_code = 404

            mock_episodes_alt = Mock()
            mock_episodes_alt.json.return_value = {
                "data": [
                    {
                        "id": 201,
                        "seasonNumber": 1,
                        "number": 1,
                        "name": "Episode 1",
                    }
                ]
            }
            mock_episodes_alt.status_code = 200
            mock_episodes_alt.raise_for_status = Mock()

            mock_artwork_response = Mock()
            mock_artwork_response.status_code = 404

            mock_get.side_effect = [
                mock_series_response,
                mock_episodes_404,
                mock_episodes_alt,
                mock_artwork_response,
            ]

            result = get_series_extended(2, "test_token")

            assert result is not None
            assert len(result["episodes"]) == 1

    def test_get_series_extended_v4_field_name_variations(self):
        """Test get_series_extended handles V4 field name variations."""
        _set_to_cache("series_3_extended", None)

        with patch("requests.get") as mock_get:
            # Mock series with V4 field names
            mock_series_response = Mock()
            mock_series_response.json.return_value = {
                "data": {
                    "id": 3,
                    "name": "Test Show 3",  # V4 uses "name" not "seriesName"
                    "description": "A description",  # V4 might use "description"
                    "firstAirTime": "2020",  # Alternative date field
                }
            }
            mock_series_response.status_code = 200
            mock_series_response.raise_for_status = Mock()

            # Mock episodes with V4 field names
            mock_episodes_response = Mock()
            mock_episodes_response.json.return_value = {
                "data": [
                    {
                        "id": 301,
                        "season": 1,  # Alternative field name
                        "episode": 1,  # Alternative field name
                        "name": "Episode 1",
                        "description": "Episode description",
                        "aired": "2020-01-01",  # Alternative date field
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

            result = get_series_extended(3, "test_token")

            assert result is not None
            assert result["name"] == "Test Show 3"
            assert len(result["episodes"]) == 1
            # Should handle field name variations
            assert result["episodes"][0]["seasonNumber"] == 1
            assert result["episodes"][0]["number"] == 1

    def test_get_series_extended_v4_artwork(self):
        """Test get_series_extended retrieves artwork from V4 API."""
        _set_to_cache("series_4_extended", None)

        with patch("requests.get") as mock_get:
            mock_series_response = Mock()
            mock_series_response.json.return_value = {
                "data": {
                    "id": 4,
                    "name": "Test Show 4",
                    "image": "https://example.com/poster.jpg",  # V4 might return full URL
                }
            }
            mock_series_response.status_code = 200
            mock_series_response.raise_for_status = Mock()

            mock_episodes_response = Mock()
            mock_episodes_response.json.return_value = {"data": []}
            mock_episodes_response.status_code = 200
            mock_episodes_response.raise_for_status = Mock()

            # Mock artwork response
            mock_artwork_response = Mock()
            mock_artwork_response.json.return_value = {
                "data": [
                    {
                        "image": "https://example.com/logo.png",
                        "fileName": "logo.png",
                    }
                ]
            }
            mock_artwork_response.status_code = 200
            mock_artwork_response.raise_for_status = Mock()

            mock_get.side_effect = [
                mock_series_response,
                mock_episodes_response,
                mock_artwork_response,
            ]

            result = get_series_extended(4, "test_token")

            assert result is not None
            assert result["image"] == "https://example.com/poster.jpg"
            # Verify artwork endpoint was called
            artwork_call = mock_get.call_args_list[2]
            assert "api4.thetvdb.com/v4/series/4/artworks" in artwork_call[0][0]

    def test_get_series_extended_v4_rating_normalization(self):
        """Test that ratings are normalized correctly from V4 API."""
        _set_to_cache("series_5_extended", None)

        with patch("requests.get") as mock_get:
            mock_series_response = Mock()
            mock_series_response.json.return_value = {
                "data": {
                    "id": 5,
                    "name": "Test Show 5",
                    "score": 7.5,  # V4 might use "score" instead of "siteRating"
                }
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

            result = get_series_extended(5, "test_token")

            assert result is not None
            # Rating should be normalized (0-10 -> 0-1)
            assert result["siteRating"] == normalize_rating(7.5)

    def test_get_series_extended_v4_not_found(self):
        """Test get_series_extended returns None for 404 responses."""
        _set_to_cache("series_999_extended", None)

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = get_series_extended(999, "test_token")

            assert result is None


class TestTVDBV4Disambiguation:
    """Test TVDB V4 API disambiguation functionality."""

    def test_disambiguate_show_v4_format(self):
        """Test disambiguate_show handles V4 search result format."""
        results = [
            {"id": 1, "name": "Test Show", "firstAired": "2020-01-01"},
            {"id": 2, "name": "Test Show", "firstAired": "2021-01-01"},
        ]

        with patch("click.echo") as mock_echo, patch("click.prompt", return_value=1):
            result = disambiguate_show(results)

            assert result == results[0]
            # Should display both options
            assert mock_echo.call_count >= 2

    def test_disambiguate_show_v4_year_extraction(self):
        """Test disambiguate_show extracts year from date strings."""
        results = [
            {"id": 1, "name": "Test Show", "firstAired": "2020-01-15"},
        ]

        with patch("click.echo"), patch("click.prompt", return_value=1):
            result = disambiguate_show(results)

            assert result == results[0]


class TestTVDBV4Integration:
    """Integration tests for TVDB V4 API workflow."""

    def test_full_workflow_v4(self):
        """Test complete workflow: authenticate -> search -> get extended."""
        # Clear all caches
        _set_to_cache("tvdb_token_v4", None)
        _set_to_cache("search_test_show", None)
        _set_to_cache("series_1_extended", None)

        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key: (
                "test_v4_key" if key == "TVDB_API_KEY2" else None
            )

            with patch("requests.post") as mock_post:
                # Mock authentication
                mock_auth_response = Mock()
                mock_auth_response.json.return_value = {"data": {"token": "v4_token"}}
                mock_auth_response.raise_for_status = Mock()
                mock_post.return_value = mock_auth_response

                token = authenticate_tvdb()
                assert token == "v4_token"

            with patch("requests.get") as mock_get:
                # Mock search
                mock_search_response = Mock()
                mock_search_response.json.return_value = {
                    "data": [{"id": 1, "name": "Test Show"}]
                }
                mock_search_response.status_code = 200
                mock_search_response.raise_for_status = Mock()

                # Mock series extended
                mock_series_response = Mock()
                mock_series_response.json.return_value = {
                    "data": {"id": 1, "name": "Test Show"}
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
                    mock_search_response,
                    mock_series_response,
                    mock_episodes_response,
                    mock_artwork_response,
                ]

                search_results = search_show("Test Show", token)
                assert len(search_results) == 1

                series_info = get_series_extended(search_results[0]["id"], token)
                assert series_info is not None
                assert series_info["id"] == 1


class TestTVDBV4EpisodeArtwork:
    """Test TVDB V4 API episode artwork fetching."""

    def test_fetch_episode_artwork_screencap_preference(self):
        """Test that fetch_episode_artwork prefers screencap type over thumbnail."""
        from mpv_scraper.tvdb import fetch_episode_artwork

        with patch("requests.get") as mock_get, patch("time.sleep"):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "type": "thumbnail",
                        "image": "thumbnail.jpg",
                    },
                    {
                        "type": "screencap",
                        "image": "screencap.jpg",
                    },
                ]
            }
            mock_get.return_value = mock_response

            result = fetch_episode_artwork(12345, "test_token")

            # Should prefer screencap over thumbnail
            assert result is not None
            assert "screencap.jpg" in result
            assert "thumbnail.jpg" not in result

    def test_fetch_episode_artwork_fallback_to_thumbnail(self):
        """Test that fetch_episode_artwork falls back to thumbnail if no screencap."""
        from mpv_scraper.tvdb import fetch_episode_artwork

        with patch("requests.get") as mock_get, patch("time.sleep"):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "type": "thumbnail",
                        "image": "thumbnail.jpg",
                    }
                ]
            }
            mock_get.return_value = mock_response

            result = fetch_episode_artwork(12345, "test_token")

            # Should fall back to thumbnail
            assert result is not None
            assert "thumbnail.jpg" in result

    def test_fetch_episode_artwork_handles_v4_urls(self):
        """Test that fetch_episode_artwork handles TVDB V4 URL formats."""
        from mpv_scraper.tvdb import fetch_episode_artwork

        with patch("requests.get") as mock_get, patch("time.sleep"):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "type": "screencap",
                        "image": "v4/episode/12345/screencap/abc123.jpg",
                    }
                ]
            }
            mock_get.return_value = mock_response

            result = fetch_episode_artwork(12345, "test_token")

            # Should build full URL correctly
            assert result is not None
            assert "artworks.thetvdb.com" in result
            assert "v4/episode" in result

    def test_fetch_episode_artwork_handles_full_urls(self):
        """Test that fetch_episode_artwork handles already-full URLs."""
        from mpv_scraper.tvdb import fetch_episode_artwork

        with patch("requests.get") as mock_get, patch("time.sleep"):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "type": "screencap",
                        "image": "https://artworks.thetvdb.com/banners/v4/episode/12345/screencap.jpg",
                    }
                ]
            }
            mock_get.return_value = mock_response

            result = fetch_episode_artwork(12345, "test_token")

            # Should return full URL as-is
            assert result is not None
            assert result.startswith("https://")

    def test_fetch_episode_artwork_rate_limited(self):
        """Test that fetch_episode_artwork handles 429 rate limit errors."""
        from mpv_scraper.tvdb import fetch_episode_artwork

        with patch("requests.get") as mock_get, patch("time.sleep"):
            mock_response = Mock()
            mock_response.status_code = 429
            mock_get.return_value = mock_response

            result = fetch_episode_artwork(12345, "test_token")

            # Should return None on rate limit
            assert result is None

    def test_fetch_episode_artwork_checks_multiple_fields(self):
        """Test that fetch_episode_artwork checks image, fileName, and url fields."""
        from mpv_scraper.tvdb import fetch_episode_artwork

        with patch("requests.get") as mock_get, patch("time.sleep"):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "type": "screencap",
                        # No 'image' field, but has 'fileName'
                        "fileName": "screencap.jpg",
                    }
                ]
            }
            mock_get.return_value = mock_response

            result = fetch_episode_artwork(12345, "test_token")

            # Should use fileName field
            assert result is not None
            assert "screencap.jpg" in result
