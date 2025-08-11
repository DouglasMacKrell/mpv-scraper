from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch


from mpv_scraper.cli import main as cli_main


def _read(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def test_init_writes_config(tmp_path: Path):
    runner = CliRunner()
    library = tmp_path / "mpv"
    library.mkdir()

    result = runner.invoke(cli_main, ["init", str(library)])
    assert result.exit_code == 0, result.output

    # Files and directories created
    config = library / "mpv-scraper.toml"
    env = library / ".env"
    env_example = library / ".env.example"
    images = library / "images"
    movies = library / "Movies"

    assert config.exists(), "config should be created"
    assert env.exists() or env_example.exists(), ".env or .env.example should exist"
    assert images.is_dir(), "images directory should be created"
    assert movies.is_dir(), "Movies directory should be created"

    # Minimal content check
    assert "library_root" in _read(config), "config should contain library_root"


def test_init_idempotent(tmp_path: Path):
    runner = CliRunner()
    library = tmp_path / "mpv"
    library.mkdir()

    # First run
    result1 = runner.invoke(cli_main, ["init", str(library)])
    assert result1.exit_code == 0, result1.output

    config = library / "mpv-scraper.toml"
    assert config.exists()
    original = config.read_text()

    # Second run should not overwrite without --force
    result2 = runner.invoke(cli_main, ["init", str(library)])
    assert result2.exit_code == 0, result2.output
    assert config.read_text() == original, "config should be unchanged without --force"


def test_init_validates_ffmpeg(tmp_path: Path):
    runner = CliRunner()
    library = tmp_path / "mpv"
    library.mkdir()

    with patch("mpv_scraper.utils.validate_prereqs") as mock_validate:
        mock_validate.return_value = {
            "ok": False,
            "ffmpeg_version": None,
            "ffprobe_version": None,
            "warnings": ["ffmpeg not found in PATH", "ffprobe not found in PATH"],
        }

        result = runner.invoke(cli_main, ["init", str(library)])
        assert result.exit_code == 0
        out = result.output.lower()
        assert "warning" in out
        assert "ffmpeg" in out and "ffprobe" in out
