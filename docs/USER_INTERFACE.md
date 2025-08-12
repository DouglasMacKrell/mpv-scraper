# User Interface (TUI)

The mpv-scraper includes a lightweight text UI to monitor jobs and view logs.

## Launch

```bash
python -m mpv_scraper.cli tui
```

- `--non-interactive`: render a single frame and exit (useful for tests/CI)

## What you see now
- Banner text and a tail of the last 5 log lines from `mpv-scraper.log` if present.
- Future sprints will add a job queue, per-job progress bars, and cancel/retry actions.

## Logs
- Logs are written to `mpv-scraper.log` in the current working directory.
- The TUI shows the last 5 lines on startup for quick diagnostics.

## Keyboard shortcuts (planned)
- `q` – quit
- `c` – cancel selected job
- `r` – retry failed job

## Troubleshooting
- If no log file is shown, ensure commands were run from the library root and that operations have generated logs.
- On macOS/Linux, ensure your terminal supports UTF‑8 to display icons/characters.

## Screenshots (placeholder)
Add screenshots or GIFs here to demonstrate TUI usage once the interactive views are implemented.
