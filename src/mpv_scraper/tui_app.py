"""Textual-based TUI application.

Provides a colored, minimal layout for header, jobs list, and log tail.
Falls back gracefully if Textual is not installed.

Quality-of-life behaviours:
- Press ``?`` to toggle help (instead of stacking multiple panels)
- Press ``q`` to quit
- Press ``i`` to init library, ``s`` to scan, ``r`` to run pipeline, ``o`` to optimize, ``u`` to undo
- Press ``l`` to list libraries, ``n`` for new library, ``c`` to change library
- Panels auto-refresh every second to show recent logs/jobs
"""

from __future__ import annotations

import subprocess
import sys
import json
from typing import Optional, List


def run_textual_once(one_shot: bool = False, root_path: str | None = None) -> None:
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import Header, Footer, Static, Button, Input, Select
        from textual.containers import Vertical, Horizontal
        from textual.screen import ModalScreen
        from textual import work
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

    class PathInputModal(ModalScreen):
        """Modal for inputting a library path."""

        def __init__(self, command: str, current_path: Optional[str] = None):
            super().__init__()
            self.command = command
            self.current_path = current_path or str(Path.cwd())

        def compose(self) -> ComposeResult:
            yield Vertical(
                Static(f"Enter path for {self.command} command:"),
                Input(value=self.current_path, id="path_input"),
                Horizontal(
                    Button("Cancel", id="cancel"),
                    Button("Execute", id="execute"),
                ),
                id="modal_content",
            )

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "cancel":
                self.dismiss()
            elif event.button.id == "execute":
                path_input = self.query_one("#path_input", Input)
                path = path_input.value.strip()
                if path:
                    self.dismiss(path)
                else:
                    path_input.styles.border = ("solid", "red")

    class LibrarySelectModal(ModalScreen):
        """Modal for selecting from recent libraries."""

        def __init__(self, libraries: List[str], current_path: str):
            super().__init__()
            self.libraries = libraries
            self.current_path = current_path

        def compose(self) -> ComposeResult:
            # Create options for the select widget
            options = [(f"📁 {lib}", lib) for lib in self.libraries]
            if self.current_path not in self.libraries:
                options.insert(
                    0, (f"📍 {self.current_path} (current)", self.current_path)
                )

            yield Vertical(
                Static("Select a library:"),
                Select(options=options, id="library_select"),
                Horizontal(
                    Button("Cancel", id="cancel"),
                    Button("Select", id="select"),
                ),
                id="modal_content",
            )

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "cancel":
                self.dismiss()
            elif event.button.id == "select":
                select_widget = self.query_one("#library_select", Select)
                if select_widget.value:
                    self.dismiss(select_widget.value)
                else:
                    select_widget.styles.border = ("solid", "red")

    class MpvScraperApp(App):
        CSS = """
        Screen { background: #101216 }
        .panel { border: solid #3a3f4b; padding: 1 1; }
        #header { color: white; background: #2d3440; }
        #jobs { color: #a3be8c; }
        #logs { color: #88c0d0; }
        #commands { color: #b48ead; }
        #libraries { color: #ebcb8b; }
        Button { margin: 1 1; }
        """

        def __init__(self) -> None:
            super().__init__()
            self._help_widget = None
            self.jobs_box = None
            self.logs_box = None
            self.commands_box = None
            self.libraries_box = None
            self._one_shot = one_shot
            self._root_path = root_path
            from pathlib import Path

            self._library_history_file = (
                Path.home() / ".mpv-scraper" / "library_history.json"
            )

        def compose(self) -> ComposeResult:
            yield Header(id="header", show_clock=False)

            # Command buttons
            command_buttons = Horizontal(
                Button("i: Init", id="init_btn"),
                Button("s: Scan", id="scan_btn"),
                Button("r: Run", id="run_btn"),
                Button("o: Optimize", id="optimize_btn"),
                Button("u: Undo", id="undo_btn"),
                id="commands",
            )

            # Library management buttons
            library_buttons = Horizontal(
                Button("l: List", id="list_btn"),
                Button("n: New", id="new_btn"),
                Button("c: Change", id="change_btn"),
                id="libraries",
            )

            # Create boxes so we can update their contents on a timer
            self.jobs_box = Static(self._jobs_snapshot(), classes="panel", id="jobs")
            self.logs_box = Static(self._read_log_tail(), classes="panel", id="logs")
            self.commands_box = Static(
                "Commands: Press buttons above or use keyboard shortcuts",
                classes="panel",
                id="commands_panel",
            )
            self.libraries_box = Static(
                f"Current: {self._get_current_path()}",
                classes="panel",
                id="libraries_panel",
            )

            left = Vertical(command_buttons, library_buttons, self.jobs_box, id="left")
            right = Vertical(
                self.logs_box, self.commands_box, self.libraries_box, id="right"
            )
            yield Horizontal(left, right)
            yield Footer()

        BINDINGS = [
            ("?", "show_help", "Help"),
            ("q", "quit", "Quit"),
            ("i", "init_library", "Init"),
            ("s", "scan_library", "Scan"),
            ("r", "run_pipeline", "Run"),
            ("o", "optimize_videos", "Optimize"),
            ("u", "undo_last", "Undo"),
            ("l", "list_libraries", "List"),
            ("n", "new_library", "New"),
            ("c", "change_library", "Change"),
        ]

        def on_mount(self) -> None:  # type: ignore[override]
            # Refresh panels periodically to reflect recent activity
            self.set_interval(1.0, self._refresh_panels)
            if self._one_shot:
                # Exit shortly after first render to support non-interactive/CI
                self.set_timer(0.05, self.exit)

        def action_show_help(self) -> None:
            # Toggle help (don't stack multiple panels)
            from textual.widgets import Static
            from textual.containers import Vertical

            if self._help_widget is not None:
                try:
                    self._help_widget.remove()
                finally:
                    self._help_widget = None
                return

            help_text = (
                "Welcome to mpv-scraper TUI!\n\n"
                "Keys:\n"
                "  ?  Toggle this help\n"
                "  q  Quit\n"
                "  i  Init library (prompt for path)\n"
                "  s  Scan library (uses current path)\n"
                "  r  Run full pipeline (scan→scrape→generate)\n"
                "  o  Optimize videos (prompt for options)\n"
                "  u  Undo last operation\n"
                "  l  List recent libraries\n"
                "  n  New library (prompt for path, run init)\n"
                "  c  Change library (browse/prompt for path)\n\n"
                "Provider Mode (left panel):\n"
                "  Primary          Use TVDB/TMDB when keys are set\n"
                "  Prefer Fallback  Try TVmaze/OMDb first\n"
                "  Fallback Only    Only use TVmaze/OMDb\n"
                "  Offline          No network calls; use cache only\n"
            )

            self._help_widget = Vertical(Static(help_text, classes="panel"))
            self.mount(self._help_widget)

        def action_quit(self) -> None:
            self.exit()

        def action_init_library(self) -> None:
            self._show_path_modal("init")

        def action_scan_library(self) -> None:
            self._execute_command("scan", self._get_current_path())

        def action_run_pipeline(self) -> None:
            self._execute_command("run", self._get_current_path())

        def action_optimize_videos(self) -> None:
            # For now, just run crop with default settings
            self._execute_command("crop", self._get_current_path())

        def action_undo_last(self) -> None:
            self._execute_command("undo", self._get_current_path())

        def action_list_libraries(self) -> None:
            """List recent libraries."""
            libraries = self._get_library_history()
            if not libraries:
                self.libraries_box.update("No recent libraries found.")
                return

            lib_list = "\n".join([f"📁 {lib}" for lib in libraries[:5]])
            self.libraries_box.update(f"Recent libraries:\n{lib_list}")

        def action_new_library(self) -> None:
            """Create a new library."""
            self._show_path_modal("new_library")

        def action_change_library(self) -> None:
            """Change to a different library."""
            libraries = self._get_library_history()
            if not libraries:
                # If no history, just show path input modal
                self._show_path_modal("change_library")
                return

            # Show library selection modal
            self.push_screen(
                LibrarySelectModal(libraries, self._get_current_path()),
                self._on_library_select_result,
            )

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "init_btn":
                self.action_init_library()
            elif event.button.id == "scan_btn":
                self.action_scan_library()
            elif event.button.id == "run_btn":
                self.action_run_pipeline()
            elif event.button.id == "optimize_btn":
                self.action_optimize_videos()
            elif event.button.id == "undo_btn":
                self.action_undo_last()
            elif event.button.id == "list_btn":
                self.action_list_libraries()
            elif event.button.id == "new_btn":
                self.action_new_library()
            elif event.button.id == "change_btn":
                self.action_change_library()

        def _get_current_path(self) -> str:
            """Get the current library path."""
            if self._root_path:
                return self._root_path
            return str(Path.cwd())

        def _get_library_history(self) -> List[str]:
            """Get list of recent libraries."""
            try:
                if self._library_history_file.exists():
                    data = json.loads(self._library_history_file.read_text())
                    return data.get("libraries", [])
            except Exception:
                pass
            return []

        def _save_library_history(self, path: str) -> None:
            """Save a library path to history."""
            try:
                self._library_history_file.parent.mkdir(parents=True, exist_ok=True)

                libraries = self._get_library_history()
                if path not in libraries:
                    libraries.insert(0, path)
                    # Keep only last 10 libraries
                    libraries = libraries[:10]

                data = {"libraries": libraries}
                self._library_history_file.write_text(json.dumps(data, indent=2))
            except Exception:
                pass

        def _validate_library_structure(self, path: str) -> bool:
            """Validate that a path has proper library structure."""
            try:
                lib_path = Path(path)
                if not lib_path.exists() or not lib_path.is_dir():
                    return False

                # Check for basic structure (Movies directory or show subdirectories)
                movies_dir = lib_path / "Movies"
                if movies_dir.exists():
                    return True

                # Check for show subdirectories
                show_dirs = [
                    d for d in lib_path.iterdir() if d.is_dir() and d.name != "images"
                ]
                return len(show_dirs) > 0

            except Exception:
                return False

        def _show_path_modal(self, command: str) -> None:
            """Show a modal for path input."""
            current_path = self._get_current_path()
            self.push_screen(
                PathInputModal(command, current_path), self._on_path_modal_result
            )

        def _on_path_modal_result(self, result: Optional[str]) -> None:
            """Handle result from path input modal."""
            if result:
                if result == "new_library":
                    # For new library, run init command
                    self._execute_command("init", result)
                    self._save_library_history(result)
                    self._switch_library(result)
                elif result == "change_library":
                    # For change library, just switch
                    if self._validate_library_structure(result):
                        self._save_library_history(result)
                        self._switch_library(result)
                    else:
                        self.libraries_box.update(
                            f"Invalid library structure: {result}"
                        )
                else:
                    # For init command
                    self._execute_command("init", result)
                    self._save_library_history(result)

        def _on_library_select_result(self, result: Optional[str]) -> None:
            """Handle result from library selection modal."""
            if result:
                if self._validate_library_structure(result):
                    self._save_library_history(result)
                    self._switch_library(result)
                else:
                    self.libraries_box.update(f"Invalid library structure: {result}")

        def _switch_library(self, new_path: str) -> None:
            """Switch to a new library."""
            self._root_path = new_path
            self.libraries_box.update(f"Current: {new_path}")
            # Refresh panels to show new library's logs/jobs
            self._refresh_panels()

        @work(thread=True)
        def _execute_command(self, command: str, path: str) -> None:
            """Execute a CLI command in a background thread."""
            try:
                # Update command status
                self.commands_box.update(f"Executing: {command} {path}")

                # Run the command
                result = subprocess.run(
                    [sys.executable, "-m", "mpv_scraper.cli", command, path],
                    capture_output=True,
                    text=True,
                    cwd=Path.cwd(),
                )

                # Update command status with result
                if result.returncode == 0:
                    self.commands_box.update(f"✓ {command} completed successfully")
                else:
                    self.commands_box.update(f"✗ {command} failed: {result.stderr}")

            except Exception as e:
                self.commands_box.update(f"✗ {command} error: {str(e)}")

        def _refresh_panels(self) -> None:
            # Lightweight periodic updates
            try:
                if self.logs_box is not None:
                    self.logs_box.update(self._read_log_tail())
                if self.jobs_box is not None:
                    self.jobs_box.update(self._jobs_snapshot())
                if self.libraries_box is not None:
                    self.libraries_box.update(f"Current: {self._get_current_path()}")
            except Exception:
                pass

        def _read_log_tail(self) -> str:
            from pathlib import Path

            base = Path(self._root_path) if self._root_path else Path.cwd()
            log_path = base / "mpv-scraper.log"
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

            base = Path(self._root_path) if self._root_path else Path.cwd()
            history = base / ".mpv-scraper" / "jobs.json"
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
        # Run the app; in one-shot mode it will exit quickly. After run, print
        # a short tail of the log to stdout so non-interactive tests can assert
        # on WARNING/ERROR content even without a terminal UI.
        app.run()
        try:
            from pathlib import Path

            base = Path(root_path) if root_path else Path.cwd()
            log_path = base / "mpv-scraper.log"
            if log_path.exists():
                tail_lines = log_path.read_text(encoding="utf-8").splitlines()[-5:]
                for line in tail_lines:
                    print(line)
        except Exception:
            pass
    except Exception:
        # Ensure fallback prints something
        print("MPV-Scraper TUI")
