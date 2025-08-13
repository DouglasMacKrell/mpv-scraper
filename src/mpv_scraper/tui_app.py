"""Textual-based TUI application scaffold.

Provides a colored, minimal layout for header, jobs list placeholder, and log tail.
Falls back gracefully if Textual is not installed.
"""

from __future__ import annotations


def run_textual_once() -> None:
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import Header, Footer, Static
        from textual.containers import Vertical, Horizontal
    except Exception:
        # Fallback: simple print when Textual not available
        print("MPV-Scraper TUI")
        return

    class MpvScraperApp(App):
        CSS = """
        Screen { background: #101216 }
        .panel { border: solid #3a3f4b; padding: 1 1; }
        #header { color: white; background: #2d3440; }
        #jobs { color: #a3be8c; }
        #logs { color: #88c0d0; }
        """

        def compose(self) -> ComposeResult:
            yield Header(id="header", show_clock=False)
            yield Horizontal(
                Vertical(
                    Static("Jobs (placeholder)", classes="panel", id="jobs"), id="left"
                ),
                Vertical(
                    Static(self._read_log_tail(), classes="panel", id="logs"),
                    id="right",
                ),
            )
            yield Footer()

        def _read_log_tail(self) -> str:
            from pathlib import Path

            log_path = Path.cwd() / "mpv-scraper.log"
            if not log_path.exists():
                return "No recent logs."
            lines = log_path.read_text(encoding="utf-8").splitlines()
            tail = "\n".join(lines[-5:]) if lines else "(empty)"
            return f"Recent log:\n{tail}"

    # Mount once and immediately exit
    app = MpvScraperApp()
    # textual's run blocks; for non-interactive, we will mount and immediately exit
    # Using `run` here is acceptable for smoke; it will render one frame
    try:
        app.run()  # User can Ctrl+C out in interactive mode; tests use non-interactive print
    except Exception:
        # Ensure fallback prints something
        print("MPV-Scraper TUI")
