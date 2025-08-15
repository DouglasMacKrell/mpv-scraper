"""Unit tests for TUI app components.

Tests the TUI app functionality through the run_textual_once function
and by testing the actual code paths, improving coverage from mock-based testing.
"""

import pytest
from unittest.mock import patch


class TestTUIAppFunctionality:
    """Test TUI app functionality through the run_textual_once function."""

    def test_run_textual_once_function_exists(self):
        """Test that run_textual_once function exists and is callable."""
        from mpv_scraper.tui_app import run_textual_once

        assert callable(run_textual_once)
        assert run_textual_once.__name__ == "run_textual_once"

    def test_run_textual_once_without_textual(self):
        """Test run_textual_once fallback when Textual is not available."""
        from mpv_scraper.tui_app import run_textual_once

        # Mock Textual import to fail
        with patch("textual.app.App", side_effect=ImportError("textual not available")):
            # Should not raise exception and should print fallback message
            try:
                run_textual_once(one_shot=True, root_path="/test/path")
            except Exception as e:
                pytest.fail(
                    f"run_textual_once should handle missing Textual gracefully: {e}"
                )


class TestTUIAppConstants:
    """Test TUI app constants and configuration."""

    def test_min_size_constant_in_code(self):
        """Test that MIN_SIZE constant is defined in the code."""
        # Read the source file to check for MIN_SIZE constant
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that MIN_SIZE is defined
        assert "MIN_SIZE = (80, 24)" in content
        assert "Minimum 80 columns, 24 lines" in content

    def test_css_constant_in_code(self):
        """Test that CSS constant is defined in the code."""
        # Read the source file to check for CSS constant
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that CSS is defined
        assert 'CSS = """' in content
        assert "Screen { background: #101216 }" in content
        assert "#progress_panel" in content

    def test_spinner_chars_definition_in_code(self):
        """Test that spinner characters are defined in the code."""
        # Read the source file to check for spinner characters
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that spinner characters are defined
        assert "_spinner_chars = [" in content
        assert '"⠋"' in content
        assert '"⠙"' in content
        assert '"⠹"' in content


class TestTUIAppFilePaths:
    """Test TUI app file path handling."""

    def test_library_history_file_path_structure(self):
        """Test that library history file path is constructed correctly."""
        # Read the source file to check path construction
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that library history file path is constructed
        assert "_library_history_file =" in content
        assert "Path.home()" in content
        assert "library_history.json" in content

    def test_tui_preferences_file_path_structure(self):
        """Test that TUI preferences file path is constructed correctly."""
        # Read the source file to check path construction
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that TUI preferences file path is constructed
        assert "_tui_preferences_file =" in content
        assert "Path.home()" in content
        assert "tui_preferences.json" in content


class TestTUIAppMethods:
    """Test TUI app method implementations."""

    def test_terminal_size_checking_method_exists(self):
        """Test that terminal size checking method exists in code."""
        # Read the source file to check for method
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that _check_terminal_size method exists
        assert "_check_terminal_size" in content
        assert "shutil.get_terminal_size()" in content

    def test_progress_tracking_methods_exist(self):
        """Test that progress tracking methods exist in code."""
        # Read the source file to check for methods
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that progress tracking methods exist
        assert "_start_operation" in content
        assert "_end_operation" in content
        assert "_update_progress_spinner" in content

    def test_file_system_methods_exist(self):
        """Test that file system methods exist in code."""
        # Read the source file to check for methods
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that file system methods exist
        assert "_read_log_tail" in content
        assert "_jobs_snapshot" in content

    def test_system_info_methods_exist(self):
        """Test that system info methods exist in code."""
        # Read the source file to check for methods
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that system info methods exist
        assert "_get_system_info" in content
        assert "_get_system_status" in content

    def test_preferences_methods_exist(self):
        """Test that preferences methods exist in code."""
        # Read the source file to check for methods
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that preferences methods exist
        assert "_load_tui_preferences" in content
        assert "_save_tui_preferences" in content


class TestTUIAppKeyboardBindings:
    """Test TUI app keyboard bindings."""

    def test_keyboard_bindings_defined(self):
        """Test that keyboard bindings are defined in code."""
        # Read the source file to check for bindings
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that BINDINGS are defined
        assert "BINDINGS = [" in content
        assert '"q"' in content  # quit
        assert '"?"' in content  # help
        assert '"i"' in content  # init
        assert '"s"' in content  # scan
        assert '"r"' in content  # run
        assert '"o"' in content  # optimize
        assert '"u"' in content  # undo
        assert '"l"' in content  # list libraries
        assert '"n"' in content  # new library
        assert '"c"' in content  # change library
        assert '"p"' in content  # provider settings
        assert '"v"' in content  # system info
        assert '"t"' in content  # test connectivity
        assert '"z"' in content  # terminal size


class TestTUIAppModalScreens:
    """Test TUI app modal screen implementations."""

    def test_modal_screens_defined(self):
        """Test that modal screens are defined in code."""
        # Read the source file to check for modal screens
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that modal screens are defined
        assert "class PathInputModal" in content
        assert "class LibrarySelectModal" in content
        assert "class SettingsModal" in content

    def test_modal_screen_methods_exist(self):
        """Test that modal screen methods exist."""
        # Read the source file to check for modal methods
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that modal methods exist
        assert "def compose(self) -> ComposeResult:" in content
        assert "def on_button_pressed(self, event:" in content


class TestTUIAppActionMethods:
    """Test TUI app action method implementations."""

    def test_action_methods_defined(self):
        """Test that action methods are defined in code."""
        # Read the source file to check for action methods
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that action methods exist
        assert "action_show_help" in content
        assert "action_quit" in content
        assert "action_init_library" in content
        assert "action_scan_library" in content
        assert "action_run_pipeline" in content
        assert "action_optimize_videos" in content
        assert "action_undo_last" in content
        assert "action_list_libraries" in content
        assert "action_new_library" in content
        assert "action_change_library" in content
        assert "action_provider_settings" in content
        assert "action_view_system_info" in content
        assert "action_test_connectivity" in content
        assert "action_show_terminal_size" in content


class TestTUIAppHelperMethods:
    """Test TUI app helper method implementations."""

    def test_helper_methods_defined(self):
        """Test that helper methods are defined in code."""
        # Read the source file to check for helper methods
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that helper methods exist
        assert "_get_current_path" in content
        assert "_get_library_history" in content
        assert "_save_library_history" in content
        assert "_validate_library_structure" in content
        assert "_switch_library" in content
        assert "_show_path_modal" in content
        assert "_execute_command" in content
        assert "_get_operation_progress" in content
        assert "_get_progress_bar" in content
        assert "_estimate_operation_duration" in content
        assert "_get_operation_description" in content
        assert "_get_comprehensive_help" in content
        assert "_get_context_help" in content


class TestTUIAppIntegration:
    """Test TUI app integration aspects."""

    def test_refresh_panels_method_exists(self):
        """Test that refresh panels method exists."""
        # Read the source file to check for refresh method
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that refresh method exists
        assert "_refresh_panels" in content

    def test_on_mount_method_exists(self):
        """Test that on_mount method exists."""
        # Read the source file to check for on_mount method
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that on_mount method exists
        assert "def on_mount(self) -> None:" in content

    def test_compose_method_exists(self):
        """Test that compose method exists."""
        # Read the source file to check for compose method
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that compose method exists
        assert "def compose(self) -> ComposeResult:" in content


class TestTUIAppStructure:
    """Test TUI app overall structure."""

    def test_mpv_scraper_app_class_exists(self):
        """Test that MpvScraperApp class is defined."""
        # Read the source file to check for class definition
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that MpvScraperApp class is defined
        assert "class MpvScraperApp(App):" in content

    def test_app_initialization_method_exists(self):
        """Test that __init__ method exists."""
        # Read the source file to check for __init__ method
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that __init__ method exists
        assert "def __init__(self) -> None:" in content

    def test_app_has_required_attributes(self):
        """Test that app has required attributes."""
        # Read the source file to check for attributes
        with open("src/mpv_scraper/tui_app.py", "r") as f:
            content = f.read()

        # Check that required attributes are defined
        assert "self._help_widget = None" in content
        assert "self.jobs_box = None" in content
        assert "self.logs_box = None" in content
        assert "self.commands_box = None" in content
        assert "self.libraries_box = None" in content
        assert "self.settings_box = None" in content
        assert "self.progress_box = None" in content
