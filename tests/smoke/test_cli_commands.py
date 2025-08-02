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
