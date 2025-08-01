import pytest
from pathlib import Path
from mpv_scraper.scanner import scan_directory


@pytest.fixture
def media_root(tmp_path: Path) -> Path:
    """Create a mock media directory structure."""
    # Show directories
    (tmp_path / "Show A").mkdir()
    (tmp_path / "Show A" / "S01E01.mkv").touch()
    (tmp_path / "Show B").mkdir()
    (tmp_path / "Show B" / "S01E01.mp4").touch()

    # Movies directory
    movies_dir = tmp_path / "Movies"
    movies_dir.mkdir()
    (movies_dir / "Movie 1 (2023).mkv").touch()
    (movies_dir / "Movie 2 (2024).mp4").touch()

    # Other files to be ignored
    (tmp_path / "desktop.ini").touch()
    (tmp_path / ".DS_Store").touch()

    return tmp_path


@pytest.fixture
def empty_root(tmp_path: Path) -> Path:
    """An empty directory."""
    return tmp_path


def test_scan_directory_returns_shows_and_movies(media_root: Path):
    """
    Tests that the scanner correctly identifies show directories and movie files,
    ignoring the 'Movies' directory itself from the shows list.
    """
    result = scan_directory(media_root)

    assert "shows" in result
    assert "movies" in result

    expected_shows = [media_root / "Show A", media_root / "Show B"]
    expected_movies = [
        media_root / "Movies" / "Movie 1 (2023).mkv",
        media_root / "Movies" / "Movie 2 (2024).mp4",
    ]

    assert sorted(result["shows"]) == sorted(expected_shows)
    assert sorted(result["movies"]) == sorted(expected_movies)


def test_scan_empty_directory(empty_root: Path):
    """Tests that scanning an empty directory returns an empty structure."""
    result = scan_directory(empty_root)

    assert result == {"shows": [], "movies": []}


def test_scan_directory_with_only_movies(media_root: Path):
    """Tests scanning a directory that only contains movies."""
    movies_only_path = media_root / "Movies"
    # We are scanning the sub-directory here, so it should find files but no "show" folders
    result = scan_directory(movies_only_path)

    assert result["shows"] == []
    assert len(result["movies"]) == 2


def test_scan_directory_with_only_shows(media_root: Path):
    """Tests scanning a directory that only contains shows (by removing the Movies dir)."""
    import shutil

    shutil.rmtree(media_root / "Movies")

    result = scan_directory(media_root)

    assert len(result["shows"]) == 2
    assert result["movies"] == []


def test_scan_non_existent_directory():
    """Tests that scanning a non-existent path returns an empty structure."""
    result = scan_directory(Path("non_existent_path_for_testing"))
    assert result == {"shows": [], "movies": []}
