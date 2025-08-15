"""Simple CLI coverage tests for Sprint 18.4.

Tests basic CLI error handling and validation to improve coverage.
"""

from pathlib import Path
from click.testing import CliRunner


class TestCLIBasicErrorHandling:
    """Test basic CLI error handling paths."""

    def test_init_command_with_invalid_path(self):
        """Test init command with invalid path."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["init", "/nonexistent/path"])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_init_command_with_file_path(self):
        """Test init command with file path instead of directory."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test_file.txt").touch()
            result = runner.invoke(main, ["init", "test_file.txt"])

        assert result.exit_code != 0
        assert "is a file" in result.output

    def test_scan_command_with_invalid_path(self):
        """Test scan command with invalid path."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["scan", "/nonexistent/path"])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_scan_command_with_file_path(self):
        """Test scan command with file path instead of directory."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test_file.txt").touch()
            result = runner.invoke(main, ["scan", "test_file.txt"])

        assert result.exit_code != 0
        assert "is a file" in result.output

    def test_scrape_command_with_invalid_path(self):
        """Test scrape command with invalid path."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["scrape", "/nonexistent/path"])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_generate_command_with_invalid_path(self):
        """Test generate command with invalid path."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["generate", "/nonexistent/path"])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_run_command_with_invalid_path(self):
        """Test run command with invalid path."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["run", "/nonexistent/path"])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_undo_command_with_invalid_path(self):
        """Test undo command with invalid path."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["undo", "/nonexistent/path"])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_undo_command_with_no_transaction_log(self):
        """Test undo command with no transaction log."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["undo", "."])

        assert result.exit_code == 0
        assert "No transaction.log found" in result.output

    def test_tui_command_with_invalid_path_option(self):
        """Test tui command with invalid path option."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main, ["tui", "--non-interactive", "--path", "/nonexistent/path"]
        )

        # TUI command with --non-interactive should succeed even with invalid path
        # because it doesn't validate the path in non-interactive mode
        assert result.exit_code == 0


class TestCLIHelpOutput:
    """Test CLI help output generation."""

    def test_main_help_output(self):
        """Test main help output."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "A CLI tool to scrape metadata for TV shows and movies" in result.output
        assert "Commands:" in result.output

    def test_init_help_output(self):
        """Test init command help output."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--help"])

        assert result.exit_code == 0
        assert "First-run wizard" in result.output
        assert "--force" in result.output

    def test_scan_help_output(self):
        """Test scan command help output."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["scan", "--help"])

        assert result.exit_code == 0
        assert "Scan DIRECTORY" in result.output

    def test_scrape_help_output(self):
        """Test scrape command help output."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["scrape", "--help"])

        assert result.exit_code == 0
        assert "Scrape metadata and artwork" in result.output
        assert "--prefer-fallback" in result.output

    def test_generate_help_output(self):
        """Test generate command help output."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["generate", "--help"])

        assert result.exit_code == 0
        assert "Generate gamelist.xml files" in result.output

    def test_run_help_output(self):
        """Test run command help output."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "End-to-end scan" in result.output

    def test_undo_help_output(self):
        """Test undo command help output."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["undo", "--help"])

        assert result.exit_code == 0
        assert "Undo the most recent scraper run" in result.output

    def test_tui_help_output(self):
        """Test tui command help output."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["tui", "--help"])

        assert result.exit_code == 0
        assert "Start the mpv-scraper TUI" in result.output


class TestCLIArgumentValidation:
    """Test CLI argument validation."""

    def test_path_argument_validation(self):
        """Test path argument validation."""
        from mpv_scraper.cli import main

        runner = CliRunner()

        # Test with missing path
        result = runner.invoke(main, ["init"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

        # Test with multiple paths - this should fail with path validation first
        result = runner.invoke(main, ["init", "path1", "path2"])
        assert result.exit_code != 0
        # The error message varies depending on which validation fails first
        assert result.exit_code == 2

    def test_boolean_flag_validation(self):
        """Test boolean flag validation."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Test force flag
            result = runner.invoke(main, ["init", ".", "--force"])
            assert result.exit_code == 0

            # Test prefer-fallback flag
            result = runner.invoke(main, ["scrape", ".", "--prefer-fallback"])
            assert result.exit_code == 0

            # Test fallback-only flag
            result = runner.invoke(main, ["scrape", ".", "--fallback-only"])
            assert result.exit_code == 0

            # Test no-remote flag
            result = runner.invoke(main, ["scrape", ".", "--no-remote"])
            assert result.exit_code == 0

    def test_optional_path_argument(self):
        """Test optional path argument in tui command."""
        from mpv_scraper.cli import main

        runner = CliRunner()

        # Test without path (should work)
        result = runner.invoke(main, ["tui", "--non-interactive"])
        assert result.exit_code == 0

        # Test with path
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["tui", "--non-interactive", "--path", "."])
            assert result.exit_code == 0

    def test_undo_path_argument(self):
        """Test undo command path argument."""
        from mpv_scraper.cli import main

        runner = CliRunner()

        # Test without path (should work)
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["undo"])
            assert result.exit_code == 0

        # Test with path
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["undo", "."])
            assert result.exit_code == 0


class TestCLIConfigLoading:
    """Test CLI config loading and validation logic."""

    def test_config_file_creation_with_force(self):
        """Test config file creation with force flag."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create initial config
            result1 = runner.invoke(main, ["init", "."])
            assert result1.exit_code == 0
            assert "Wrote" in result1.output

            # Force recreate config
            result2 = runner.invoke(main, ["init", ".", "--force"])
            assert result2.exit_code == 0
            assert "Wrote" in result2.output

    def test_config_file_creation_without_force(self):
        """Test config file creation without force flag."""
        from mpv_scraper.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create initial config
            result1 = runner.invoke(main, ["init", "."])
            assert result1.exit_code == 0
            assert "Wrote" in result1.output

            # Try to create again without force
            result2 = runner.invoke(main, ["init", "."])
            assert result2.exit_code == 0
            assert "Found existing" in result2.output
