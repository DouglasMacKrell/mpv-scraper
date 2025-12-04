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

# Supported API providers for filename tags
SUPPORTED_API_PROVIDERS = ["tvdb", "tmdb", "omdb", "tvmaze", "anidb", "fanarttv"]


def _extract_api_tag(filename: str) -> Optional[str]:
    """
    Extracts API tag from filename in format {provider-id} at the end.

    Examples:
        "Show - S01E01 - Title {tvdb-70533}.mkv" -> "tvdb-70533"
        "Movie (1985) {tmdb-15196}.mkv" -> "tmdb-15196"
        "Show {TVDB-70533}.mkv" -> "tvdb-70533" (normalized to lowercase)

    Args:
        filename: The filename to parse.

    Returns:
        Normalized API tag string (e.g., "tvdb-70533") or None if not found.
    """
    # Pattern to match {provider-id} at end of filename (before extension)
    # Supports case-insensitive provider names
    pattern = r"\{([a-zA-Z]+)-(\d+)\}"
    matches = re.findall(pattern, filename)

    if not matches:
        return None

    # Use the last match if multiple tags present (fallback behavior)
    provider, api_id = matches[-1]
    provider_lower = provider.lower()

    # Validate provider is supported
    if provider_lower not in SUPPORTED_API_PROVIDERS:
        return None

    # Normalize to lowercase format: "provider-id"
    return f"{provider_lower}-{api_id}"


def parse_tv_filename(filename: str) -> Optional[TVMeta]:
    """
    Parses a TV show filename to extract metadata using regex.

    The regex is designed to capture:
    - Show name (group 1)
    - Season number or year (group 2)
    - Starting episode number (group 3)
    - Optional ending episode number for spans (group 5)
    - Episode titles (group 6)

    It handles:
    - Traditional episodes (S01E01)
    - Year-based episodes (S1934E03) for shows like Popeye
    - Alternative format (01x01)
    - Anthology spans (S01E09-E10)
    - Variations in spacing and separators

    Args:
        filename: The name of the media file (e.g., "Show - S01E01 - Title.mkv").

    Returns:
        A TVMeta object if parsing is successful, otherwise None.
    """
    # Extract API tag before processing (it's at the end of filename)
    api_tag = _extract_api_tag(filename)

    # Remove API tag from filename stem before parsing (to avoid including in title)
    filename_stem = Path(filename).stem
    if api_tag:
        # Remove {provider-id} pattern (case-insensitive)
        filename_stem = re.sub(
            r"\{[a-zA-Z]+-\d+\}", "", filename_stem, flags=re.IGNORECASE
        )

    # Multiple patterns to handle different formats
    patterns = [
        # Traditional format: S01E01 or S1934E03 (year-based)
        r"^(.*?)[\s\.-]*[Ss](\d{1,4})[Ee](\d{1,3})([\s\.-]*[Ee](\d{1,3}))?[\s\.-]*(.*?)(\.\w+)?$",
        # Alternative format: 01x01
        r"^(.*?)[\s\.-]*(\d{1,2})[xX](\d{1,2})([\s\.-]*[xX](\d{1,2}))?[\s\.-]*(.*?)(\.\w+)?$",
    ]

    for pattern in patterns:
        match = re.match(pattern, filename_stem)
        if match:
            show_name = match.group(1).strip()
            season_or_year = int(match.group(2))
            start_ep = int(match.group(3))

            # Handle episode spans (e.g., S01E09-E10 or 01x09-10)
            end_ep = int(match.group(5)) if match.group(5) else start_ep

            # Split titles for anthology episodes
            title_part = match.group(6).strip()
            if title_part:
                # Clean quality metadata from titles (same as movie parser)
                quality_patterns = [
                    r"\s+(?:Bluray|WEBRip|HDRip|BRRip|DVDRip|HDTV|PDTV|WEB-DL|BluRay|Blu-Ray|WEB|HD|1080p|720p|480p|2160p|4K|UHD)",
                    r"\s+(?:x264|x265|HEVC|AVC|AAC|AC3|DTS|FLAC|MP3)",
                    r"\s+(?:REPACK|PROPER|INTERNAL|EXTENDED|DIRFIX|SUBFIX|AUDIOFIX)",
                    r"\s+\[.*?\]",  # Remove anything in brackets
                    r"\s*-\s*(?:1080p|720p|480p|2160p|4K|UHD)",  # Remove quality tags after dashes
                    r"\s+(?:Remux|REMUX|Remastered|REMUX)",  # Remove remux tags
                ]

                for pattern in quality_patterns:
                    title_part = re.sub(pattern, "", title_part, flags=re.IGNORECASE)

                # Clean up extra spaces and dashes
                title_part = title_part.strip().rstrip("-").strip()

                # Split titles by common delimiters like ' & '
                titles = [
                    t.strip()
                    for t in re.split(r"\s*&\s*|\s*–\s*", title_part)
                    if t.strip()
                ]
            else:
                titles = []

            return TVMeta(
                show=show_name,
                season=season_or_year,
                start_ep=start_ep,
                end_ep=end_ep,
                titles=titles,
                api_tag=api_tag,
            )

    return None


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

    # Extract API tag before processing (it's at the end of filename)
    api_tag = _extract_api_tag(filename)

    # Clean filename by removing quality tags and other metadata
    clean_filename = Path(filename).stem

    # Remove API tag from filename if present (before processing title)
    if api_tag:
        # Remove {provider-id} pattern (case-insensitive)
        clean_filename = re.sub(
            r"\{[a-zA-Z]+-\d+\}", "", clean_filename, flags=re.IGNORECASE
        )

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

    return MovieMeta(title=title, year=year, api_tag=api_tag)
