"""Directory scanner for the `/mpv` media folder.

`scan_directory` walks one level deep, distinguishing between show
sub-folders and the special `Movies/` folder, returning a `ScanResult`
object listing all discovered media.
"""

from pathlib import Path
from .types import ScanResult, ShowDirectory, MovieFile

# Common video file extensions
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}


def is_video_file(file_path: Path) -> bool:
    """Check if a file is a video file based on its extension."""
    return file_path.suffix.lower() in VIDEO_EXTENSIONS


def scan_directory(path: Path) -> ScanResult:
    """
    Scans a directory to identify TV show subdirectories and movie files.

    Args:
        path: The root directory to scan.

    Returns:
        A ScanResult object containing lists of ShowDirectory and MovieFile objects.

    Raises:
        FileNotFoundError: If the provided path does not exist or is not a directory.
    """
    if not path.is_dir():
        raise FileNotFoundError(
            f"The specified path does not exist or is not a directory: {path}"
        )

    shows = []
    movies = []

    for item in path.iterdir():
        if item.name.startswith("."):
            continue

        if item.is_dir():
            if item.name == "Movies":
                for movie_file in item.iterdir():
                    if (
                        movie_file.is_file()
                        and not movie_file.name.startswith(".")
                        and is_video_file(movie_file)
                    ):
                        movies.append(MovieFile(path=movie_file))
            else:
                show_files = [
                    f
                    for f in item.iterdir()
                    if f.is_file() and not f.name.startswith(".") and is_video_file(f)
                ]
                if show_files:
                    shows.append(ShowDirectory(path=item, files=show_files))

    return ScanResult(shows=shows, movies=movies)
