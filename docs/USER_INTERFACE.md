# User Interface (TUI)

Welcome! The TUI lets you keep an eye on scraping/optimization jobs and recent logs – right in your terminal.

## Launch

```bash
python -m mpv_scraper.cli tui
```

- `--non-interactive`: render a single frame and exit (useful for tests/CI)

## What you see now
- Colored header
- Left panel: Jobs snapshot and a “Provider Mode” selector
- Right panel: Recent log tail (last 5 lines), with warnings and errors highlighted

## Logs
- Logs are written to `mpv-scraper.log` in the current working directory.
- The TUI shows the last 5 lines on startup for quick diagnostics.

## Keyboard shortcuts
- `?` – Show in-app help
- `q` – Quit (planned)
- `o` – Start optimize job (planned)
- `s` – Start scrape job (planned)

## Troubleshooting
- If no log file is shown, ensure commands were run from the library root and that operations have generated logs.
- On macOS/Linux, ensure your terminal supports UTF‑8 to display icons/characters.

## Quick How-To
- Pick a library folder in your terminal, then run:
  ```bash
  python -m mpv_scraper.cli tui
  ```
- Choose a provider mode in the left panel depending on your setup:
  - Primary: Use TVDB/TMDB if keys are set
  - Prefer Fallback: Try TVmaze/OMDb first
  - Fallback Only: Only TVmaze/OMDb (no paid keys)
  - Offline: No network; use cache/placeholders
- Press `?` anytime to see the key map.

## Tips
- If the log panel is empty, run a command (e.g., `scrape`) to generate activity.
- For a quick, one-shot render (CI or script usage):
  ```bash
  python -m mpv_scraper.cli tui --non-interactive
  ```
