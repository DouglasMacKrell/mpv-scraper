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
- **Image Processing:** Downloads artwork, converts it to PNG, automatically resizes/compresses to stay under 600 KB (max 500 px width) for fast loading.
- **Error Handling & Retry Logic:** Robust retry mechanism with exponential backoff for network failures, graceful fallbacks for missing artwork.
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
│       ├── Movie Title (Year).png
│       └── logo.png              # Movie collection logo (marquee)
└── <Show Name>/
    ├── gamelist.xml          # Gamelist for this show's episodes
    ├── Show - S01E01 - Title.mp4
    └── images/
        ├── poster.png        # Show poster
        ├── logo.png          # Show logo (marquee)
        └── S01E01.png        # Episode thumbnail
```

## CLI Usage

After installing the package and activating your virtual-environment you can invoke the scraper via **Click** commands:

```bash
# View help
python -m mpv_scraper.cli --help

# Scan a directory (discover shows and movies)
python -m mpv_scraper.cli scan /mpv

# Scrape metadata and artwork from TVDB/TMDB
python -m mpv_scraper.cli scrape /mpv

# Generate gamelist.xml files (requires scraped metadata)
python -m mpv_scraper.cli generate /mpv

# Undo (rollback the last run)
python -m mpv_scraper.cli undo

# Full workflow – scan ➜ scrape ➜ generate
python -m mpv_scraper.cli run /mpv
```

### Extended Metadata Example

After the scrape you’ll see additional tags in each `<game>` entry:

```xml
<game>
  <path>./Paw Patrol - S04E01-E02 - Pups Save a Blimp &amp; Pups Save the Chili Cook-Off.mp4</path>
  <name>Pups Save a Blimp &amp; Pups Save the Chili Cook-Off – S04E01-E02</name>
  <desc>When Mayor Humdinger causes trouble…</desc>
  <image>./images/S04E01.png</image>
  <marquee>./images/logo.png</marquee>
  <rating>0.78</rating>
</game>
```


---

## Quick Start

For the fastest path, read the step-by-step guide in [docs/QUICK_START.md](docs/QUICK_START.md).

👉 **Running tests?** See [docs/TESTING.md](docs/TESTING.md) for details.

👉 **Error handling details?** See [docs/error_handling.md](docs/error_handling.md) for comprehensive information about retry logic and resilience features.

👉 **API issues?** See [docs/API_TROUBLESHOOTING.md](docs/API_TROUBLESHOOTING.md) for help with TVDB and TMDB authentication problems.

👉 **Performance optimization?** See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for tips on optimizing large library processing.

---

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

5.  **Install pre-commit hooks (recommended):**
    ```bash
    pip install pre-commit
    pre-commit install
    ```

## Development Workflow

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality and test coverage:

- **Code Formatting:** Black and Ruff automatically format and lint your code
- **Tests:** Pytest runs automatically before each commit
- **Smart Test Selection:** The pre-commit hook intelligently runs only relevant tests based on changed files

### Pre-push Hooks

A Git pre-push hook ensures all tests pass before pushing to remote:

- **Full Test Suite:** Runs the complete test suite before allowing push
- **Automatic Blocking:** Push is blocked if any tests fail
- **Helpful Error Messages:** Provides clear guidance on fixing test failures

### Running Tests Manually

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/e2e/          # End-to-end tests
python -m pytest tests/integration/  # Integration tests
python -m pytest tests/smoke/        # Smoke tests

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=mpv_scraper
```

## Usage

The tool will provide several commands to manage the scraping process. The primary command will be `run`, which executes the entire workflow.

```bash
# Run the full scraping and generation process on the /mpv directory
python -m mpv_scraper.cli run /path/to/your/mpv/folder
```

## Error Handling & Resilience

The scraper is designed to be resilient to common failures:

- **Network Retries:** Download functions automatically retry up to 3 times with exponential backoff (1s, 2s, 4s delays)
- **Missing Artwork:** If poster or logo downloads fail, placeholder PNG images are created automatically
- **Partial Failures:** The scraper continues processing even if some operations fail, ensuring metadata is still captured
- **Graceful Degradation:** Missing artwork doesn't prevent metadata scraping or XML generation

This ensures the scraper completes successfully even in challenging network conditions or when some artwork is unavailable.
<!-- ci trigger -->
