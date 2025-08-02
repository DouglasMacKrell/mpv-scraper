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

    from mpv_scraper.images import create_placeholder_png
    from mpv_scraper.parser import parse_tv_filename, parse_movie_filename
    from mpv_scraper.scanner import scan_directory
    from mpv_scraper.xml_writer import write_top_gamelist, write_show_gamelist

    root = Path(path)

    # 1. Scan directory
    result = scan_directory(root)

    folder_entries = []  # Data for the top-level gamelist

    # 2. Per-show gamelists and posters
    for show in result.shows:
        images_dir = show.path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        poster_path = images_dir / "poster.png"
        create_placeholder_png(poster_path)

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

            games.append(
                {
                    "path": f"./{file_path.relative_to(root)}",
                    "name": name,
                    "image": f"./images/{img_name}",
                }
            )

        write_show_gamelist(games, show.path / "gamelist.xml")

    # 3. Movies folder (optional)
    movies_dir = root / "Movies"
    if movies_dir.exists():
        images_dir = movies_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        poster_path = images_dir / "poster.png"
        create_placeholder_png(poster_path)

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

            games.append(
                {
                    "path": f"./{movie_file.path.relative_to(root)}",
                    "name": name,
                    "image": f"./images/{img_name}",
                }
            )
        write_show_gamelist(games, movies_dir / "gamelist.xml")

    # 4. Top-level gamelist
    write_top_gamelist(folder_entries, root / "gamelist.xml")

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
