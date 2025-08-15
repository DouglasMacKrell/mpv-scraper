"""Textual-based TUI application.

Provides a colored, minimal layout for header, jobs list, and log tail.
Falls back gracefully if Textual is not installed.

Quality-of-life behaviours:
- Press ``?`` to toggle help (instead of stacking multiple panels)
- Press ``q`` to quit
- Press ``i`` to init library, ``s`` to scan, ``r`` to run pipeline, ``o`` to optimize, ``u`` to undo
- Press ``l`` to list libraries, ``n`` for new library, ``c`` to change library
- Press ``p`` for provider settings, ``v`` for system info, ``t`` for connectivity test
- Panels auto-refresh every second to show recent logs/jobs
"""

from __future__ import annotations

import subprocess
import sys
import json
import shutil
import platform
from typing import Optional, List, Dict, Any
import time


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

    class SettingsModal(ModalScreen):
        """Modal for advanced settings and configuration."""

        def __init__(self, current_settings: Dict[str, Any]):
            super().__init__()
            self.current_settings = current_settings

        def compose(self) -> ComposeResult:
            yield Vertical(
                Static("Advanced Settings & Configuration"),
                Static("Provider Mode:"),
                Select(
                    options=[
                        ("Primary", "primary"),
                        ("Prefer Fallback", "prefer_fallback"),
                        ("Fallback Only", "fallback_only"),
                        ("Offline", "offline"),
                    ],
                    value=self.current_settings.get("provider_mode", "primary"),
                    id="provider_mode",
                ),
                Static("TUI Preferences:"),
                Select(
                    options=[
                        ("Dark Theme", "dark"),
                        ("Light Theme", "light"),
                        ("Auto Theme", "auto"),
                    ],
                    value=self.current_settings.get("theme", "dark"),
                    id="theme",
                ),
                Select(
                    options=[
                        ("0.5s Refresh", "0.5"),
                        ("1.0s Refresh", "1.0"),
                        ("2.0s Refresh", "2.0"),
                    ],
                    value=str(self.current_settings.get("refresh_rate", "1.0")),
                    id="refresh_rate",
                ),
                Horizontal(
                    Button("Cancel", id="cancel"),
                    Button("Save", id="save"),
                ),
                id="modal_content",
            )

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "cancel":
                self.dismiss()
            elif event.button.id == "save":
                provider_mode = self.query_one("#provider_mode", Select).value
                theme = self.query_one("#theme", Select).value
                refresh_rate = float(self.query_one("#refresh_rate", Select).value)

                settings = {
                    "provider_mode": provider_mode,
                    "theme": theme,
                    "refresh_rate": refresh_rate,
                }
                self.dismiss(settings)

    class MpvScraperApp(App):
        CSS = """
        Screen { background: #101216 }
        .panel { border: solid #3a3f4b; padding: 1 1; }
        #header { color: white; background: #2d3440; }
        #jobs { color: #a3be8c; }
        #logs { color: #88c0d0; }
        #commands { color: #b48ead; }
        #libraries { color: #ebcb8b; }
        #settings { color: #d08770; }
        #progress_panel {
            color: #ffffff;
            border: solid #4fc3f7;
            background: #1976d2;
            padding: 1 2;
            text-align: center;
        }
        Button { margin: 1 1; }
        """

        def __init__(self) -> None:
            super().__init__()
            self._help_widget = None
            self.jobs_box = None
            self.logs_box = None
            self.commands_box = None
            self.libraries_box = None
            self.settings_box = None
            self.progress_box = None
            self._one_shot = one_shot
            self._root_path = root_path
            from pathlib import Path

            self._library_history_file = (
                Path.home() / ".mpv-scraper" / "library_history.json"
            )
            self._tui_preferences_file = (
                Path.home() / ".mpv-scraper" / "tui_preferences.json"
            )
            self._refresh_rate = 1.0
            self._load_tui_preferences()

            # Progress tracking
            self._current_operation = None
            self._operation_start_time = None
            self._spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            self._spinner_index = 0
            self._clear_progress_after_delay = False
            self._clear_progress_time = None

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

            # Settings buttons
            settings_buttons = Horizontal(
                Button("p: Provider", id="provider_btn"),
                Button("v: System", id="system_btn"),
                Button("t: Test", id="test_btn"),
                id="settings",
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
            self.settings_box = Static(
                self._get_system_status(),
                classes="panel",
                id="settings_panel",
            )
            self.progress_box = Static(
                "",
                classes="panel",
                id="progress_panel",
            )

            left = Vertical(
                command_buttons,
                library_buttons,
                settings_buttons,
                self.jobs_box,
                self.progress_box,
                id="left",
            )
            right = Vertical(
                self.logs_box,
                self.commands_box,
                self.libraries_box,
                self.settings_box,
                id="right",
            )
            yield Horizontal(left, right)
            yield Footer()

        BINDINGS = [
            ("?", "show_help", "Help"),
            ("F1", "show_context_help", "Context Help"),
            ("q", "quit", "Quit"),
            ("i", "init_library", "Init"),
            ("s", "scan_library", "Scan"),
            ("r", "run_pipeline", "Run"),
            ("o", "optimize_videos", "Optimize"),
            ("u", "undo_last", "Undo"),
            ("l", "list_libraries", "List"),
            ("n", "new_library", "New"),
            ("c", "change_library", "Change"),
            ("p", "provider_settings", "Provider"),
            ("v", "view_system_info", "System"),
            ("t", "test_connectivity", "Test"),
        ]

        def on_mount(self) -> None:  # type: ignore[override]
            # Refresh panels periodically to reflect recent activity
            self.set_interval(self._refresh_rate, self._refresh_panels)
            # Update progress spinner more frequently
            self.set_interval(0.1, self._update_progress_spinner)
            if self._one_shot:
                # Exit shortly after first render to support non-interactive/CI
                self.set_timer(0.05, self.exit)

        def _start_operation(self, operation: str) -> None:
            """Start tracking an operation with progress indicators."""
            self._current_operation = operation
            self._operation_start_time = time.time()
            self._spinner_index = 0
            self._update_progress_display()

        def _end_operation(self, success: bool = True) -> None:
            """End operation tracking and show final status."""
            if self._current_operation:
                duration = time.time() - self._operation_start_time
                status = "✓" if success else "✗"
                duration_str = f"{duration:.1f}s"

                if success:
                    self.progress_box.update(
                        f"{status} {self._current_operation} completed in {duration_str}"
                    )
                else:
                    self.progress_box.update(
                        f"{status} {self._current_operation} failed after {duration_str}"
                    )

                # Clear operation after a delay - use a flag instead of timer
                self._clear_progress_after_delay = True
                self._clear_progress_time = time.time() + 3.0

                self._current_operation = None
                self._operation_start_time = None

        def _update_progress_spinner(self) -> None:
            """Update the progress spinner animation."""
            # Check if we need to clear progress after delay
            if self._clear_progress_after_delay and self._clear_progress_time:
                if time.time() >= self._clear_progress_time:
                    self._clear_progress()
                    self._clear_progress_after_delay = False
                    self._clear_progress_time = None
                    return

            if self._current_operation and self._operation_start_time:
                self._spinner_index = (self._spinner_index + 1) % len(
                    self._spinner_chars
                )
                self._update_progress_display()

        def _update_progress_display(self) -> None:
            """Update the progress display with current operation and spinner."""
            if self._current_operation and self._operation_start_time:
                duration = time.time() - self._operation_start_time
                spinner = self._spinner_chars[self._spinner_index]

                # Get operation-specific progress info
                progress_info = self._get_operation_progress()

                # Try to get actual progress data for progress bar
                progress_bar = ""
                try:
                    from pathlib import Path
                    import json

                    base = Path(self._root_path) if self._root_path else Path.cwd()
                    jobs_file = base / ".mpv-scraper" / "jobs.json"

                    if jobs_file.exists():
                        data = json.loads(jobs_file.read_text())

                        # For composite operations like "run", show the most recent job
                        if self._current_operation.lower() == "run":
                            # Find the most recent job (scan, scrape, or generate)
                            recent_jobs = [
                                "generate",
                                "scrape",
                                "scan",
                            ]  # Most recent first
                            for job_type in recent_jobs:
                                if job_type in data:
                                    job = data[job_type]
                                    progress = job.get("progress", 0)
                                    total = job.get("total", 0)
                                    if total > 0:
                                        progress_bar = f"\n{self._get_progress_bar(progress, total, 30)}"
                                        break
                        else:
                            # For individual operations, find matching job
                            for jid, job in data.items():
                                if (
                                    job.get("name", "")
                                    .lower()
                                    .startswith(self._current_operation.lower())
                                ):
                                    progress = job.get("progress", 0)
                                    total = job.get("total", 0)
                                    if total > 0:
                                        progress_bar = f"\n{self._get_progress_bar(progress, total, 30)}"
                                        break
                except Exception:
                    pass

                progress_text = f"{spinner} {self._current_operation} running... ({duration:.1f}s){progress_bar}\n{progress_info}"
                self.progress_box.update(progress_text)
            else:
                # Show most recent completed job when no active operation
                try:
                    from pathlib import Path
                    import json

                    base = Path(self._root_path) if self._root_path else Path.cwd()
                    jobs_file = base / ".mpv-scraper" / "jobs.json"

                    if jobs_file.exists():
                        data = json.loads(jobs_file.read_text())
                        # Find the most recent completed job
                        recent_jobs = ["generate", "scrape", "scan"]
                        for job_type in recent_jobs:
                            if job_type in data:
                                job = data[job_type]
                                if job.get("status") == "completed":
                                    progress = job.get("progress", 0)
                                    total = job.get("total", 0)
                                    if total > 0:
                                        progress_bar = self._get_progress_bar(
                                            progress, total, 30
                                        )
                                        progress_text = f"✓ {job_type.title()} completed\n{progress_bar}"
                                        self.progress_box.update(progress_text)
                                        return
                except Exception:
                    pass

        def _clear_progress(self) -> None:
            """Clear the progress display."""
            self.progress_box.update("")

        def _get_operation_progress(self) -> str:
            """Get operation-specific progress information."""
            if not self._current_operation:
                return ""

            try:
                from pathlib import Path
                import json

                base = Path(self._root_path) if self._root_path else Path.cwd()
                jobs_file = base / ".mpv-scraper" / "jobs.json"

                if jobs_file.exists():
                    data = json.loads(jobs_file.read_text())
                    # Find the most recent job for this operation
                    for jid, job in data.items():
                        if (
                            job.get("name", "")
                            .lower()
                            .startswith(self._current_operation.lower())
                        ):
                            progress = job.get("progress", 0)
                            total = job.get("total", 0)
                            status = job.get("status", "running")

                            if total > 0:
                                percentage = (progress / total) * 100
                                return (
                                    f"Progress: {progress}/{total} ({percentage:.1f}%)"
                                )
                            else:
                                return f"Status: {status}"

                # Fallback progress indicators based on operation type
                operation_progress = {
                    "scan": "Scanning library structure...",
                    "scrape": "Fetching metadata from APIs...",
                    "generate": "Generating gamelist.xml files...",
                    "optimize": "Processing video files...",
                    "crop": "Cropping videos to 4:3...",
                    "init": "Initializing library structure...",
                    "undo": "Reverting changes...",
                }

                return operation_progress.get(
                    self._current_operation.lower(), "Processing..."
                )

            except Exception:
                return "Processing..."

        def _get_progress_bar(self, current: int, total: int, width: int = 20) -> str:
            """Generate a text-based progress bar."""
            if total <= 0:
                return "[" + " " * width + "]"

            filled = int((current / total) * width)
            # Use more visible characters for better accessibility
            bar = "█" * filled + "░" * (width - filled)
            percentage = (current / total) * 100
            return f"[{bar}] {percentage:.1f}%"

        def _estimate_operation_duration(self, operation: str) -> str:
            """Estimate duration for different operations."""
            estimates = {
                "scan": "10-30 seconds",
                "scrape": "2-10 minutes",
                "generate": "30 seconds - 2 minutes",
                "optimize": "5-30 minutes",
                "crop": "5-30 minutes",
                "init": "5-10 seconds",
                "undo": "10-30 seconds",
            }
            return estimates.get(operation.lower(), "variable")

        def _get_operation_description(self, operation: str) -> str:
            """Get a user-friendly description of the operation."""
            descriptions = {
                "scan": "Scanning library for shows and movies",
                "scrape": "Fetching metadata from TVDB/TMDB APIs",
                "generate": "Creating gamelist.xml files for EmulationStation",
                "optimize": "Optimizing video files for 4:3 displays",
                "crop": "Cropping videos to remove letterboxing",
                "init": "Setting up new library structure",
                "undo": "Reverting last operation",
            }
            return descriptions.get(operation.lower(), "Processing")

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

            help_text = self._get_comprehensive_help()
            self._help_widget = Vertical(Static(help_text, classes="panel"))
            self.mount(self._help_widget)

        def action_show_context_help(self) -> None:
            """Show context-sensitive help for the currently focused element."""
            from textual.widgets import Static
            from textual.containers import Vertical

            if self._help_widget is not None:
                try:
                    self._help_widget.remove()
                finally:
                    self._help_widget = None
                return

            # Get the currently focused widget and show relevant help
            focused = self.focused
            if focused:
                context_help = self._get_context_help(
                    focused.id if hasattr(focused, "id") else str(focused)
                )
            else:
                context_help = self._get_general_help()

            self._help_widget = Vertical(Static(context_help, classes="panel"))
            self.mount(self._help_widget)

        def _get_comprehensive_help(self) -> str:
            """Get comprehensive help text with all features."""
            return (
                "🎯 MPV-Scraper TUI - Complete Help Guide\n"
                "=====================================\n\n"
                "📋 QUICK START\n"
                "1. Press 'i' to initialize a new library\n"
                "2. Press 's' to scan for shows/movies\n"
                "3. Press 'r' to run the full pipeline\n"
                "4. Use 'l', 'n', 'c' to manage libraries\n\n"
                "⌨️  KEYBOARD SHORTCUTS\n"
                "  ?  Toggle this comprehensive help\n"
                "  F1 Show context-sensitive help\n"
                "  q  Quit the application\n\n"
                "🚀 COMMAND OPERATIONS\n"
                "  i  Init library (prompt for path)\n"
                "  s  Scan library (uses current path)\n"
                "  r  Run full pipeline (scan→scrape→generate)\n"
                "  o  Optimize videos (crop to 4:3)\n"
                "  u  Undo last operation\n\n"
                "📁 LIBRARY MANAGEMENT\n"
                "  l  List recent libraries\n"
                "  n  New library (prompt for path, run init)\n"
                "  c  Change library (browse/prompt for path)\n\n"
                "⚙️  SETTINGS & MONITORING\n"
                "  p  Provider mode settings\n"
                "  v  View system information\n"
                "  t  Test connectivity\n\n"
                "🔧 PROVIDER MODES\n"
                "  Primary          Use TVDB/TMDB when keys are set\n"
                "  Prefer Fallback  Try TVmaze/OMDb first\n"
                "  Fallback Only    Only use TVmaze/OMDb\n"
                "  Offline          No network calls; use cache only\n\n"
                "⏱️  PROGRESS INDICATORS\n"
                "• Spinning animation shows operations are running\n"
                "• Progress panel displays current operation and duration\n"
                "• Estimated times: Scan (10-30s), Scrape (2-10min), Optimize (5-30min)\n"
                "• Jobs panel shows detailed progress for background operations\n"
                "• UI remains responsive during long operations\n\n"
                "💡 TIPS & TRICKS\n"
                "• Use F1 for context-sensitive help on any element\n"
                "• Panels auto-refresh to show real-time status\n"
                "• Check system status for disk space and API keys\n"
                "• Test connectivity before running scrape operations\n"
                "• Use undo (u) if something goes wrong\n"
                "• Long operations show progress in the progress panel\n\n"
                "🆘 TROUBLESHOOTING\n"
                "• No shows found? Check library structure\n"
                "• Scrape failing? Verify API keys and connectivity\n"
                "• Low disk space? Check system status\n"
                "• TUI not responding? Press 'q' to quit and restart\n"
                "• Operation taking too long? Check progress panel for status\n"
            )

        def _get_context_help(self, element_id: str) -> str:
            """Get context-sensitive help for a specific element."""
            help_texts = {
                "init_btn": (
                    "🔧 Initialize Library\n"
                    "==================\n\n"
                    "Creates a new MPV library with proper structure:\n"
                    "• Creates /Movies directory for movies\n"
                    "• Creates /images directory for artwork\n"
                    "• Generates mpv-scraper.toml configuration\n"
                    "• Creates .env file for API keys\n\n"
                    "Usage: Press 'i' or click the button, then enter the path\n"
                    "Example: /Volumes/SD Card/roms/mpv\n\n"
                    "This is the first step for any new library!"
                ),
                "scan_btn": (
                    "🔍 Scan Library\n"
                    "==============\n\n"
                    "Scans the current library and shows what was found:\n"
                    "• Counts TV show folders\n"
                    "• Counts movie files\n"
                    "• Validates library structure\n"
                    "• Shows summary in jobs panel\n\n"
                    "Usage: Press 's' or click the button\n"
                    "No path needed - uses current library\n\n"
                    "Run this to see what the scraper will process!"
                ),
                "run_btn": (
                    "🚀 Run Full Pipeline\n"
                    "==================\n\n"
                    "Executes the complete workflow:\n"
                    "1. Scan library for shows/movies\n"
                    "2. Scrape metadata from APIs\n"
                    "3. Generate gamelist.xml files\n\n"
                    "Usage: Press 'r' or click the button\n"
                    "This is the main operation - processes everything!\n\n"
                    "Make sure you have API keys set up first."
                ),
                "optimize_btn": (
                    "🎬 Optimize Videos\n"
                    "=================\n\n"
                    "Crops videos to 4:3 aspect ratio:\n"
                    "• Removes letterboxing (black bars)\n"
                    "• Optimizes for 4:3 displays\n"
                    "• Useful for older content like cartoons\n\n"
                    "Usage: Press 'o' or click the button\n"
                    "Currently runs crop operation with default settings\n\n"
                    "Great for classic TV shows and cartoons!"
                ),
                "undo_btn": (
                    "↩️  Undo Last Operation\n"
                    "=====================\n\n"
                    "Reverts the most recent scraper operation:\n"
                    "• Restores original files\n"
                    "• Removes generated metadata\n"
                    "• Uses transaction.log for safety\n\n"
                    "Usage: Press 'u' or click the button\n"
                    "Only works if transaction.log exists\n\n"
                    "Safety net if something goes wrong!"
                ),
                "list_btn": (
                    "📋 List Libraries\n"
                    "================\n\n"
                    "Shows recently used libraries:\n"
                    "• Displays up to 5 recent paths\n"
                    "• Stored in ~/.mpv-scraper/library_history.json\n"
                    "• Shows in libraries panel\n\n"
                    "Usage: Press 'l' or click the button\n"
                    "Quick way to see your library history\n\n"
                    "Useful for switching between multiple libraries!"
                ),
                "new_btn": (
                    "🆕 New Library\n"
                    "=============\n\n"
                    "Creates and initializes a new library:\n"
                    "• Prompts for library path\n"
                    "• Runs init command automatically\n"
                    "• Switches to the new library\n\n"
                    "Usage: Press 'n' or click the button\n"
                    "Combines 'i' (init) and 'c' (change) operations\n\n"
                    "Perfect for setting up a new library quickly!"
                ),
                "change_btn": (
                    "🔄 Change Library\n"
                    "================\n\n"
                    "Switches to a different library:\n"
                    "• Shows library selection modal\n"
                    "• Lists recent libraries\n"
                    "• Validates library structure\n\n"
                    "Usage: Press 'c' or click the button\n"
                    "Shows modal with recent libraries to choose from\n\n"
                    "Great for managing multiple libraries!"
                ),
                "provider_btn": (
                    "⚙️  Provider Settings\n"
                    "===================\n\n"
                    "Configure metadata provider preferences:\n"
                    "• Primary: Use TVDB/TMDB when keys are set\n"
                    "• Prefer Fallback: Try TVmaze/OMDb first\n"
                    "• Fallback Only: Only use TVmaze/OMDb\n"
                    "• Offline: No network calls; use cache only\n\n"
                    "Usage: Press 'p' or click the button\n"
                    "Opens settings modal with provider options\n\n"
                    "Configure based on your API key availability!"
                ),
                "system_btn": (
                    "💻 System Information\n"
                    "====================\n\n"
                    "Shows comprehensive system details:\n"
                    "• Operating system and version\n"
                    "• Python version\n"
                    "• Architecture\n"
                    "• Disk space (total and free)\n"
                    "• ffmpeg version\n\n"
                    "Usage: Press 'v' or click the button\n"
                    "Displays detailed system info in settings panel\n\n"
                    "Useful for troubleshooting and system verification!"
                ),
                "test_btn": (
                    "🌐 Test Connectivity\n"
                    "==================\n\n"
                    "Tests network and API connectivity:\n"
                    "• Internet connection (8.8.8.8)\n"
                    "• TVDB API (api4.thetvdb.com)\n"
                    "• TMDB API (api.themoviedb.org)\n"
                    "• TVmaze API (api.tvmaze.com)\n"
                    "• OMDb API (www.omdbapi.com)\n\n"
                    "Usage: Press 't' or click the button\n"
                    "Shows connectivity results in settings panel\n\n"
                    "Run this before scraping to ensure APIs are reachable!"
                ),
                "jobs": (
                    "📊 Jobs Panel\n"
                    "============\n\n"
                    "Shows recent job activity:\n"
                    "• Displays up to 5 recent jobs\n"
                    "• Shows job status and progress\n"
                    "• Auto-refreshes every second\n"
                    "• Data from .mpv-scraper/jobs.json\n\n"
                    "Jobs include: scan, scrape, generate operations\n"
                    "Status indicators: completed, running, failed\n\n"
                    "Monitor your scraper activity here!"
                ),
                "logs": (
                    "📝 Logs Panel\n"
                    "============\n\n"
                    "Shows recent log entries:\n"
                    "• Displays last 5 lines from mpv-scraper.log\n"
                    "• Color-coded: ERROR (red), WARNING (yellow)\n"
                    "• Auto-refreshes every second\n"
                    "• Located in current library directory\n\n"
                    "Useful for debugging and monitoring operations\n"
                    "Check here if something goes wrong!\n\n"
                    "Logs are written to mpv-scraper.log in your library."
                ),
                "commands_panel": (
                    "🎮 Commands Panel\n"
                    "================\n\n"
                    "Shows command execution status:\n"
                    "• Displays current command being executed\n"
                    "• Shows success (✓) or failure (✗) indicators\n"
                    "• Updates in real-time during operations\n"
                    "• Shows error messages if commands fail\n\n"
                    "Commands run in background threads\n"
                    "UI remains responsive during execution\n\n"
                    "Watch here to see what's happening!"
                ),
                "libraries_panel": (
                    "📁 Libraries Panel\n"
                    "=================\n\n"
                    "Shows current library information:\n"
                    "• Displays current library path\n"
                    "• Updates when switching libraries\n"
                    "• Shows library history when listing\n"
                    "• Validates library structure\n\n"
                    "Current library is used for all operations\n"
                    "Switch libraries with 'c' (change) command\n\n"
                    "Always know which library you're working with!"
                ),
                "settings_panel": (
                    "⚙️  Settings Panel\n"
                    "=================\n\n"
                    "Shows real-time system status:\n"
                    "• Disk space with warnings for low space\n"
                    "• Network connectivity status\n"
                    "• API key validation (TVDB/TMDB)\n"
                    "• Auto-refreshes every second\n\n"
                    "Status indicators:\n"
                    "💾 Disk space, 🌐 Network, 🔑 API keys\n"
                    "⚠️  Warnings, ❌ Errors, ✅ Success\n\n"
                    "Monitor your system health here!"
                ),
                "progress_panel": (
                    "⏱️  Progress Panel\n"
                    "=================\n\n"
                    "Shows real-time operation progress:\n"
                    "• Spinning animation indicates active operations\n"
                    "• Operation name and running duration\n"
                    "• Progress information from jobs.json\n"
                    "• Estimated completion times\n\n"
                    "Operation estimates:\n"
                    "• Scan: 10-30 seconds\n"
                    "• Scrape: 2-10 minutes\n"
                    "• Optimize/Crop: 5-30 minutes\n"
                    "• Generate: 30 seconds - 2 minutes\n\n"
                    "Watch here during long operations!"
                ),
            }

            return help_texts.get(element_id, self._get_general_help())

        def _get_general_help(self) -> str:
            """Get general help when no specific context is available."""
            return (
                "🎯 MPV-Scraper TUI - General Help\n"
                "===============================\n\n"
                "Welcome to the MPV-Scraper Text User Interface!\n\n"
                "📋 QUICK REFERENCE\n"
                "• Press '?' for comprehensive help\n"
                "• Press 'F1' for context-sensitive help\n"
                "• Press 'q' to quit\n\n"
                "🚀 GETTING STARTED\n"
                "1. Press 'i' to initialize a new library\n"
                "2. Press 's' to scan for content\n"
                "3. Press 'r' to run the full pipeline\n\n"
                "💡 TIP\n"
                "Focus on any element and press F1 for specific help!\n\n"
                "For detailed help, press '?' to see the complete guide."
            )

        def _get_troubleshooting_guide(self) -> str:
            """Get comprehensive troubleshooting guide."""
            return (
                "🆘 TROUBLESHOOTING GUIDE\n"
                "========================\n\n"
                "🔍 COMMON ISSUES & SOLUTIONS\n\n"
                "❌ No shows/movies found during scan\n"
                "   → Check library structure (needs /Movies or show folders)\n"
                "   → Verify file extensions (.mp4, .mkv, etc.)\n"
                "   → Ensure library path is correct\n\n"
                "❌ Scrape operations failing\n"
                "   → Press 't' to test connectivity\n"
                "   → Check API keys in .env file\n"
                "   → Verify network connection\n"
                "   → Try different provider mode\n\n"
                "❌ Low disk space warnings\n"
                "   → Check system status panel\n"
                "   → Free up space on target drive\n"
                "   → Consider using external storage\n\n"
                "❌ TUI not responding\n"
                "   → Press 'q' to quit and restart\n"
                "   → Check if commands are running in background\n"
                "   → Verify Python and dependencies are installed\n\n"
                "❌ API key validation failing\n"
                "   → Check .env file in library directory\n"
                "   → Verify TVDB_API_KEY and TMDB_API_KEY are set\n"
                "   → Ensure keys are valid and active\n\n"
                "❌ ffmpeg not found\n"
                "   → Install ffmpeg on your system\n"
                "   → Ensure it's in your PATH\n"
                "   → Check system info with 'v' command\n\n"
                "🔧 ADVANCED TROUBLESHOOTING\n\n"
                "📝 Check Logs\n"
                "• Look at the logs panel for error messages\n"
                "• Check mpv-scraper.log in your library directory\n"
                "• Look for ERROR and WARNING messages\n\n"
                "🌐 Network Issues\n"
                "• Press 't' to test connectivity\n"
                "• Check firewall settings\n"
                "• Try different network connection\n"
                "• Use 'offline' provider mode if needed\n\n"
                "💾 Disk Issues\n"
                "• Check available disk space\n"
                "• Ensure write permissions to library directory\n"
                "• Try different storage location\n\n"
                "🔄 Reset Operations\n"
                "• Use 'u' (undo) to revert last operation\n"
                "• Delete .mpv-scraper directory to reset completely\n"
                "• Re-initialize library with 'i' command\n\n"
                "📞 GETTING HELP\n"
                "• Check the comprehensive help with '?'\n"
                "• Use context-sensitive help with F1\n"
                "• Review system status with 'v' command\n"
                "• Test connectivity with 't' command\n"
            )

        def _get_command_reference(self) -> str:
            """Get detailed command reference with examples."""
            return (
                "📚 COMMAND REFERENCE\n"
                "===================\n\n"
                "🚀 CORE COMMANDS\n\n"
                "🔧 INIT (i)\n"
                "   Purpose: Initialize a new MPV library\n"
                "   Usage: Press 'i' or click Init button\n"
                "   Example: /Volumes/SD Card/roms/mpv\n"
                "   Creates: /Movies, /images, mpv-scraper.toml, .env\n\n"
                "🔍 SCAN (s)\n"
                "   Purpose: Scan library for shows and movies\n"
                "   Usage: Press 's' or click Scan button\n"
                "   Output: Shows count of TV shows and movies found\n"
                "   Example: 'Found 5 show folders and 12 movies'\n\n"
                "🚀 RUN (r)\n"
                "   Purpose: Execute full pipeline (scan→scrape→generate)\n"
                "   Usage: Press 'r' or click Run button\n"
                "   Steps: 1. Scan library 2. Scrape metadata 3. Generate XML\n"
                "   Time: Can take several minutes depending on library size\n\n"
                "🎬 OPTIMIZE (o)\n"
                "   Purpose: Crop videos to 4:3 aspect ratio\n"
                "   Usage: Press 'o' or click Optimize button\n"
                "   Target: Removes letterboxing from older content\n"
                "   Example: Great for classic cartoons and TV shows\n\n"
                "↩️  UNDO (u)\n"
                "   Purpose: Revert last scraper operation\n"
                "   Usage: Press 'u' or click Undo button\n"
                "   Safety: Uses transaction.log for safe rollback\n"
                "   Note: Only works if transaction.log exists\n\n"
                "📁 LIBRARY MANAGEMENT\n\n"
                "📋 LIST (l)\n"
                "   Purpose: Show recent libraries\n"
                "   Usage: Press 'l' or click List button\n"
                "   Display: Shows up to 5 recent library paths\n"
                "   Storage: ~/.mpv-scraper/library_history.json\n\n"
                "🆕 NEW (n)\n"
                "   Purpose: Create and switch to new library\n"
                "   Usage: Press 'n' or click New button\n"
                "   Action: Combines init + change operations\n"
                "   Example: Quick setup for new SD card\n\n"
                "🔄 CHANGE (c)\n"
                "   Purpose: Switch to different library\n"
                "   Usage: Press 'c' or click Change button\n"
                "   Modal: Shows library selection with recent paths\n"
                "   Validation: Checks library structure before switching\n\n"
                "⚙️  SETTINGS & MONITORING\n\n"
                "⚙️  PROVIDER (p)\n"
                "   Purpose: Configure metadata provider preferences\n"
                "   Usage: Press 'p' or click Provider button\n"
                "   Options: Primary, Prefer Fallback, Fallback Only, Offline\n"
                "   Impact: Affects which APIs are used for scraping\n\n"
                "💻 SYSTEM (v)\n"
                "   Purpose: View comprehensive system information\n"
                "   Usage: Press 'v' or click System button\n"
                "   Info: OS, Python, Architecture, Disk, ffmpeg\n"
                "   Use: Troubleshooting and system verification\n\n"
                "🌐 TEST (t)\n"
                "   Purpose: Test network and API connectivity\n"
                "   Usage: Press 't' or click Test button\n"
                "   Tests: Internet, TVDB, TMDB, TVmaze, OMDb\n"
                "   Output: Shows ✅/❌ status for each endpoint\n\n"
                "🎯 WORKFLOW EXAMPLES\n\n"
                "📱 New SD Card Setup:\n"
                "1. Press 'n' → Enter path → Auto-initialize\n"
                "2. Press 't' → Verify connectivity\n"
                "3. Press 'r' → Run full pipeline\n\n"
                "🔄 Switch Between Libraries:\n"
                "1. Press 'c' → Select from recent libraries\n"
                "2. Press 's' → Verify content is found\n"
                "3. Press 'r' → Process if needed\n\n"
                "🔧 Troubleshooting:\n"
                "1. Press 'v' → Check system status\n"
                "2. Press 't' → Test connectivity\n"
                "3. Press '?' → Get comprehensive help\n"
            )

        def action_quit(self) -> None:
            self.exit()

        def action_init_library(self) -> None:
            self._start_operation("init")
            self._show_path_modal("init")

        def action_scan_library(self) -> None:
            self._start_operation("scan")
            self._execute_command("scan", self._get_current_path())

        def action_run_pipeline(self) -> None:
            self._start_operation("run")
            self._execute_command("run", self._get_current_path())

        def action_optimize_videos(self) -> None:
            self._start_operation("optimize")
            # For now, just run crop with default settings
            self._execute_command("crop", self._get_current_path())

        def action_undo_last(self) -> None:
            self._start_operation("undo")
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

        def action_provider_settings(self) -> None:
            """Open provider mode settings."""
            current_settings = self._get_library_settings()
            self.push_screen(SettingsModal(current_settings), self._on_settings_result)

        def action_view_system_info(self) -> None:
            """View system information."""
            info = self._get_system_info()
            self.settings_box.update(info)

        def action_test_connectivity(self) -> None:
            """Test connectivity to API endpoints."""
            self._test_connectivity()

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
            elif event.button.id == "provider_btn":
                self.action_provider_settings()
            elif event.button.id == "system_btn":
                self.action_view_system_info()
            elif event.button.id == "test_btn":
                self.action_test_connectivity()

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

        def _load_tui_preferences(self) -> None:
            """Load TUI preferences from file."""
            try:
                if self._tui_preferences_file.exists():
                    data = json.loads(self._tui_preferences_file.read_text())
                    self._refresh_rate = data.get("refresh_rate", 1.0)
            except Exception:
                self._refresh_rate = 1.0

        def _save_tui_preferences(self) -> None:
            """Save TUI preferences to file."""
            try:
                self._tui_preferences_file.parent.mkdir(parents=True, exist_ok=True)
                data = {"refresh_rate": self._refresh_rate}
                self._tui_preferences_file.write_text(json.dumps(data, indent=2))
            except Exception:
                pass

        def _get_library_settings(self) -> Dict[str, Any]:
            """Get library-specific settings."""
            try:
                from pathlib import Path

                lib_path = Path(self._get_current_path())
                settings_file = lib_path / "mpv-scraper.toml"

                if settings_file.exists():
                    # For now, return default settings
                    # In a real implementation, parse TOML file
                    return {
                        "provider_mode": "primary",
                        "theme": "dark",
                        "refresh_rate": self._refresh_rate,
                    }
            except Exception:
                pass

            return {
                "provider_mode": "primary",
                "theme": "dark",
                "refresh_rate": self._refresh_rate,
            }

        def _save_library_settings(self, settings: Dict[str, Any]) -> None:
            """Save library-specific settings."""
            try:
                # For now, just update TUI preferences
                if "refresh_rate" in settings:
                    self._refresh_rate = settings["refresh_rate"]
                    self._save_tui_preferences()
            except Exception:
                pass

        def _get_system_info(self) -> str:
            """Get comprehensive system information."""
            try:
                from pathlib import Path

                # System info
                system_info = [
                    f"System: {platform.system()} {platform.release()}",
                    f"Python: {sys.version.split()[0]}",
                    f"Architecture: {platform.machine()}",
                ]

                # Disk space
                lib_path = Path(self._get_current_path())
                if lib_path.exists():
                    total, used, free = shutil.disk_usage(lib_path)
                    total_gb = total / (1024**3)
                    free_gb = free / (1024**3)
                    system_info.append(
                        f"Disk: {free_gb:.1f}GB free of {total_gb:.1f}GB"
                    )

                # ffmpeg version
                try:
                    result = subprocess.run(
                        ["ffmpeg", "-version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        version_line = result.stdout.split("\n")[0]
                        system_info.append(f"ffmpeg: {version_line.split()[2]}")
                    else:
                        system_info.append("ffmpeg: Not found")
                except Exception:
                    system_info.append("ffmpeg: Not found")

                return "System Info:\n" + "\n".join(system_info)

            except Exception as e:
                return f"System Info: Error - {str(e)}"

        def _get_system_status(self) -> str:
            """Get real-time system status."""
            try:
                from pathlib import Path

                status_lines = ["System Status:"]

                # Disk space
                lib_path = Path(self._get_current_path())
                if lib_path.exists():
                    total, used, free = shutil.disk_usage(lib_path)
                    free_gb = free / (1024**3)
                    if free_gb < 1.0:
                        status_lines.append(f"⚠️  Low disk space: {free_gb:.1f}GB")
                    else:
                        status_lines.append(f"💾 Disk: {free_gb:.1f}GB free")

                # Network connectivity (basic test)
                try:
                    import socket

                    socket.create_connection(("8.8.8.8", 53), timeout=3)
                    status_lines.append("🌐 Network: Connected")
                except Exception:
                    status_lines.append("❌ Network: Disconnected")

                # API keys (basic check)
                env_file = lib_path / ".env"
                if env_file.exists():
                    try:
                        env_content = env_file.read_text()
                        if (
                            "TVDB_API_KEY=" in env_content
                            and "TVDB_API_KEY=\n" not in env_content
                        ):
                            status_lines.append("🔑 TVDB: Key set")
                        else:
                            status_lines.append("⚠️  TVDB: No key")

                        if (
                            "TMDB_API_KEY=" in env_content
                            and "TMDB_API_KEY=\n" not in env_content
                        ):
                            status_lines.append("🔑 TMDB: Key set")
                        else:
                            status_lines.append("⚠️  TMDB: No key")
                    except Exception:
                        status_lines.append("⚠️  API: Config error")
                else:
                    status_lines.append("⚠️  API: No config")

                return "\n".join(status_lines)

            except Exception as e:
                return f"Status: Error - {str(e)}"

        def _test_connectivity(self) -> None:
            """Test connectivity to API endpoints."""
            try:
                self.settings_box.update("Testing connectivity...")

                # Test basic internet connectivity
                import socket

                try:
                    socket.create_connection(("8.8.8.8", 53), timeout=3)
                    internet_status = "✅ Internet: Connected"
                except Exception:
                    internet_status = "❌ Internet: Disconnected"

                # Test API endpoints (basic DNS resolution)
                endpoints = [
                    ("TVDB", "api4.thetvdb.com"),
                    ("TMDB", "api.themoviedb.org"),
                    ("TVmaze", "api.tvmaze.com"),
                    ("OMDb", "www.omdbapi.com"),
                ]

                results = [internet_status]
                for name, host in endpoints:
                    try:
                        socket.gethostbyname(host)
                        results.append(f"✅ {name}: Reachable")
                    except Exception:
                        results.append(f"❌ {name}: Unreachable")

                self.settings_box.update("Connectivity Test:\n" + "\n".join(results))

            except Exception as e:
                self.settings_box.update(f"Connectivity test failed: {str(e)}")

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

        def _on_settings_result(self, result: Optional[Dict[str, Any]]) -> None:
            """Handle result from settings modal."""
            if result:
                self._save_library_settings(result)
                self.settings_box.update("Settings saved successfully!")

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
                from pathlib import Path

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
                    self._end_operation(success=True)
                else:
                    self.commands_box.update(f"✗ {command} failed: {result.stderr}")
                    self._end_operation(success=False)

            except Exception as e:
                self.commands_box.update(f"✗ {command} error: {str(e)}")
                self._end_operation(success=False)

        def _refresh_panels(self) -> None:
            # Lightweight periodic updates
            try:
                if self.logs_box is not None:
                    self.logs_box.update(self._read_log_tail())
                if self.jobs_box is not None:
                    self.jobs_box.update(self._jobs_snapshot())
                if self.libraries_box is not None:
                    self.libraries_box.update(f"Current: {self._get_current_path()}")
                if self.settings_box is not None:
                    self.settings_box.update(self._get_system_status())
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
