import xml.etree.ElementTree as ET
from pathlib import Path
from click.testing import CliRunner

from mpv_scraper.cli import main as cli


def _collect_marquee_tags(xml_path: Path):
    tree = ET.parse(xml_path)
    return [el.text for el in tree.findall(".//marquee")]


def _collect_rating_tags(xml_path: Path):
    tree = ET.parse(xml_path)
    return [el.text for el in tree.findall(".//rating")]


def test_generate_includes_extended_tags(tmp_path: Path, monkeypatch):
    """`generate` should write <marquee> and <rating> tags to gamelists."""

    # Build minimal mock library
    show_dir = tmp_path / "My Show"
    show_dir.mkdir(parents=True)
    (show_dir / "My Show - S01E01 - Pilot.mp4").touch()

    # Run `generate`
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", str(tmp_path)])
    assert result.exit_code == 0, result.output

    # Validate tags in top-level gamelist (our current logic only creates top-level gamelist.xml)
    gamelist = tmp_path / "gamelist.xml"
    assert gamelist.exists()
    marquees = _collect_marquee_tags(gamelist)
    ratings = _collect_rating_tags(gamelist)

    # Our new logic uses different naming conventions
    # Check that marquee tags exist and have valid paths
    assert marquees, "Marquee tags should be present"
    assert marquees[0].startswith("./"), "Marquee paths should be relative"
    assert ratings and ratings[0] == "0.00"  # normalized format


def test_scrape_flags_parsed(tmp_path: Path, monkeypatch):
    from unittest.mock import patch
    from click.testing import CliRunner
    import mpv_scraper.cli as cli_mod

    # Build a tiny library and ensure directories exist
    root = tmp_path / "mpv"
    (root / "Movies").mkdir(parents=True, exist_ok=True)

    with patch("mpv_scraper.scanner.scan_directory") as mock_scan, patch(
        "mpv_scraper.scraper.scrape_tv_parallel"
    ), patch("mpv_scraper.scraper.scrape_movie"):
        mock_scan.return_value = type("R", (), {"shows": [], "movies": []})()

        runner = CliRunner()
        res = runner.invoke(
            cli_mod.main,
            [
                "scrape",
                str(root),
                "--prefer-fallback",
                "--fallback-only",
                "--no-remote",
            ],
        )
        assert res.exit_code == 0, res.output
