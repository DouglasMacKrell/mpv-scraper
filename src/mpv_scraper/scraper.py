"""Scraper helpers for live metadata/artwork download.

Currently implements `scrape_tv` (Sprint 10.1).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mpv_scraper.images import download_image, download_marquee
from mpv_scraper.utils import normalize_rating

# Lazily import tvdb and tmdb to keep top-level deps light and simplify test patching.
import mpv_scraper.tvdb as tvdb  # noqa: WPS433 – runtime import is intentional
import mpv_scraper.tmdb as tmdb  # noqa: WPS433 – runtime import is intentional


CACHE_FILE = ".scrape_cache.json"


def _safe_write_json(path: Path, data: Any) -> None:
    """Write *data* as JSON with pretty indentation."""

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def scrape_tv(show_dir: Path) -> None:  # pragma: no cover – covered via integration
    """Scrape a TV show directory.

    Parameters
    ----------
    show_dir
        Directory containing episode media files (one level deep).
    """

    token = "token"  # In tests the token value is unimportant / patched

    # 1. Look up series
    search_results = tvdb.search_show(show_dir.name, token)
    if not search_results:
        raise RuntimeError(f"TVDB could not find series for {show_dir.name!r}")
    series_id = search_results[0]["id"]

    record = tvdb.get_series_extended(series_id, token)
    if not record:
        raise RuntimeError(f"Failed to fetch extended record for id {series_id}")

    # Normalise rating if present
    if "siteRating" in record:
        record["siteRating"] = normalize_rating(record["siteRating"])

    images_dir = show_dir / "images"
    images_dir.mkdir(exist_ok=True, parents=True)

    # 2. Poster
    poster_url: str | None = record.get("image")
    if poster_url:
        try:
            download_image(poster_url, images_dir / "poster.png")
        except Exception:
            # Create placeholder if poster download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / "poster.png")

    # 3. Logo (clearLogo)
    logo_url: str | None = (
        record.get("artworks", {}).get("clearLogo") if record.get("artworks") else None
    )
    if logo_url:
        try:
            download_marquee(logo_url, images_dir / "logo.png")
        except Exception:
            # Create placeholder if logo download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / "logo.png")

    # 4. Episode images (best-effort)
    for ep in record.get("episodes", []):
        season = ep.get("seasonNumber")
        number = ep.get("number")
        img_url = ep.get("image")
        if not (season and number and img_url):
            continue
        dest = images_dir / f"S{season:02d}E{number:02d}.png"
        try:
            download_image(img_url, dest)
        except Exception:
            # Create placeholder if episode image download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(dest)

    # 5. Cache raw record for later generate step
    _safe_write_json(show_dir / CACHE_FILE, record)


def scrape_movie(
    movie_path: Path,
) -> None:  # pragma: no cover – covered via integration
    """Scrape a movie file.

    Parameters
    ----------
    movie_path
        Path to the movie media file.
    """
    from mpv_scraper.parser import parse_movie_filename

    # 1. Parse movie filename to extract title and year
    movie_meta = parse_movie_filename(movie_path.name)
    if not movie_meta:
        raise RuntimeError(f"Could not parse movie filename: {movie_path.name!r}")

    # 2. Search for movie in TMDB
    search_results = tmdb.search_movie(movie_meta.title, movie_meta.year)
    if not search_results:
        raise RuntimeError(f"TMDB could not find movie for {movie_meta.title!r}")
    movie_id = search_results[0]["id"]

    # 3. Get detailed movie information
    record = tmdb.get_movie_details(movie_id)
    if not record:
        raise RuntimeError(f"Failed to fetch details for movie id {movie_id}")

    # 4. Create images directory
    images_dir = movie_path.parent / "images"
    images_dir.mkdir(exist_ok=True, parents=True)

    # 5. Download poster
    poster_path = record.get("poster_path")
    if poster_path:
        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
        try:
            download_image(poster_url, images_dir / f"{movie_meta.title}.png")
        except Exception:
            # Create placeholder if poster download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / f"{movie_meta.title}.png")

    # 6. Download logo (from collection if available)
    logo_url = None
    collection = record.get("belongs_to_collection", {})
    if collection and collection.get("poster_path"):
        logo_url = f"https://image.tmdb.org/t/p/original{collection['poster_path']}"

    if logo_url:
        try:
            download_marquee(logo_url, images_dir / "logo.png")
        except Exception:
            # Create placeholder if logo download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / "logo.png")

    # 7. Cache raw record for later generate step
    _safe_write_json(movie_path.parent / CACHE_FILE, record)
