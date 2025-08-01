# Documentation: Filename Parser

## 1. Overview

The Filename Parser module is responsible for extracting structured metadata from raw media filenames. It contains specialized functions to handle different naming conventions for TV shows and movies, including complex cases like multi-episode "anthology" files.

This module is critical for providing the metadata APIs (TVDB, TMDB) with clean, accurate search queries.

## 2. Core Functionality

The parser exposes two primary functions:
- `parser.parse_tv_filename(filename)`
- `parser.parse_movie_filename(filename)`

### `parse_tv_filename`
This function is designed to process filenames that follow a standard Scene-style `SxxEyy` format.

**Supported Formats:**
- Single Episode: `Show Name - S01E01 - Episode Title.mkv`
- Anthology/Span: `Show Name - S01E09-E10 - Title A & Title B.mp4`
- No Episode Title: `Show Name - S10E05.mkv`
- Unconventional Spacing: `Show  -  S01E01  -  Title.mp4`

**Output:**
Returns a `TVMeta` object (from `mpv_scraper.types`) on success, or `None` if the filename does not match the TV show pattern.

```python
@dataclass
class TVMeta:
    show: str       # e.g., "Paw Patrol"
    season: int     # e.g., 1
    start_ep: int   # e.g., 9
    end_ep: int     # e.g., 10 (same as start_ep if not a span)
    titles: List[str] # e.g., ["Pup Pup Goose", "Pup Pup and Away"]
```

### `parse_movie_filename`
This function processes filenames for standalone movies.

**Supported Formats:**
- With Year: `Back to the Future (1985).mp4`
- Without Year: `The Terminator.mkv`

**Output:**
Returns a `MovieMeta` object (from `mpv_scraper.types`) on success, or `None` if the filename appears to be a TV show (to prevent crossover).

```python
@dataclass
class MovieMeta:
    title: str      # e.g., "Back to the Future"
    year: Optional[int] # e.g., 1985
```

## 3. Implementation Details

### Regex Patterns
The core of the parser relies on robust regular expressions.

- **TV Show Pattern:**
  - `^(.*?)[\s\.-]*[Ss](\d{1,2})[Ee](\d{1,2})([\s\.-]*[Ee](\d{1,2}))?[\s\.-]*(.*?)(\.\w+)?$`
  - This pattern is designed to be flexible, capturing the show name, season/episode numbers (including optional end episode for spans), and the remaining string, which is treated as the title(s). It correctly handles various separators (`-`, `.`, ` `).

- **Movie Pattern:**
  - `^(.+?)(?:\s\((\d{4})\))?(\.\w+)?$`
  - This pattern captures the main title and an optional 4-digit year enclosed in parentheses at the end of the filename.

### Anthology Span Logic
For TV shows, if an end episode is detected (e.g., `-E10`), the parser:
1.  Sets both `start_ep` and `end_ep`.
2.  Splits the remaining title string by common delimiters (`&`, `–`) to create a list of individual episode titles.

This ensures anthology episodes are fully represented in the metadata, allowing for correct naming and fallback lookups during scraping.

### Disambiguation
- The `parse_movie_filename` function contains a preliminary check to see if a filename contains a TV-style `SxxEyy` pattern. If it does, it immediately returns `None` to avoid incorrectly classifying a TV episode as a movie.
- The `parse_tv_filename` function will naturally return `None` for a typical movie file, as it will fail to find the required season/episode markers.
