from dataclasses import dataclass
from typing import List


@dataclass
class TVShowMeta:
    """A dataclass to hold metadata parsed from a TV show filename."""

    show: str
    season: int
    start_ep: int
    end_ep: int
    titles: List[str]
