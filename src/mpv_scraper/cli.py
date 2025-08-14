"""Command-line interface entrypoint for MPV Metadata Scraper.

Commands
========
scan PATH
    Scan a media directory and output a brief summary of shows/movies discovered.

generate PATH
    Generate *gamelist.xml* files for the directory using metadata previously scraped.

run PATH
    Perform scan ➜ scrape ➜ generate in sequence.
"""

import click
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Test-only hook ----------------------------------------------------------


def _noop_test_hook(*_args, **_kwargs):
    """No-op; used by tests to inject behaviour when needed."""


# -----------------------------------------------------------------------------


@click.group()
def main():
    """A CLI tool to scrape metadata for TV shows and movies."""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--force", is_flag=True, help="Overwrite existing config files")
def init(path, force=False):
    """First-run wizard: validate tools, scaffold config, and set defaults."""
    from pathlib import Path
    from textwrap import dedent
    from mpv_scraper.utils import validate_prereqs

    root = Path(path)

    # 1) Prerequisites
    prereq = validate_prereqs()
    if prereq["ffmpeg_version"]:
        click.echo(f"ffmpeg: {prereq['ffmpeg_version']}")
    if prereq["ffprobe_version"]:
        click.echo(f"ffprobe: {prereq['ffprobe_version']}")
    if prereq["warnings"]:
        for w in prereq["warnings"]:
            click.echo(f"WARNING: {w}")

    # 2) Ensure directories
    images_dir = root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    movies_dir = root / "Movies"
    movies_dir.mkdir(parents=True, exist_ok=True)

    # 3) Config files
    config_path = root / "mpv-scraper.toml"
    env_example = root / ".env.example"
    env_path = root / ".env"

    default_toml = dedent(
        f"""
        # mpv-scraper configuration
        library_root = "{root.as_posix()}"
        workers = 0  # 0 = auto-detect
        preset = "handheld"
        replace_originals_default = false
        regen_gamelist_default = false
        """
    ).lstrip()

    if not config_path.exists() or force:
        config_path.write_text(default_toml)
        click.echo(f"Wrote {config_path}")
    else:
        click.echo(f"Found existing {config_path}; leaving unchanged")

    if not env_example.exists():
        env_example.write_text(
            "TVDB_API_KEY=\nTMDB_API_KEY=\n# Optional: OMDB_API_KEY=\n"
        )
        click.echo(f"Wrote {env_example}")

    if not env_path.exists():
        env_path.write_text(env_example.read_text())
        click.echo(f"Wrote {env_path}")
    else:
        click.echo(f"Found existing {env_path}; leaving unchanged")

    # 4) Cheat sheet
    click.echo(
        "\nNext steps:\n"
        "  - Edit .env with API keys or use fallback-only modes later\n"
        "  - Try: mpv-scraper scan <library> | mpv-scraper run <library>\n"
    )


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def scan(path):
    """Scan DIRECTORY and print a summary (debug helper)."""
    from pathlib import Path
    from mpv_scraper.utils import get_logger
    from mpv_scraper.scanner import scan_directory

    root = Path(path)
    logger = get_logger(root)
    result = scan_directory(root)
    click.echo(
        f"Found {len(result.shows)} show folders and {len(result.movies)} movies."
    )
    logger.info(
        "Scan: Found %d show folders and %d movies at %s",
        len(result.shows),
        len(result.movies),
        root,
    )

    # Opportunistic: write a quick completed job snapshot so the TUI can see activity
    try:
        jobs_dir = root / ".mpv-scraper"
        jobs_dir.mkdir(exist_ok=True)
        jobs_file = jobs_dir / "jobs.json"
        import json

        jobs = {}
        if jobs_file.exists():
            try:
                jobs = json.loads(jobs_file.read_text())
            except Exception:
                jobs = {}
        jobs["scan"] = {
            "name": f"Scan {root.name}",
            "status": "completed",
            "progress": 1,
            "total": 1,
            "error": None,
        }
        jobs_file.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    except Exception:
        # Never let job snapshot failures impact CLI result
        pass


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--prefer-fallback", is_flag=True, help="Prefer fallback providers (TVmaze/OMDb)"
)
@click.option(
    "--fallback-only", is_flag=True, help="Use only fallback providers; skip TVDB/TMDB"
)
@click.option(
    "--no-remote",
    is_flag=True,
    help="Do not perform any network calls; cache/placeholder only",
)
def scrape(path, prefer_fallback=False, fallback_only=False, no_remote=False):
    """Scrape metadata and artwork for DIRECTORY.

    Scans *path* and downloads:

    * TV show metadata from TVDB (episodes, ratings, descriptions)
    * Movie metadata from TMDB (overview, ratings, release dates)
    * Poster images for shows and movies
    * Logo artwork for marquee display
    * Caches all metadata for later generate step

    Uses parallel processing for improved performance.
    """
    from pathlib import Path
    from mpv_scraper.scanner import scan_directory
    from mpv_scraper.scraper import (
        scrape_tv_parallel,
        scrape_movie,
        ParallelDownloadManager,
    )
    from mpv_scraper.transaction import TransactionLogger
    from mpv_scraper.utils import get_logger

    root = Path(path)
    logger_out = get_logger(root)
    logger = TransactionLogger(root / "transaction.log")  # Create in target directory

    # Initialize a lightweight job snapshot for the TUI
    def _jobs_begin(total: int) -> None:
        try:
            jobs_dir = root / ".mpv-scraper"
            jobs_dir.mkdir(exist_ok=True)
            jf = jobs_dir / "jobs.json"
            import json

            jobs = {}
            if jf.exists():
                try:
                    jobs = json.loads(jf.read_text())
                except Exception:
                    jobs = {}
            jobs["scrape"] = {
                "name": f"Scrape {root.name}",
                "status": "running",
                "progress": 0,
                "total": total,
                "error": None,
            }
            jf.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _jobs_inc() -> None:
        try:
            jf = root / ".mpv-scraper" / "jobs.json"
            if not jf.exists():
                return
            import json

            jobs = json.loads(jf.read_text()) if jf.exists() else {}
            job = jobs.get("scrape") or {}
            job["progress"] = int(job.get("progress", 0)) + 1
            jobs["scrape"] = job
            jf.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _jobs_end(status: str = "completed") -> None:
        try:
            jf = root / ".mpv-scraper" / "jobs.json"
            if not jf.exists():
                return
            import json

            jobs = json.loads(jf.read_text()) if jf.exists() else {}
            job = jobs.get("scrape") or {}
            job["status"] = status
            if job.get("total") is not None and job.get("progress") is not None:
                if int(job["progress"]) < int(job["total"]):
                    job["progress"] = job["total"]
            jobs["scrape"] = job
            jf.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _log_creation(p: Path) -> None:
        logger.log_create(p.resolve())

    # 1. Create top-level images directory
    top_images_dir = root / "images"
    if not top_images_dir.exists():
        top_images_dir.mkdir(parents=True, exist_ok=True)
        _log_creation(top_images_dir)

    # 2. Scan directory
    result = scan_directory(root)
    click.echo(
        f"Found {len(result.shows)} show folders and {len(result.movies)} movies."
    )
    logger_out.info(
        "Scrape: Found %d show folders and %d movies at %s",
        len(result.shows),
        len(result.movies),
        root,
    )

    # 3. Create global parallel download manager
    download_manager = ParallelDownloadManager(
        max_workers=12
    )  # Increased for cross-show parallelization

    # 3.5 Initialize job snapshot total (shows + movies + downloads phase)
    try:
        total_units = len(result.shows) + len(result.movies)
        # Add one unit for the bulk download execution phase if there will be tasks
        total_units += 1
        _jobs_begin(total_units)
    except Exception:
        pass

    # 4. Scrape TV shows (metadata + queue downloads)
    all_tasks = []
    for show in result.shows:
        click.echo(f"Scraping {show.path.name}...")
        try:
            tasks = scrape_tv_parallel(
                show.path,
                download_manager,
                logger,
                top_images_dir,
                prefer_fallback=prefer_fallback,
                fallback_only=fallback_only,
                no_remote=no_remote,
            )
            all_tasks.extend(tasks)
            click.echo(f"✓ Scraped {show.path.name}")
            logger_out.info("Scraped show: %s", show.path.name)
            _jobs_inc()
        except Exception as e:
            click.echo(f"✗ Failed to scrape {show.path.name}: {e}")
            logger_out.error("Failed to scrape show %s: %s", show.path.name, e)

    # 5. Scrape movies (sequential for now, could be parallelized later)
    for movie in result.movies:
        click.echo(f"Scraping {movie.path.name}...")
        try:
            scrape_movie(
                movie.path,
                logger,
                top_images_dir,
                prefer_fallback=prefer_fallback,
                fallback_only=fallback_only,
                no_remote=no_remote,
            )
            click.echo(f"✓ Scraped {movie.path.name}")
            logger_out.info("Scraped movie: %s", movie.path.name)
            _jobs_inc()
        except Exception as e:
            click.echo(f"✗ Failed to scrape {movie.path.name}: {e}")
            logger_out.error("Failed to scrape movie %s: %s", movie.path.name, e)

    # 6. Execute all parallel downloads
    if all_tasks:
        click.echo(f"Executing {len(all_tasks)} parallel downloads...")
        results = download_manager.execute_downloads()

        # Process results
        successful_downloads = 0
        failed_downloads = 0
        for task, success, error in results:
            if success:
                successful_downloads += 1
                logger.log_create(task.dest_path)
            else:
                failed_downloads += 1
                click.echo(
                    f"✗ Failed to download {task.source} image for {task.episode_info}: {error}"
                )

        click.echo(
            f"✓ Completed parallel downloads: {successful_downloads} successful, {failed_downloads} failed"
        )
        logger_out.info(
            "Downloads complete: %d success, %d failed",
            successful_downloads,
            failed_downloads,
        )
        _jobs_inc()
    else:
        click.echo("No downloads to process.")
        logger_out.info("No downloads to process.")

    _jobs_end("completed")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def generate(path):
    """Generate gamelist.xml files from scraped metadata."""

    from pathlib import Path
    from mpv_scraper.utils import get_logger

    # First, sanitize any filenames with special characters
    root = Path(path)
    logger_out = get_logger(root)
    sanitized_count = _sanitize_filenames(root)
    if sanitized_count > 0:
        click.echo(f"Sanitized {sanitized_count} filenames with special characters.")
        logger_out.info("Sanitized %d filenames", sanitized_count)

    """Generate gamelist.xml files for all TV shows and movies."""
    from mpv_scraper.parser import parse_tv_filename, parse_movie_filename
    from mpv_scraper.scanner import scan_directory
    from mpv_scraper.xml_writer import write_top_gamelist
    from typing import Union
    import shutil

    root = Path(path)
    # TransactionLogger(root / "transaction.log")  # Create in target directory

    def _log_creation(p: Path) -> None:
        click.echo(f"Created: {p}")

    def _load_scrape_cache(cache_path: Path) -> Union[dict, None]:
        if cache_path.exists():
            try:
                import json

                return json.loads(cache_path.read_text())
            except (json.JSONDecodeError, OSError):
                return None
        return None

    # 1. Create top-level images directory for folder-level images only
    top_images_dir = root / "images"
    if not top_images_dir.exists():
        top_images_dir.mkdir(parents=True, exist_ok=True)
        _log_creation(top_images_dir)

    # 2. Scan MPV directory
    result = scan_directory(root)

    # 3. Generate folder entries and collect all game entries for top-level gamelist
    folder_entries = []
    all_games = []  # Collect all game entries here
    for show in result.shows:
        # Don't create placeholder posters - real images will be created by the scraper

        folder_entries.append(
            {
                "path": f"./{show.path.name}",
                "name": show.path.name,
                "image": f"./images/{show.path.name}-poster.png",
            }
        )

        # Load scrape cache for this show
        show_cache = _load_scrape_cache(show.path / ".scrape_cache.json")

        games = []
        for file_path in show.files:
            meta = parse_tv_filename(file_path.name)
            if meta and meta.titles:
                title_part = " & ".join(meta.titles)
                ep_span = f"S{meta.season:02d}E{meta.start_ep:02d}"
                if meta.end_ep != meta.start_ep:
                    ep_span += f"-E{meta.end_ep:02d}"
                name = f"{title_part} – {ep_span}"
            else:
                name = file_path.stem

            # Get metadata from scrape cache if available
            desc = None
            rating = 0.0
            # marquee = (
            #     "./images/logo.png"  # Will be updated below if proper marquee exists
            # )
            releasedate = None
            genre = None
            developer = None
            publisher = None
            video = None
            lang = "en"

            if show_cache and meta:
                # Find episode in cache
                for episode in show_cache.get("episodes", []):
                    if (
                        episode.get("seasonNumber") == meta.season
                        and episode.get("number") == meta.start_ep
                    ):
                        desc = episode.get("overview")
                        # Rating is already normalized 0-1 from scraper
                        rating = episode.get("siteRating", 0.0)
                        # Format release date
                        from mpv_scraper.utils import format_release_date

                        releasedate = format_release_date(episode.get("firstAired"))
                        break

                # Get series rating if no episode rating
                if rating == 0.0:
                    rating = show_cache.get("siteRating", 0.0)

                # Ensure minimum rating to avoid "?" display in EmulationStation
                if rating < 0.1:
                    rating = 0.5  # Set a reasonable default for low-rated content

                # Use series firstAired as fallback if episode doesn't have one
                if not releasedate and show_cache.get("firstAired"):
                    from mpv_scraper.utils import format_release_date

                    releasedate = format_release_date(show_cache.get("firstAired"))

                # Get series-level metadata
                if show_cache.get("genre"):
                    genre = ", ".join(show_cache.get("genre", []))
                if show_cache.get("network", {}).get("name"):
                    developer = show_cache.get("network", {}).get("name")
                if show_cache.get("studio"):
                    publisher = ", ".join(
                        [
                            s.get("name", "")
                            for s in show_cache.get("studio", [])
                            if s.get("name")
                        ]
                    )

            # Reference show-level marquee and box images (already copied to show directory)
            # show_marquee_path = f"./images/{show.path.name}-marquee.png"
            # show_box_path = f"./images/{show.path.name}-box.png"

            # Create images in top-level images directory with episode number naming
            if meta:
                ep_span = f"S{meta.season:02d}E{meta.start_ep:02d}"
                if meta.end_ep != meta.start_ep:
                    ep_span += f"-E{meta.end_ep:02d}"
                img_name = f"{show.path.name} - {ep_span}-image.png"  # e.g., "Darkwing Duck - S01E01-image.png"
                # thumb_name = f"{show.path.name} - {ep_span}-thumb.png"
            else:
                img_name = (
                    f"{show.path.name} - {file_path.stem.split(' - ')[-1]}-image.png"
                )
                # thumb_name = (
                #     f"{show.path.name} - {file_path.stem.split(' - ')[-1]}-thumb.png"
                # )

            # Define img_path for video capture
            img_path = top_images_dir / img_name

            # Check if the scraper already downloaded an episode image
            api_image_exists = img_path.exists()

            # Only generate screenshot as fallback if no API image was downloaded
            if not api_image_exists:
                from mpv_scraper.video_capture import capture_at_percentage

                if capture_at_percentage(file_path, img_path, percentage=25.0):
                    _log_creation(img_path)
                    click.echo(f"Generated fallback screenshot for {file_path.name}")
                else:
                    click.echo(
                        f"Failed to generate fallback screenshot for {file_path.name}"
                    )
            else:
                click.echo(f"Using API image for {file_path.name}")

            # Create marquee and box images for show (once per show)
            # show_marquee_name = f"{show.path.name}-marquee.png"
            # show_box_name = f"{show.path.name}-box.png"
            # show_marquee_path = top_images_dir / show_marquee_name
            # show_box_path = top_images_dir / show_box_name

            # Don't create placeholders - real images will be created by the scraper

            # Update name to be "SXXEYY-<EPISODE TITLE>" for better ordering
            if meta and meta.titles:
                title_part = " & ".join(meta.titles)
                # Normalize special characters in episode titles
                from mpv_scraper.utils import normalize_text

                title_part = normalize_text(title_part)
                ep_span = f"S{meta.season:02d}E{meta.start_ep:02d}"
                if meta.end_ep != meta.start_ep:
                    ep_span += f"-E{meta.end_ep:02d}"
                name = f"{ep_span} - {title_part}"  # e.g., "S01E01 - Darkly Dawns the Duck (1)"
            else:
                name = file_path.stem

            game_entry = {
                "path": f"./{show.path.name}/{file_path.name}",  # Relative to top-level MPV directory
                "name": name,
                "image": f"./images/{img_name}",  # Point to episode screenshot
                "rating": rating,
                "marquee": f"./images/{show.path.name}-marquee.png",  # Point to marquee-specific image
                "thumbnail": f"./images/{show.path.name}-box.png",  # Point to box art (theme expects this in <thumbnail> field)
                "lang": lang,
            }

            if desc:
                # Normalize special characters in descriptions
                from mpv_scraper.utils import normalize_text

                game_entry["desc"] = normalize_text(desc)
            if releasedate:
                game_entry["releasedate"] = releasedate
            if genre:
                game_entry["genre"] = genre
            if developer:
                game_entry["developer"] = developer
            if publisher:
                game_entry["publisher"] = publisher
            if video:
                game_entry["video"] = video

            games.append(game_entry)

        # Add show games to the main games list instead of creating show-specific gamelist
        all_games.extend(games)

    # 4. Movies folder (optional)
    movies_dir = root / "Movies"
    if movies_dir.exists():
        # Use top-level images directory for movies too
        images_dir = top_images_dir

        # Copy movies-poster.jpg to top-level images directory if it exists
        # Look for the file in the project's public/images directory

        project_root = Path(
            __file__
        ).parent.parent.parent  # Go up from src/mpv_scraper/cli.py to project root
        movies_poster_source = project_root / "public" / "images" / "movies-poster.jpg"
        if movies_poster_source.exists():
            top_movies_poster = top_images_dir / "movies-poster.jpg"
            if not top_movies_poster.exists():
                import shutil

                shutil.copy2(movies_poster_source, top_movies_poster)
                _log_creation(top_movies_poster)

            # Also copy to top-level images directory for consistency
            movies_poster_dest = top_images_dir / "movies-poster.jpg"
            if not movies_poster_dest.exists():
                shutil.copy2(movies_poster_source, movies_poster_dest)
                _log_creation(movies_poster_dest)
        else:
            # Fallback: Create a custom movies folder image if the stock image doesn't exist
            poster_path = images_dir / "poster.png"
            if not poster_path.exists():
                from mpv_scraper.images import create_movies_folder_image

                create_movies_folder_image(poster_path)
                _log_creation(poster_path)

        folder_entries.append(
            {
                "path": "./Movies",
                "name": "Movies",
                "image": "./images/movies-poster.jpg",
            }
        )

        games = []
        for movie_file in result.movies:
            meta = parse_movie_filename(movie_file.path.name)
            name = meta.title if meta else movie_file.path.stem

            # Movies should use individual posters downloaded by scraper
            img_path = images_dir / f"{movie_file.path.stem}-image.png"
            # Check if individual movie poster exists, otherwise use generic
            if img_path.exists():
                click.echo(f"Movie {movie_file.path.name} will use individual poster")
                movie_image = f"./images/{movie_file.path.stem}-image.png"
            else:
                click.echo(f"Movie {movie_file.path.name} will use generic poster")
                movie_image = "./images/movies-poster.jpg"

            # Get metadata from scrape cache if available
            desc = None
            rating = 0.0
            releasedate = None
            genre = None
            developer = None
            publisher = None
            lang = "en"

            movie_cache = _load_scrape_cache(
                movie_file.path.parent / ".scrape_cache.json"
            )
            if movie_cache and meta:
                # Find movie in cache
                for movie in movie_cache.get("movies", []):
                    if movie.get("title") == meta.title:
                        desc = movie.get("overview")
                        rating = (
                            movie.get("vote_average", 0.0) / 10.0
                        )  # Normalize to 0-1
                        from mpv_scraper.utils import format_release_date

                        releasedate = format_release_date(movie.get("release_date"))
                        if movie.get("genres"):
                            genre = ", ".join(
                                [g.get("name", "") for g in movie["genres"]]
                            )
                        if movie.get("production_companies"):
                            publisher = ", ".join(
                                [
                                    c.get("name", "")
                                    for c in movie["production_companies"]
                                    if c.get("name")
                                ]
                            )
                        break

            game_entry = {
                "path": f"./Movies/{movie_file.path.name}",  # Relative to top-level MPV directory
                "name": name,
                "image": movie_image,  # Use individual poster or generic fallback
                "rating": rating,
                "thumbnail": movie_image,  # Use individual poster or generic fallback
                "lang": lang,
            }

            if desc:
                # Normalize special characters in descriptions
                from mpv_scraper.utils import normalize_text

                game_entry["desc"] = normalize_text(desc)
            if releasedate:
                game_entry["releasedate"] = releasedate
            if genre:
                game_entry["genre"] = genre
            if developer:
                game_entry["developer"] = developer
            if publisher:
                game_entry["publisher"] = publisher

            games.append(game_entry)

        # Add movie games to the main games list
        all_games.extend(games)

    # 5. Write top-level gamelist with both folder entries and all game entries
    top_gamelist_path = root / "gamelist.xml"

    write_top_gamelist(folder_entries + all_games, top_gamelist_path)
    _log_creation(top_gamelist_path)
    logger_out.info("Wrote %s", top_gamelist_path)

    click.echo("gamelist.xml files generated.")

    # Update jobs snapshot for TUI
    try:
        jobs_dir = root / ".mpv-scraper"
        jf = jobs_dir / "jobs.json"
        if jf.exists():
            import json

            jobs = json.loads(jf.read_text())
            jobs["generate"] = {
                "name": f"Generate {root.name}",
                "status": "completed",
                "progress": 1,
                "total": 1,
                "error": None,
            }
            jf.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    except Exception:
        pass


@main.command()
@click.argument(
    "path", required=False, type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
def undo(path: str | None = None):
    """Undo the most recent scraper run.

    Looks for a ``transaction.log`` in the provided PATH (if given), otherwise
    the current working directory. As a convenience, if not found, the parent
    directory is also checked (preserves previous behaviour).
    """
    from pathlib import Path
    from mpv_scraper.transaction import revert_transaction

    root = Path(path) if path else Path.cwd()

    # Look for transaction.log in the target directory first, then parent
    log_path = root / "transaction.log"
    if not log_path.exists():
        parent_log = root.parent / "transaction.log"
        if parent_log.exists():
            log_path = parent_log
        else:
            click.echo(f"No transaction.log found in {root} or its parent.")
            return 0

    revert_transaction(log_path)
    click.echo("Undo completed.")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--quality",
    type=click.Choice(["fast", "medium", "high"]),
    default="medium",
    help="Encoding quality (fast=lower quality, high=better quality but slower)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be cropped without actually processing videos",
)
def crop(path, quality, dry_run):
    """Crop videos in DIRECTORY to 4:3 aspect ratio.

    Detects videos with letterboxing (black bars on left/right) and crops them
    to proper 4:3 aspect ratio for better display on 4:3 devices.

    This is useful for older content like Scooby-Doo episodes that were
    originally 4:3 but are stored in 16:9 containers with letterboxing.
    """
    from pathlib import Path
    from mpv_scraper.video_crop import batch_crop_videos_to_4_3

    directory = Path(path)

    if dry_run:
        click.echo(f"DRY RUN: Analyzing {directory} for videos to crop...")
    else:
        click.echo(f"Cropping videos in {directory} to 4:3 aspect ratio...")

    processed, successful = batch_crop_videos_to_4_3(
        directory, quality=quality, dry_run=dry_run
    )

    if dry_run:
        click.echo(f"DRY RUN: Would process {processed} videos")
    else:
        click.echo(
            f"Crop processing complete: {successful}/{processed} videos processed successfully"
        )


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be converted without actually processing videos",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing MP4 files",
)
def convert_with_subs(path, dry_run, overwrite):
    """Convert MKV files in DIRECTORY to web-optimized MP4 with subtitles.

    Converts MKV files to MP4 format with web optimization and subtitle support.
    Reduces file size by ~2/3 while maintaining quality and including soft subtitles.

    Features:
    - 2 channel audio, soft subs, web optimized
    - Shrink file size by ~2/3
    - H.264 encoding with faststart for web streaming
    """
    from pathlib import Path
    from mpv_scraper.video_convert import (
        batch_convert_mkv_to_mp4_with_fallback,
    )

    directory = Path(path)

    if dry_run:
        click.echo(
            f"DRY RUN: Analyzing {directory} for MKV files to convert with subtitles..."
        )
        click.echo(
            "Will attempt with subtitles first, fallback to no subtitles if conversion fails"
        )
    else:
        click.echo(f"Converting MKV files in {directory} to MP4 with subtitles...")
        click.echo(
            "Will attempt with subtitles first, fallback to no subtitles if conversion fails"
        )

    processed, successful = batch_convert_mkv_to_mp4_with_fallback(
        directory, dry_run=dry_run, overwrite=overwrite
    )

    if dry_run:
        click.echo(f"DRY RUN: Would convert {processed} MKV files")
    else:
        click.echo(
            f"Conversion complete: {successful}/{processed} videos converted successfully"
        )


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be analyzed without actually processing videos",
)
def analyze(path, dry_run):
    """Analyze videos in DIRECTORY for handheld playback compatibility.

    Scans video files to identify those that may cause playback issues on handheld
    devices (slow frame rate, audio sync problems). Provides detailed analysis and
    optimization recommendations.

    Detects issues like:
    - HEVC/H.265 codecs (CPU intensive)
    - 10-bit color depth (requires more processing)
    - High bitrates (>3 Mbps)
    - High resolutions (>720p)
    - Complex encoding profiles
    - Large file sizes relative to duration
    """
    from pathlib import Path
    from mpv_scraper.video_cleaner import (
        batch_analyze_videos,
        get_optimization_recommendation,
    )

    directory = Path(path)

    if dry_run:
        click.echo(
            f"DRY RUN: Would analyze videos in {directory} for compatibility issues"
        )
        return

    click.echo(f"Analyzing videos in {directory} for handheld compatibility...")

    all_videos, problematic_videos = batch_analyze_videos(directory, dry_run)

    if not all_videos:
        click.echo("No video files found to analyze")
        return

    click.echo("\nAnalysis Summary:")
    click.echo(f"  Total videos: {len(all_videos)}")
    click.echo(f"  Problematic: {len(problematic_videos)}")
    click.echo(f"  Good: {len(all_videos) - len(problematic_videos)}")

    if problematic_videos:
        click.echo("\nProblematic Videos:")
        for analysis in problematic_videos:
            click.echo(f"  📁 {analysis.file_path.name}")
            click.echo(f"     Codec: {analysis.codec} ({analysis.profile})")
            click.echo(f"     Resolution: {analysis.width}x{analysis.height}")
            click.echo(f"     Bitrate: {analysis.bitrate/1000000:.1f} Mbps")
            click.echo(f"     File size: {analysis.file_size_mb:.1f} MB")
            click.echo(f"     Issues: {', '.join(analysis.issues)}")
            click.echo(f"     Optimization score: {analysis.optimization_score:.2f}")
            click.echo(
                f"     Recommendation: {get_optimization_recommendation(analysis)}"
            )
            click.echo()
    else:
        click.echo("\n✅ All videos are compatible with handheld devices!")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--preset",
    type=click.Choice(["handheld", "compatibility"]),
    default="handheld",
    help="Optimization preset (handheld=balanced, compatibility=maximum compatibility)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be optimized without actually processing videos",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing optimized files",
)
@click.option(
    "--regen-gamelist",
    is_flag=True,
    help="Regenerate gamelist.xml for PATH after optimization completes",
)
def optimize(path, preset, dry_run, overwrite, regen_gamelist):
    """Optimize videos in DIRECTORY for handheld playback.

    Automatically detects problematic videos and optimizes them for smooth playback
    on handheld devices. Creates new optimized files with "_optimized" suffix.

    Presets:
    - handheld: Balanced optimization (H.264, 720p max, 1.5 Mbps)
    - compatibility: Maximum compatibility (H.264, 480p max, 800 kbps)

    Optimizations include:
    - Converting HEVC/H.265 to H.264
    - Reducing bitrate for smoother playback
    - Scaling down high resolutions
    - Converting 10-bit to 8-bit color depth
    - Using faster encoding presets
    """
    from pathlib import Path
    from mpv_scraper.video_cleaner import (
        batch_optimize_videos,
        HANDHELD_OPTIMIZED,
        COMPATIBILITY_MODE,
    )

    directory = Path(path)

    # Map preset names to preset objects
    preset_map = {"handheld": HANDHELD_OPTIMIZED, "compatibility": COMPATIBILITY_MODE}

    selected_preset = preset_map[preset]

    if dry_run:
        click.echo(f"DRY RUN: Would optimize videos in {directory}...")
        click.echo(
            f"Using preset: {selected_preset.name} - {selected_preset.description}"
        )
    else:
        click.echo(f"Optimizing videos in {directory} for handheld compatibility...")
        click.echo(
            f"Using preset: {selected_preset.name} - {selected_preset.description}"
        )

    processed, successful = batch_optimize_videos(
        directory, preset=selected_preset, dry_run=dry_run, overwrite=overwrite
    )

    if dry_run:
        click.echo(f"DRY RUN: Would optimize {processed} videos")
    else:
        click.echo(
            f"Optimization complete: {successful}/{processed} videos optimized successfully"
        )
        if regen_gamelist:
            ctx = click.get_current_context()
            ctx.invoke(generate, path=path)
            click.echo("Regenerated gamelist.xml after optimization")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--preset",
    type=click.Choice(["handheld", "compatibility"]),
    default=None,
    help="Optimization preset (default from config or 'handheld')",
)
@click.option(
    "--workers",
    type=int,
    help="Number of parallel workers (auto-detect if not specified)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be optimized without actually processing videos",
)
@click.option(
    "--replace-originals",
    is_flag=True,
    help="Replace original files with optimized versions (removes originals after successful optimization)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Automatically answer yes to confirmation prompts (dangerous with --replace-originals)",
)
@click.option(
    "--regen-gamelist",
    is_flag=True,
    help="Regenerate gamelist.xml for PATH after optimization completes",
)
def optimize_parallel(
    path, preset, workers, dry_run, replace_originals, yes, regen_gamelist
):
    """Optimize videos in DIRECTORY using parallel processing for faster results.

    Uses multiple CPU cores to process multiple video files simultaneously,
    significantly reducing total processing time. Automatically determines
    optimal number of workers based on system resources.
    """
    from pathlib import Path
    from mpv_scraper.video_cleaner_parallel import (
        parallel_optimize_videos,
        get_optimal_worker_count,
        estimate_parallel_processing_time,
    )

    directory = Path(path)

    # Load config defaults if present in target directory
    from mpv_scraper.utils import load_config

    cfg = load_config(directory)

    # Determine worker count
    if workers is None:
        if cfg.get("workers"):
            workers = int(cfg["workers"])
            click.echo(f"Using {workers} workers (from config)")
        else:
            workers = get_optimal_worker_count()
            click.echo(f"Auto-detected optimal worker count: {workers}")
    else:
        click.echo(f"Using {workers} workers")

    # Select preset configuration
    # Allow config to set default preset if not overridden by flag
    if preset is None:
        if cfg.get("preset") in ("handheld", "compatibility"):
            preset = cfg.get("preset")
        else:
            preset = "handheld"
    if preset == "handheld":
        preset_config = {
            "name": "handheld_optimized",
            "target_codec": "libx264",
            "target_profile": "high",
            "target_bitrate": 1500000,
            "target_resolution": (1280, 720),
            "crf": 23,
            "preset": "faster",
            "tune": "film",
            "audio_codec": "aac",
            "audio_bitrate": 128000,
            "timeout": 1800,
        }
    else:  # compatibility
        preset_config = {
            "name": "compatibility_optimized",
            "target_codec": "libx264",
            "target_profile": "baseline",
            "target_bitrate": 1000000,
            "target_resolution": (854, 480),
            "crf": 28,
            "preset": "ultrafast",
            "tune": "fastdecode",
            "audio_codec": "aac",
            "audio_bitrate": 96000,
            "timeout": 1800,
        }

    # Inform preset choice
    click.echo(f"Using preset: {preset}")

    # Count files for time estimation
    video_files = []
    for ext in [".mp4", ".mkv", ".avi", ".mov"]:
        video_files.extend(directory.glob(f"*{ext}"))

    # Filter out already optimized files and AppleDouble files
    files_to_process = [
        f
        for f in video_files
        if not f.name.startswith("._") and not f.name.endswith("_optimized.mp4")
    ]

    if files_to_process:
        estimated_time = estimate_parallel_processing_time(
            len(files_to_process), 1.0, workers
        )
        click.echo(f"Found {len(files_to_process)} files to process")
        click.echo(f"Estimated processing time: {estimated_time}")

        # Prefer config default for replace_originals when flag omitted
        if replace_originals is False and cfg.get("replace_originals_default"):
            replace_originals = True
        if replace_originals and not dry_run:
            click.echo("⚠️  WARNING: --replace-originals flag is enabled!")
            click.echo(
                "   Original files will be PERMANENTLY DELETED after successful optimization."
            )
            click.echo("   This action cannot be undone!")

            # Calculate space savings
            total_size_gb = sum(f.stat().st_size for f in files_to_process) / (1024**3)
            estimated_optimized_size_gb = (
                total_size_gb * 0.2
            )  # Assume 80% size reduction
            space_savings_gb = total_size_gb - estimated_optimized_size_gb

            click.echo(f"   Estimated space savings: {space_savings_gb:.1f}GB")
            click.echo()

            # Require confirmation unless --yes is provided
            if not yes:
                proceed = click.confirm(
                    "Proceed with deleting originals after successful optimization?",
                    default=False,
                )
                if not proceed:
                    click.echo("Aborted by user.")
                    return 1

    # Run parallel optimization with a progress bar (when we know total count)
    if files_to_process:
        with click.progressbar(
            length=len(files_to_process),
            label="Optimizing videos",
            show_eta=True,
            show_percent=True,
        ) as bar:
            total, successful, errors = parallel_optimize_videos(
                directory=directory,
                preset_config=preset_config,
                max_workers=workers,
                dry_run=dry_run,
                replace_originals=replace_originals,
                progress_callback=lambda n: bar.update(n),
            )
    else:
        total, successful, errors = parallel_optimize_videos(
            directory=directory,
            preset_config=preset_config,
            max_workers=workers,
            dry_run=dry_run,
            replace_originals=replace_originals,
        )

    if dry_run:
        click.echo(f"DRY RUN: Would process {total} videos with {workers} workers")
    else:
        click.echo(
            f"Parallel optimization complete: {successful}/{total} videos optimized successfully"
        )
        if errors:
            click.echo(f"Failed: {len(errors)} videos")
            for error in errors[:5]:  # Show first 5 errors
                click.echo(f"  {error}")
            if len(errors) > 5:
                click.echo(f"  ... and {len(errors) - 5} more errors")
        # Prefer config default for regen_gamelist when flag omitted
        if regen_gamelist is False and cfg.get("regen_gamelist_default"):
            regen_gamelist = True
        if regen_gamelist:
            ctx = click.get_current_context()
            ctx.invoke(generate, path=path)
            click.echo("Regenerated gamelist.xml after optimization")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be converted without actually processing videos",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing MP4 files",
)
def convert_without_subs(path, dry_run, overwrite):
    """Convert MKV files in DIRECTORY to web-optimized MP4 without subtitles.

    Converts MKV files to MP4 format with web optimization, excluding subtitles.
    Reduces file size by ~2/3 while maintaining quality.

    Features:
    - 2 channel audio, no subtitles, web optimized
    - Shrink file size by ~2/3
    - H.264 encoding with faststart for web streaming
    """
    from pathlib import Path
    from mpv_scraper.video_convert import batch_convert_mkv_to_mp4, VANILLA_NO_SUBS

    directory = Path(path)

    if dry_run:
        click.echo(
            f"DRY RUN: Analyzing {directory} for MKV files to convert without subtitles..."
        )
        click.echo(
            f"Using preset: {VANILLA_NO_SUBS.name} - {VANILLA_NO_SUBS.description}"
        )
    else:
        click.echo(f"Converting MKV files in {directory} to MP4 without subtitles...")
        click.echo(
            f"Using preset: {VANILLA_NO_SUBS.name} - {VANILLA_NO_SUBS.description}"
        )

    processed, successful = batch_convert_mkv_to_mp4(
        directory, preset=VANILLA_NO_SUBS, dry_run=dry_run, overwrite=overwrite
    )

    if dry_run:
        click.echo(f"DRY RUN: Would convert {processed} MKV files")
    else:
        click.echo(
            f"Conversion complete: {successful}/{processed} videos converted successfully"
        )


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def run(ctx, path):
    """End-to-end scan → scrape → generate workflow for DIRECTORY."""
    ctx = click.get_current_context()
    ctx.invoke(scan, path=path)
    ctx.invoke(scrape, path=path)
    ctx.invoke(generate, path=path)


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--show",
    help="Specific show name to update (e.g., 'Wild West C.O.W. Boys of Moo Mesa')",
)
@click.option(
    "--force", is_flag=True, help="Force update even if logo files don't exist"
)
def sync_logos(path, show=None, force=False):
    """Sync manually downloaded logos to gamelist.xml entries.

    This command looks for manually downloaded logo files in the images directory
    and updates the gamelist.xml to use them. Expected naming convention:
    - {show}-logo.png
    - {show}-box.png
    - {show}-marquee.png

    Updates marquee and thumbnail fields. If only one file exists, it will be used for both fields.
    """
    from pathlib import Path

    root = Path(path)
    top_images_dir = root / "images"
    gamelist_path = root / "gamelist.xml"

    if not gamelist_path.exists():
        click.echo(f"Error: No gamelist.xml found at {gamelist_path}")
        return 1

    if not top_images_dir.exists():
        click.echo(f"Error: No images directory found at {top_images_dir}")
        return 1

    # Parse existing gamelist.xml
    import xml.etree.ElementTree as ET

    tree = ET.parse(gamelist_path)
    root_elem = tree.getroot()

    # Find all game entries
    updated_count = 0
    shows_processed = set()

    for game_elem in root_elem.findall("game"):
        # Get the show name from the path
        path_elem = game_elem.find("path")
        if path_elem is None:
            continue

        path_text = path_elem.text
        if not path_text:
            continue

        # Extract show name from path (e.g., "./Darkwing Duck/file.mp4" -> "Darkwing Duck")
        show_name = None
        if path_text.startswith("./"):
            parts = path_text[2:].split("/")
            if len(parts) >= 2:
                show_name = parts[0]

        if not show_name:
            continue

        # Skip if specific show requested and this doesn't match
        if show and show_name != show:
            continue

        # Check for logo files
        logo_path = top_images_dir / f"{show_name}-logo.png"
        box_path = top_images_dir / f"{show_name}-box.png"
        marquee_path = top_images_dir / f"{show_name}-marquee.png"

        # Determine which logo file to use
        logo_file = None
        if logo_path.exists():
            logo_file = f"{show_name}-logo.png"
        elif box_path.exists():
            logo_file = f"{show_name}-box.png"
        elif marquee_path.exists():
            logo_file = f"{show_name}-marquee.png"
        elif force:
            # If force is enabled, use logo.png even if it doesn't exist
            logo_file = f"{show_name}-logo.png"
        else:
            continue

        # Update marquee and thumbnail elements to use their specific files when available
        marquee_file = f"{show_name}-marquee.png"
        box_file = f"{show_name}-box.png"
        logo_file = f"{show_name}-logo.png"

        # Remove any existing boxart elements (incorrect field name)
        boxart_elem = game_elem.find("boxart")
        if boxart_elem is not None:
            game_elem.remove(boxart_elem)

        # Use specific files if they exist, otherwise fall back to logo.png
        marquee_elem = game_elem.find("marquee")
        if marquee_elem is not None:
            marquee_elem.text = (
                f"./images/{marquee_file if marquee_path.exists() else logo_file}"
            )
        else:
            marquee_elem = ET.SubElement(game_elem, "marquee")
            marquee_elem.text = (
                f"./images/{marquee_file if marquee_path.exists() else logo_file}"
            )

        thumbnail_elem = game_elem.find("thumbnail")
        if thumbnail_elem is not None:
            thumbnail_elem.text = (
                f"./images/{box_file if box_path.exists() else logo_file}"
            )
        else:
            thumbnail_elem = ET.SubElement(game_elem, "thumbnail")
            thumbnail_elem.text = (
                f"./images/{box_file if box_path.exists() else logo_file}"
            )

        shows_processed.add(show_name)
        updated_count += 1

    if updated_count > 0:
        # Write updated gamelist.xml
        tree.write(gamelist_path, encoding="UTF-8", xml_declaration=True)
        click.echo(
            f"Updated {updated_count} game entries for shows: {', '.join(sorted(shows_processed))}"
        )
        click.echo(f"Updated gamelist.xml at {gamelist_path}")
    else:
        if show:
            click.echo(f"No logo files found for show '{show}' in {top_images_dir}")
            click.echo("Expected files:")
            click.echo(f"  {show}-logo.png")
            click.echo(f"  {show}-box.png")
            click.echo(f"  {show}-marquee.png")
        else:
            click.echo("No logo files found in images directory")
            click.echo(
                "Expected naming convention: {show}-logo.png, {show}-box.png, or {show}-marquee.png"
            )

    return 0


def _sanitize_filenames(root) -> int:
    """Sanitize filenames by removing special characters that can cause display issues.

    This function renames files with special characters (umlauts, tildes, etc.) to their
    ASCII equivalents to ensure proper display in EmulationStation and other systems.

    Returns:
        Number of files renamed
    """
    from mpv_scraper.utils import normalize_text

    renamed_count = 0

    # Find all video files recursively
    for video_file in root.rglob("*.mp4"):
        original_name = video_file.name
        normalized_name = normalize_text(original_name)

        if original_name != normalized_name:
            new_path = video_file.parent / normalized_name

            try:
                video_file.rename(new_path)
                click.echo(f"Sanitized filename: {original_name} -> {normalized_name}")
                renamed_count += 1
            except Exception as e:
                click.echo(f"Error renaming {original_name}: {e}")

    return renamed_count


@main.command()
@click.option("--non-interactive", is_flag=True, help="Render once and exit")
@click.option(
    "--path",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Target library path to monitor (for logs/jobs)",
)
def tui(non_interactive: bool = False, path: str | None = None):
    """Start the mpv-scraper TUI (text UI).

    Optionally pass --path to point the monitor at a specific library root so it
    can read the correct mpv-scraper.log and .mpv-scraper/jobs.json while your
    CLI commands run elsewhere.
    """
    from mpv_scraper.tui import run_tui

    code = run_tui(non_interactive=non_interactive, path=path)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
