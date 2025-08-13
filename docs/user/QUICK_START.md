# Quick Start Guide

Welcome! This guide gets you scraping in minutes — no developer skills required.

What this tool does for you:
- Finds your TV shows and movies in a simple `/mpv` folder
- Grabs titles, descriptions, ratings, and images
- Generates EmulationStation-ready `gamelist.xml` files
- Can optimize videos for handhelds (optional)

If you don’t have paid API keys, don’t worry — you can use our free fallbacks.

## 🚀 Quick Start Flow

```mermaid
flowchart TD
    A[Clone Repository] --> B[Create Virtual Environment]
    B --> C[Install Dependencies]
    C --> D[Set API Keys]
    D --> E[Test Installation]
    E --> F[Run First Scrape]
    F --> G[Success!]

    E --> H{Installation OK?}
    H -->|No| I[Check Dependencies]
    I --> E

    F --> J{API Keys Valid?}
    J -->|No| K[Check API Keys]
    K --> F

    style G fill:#c8e6c9
    style H fill:#ffcdd2
    style J fill:#ffcdd2
```

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

## First‑run wizard (init)

Let the tool scaffold config and verify prerequisites for you:

```bash
python -m mpv_scraper.cli init /mpv
```

This will:
- Check `ffmpeg` and `ffprobe` availability and print versions
- Create `/mpv/images/` and `/mpv/Movies/` if missing
- Write `/mpv/mpv-scraper.toml` with sensible defaults
- Create `/mpv/.env.example` and `/mpv/.env` with empty API key placeholders

You can re-run safely; use `--force` to overwrite existing config.

Tip: After `init`, you’re ready to try scraping right away — even without keys — using fallbacks below.

### Config defaults
`mpv-scraper.toml` supports:
```toml
library_root = "/mpv"
workers = 0                 # 0 = auto-detect
preset = "handheld"        # or "compatibility"
replace_originals_default = false
regen_gamelist_default = false
```

When you omit CLI flags on `optimize-parallel`, these defaults are applied.

---

## Configure API Keys

Export your keys as environment variables **in the same shell session** where you will run the scraper:

```bash
export TVDB_API_KEY="YOUR_TVDB_API_KEY"
export TMDB_API_KEY="YOUR_TMDB_API_KEY"
```

You can add these lines to your shell profile (e.g., `~/.zshrc`) for persistence.

Notes:
- You can run without keys using fallbacks; see `docs/FALLBACKS.md`.

### No keys? Use fallbacks
If you don’t want to set up keys now:

```bash
# Use only free fallbacks (TVmaze/OMDb)
python -m mpv_scraper.cli scrape /mpv --fallback-only

# Prefer fallbacks, but allow primary providers too
python -m mpv_scraper.cli scrape /mpv --prefer-fallback

# Do an offline pass (no network): writes placeholders from cache
python -m mpv_scraper.cli scrape /mpv --no-remote
```

More details in `docs/FALLBACKS.md`.

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
- **`sync-logos`** - Sync manually downloaded logos to gamelist.xml entries

All commands support the `--help` flag for detailed usage information.

### Manual Logo Management

The `sync-logos` command allows you to manually manage logo files and sync them to your gamelist.xml entries:

```bash
# Sync all logos in a directory
python -m mpv_scraper.cli sync-logos /mpv

# Sync logos for a specific show
python -m mpv_scraper.cli sync-logos /mpv --show "Darkwing Duck"

# Force update even if logo files don't exist
python -m mpv_scraper.cli sync-logos /mpv --force
```

**Naming Convention**: Place logo files in the `images/` directory with these names:
- `{show}-logo.png` - Main logo file
- `{show}-box.png` - Box art (alternative)
- `{show}-marquee.png` - Marquee display (alternative)

**Use Cases**:
- Manual logo downloads when automatic scraping fails
- Custom logo replacements
- Batch logo management for multiple shows

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

### API Issues

For detailed help with TVDB and TMDB API authentication issues, see the [API Troubleshooting Guide](../technical/API_TROUBLESHOOTING.md).

Common API problems and quick fixes:
- **401 Unauthorized**: Check API key format and environment variables
- **Rate limiting**: Wait between large scraping operations
- **Network issues**: Verify internet connectivity and firewall settings

---

Happy scraping!
