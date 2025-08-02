"""TMDB API client helpers.

This module provides lightweight wrappers around TheMovieDB v3 REST API
for movie search (`search_movie`) and detailed lookup (`get_movie_details`).
Functions implement simple file-based caching and respect a global rate-
limit delay shared with the TVDB client.
"""

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

    cache_key = f"tmdb_search_{title.lower().replace(' ', '_')}_{year or 'any'}"
    cached_search = _get_from_cache(cache_key)
    if cached_search:
        return cached_search

    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "query": title,
    }
    if year:
        params["year"] = year

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    response = requests.get(
        "https://api.themoviedb.org/3/search/movie",
        headers=headers,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    _set_to_cache(cache_key, results)

    return results


def get_movie_details(movie_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches detailed information for a specific movie from the TMDB API.

    Args:
        movie_id: The TMDB ID of the movie.

    Returns:
        A dictionary containing the movie's details, or None if not found.

    Raises:
        ValueError: If the TMDB_API_KEY environment variable is not set.
    """
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError("TMDB_API_KEY environment variable not set.")

    cache_key = f"tmdb_movie_{movie_id}_details"
    cached_details = _get_from_cache(cache_key)
    if cached_details:
        return cached_details

    headers = {"Authorization": f"Bearer {api_key}"}

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    response = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}",
        headers=headers,
        timeout=10,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()

    details = response.json()

    # Normalize vote_average to a 0-1 float
    from mpv_scraper.utils import normalize_rating  # type: ignore

    vote_average = details.get("vote_average", 0.0)
    details["vote_average"] = normalize_rating(vote_average)

    _set_to_cache(cache_key, details)

    return details
