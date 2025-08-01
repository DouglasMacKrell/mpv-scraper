from pathlib import Path
from typing import Dict, List


def scan_directory(path: Path) -> Dict[str, List[Path]]:
    """
    Scans a directory to identify TV show subdirectories and movie files.

    This function iterates through a given path and sorts its contents:
    - Subdirectories are considered TV show folders.
    - The special 'Movies' subdirectory is scanned for individual movie files.
    - It handles cases where the path itself is the 'Movies' directory.
    - Hidden files and system files (like .DS_Store) are ignored.

    Args:
        path: The root directory to scan (e.g., '/mpv').

    Returns:
        A dictionary with two keys:
        'shows': A list of Paths to individual show directories.
        'movies': A list of Paths to individual movie files.
        Returns an empty structure if the path doesn't exist.
    """
    if not path.exists() or not path.is_dir():
        return {"shows": [], "movies": []}

    shows = []
    movies = []

    # Handle the case where the scanner is pointed directly at the Movies folder
    if path.name == "Movies":
        for item in path.iterdir():
            if item.is_file() and not item.name.startswith("."):
                movies.append(item)
        return {"shows": [], "movies": movies}

    # Standard case: scanning the root media directory
    for item in path.iterdir():
        if item.name.startswith("."):
            continue

        if item.is_dir():
            if item.name == "Movies":
                # Scan inside the Movies directory for movie files
                for movie_file in item.iterdir():
                    if movie_file.is_file() and not movie_file.name.startswith("."):
                        movies.append(movie_file)
            else:
                # Any other directory is considered a show directory
                shows.append(item)

    return {"shows": shows, "movies": movies}
