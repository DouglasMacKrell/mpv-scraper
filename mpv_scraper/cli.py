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
