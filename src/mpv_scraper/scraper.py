"""Scraper helpers for live metadata/artwork download.

Implements `scrape_tv` and `scrape_movie` with robust error handling and retry logic.
Includes graceful fallbacks for missing artwork and network failures.
Supports parallel downloads for improved performance.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Union, Optional, Dict, List, Tuple
import threading
from dataclasses import dataclass
import queue

from mpv_scraper.images import download_image, download_marquee
from mpv_scraper.utils import normalize_rating

# Lazily import tvdb and tmdb to keep top-level deps light and simplify test patching.
import mpv_scraper.tvdb as tvdb  # noqa: WPS433 – runtime import is intentional
import mpv_scraper.tmdb as tmdb  # noqa: WPS433 – runtime import is intentional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_FILE = ".scrape_cache.json"


@dataclass
class DownloadTask:
    """Represents a single download task for parallel processing."""

    url: str
    dest_path: Path
    source: str  # "TVDB", "TMDB", or "SCREENSHOT"
    show_name: str
    episode_info: str
    headers: Optional[Dict[str, str]] = None
    video_path: Optional[Path] = None  # For screenshot generation


class ParallelDownloadManager:
    """Manages parallel downloads across different sources."""

    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.download_queue = queue.Queue()
        self.results = []
        self.lock = threading.Lock()

    def add_task(self, task: DownloadTask):
        """Add a download task to the queue."""
        self.download_queue.put(task)

    def _download_worker(self):
        """Worker thread for downloading images."""
        while True:
            try:
                task = self.download_queue.get(timeout=1)
                if task is None:  # Shutdown signal
                    self.download_queue.task_done()
                    break

                try:
                    if task.source in ["TVDB", "TMDB"]:
                        # Download from URL
                        download_image(task.url, task.dest_path, task.headers or {})
                        logger.debug(
                            f"✓ Downloaded {task.source} image: {task.episode_info}"
                        )
                    elif task.source == "SCREENSHOT":
                        # Generate screenshot
                        from mpv_scraper.video_capture import capture_video_frame

                        capture_video_frame(task.video_path, task.dest_path)
                        logger.debug(f"✓ Generated screenshot: {task.episode_info}")

                    with self.lock:
                        self.results.append((task, True, None))

                except Exception as e:
                    logger.warning(
                        f"Failed to download {task.source} image for {task.episode_info}: {e}"
                    )
                    with self.lock:
                        self.results.append((task, False, str(e)))

                # Mark task as done only after processing
                self.download_queue.task_done()

            except queue.Empty:
                break

    def execute_downloads(self) -> List[Tuple[DownloadTask, bool, Optional[str]]]:
        """Execute all queued downloads in parallel."""
        if self.download_queue.empty():
            return []

        # Start worker threads
        threads = []
        for _ in range(min(self.max_workers, self.download_queue.qsize())):
            thread = threading.Thread(target=self._download_worker)
            thread.start()
            threads.append(thread)

        # Wait for all downloads to complete
        for thread in threads:
            thread.join()

        return self.results


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


def _load_scrape_cache(cache_path: Path) -> Optional[Dict[str, Any]]:
    """Load scrape cache from JSON file if it exists."""
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _is_episode_scraped(
    show_dir: Path,
    season: int,
    episode: int,
    cache: Optional[Dict[str, Any]],
    images_dir: Path,
    show_name: str,
) -> bool:
    """
    Check if an episode is already scraped by verifying cache and image existence.

    Args:
        show_dir: Directory containing the show
        season: Season number
        episode: Episode number
        cache: Loaded cache dictionary (None if cache doesn't exist)
        images_dir: Directory where episode images are stored
        show_name: Name of the show (for image filename)

    Returns:
        True if episode is already scraped (exists in cache and image exists), False otherwise
    """
    if not cache:
        return False

    # Check if episode exists in cache
    episodes = cache.get("episodes", [])
    episode_found = False
    for ep in episodes:
        if ep.get("seasonNumber") == season and ep.get("number") == episode:
            episode_found = True
            break

    if not episode_found:
        return False

    # Check if image exists
    ep_span = f"S{season:02d}E{episode:02d}"
    img_name = f"{show_name} - {ep_span}-image.png"
    img_path = images_dir / img_name

    return img_path.exists()


def _is_movie_scraped(
    movie_path: Path,
    cache: Optional[Dict[str, Any]],
    images_dir: Path,
) -> bool:
    """
    Check if a movie is already scraped by verifying cache and image existence.

    Args:
        movie_path: Path to the movie file
        cache: Loaded cache dictionary (None if cache doesn't exist)
        images_dir: Directory where movie images are stored

    Returns:
        True if movie is already scraped (exists in cache and image exists), False otherwise
    """
    if not cache:
        return False

    # Check if movie exists in cache (cache is a single movie record)
    # We verify it's a valid movie record by checking for common fields
    if not cache.get("title") and not cache.get("name"):
        return False

    # Check if image exists
    img_name = f"{movie_path.stem}-image.png"
    img_path = images_dir / img_name

    return img_path.exists()


def _get_show_name_variations(show_name: str) -> list[str]:
    """
    Generate variations of a show name for better TVDB matching.

    Handles common patterns like:
    - "Teenage Mutant Ninja Turtles" -> ["Teenage Mutant Ninja Turtles", "Teenage Mutant Ninja Turtles (1987)"]
    - "Popeye the Sailor" -> ["Popeye the Sailor", "Popeye"]
    - Shows with years in parentheses
    """
    variations = [show_name]

    # Handle shows that might have year suffixes in TVDB
    year_patterns = [
        r"^(.*?)\s*\((\d{4})\)$",  # "Show Name (1987)"
        r"^(.*?)\s*(\d{4})$",  # "Show Name 1987"
    ]

    for pattern in year_patterns:
        match = re.match(pattern, show_name)
        if match:
            base_name = match.group(1).strip()
            year = match.group(2)
            variations.extend(
                [base_name, f"{base_name} ({year})", f"{base_name} {year}"]
            )
            break

    # Handle shows without years that might have them in TVDB
    if not any(re.match(r".*\(\d{4}\)", show_name) for show_name in variations):
        # Common years to try for shows that might have them
        common_years = ["1987", "1990", "1995", "2000", "2005", "2010", "2015", "2020"]
        for year in common_years:
            variations.append(f"{show_name} ({year})")

    # Handle specific show variations
    if "Teenage Mutant Ninja Turtles" in show_name:
        variations.extend(
            [
                "Teenage Mutant Ninja Turtles (1987)",
                "TMNT",
                "Teenage Mutant Ninja Turtles",
            ]
        )
    elif "Popeye" in show_name:
        variations.extend(["Popeye the Sailor", "Popeye", "Popeye the Sailor Man"])

    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for variation in variations:
        if variation not in seen:
            seen.add(variation)
            unique_variations.append(variation)

    return unique_variations


def scrape_tv_parallel(
    show_dir: Path,
    download_manager: ParallelDownloadManager,
    transaction_logger=None,
    top_images_dir: Path = None,
    *,
    prefer_fallback: bool = False,
    fallback_only: bool = False,
    no_remote: bool = False,
    refresh: bool = False,
) -> List[DownloadTask]:
    """
    Scrape metadata for a TV show directory and queue downloads for parallel processing.

    Returns:
        List of DownloadTask objects that were queued for processing.
    """
    # Use top-level images directory if provided, otherwise show-specific
    if top_images_dir:
        images_dir = top_images_dir
    else:
        images_dir = show_dir / "images"
        images_dir.mkdir(exist_ok=True, parents=True)
        if transaction_logger:
            transaction_logger.log_create(images_dir)

    # Load existing cache for incremental scraping
    cache_path = show_dir / CACHE_FILE
    existing_cache = None if refresh else _load_scrape_cache(cache_path)

    # Provider selection
    if no_remote:
        record = {"episodes": []}
        headers = {}
    else:
        record = None
        headers = {}
        try_tvdb = not fallback_only
        use_tvmaze = prefer_fallback or fallback_only
        if try_tvdb:
            # TVDB requires key; authenticate may raise if missing
            try:
                token = tvdb.authenticate_tvdb()
                headers = {"Authorization": f"Bearer {token}"}
            except Exception:
                try_tvdb = False

        # Search and get record
        if use_tvmaze and not try_tvdb:
            # Fallback path via TVmaze
            from mpv_scraper import tvmaze

            results = tvmaze.search_show(show_dir.name)
            if not results:
                raise RuntimeError(
                    f"TVmaze could not find series for {show_dir.name!r}"
                )
            series_id = results[0]["id"]
            episodes = tvmaze.get_show_episodes(series_id)
            record = {"episodes": episodes, "artworks": {}}
        else:
            # TVDB path
            token = headers.get("Authorization", "")[7:] if headers else None
            if not token:
                # If we ended here with no token and not using TVmaze, bail
                raise RuntimeError("TVDB auth missing and fallback not selected")
            show_name_variations = _get_show_name_variations(show_dir.name)
            search_results = None
            for variation in show_name_variations:
                try:
                    search_results = tvdb.search_show(variation, token)
                    if search_results:
                        break
                except Exception:
                    continue
            if not search_results:
                raise RuntimeError(
                    f"TVDB could not find series for {show_dir.name!r} (tried variations: {show_name_variations})"
                )
            series_id = search_results[0]["id"]
            record = tvdb.get_series_extended(series_id, token)
            if not record:
                raise RuntimeError(
                    f"Failed to fetch extended record for id {series_id}"
                )

    # 1. Look up series with name variations
    show_name_variations = _get_show_name_variations(show_dir.name)
    search_results = None

    for variation in show_name_variations:
        try:
            search_results = tvdb.search_show(variation, token)
            if search_results:
                logger.info(f"Found show '{show_dir.name}' in TVDB as '{variation}'")
                break
        except Exception as e:
            logger.debug(f"TVDB search failed for '{variation}': {e}")
            continue

    if not search_results:
        raise RuntimeError(
            f"TVDB could not find series for {show_dir.name!r} (tried variations: {show_name_variations})"
        )

    # 'record' now present

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
    episodes_with_images = 0

    # Track source usage for logging
    tvdb_episode_count = 0
    tmdb_episode_count = 0
    no_image_count = 0

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

            # Handle year-based episodes (like Popeye S1934E03)
            # For year-based episodes, treat them as season 1 for TMDB purposes
            tmdb_seasons_to_fetch = []
            for season in all_seasons:
                if season > 100:  # Likely a year (1934, 1987, etc.)
                    tmdb_seasons_to_fetch.append(1)  # Treat as season 1
                    logger.info(f"Treating year-based season {season} as TMDB season 1")
                else:
                    tmdb_seasons_to_fetch.append(season)

            # Remove duplicates and fetch
            unique_tmdb_seasons = list(set(tmdb_seasons_to_fetch))
            for season in unique_tmdb_seasons:
                season_images = _try_tmdb_season_images(parsed_show_name, season)
                tmdb_episode_images.update(season_images)

            logger.info(
                f"Bulk fetched {len(tmdb_episode_images)} TMDB episode images for {parsed_show_name} (seasons {unique_tmdb_seasons})"
            )
        except Exception as e:
            logger.debug(f"TMDB bulk fetch failed for {parsed_show_name}: {e}")

    # Collect all download tasks
    download_tasks = []
    skipped_count = 0

    for file_path, meta in episode_files:
        # Look for API image for the first episode in the span
        target_season = meta.season
        target_episode = meta.start_ep

        # Check if episode is already scraped (incremental scraping)
        if not refresh and existing_cache:
            if _is_episode_scraped(
                show_dir,
                target_season,
                target_episode,
                existing_cache,
                images_dir,
                show_dir.name,
            ):
                logger.debug(
                    f"Skipping already-scraped episode S{target_season:02d}E{target_episode:02d} for {show_dir.name}"
                )
                skipped_count += 1
                continue

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
            tvdb_episode_count += 1
            logger.debug(
                f"Found TVDB episode image for S{target_season:02d}E{target_episode:02d}"
            )
        else:
            # Try TMDB from bulk-fetched data
            # Handle year-based episodes by mapping to season 1 for TMDB
            tmdb_season = 1 if target_season > 100 else target_season
            tmdb_key = f"S{tmdb_season:02d}E{target_episode:02d}"
            if tmdb_key in tmdb_episode_images:
                img_url = tmdb_episode_images[tmdb_key]
                source = "TMDB"
                episodes_with_images += 1
                tmdb_episode_count += 1
                logger.debug(
                    f"Found TMDB episode image for {tmdb_key} (mapped from S{target_season:02d}E{target_episode:02d})"
                )
            else:
                no_image_count += 1
                logger.debug(
                    f"No episode image found for S{target_season:02d}E{target_episode:02d} (TVDB: {bool(api_episode)}, TMDB: {tmdb_key in tmdb_episode_images})"
                )

        if img_url:
            # Create the span filename (e.g., "S04E01-E02" for span)
            if meta.end_ep != meta.start_ep:
                span_name = f"S{meta.season:02d}E{meta.start_ep:02d}-E{meta.end_ep:02d}"
            else:
                span_name = f"S{meta.season:02d}E{meta.start_ep:02d}"

            dest = images_dir / f"{show_dir.name} - {span_name}-image.png"

            # Create download task
            task = DownloadTask(
                url=img_url,
                dest_path=dest,
                source=source,
                show_name=show_dir.name,
                episode_info=span_name,
                headers=headers,
            )
            download_tasks.append(task)
        else:
            # No image found - add screenshot generation task
            if meta.end_ep != meta.start_ep:
                span_name = f"S{meta.season:02d}E{meta.start_ep:02d}-E{meta.end_ep:02d}"
            else:
                span_name = f"S{meta.season:02d}E{meta.start_ep:02d}"

            dest = images_dir / f"{show_dir.name} - {span_name}-image.png"

            # Create screenshot generation task
            task = DownloadTask(
                url="",  # Not used for screenshots
                dest_path=dest,
                source="SCREENSHOT",
                show_name=show_dir.name,
                episode_info=span_name,
                video_path=file_path,
            )
            download_tasks.append(task)

    # Log source usage summary
    logger.info(
        f"Episode image sources for {show_dir.name}: TVDB={tvdb_episode_count}, TMDB={tmdb_episode_count}, None={no_image_count}"
    )

    # Add all tasks to the global download manager
    for task in download_tasks:
        download_manager.add_task(task)

    logger.info(
        f"Queued {len(download_tasks)} episode images for {show_dir.name} (parallel processing)"
    )
    if skipped_count > 0:
        logger.info(
            f"Skipped {skipped_count} already-scraped episodes for {show_dir.name} (use --refresh to re-scrape)"
        )

    # 5. Cache the record (update existing cache or create new)
    _safe_write_json(cache_path, record)
    if transaction_logger:
        transaction_logger.log_create(cache_path)
    logger.info(f"Cached metadata for {show_dir.name}")

    return download_tasks


def scrape_movie(
    movie_path: Path,
    transaction_logger=None,
    top_images_dir: Path = None,
    *,
    prefer_fallback: bool = False,
    fallback_only: bool = False,
    no_remote: bool = False,
    refresh: bool = False,
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

    # Use top-level images directory if provided, otherwise create local images directory
    if top_images_dir:
        images_dir = top_images_dir
    else:
        images_dir = movie_path.parent / "images"
        images_dir.mkdir(exist_ok=True, parents=True)
        if transaction_logger:
            transaction_logger.log_create(images_dir)

    # Check if movie is already scraped (incremental scraping)
    movie_cache_file = movie_path.parent / CACHE_FILE
    existing_cache = None if refresh else _load_scrape_cache(movie_cache_file)
    if not refresh and existing_cache:
        if _is_movie_scraped(movie_path, existing_cache, images_dir):
            logger.info(
                f"Skipping already-scraped movie {movie_meta.title} (use --refresh to re-scrape)"
            )
            return

    # 2. Provider selection
    if no_remote:
        record = {}
    else:
        try_tmdb = not fallback_only
        record = None
        if try_tmdb:
            try:
                search_results = tmdb.search_movie(movie_meta.title, movie_meta.year)
            except Exception:
                search_results = []
            if search_results:
                movie_id = search_results[0]["id"]
                record = tmdb.get_movie_details(movie_id)
        if record is None:
            # Try OMDb fallback if available
            from mpv_scraper import omdb

            try:
                omdb_results = omdb.search_movie(movie_meta.title, movie_meta.year)
            except Exception:
                omdb_results = []
            if omdb_results:
                imdb_id = omdb_results[0]["id"]
                record = omdb.get_movie_details(imdb_id)
        if record is None:
            raise RuntimeError(
                f"Could not find metadata for movie {movie_meta.title!r}"
            )

    # 5. Download poster
    poster_url = record.get("poster_url")
    if poster_url:
        try:
            logger.info(f"Downloading poster for {movie_meta.title}")
            # Use proper EmulationStation naming convention
            poster_path = images_dir / f"{movie_path.stem}-image.png"
            download_image(poster_url, poster_path)
            # Ensure poster meets size constraints (≤600KB, ≤500px width)
            from mpv_scraper.images import ensure_png_size

            ensure_png_size(poster_path)
            if transaction_logger:
                transaction_logger.log_create(poster_path)
            logger.info(f"✓ Downloaded and optimized poster for {movie_meta.title}")
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
    _safe_write_json(movie_cache_file, record)
    if transaction_logger:
        transaction_logger.log_create(movie_cache_file)
    logger.info(f"Cached metadata for {movie_meta.title}")
