"""Filename parsing utilities for TV episodes and movies.

This module exposes two public helpers:

* `parse_tv_filename`  – Parses TV episode filenames, including anthology
  spans like `S01E09-E10`, returning a `TVMeta` dataclass.
* `parse_movie_filename` – Parses movie filenames in `Title (Year)` format,
  returning a `MovieMeta` dataclass (or `None` if the file actually looks
  like a TV episode).
"""

import re
from pathlib import Path
from typing import Optional

from mpv_scraper.types import TVMeta, MovieMeta


def parse_tv_filename(filename: str) -> Optional[TVMeta]:
    """
    Parses a TV show filename to extract metadata using regex.

    The regex is designed to capture:
    - Show name (group 1)
    - Season number (group 2)
    - Starting episode number (group 3)
    - Optional ending episode number for spans (group 5)
    - Episode titles (group 6)

    It handles single episodes (SxxEyy), anthology spans (SxxExx-Eyy),
    and variations in spacing and separators.

    Args:
        filename: The name of the media file (e.g., "Show - S01E01 - Title.mkv").

    Returns:
        A TVMeta object if parsing is successful, otherwise None.
    """
    # Regex to capture show name, season/episode info, and titles
    pattern = re.compile(
        r"^(.*?)[\s\.-]*[Ss](\d{1,2})[Ee](\d{1,2})([\s\.-]*[Ee](\d{1,2}))?[\s\.-]*(.*?)(\.\w+)?$"
    )

    match = pattern.match(Path(filename).stem)

    if not match:
        return None

    show_name = match.group(1).strip()
    season = int(match.group(2))
    start_ep = int(match.group(3))

    # Handle episode spans (e.g., S01E09-E10)
    end_ep = int(match.group(5)) if match.group(5) else start_ep

    # Split titles for anthology episodes
    title_part = match.group(6).strip()
    if title_part:
        # Split titles by common delimiters like ' & '
        titles = [
            t.strip() for t in re.split(r"\s*&\s*|\s*–\s*", title_part) if t.strip()
        ]
    else:
        titles = []

    return TVMeta(
        show=show_name,
        season=season,
        start_ep=start_ep,
        end_ep=end_ep,
        titles=titles,
    )


def parse_movie_filename(filename: str) -> Optional[MovieMeta]:
    """
    Parses a movie filename to extract the title and year.

    Args:
        filename: The name of the media file (e.g., "Movie Title (Year).mkv").

    Returns:
        A MovieMeta object if parsing is successful, otherwise None.
    """
    # First, check if it's a TV show, and if so, ignore it.
    tv_pattern = re.compile(r"S\d{2}E\d{2}", re.IGNORECASE)
    if tv_pattern.search(filename):
        return None

    # Regex to capture movie title and optional year
    pattern = re.compile(r"^(.+?)(?:\s\((\d{4})\))?(\.\w+)?$")
    match = pattern.match(Path(filename).stem)

    if not match:
        return None

    title = match.group(1).strip()
    year = int(match.group(2)) if match.group(2) else None

    return MovieMeta(title=title, year=year)
