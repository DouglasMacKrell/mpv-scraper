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

    banner = "MPV-Scraper TUI"
    print(banner)

    if non_interactive:
        # Exit immediately; tests will assert the banner text is present
        return 0

    # Placeholder for future interactive loop (Sprint 12.2+)
    try:
        print("Press Ctrl+C to exit…")
        # A minimal blocking loop; in future this will start a proper Textual app
        import time

        time.sleep(0.1)
    except KeyboardInterrupt:
        return 0
    return 0
