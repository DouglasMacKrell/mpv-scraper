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

    # Validate tags in show gamelist
    gamelist = show_dir / "gamelist.xml"
    assert gamelist.exists()
    marquees = _collect_marquee_tags(gamelist)
    ratings = _collect_rating_tags(gamelist)
    assert marquees and marquees[0].endswith("marquee.png")
    assert ratings and ratings[0] == "0.00"  # normalized format
