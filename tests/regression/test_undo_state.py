from pathlib import Path
import shutil

from click.testing import CliRunner

from mpv_scraper.cli import main as cli_main
from mpv_scraper.images import create_placeholder_png


def _snapshot_dir(path: Path):
    """Return a sorted list of (relative_path, bytes_or_None) for files/dirs."""
    entries = []
    for p in sorted(path.rglob("*")):
        rel = p.relative_to(path)
        if p.is_file():
            entries.append((str(rel), p.read_bytes()))
        else:
            entries.append((str(rel), None))
    return entries


def test_run_then_undo_restores_checksum(tmp_path: Path, monkeypatch):
    """End-to-end regression: run ➜ undo restores the filesystem exactly."""

    # 1. Copy mock media library to a temp location
    project_root = Path(__file__).resolve().parents[2]
    src_library = project_root / "mocks" / "mpv"
    dst_library = tmp_path / "mpv"

    if src_library.exists():
        shutil.copytree(src_library, dst_library)
    else:
        # Fallback: create a minimal mock library so CI does not fail when mocks are absent.
        show_dir = dst_library / "Sample Show"
        show_dir.mkdir(parents=True, exist_ok=True)
        (show_dir / "S01E01 - Pilot.mp4").write_text("dummy")
        movies_dir = dst_library / "Movies"
        movies_dir.mkdir(parents=True, exist_ok=True)
        (movies_dir / "Sample Movie (2024).mp4").write_text("dummy")

    # 2. Capture initial directory snapshot
    before = _snapshot_dir(dst_library)

    # 3. Ensure placeholder PNGs are actually created during generate()
    monkeypatch.setattr(
        "mpv_scraper.cli.create_placeholder_png", create_placeholder_png
    )

    runner = CliRunner()

    # 4. Run the full workflow
    result_run = runner.invoke(cli_main, ["run", str(dst_library)])
    assert result_run.exit_code == 0, result_run.output
    assert (dst_library / "transaction.log").exists()

    # 5. Undo inside the library directory
    # Change working directory to the library root before undo
    monkeypatch.chdir(dst_library)
    result_undo = runner.invoke(cli_main, ["undo"])
    assert result_undo.exit_code == 0, result_undo.output
    assert not (dst_library / "transaction.log").exists()

    # 6. Verify directory is identical to the original snapshot
    after = _snapshot_dir(dst_library)
    assert before == after
