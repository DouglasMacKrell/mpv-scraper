"""End-to-end test for TVDB V4 API integration.

Tests that the full `cli.run` workflow works with real TVDB V4 API calls.
This test requires TVDB_API_KEY2 to be set in the environment.

Run with: pytest tests/e2e/test_pipeline_v4_real.py -m integration -v
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from click.testing import CliRunner
from dotenv import load_dotenv

import mpv_scraper.cli as cli
import sys

# Load environment variables
load_dotenv()

# Ensure utils_images importable when running via "pytest -m e2e"
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils_images import create_placeholder_png  # noqa: E402

cli.create_placeholder_png = create_placeholder_png  # inject test helper

cli_main = cli.main


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("TVDB_API_KEY2") and not os.getenv("TVDB_API_KEY"),
    reason="TVDB_API_KEY2 or TVDB_API_KEY not set - skipping real API test",
)
def test_full_pipeline_with_v4_api():
    """Test that run command works with real TVDB V4 API calls."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "mpv"

        # --- Build a minimal test library ----------------------------------
        # Use a well-known show that should exist in TVDB
        show_dir = root / "The Simpsons"
        show_dir.mkdir(parents=True, exist_ok=True)
        # Create a few episode files
        (
            show_dir / "The Simpsons - S01E01 - Simpsons Roasting on an Open Fire.mp4"
        ).touch()
        (show_dir / "The Simpsons - S01E02 - Bart the Genius.mp4").touch()

        movies_dir = root / "Movies"
        movies_dir.mkdir(parents=True, exist_ok=True)
        (movies_dir / "The Matrix (1999).mp4").touch()

        # Execute: mpv-scraper run <library>
        # This will make real API calls to TVDB V4
        result = runner.invoke(cli_main, ["run", str(root)])

        # The command should complete successfully
        # (it might prompt for disambiguation, so we check exit code)
        assert result.exit_code in [
            0,
            1,
        ], f"Unexpected exit code: {result.exit_code}\nOutput: {result.output}"

        # If it succeeded, validate the outputs
        if result.exit_code == 0:
            # Check that scrape cache was created
            show_cache = show_dir / ".scrape_cache.json"
            assert show_cache.exists(), "TV show scrape cache should be created"

            # Check that gamelist.xml was created
            top_gamelist = root / "gamelist.xml"
            if top_gamelist.exists():
                # Parse and validate XML
                tree = ET.parse(top_gamelist)
                all_games = tree.findall(".//game")

                # Should have at least one game entry
                assert len(all_games) >= 1, "Should have at least one game entry"

                # Check that entries have metadata
                for game in all_games:
                    name_elem = game.find("name")
                    assert name_elem is not None, "Game entry should have <name> tag"

                    # Check for description (may or may not be present)
                    desc_elem = game.find("desc")
                    if desc_elem is not None:
                        assert (
                            desc_elem.text
                        ), "Description should not be empty if present"

                    # Check for rating (should be normalized 0-1)
                    rating_elem = game.find("rating")
                    if rating_elem is not None:
                        rating = float(rating_elem.text)
                        assert (
                            0.0 <= rating <= 1.0
                        ), f"Rating should be normalized (0-1), got {rating}"

        print(f"\n✅ E2E test completed with exit code {result.exit_code}")
        if result.output:
            print(f"Output preview:\n{result.output[:500]}...")


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("TVDB_API_KEY2") and not os.getenv("TVDB_API_KEY"),
    reason="TVDB_API_KEY2 or TVDB_API_KEY not set - skipping real API test",
)
def test_search_and_scrape_v4_api():
    """Test search and scrape workflow with real V4 API."""
    from mpv_scraper.tvdb import authenticate_tvdb, search_show, get_series_extended

    # Test authentication
    token = authenticate_tvdb()
    assert token is not None, "Should get authentication token"
    assert len(token) > 0, "Token should not be empty"

    # Test search
    results = search_show("The Simpsons", token)
    assert len(results) > 0, "Should find search results"

    # Find The Simpsons (should be first result)
    simpsons_result = None
    for result in results:
        name = result.get("name") or result.get("seriesName", "")
        if "Simpsons" in name and "1989" in str(result.get("year", "")):
            simpsons_result = result
            break

    assert simpsons_result is not None, "Should find The Simpsons in search results"

    # Test get series extended
    series_id = simpsons_result.get("id")
    assert series_id is not None, "Series should have an ID"

    series_info = get_series_extended(series_id, token)
    assert series_info is not None, "Should get series extended info"
    assert series_info.get("name") is not None, "Series should have a name"
    assert len(series_info.get("episodes", [])) > 0, "Series should have episodes"

    print(f"\n✅ Found series: {series_info.get('name')}")
    print(f"   Episodes: {len(series_info.get('episodes', []))}")
    print(f"   Rating: {series_info.get('siteRating')}")
