"""Miscellaneous utility helpers for mpv_scraper."""

import functools
import time
from typing import Any, Callable, Final, Type, Union

__all__ = [
    "normalize_rating",
    "retry_with_backoff",
]

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


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Retry decorator with exponential backoff.

    Parameters
    ----------
    max_attempts
        Maximum number of attempts before giving up.
    base_delay
        Base delay in seconds for exponential backoff.
    exceptions
        Tuple of exception types to retry on.

    Returns
    -------
    Callable
        Decorated function that will retry on specified exceptions.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:  # Don't sleep on last attempt
                        delay = base_delay * (2**attempt)  # Exponential backoff
                        time.sleep(delay)

            # If we get here, all attempts failed
            raise last_exception

        return wrapper

    return decorator
