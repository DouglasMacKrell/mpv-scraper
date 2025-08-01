def test_cli_imports():
    """Tests that the CLI entrypoint can be imported."""
    try:
        from mpv_scraper import cli
        from mpv_scraper.cli import run
    except ImportError as e:
        assert False, f"Failed to import CLI module or command: {e}"

    assert callable(cli.main)
    assert callable(run)
