from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TVMeta:
    """Metadata extracted from a TV show filename."""

    show: str
    season: int
    start_ep: int
    end_ep: int
    titles: List[str] = field(default_factory=list)


@dataclass
class MovieMeta:
    """Metadata extracted from a movie filename."""

    title: str
    year: Optional[int]
