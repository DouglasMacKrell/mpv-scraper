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

    response = requests.post(
        "https://api4.thetvdb.com/v4/login", json={"apikey": api_key}, timeout=10
    )
    response.raise_for_status()
    token = response.json()["data"]["token"]

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
    params = {"query": name}

    # Check cache
    cache_key = f"search_{name.lower().replace(' ', '_')}"
    cached_search = _get_from_cache(cache_key)
    if cached_search:
        return cached_search

    response = requests.get(
        "https://api4.thetvdb.com/v4/search", headers=headers, params=params, timeout=10
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
