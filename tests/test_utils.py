"""Tests for utility functions."""

from mpv_scraper.utils import normalize_rating, format_release_date


def test_normalize_rating():
    """Test rating normalization from 0-10 to 0-1 scale."""
    assert normalize_rating(10.0) == 1.0
    assert normalize_rating(5.0) == 0.5
    assert normalize_rating(0.0) == 0.0
    assert normalize_rating(7.5) == 0.75
    assert normalize_rating(None) == 0.0
    assert normalize_rating("invalid") == 0.0


def test_format_release_date():
    """Test date formatting to EmulationStation format."""
    # Valid dates
    assert format_release_date("2023-01-15") == "20230115T000000"
    assert format_release_date("1995-03-11") == "19950311T000000"
    assert format_release_date("2020-12-31") == "20201231T000000"

    # Invalid dates
    assert format_release_date(None) is None
    assert format_release_date("") is None
    assert format_release_date("invalid") is None
    assert format_release_date("2023/01/15") is None  # Wrong separator
    assert format_release_date("2023-1-15") is None  # Missing leading zeros
    assert format_release_date("2023-01-5") is None  # Missing leading zeros
    assert format_release_date("23-01-15") is None  # Short year
