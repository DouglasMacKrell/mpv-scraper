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

## Troubleshooting

* **Environment variable errors** – ensure `TVDB_API_KEY` and `TMDB_API_KEY` are exported.
* **Rate limiting** – the scraper respects API limits; if you scrape a large library, the run may pause briefly between requests.
* **Incorrect matches** – the CLI will prompt for ambiguous titles; re-run the scraper if you made a wrong selection.

---

Happy scraping!
