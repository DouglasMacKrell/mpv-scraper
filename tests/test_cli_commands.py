from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from mpv_scraper.cli import main as cli_main


@patch("mpv_scraper.cli.scan")
@patch("mpv_scraper.cli.generate")
def test_run_combined_workflow(mock_generate, mock_scan, tmp_path: Path):
    runner = CliRunner()

    # Provide a temporary directory as the media path
    result = runner.invoke(cli_main, ["run", str(tmp_path)])

    assert result.exit_code == 0
    # The scan and generate commands should be invoked once each.
    mock_scan.assert_called_once_with(path=str(tmp_path))
    mock_generate.assert_called_once_with(path=str(tmp_path))
