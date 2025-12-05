"""TVDB API client helpers.

Handles authentication, searching, disambiguation prompts, and fetching
extended series information.  Implements simple disk caching and honors a
small delay between HTTP requests to respect rate limits.
"""

import click
import os
import requests
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

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
    Authenticates with the TVDB API V4 and returns a bearer token.

    Raises:
        ValueError: If the TVDB_API_KEY2 is not set.
        requests.HTTPError: If the API call fails.

    Returns:
        A bearer token string.
    """
    # Try TVDB_API_KEY2 first (V4 API key), fallback to TVDB_API_KEY for backward compatibility
    api_key = os.getenv("TVDB_API_KEY2") or os.getenv("TVDB_API_KEY")
    if not api_key:
        raise ValueError("TVDB_API_KEY2 or TVDB_API_KEY environment variable not set.")

    # Check cache for a valid token first
    cached_token = _get_from_cache("tvdb_token_v4")
    if cached_token and cached_token.get("token"):
        return cached_token["token"]

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)

    # Use V4 API
    # PIN is optional - only include if TVDB_PIN is set
    pin = os.getenv("TVDB_PIN")
    payload = {"apikey": api_key}
    if pin:
        payload["pin"] = pin

    response = requests.post(
        "https://api4.thetvdb.com/v4/login", json=payload, timeout=10
    )
    response.raise_for_status()

    # V4 API returns {"data": {"token": "..."}}
    response_data = response.json()
    token = response_data.get("data", {}).get("token") or response_data.get("token")

    if not token:
        raise ValueError("No token received from TVDB API V4 login response")

    # Cache the new token
    _set_to_cache("tvdb_token_v4", {"token": token})

    return token


def search_show(name: str, token: str) -> List[Dict[str, Any]]:
    """
    Searches for a TV show by name using TVDB API V4.

    Args:
        name: The name of the show to search for.
        token: The bearer authentication token.

    Returns:
        A list of candidate shows from the API.
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {"query": name, "type": "series"}

    # Check cache
    cache_key = f"search_{name.lower().replace(' ', '_')}"
    cached_search = _get_from_cache(cache_key)
    if cached_search:
        return cached_search

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    # Use V4 API search endpoint
    response = requests.get(
        "https://api4.thetvdb.com/v4/search",
        headers=headers,
        params=params,
        timeout=10,
    )
    response.raise_for_status()

    # V4 API returns {"data": [...]} or {"data": {"results": [...]}}
    response_data = response.json()
    search_results = response_data.get("data", [])

    # Handle nested results structure if present
    if isinstance(search_results, dict) and "results" in search_results:
        search_results = search_results["results"]
    elif not isinstance(search_results, list):
        search_results = []

    _set_to_cache(cache_key, search_results)

    return search_results


def fetch_episode_artwork(episode_id: int, token: str) -> Optional[str]:
    """
    Fetch artwork for a single episode from TVDB API V4.

    Args:
        episode_id: The TVDB episode ID
        token: The bearer authentication token

    Returns:
        Image URL if found, None otherwise
    """
    headers = {"Authorization": f"Bearer {token}"}

    try:
        time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
        artwork_response = requests.get(
            f"https://api4.thetvdb.com/v4/episodes/{episode_id}/artworks",
            headers=headers,
            timeout=10,
        )

        if artwork_response.status_code == 200:
            artwork_data = artwork_response.json().get("data", [])
            if isinstance(artwork_data, dict):
                artwork_data = artwork_data.get(
                    "artworks", artwork_data.get("results", [])
                )
            if artwork_data and isinstance(artwork_data, list):
                # Look for screencap/thumbnail type artwork
                # Prefer screencap over thumbnail, as screencaps are actual episode frames
                # TVDB V4 API uses "screencap" type for episode images
                thumbnail_url = None
                
                for artwork in artwork_data:
                    artwork_type = artwork.get("type", "").lower()
                    img_path = (
                        artwork.get("image")
                        or artwork.get("fileName", "")
                        or artwork.get("url", "")
                    )

                    if not img_path:
                        continue

                    # Build full URL if needed
                    if img_path.startswith("http"):
                        full_url = img_path
                    else:
                        # TVDB V4 uses artworks.thetvdb.com/banners/v4/episode/{id}/screencap/{hash}
                        # Check if it's already a v4 path
                        if img_path.startswith("v4/"):
                            full_url = (
                                f"https://artworks.thetvdb.com/banners/{img_path}"
                            )
                        else:
                            full_url = (
                                f"https://artworks.thetvdb.com/banners/{img_path}"
                            )

                    if artwork_type == "screencap":
                        # Prefer screencap, return immediately
                        return full_url
                    elif artwork_type in ("thumbnail", "episode") and not thumbnail_url:
                        thumbnail_url = full_url

                # Fall back to thumbnail if no screencap found
                if thumbnail_url:
                    return thumbnail_url
        elif artwork_response.status_code == 429:
            # Rate limited - log and return None
            logger.debug(
                f"Rate limited (429) when fetching artwork for episode {episode_id}"
            )
            return None
        else:
            artwork_response.raise_for_status()
    except Exception as e:
        logger.debug(f"Failed to fetch artwork for episode {episode_id}: {e}")
        return None

    return None


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
        # Handle both V3 and V4 API response formats
        name = result.get("name") or result.get("seriesName") or "Unknown"
        # V4 may return year differently - try multiple fields
        year = (
            result.get("year")
            or result.get("firstAired")
            or result.get("firstAirTime")
            or "N/A"
        )
        # Extract year from date string if needed
        if isinstance(year, str) and len(year) >= 4:
            year = year[:4]
        click.echo(f"  [{i+1}] {name} ({year})")

    choice = click.prompt(
        "Enter the number of the correct show (or 0 to cancel)", type=int, default=0
    )

    if 0 < choice <= len(results):
        return results[choice - 1]

    return None


def get_series_extended(series_id: int, token: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the full extended record for a series, including all episodes using TVDB API V4.

    Args:
        series_id: The ID of the series (can be int or string like "series-71663").
        token: The bearer authentication token.

    Returns:
        A dictionary containing the full series record, or None if not found.
    """
    headers = {"Authorization": f"Bearer {token}"}

    # Handle V4 API series ID format (e.g., "series-71663" or just 71663)
    # V4 API search returns IDs in format "series-{number}", but endpoint may need just the number
    series_id_str = str(series_id)
    if series_id_str.startswith("series-"):
        # Extract numeric part from "series-71663" format
        series_id_for_url = series_id_str.replace("series-", "")
    else:
        series_id_for_url = series_id_str

    # Check cache
    cache_key = f"series_{series_id}_extended"
    cached_record = _get_from_cache(cache_key)

    # If we have cached data, check if episodes are missing artwork
    # If many episodes are missing artwork, fetch fresh data to get artwork
    if cached_record:
        episodes = cached_record.get("episodes", [])
        if episodes:
            episodes_with_images = sum(
                1
                for ep in episodes
                if ep.get("image")
                and isinstance(ep.get("image"), str)
                and ep.get("image").strip()
            )
            # If less than 20% of episodes have images, fetch fresh to get artwork
            if episodes_with_images / len(episodes) < 0.2:
                logger.info(
                    f"Only {episodes_with_images}/{len(episodes)} episodes have images in cache, fetching fresh data for artwork"
                )
                cached_record = None  # Force fresh fetch to get artwork

    if cached_record:
        return cached_record

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)

    # V4 API - get series details
    series_response = requests.get(
        f"https://api4.thetvdb.com/v4/series/{series_id_for_url}",
        headers=headers,
        timeout=10,
    )

    if series_response.status_code == 404:
        return None

    series_response.raise_for_status()
    # V4 API returns {"data": {...}}
    series_data = series_response.json().get("data", {})

    # Get episodes - V4 API uses /episodes endpoint with series filter
    episodes_response = requests.get(
        f"https://api4.thetvdb.com/v4/series/{series_id_for_url}/episodes/default",
        headers=headers,
        timeout=10,
    )

    # If default endpoint doesn't work, try alternative endpoint
    if episodes_response.status_code == 404:
        episodes_response = requests.get(
            "https://api4.thetvdb.com/v4/episodes",
            headers=headers,
            params={"series": series_id_for_url},
            timeout=10,
        )

    episodes_response.raise_for_status()
    # V4 API returns {"data": [...]} or paginated {"data": {"episodes": [...]}}
    episodes_response_data = episodes_response.json().get("data", [])

    # Handle paginated or nested structure
    if isinstance(episodes_response_data, dict):
        episodes_data = episodes_response_data.get(
            "episodes", episodes_response_data.get("results", [])
        )
    else:
        episodes_data = (
            episodes_response_data if isinstance(episodes_response_data, list) else []
        )

    # Fetch episode artwork for episodes that don't have images in the episode object
    # TVDB V4 may require fetching episode artwork separately
    episode_artwork_map = {}
    episodes_needing_artwork = []

    # First pass: identify episodes without images
    for ep in episodes_data:
        if isinstance(ep, dict) and ep.get("id"):
            # Check if episode already has an image in the response
            has_image = (
                (
                    ep.get("image")
                    and isinstance(ep.get("image"), str)
                    and ep.get("image").strip()
                )
                or (
                    ep.get("filename")
                    and isinstance(ep.get("filename"), str)
                    and ep.get("filename").strip()
                )
                or (
                    ep.get("imageUrl")
                    and isinstance(ep.get("imageUrl"), str)
                    and ep.get("imageUrl").strip()
                )
            )
            if not has_image:
                episodes_needing_artwork.append(ep.get("id"))

    # Don't fetch artwork here - it will be fetched lazily in scrape_tv_parallel()
    # only for episodes that actually exist in the user's library
    # This avoids making hundreds of API calls for episodes the user doesn't have
    if episodes_needing_artwork:
        logger.debug(
            f"Found {len(episodes_needing_artwork)}/{len(episodes_data)} episodes without artwork in API response. Artwork will be fetched lazily for episodes in user's library."
        )

    # Skip bulk artwork fetching - will be done lazily per-episode in scrape_tv_parallel()
    # This avoids making hundreds of API calls for episodes the user doesn't have
    # For Super Kitties: 138 episodes total, but user might only have 30-50 files
    # Old approach: 117 API calls (~1 minute) for all episodes
    # New approach: Only fetch artwork for episodes that exist in user's library
    episode_artwork_map = {}

    # Get image URLs from series data
    # V4 API may use different field names
    poster_url = None
    logo_url = None

    # Try to get poster from series artwork
    if series_data.get("poster"):
        poster_url = f"https://www.thetvdb.com/banners/{series_data.get('poster')}"
    elif series_data.get("image"):
        poster_url = series_data.get("image")

    # Get ClearLogo from artwork endpoint
    try:
        artwork_response = requests.get(
            f"https://api4.thetvdb.com/v4/series/{series_id_for_url}/artworks",
            headers=headers,
            params={"type": "clearlogo"},
            timeout=10,
        )
        if artwork_response.status_code == 200:
            artwork_data = artwork_response.json().get("data", [])
            # Handle nested structure
            if isinstance(artwork_data, dict):
                artwork_data = artwork_data.get(
                    "artworks", artwork_data.get("results", [])
                )
            if (
                artwork_data
                and isinstance(artwork_data, list)
                and len(artwork_data) > 0
            ):
                # V4 API may return full URL or relative path
                logo_path = artwork_data[0].get("image") or artwork_data[0].get(
                    "fileName", ""
                )
                if logo_path:
                    if logo_path.startswith("http"):
                        logo_url = logo_path
                    else:
                        logo_url = f"https://www.thetvdb.com/banners/{logo_path}"
    except Exception:
        # Fallback to banner if ClearLogo fetch fails
        if series_data.get("banner"):
            logo_url = f"https://www.thetvdb.com/banners/{series_data.get('banner')}"
        elif series_data.get("logo"):
            logo_url = series_data.get("logo")

    # Transform episodes to match expected format
    # V4 API field names may differ from V3
    transformed_episodes = []
    for ep in episodes_data:
        if isinstance(ep, dict):
            # Get episode image - V4 API may return image in different fields
            episode_image = None

            # Try direct image field first (full URL)
            if ep.get("image"):
                img_val = ep.get("image")
                if isinstance(img_val, str) and img_val.strip():
                    if img_val.startswith("http"):
                        episode_image = img_val
                    else:
                        episode_image = f"https://www.thetvdb.com/banners/{img_val}"

            # Try filename field
            elif ep.get("filename"):
                filename_val = ep.get("filename")
                if isinstance(filename_val, str) and filename_val.strip():
                    episode_image = f"https://www.thetvdb.com/banners/{filename_val}"

            # V4 API may have imageUrl field
            elif ep.get("imageUrl"):
                img_url_val = ep.get("imageUrl")
                if isinstance(img_url_val, str) and img_url_val.strip():
                    episode_image = img_url_val

            # V4 API may have artwork/image in nested structure
            elif ep.get("artwork") and isinstance(ep.get("artwork"), dict):
                artwork = ep.get("artwork")
                if artwork.get("image"):
                    img_val = artwork.get("image")
                    if isinstance(img_val, str) and img_val.strip():
                        if img_val.startswith("http"):
                            episode_image = img_val
                        else:
                            episode_image = f"https://www.thetvdb.com/banners/{img_val}"

            # Use artwork fetched from separate endpoint if available
            if (
                not episode_image
                and ep.get("id")
                and ep.get("id") in episode_artwork_map
            ):
                episode_image = episode_artwork_map[ep.get("id")]

            # V4 API uses different field names - try both V3 and V4 formats
            season_num = (
                ep.get("seasonNumber") or ep.get("airedSeason") or ep.get("season")
            )
            episode_num = (
                ep.get("number") or ep.get("airedEpisodeNumber") or ep.get("episode")
            )
            overview = (
                ep.get("overview")
                or ep.get("synopsis")
                or ep.get("shortDescription")
                or ep.get("description")
                or ""
            )
            episode_name = ep.get("name") or ep.get("episodeName") or ""
            first_aired = ep.get("firstAired") or ep.get("aired") or ep.get("airDate")

            transformed_ep = {
                "seasonNumber": season_num,
                "number": episode_num,
                "image": episode_image,
                "overview": overview,
                "episodeName": episode_name,
                "id": ep.get("id"),
                "firstAired": first_aired,
            }
            transformed_episodes.append(transformed_ep)

    # Transform series data to match expected format
    # V4 API field names may differ
    series_name = series_data.get("name") or series_data.get("seriesName") or ""
    overview = (
        series_data.get("overview")
        or series_data.get("synopsis")
        or series_data.get("description")
        or ""
    )
    rating = (
        series_data.get("score")
        or series_data.get("siteRating")
        or series_data.get("rating")
    )
    first_aired = (
        series_data.get("firstAired")
        or series_data.get("firstAirTime")
        or series_data.get("year")
    )

    # Handle genres - V4 may return as list of strings or list of objects
    genres = []
    if series_data.get("genres"):
        genres_list = series_data.get("genres", [])
        if isinstance(genres_list, list):
            genres = [
                g.get("name", g) if isinstance(g, dict) else g for g in genres_list
            ]
    elif series_data.get("genre"):
        genres = series_data.get("genre", [])

    # Handle network - V4 may return as object or string
    network_name = ""
    if series_data.get("network"):
        network_obj = series_data.get("network")
        if isinstance(network_obj, dict):
            network_name = network_obj.get("name", "")
        else:
            network_name = str(network_obj)

    transformed_series = {
        "id": series_data.get("id"),
        "name": series_name,
        "overview": overview,
        "siteRating": rating,
        "image": poster_url,
        "artworks": {"clearLogo": logo_url},
        "episodes": transformed_episodes,
        "genre": genres,
        "network": {"name": network_name},
        "firstAired": first_aired,
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
