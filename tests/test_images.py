import io
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image

from mpv_scraper.images import download_image


def _fake_jpeg_bytes(color=(255, 0, 0)) -> bytes:
    """Generate an in-memory JPEG image and return its bytes."""
    file_obj = io.BytesIO()
    img = Image.new("RGB", (10, 10), color=color)
    img.save(file_obj, format="JPEG")
    return file_obj.getvalue()


@patch("requests.get")
def test_download_and_convert_png(mock_get, tmp_path: Path, monkeypatch):
    """download_image should fetch remote image and save a PNG file."""

    # Arrange: mock HTTP response
    response = MagicMock()
    response.status_code = 200
    response.content = _fake_jpeg_bytes()
    mock_get.return_value = response

    dest = tmp_path / "test_art.png"

    # Act
    download_image("https://example.com/test.jpg", dest)

    # Assert
    assert dest.exists(), "PNG file should be created"

    # Verify the file is a valid PNG
    with Image.open(dest) as img:
        assert img.format == "PNG"
        assert img.size == (10, 10)

    mock_get.assert_called_once_with("https://example.com/test.jpg", timeout=15)
