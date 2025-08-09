from pathlib import Path
from click.testing import CliRunner
import pytest

from mpv_scraper.cli import main as cli_main


@pytest.fixture(scope="module")
def tmp_media(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Provide a temp dir with a minimal media library."""
    root = tmp_path_factory.mktemp("media")
    (root / "Movies").mkdir()
    # create dummy files so scanner finds something
    (root / "Movies" / "Stub (2024).mp4").touch()
    show_dir = root / "Example Show"
    show_dir.mkdir()
    (show_dir / "Example Show - S01E01 - Pilot.mp4").touch()
    return root


@pytest.mark.parametrize(
    "command, args",
    [
        ("scan", lambda p: [str(p)]),
        ("scrape", lambda p: [str(p)]),
        ("generate", lambda p: [str(p)]),
        ("run", lambda p: [str(p)]),
        ("undo", lambda p: []),  # undo runs in cwd containing transaction.log or not
    ],
)
def test_cli_smoke(command: str, args, tmp_media: Path, monkeypatch):
    """Ensure CLI commands exit 0 quickly (smoke test)."""

    runner = CliRunner()

    if command == "undo":
        # ensure cwd has no transaction.log so command still exits 0
        monkeypatch.chdir(tmp_media)
        result = runner.invoke(cli_main, [command])
    else:
        result = runner.invoke(cli_main, [command, *args(tmp_media)])

    assert result.exit_code == 0, result.output


def test_scrape_command(tmp_media: Path, monkeypatch):
    """Test the scrape command specifically with mocked scrapers."""
    from unittest.mock import patch

    runner = CliRunner()

    # Mock the scraper functions to avoid real API calls
    with patch("mpv_scraper.scraper.scrape_tv_parallel") as mock_scrape_tv, patch(
        "mpv_scraper.scraper.scrape_movie"
    ) as mock_scrape_movie:
        result = runner.invoke(cli_main, ["scrape", str(tmp_media)])

        assert result.exit_code == 0, result.output
        assert "scraping" in result.output.lower(), "Should mention scraping in output"

        # Verify scrapers were called for the discovered content
        assert (
            mock_scrape_tv.called
        ), "scrape_tv_parallel should be called for show directories"
        assert mock_scrape_movie.called, "scrape_movie should be called for movie files"


def test_run_command_includes_scrape(tmp_media: Path, monkeypatch):
    """Test that the run command includes the scrape step."""
    from unittest.mock import patch

    runner = CliRunner()

    # Mock the scraper functions to avoid real API calls
    with patch("mpv_scraper.scraper.scrape_tv_parallel") as mock_scrape_tv, patch(
        "mpv_scraper.scraper.scrape_movie"
    ) as mock_scrape_movie:
        result = runner.invoke(cli_main, ["run", str(tmp_media)])

        assert result.exit_code == 0, result.output
        assert "scraping" in result.output.lower(), "Should mention scraping in output"

        # Verify scrapers were called as part of the run workflow
        assert mock_scrape_tv.called, "scrape_tv_parallel should be called during run"
        assert mock_scrape_movie.called, "scrape_movie should be called during run"
