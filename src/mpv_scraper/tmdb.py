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

    # Determine if we have an API key or Bearer token
    is_bearer_token = api_key.startswith("eyJ") and len(api_key) > 100

    if is_bearer_token:
        # Use Bearer token authentication
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"query": title}
        if year:
            params["year"] = year
    else:
        # Use API key as query parameter
        headers = {}
        params = {"api_key": api_key, "query": title}
        if year:
            params["year"] = year

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    # Add language preference for English content
    if not is_bearer_token:
        params["language"] = "en-US"
    
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


def get_movie_images(movie_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches image information for a specific movie from the TMDB API.

    Args:
        movie_id: The TMDB ID of the movie.

    Returns:
        A dictionary containing the movie's images, or None if not found.

    Raises:
        ValueError: If the TMDB_API_KEY environment variable is not set.
    """
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError("TMDB_API_KEY environment variable not set.")

    cache_key = f"tmdb_movie_{movie_id}_images"
    cached_images = _get_from_cache(cache_key)
    if cached_images:
        return cached_images

    # Determine if we have an API key or Bearer token
    is_bearer_token = api_key.startswith("eyJ") and len(api_key) > 100

    if is_bearer_token:
        # Use Bearer token authentication
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {}
    else:
        # Use API key as query parameter
        headers = {}
        params = {"api_key": api_key}

    # Add language preference for English content
    if not is_bearer_token:
        params["include_image_language"] = "en,en-US,null"
    
    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    response = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}/images",
        headers=headers,
        params=params,
        timeout=10,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()

    images = response.json()
    _set_to_cache(cache_key, images)

    return images


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

    # Determine if we have an API key or Bearer token
    is_bearer_token = api_key.startswith("eyJ") and len(api_key) > 100

    if is_bearer_token:
        # Use Bearer token authentication
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {}
    else:
        # Use API key as query parameter
        headers = {}
        params = {"api_key": api_key}

    # Add language preference for English content
    if not is_bearer_token:
        params["language"] = "en-US"
    
    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    response = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}",
        headers=headers,
        params=params,
        timeout=10,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()

    details = response.json()

    # Get images to add poster and logo URLs
    images = get_movie_images(movie_id)
    if images:
        # Get best poster (highest vote_average, prefer USA region, filter for English)
        posters = images.get("posters", [])
        if posters:
            # More aggressive English filtering - prioritize US region and exclude known non-English
            us_posters = [p for p in posters if p.get("iso_3166_1") == "US"]
            english_posters = [p for p in posters if p.get("iso_639_1") == "en"]
            
            # Priority order: US posters first, then English posters, then all others
            if us_posters:
                poster_candidates = us_posters
            elif english_posters:
                poster_candidates = english_posters
            else:
                # If no language info, try to filter by excluding known non-English patterns
                # Look for posters that don't have obvious non-English indicators
                poster_candidates = [
                    p for p in posters 
                    if not any(non_eng in p.get("file_path", "").lower() 
                             for non_eng in ["ru", "de", "fr", "es", "it", "pt", "ja", "ko", "zh"])
                ]
                # If still no good candidates, use all posters
                if not poster_candidates:
                    poster_candidates = posters
            
            # Sort by vote_average descending and prefer USA region
            best_poster = max(
                poster_candidates,
                key=lambda x: (x.get("vote_average", 0), x.get("iso_3166_1") == "US"),
            )
            details["poster_url"] = (
                f"https://image.tmdb.org/t/p/original{best_poster['file_path']}"
            )

        # Get best logo (highest vote_average, prefer PNG for transparency, prefer USA region, filter for English)
        logos = images.get("logos", [])
        if logos:
            # More aggressive English filtering - prioritize US region and exclude known non-English
            us_logos = [l for l in logos if l.get("iso_3166_1") == "US"]
            english_logos = [l for l in logos if l.get("iso_639_1") == "en"]
            
            # Priority order: US logos first, then English logos, then all others
            if us_logos:
                logo_candidates = us_logos
            elif english_logos:
                logo_candidates = english_logos
            else:
                # If no language info, try to filter by excluding known non-English patterns
                logo_candidates = [
                    l for l in logos 
                    if not any(non_eng in l.get("file_path", "").lower() 
                             for non_eng in ["ru", "de", "fr", "es", "it", "pt", "ja", "ko", "zh"])
                ]
                # If still no good candidates, use all logos
                if not logo_candidates:
                    logo_candidates = logos
            
            # Sort by vote_average descending, prefer PNG files, and prefer USA region
            best_logo = max(
                logo_candidates,
                key=lambda x: (
                    x.get("vote_average", 0),
                    x.get("file_path", "").endswith(".png"),
                    x.get("iso_3166_1") == "US",
                ),
            )
            details["logo_url"] = (
                f"https://image.tmdb.org/t/p/original{best_logo['file_path']}"
            )

    # Normalize vote_average to a 0-1 float
    from mpv_scraper.utils import normalize_rating  # type: ignore

    vote_average = details.get("vote_average", 0.0)
    details["vote_average"] = normalize_rating(vote_average)

    # Ensure a useful long description is always present.
    if not details.get("overview"):
        details["overview"] = details.get("tagline", "")

    # Extract genre names from genre objects
    if details.get("genres"):
        details["genre_names"] = [
            genre.get("name", "") for genre in details.get("genres", [])
        ]

    # Extract production company names
    if details.get("production_companies"):
        details["production_company_names"] = [
            company.get("name", "")
            for company in details.get("production_companies", [])
        ]

    # Extract distributor from release dates (simplified approach)
    # For now, we'll use the first production company as a fallback
    if details.get("production_companies"):
        details["distributor"] = details.get("production_companies", [{}])[0].get(
            "name", ""
        )

    _set_to_cache(cache_key, details)

    return details
