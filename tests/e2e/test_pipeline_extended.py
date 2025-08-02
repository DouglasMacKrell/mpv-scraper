"""Extended end-to-end test (Sprint 9.5.1.2).

Builds a multi-season mock library with an anthology span file, runs the full
`cli.run` workflow, and validates:
  • gamelist XMLs are generated & well-formed
  • <marquee> and normalised <rating> tags exist
  • images referred in XML exist and satisfy size limits
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from click.testing import CliRunner

import mpv_scraper.cli as cli
import sys

# Ensure utils_images importable when running via "pytest -m e2e"
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils_images import create_placeholder_png  # noqa: E402

cli.create_placeholder_png = create_placeholder_png  # inject test helper

cli_main = cli.main


@pytest.mark.integration
def test_full_pipeline_multi_season():
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "mpv"
        # --- build library ---------------------------------------------------
        show = root / "Mega Show"
        show.mkdir(parents=True, exist_ok=True)
        # Season 1 single ep
        (show / "Mega Show - S01E01 - The Beginning.mp4").touch()
        # Season 1 anthology span
        (show / "Mega Show - S01E02-E03 - Part A & Part B.mp4").touch()
        # Season 2 ep
        (show / "Mega Show - S02E05 - The Return.mp4").touch()

        # Movies folder with one film
        movies = root / "Movies"
        movies.mkdir(parents=True)
        (movies / "Epic Film (2020).mp4").touch()

        # Execute workflow
        result = runner.invoke(cli_main, ["run", str(root)])
        assert result.exit_code == 0, result.output

        # Helper: walk XML files
        xml_files = list(root.rglob("gamelist.xml"))
        assert xml_files, "No gamelist.xml files generated"

        # Validate each XML
        for xml_path in xml_files:
            tree = ET.parse(xml_path)
            # validate marquee + rating presence if <game> elements exist
            games = tree.findall(".//game")
            if games:
                marquee_tags = tree.findall(".//marquee")
                rating_tags = tree.findall(".//rating")
                assert marquee_tags, f"Missing <marquee> in {xml_path}"
                assert rating_tags, f"Missing <rating> in {xml_path}"
                # rating values should be 0.00 format
                for r_elt in rating_tags:
                    val = float(r_elt.text or 0.0)
                    assert 0.0 <= val <= 1.0
            # check images exist & size
            for img_elt in tree.findall(".//image") + tree.findall(".//marquee"):
                rel = img_elt.text or ""
                abs_path = (xml_path.parent / rel).resolve()
                assert abs_path.exists(), f"Image missing: {abs_path}"
                assert abs_path.stat().st_size / 1024 <= 600
