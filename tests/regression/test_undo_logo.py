from pathlib import Path
from click.testing import CliRunner

from mpv_scraper.cli import main as cli


def test_logo_undo(tmp_path: Path):
    """Ensure logo.png is created and removed by undo."""

    # Build minimal show folder with one episode
    show_dir = tmp_path / "My Show"
    show_dir.mkdir(parents=True)
    (show_dir / "My Show - S01E01 - Pilot.mp4").touch()

    runner = CliRunner()

    # Run generate (without scraping)
    result = runner.invoke(cli, ["generate", str(tmp_path)])
    assert result.exit_code == 0

    logo_path = show_dir / "images" / "logo.png"
    assert logo_path.exists(), "Logo placeholder should be created"

    # Undo
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        result = runner.invoke(cli, ["undo"])
        assert result.exit_code == 0

    assert not logo_path.exists(), "Logo should be removed after undo"
