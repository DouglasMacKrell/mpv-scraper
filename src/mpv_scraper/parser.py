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

    # Clean filename by removing quality tags and other metadata
    clean_filename = Path(filename).stem

    # First, extract year if present in parentheses
    year_match = re.search(r"\((\d{4})\)", clean_filename)
    year = int(year_match.group(1)) if year_match else None

    # Remove year from filename for further cleaning
    if year_match:
        clean_filename = clean_filename.replace(year_match.group(0), "")

    # Remove common quality tags and metadata
    quality_patterns = [
        r"\s+(?:Bluray|WEBRip|HDRip|BRRip|DVDRip|HDTV|PDTV|WEB-DL|BluRay|Blu-Ray|WEB|HD|1080p|720p|480p|2160p|4K|UHD)",
        r"\s+(?:x264|x265|HEVC|AVC|AAC|AC3|DTS|FLAC|MP3)",
        r"\s+(?:REPACK|PROPER|INTERNAL|EXTENDED|DIRFIX|SUBFIX|AUDIOFIX)",
        r"\s+\[.*?\]",  # Remove anything in brackets
        r"\s*-\s*(?:1080p|720p|480p|2160p|4K|UHD)",  # Remove quality tags after dashes
    ]

    for pattern in quality_patterns:
        clean_filename = re.sub(pattern, "", clean_filename, flags=re.IGNORECASE)

    # Clean up extra spaces and dashes
    title = clean_filename.strip().rstrip("-").strip()

    if not title:
        return None

    return MovieMeta(title=title, year=year)
