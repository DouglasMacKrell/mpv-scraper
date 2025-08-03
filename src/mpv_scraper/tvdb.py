"""TVDB API client helpers.

Handles authentication, searching, disambiguation prompts, and fetching
extended series information.  Implements simple disk caching and honors a
small delay between HTTP requests to respect rate limits.
"""

import click
import os
import requests
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

CACHE_DIR = Path.home() / ".cache" / "mpv-scraper"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
API_RATE_LIMIT_DELAY_SECONDS = 0.5


def _get_from_cache(key: str) -> Optional[Dict[str, Any]]:
    """Retrieves a JSON object from the cache if it exists and is not expired."""
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        cached_data = json.loads(cache_file.read_text())
        if time.time() - cached_data.get("timestamp", 0) < CACHE_TTL_SECONDS:
            return cached_data.get("data")
    return None


def _set_to_cache(key: str, data: Dict[str, Any]):
    """Saves a JSON object to the cache with a timestamp."""
    cache_file = CACHE_DIR / f"{key}.json"
    cached_data = {"timestamp": time.time(), "data": data}
    cache_file.write_text(json.dumps(cached_data))


def authenticate_tvdb() -> str:
    """
    Authenticates with the TVDB API and returns a JWT token.

    Raises:
        ValueError: If the TVDB_API_KEY is not set.
        requests.HTTPError: If the API call fails.

    Returns:
        A JWT token string.
    """
    api_key = os.getenv("TVDB_API_KEY")
    if not api_key:
        raise ValueError("TVDB_API_KEY environment variable not set.")

    # Check cache for a valid token first
    cached_token = _get_from_cache("tvdb_token")
    if cached_token and cached_token.get("token"):
        return cached_token["token"]

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    # Use legacy v3 API instead of v4
    response = requests.post(
        "https://api.thetvdb.com/login", json={"apikey": api_key}, timeout=10
    )
    response.raise_for_status()
    token = response.json()["token"]

    # Cache the new token
    _set_to_cache("tvdb_token", {"token": token})

    return token


def search_show(name: str, token: str) -> List[Dict[str, Any]]:
    """
    Searches for a TV show by name.

    Args:
        name: The name of the show to search for.
        token: The JWT authentication token.

    Returns:
        A list of candidate shows from the API.
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {"name": name}

    # Check cache
    cache_key = f"search_{name.lower().replace(' ', '_')}"
    cached_search = _get_from_cache(cache_key)
    if cached_search:
        return cached_search

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    # Use legacy v3 API instead of v4
    response = requests.get(
        "https://api.thetvdb.com/search/series",
        headers=headers,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    search_results = response.json().get("data", [])

    _set_to_cache(cache_key, search_results)

    return search_results


def disambiguate_show(results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Prompts the user to choose from a list of search results.

    Args:
        results: A list of show data dictionaries from the search.

    Returns:
        The selected show dictionary, or None if the user cancels.
    """
    if not results:
        return None
    if len(results) == 1:
        return results[0]

    click.echo("Found multiple possible matches. Please choose one:")
    for i, result in enumerate(results):
        name = result.get("name", "Unknown")
        year = result.get("year", "N/A")
        click.echo(f"  [{i+1}] {name} ({year})")

    choice = click.prompt(
        "Enter the number of the correct show (or 0 to cancel)", type=int, default=0
    )

    if 0 < choice <= len(results):
        return results[choice - 1]

    return None


def get_series_extended(series_id: int, token: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the full extended record for a series, including all episodes.

    Args:
        series_id: The numeric ID of the series.
        token: The JWT authentication token.

    Returns:
        A dictionary containing the full series record, or None if not found.
    """
    # Based on namegnome working implementation, use legacy v3 API
    headers = {"Authorization": f"Bearer {token}"}

    # Check cache
    cache_key = f"series_{series_id}_extended"
    cached_record = _get_from_cache(cache_key)
    if cached_record:
        return cached_record

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)

    # Legacy v3 API - get series and episodes separately
    series_response = requests.get(
        f"https://api.thetvdb.com/series/{series_id}",
        headers=headers,
        timeout=10,
    )

    if series_response.status_code == 404:
        return None

    series_response.raise_for_status()
    series_data = series_response.json().get("data", {})

    # Get episodes
    episodes_response = requests.get(
        f"https://api.thetvdb.com/series/{series_id}/episodes",
        headers=headers,
        timeout=10,
    )
    episodes_response.raise_for_status()
    episodes_data = episodes_response.json().get("data", [])

    # Get image URLs from series data
    poster_url = None
    logo_url = None
    if series_data.get("poster"):
        poster_url = f"https://www.thetvdb.com/banners/{series_data.get('poster')}"

    # Get ClearLogo from artwork endpoint
    try:
        artwork_response = requests.get(
            f"https://api.thetvdb.com/series/{series_id}/images/query?keyType=clearlogo",
            headers=headers,
            timeout=10,
        )
        if artwork_response.status_code == 200:
            artwork_data = artwork_response.json().get("data", [])
            if artwork_data:
                # Get the first ClearLogo (usually the best one)
                logo_url = f"https://www.thetvdb.com/banners/{artwork_data[0].get('fileName', '')}"
    except Exception:
        # Fallback to banner if ClearLogo fetch fails
        if series_data.get("banner"):
            logo_url = f"https://www.thetvdb.com/banners/{series_data.get('banner')}"

    # Transform episodes to match expected format
    transformed_episodes = []
    for ep in episodes_data:
        if isinstance(ep, dict):
            # Get episode image from filename field
            episode_image = None
            if ep.get("filename"):
                episode_image = f"https://www.thetvdb.com/banners/{ep.get('filename')}"

            transformed_ep = {
                "seasonNumber": ep.get("airedSeason"),
                "number": ep.get("airedEpisodeNumber"),
                "image": episode_image,  # Use episode image from filename field
                "overview": ep.get("overview")
                or ep.get("synopsis")
                or ep.get("shortDescription")
                or "",
                "episodeName": ep.get("episodeName", ""),
                "id": ep.get("id"),
                "firstAired": ep.get("firstAired"),  # Air date for release date
            }
            transformed_episodes.append(transformed_ep)

    # Transform series data to match expected format
    transformed_series = {
        "id": series_data.get("id"),
        "name": series_data.get("seriesName"),
        "overview": series_data.get("overview") or series_data.get("synopsis") or "",
        "siteRating": series_data.get("siteRating"),
        "image": poster_url,  # Use poster from artwork API
        "artworks": {"clearLogo": logo_url},  # Use logo from artwork API
        "episodes": transformed_episodes,
        # Additional metadata for EmulationStation
        "genre": series_data.get("genre", []),  # List of genres
        "network": {
            "name": series_data.get("network", "")
        },  # Network as string, convert to object
        "firstAired": series_data.get("firstAired"),  # Series first aired date
        # Note: studio information is not available in the basic series response
    }

    # Combine into expected format
    record = transformed_series

    if record:
        # Normalize siteRating (0-10) ➜ 0-1
        from mpv_scraper.utils import normalize_rating

        rating_raw = record.get("siteRating")
        record["siteRating"] = normalize_rating(rating_raw)

        _set_to_cache(cache_key, record)

    return record
