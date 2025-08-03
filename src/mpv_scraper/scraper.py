"""Scraper helpers for live metadata/artwork download.

Implements `scrape_tv` and `scrape_movie` with robust error handling and retry logic.
Includes graceful fallbacks for missing artwork and network failures.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mpv_scraper.images import download_image, download_marquee
from mpv_scraper.utils import normalize_rating

# Lazily import tvdb and tmdb to keep top-level deps light and simplify test patching.
import mpv_scraper.tvdb as tvdb  # noqa: WPS433 – runtime import is intentional
import mpv_scraper.tmdb as tmdb  # noqa: WPS433 – runtime import is intentional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_FILE = ".scrape_cache.json"


def _safe_write_json(path: Path, data: Any) -> None:
    """Write *data* as JSON with pretty indentation."""

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def scrape_tv(
    show_dir: Path, transaction_logger=None
) -> None:  # pragma: no cover – covered via integration
    """Scrape a TV show directory.

    Parameters
    ----------
    show_dir
        Directory containing episode media files (one level deep).
    transaction_logger
        Optional transaction logger for undo operations.
    """

    token = tvdb.authenticate_tvdb()
    headers = {"Authorization": f"Bearer {token}"}

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
    if transaction_logger:
        transaction_logger.log_create(images_dir)

    # 2. Poster
    poster_url: str | None = record.get("image")
    if poster_url:
        try:
            logger.info(f"Downloading poster for {show_dir.name}")
            download_image(poster_url, images_dir / "poster.png", headers)
            if transaction_logger:
                transaction_logger.log_create(images_dir / "poster.png")
            logger.info(f"✓ Downloaded poster for {show_dir.name}")
        except Exception as e:
            logger.warning(f"Failed to download poster for {show_dir.name}: {e}")
            # Create placeholder if poster download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / "poster.png")
            if transaction_logger:
                transaction_logger.log_create(images_dir / "poster.png")
            logger.info(f"Created placeholder poster for {show_dir.name}")

    # 3. Logo (clearLogo)
    logo_url: str | None = (
        record.get("artworks", {}).get("clearLogo") if record.get("artworks") else None
    )
    if logo_url:
        try:
            logger.info(f"Downloading logo for {show_dir.name}")
            download_marquee(logo_url, images_dir / "logo.png", headers)
            if transaction_logger:
                transaction_logger.log_create(images_dir / "logo.png")
            logger.info(f"✓ Downloaded logo for {show_dir.name}")
        except Exception as e:
            logger.warning(f"Failed to download logo for {show_dir.name}: {e}")
            # Create placeholder if logo download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / "logo.png")
            if transaction_logger:
                transaction_logger.log_create(images_dir / "logo.png")
            logger.info(f"Created placeholder logo for {show_dir.name}")

    # 4. Episode images (best-effort)
    episode_count = 0
    episodes_with_images = 0
    total_episodes = len(record.get("episodes", []))

    for ep in record.get("episodes", []):
        season = ep.get("seasonNumber")
        number = ep.get("number")
        img_url = ep.get("image")

        if img_url:
            episodes_with_images += 1

        if not (season and number and img_url):
            continue
        dest = images_dir / f"S{season:02d}E{number:02d}.png"
        try:
            download_image(img_url, dest, headers)
            if transaction_logger:
                transaction_logger.log_create(dest)
            episode_count += 1
        except Exception as e:
            logger.warning(
                f"Failed to download episode image S{season:02d}E{number:02d}: {e}"
            )
            # Create placeholder if episode image download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(dest)
            if transaction_logger:
                transaction_logger.log_create(dest)

    logger.info(
        f"Total episodes: {total_episodes}, Episodes with images: {episodes_with_images}, Downloaded: {episode_count} episode images for {show_dir.name}"
    )

    # 5. Cache raw record for later generate step
    _safe_write_json(show_dir / CACHE_FILE, record)
    if transaction_logger:
        transaction_logger.log_create(show_dir / CACHE_FILE)
    logger.info(f"Cached metadata for {show_dir.name}")


def scrape_movie(
    movie_path: Path, transaction_logger=None
) -> None:  # pragma: no cover – covered via integration
    """Scrape a movie file.

    Parameters
    ----------
    movie_path
        Path to the movie media file.
    transaction_logger
        Optional transaction logger for undo operations.
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
    if transaction_logger:
        transaction_logger.log_create(images_dir)

    # 5. Download poster
    poster_url = record.get("poster_url")
    if poster_url:
        try:
            logger.info(f"Downloading poster for {movie_meta.title}")
            # Use filename stem for consistency with generate command
            download_image(poster_url, images_dir / f"{movie_path.stem}.png")
            if transaction_logger:
                transaction_logger.log_create(images_dir / f"{movie_path.stem}.png")
            logger.info(f"✓ Downloaded poster for {movie_meta.title}")
        except Exception as e:
            logger.warning(f"Failed to download poster for {movie_meta.title}: {e}")
            # Create placeholder if poster download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / f"{movie_path.stem}.png")
            if transaction_logger:
                transaction_logger.log_create(images_dir / f"{movie_path.stem}.png")
            logger.info(f"Created placeholder poster for {movie_meta.title}")

    # 6. Download logo (alpha logo for overlay)
    logo_url = record.get("logo_url")
    if logo_url:
        try:
            logger.info(f"Downloading logo for {movie_meta.title}")
            # Use unique logo name per movie
            download_marquee(logo_url, images_dir / f"{movie_path.stem}-logo.png")
            if transaction_logger:
                transaction_logger.log_create(
                    images_dir / f"{movie_path.stem}-logo.png"
                )
            logger.info(f"✓ Downloaded logo for {movie_meta.title}")
        except Exception as e:
            logger.warning(f"Failed to download logo for {movie_meta.title}: {e}")
            # Don't create placeholder logo if download fails - just skip it
            logger.info(f"Skipped logo for {movie_meta.title}")

    # 7. Cache raw record for later generate step
    # Store in standard .scrape_cache.json file for consistency with TV shows
    movie_cache_file = movie_path.parent / ".scrape_cache.json"
    _safe_write_json(movie_cache_file, record)
    if transaction_logger:
        transaction_logger.log_create(movie_cache_file)
    logger.info(f"Cached metadata for {movie_meta.title}")
