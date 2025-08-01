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
def run():
    """Scan, scrape, and generate gamelist.xml."""
    click.echo("Running the scraper...")


if __name__ == "__main__":
    main()
