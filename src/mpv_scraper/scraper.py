"""Scraper helpers for live metadata/artwork download.

Implements `scrape_tv` and `scrape_movie` with robust error handling and retry logic.
Includes graceful fallbacks for missing artwork and network failures.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Union, Optional, Dict

from mpv_scraper.images import download_image, download_marquee
from mpv_scraper.utils import normalize_rating

# Lazily import tvdb and tmdb to keep top-level deps light and simplify test patching.
import mpv_scraper.tvdb as tvdb  # noqa: WPS433 – runtime import is intentional
import mpv_scraper.tmdb as tmdb  # noqa: WPS433 – runtime import is intentional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_FILE = ".scrape_cache.json"


def _try_tmdb_episode_image(
    show_title: str, season: int, episode: int
) -> Optional[str]:
    """Try to get episode image from TMDB."""
    try:
        import os
        import requests

        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            return None

        # Search for TV show on TMDB
        search_results = requests.get(
            "https://api.themoviedb.org/3/search/tv",
            params={"api_key": api_key, "query": show_title, "language": "en-US"},
            timeout=10,
        ).json()

        if not search_results.get("results"):
            return None

        # Get the first result
        show_id = search_results["results"][0]["id"]

        # Get episode images
        episode_images = requests.get(
            f"https://api.themoviedb.org/3/tv/{show_id}/season/{season}/episode/{episode}/images",
            params={"api_key": api_key, "include_image_language": "en,null"},
            timeout=10,
        ).json()

        # Return the first still image if available
        if episode_images.get("stills"):
            return f"https://image.tmdb.org/t/p/original{episode_images['stills'][0]['file_path']}"

        return None

    except Exception as e:
        logger.debug(f"TMDB episode image lookup failed: {e}")
        return None


def _try_tmdb_season_images(show_title: str, max_season: int) -> Dict[str, str]:
    """Bulk fetch all episode images for a season from TMDB to avoid API bombing."""
    try:
        import os
        import requests

        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            return {}

        # Search for TV show on TMDB
        search_results = requests.get(
            "https://api.themoviedb.org/3/search/tv",
            params={"api_key": api_key, "query": show_title, "language": "en-US"},
            timeout=10,
        ).json()

        if not search_results.get("results"):
            return {}

        # Get the first result
        show_id = search_results["results"][0]["id"]

        episode_images = {}

        # Fetch all episodes for the season
        season_details = requests.get(
            f"https://api.themoviedb.org/3/tv/{show_id}/season/{max_season}",
            params={"api_key": api_key, "language": "en-US"},
            timeout=10,
        ).json()

        if not season_details.get("episodes"):
            return {}

        # Extract episode images from the season response (no additional API calls needed!)
        for episode in season_details["episodes"]:
            episode_num = episode.get("episode_number")
            still_path = episode.get("still_path")
            if episode_num and still_path:
                episode_key = f"S{max_season:02d}E{episode_num:02d}"
                episode_images[episode_key] = (
                    f"https://image.tmdb.org/t/p/original{still_path}"
                )

        return episode_images

    except Exception as e:
        logger.debug(f"TMDB season images lookup failed: {e}")
        return {}


def _safe_write_json(path: Path, data: Any) -> None:
    """Write *data* as JSON with pretty indentation."""

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def scrape_tv(
    show_dir: Path, transaction_logger=None, top_images_dir: Path = None
) -> None:  # pragma: no cover – covered via integration
    """Scrape metadata for a TV show directory."""
    # Use top-level images directory if provided, otherwise show-specific
    if top_images_dir:
        images_dir = top_images_dir
    else:
        images_dir = show_dir / "images"
        images_dir.mkdir(exist_ok=True, parents=True)
        if transaction_logger:
            transaction_logger.log_create(images_dir)

    # Try TVDB first
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

    # Check if TVDB has poor logo data and try TMDB fallback
    has_good_logo = bool(record.get("artworks", {}).get("clearLogo"))
    if not has_good_logo:
        logger.info(f"TVDB has no logo for {show_dir.name}, trying TMDB fallback...")
        try:
            from .fallback import FallbackScraper

            fallback_scraper = FallbackScraper()
            tmdb_record = fallback_scraper._try_tmdb_for_tv_show(show_dir.name)
            if tmdb_record and tmdb_record.get("artworks", {}).get("clearLogo"):
                logger.info(f"✓ TMDB fallback found logo for {show_dir.name}")
                # Merge TMDB logo into TVDB record
                if not record.get("artworks"):
                    record["artworks"] = {}
                record["artworks"]["clearLogo"] = tmdb_record["artworks"]["clearLogo"]

                # Also merge studio data for publisher field
                if tmdb_record.get("studio"):
                    record["studio"] = tmdb_record["studio"]

                record["source"] = "tvdb_with_tmdb_logo_fallback"
            else:
                logger.info(f"TMDB fallback also has no logo for {show_dir.name}")
        except Exception as e:
            logger.warning(f"TMDB fallback failed for {show_dir.name}: {e}")

    # Normalise rating if present
    if "siteRating" in record:
        record["siteRating"] = normalize_rating(record["siteRating"])

    # 2. Poster
    poster_url: Union[str, None] = record.get("image")
    if poster_url:
        try:
            logger.info(f"Downloading poster for {show_dir.name}")
            # Use show name for poster
            poster_path = images_dir / f"{show_dir.name}-poster.png"
            download_image(poster_url, poster_path, headers)
            if transaction_logger:
                transaction_logger.log_create(poster_path)
            logger.info(f"✓ Downloaded poster for {show_dir.name}")
        except Exception as e:
            logger.warning(f"Failed to download poster for {show_dir.name}: {e}")
            # Create placeholder if poster download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(poster_path)
            if transaction_logger:
                transaction_logger.log_create(poster_path)
            logger.info(f"Created placeholder poster for {show_dir.name}")

    # 3. Logo (clearLogo) - duplicate across marquee and box for theme compatibility
    logo_url: Union[str, None] = (
        record.get("artworks", {}).get("clearLogo") if record.get("artworks") else None
    )
    if logo_url:
        try:
            logger.info(f"Downloading logo for {show_dir.name}")
            # Use show name for logo
            logo_path = images_dir / f"{show_dir.name}-logo.png"
            marquee_path = images_dir / f"{show_dir.name}-marquee.png"
            box_path = images_dir / f"{show_dir.name}-box.png"

            download_marquee(logo_url, logo_path, headers)
            if transaction_logger:
                transaction_logger.log_create(logo_path)
            logger.info(f"✓ Downloaded logo for {show_dir.name}")

            # Duplicate logo for marquee and box fields (theme compatibility)
            import shutil

            shutil.copy2(logo_path, marquee_path)
            if transaction_logger:
                transaction_logger.log_create(marquee_path)
            shutil.copy2(logo_path, box_path)
            if transaction_logger:
                transaction_logger.log_create(box_path)
            logger.info("✓ Duplicated logo for marquee and box fields")
        except Exception as e:
            logger.warning(f"Failed to download logo for {show_dir.name}: {e}")
            # Create placeholder if logo download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(logo_path)
            if transaction_logger:
                transaction_logger.log_create(logo_path)
            create_placeholder_png(marquee_path)
            if transaction_logger:
                transaction_logger.log_create(marquee_path)
            create_placeholder_png(box_path)
            if transaction_logger:
                transaction_logger.log_create(box_path)
            logger.info(f"Created placeholder logos for {show_dir.name}")

    # 4. Episode images - handle anthology shows properly
    episode_count = 0
    episodes_with_images = 0
    total_episodes = len(record.get("episodes", []))

    # First, analyze the actual files to understand the structure
    from mpv_scraper.parser import parse_tv_filename

    # Get all episode files and their spans
    episode_files = []
    for file_path in show_dir.glob("*.mp4"):
        meta = parse_tv_filename(file_path.name)
        if meta:
            episode_files.append((file_path, meta))

    # Also check for .mkv files (Scooby Doo uses .mkv)
    for file_path in show_dir.glob("*.mkv"):
        meta = parse_tv_filename(file_path.name)
        if meta:
            episode_files.append((file_path, meta))

    # Sort by season and episode for consistent ordering
    episode_files.sort(key=lambda x: (x[1].season, x[1].start_ep))

    logger.info(f"Found {len(episode_files)} episode files for {show_dir.name}")

    # Bulk fetch TMDB episode images for all seasons to avoid API bombing
    tmdb_episode_images = {}
    all_seasons = list(
        set([meta.season for _, meta in episode_files])
    )  # All unique seasons
    if all_seasons and episode_files:
        try:
            # Use the parsed show name from the first episode file (more accurate than directory name)
            parsed_show_name = episode_files[0][1].show
            logger.info(
                f"Using parsed show name for TMDB bulk fetch: '{parsed_show_name}'"
            )
            # Fetch all seasons in bulk
            for season in all_seasons:
                season_images = _try_tmdb_season_images(parsed_show_name, season)
                tmdb_episode_images.update(season_images)
            logger.info(
                f"Bulk fetched {len(tmdb_episode_images)} TMDB episode images for {parsed_show_name} (seasons {all_seasons})"
            )
        except Exception as e:
            logger.debug(f"TMDB bulk fetch failed for {parsed_show_name}: {e}")

    # Batch collect all images to download
    downloads_to_process = []

    for file_path, meta in episode_files:
        # Look for API image for the first episode in the span
        target_season = meta.season
        target_episode = meta.start_ep

        # Try TVDB first
        api_episode = None
        img_url = None
        source = "TVDB"

        # Find matching episode in TVDB data
        for ep in record.get("episodes", []):
            if (
                ep.get("seasonNumber") == target_season
                and ep.get("number") == target_episode
            ):
                api_episode = ep
                break

        if api_episode and api_episode.get("image"):
            img_url = api_episode["image"]
            episodes_with_images += 1
        else:
            # Try TMDB from bulk-fetched data
            tmdb_key = f"S{target_season:02d}E{target_episode:02d}"
            if tmdb_key in tmdb_episode_images:
                img_url = tmdb_episode_images[tmdb_key]
                source = "TMDB"
                episodes_with_images += 1
                logger.info(f"Found TMDB episode image for {tmdb_key}")
            else:
                logger.debug(
                    f"TMDB key {tmdb_key} not found in bulk cache (cache has {len(tmdb_episode_images)} items)"
                )

        if img_url:
            # Create the span filename (e.g., "S04E01-E02" for span)
            if meta.end_ep != meta.start_ep:
                span_name = f"S{meta.season:02d}E{meta.start_ep:02d}-E{meta.end_ep:02d}"
            else:
                span_name = f"S{meta.season:02d}E{meta.start_ep:02d}"

            dest = images_dir / f"{show_dir.name} - {span_name}-image.png"
            downloads_to_process.append(
                (img_url, dest, source, span_name, target_season, target_episode)
            )

    # Batch download all images
    if downloads_to_process:
        logger.info(
            f"Downloading {len(downloads_to_process)} episode images for {show_dir.name}..."
        )

        for (
            img_url,
            dest,
            source,
            span_name,
            target_season,
            target_episode,
        ) in downloads_to_process:
            try:
                download_image(img_url, dest, headers)
                if transaction_logger:
                    transaction_logger.log_create(dest)
                episode_count += 1
            except Exception as e:
                logger.warning(f"Failed to download episode image {span_name}: {e}")

        logger.info(f"✓ Downloaded {episode_count} episode images for {show_dir.name}")

    logger.info(
        f"Total episodes: {total_episodes}, Episodes with images: {episodes_with_images}, Downloaded: {episode_count} episode images for {show_dir.name}"
    )

    # 5. Cache the record
    cache_path = show_dir / CACHE_FILE
    _safe_write_json(cache_path, record)
    if transaction_logger:
        transaction_logger.log_create(cache_path)
    logger.info(f"Cached metadata for {show_dir.name}")


def scrape_movie(
    movie_path: Path, transaction_logger=None, top_images_dir: Path = None
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

    # 4. Use top-level images directory if provided, otherwise create local images directory
    if top_images_dir:
        images_dir = top_images_dir
    else:
        images_dir = movie_path.parent / "images"
        images_dir.mkdir(exist_ok=True, parents=True)
        if transaction_logger:
            transaction_logger.log_create(images_dir)

    # 5. Download poster
    poster_url = record.get("poster_url")
    if poster_url:
        try:
            logger.info(f"Downloading poster for {movie_meta.title}")
            # Use proper EmulationStation naming convention
            download_image(poster_url, images_dir / f"{movie_path.stem}-image.png")
            if transaction_logger:
                transaction_logger.log_create(
                    images_dir / f"{movie_path.stem}-image.png"
                )
            logger.info(f"✓ Downloaded poster for {movie_meta.title}")
        except Exception as e:
            logger.warning(f"Failed to download poster for {movie_meta.title}: {e}")
            # Create placeholder if poster download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / f"{movie_path.stem}-image.png")
            if transaction_logger:
                transaction_logger.log_create(
                    images_dir / f"{movie_path.stem}-image.png"
                )
            logger.info(f"Created placeholder poster for {movie_meta.title}")

    # 6. Download logo/marquee
    logo_url = record.get("logo_url")
    if logo_url:
        try:
            logger.info(f"Downloading logo for {movie_meta.title}")
            # Use proper EmulationStation naming convention
            download_marquee(logo_url, images_dir / f"{movie_path.stem}-marquee.png")
            if transaction_logger:
                transaction_logger.log_create(
                    images_dir / f"{movie_path.stem}-marquee.png"
                )
            logger.info(f"✓ Downloaded logo for {movie_meta.title}")
        except Exception as e:
            logger.warning(f"Failed to download logo for {movie_meta.title}: {e}")
            # Create placeholder if logo download fails
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / f"{movie_path.stem}-marquee.png")
            if transaction_logger:
                transaction_logger.log_create(
                    images_dir / f"{movie_path.stem}-marquee.png"
                )
            logger.info(f"Created placeholder logo for {movie_meta.title}")

    # 7. Create thumbnail version (use same logo as marquee, not placeholder)
    if logo_url:
        try:
            # Copy the marquee logo to thumbnail
            import shutil

            marquee_path = images_dir / f"{movie_path.stem}-marquee.png"
            thumb_path = images_dir / f"{movie_path.stem}-thumb.png"
            if marquee_path.exists():
                shutil.copy2(marquee_path, thumb_path)
                if transaction_logger:
                    transaction_logger.log_create(thumb_path)
                logger.info(
                    f"Created thumbnail for {movie_meta.title} (copied from marquee)"
                )
            else:
                # Fallback to placeholder only if marquee doesn't exist
                from mpv_scraper.images import create_placeholder_png

                create_placeholder_png(thumb_path)
                if transaction_logger:
                    transaction_logger.log_create(thumb_path)
                logger.info(f"Created placeholder thumbnail for {movie_meta.title}")
        except Exception as e:
            logger.warning(f"Failed to create thumbnail for {movie_meta.title}: {e}")
    else:
        # Only create placeholder if no logo was downloaded
        try:
            from mpv_scraper.images import create_placeholder_png

            create_placeholder_png(images_dir / f"{movie_path.stem}-thumb.png")
            if transaction_logger:
                transaction_logger.log_create(
                    images_dir / f"{movie_path.stem}-thumb.png"
                )
            logger.info(f"Created placeholder thumbnail for {movie_meta.title}")
        except Exception as e:
            logger.warning(f"Failed to create thumbnail for {movie_meta.title}: {e}")

    # 7. Cache raw record for later generate step
    # Store in standard .scrape_cache.json file for consistency with TV shows
    movie_cache_file = movie_path.parent / ".scrape_cache.json"
    _safe_write_json(movie_cache_file, record)
    if transaction_logger:
        transaction_logger.log_create(movie_cache_file)
    logger.info(f"Cached metadata for {movie_meta.title}")
