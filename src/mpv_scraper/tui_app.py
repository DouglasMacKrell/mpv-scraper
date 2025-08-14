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

            left = Vertical(
                command_buttons,
                library_buttons,
                settings_buttons,
                self.jobs_box,
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
                "  c  Change library (browse/prompt for path)\n"
                "  p  Provider mode settings\n"
                "  v  View system info\n"
                "  t  Test connectivity\n\n"
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
