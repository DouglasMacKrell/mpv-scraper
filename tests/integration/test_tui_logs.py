from click.testing import CliRunner


def test_log_tail_renders_lines(tmp_path, monkeypatch):
    # Write a small log file with mixed levels
    log = tmp_path / "mpv-scraper.log"
    log.write_text(
        """
2025-01-01T00:00:00 INFO starting job
2025-01-01T00:00:01 WARNING something odd
2025-01-01T00:00:02 ERROR boom
""".strip()
    )

    monkeypatch.chdir(tmp_path)

    from mpv_scraper.cli import main as cli_main

    runner = CliRunner()
    res = runner.invoke(cli_main, ["tui", "--non-interactive"])
    assert res.exit_code == 0, res.output
    out = res.output
    # Validate the tail content appears
    assert "WARNING" in out and "ERROR" in out
