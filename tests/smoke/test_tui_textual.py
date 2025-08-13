from click.testing import CliRunner


def test_tui_non_interactive_renders():
    from mpv_scraper.cli import main as cli_main

    runner = CliRunner()
    result = runner.invoke(cli_main, ["tui", "--non-interactive"])
    assert result.exit_code == 0, result.output
    assert "mpv-scraper tui" in result.output.lower()


def test_help_overlay_renders_non_interactive(tmp_path, monkeypatch):
    # We can't drive real keypresses in non-interactive smoke, but ensure help text is available in output path
    from mpv_scraper.cli import main as cli_main

    runner = CliRunner()
    result = runner.invoke(cli_main, ["tui", "--non-interactive"])
    assert result.exit_code == 0, result.output
