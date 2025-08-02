# Quick Start Guide

Welcome to **MPV Metadata Scraper**!  This guide walks you through getting the tool running quickly on your machine and integrating it with Knulli UI.

---

## Prerequisites

1. **Python 3.9+** (the project currently supports Python 3.9 or newer).
2. **TheTVDB** and **TheMovieDB** API keys.
   * Create free accounts and generate keys:
     * TVDB: <https://thetvdb.com/dashboard/api>
     * TMDB: <https://www.themoviedb.org/settings/api>
3. A media folder resembling:
   ```text
   /mpv
     ├── Movies/
     └── <Show Name>/
   ```

---

## Installation

```bash
# Clone the repo
git clone https://github.com/<your-username>/mpv-scraper.git
cd mpv-scraper

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configure API Keys

Export your keys as environment variables **in the same shell session** where you will run the scraper:

```bash
export TVDB_API_KEY="YOUR_TVDB_API_KEY"
export TMDB_API_KEY="YOUR_TMDB_API_KEY"
```

You can add these lines to your shell profile (e.g., `~/.zshrc`) for persistence.

---

## Reverting Changes

If you run the scraper and want to undo the filesystem changes it made, simply run:

```bash
python -m mpv_scraper.cli undo
```

The command consumes the generated `transaction.log` (created during a run) and restores the previous state.

---

## Artwork & Extended Metadata

All downloaded artwork is automatically saved as PNGs, including series/movie logo files used for the EmulationStation `<marquee>` tag.  If an image is wider than **500 px** or the file exceeds **600 KB**, the scraper resizes it proportionally and applies additional compression so it always meets EmulationStation performance recommendations.

## Error Handling & Resilience

The scraper includes robust error handling to ensure successful completion:

- **Automatic Retries:** Network downloads retry up to 3 times with exponential backoff
- **Placeholder Images:** If artwork downloads fail, transparent placeholder PNGs are created automatically
- **Graceful Degradation:** Missing artwork doesn't prevent metadata scraping or XML generation
- **Partial Success:** The scraper continues processing even if some operations fail

This means your scraping will complete successfully even with poor network conditions or missing artwork.

---

## Running the Scraper

The scraper provides several commands for different workflows:

### Full Workflow (Recommended)
```bash
python -m mpv_scraper.cli run /mpv
```

This performs the complete workflow:
1. **Scan** the directory for TV shows and movies
2. **Scrape** metadata and artwork from TVDB/TMDB
3. **Generate** EmulationStation-compatible `gamelist.xml` files

### Individual Commands
You can also run each step separately:

```bash
# Step 1: Scan directory (debug helper)
python -m mpv_scraper.cli scan /mpv

# Step 2: Scrape metadata and artwork
python -m mpv_scraper.cli scrape /mpv

# Step 3: Generate XML files
python -m mpv_scraper.cli generate /mpv
```

The scraper will prompt for ambiguous titles and automatically retry failed downloads.

You should end up with a structure like:

```text
/mpv
  ├ gamelist.xml                # top-level
  ├ Movies/
  │   ├ gamelist.xml
  │   └ images/
  └ <Show Name>/
      ├ gamelist.xml
      └ images/
```

---

## Available Commands

The scraper provides these commands:

- **`scan`** - Discover shows and movies in a directory
- **`scrape`** - Download metadata and artwork from TVDB/TMDB
- **`generate`** - Create gamelist.xml files from scraped data
- **`run`** - Complete workflow (scan → scrape → generate)
- **`undo`** - Revert the last run using transaction.log

All commands support the `--help` flag for detailed usage information.

---

## Running the Test Suite

After installing dev dependencies you can execute all tests with:

```bash
pytest -q
```

Common filters:

* Only end-to-end pipeline: `pytest -k e2e`
* Only smoke tests: `pytest -k smoke`

Refer to [docs/TESTING.md](TESTING.md) for detailed guidance.

---

## Troubleshooting

* **Environment variable errors** – ensure `TVDB_API_KEY` and `TMDB_API_KEY` are exported.
* **Rate limiting** – the scraper respects API limits; if you scrape a large library, the run may pause briefly between requests.
* **Network failures** – the scraper automatically retries failed downloads; if you see placeholder images, some artwork downloads failed but processing continued.
* **Incorrect matches** – the CLI will prompt for ambiguous titles; re-run the scraper if you made a wrong selection.

---

Happy scraping!
