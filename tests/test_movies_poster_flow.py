"""Test the movies poster flow functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner

from mpv_scraper.cli import main


class TestMoviesPosterFlow:
    """Test that the movies poster flow works correctly."""

    def test_movies_poster_copy_to_top_level(self):
        """Test that movies-poster.jpg is copied to top-level images directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create the public/images directory structure
            public_images_dir = temp_path / "public" / "images"
            public_images_dir.mkdir(parents=True, exist_ok=True)

            # Create a mock movies-poster.jpg file
            movies_poster_source = public_images_dir / "movies-poster.jpg"
            movies_poster_source.write_bytes(b"mock jpeg data")

            # Create Movies directory
            movies_dir = temp_path / "Movies"
            movies_dir.mkdir()

            # Create a mock movie file
            movie_file = movies_dir / "Test Movie (2023).mp4"
            movie_file.touch()

            # Mock the scan_directory function
            with patch("mpv_scraper.scanner.scan_directory") as mock_scan:
                from mpv_scraper.scanner import ScanResult, MovieFile

                mock_scan.return_value = ScanResult(
                    shows=[], movies=[MovieFile(path=movie_file)]
                )

                # Run generate command
                runner = CliRunner()
                result = runner.invoke(main, ["generate", str(temp_path)])
                assert result.exit_code == 0, f"Command failed: {result.output}"

            # Check that movies-poster.jpg was copied to top-level images directory
            top_images_dir = temp_path / "images"
            top_movies_poster = top_images_dir / "movies-poster.jpg"
            assert (
                top_movies_poster.exists()
            ), "movies-poster.jpg should be copied to top-level images"

            # Check that the content was actually copied (not just a placeholder)
            assert top_movies_poster.read_bytes() == b"mock jpeg data"

            # Check that it was also copied to Movies/images/poster.png
            movies_images_dir = movies_dir / "images"
            movies_poster_dest = movies_images_dir / "poster.png"
            assert (
                movies_poster_dest.exists()
            ), "movies-poster.jpg should be copied to Movies/images/poster.png"

            # Check that the top-level gamelist.xml references the correct image
            top_gamelist_path = temp_path / "gamelist.xml"
            assert top_gamelist_path.exists()

            import xml.etree.ElementTree as ET

            tree = ET.parse(top_gamelist_path)
            root = tree.getroot()

            # Find the Movies folder entry
            movies_folder = None
            for folder in root.findall("folder"):
                if folder.find("path").text == "./Movies":
                    movies_folder = folder
                    break

            assert (
                movies_folder is not None
            ), "Movies folder entry should exist in top-level gamelist"
            assert (
                movies_folder.find("image").text == "./images/movies-poster.jpg"
            ), "Movies folder should reference the top-level movies-poster.jpg"

    def test_movies_poster_fallback_to_custom_image(self):
        """Test that when movies-poster.jpg doesn't exist, it falls back to creating a custom image."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create Movies directory (but no public/images/movies-poster.jpg)
            movies_dir = temp_path / "Movies"
            movies_dir.mkdir()

            # Create a mock movie file
            movie_file = movies_dir / "Test Movie (2023).mp4"
            movie_file.touch()

            # Mock the scan_directory function
            with patch("mpv_scraper.scanner.scan_directory") as mock_scan:
                from mpv_scraper.scanner import ScanResult, MovieFile

                mock_scan.return_value = ScanResult(
                    shows=[], movies=[MovieFile(path=movie_file)]
                )

                # Run generate command
                runner = CliRunner()
                result = runner.invoke(main, ["generate", str(temp_path)])
                assert result.exit_code == 0, f"Command failed: {result.output}"

            # Check that a custom poster was created in Movies/images
            movies_images_dir = movies_dir / "images"
            custom_poster = movies_images_dir / "poster.png"
            assert (
                custom_poster.exists()
            ), "Custom poster should be created when movies-poster.jpg doesn't exist"

            # Check that the top-level gamelist.xml references the custom image
            top_gamelist_path = temp_path / "gamelist.xml"
            assert top_gamelist_path.exists()

            import xml.etree.ElementTree as ET

            tree = ET.parse(top_gamelist_path)
            root = tree.getroot()

            # Find the Movies folder entry
            movies_folder = None
            for folder in root.findall("folder"):
                if folder.find("path").text == "./Movies":
                    movies_folder = folder
                    break

            assert (
                movies_folder is not None
            ), "Movies folder entry should exist in top-level gamelist"
            assert (
                movies_folder.find("image").text == "./Movies/images/poster.png"
            ), "Movies folder should reference the custom poster when movies-poster.jpg doesn't exist"

    def test_movies_poster_transaction_logging(self):
        """Test that the movies poster copy operations are logged in the transaction log."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create the public/images directory structure
            public_images_dir = temp_path / "public" / "images"
            public_images_dir.mkdir(parents=True, exist_ok=True)

            # Create a mock movies-poster.jpg file
            movies_poster_source = public_images_dir / "movies-poster.jpg"
            movies_poster_source.write_bytes(b"mock jpeg data")

            # Create Movies directory
            movies_dir = temp_path / "Movies"
            movies_dir.mkdir()

            # Create a mock movie file
            movie_file = movies_dir / "Test Movie (2023).mp4"
            movie_file.touch()

            # Mock the scan_directory function
            with patch("mpv_scraper.scanner.scan_directory") as mock_scan:
                from mpv_scraper.scanner import ScanResult, MovieFile

                mock_scan.return_value = ScanResult(
                    shows=[], movies=[MovieFile(path=movie_file)]
                )

                # Run generate command
                runner = CliRunner()
                result = runner.invoke(main, ["generate", str(temp_path)])
                assert result.exit_code == 0, f"Command failed: {result.output}"

            # Check that transaction.log was created and contains the poster copy operations
            transaction_log = temp_path / "transaction.log"
            assert transaction_log.exists(), "Transaction log should be created"

            log_content = transaction_log.read_text()
            assert (
                "movies-poster.jpg" in log_content
            ), "Transaction log should contain movies-poster.jpg operations"
            assert (
                "create" in log_content
            ), "Transaction log should contain create operations"
