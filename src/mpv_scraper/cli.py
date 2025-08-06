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

    # 3. Scrape TV shows
    for show in result.shows:
        click.echo(f"Scraping {show.path.name}...")
        try:
            scrape_tv(show.path, logger, top_images_dir)
            click.echo(f"✓ Scraped {show.path.name}")
        except Exception as e:
            click.echo(f"✗ Failed to scrape {show.path.name}: {e}")

    # 4. Scrape movies
    for movie in result.movies:
        click.echo(f"Scraping {movie.path.name}...")
        try:
            scrape_movie(movie.path, logger, top_images_dir)
            click.echo(f"✓ Scraped {movie.path.name}")
        except Exception as e:
            click.echo(f"✗ Failed to scrape {movie.path.name}: {e}")

    click.echo("Scraping completed.")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def generate(path):
    """Generate gamelist.xml files from scraped metadata."""
    
    from pathlib import Path
    
    # First, sanitize any filenames with special characters
    root = Path(path)
    sanitized_count = _sanitize_filenames(root)
    if sanitized_count > 0:
        click.echo(f"Sanitized {sanitized_count} filenames with special characters.")
    
    """Generate gamelist.xml files for all TV shows and movies."""
    from mpv_scraper.parser import parse_tv_filename, parse_movie_filename
    from mpv_scraper.scanner import scan_directory
    from mpv_scraper.xml_writer import write_top_gamelist, write_show_gamelist
    from mpv_scraper.transaction import TransactionLogger
    from mpv_scraper.images import create_placeholder_png
    from typing import Union
    import json
    import shutil

    root = Path(path)
    logger = TransactionLogger(root / "transaction.log")  # Create in target directory

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
            marquee = (
                "./images/logo.png"  # Will be updated below if proper marquee exists
            )
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
            show_marquee_path = f"./images/{show.path.name}-marquee.png"
            show_box_path = f"./images/{show.path.name}-box.png"

            # Create images in top-level images directory with episode number naming
            if meta:
                ep_span = f"S{meta.season:02d}E{meta.start_ep:02d}"
                if meta.end_ep != meta.start_ep:
                    ep_span += f"-E{meta.end_ep:02d}"
                img_name = f"{show.path.name} - {ep_span}-image.png"  # e.g., "Darkwing Duck - S01E01-image.png"
                thumb_name = f"{show.path.name} - {ep_span}-thumb.png"
            else:
                img_name = f"{show.path.name} - {file_path.stem.split(' - ')[-1]}-image.png"
                thumb_name = f"{show.path.name} - {file_path.stem.split(' - ')[-1]}-thumb.png"
                
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
                    click.echo(f"Failed to generate fallback screenshot for {file_path.name}")
            else:
                click.echo(f"Using API image for {file_path.name}")

            # Create marquee and box images for show (once per show)
            show_marquee_name = f"{show.path.name}-marquee.png"
            show_box_name = f"{show.path.name}-box.png"
            show_marquee_path = top_images_dir / show_marquee_name
            show_box_path = top_images_dir / show_box_name
            
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

            movie_cache = _load_scrape_cache(movie_file.path.parent / ".scrape_cache.json")
            if movie_cache and meta:
                # Find movie in cache
                for movie in movie_cache.get("movies", []):
                    if movie.get("title") == meta.title:
                        desc = movie.get("overview")
                        rating = movie.get("vote_average", 0.0) / 10.0  # Normalize to 0-1
                        from mpv_scraper.utils import format_release_date

                        releasedate = format_release_date(movie.get("release_date"))
                        if movie.get("genres"):
                            genre = ", ".join([g.get("name", "") for g in movie["genres"]])
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
    from mpv_scraper.xml_writer import write_top_gamelist
    write_top_gamelist(folder_entries + all_games, top_gamelist_path)
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


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--show", help="Specific show name to update (e.g., 'Wild West C.O.W. Boys of Moo Mesa')")
@click.option("--force", is_flag=True, help="Force update even if logo files don't exist")
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
            marquee_elem.text = f"./images/{marquee_file if marquee_path.exists() else logo_file}"
        else:
            marquee_elem = ET.SubElement(game_elem, "marquee")
            marquee_elem.text = f"./images/{marquee_file if marquee_path.exists() else logo_file}"
            
        thumbnail_elem = game_elem.find("thumbnail")
        if thumbnail_elem is not None:
            thumbnail_elem.text = f"./images/{box_file if box_path.exists() else logo_file}"
        else:
            thumbnail_elem = ET.SubElement(game_elem, "thumbnail")
            thumbnail_elem.text = f"./images/{box_file if box_path.exists() else logo_file}"
            
        shows_processed.add(show_name)
        updated_count += 1
    
    if updated_count > 0:
        # Write updated gamelist.xml
        tree.write(gamelist_path, encoding="UTF-8", xml_declaration=True)
        click.echo(f"Updated {updated_count} game entries for shows: {', '.join(sorted(shows_processed))}")
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
            click.echo("Expected naming convention: {show}-logo.png, {show}-box.png, or {show}-marquee.png")
    
    return 0


def _sanitize_filenames(root: "Path") -> int:
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


if __name__ == "__main__":
    main()
