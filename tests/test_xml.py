"""Tests for XML generation functionality."""

import pytest
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from mpv_scraper.xml_writer import write_top_gamelist, write_show_gamelist


class TestWriteTopGamelist:
    """Test top-level gamelist.xml generation."""

    def test_write_top_gamelist_creates_valid_xml(self):
        """Test that write_top_gamelist creates well-formed XML."""
        folders = [
            {"path": "./Test Show", "name": "Test Show", "image": "./images/test.png"},
            {"path": "./Movies", "name": "Movies", "image": "./images/movies.png"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "gamelist.xml"
            write_top_gamelist(folders, dest)

            # Verify file exists and is valid XML
            assert dest.exists()
            tree = ET.parse(dest)
            root = tree.getroot()

            # Check structure
            assert root.tag == "gameList"
            assert len(root) == 2

            # Check first folder
            folder1 = root[0]
            assert folder1.tag == "folder"
            assert folder1.find("path").text == "./Test Show"
            assert folder1.find("name").text == "Test Show"
            assert folder1.find("image").text == "./images/test.png"

            # Check second folder
            folder2 = root[1]
            assert folder2.tag == "folder"
            assert folder2.find("path").text == "./Movies"
            assert folder2.find("name").text == "Movies"
            assert folder2.find("image").text == "./images/movies.png"


class TestWriteShowGamelist:
    """Test show/movie gamelist.xml generation."""

    def test_write_show_gamelist_basic_fields(self):
        """Test basic game entry fields."""
        games = [
            {
                "path": "./test.mp4",
                "name": "Test Episode",
                "desc": "A test episode",
                "image": "./images/test.png",
                "rating": 0.8,
                "marquee": "./images/logo.png",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "gamelist.xml"
            write_show_gamelist(games, dest)

            # Verify file exists and is valid XML
            assert dest.exists()
            tree = ET.parse(dest)
            root = tree.getroot()

            # Check structure
            assert root.tag == "gameList"
            assert len(root) == 1

            # Check game entry
            game = root[0]
            assert game.tag == "game"
            assert game.find("path").text == "./test.mp4"
            assert game.find("name").text == "Test Episode"
            assert game.find("desc").text == "A test episode"
            assert game.find("image").text == "./images/test.png"
            assert game.find("rating").text == "0.80"
            assert game.find("marquee").text == "./images/logo.png"

    def test_write_show_gamelist_extended_metadata(self):
        """Test extended metadata fields for TV shows and movies."""
        games = [
            {
                "path": "./episode.mp4",
                "name": "Test Episode",
                "desc": "A test episode",
                "image": "./images/episode.png",
                "rating": 0.75,
                "marquee": "./images/logo.png",
                "releasedate": "20230115T000000",
                "genre": "Action, Adventure",
                "developer": "Test Network",
                "publisher": "Test Studio",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "gamelist.xml"
            write_show_gamelist(games, dest)

            # Verify file exists and is valid XML
            assert dest.exists()
            tree = ET.parse(dest)
            root = tree.getroot()

            # Check game entry
            game = root[0]
            assert game.find("releasedate").text == "20230115T000000"
            assert game.find("genre").text == "Action, Adventure"
            assert game.find("developer").text == "Test Network"
            assert game.find("publisher").text == "Test Studio"

    def test_write_show_gamelist_optional_fields(self):
        """Test that optional fields are only included when present."""
        games = [
            {
                "path": "./episode.mp4",
                "name": "Test Episode",
                # No optional fields
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "gamelist.xml"
            write_show_gamelist(games, dest)

            tree = ET.parse(dest)
            root = tree.getroot()
            game = root[0]

            # Required fields should be present
            assert game.find("path") is not None
            assert game.find("name") is not None

            # Optional fields should not be present
            assert game.find("desc") is None
            assert game.find("image") is None
            assert game.find("rating") is None
            assert game.find("marquee") is None
            assert game.find("releasedate") is None
            assert game.find("genre") is None
            assert game.find("developer") is None
            assert game.find("publisher") is None

    def test_write_show_gamelist_rating_validation(self):
        """Test that rating validation works correctly."""
        games = [
            {
                "path": "./episode.mp4",
                "name": "Test Episode",
                "rating": 1.5,  # Invalid rating > 1.0
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "gamelist.xml"

            with pytest.raises(ValueError, match="rating must be between 0 and 1"):
                write_show_gamelist(games, dest)

    def test_write_show_gamelist_relative_paths(self):
        """Test that paths are properly converted to relative format."""
        games = [
            {
                "path": "test.mp4",  # No ./ prefix
                "name": "Test Episode",
                "image": "images/test.png",  # No ./ prefix
                "marquee": "images/logo.png",  # No ./ prefix
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "gamelist.xml"
            write_show_gamelist(games, dest)

            tree = ET.parse(dest)
            root = tree.getroot()
            game = root[0]

            # Paths should have ./ prefix
            assert game.find("path").text == "./test.mp4"
            assert game.find("image").text == "./images/test.png"
            assert game.find("marquee").text == "./images/logo.png"
