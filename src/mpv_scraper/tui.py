"""Minimal TUI scaffolding for mpv-scraper.

Provides a very lightweight non-interactive render suitable for tests,
and a placeholder interactive loop for future sprints.
"""

from __future__ import annotations


def run_tui(non_interactive: bool = False) -> int:
    """Run the TUI.

    Parameters
    ----------
    non_interactive
        If True, render a minimal banner and exit immediately (used for tests/CI).

    Returns
    -------
    int
        Exit code (0 = success)
    """

    if non_interactive:
        # One-shot render via textual app scaffold (will fallback to simple print if missing)
        try:
            from mpv_scraper.tui_app import run_textual_once

            run_textual_once()
        except Exception:
            print("MPV-Scraper TUI")
            # Fallback: also print recent log tail
            try:
                from pathlib import Path

                log_path = Path.cwd() / "mpv-scraper.log"
                if log_path.exists():
                    tail_lines = log_path.read_text(encoding="utf-8").splitlines()[-5:]
                    if tail_lines:
                        print("Recent log:")
                        for line in tail_lines:
                            print(line)
            except Exception:
                pass
        return 0

    # Interactive: start textual app if available
    try:
        from mpv_scraper.tui_app import run_textual_once

        run_textual_once()
        return 0
    except Exception:
        print("MPV-Scraper TUI")
        return 0

    # Placeholder for future interactive loop (Sprint 12.2+)
    return 0
