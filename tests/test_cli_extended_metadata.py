"""Test CLI extended metadata functionality."""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from mpv_scraper.cli import main
from click.testing import CliRunner


class TestGenerateExtendedMetadata:
    """Test that generate command includes extended metadata fields."""

    def test_generate_includes_extended_metadata(self):
        """Test that generate command includes all extended metadata fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a mock show directory structure
            show_dir = temp_path / "Test Show"
            show_dir.mkdir()

            # Create a mock episode file
            episode_file = show_dir / "Test Show - S01E01 - Pilot.mp4"
            episode_file.touch()

            # Create mock scrape cache with extended metadata
            cache_data = {
                "id": 12345,
                "name": "Test Show",
                "overview": "A test show",
                "siteRating": 0.8,
                "image": "https://example.com/poster.jpg",
                "artworks": {"clearLogo": "https://example.com/logo.png"},
                "genre": ["Action", "Adventure"],
                "network": {"name": "Test Network"},
                "studio": [{"name": "Test Studio"}],
                "episodes": [
                    {
                        "seasonNumber": 1,
                        "number": 1,
                        "overview": "A pilot episode",
                        "firstAired": "2023-01-15",
                        "siteRating": 0.75,
                        "episodeName": "Pilot",
                    }
                ],
            }

            # Write mock cache file
            cache_file = show_dir / ".scrape_cache.json"
            import json

            cache_file.write_text(json.dumps(cache_data))

            # Create images directory and placeholder images
            images_dir = show_dir / "images"
            images_dir.mkdir()
            (images_dir / "poster.png").touch()
            (images_dir / "logo.png").touch()
            (images_dir / "S01E01.png").touch()

            # Mock the scan_directory function to return our test data
            with patch("mpv_scraper.scanner.scan_directory") as mock_scan:
                from mpv_scraper.scanner import ScanResult, ShowDirectory

                mock_scan.return_value = ScanResult(
                    shows=[ShowDirectory(path=show_dir, files=[episode_file])],
                    movies=[],
                )

                # Run generate command using Click test runner
                runner = CliRunner()
                result = runner.invoke(main, ["generate", str(temp_path)])
                assert result.exit_code == 0, f"Command failed: {result.output}"

            # Check that gamelist.xml was created
            gamelist_path = show_dir / "gamelist.xml"
            assert gamelist_path.exists()

            # Parse and verify XML content
            tree = ET.parse(gamelist_path)
            root = tree.getroot()

            # Check that we have a game entry
            assert root.tag == "gameList"
            assert len(root) == 1

            game = root[0]
            assert game.tag == "game"

            # Check basic fields
            assert (
                game.find("path").text == "./Test Show/Test Show - S01E01 - Pilot.mp4"
            )
            assert game.find("name").text == "Pilot – S01E01"
            assert game.find("desc").text == "A pilot episode"
            assert game.find("image").text == "./images/S01E01.png"
            assert game.find("rating").text == "0.75"
            assert game.find("marquee").text == "./images/logo.png"

            # Check extended metadata fields
            assert game.find("releasedate").text == "20230115T000000"
            assert game.find("genre").text == "Action, Adventure"
            assert game.find("developer").text == "Test Network"
            assert game.find("publisher").text == "Test Studio"

    def test_generate_movie_extended_metadata(self):
        """Test that generate command includes extended metadata for movies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create Movies directory
            movies_dir = temp_path / "Movies"
            movies_dir.mkdir()

            # Create a mock movie file
            movie_file = movies_dir / "Test Movie (2023).mp4"
            movie_file.touch()

            # Create mock scrape cache with extended metadata
            cache_data = {
                "id": 67890,
                "title": "Test Movie",
                "overview": "A test movie",
                "vote_average": 0.85,
                "release_date": "2023-06-15",
                "genre_names": ["Action", "Sci-Fi"],
                "production_company_names": ["Test Productions"],
                "distributor": "Test Distributor",
            }

            # Write mock cache file
            cache_file = movies_dir / ".scrape_cache.json"
            import json

            cache_file.write_text(json.dumps(cache_data))

            # Create images directory and placeholder images
            images_dir = movies_dir / "images"
            images_dir.mkdir()
            (images_dir / "Test Movie (2023).png").touch()
            (images_dir / "Test Movie (2023)-logo.png").touch()

            # Mock the scan_directory function to return our test data
            with patch("mpv_scraper.scanner.scan_directory") as mock_scan:
                from mpv_scraper.scanner import ScanResult, MovieFile

                mock_scan.return_value = ScanResult(
                    shows=[], movies=[MovieFile(path=movie_file)]
                )

                # Run generate command using Click test runner
                runner = CliRunner()
                result = runner.invoke(main, ["generate", str(temp_path)])
                assert result.exit_code == 0, f"Command failed: {result.output}"

            # Check that gamelist.xml was created
            gamelist_path = movies_dir / "gamelist.xml"
            assert gamelist_path.exists()

            # Parse and verify XML content
            tree = ET.parse(gamelist_path)
            root = tree.getroot()

            # Check that we have a game entry
            assert root.tag == "gameList"
            assert len(root) == 1

            game = root[0]
            assert game.tag == "game"

            # Check basic fields
            assert game.find("path").text == "./Movies/Test Movie (2023).mp4"
            assert game.find("name").text == "Test Movie"
            assert game.find("desc").text == "A test movie"
            assert game.find("image").text == "./images/Test Movie (2023).png"
            assert game.find("rating").text == "0.85"
            assert game.find("marquee").text == "./images/Test Movie (2023)-logo.png"

            # Check extended metadata fields
            assert game.find("releasedate").text == "20230615T000000"
            assert game.find("genre").text == "Action, Sci-Fi"
            assert game.find("developer").text == "Test Productions"
            assert game.find("publisher").text == "Test Distributor"
