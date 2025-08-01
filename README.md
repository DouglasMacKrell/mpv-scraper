# MPV Metadata Scraper

A command-line tool to automatically scrape metadata for TV shows and movies and generate EmulationStation-compatible `gamelist.xml` files for the Knulli UI.

## Overview

This tool scans a target directory (e.g., `/mpv`) containing TV show and movie media files, fetches metadata from online databases, downloads artwork, and generates the necessary `gamelist.xml` files for a rich media experience in frontends like EmulationStation.

It's designed to work with the Knulli UI's expected directory structure, ensuring that all media is correctly cataloged with titles, descriptions, ratings, release dates, and artwork.

## Project Structure
The project follows a standard `src` layout to ensure clean imports and a clear separation between the application code and project configuration.

```mermaid
graph TD
    A[mpv-scraper] --> B[src];
    A --> C[tests];
    A --> D[docs];
    A --> E[examples];
    A --> F[setup.py];
    A --> G[README.md];
    A --> H[PLANNING.md];

    B --> B1[mpv_scraper];
    B1 --> B2[__init__.py];
    B1 --> B3[cli.py];
    B1 --> B4[parser.py];
```

## Key Features

- **TV & Movie Scraping:** Uses TheTVDB for television series and TheMovieDB for movies.
- **`gamelist.xml` Generation:** Creates EmulationStation-compatible `gamelist.xml` files for the root media folder and each subdirectory.
- **Smart Filename Parsing:** Robustly parses filenames for both TV shows (`Show - S01E01 - Title.ext`) and movies (`Movie (Year).ext`).
- **Anthology Span Support:** Correctly handles TV episode ranges (e.g., `S01E09-E10`), combining metadata and titles appropriately.
- **Image Processing:** Downloads artwork, converts it to PNG, and optimizes it to be under 600KB for performance.
- **Interactive Mode:** Prompts the user to resolve ambiguities when multiple search results are found. The user's choice is for the current session only and is not saved.
- **API Key Management:** Loads API keys securely from environment variables.

## Tech Stack

- **Language:** Python 3.9+
- **CLI Framework:** Click
- **Core Libraries:**
  - `requests` for API communication
  - `Pillow` for image processing
  - `lxml` for XML generation

## Target Directory Structure

The scraper expects and generates the following structure within the main media folder (e.g., `/mpv`):

```
/mpv
├── gamelist.xml              # Top-level gamelist with <folder> entries for shows/movies
├── Movies/
│   ├── gamelist.xml          # Gamelist for all movies
│   ├── Movie Title (Year).mp4
│   └── images/
│       └── Movie Title (Year).png
└── <Show Name>/
    ├── gamelist.xml          # Gamelist for this show's episodes
    ├── Show - S01E01 - Title.mp4
    └── images/
        ├── poster.png        # Show poster
        └── S01E01.png        # Episode thumbnail
```

## Installation and Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd mpv-scraper
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up API keys:**
    Export your API keys as environment variables.
    ```bash
    export TVDB_API_KEY="YOUR_TVDB_API_KEY"
    export TMDB_API_KEY="YOUR_TMDB_API_KEY"
    ```

## Usage

The tool will provide several commands to manage the scraping process. The primary command will be `run`, which executes the entire workflow.

```bash
# Run the full scraping and generation process on the /mpv directory
python -m mpv_scraper.cli run /path/to/your/mpv/folder
```
<!-- ci trigger -->
