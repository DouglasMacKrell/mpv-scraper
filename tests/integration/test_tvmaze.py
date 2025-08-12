from unittest.mock import patch


@patch("mpv_scraper.tvmaze.requests.get")
@patch("mpv_scraper.tvmaze._set_to_cache")
@patch("mpv_scraper.tvmaze._get_from_cache")
def test_search_show(mock_get_cache, _set_cache, mock_http):
    from mpv_scraper.tvmaze import search_show

    # No cache on first call
    mock_get_cache.return_value = None
    mock_http.return_value.status_code = 200
    mock_http.return_value.json.return_value = [
        {
            "show": {
                "id": 100,
                "name": "Test Show",
                "premiered": "2020-01-01",
                "rating": {"average": 7.8},
                "image": {"medium": "http://img/t.png"},
            }
        }
    ]

    results = search_show("Test Show")
    assert isinstance(results, list)
    assert results[0]["id"] == 100
    assert results[0]["name"] == "Test Show"


@patch("mpv_scraper.tvmaze.requests.get")
@patch("mpv_scraper.tvmaze._set_to_cache")
@patch("mpv_scraper.tvmaze._get_from_cache")
def test_get_episodes(mock_get_cache, _set_cache, mock_http):
    from mpv_scraper.tvmaze import get_show_episodes

    # First call no cache; provide API episodes
    mock_get_cache.return_value = None
    mock_http.return_value.status_code = 200
    mock_http.return_value.json.return_value = [
        {
            "id": 1,
            "name": "Pilot",
            "season": 1,
            "number": 1,
            "summary": "<p>Intro</p>",
            "airdate": "2020-01-01",
            "image": {"medium": "http://img/e1.png"},
        },
        {
            "id": 2,
            "name": "Ep 2",
            "season": 1,
            "number": 2,
            "summary": None,
            "airdate": "2020-01-02",
            "image": None,
        },
    ]

    eps = get_show_episodes(100)
    assert len(eps) == 2
    e1 = eps[0]
    assert e1["seasonNumber"] == 1
    assert e1["number"] == 1
    assert e1["episodeName"] == "Pilot"
    assert e1["overview"] == "Intro"
    assert e1["firstAired"] == "2020-01-01"
