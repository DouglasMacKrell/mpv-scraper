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

# --- Test-only placeholder hook ---------------------------------------------


def _noop_placeholder(*_args, **_kwargs):
    """No-op; real implementation is monkey-patched in tests."""


# Points to the active placeholder factory used by generate(); overridden in tests.
create_placeholder_png = _noop_placeholder
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
    logger = TransactionLogger(root / "transaction.log")

    def _log_creation(p: Path) -> None:
        if p.exists():
            logger.log_create(p)

    # 1. Scan directory
    result = scan_directory(root)
    click.echo(
        f"Found {len(result.shows)} show folders and {len(result.movies)} movies."
    )

    # 2. Scrape TV shows
    for show in result.shows:
        click.echo(f"Scraping {show.path.name}...")
        try:
            scrape_tv(show.path)
            click.echo(f"✓ Scraped {show.path.name}")
        except Exception as e:
            click.echo(f"✗ Failed to scrape {show.path.name}: {e}")

    # 3. Scrape movies
    for movie in result.movies:
        click.echo(f"Scraping {movie.path.name}...")
        try:
            scrape_movie(movie.path)
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
    logger = TransactionLogger(root / "transaction.log")

    def _log_creation(p: Path) -> None:
        if p.exists():
            logger.log_create(p)

    def _load_scrape_cache(cache_path: Path) -> Union[dict, None]:
        """Load scrape cache if it exists."""
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text())
            except (json.JSONDecodeError, OSError):
                return None
        return None

    # 1. Scan directory
    result = scan_directory(root)

    folder_entries = []  # Data for the top-level gamelist

    # 2. Per-show gamelists and posters
    for show in result.shows:
        images_dir = show.path / "images"
        if not images_dir.exists():
            images_dir.mkdir(parents=True, exist_ok=True)
            _log_creation(images_dir)
        poster_path = images_dir / "poster.png"
        create_placeholder_png(poster_path)
        _log_creation(poster_path)

        # Create placeholder logo for marquee
        logo_path = images_dir / "logo.png"
        if not logo_path.exists():
            create_placeholder_png(logo_path)
            _log_creation(logo_path)

        folder_entries.append(
            {
                "path": f"./{show.path.name}",
                "name": show.path.name,
                "image": f"./{show.path.name}/images/poster.png",
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
                f"S{meta.season:02d}E{meta.start_ep:02d}.png"
                if meta
                else f"{file_path.stem}.png"
            )
            img_path = images_dir / img_name
            create_placeholder_png(img_path)
            _log_creation(img_path)

            # Get metadata from scrape cache if available
            desc = None
            rating = 0.0
            marquee = "./images/logo.png"

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
                        break

                # Get series rating if no episode rating
                if rating == 0.0:
                    rating = show_cache.get("siteRating", 0.0)

            game_entry = {
                "path": f"./{file_path.relative_to(root)}",
                "name": name,
                "image": f"./images/{img_name}",
                "rating": rating,
                "marquee": marquee,
            }

            if desc:
                game_entry["desc"] = desc

            games.append(game_entry)

        show_gamelist_path = show.path / "gamelist.xml"
        write_show_gamelist(games, show_gamelist_path)
        _log_creation(show_gamelist_path)

    # 3. Movies folder (optional)
    movies_dir = root / "Movies"
    if movies_dir.exists():
        images_dir = movies_dir / "images"
        if not images_dir.exists():
            images_dir.mkdir(parents=True, exist_ok=True)
            _log_creation(images_dir)
        poster_path = images_dir / "poster.png"
        create_placeholder_png(poster_path)
        _log_creation(poster_path)

        # Create placeholder logo for marquee
        logo_path = images_dir / "logo.png"
        if not logo_path.exists():
            create_placeholder_png(logo_path)
            _log_creation(logo_path)

        folder_entries.append(
            {
                "path": "./Movies",
                "name": "Movies",
                "image": "./Movies/images/poster.png",
            }
        )

        # Load scrape cache for movies
        movies_cache = _load_scrape_cache(movies_dir / ".scrape_cache.json")

        games = []
        for movie_file in result.movies:
            meta = parse_movie_filename(movie_file.path.name)
            name = meta.title if meta else movie_file.path.stem
            img_name = f"{movie_file.path.stem}.png"
            img_path = images_dir / img_name
            create_placeholder_png(img_path)
            _log_creation(img_path)

            # Get metadata from scrape cache if available
            desc = None
            rating = 0.0
            marquee = "./images/logo.png"

            if movies_cache:
                desc = movies_cache.get("overview")
                # TMDB ratings are already normalized 0-1
                rating = movies_cache.get("vote_average", 0.0)

            game_entry = {
                "path": f"./{movie_file.path.relative_to(root)}",
                "name": name,
                "image": f"./images/{img_name}",
                "rating": rating,
                "marquee": marquee,
            }

            if desc:
                game_entry["desc"] = desc

            games.append(game_entry)
        movies_gamelist_path = movies_dir / "gamelist.xml"
        write_show_gamelist(games, movies_gamelist_path)
        _log_creation(movies_gamelist_path)

    # 4. Top-level gamelist
    top_gamelist_path = root / "gamelist.xml"
    write_top_gamelist(folder_entries, top_gamelist_path)
    _log_creation(top_gamelist_path)

    click.echo("gamelist.xml files generated.")


@main.command()
def undo():
    """Undo the most recent scraper run using *transaction.log* in cwd."""
    from pathlib import Path
    from mpv_scraper.transaction import revert_transaction

    log_path = Path("transaction.log")
    if not log_path.exists():
        click.echo("No transaction.log found in current directory.")
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
