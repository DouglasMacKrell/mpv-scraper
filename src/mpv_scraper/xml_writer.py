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

    tree = ET.ElementTree(root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tree.write(dest, encoding="utf-8", xml_declaration=True)


def write_show_gamelist(games: List[Dict[str, Any]], dest: Path) -> None:
    """Write ``gamelist.xml`` for a specific show or Movies folder.

    Each *game* dict supports ``path`` (str), ``name`` (str), ``desc`` (str),
    and ``image`` (str).  Desc and image are optional but recommended.
    """

    root = ET.Element("gameList")

    for game in games:
        game_el = ET.SubElement(root, "game")
        ET.SubElement(game_el, "path").text = _ensure_relative(game["path"])
        ET.SubElement(game_el, "name").text = game["name"]
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

    tree = ET.ElementTree(root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tree.write(dest, encoding="utf-8", xml_declaration=True)
