import pytest

from mpv_scraper.types import TVShowMeta

# This import will fail until the parser module is created
from mpv_scraper.parser import parse_tv_filename


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "Paw Patrol - S01E01 - Pups Make a Splash.mkv",
            TVShowMeta(
                show="Paw Patrol",
                season=1,
                start_ep=1,
                end_ep=1,
                titles=["Pups Make a Splash"],
            ),
        ),
        (
            "Game of Thrones - S08E06 - The Iron Throne.mp4",
            TVShowMeta(
                show="Game of Thrones",
                season=8,
                start_ep=6,
                end_ep=6,
                titles=["The Iron Throne"],
            ),
        ),
        (
            "Bluey - S02E25 - Christmas Swim.mkv",
            TVShowMeta(
                show="Bluey",
                season=2,
                start_ep=25,
                end_ep=25,
                titles=["Christmas Swim"],
            ),
        ),
    ],
)
def test_parse_single_episode(filename: str, expected: TVShowMeta):
    """Tests parsing of filenames with a single episode."""
    assert parse_tv_filename(filename) == expected


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "Paw Patrol - S01E09-E10 - Pup Pup Goose & Pup Pup and Away.mp4",
            TVShowMeta(
                show="Paw Patrol",
                season=1,
                start_ep=9,
                end_ep=10,
                titles=["Pup Pup Goose", "Pup Pup and Away"],
            ),
        ),
        (
            "Doctor Who (2005) - S04E08-E09 - Silence in the Library & Forest of the Dead.mkv",
            TVShowMeta(
                show="Doctor Who (2005)",
                season=4,
                start_ep=8,
                end_ep=9,
                titles=["Silence in the Library", "Forest of the Dead"],
            ),
        ),
    ],
)
def test_parse_anthology_span(filename: str, expected: TVShowMeta):
    """Tests parsing of filenames with an episode range (SxxExx-Eyy)."""
    assert parse_tv_filename(filename) == expected


def test_parse_filename_with_no_title():
    """Tests parsing a filename that lacks an episode title section."""
    filename = "The Simpsons - S10E05.mkv"
    expected = TVShowMeta(
        show="The Simpsons", season=10, start_ep=5, end_ep=5, titles=[]
    )
    assert parse_tv_filename(filename) == expected


def test_parse_filename_with_unconventional_spacing():
    """Tests robustness against extra spaces in the filename."""
    filename = "Loki  -  S01E01  -  Glorious Purpose.mp4"
    expected = TVShowMeta(
        show="Loki", season=1, start_ep=1, end_ep=1, titles=["Glorious Purpose"]
    )
    assert parse_tv_filename(filename) == expected


def test_parse_filename_returns_none_for_invalid_format():
    """Tests that non-matching filenames return None."""
    assert parse_tv_filename("my_vacation_video.mov") is None
    assert parse_tv_filename("A Movie (2023).mp4") is None
    assert parse_tv_filename("Just a random file.txt") is None
