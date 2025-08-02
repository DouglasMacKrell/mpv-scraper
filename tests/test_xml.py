from pathlib import Path
import xml.etree.ElementTree as ET

from mpv_scraper.xml_writer import write_top_gamelist, write_show_gamelist


def test_write_top_gamelist(tmp_path: Path):
    folders = [
        {
            "path": "Paw Patrol",
            "name": "Paw Patrol",
            "image": "Paw Patrol/images/poster.png",
        },
        {"path": "Movies", "name": "Movies", "image": "Movies/images/poster.png"},
    ]
    dest = tmp_path / "gamelist.xml"
    write_top_gamelist(folders, dest)
    root = ET.parse(dest).getroot()
    assert len(root.findall("folder")) == 2


def test_write_show_gamelist_with_span(tmp_path: Path):
    games = [
        {
            "path": "./Paw Patrol - S01E09-E10 - Pup Pup Goose & Pup Pup and Away.mp4",
            "name": "Pup Pup Goose & Pup Pup and Away – S01E09-E10",
            "desc": "Sample description",
            "image": "Paw Patrol/images/S01E09.png",
        }
    ]
    dest = tmp_path / "Paw Patrol" / "gamelist.xml"
    write_show_gamelist(games, dest)
    game_el = ET.parse(dest).getroot().find("game")
    assert game_el.find("desc").text == "Sample description"


def test_write_game_extended_tags(tmp_path: Path):
    games = [
        {
            "path": "./Movies/Sample.mp4",
            "name": "Sample Movie",
            "rating": 0.85,
            "marquee": "Movies/images/marquee.png",
        }
    ]
    dest = tmp_path / "Movies" / "gamelist.xml"
    write_show_gamelist(games, dest)
    game_el = ET.parse(dest).getroot().find("game")
    assert game_el.find("rating").text == "0.85"
    assert game_el.find("marquee").text.startswith("./Movies")
