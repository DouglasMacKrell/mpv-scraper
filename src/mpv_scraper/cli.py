"""Command-line interface entrypoint for MPV Metadata Scraper.

This module wires up Click commands that allow users to execute the full
workflow (scan, scrape, generate) from the terminal.  Additional commands
such as `undo` will be introduced in later sprints.
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
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def run(path):
    """End-to-end scan → scrape → generate workflow for DIRECTORY."""
    ctx = click.get_current_context()
    ctx.invoke(scan, path=path)
    # Scrape step would go here (TVDB/TMDB calls) – mocked in tests.
    ctx.invoke(generate, path=path)


if __name__ == "__main__":
    main()
