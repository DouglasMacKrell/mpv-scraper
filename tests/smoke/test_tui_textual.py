from click.testing import CliRunner


def test_tui_non_interactive_renders():
    from mpv_scraper.cli import main as cli_main

    runner = CliRunner()
    result = runner.invoke(cli_main, ["tui", "--non-interactive"])
    assert result.exit_code == 0, result.output
    assert "mpv-scraper tui" in result.output.lower()
