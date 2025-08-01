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
    """Generate gamelist XML for DIRECTORY based on previously scraped data."""
    # Placeholder: In MVP we just echo; actual wiring occurs in Sprint 6.3.
    click.echo(f"Generating gamelist XML for {path} (stub).")


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
