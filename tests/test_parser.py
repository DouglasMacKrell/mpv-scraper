import pytest

from mpv_scraper.types import TVMeta, MovieMeta
from mpv_scraper.parser import parse_tv_filename, parse_movie_filename


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "Paw Patrol - S01E01 - Pups Make a Splash.mkv",
            TVMeta(
                show="Paw Patrol",
                season=1,
                start_ep=1,
                end_ep=1,
                titles=["Pups Make a Splash"],
                api_tag=None,
            ),
        ),
        (
            "Game of Thrones - S08E06 - The Iron Throne.mp4",
            TVMeta(
                show="Game of Thrones",
                season=8,
                start_ep=6,
                end_ep=6,
                titles=["The Iron Throne"],
                api_tag=None,
            ),
        ),
        (
            "Bluey - S02E25 - Christmas Swim.mkv",
            TVMeta(
                show="Bluey",
                season=2,
                start_ep=25,
                end_ep=25,
                titles=["Christmas Swim"],
                api_tag=None,
            ),
        ),
    ],
)
def test_parse_single_episode(filename: str, expected: TVMeta):
    """Tests parsing of filenames with a single episode."""
    assert parse_tv_filename(filename) == expected


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "Paw Patrol - S01E09-E10 - Pup Pup Goose & Pup Pup and Away.mp4",
            TVMeta(
                show="Paw Patrol",
                season=1,
                start_ep=9,
                end_ep=10,
                titles=["Pup Pup Goose", "Pup Pup and Away"],
                api_tag=None,
            ),
        ),
        (
            "Doctor Who (2005) - S04E08-E09 - Silence in the Library & Forest of the Dead.mkv",
            TVMeta(
                show="Doctor Who (2005)",
                season=4,
                start_ep=8,
                end_ep=9,
                titles=["Silence in the Library", "Forest of the Dead"],
                api_tag=None,
            ),
        ),
    ],
)
def test_parse_anthology_span(filename: str, expected: TVMeta):
    """Tests parsing of filenames with an episode range (SxxExx-Eyy)."""
    assert parse_tv_filename(filename) == expected


def test_parse_filename_with_no_title():
    """Tests parsing a filename that lacks an episode title section."""
    filename = "The Simpsons - S10E05.mkv"
    expected = TVMeta(
        show="The Simpsons", season=10, start_ep=5, end_ep=5, titles=[], api_tag=None
    )
    assert parse_tv_filename(filename) == expected


def test_parse_filename_with_unconventional_spacing():
    """Tests robustness against extra spaces in the filename."""
    filename = "Loki  -  S01E01  -  Glorious Purpose.mp4"
    expected = TVMeta(
        show="Loki",
        season=1,
        start_ep=1,
        end_ep=1,
        titles=["Glorious Purpose"],
        api_tag=None,
    )
    assert parse_tv_filename(filename) == expected


def test_parse_filename_returns_none_for_invalid_format():
    """Tests that non-matching filenames return None."""
    assert parse_tv_filename("my_vacation_video.mov") is None
    assert parse_tv_filename("A Movie (2023).mp4") is None
    assert parse_tv_filename("Just a random file.txt") is None


class TestParseMovieFilename:
    def test_standard_movie(self):
        """Tests parsing of a standard movie filename `Title (Year).ext`."""
        filename = "Back to the Future (1985).mp4"
        expected = MovieMeta(title="Back to the Future", year=1985, api_tag=None)
        assert parse_movie_filename(filename) == expected

    def test_missing_year(self):
        """Tests parsing a movie filename without a year."""
        filename = "The Terminator.mkv"
        expected = MovieMeta(title="The Terminator", year=None, api_tag=None)
        assert parse_movie_filename(filename) == expected

    def test_returns_none_for_tv_show(self):
        """Tests that a TV show filename returns None."""
        filename = "Paw Patrol - S01E01 - Pups Make a Splash.mkv"
        assert parse_movie_filename(filename) is None


class TestParseFilenameWithApiTags:
    """Tests for API tag extraction from filenames."""

    def test_parse_filename_with_api_tag_tvdb(self):
        """Tests parsing TV filename with TVDB API tag."""
        filename = "Twin Peaks - S01E01 - Pilot {tvdb-70533}.mkv"
        result = parse_tv_filename(filename)
        assert result is not None
        assert result.api_tag == "tvdb-70533"
        assert result.show == "Twin Peaks"
        assert result.season == 1
        assert result.start_ep == 1

    def test_parse_filename_with_api_tag_tmdb(self):
        """Tests parsing movie filename with TMDB API tag."""
        filename = "Clue (1985) {tmdb-15196}.mkv"
        result = parse_movie_filename(filename)
        assert result is not None
        assert result.api_tag == "tmdb-15196"
        assert result.title == "Clue"
        assert result.year == 1985

    def test_parse_filename_with_api_tag_case_insensitive(self):
        """Tests that API tags are normalized to lowercase."""
        filename = "Twin Peaks - S01E01 - Pilot {TVDB-70533}.mkv"
        result = parse_tv_filename(filename)
        assert result is not None
        assert result.api_tag == "tvdb-70533"  # Normalized to lowercase

        filename2 = "Clue (1985) {TMDB-15196}.mkv"
        result2 = parse_movie_filename(filename2)
        assert result2 is not None
        assert result2.api_tag == "tmdb-15196"  # Normalized to lowercase

    def test_parse_filename_with_api_tag_multiple_tags_uses_last(self):
        """Tests that if multiple API tags are present, the last one is used."""
        filename = "Show - S01E01 - Title {tvdb-12345} {tmdb-67890}.mkv"
        result = parse_tv_filename(filename)
        assert result is not None
        assert result.api_tag == "tmdb-67890"  # Last tag used as fallback

    def test_parse_filename_with_api_tag_all_providers(self):
        """Tests that all supported API providers are recognized."""
        providers = ["tvdb", "tmdb", "omdb", "tvmaze", "anidb", "fanarttv"]
        for provider in providers:
            filename = f"Test - S01E01 - Episode {{{provider}-12345}}.mkv"
            result = parse_tv_filename(filename)
            assert result is not None
            assert result.api_tag == f"{provider}-12345"

    def test_parse_filename_with_api_tag_unsupported_provider(self):
        """Tests that unsupported providers are ignored."""
        filename = "Test - S01E01 - Episode {unsupported-12345}.mkv"
        result = parse_tv_filename(filename)
        assert result is not None
        assert result.api_tag is None  # Unsupported provider ignored

    def test_parse_filename_with_api_tag_no_tag(self):
        """Tests that files without API tags still parse correctly."""
        filename = "Twin Peaks - S01E01 - Pilot.mkv"
        result = parse_tv_filename(filename)
        assert result is not None
        assert result.api_tag is None
        assert result.show == "Twin Peaks"
