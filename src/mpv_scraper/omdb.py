"""OMDb client (movie fallback).

Endpoints (per OMDb docs):
- Search by title: GET http://www.omdbapi.com/?s=Title&y=Year&type=movie&apikey=KEY
- Title by IMDb ID: GET http://www.omdbapi.com/?i=tt1234567&plot=full&apikey=KEY

Rules:
- Use `apikey` query parameter from environment variable `OMDB_API_KEY`.
- Respect HTTP 200 with error payloads (Response['Response'] == 'False').
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests

from .tvdb import _get_from_cache, _set_to_cache, API_RATE_LIMIT_DELAY_SECONDS
from .utils import normalize_rating


BASE_URL = "http://www.omdbapi.com/"


def _apikey() -> str:
    key = os.getenv("OMDB_API_KEY")
    if not key:
        raise ValueError("OMDB_API_KEY environment variable not set.")
    return key


def search_movie(title: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
    cache_key = f"omdb_search_{title.lower().replace(' ', '_')}_{year or 'any'}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    params: Dict[str, Any] = {"s": title, "type": "movie", "apikey": _apikey()}
    if year:
        params["y"] = year

    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json() or {}
    if str(data.get("Response", "True")) == "False":
        _set_to_cache(cache_key, [])
        return []

    results: List[Dict[str, Any]] = []
    for item in data.get("Search", []) or []:
        if not isinstance(item, dict):
            continue
        title_str = item.get("Title")
        year_str = item.get("Year")
        try:
            year_int = int(year_str) if year_str and year_str.isdigit() else None
        except Exception:
            year_int = None
        results.append(
            {
                "id": item.get("imdbID"),
                "title": title_str,
                "year": year_int,
                "poster_url": item.get("Poster"),
            }
        )

    _set_to_cache(cache_key, results)
    return results


def get_movie_details(imdb_id: str) -> Dict[str, Any]:
    cache_key = f"omdb_details_{imdb_id}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    params = {"i": imdb_id, "plot": "full", "apikey": _apikey()}
    time.sleep(API_RATE_LIMIT_DELAY_SECONDS)
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json() or {}
    if str(data.get("Response", "True")) == "False":
        raise ValueError(data.get("Error", "OMDb lookup failed"))

    # Map to our internal structure
    title = data.get("Title")
    plot = data.get("Plot") or ""
    rating_raw = 0.0
    try:
        rating_raw = float(data.get("imdbRating", 0.0))
    except Exception:
        rating_raw = 0.0

    mapped = {
        "id": data.get("imdbID"),
        "title": title,
        "overview": plot,
        "vote_average": normalize_rating(rating_raw),  # imdb 0-10 -> 0-1
        "poster_url": data.get("Poster"),
        "release_date": data.get("Released"),
    }

    _set_to_cache(cache_key, mapped)
    return mapped
