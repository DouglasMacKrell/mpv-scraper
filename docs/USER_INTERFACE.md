# User Interface (TUI)

Welcome! The TUI lets you keep an eye on scraping/optimization jobs and recent logs – right in your terminal.

## Launch

```bash
python -m mpv_scraper.cli tui
```

- `--non-interactive`: render a single frame and exit (useful for tests/CI)
- `--path <library>`: monitor a specific library root (reads `<library>/mpv-scraper.log` and `<library>/.mpv-scraper/jobs.json`)

## What you see now
- Colored header
- Left panel: Jobs snapshot and a “Provider Mode” selector
- Right panel: Recent log tail (last 5 lines), with warnings and errors highlighted

## Logs
- By default, logs are read from `mpv-scraper.log` in the current working directory.
- Use `--path <library>` to monitor a different library root.
- The TUI shows the last 5 lines on startup for quick diagnostics.

## Keyboard shortcuts
- `?` – Toggle in‑app help
- `q` – Quit
- `o` – Start optimize job (planned)
- `s` – Start scrape job (planned)

## Troubleshooting
- If no log lines appear, ensure you are pointing at the right library:
  - Example: `python -m mpv_scraper.cli tui --path /Volumes/Untitled/roms/mpv`
- On macOS/Linux, ensure your terminal supports UTF‑8 to display icons/characters.

## Quick How-To
- Monitor a library while you run jobs in another terminal:
  ```bash
  # Terminal A (monitor)
  python -m mpv_scraper.cli tui --path /path/to/mpv

  # Terminal B (jobs)
  python -m mpv_scraper.cli run /path/to/mpv
  ```
- Choose a provider mode in the left panel depending on your setup:
  - Primary: Use TVDB/TMDB if keys are set
  - Prefer Fallback: Try TVmaze/OMDb first
  - Fallback Only: Only TVmaze/OMDb (no paid keys)
  - Offline: No network; use cache only
- Press `?` anytime to see the key map.

## Tips
- If the log panel is empty, run a command (e.g., `scrape`) to generate activity.
- For a quick, one-shot render (CI or script usage):
  ```bash
  python -m mpv_scraper.cli tui --non-interactive
  ```
