"""Utilities to generate EmulationStation-compatible ``gamelist.xml`` files.

This module focuses on *writing* XML documents that list folders (TV shows,
Movies) or playable items (episodes, movies).  Paths written to the XML are
always *relative* and images are expected to live alongside the generated
XML (per project conventions).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any
import xml.etree.ElementTree as ET

__all__ = ["write_top_gamelist", "write_show_gamelist"]


def _ensure_relative(path: Path | str) -> str:
    path_str = str(path)
    if not path_str.startswith("./"):
        path_str = f"./{path_str.lstrip('./')}"
    return path_str


def _write_xml_with_pretty_print(element: ET.Element, dest: Path) -> None:
    """Write XML with proper formatting and encoding."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Create a pretty-printed XML string
    rough_string = ET.tostring(element, encoding="unicode")

    # Parse it back to get pretty formatting
    reparsed = ET.fromstring(rough_string)

    # Write with proper XML declaration and encoding
    with open(dest, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        # Write the element with proper formatting
        ET.indent(reparsed, space="  ")  # Add indentation
        f.write(ET.tostring(reparsed, encoding="unicode"))


def write_top_gamelist(folders: List[Dict[str, Any]], dest: Path) -> None:
    """Write the top-level ``gamelist.xml``.

    Parameters
    ----------
    folders
        List of dicts with keys ``path``, ``name``, ``image``.
    dest
        File path where the XML will be written.
    """

    root = ET.Element("gameList")

    for folder in folders:
        folder_el = ET.SubElement(root, "folder")
        ET.SubElement(folder_el, "path").text = _ensure_relative(folder["path"])
        ET.SubElement(folder_el, "name").text = folder["name"]
        if folder.get("image"):
            ET.SubElement(folder_el, "image").text = _ensure_relative(folder["image"])

    _write_xml_with_pretty_print(root, dest)


def write_show_gamelist(games: List[Dict[str, Any]], dest: Path) -> None:
    """Write ``gamelist.xml`` for a specific show or Movies folder.

    Each *game* dict supports:
    - ``path`` (str): Path to the media file
    - ``name`` (str): Display name
    - ``desc`` (str): Description (optional)
    - ``image`` (str): Path to poster image (optional)
    - ``rating`` (float): Rating 0.0-1.0 (optional)
    - ``marquee`` (str): Path to logo image (optional)
    - ``releasedate`` (str): Release date in YYYYMMDDT000000 format (optional)
    - ``developer`` (str): Production company/Network (optional)
    - ``publisher`` (str): Distributor/Studio (optional)
    - ``genre`` (str): Genre (optional)
    - ``video`` (str): Path to video preview/trailer (optional)
    - ``thumbnail`` (str): Path to thumbnail image (optional)
    - ``fanart`` (str): Path to fan art (optional)
    - ``titleshot`` (str): Path to title shot (optional)
    - ``lang`` (str): Language code (optional)
    - ``region`` (str): Region code (optional)
    - ``favorite`` (bool): Favorite status (optional)
    - ``hidden`` (bool): Hidden status (optional)
    """

    root = ET.Element("gameList")

    for game in games:
        game_el = ET.SubElement(root, "game")
        ET.SubElement(game_el, "path").text = _ensure_relative(game["path"])
        ET.SubElement(game_el, "name").text = game["name"]

        # Core metadata fields
        if game.get("desc"):
            ET.SubElement(game_el, "desc").text = game["desc"]
        if game.get("image"):
            ET.SubElement(game_el, "image").text = _ensure_relative(game["image"])
        if game.get("rating") is not None:
            rating_val = float(game["rating"])
            if not 0.0 <= rating_val <= 1.0:
                raise ValueError("rating must be between 0 and 1")
            ET.SubElement(game_el, "rating").text = f"{rating_val:.2f}"
        if game.get("marquee"):
            ET.SubElement(game_el, "marquee").text = _ensure_relative(game["marquee"])
        if game.get("box"):
            ET.SubElement(game_el, "box").text = _ensure_relative(game["box"])
        if game.get("releasedate"):
            ET.SubElement(game_el, "releasedate").text = game["releasedate"]
        if game.get("developer"):
            ET.SubElement(game_el, "developer").text = game["developer"]
        if game.get("publisher"):
            ET.SubElement(game_el, "publisher").text = game["publisher"]
        if game.get("genre"):
            ET.SubElement(game_el, "genre").text = game["genre"]

        # Additional EmulationStation fields
        if game.get("video"):
            ET.SubElement(game_el, "video").text = _ensure_relative(game["video"])
        if game.get("thumbnail"):
            ET.SubElement(game_el, "thumbnail").text = _ensure_relative(
                game["thumbnail"]
            )
        if game.get("fanart"):
            ET.SubElement(game_el, "fanart").text = _ensure_relative(game["fanart"])
        if game.get("titleshot"):
            ET.SubElement(game_el, "titleshot").text = _ensure_relative(
                game["titleshot"]
            )
        if game.get("lang"):
            ET.SubElement(game_el, "lang").text = game["lang"]
        if game.get("region"):
            ET.SubElement(game_el, "region").text = game["region"]
        if game.get("favorite") is not None:
            ET.SubElement(game_el, "favorite").text = str(game["favorite"]).lower()
        if game.get("hidden") is not None:
            ET.SubElement(game_el, "hidden").text = str(game["hidden"]).lower()

    _write_xml_with_pretty_print(root, dest)
