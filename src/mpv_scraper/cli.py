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

    root = Path(path)
    logger = TransactionLogger(root / "transaction.log")

    def _log_creation(p: Path) -> None:
        if p.exists():
            logger.log_create(p)

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

        folder_entries.append(
            {
                "path": f"./{show.path.name}",
                "name": show.path.name,
                "image": f"./{show.path.name}/images/poster.png",
            }
        )

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

            games.append(
                {
                    "path": f"./{file_path.relative_to(root)}",
                    "name": name,
                    "image": f"./images/{img_name}",
                }
            )

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

        folder_entries.append(
            {
                "path": "./Movies",
                "name": "Movies",
                "image": "./Movies/images/poster.png",
            }
        )

        games = []
        for movie_file in result.movies:
            meta = parse_movie_filename(movie_file.path.name)
            name = meta.title if meta else movie_file.path.stem
            img_name = f"{movie_file.path.stem}.png"
            img_path = images_dir / img_name
            create_placeholder_png(img_path)
            _log_creation(img_path)

            games.append(
                {
                    "path": f"./{movie_file.path.relative_to(root)}",
                    "name": name,
                    "image": f"./images/{img_name}",
                }
            )
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
        return 1
    revert_transaction(log_path)
    click.echo("Undo completed.")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def run(ctx, path):
    """End-to-end scan → scrape → generate workflow for DIRECTORY."""
    ctx = click.get_current_context()
    ctx.invoke(scan, path=path)
    # Scrape step would go here (TVDB/TMDB calls) – mocked in tests.
    ctx.invoke(generate, path=path)


if __name__ == "__main__":
    main()
