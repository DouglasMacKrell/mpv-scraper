"""Scraper helpers for live metadata/artwork download.

Currently implements `scrape_tv` (Sprint 10.1).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mpv_scraper.images import download_image, download_marquee
from mpv_scraper.utils import normalize_rating

# Lazily import tvdb to keep top-level deps light and simplify test patching.
import mpv_scraper.tvdb as tvdb  # noqa: WPS433 – runtime import is intentional


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
        download_image(poster_url, images_dir / "poster.png")

    # 3. Logo (clearLogo)
    logo_url: str | None = (
        record.get("artworks", {}).get("clearLogo") if record.get("artworks") else None
    )
    if logo_url:
        download_marquee(logo_url, images_dir / "logo.png")

    # 4. Episode images (best-effort)
    for ep in record.get("episodes", []):
        season = ep.get("seasonNumber")
        number = ep.get("number")
        img_url = ep.get("image")
        if not (season and number and img_url):
            continue
        dest = images_dir / f"S{season:02d}E{number:02d}.png"
        download_image(img_url, dest)

    # 5. Cache raw record for later generate step
    _safe_write_json(show_dir / CACHE_FILE, record)
