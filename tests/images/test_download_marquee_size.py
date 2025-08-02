import io
import random
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image

from mpv_scraper.images import download_marquee


@patch("requests.get")
def test_size_enforcement(mock_get, tmp_path: Path):
    """download_marquee must resize/compress large images to project limits."""

    # Build a noisy 800×800 RGBA PNG (>500 px) so size will exceed 600 KB.
    width = height = 800
    img = Image.new("RGBA", (width, height))
    pixels = [
        (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            255,
        )
        for _ in range(width * height)
    ]
    img.putdata(pixels)

    buff = io.BytesIO()
    img.save(buff, format="PNG")

    response = MagicMock()
    response.status_code = 200
    response.content = buff.getvalue()
    mock_get.return_value = response

    dest = tmp_path / "logo.png"
    download_marquee("https://example.com/logo.png", dest)

    # Assertions — output file exists, width ≤ 500, size ≤ 600 KB
    assert dest.exists()
    with Image.open(dest) as out_img:
        assert out_img.width <= 500
    assert dest.stat().st_size / 1024 <= 600

    mock_get.assert_called_once()
