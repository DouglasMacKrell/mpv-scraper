"""Miscellaneous utility helpers for mpv_scraper."""

from typing import Final

__all__ = [
    "normalize_rating",
]

from typing import Union

_MAX_RAW: Final[float] = 10.0


def normalize_rating(raw: Union[float, int, None]) -> float:
    """Convert a 0–10 rating to 0–1, clamped to range.

    Parameters
    ----------
    raw
        Original rating value as returned by TVDB / TMDB (0‒10 scale).

    Returns
    -------
    float
        Rating between 0.0 and 1.0 rounded to two decimals.
    """

    if raw is None:
        return 0.0
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0

    if value < 0:
        value = 0.0
    elif value > _MAX_RAW:
        value = _MAX_RAW

    return round(value / _MAX_RAW, 2)
