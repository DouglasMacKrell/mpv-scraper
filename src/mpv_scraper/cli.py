"""Command-line interface entrypoint for MPV Metadata Scraper.

Commands
========
scan PATH
    Scan a media directory and output a brief summary of shows/movies discovered.

generate PATH
    Generate *gamelist.xml* files for the directory using metadata previously scraped (stub for now).

run PATH
    Convenience wrapper that performs *scan* ➜ (future) *scrape* ➜ *generate* in sequence.
"""

import click
from dotenv import load_dotenv
from mpv_scraper.images import create_placeholder_png

# Load environment variables from .env file
load_dotenv()

# --- Test-only placeholder hook ---------------------------------------------


def _noop_placeholder(*_args, **_kwargs):
    """No-op; real implementation is monkey-patched in tests."""


# -----------------------------------------------------------------------------


@click.group()
def main():
    """A CLI tool to scrape metadata for TV shows and movies."""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def scan(path):
    """Scan DIRECTORY and print a summary (debug helper)."""
    from pathlib import Path
    from mpv_scraper.scanner import scan_directory

    result = scan_directory(Path(path))
    click.echo(
        f"Found {len(result.shows)} show folders and {len(result.movies)} movies."
    )


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def scrape(path):
    """Scrape metadata and artwork for DIRECTORY.

    Scans *path* and downloads:

    * TV show metadata from TVDB (episodes, ratings, descriptions)
    * Movie metadata from TMDB (overview, ratings, release dates)
    * Poster images for shows and movies
    * Logo artwork for marquee display
    * Caches all metadata for later generate step
    """
    from pathlib import Path
    from mpv_scraper.scanner import scan_directory
    from mpv_scraper.scraper import scrape_tv, scrape_movie
    from mpv_scraper.transaction import TransactionLogger

    root = Path(path)
    logger = TransactionLogger(root / "transaction.log")  # Create in target directory

    def _log_creation(p: Path) -> None:
        logger.log_create(p.resolve())

    # 1. Scan directory
    result = scan_directory(root)
    click.echo(
        f"Found {len(result.shows)} show folders and {len(result.movies)} movies."
    )

    # 2. Scrape TV shows
    for show in result.shows:
        click.echo(f"Scraping {show.path.name}...")
        try:
            scrape_tv(show.path, logger)
            click.echo(f"✓ Scraped {show.path.name}")
        except Exception as e:
            click.echo(f"✗ Failed to scrape {show.path.name}: {e}")

    # 3. Scrape movies
    for movie in result.movies:
        click.echo(f"Scraping {movie.path.name}...")
        try:
            scrape_movie(movie.path, logger)
            click.echo(f"✓ Scraped {movie.path.name}")
        except Exception as e:
            click.echo(f"✗ Failed to scrape {movie.path.name}: {e}")

    click.echo("Scraping completed.")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def generate(path):
    """Generate gamelist XML for DIRECTORY.

    Scans *path* and writes:

    * Top-level ``gamelist.xml`` listing show folders + *Movies*
    * Per-show / *Movies* ``gamelist.xml`` with <game> entries
    * Minimal placeholder PNG artwork so the test suite can run without real API calls.
    """
    from pathlib import Path

    from mpv_scraper.parser import parse_tv_filename, parse_movie_filename
    from mpv_scraper.scanner import scan_directory
    from mpv_scraper.xml_writer import write_top_gamelist, write_show_gamelist
    from mpv_scraper.transaction import TransactionLogger
    from typing import Union
    import json

    root = Path(path)
    logger = TransactionLogger(root / "transaction.log")  # Create in target directory

    def _log_creation(p: Path) -> None:
        logger.log_create(p.resolve())

    def _load_scrape_cache(cache_path: Path) -> Union[dict, None]:
        """Load scrape cache if it exists."""
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text())
            except (json.JSONDecodeError, OSError):
                return None
        return None

    # 1. Create top-level images directory for folder-level images
    top_images_dir = root / "images"
    if not top_images_dir.exists():
        top_images_dir.mkdir(parents=True, exist_ok=True)
        _log_creation(top_images_dir)

    # 2. Scan directory
    result = scan_directory(root)

    folder_entries = []  # Data for the top-level gamelist

    # 3. Per-show gamelists and posters
    for show in result.shows:
        images_dir = show.path / "images"
        if not images_dir.exists():
            images_dir.mkdir(parents=True, exist_ok=True)
            _log_creation(images_dir)

        # Create show poster (use real image if available, otherwise placeholder)
        poster_path = images_dir / "poster.png"
        if not poster_path.exists():
            create_placeholder_png(poster_path)
            _log_creation(poster_path)

        # Create show logo (use real image if available, otherwise placeholder)
        logo_path = images_dir / "logo.png"
        if not logo_path.exists():
            create_placeholder_png(logo_path)
            _log_creation(logo_path)

        # Create top-level image for this series folder
        top_show_poster = top_images_dir / f"{show.path.name}.png"
        if not top_show_poster.exists() and poster_path.exists():
            # Copy the show's poster to top-level
            import shutil

            shutil.copy2(poster_path, top_show_poster)
            _log_creation(top_show_poster)

        folder_entries.append(
            {
                "path": f"./{show.path.name}",
                "name": show.path.name,
                "image": (
                    f"./images/{show.path.name}.png"
                    if top_show_poster.exists()
                    else f"./{show.path.name}/images/poster.png"
                ),
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

            img_name = (
                f"S{meta.season:02d}E{meta.start_ep:02d}-image.png"
                if meta
                else f"{file_path.stem}-image.png"
            )
            img_path = images_dir / img_name
            if not img_path.exists():
                create_placeholder_png(img_path)
                _log_creation(img_path)

            # Create thumbnail version
            thumb_name = (
                f"S{meta.season:02d}E{meta.start_ep:02d}-thumb.png"
                if meta
                else f"{file_path.stem}-thumb.png"
            )
            thumb_path = images_dir / thumb_name
            if not thumb_path.exists():
                create_placeholder_png(thumb_path)
                _log_creation(thumb_path)

            # Get metadata from scrape cache if available
            desc = None
            rating = 0.0
            marquee = (
                "./images/logo.png"  # Will be updated below if proper marquee exists
            )
            releasedate = None
            genre = None
            developer = None
            publisher = None
            video = None
            lang = "en"

            # Check if show-specific marquee exists
            marquee_path = images_dir / "logo.png"
            if marquee_path.exists():
                marquee = "./images/logo.png"
            else:
                # Try the proper EmulationStation naming convention
                proper_marquee_path = images_dir / f"{show.path.name}-marquee.png"
                if proper_marquee_path.exists():
                    marquee = f"./images/{show.path.name}-marquee.png"

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

            game_entry = {
                "path": f"./{file_path.relative_to(root)}",
                "name": name,
                "image": f"./images/{img_name}",
                "rating": rating,
                "marquee": marquee,
                "thumbnail": f"./images/{thumb_name}",
                "lang": lang,
            }

            if desc:
                game_entry["desc"] = desc
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

        show_gamelist_path = show.path / "gamelist.xml"
        write_show_gamelist(games, show_gamelist_path)
        _log_creation(show_gamelist_path)

    # 4. Movies folder (optional)
    movies_dir = root / "Movies"
    if movies_dir.exists():
        images_dir = movies_dir / "images"
        if not images_dir.exists():
            images_dir.mkdir(parents=True, exist_ok=True)
            _log_creation(images_dir)

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

            # Also copy to Movies/images/poster.png for consistency
            movies_poster_dest = images_dir / "poster.png"
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
                "image": (
                    "./images/movies-poster.jpg"
                    if (top_images_dir / "movies-poster.jpg").exists()
                    else "./Movies/images/poster.png"
                ),
            }
        )

        games = []
        for movie_file in result.movies:
            meta = parse_movie_filename(movie_file.path.name)
            name = meta.title if meta else movie_file.path.stem
            img_name = f"{movie_file.path.stem}-image.png"
            img_path = images_dir / img_name

            # Only create placeholder if no real image exists
            if not img_path.exists():
                create_placeholder_png(img_path)
                _log_creation(img_path)

            # Create thumbnail version
            thumb_name = f"{movie_file.path.stem}-thumb.png"
            thumb_path = images_dir / thumb_name
            if not thumb_path.exists():
                create_placeholder_png(thumb_path)
                _log_creation(thumb_path)

            # Get metadata from individual movie cache if available
            desc = None
            rating = 0.0
            marquee = None  # Will be set below if logo exists
            releasedate = None
            genre = None
            developer = None
            publisher = None
            video = None
            lang = "en"

            movie_cache_file = movies_dir / ".scrape_cache.json"
            movie_cache = _load_scrape_cache(movie_cache_file)
            if movie_cache:
                desc = movie_cache.get("overview")
                # TMDB ratings are already normalized 0-1
                rating = movie_cache.get("vote_average", 0.0)
                # Format release date
                from mpv_scraper.utils import format_release_date

                releasedate = format_release_date(movie_cache.get("release_date"))
                # Get genre
                if movie_cache.get("genre_names"):
                    genre = ", ".join(movie_cache.get("genre_names", []))
                # Get production company as developer
                if movie_cache.get("production_company_names"):
                    developer = movie_cache.get("production_company_names", [])[0]
                # Get distributor as publisher
                if movie_cache.get("distributor"):
                    publisher = movie_cache.get("distributor")

            # Check if movie-specific logo exists
            logo_name = f"{movie_file.path.stem}-logo.png"
            logo_path = images_dir / logo_name
            marquee_name = f"{movie_file.path.stem}-marquee.png"
            marquee_path = images_dir / marquee_name

            if marquee_path.exists():
                marquee = f"./images/{marquee_name}"
            elif logo_path.exists():
                marquee = f"./images/{logo_name}"

            game_entry = {
                "path": f"./{movie_file.path.relative_to(root)}",
                "name": name,
                "image": f"./images/{img_name}",
                "rating": rating,
                "thumbnail": f"./images/{thumb_name}",
                "lang": lang,
            }

            if desc:
                game_entry["desc"] = desc
            if marquee:
                game_entry["marquee"] = marquee
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
        movies_gamelist_path = movies_dir / "gamelist.xml"
        write_show_gamelist(games, movies_gamelist_path)
        _log_creation(movies_gamelist_path)

    # 5. Top-level gamelist
    top_gamelist_path = root / "gamelist.xml"
    write_top_gamelist(folder_entries, top_gamelist_path)
    _log_creation(top_gamelist_path)

    click.echo("gamelist.xml files generated.")


@main.command()
def undo():
    """Undo the most recent scraper run using *transaction.log* in cwd."""
    from pathlib import Path
    from mpv_scraper.transaction import revert_transaction

    # Look for transaction.log in current directory first, then parent
    log_path = Path("transaction.log")
    if not log_path.exists():
        log_path = Path("../transaction.log")
        if not log_path.exists():
            click.echo(
                "No transaction.log found in current directory or parent directory."
            )
            return 0
    revert_transaction(log_path)
    click.echo("Undo completed.")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def run(ctx, path):
    """End-to-end scan → scrape → generate workflow for DIRECTORY."""
    ctx = click.get_current_context()
    ctx.invoke(scan, path=path)
    ctx.invoke(scrape, path=path)
    ctx.invoke(generate, path=path)


if __name__ == "__main__":
    main()
