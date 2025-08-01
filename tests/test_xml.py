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
        {
            "path": "Movies",
            "name": "Movies",
            "image": "Movies/images/poster.png",
        },
    ]

    dest = tmp_path / "gamelist.xml"
    write_top_gamelist(folders, dest)

    tree = ET.parse(dest)
    root = tree.getroot()
    folder_tags = root.findall("folder")
    assert len(folder_tags) == 2
    assert folder_tags[0].find("path").text == "./Paw Patrol"
    assert folder_tags[1].find("name").text == "Movies"


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

    tree = ET.parse(dest)
    root = tree.getroot()
    game_el = root.find("game")
    assert game_el is not None
    assert game_el.find("name").text == "Pup Pup Goose & Pup Pup and Away – S01E09-E10"
    assert game_el.find("image").text.startswith("./Paw Patrol")
