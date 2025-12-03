"""Test fallback provider coverage for Sprint 18.8."""

from unittest.mock import Mock, patch
from pathlib import Path

from mpv_scraper.fallback import FallbackScraper


class TestFallbackScraperCoverage:
    """Test FallbackScraper functionality to improve coverage."""

    def test_fallback_scraper_initialization(self):
        """Test FallbackScraper initialization."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key: {
                "TMDB_API_KEY": "test_tmdb_key",
                "OMDB_API_KEY": "test_omdb_key",
                "FANARTTV_API_KEY": "test_fanarttv_key",
                "ANIDB_API_KEY": "test_anidb_key",
            }.get(key)

            scraper = FallbackScraper()

            assert scraper.tvdb_token is None
            assert scraper.api_keys["tmdb"] == "test_tmdb_key"
            assert scraper.api_keys["omdb"] == "test_omdb_key"
            assert scraper.api_keys["fanarttv"] == "test_fanarttv_key"
            assert scraper.api_keys["anidb"] == "test_anidb_key"

    def test_get_tvdb_token_caching(self):
        """Test TVDB token caching functionality."""
        scraper = FallbackScraper()

        with patch("mpv_scraper.fallback.authenticate_tvdb") as mock_auth:
            mock_auth.return_value = "test_token"

            # First call should authenticate
            token1 = scraper._get_tvdb_token()
            assert token1 == "test_token"
            assert scraper.tvdb_token == "test_token"
            mock_auth.assert_called_once()

            # Second call should use cached token
            token2 = scraper._get_tvdb_token()
            assert token2 == "test_token"
            # Should not call authenticate again
            mock_auth.assert_called_once()

    def test_is_poor_data_tvdb_good(self):
        """Test _is_poor_data with good TVDB data."""
        scraper = FallbackScraper()

        good_record = {
            "image": "poster.jpg",
            "artworks": {"clearLogo": "logo.png"},
            "episodes": [{"id": 1, "name": "Pilot"}],
            "overview": "A great show",
        }

        assert not scraper._is_poor_data(good_record, "tvdb")

    def test_is_poor_data_tvdb_poor(self):
        """Test _is_poor_data with poor TVDB data."""
        scraper = FallbackScraper()

        poor_record = {
            "image": None,
            "artworks": {},
            "episodes": [],
            "overview": "",
        }

        assert scraper._is_poor_data(poor_record, "tvdb")

    def test_is_poor_data_tmdb_good(self):
        """Test _is_poor_data with good TMDB data."""
        scraper = FallbackScraper()

        good_record = {
            "poster_url": "poster.jpg",
            "logo_url": "logo.png",
            "overview": "A great movie",
        }

        assert not scraper._is_poor_data(good_record, "tmdb")

    def test_is_poor_data_tmdb_poor(self):
        """Test _is_poor_data with poor TMDB data."""
        scraper = FallbackScraper()

        poor_record = {
            "poster_url": None,
            "logo_url": None,
            "overview": "",
        }

        assert scraper._is_poor_data(poor_record, "tmdb")

    def test_is_poor_data_empty_record(self):
        """Test _is_poor_data with empty record."""
        scraper = FallbackScraper()

        assert scraper._is_poor_data(None, "tvdb")
        assert scraper._is_poor_data({}, "tmdb")

    def test_is_poor_data_unknown_source(self):
        """Test _is_poor_data with unknown source."""
        scraper = FallbackScraper()

        record = {"some": "data"}
        assert not scraper._is_poor_data(record, "unknown")

    def test_try_tmdb_for_tv_show_success(self):
        """Test successful TMDB fallback for TV show."""
        scraper = FallbackScraper()
        scraper.api_keys["tmdb"] = "test_key"

        mock_search_response = {"results": [{"id": 123, "name": "Test Show"}]}

        mock_details_response = {
            "id": 123,
            "name": "Test Show",
            "overview": "A test show",
            "vote_average": 8.5,
            "genres": [{"name": "Drama"}],
            "networks": [{"name": "Test Network"}],
            "production_companies": [{"name": "Test Studio"}],
            "first_air_date": "2020-01-01",
        }

        mock_images_response = {
            "posters": [
                {"file_path": "/poster.jpg", "iso_3166_1": "US", "iso_639_1": "en"}
            ],
            "logos": [
                {"file_path": "/logo.png", "iso_3166_1": "US", "iso_639_1": "en"}
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                Mock(json=lambda: mock_search_response),
                Mock(json=lambda: mock_details_response),
                Mock(json=lambda: mock_images_response),
            ]

            result = scraper._try_tmdb_for_tv_show("Test Show", 2020)

            assert result is not None
            assert result["name"] == "Test Show"
            assert result["overview"] == "A test show"
            assert result["image"] == "https://image.tmdb.org/t/p/original/poster.jpg"
            assert (
                result["artworks"]["clearLogo"]
                == "https://image.tmdb.org/t/p/original/logo.png"
            )
            assert result["source"] == "tmdb_fallback"

    def test_try_tmdb_for_tv_show_no_results(self):
        """Test TMDB fallback with no search results."""
        scraper = FallbackScraper()
        scraper.api_keys["tmdb"] = "test_key"

        mock_search_response = {"results": []}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(json=lambda: mock_search_response)

            result = scraper._try_tmdb_for_tv_show("Nonexistent Show")

            assert result is None

    def test_try_tmdb_for_tv_show_exception(self):
        """Test TMDB fallback with exception handling."""
        scraper = FallbackScraper()
        scraper.api_keys["tmdb"] = "test_key"

        with patch("requests.get", side_effect=Exception("Network error")):
            with patch("builtins.print") as mock_print:
                result = scraper._try_tmdb_for_tv_show("Test Show")

                assert result is None
                mock_print.assert_called_once()

    def test_try_fanarttv_for_tv_show_no_key(self):
        """Test FanartTV fallback with no API key."""
        scraper = FallbackScraper()
        scraper.api_keys["fanarttv"] = None

        result = scraper._try_fanarttv_for_tv_show("Test Show")

        assert result is None

    def test_try_fanarttv_for_tv_show_exception(self):
        """Test FanartTV fallback with exception handling."""
        scraper = FallbackScraper()
        scraper.api_keys["fanarttv"] = "test_key"

        with patch("requests.get", side_effect=Exception("Network error")):
            result = scraper._try_fanarttv_for_tv_show("Test Show")

            assert result is None

    def test_scrape_tv_with_fallback_tvdb_success(self):
        """Test TV scraping with successful TVDB primary."""
        scraper = FallbackScraper()

        mock_results = [{"id": 123, "seriesName": "Test Show"}]
        mock_record = {
            "id": 123,
            "name": "Test Show",
            "image": "poster.jpg",
            "artworks": {"clearLogo": "logo.png"},
            "episodes": [{"id": 1, "name": "Pilot"}],
            "overview": "A great show",
        }

        with patch("mpv_scraper.fallback.authenticate_tvdb") as mock_auth:
            with patch("mpv_scraper.fallback.search_show") as mock_search:
                with patch("mpv_scraper.fallback.get_series_extended") as mock_extended:
                    mock_auth.return_value = "test_token"
                    mock_search.return_value = mock_results
                    mock_extended.return_value = mock_record

                    with patch("builtins.print") as mock_print:
                        result = scraper.scrape_tv_with_fallback(Path("Test Show"))

                        assert result == mock_record
                        mock_print.assert_called_with(
                            "✓ TVDB has good data for Test Show"
                        )

    def test_scrape_tv_with_fallback_tvdb_poor_data(self):
        """Test TV scraping with poor TVDB data, falling back to TMDB."""
        scraper = FallbackScraper()
        scraper.api_keys["tmdb"] = "test_key"

        mock_results = [{"id": 123, "seriesName": "Test Show"}]
        poor_record = {
            "id": 123,
            "name": "Test Show",
            "image": None,  # Poor data
            "artworks": {},
            "episodes": [],
            "overview": "",
        }

        mock_tmdb_record = {
            "id": 123,
            "name": "Test Show",
            "image": "tmdb_poster.jpg",
            "artworks": {"clearLogo": "tmdb_logo.png"},
            "episodes": [],
            "overview": "TMDB overview",
            "source": "tmdb_fallback",
        }

        with patch("mpv_scraper.fallback.authenticate_tvdb") as mock_auth:
            with patch("mpv_scraper.fallback.search_show") as mock_search:
                with patch("mpv_scraper.fallback.get_series_extended") as mock_extended:
                    with patch.object(scraper, "_try_tmdb_for_tv_show") as mock_tmdb:
                        mock_auth.return_value = "test_token"
                        mock_search.return_value = mock_results
                        mock_extended.return_value = poor_record
                        mock_tmdb.return_value = mock_tmdb_record

                        with patch("builtins.print") as mock_print:
                            result = scraper.scrape_tv_with_fallback(Path("Test Show"))

                            assert result == mock_tmdb_record
                            mock_print.assert_any_call(
                                "⚠ TVDB has poor data for Test Show, trying fallbacks..."
                            )
                            mock_print.assert_any_call(
                                "⚠ Using best available data for Test Show (may be incomplete)"
                            )

    def test_scrape_tv_with_fallback_no_good_data(self):
        """Test TV scraping with no good data from any provider."""
        scraper = FallbackScraper()
        scraper.api_keys["tmdb"] = "test_key"

        with patch("mpv_scraper.fallback.authenticate_tvdb") as mock_auth:
            with patch("mpv_scraper.fallback.search_show") as mock_search:
                with patch.object(scraper, "_try_tmdb_for_tv_show") as mock_tmdb:
                    with patch.object(
                        scraper, "_try_fanarttv_for_tv_show"
                    ) as mock_fanart:
                        mock_auth.return_value = "test_token"
                        mock_search.return_value = []
                        mock_tmdb.return_value = None
                        mock_fanart.return_value = None

                        with patch("builtins.print") as mock_print:
                            result = scraper.scrape_tv_with_fallback(Path("Test Show"))

                            assert result is None
                            mock_print.assert_any_call(
                                "❌ No good data found for Test Show from any API"
                            )

    def test_scrape_movie_with_fallback_tmdb_success(self):
        """Test movie scraping with successful TMDB primary."""
        scraper = FallbackScraper()

        mock_movie_meta = Mock()
        mock_movie_meta.title = "Test Movie"
        mock_movie_meta.year = 2020

        mock_results = [{"id": 123, "title": "Test Movie"}]
        mock_record = {
            "id": 123,
            "title": "Test Movie",
            "poster_url": "poster.jpg",
            "logo_url": "logo.png",
            "overview": "A great movie",
        }

        with patch("mpv_scraper.parser.parse_movie_filename") as mock_parse:
            with patch("mpv_scraper.fallback.search_movie") as mock_search:
                with patch("mpv_scraper.fallback.get_movie_details") as mock_details:
                    mock_parse.return_value = mock_movie_meta
                    mock_search.return_value = mock_results
                    mock_details.return_value = mock_record

                    with patch("builtins.print") as mock_print:
                        result = scraper.scrape_movie_with_fallback(
                            Path("Test Movie (2020).mp4")
                        )

                        assert result == mock_record
                        mock_print.assert_called_with(
                            "✓ TMDB has good data for Test Movie"
                        )

    def test_scrape_movie_with_fallback_no_parse(self):
        """Test movie scraping with unparseable filename."""
        scraper = FallbackScraper()

        with patch("mpv_scraper.parser.parse_movie_filename") as mock_parse:
            mock_parse.return_value = None

            result = scraper.scrape_movie_with_fallback(Path("invalid_filename.mp4"))

            assert result is None
