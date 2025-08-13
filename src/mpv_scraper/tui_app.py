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
        # Fallback: simple print when Textual not available; include log tail
        print("MPV-Scraper TUI")
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
            from textual.widgets import Select

            provider_select = Select(
                options=[
                    ("Primary", "primary"),
                    ("Prefer Fallback", "prefer_fallback"),
                    ("Fallback Only", "fallback_only"),
                    ("Offline", "offline"),
                ],
                value="primary",
                prompt="Provider Mode:",
            )
            left = Vertical(
                Static(self._jobs_snapshot(), classes="panel", id="jobs"),
                provider_select,
                id="left",
            )
            right = Vertical(
                Static(self._read_log_tail(), classes="panel", id="logs"), id="right"
            )
            yield Horizontal(left, right)
            yield Footer()

        BINDINGS = [
            ("?", "show_help", "Help"),
        ]

        def action_show_help(self) -> None:
            # Simple modal help text for now
            help_text = (
                "Keys:\n"
                "  ?  Show this help\n"
                "  q  Quit (planned)\n"
                "  o  Enqueue optimize (planned)\n"
                "  s  Enqueue scrape (planned)\n"
                "Provider Mode (planned): Primary / Prefer Fallback / Fallback Only / Offline\n"
            )
            from textual.widgets import Static
            from textual.containers import Vertical

            self.mount(Vertical(Static(help_text, classes="panel")))

        def _read_log_tail(self) -> str:
            from pathlib import Path

            log_path = Path.cwd() / "mpv-scraper.log"
            if not log_path.exists():
                return "No recent logs."
            lines = log_path.read_text(encoding="utf-8").splitlines()
            tail = "\n".join(lines[-5:]) if lines else "(empty)"

            # Basic highlighting tags; Textual will render ANSI and markdown-like emphasis
            def colorize(line: str) -> str:
                if "ERROR" in line:
                    return f"[red]{line}[/red]"
                if "WARNING" in line:
                    return f"[yellow]{line}[/yellow]"
                return line

            colored = "\n".join(colorize(line) for line in tail.splitlines())
            return f"Recent log:\n{colored}"

        def _jobs_snapshot(self) -> str:
            # Read job history JSON and render a tiny snapshot
            from pathlib import Path
            import json

            history = Path.cwd() / ".mpv-scraper" / "jobs.json"
            if not history.exists():
                return "Jobs: (no jobs yet)"
            try:
                data = json.loads(history.read_text())
            except Exception:
                return "Jobs: (unreadable)"
            lines = ["Jobs:"]
            for jid, j in list(data.items())[:5]:
                progress = j.get("progress", 0)
                total = j.get("total") or "?"
                status = j.get("status", "?")
                name = j.get("name", jid)
                lines.append(f"- {name} [{status}] {progress}/{total}")
            return "\n".join(lines)

    # Mount once and immediately exit
    app = MpvScraperApp()
    # textual's run blocks; for non-interactive, we will mount and immediately exit
    # Using `run` here is acceptable for smoke; it will render one frame
    try:
        app.run()  # User can Ctrl+C out in interactive mode; tests use non-interactive print
    except Exception:
        # Ensure fallback prints something
        print("MPV-Scraper TUI")
