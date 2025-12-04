from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class TVMeta:
    """Metadata extracted from a TV show filename."""

    show: str
    season: int
    start_ep: int
    end_ep: int
    titles: List[str] = field(default_factory=list)
    api_tag: Optional[str] = None  # Format: "tvdb-70533" or "tmdb-15196"


@dataclass
class MovieMeta:
    """Metadata extracted from a movie filename."""

    title: str
    year: Optional[int]
    api_tag: Optional[str] = None  # Format: "tvdb-70533" or "tmdb-15196"


@dataclass
class ShowDirectory:
    """Represents a directory containing episodes for a single TV show."""

    path: Path
    files: List[Path]


@dataclass
class MovieFile:
    """Represents a single movie file."""

    path: Path


@dataclass
class ScanResult:
    """The result of a directory scan, containing discovered shows and movies."""

    shows: List[ShowDirectory]
    movies: List[MovieFile]
