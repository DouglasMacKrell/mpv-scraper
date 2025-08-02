from mpv_scraper.utils import normalize_rating


def test_normalize_rating_basic():
    assert normalize_rating(7.5) == 0.75
    assert normalize_rating(0) == 0.0
    assert normalize_rating(10) == 1.0


def test_normalize_rating_bounds():
    # Values outside expected range are clamped
    assert normalize_rating(-5) == 0.0
    assert normalize_rating(12) == 1.0


def test_normalize_rating_invalid():
    assert normalize_rating(None) == 0.0
    assert normalize_rating("bad") == 0.0
