from unittest.mock import patch


@patch("mpv_scraper.omdb.requests.get")
@patch("mpv_scraper.omdb._set_to_cache")
@patch("mpv_scraper.omdb._get_from_cache")
def test_search_movie(mock_get_cache, _set_cache, mock_http, monkeypatch):
    from mpv_scraper.omdb import search_movie

    # Ensure env has a key without exposing value
    monkeypatch.setenv("OMDB_API_KEY", "dummy-key")

    mock_get_cache.return_value = None
    mock_http.return_value.status_code = 200
    mock_http.return_value.json.return_value = {
        "Search": [
            {
                "Title": "Sample Movie",
                "Year": "1999",
                "imdbID": "tt1234567",
                "Type": "movie",
                "Poster": "http://img/poster.jpg",
            }
        ]
    }

    results = search_movie("Sample Movie", 1999)
    assert isinstance(results, list)
    assert results[0]["id"] == "tt1234567"
    assert results[0]["title"] == "Sample Movie"
    assert results[0]["year"] == 1999


@patch("mpv_scraper.omdb.requests.get")
@patch("mpv_scraper.omdb._set_to_cache")
@patch("mpv_scraper.omdb._get_from_cache")
def test_get_movie_details(mock_get_cache, _set_cache, mock_http, monkeypatch):
    from mpv_scraper.omdb import get_movie_details

    monkeypatch.setenv("OMDB_API_KEY", "dummy-key")

    mock_get_cache.return_value = None
    mock_http.return_value.status_code = 200
    mock_http.return_value.json.return_value = {
        "Title": "Sample Movie",
        "Year": "1999",
        "imdbID": "tt1234567",
        "Type": "movie",
        "Poster": "http://img/poster.jpg",
        "Plot": "Test movie description.",
        "imdbRating": "7.5",
        "Released": "1999-07-09",
    }

    details = get_movie_details("tt1234567")
    assert details["title"] == "Sample Movie"
    assert details["overview"] == "Test movie description."
    assert 0.0 <= details["vote_average"] <= 1.0
    assert details["poster_url"].endswith("poster.jpg")
    assert details["release_date"] == "1999-07-09"
