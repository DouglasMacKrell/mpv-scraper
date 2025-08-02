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

## Artwork Handling

All downloaded artwork is automatically saved as PNGs.  If an image is wider than **500 px** or the file exceeds **600 KB**, the scraper resizes it proportionally and applies additional compression so it always meets EmulationStation performance recommendations.

---

## Running the Scraper

Assuming your media lives in `/mpv`:

```bash
python -m mpv_scraper.cli run /mpv
```

The command will:

1. Scan the directory for TV shows and movies.
2. Fetch metadata and artwork (prompting if ambiguous titles are found).
3. Generate EmulationStation‐compatible `gamelist.xml` files and PNG images.

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

## Common Flags (coming soon)

Additional CLI flags will be introduced in later sprints—for example `--dry-run`, `--verbose`, and `undo`—keep an eye on the README for updates.

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
* **Incorrect matches** – the CLI will prompt for ambiguous titles; re-run the scraper if you made a wrong selection.

---

Happy scraping!
