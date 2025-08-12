"""TVmaze client (fallback for TV metadata).

Endpoints used (per TVmaze docs):
- Search: GET https://api.tvmaze.com/search/shows?q={query}
- Episodes (by show id): GET https://api.tvmaze.com/shows/{id}/episodes

Rate limiting: TVmaze requests fair use; we apply a small delay per request
to be polite and cache results to minimize repeated calls.
"""

from __future__ import annotations

from html import unescape
import re
import time
from typing import Any, Dict, List, Optional

import requests

from .tvdb import _get_from_cache, _set_to_cache, API_RATE_LIMIT_DELAY_SECONDS


def _strip_html(s: Optional[str]) -> str:
    if not s:
        return ""
    # Remove HTML tags and unescape entities
    text = re.sub(r"<[^>]+>", "", s)
    return unescape(text).strip()


def search_show(name: str) -> List[Dict[str, Any]]:
    """Search TVmaze for shows by name.

    Returns a simplified list: [{id, name, premiered, rating, image}].
    """
    cache_key = f"tvmaze_search_{name.lower().replace(' ', '_')}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    resp = requests.get(
        "https://api.tvmaze.com/search/shows", params={"q": name}, timeout=10
    )
    resp.raise_for_status()
    data = resp.json() or []

    results: List[Dict[str, Any]] = []
    for item in data:
        show = item.get("show", {}) if isinstance(item, dict) else {}
        results.append(
            {
                "id": show.get("id"),
                "name": show.get("name"),
                "premiered": show.get("premiered"),
                "siteRating": (show.get("rating") or {}).get("average"),
                "image": (show.get("image") or {}).get("medium"),
            }
        )

    _set_to_cache(cache_key, results)
    return results


def get_show_episodes(show_id: int) -> List[Dict[str, Any]]:
    """Fetch episodes for a TVmaze show id; map to our internal episode structure."""
    cache_key = f"tvmaze_show_{show_id}_episodes"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    resp = requests.get(f"https://api.tvmaze.com/shows/{show_id}/episodes", timeout=10)
    resp.raise_for_status()
    data = resp.json() or []

    episodes: List[Dict[str, Any]] = []
    for ep in data:
        if not isinstance(ep, dict):
            continue
        episodes.append(
            {
                "seasonNumber": ep.get("season"),
                "number": ep.get("number"),
                "episodeName": ep.get("name"),
                "overview": _strip_html(ep.get("summary")),
                "firstAired": ep.get("airdate"),
                "image": (ep.get("image") or {}).get("medium"),
                "id": ep.get("id"),
            }
        )

    _set_to_cache(cache_key, episodes)
    return episodes
