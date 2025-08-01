"""MPV Metadata Scraper package.

Exposes high-level APIs for scanning media directories and scraping
metadata. Public entrypoints live in sub-modules (`cli`, `scanner`,
`parser`, `tvdb`, `tmdb`).
"""

__all__ = [
    "cli",
    "scanner",
    "parser",
    "tvdb",
    "images",
    "tmdb",
    "xml_writer",
]
