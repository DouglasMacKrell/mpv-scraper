from pathlib import Path
from .types import ScanResult, ShowDirectory, MovieFile


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
                    if movie_file.is_file() and not movie_file.name.startswith("."):
                        movies.append(MovieFile(path=movie_file))
            else:
                show_files = [
                    f
                    for f in item.iterdir()
                    if f.is_file() and not f.name.startswith(".")
                ]
                if show_files:
                    shows.append(ShowDirectory(path=item, files=show_files))

    return ScanResult(shows=shows, movies=movies)
