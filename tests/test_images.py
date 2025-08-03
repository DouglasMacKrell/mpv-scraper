import io
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image
import random
from mpv_scraper.images import ensure_png_size

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

    mock_get.assert_called_once_with(
        "https://example.com/test.jpg", timeout=15, headers=None
    )


def test_resize_under_threshold(tmp_path: Path):
    """ensure_png_size should downscale images over width or size limit."""

    # Create a large noisy image (>500 px wide) to exceed size threshold.
    width, height = 1200, 1200
    img = Image.new("RGB", (width, height))

    # Fill with random noise to avoid heavy PNG compression on solid color.
    pixels = [
        (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        for _ in range(width * height)
    ]
    img.putdata(pixels)

    dest = tmp_path / "large.png"
    img.save(dest, format="PNG", optimize=False)

    # Sanity check: width > 500 and size likely > 600 KB
    orig_size_kb = dest.stat().st_size / 1024
    assert img.width > 500
    assert orig_size_kb > 100  # at least something sizeable

    # Act
    ensure_png_size(dest, max_kb=600, max_width=500)

    # Assert width <= 500 and size <= 600 KB
    with Image.open(dest) as resized:
        assert resized.width <= 500
    assert dest.stat().st_size / 1024 <= 600


@patch("requests.get")
def test_download_marquee_png(mock_get, tmp_path: Path):
    """download_marquee should save a PNG and enforce <600 KB size."""

    from mpv_scraper.images import download_marquee

    # Build a tiny RGBA PNG in-memory
    file_obj = io.BytesIO()
    Image.new("RGBA", (32, 32), (0, 0, 0, 0)).save(file_obj, format="PNG")

    response = MagicMock()
    response.status_code = 200
    response.content = file_obj.getvalue()
    mock_get.return_value = response

    dest = tmp_path / "logo.png"
    download_marquee("https://example.com/logo.png", dest)

    # Assert PNG exists and is under limit
    assert dest.exists()
    assert dest.stat().st_size / 1024 <= 600
    with Image.open(dest) as img:
        assert img.format == "PNG"

    mock_get.assert_called_once()
