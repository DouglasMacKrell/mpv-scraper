import os
import requests
from typing import List, Dict, Any, Optional
import time

from .tvdb import _get_from_cache, _set_to_cache, API_RATE_LIMIT_DELAY_SECONDS


def search_movie(title: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Searches for a movie by title and optional year using the TMDB API.

    Args:
        title: The title of the movie.
        year: The optional year of the movie's release.

    Returns:
        A list of movie results from the TMDB API.

    Raises:
        ValueError: If the TMDB_API_KEY environment variable is not set.
    """
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError("TMDB_API_KEY environment variable not set.")

    # Use the same cache functions from the tvdb module
    cache_key = f"tmdb_search_{title.lower().replace(' ', '_')}_{year or 'any'}"
    cached_search = _get_from_cache(cache_key)
    if cached_search:
        return cached_search

    params = {
        "api_key": api_key,
        "query": title,
    }
    if year:
        params["year"] = year

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    response = requests.get(
        "https://api.themoviedb.org/3/search/movie",
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    _set_to_cache(cache_key, results)

    return results
