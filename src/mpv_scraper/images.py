"""Image processing utilities.

Sprint 5 handles downloading artwork and ensuring it meets EmulationStation
requirements.  This module currently provides `download_image`, which fetches
an image from a remote URL, converts it to PNG, and stores it at the
specified destination path.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Final

import requests
from PIL import Image

from mpv_scraper.utils import retry_with_backoff

__all__ = [
    "download_image",
    "ensure_png_size",
    "create_placeholder_png",
    "create_movies_folder_image",
    "download_marquee",
]

# PIL recommends using RGBA for universal compatibility.
PNG_MODE: Final[str] = "RGBA"


@retry_with_backoff(
    max_attempts=3, base_delay=1.0, exceptions=(requests.RequestException,)
)
def download_image(url: str, dest: Path, headers: dict = None) -> None:
    """Download an image and save it as PNG.

    The function will create the *parent* directories for *dest* if they do
    not yet exist.

    Parameters
    ----------
    url:
        The remote image URL.
    dest:
        Full destination path, including the desired ``.png`` filename.
    headers:
        Optional HTTP headers for authentication (e.g., for TVDB artwork).

    Raises
    ------
    requests.HTTPError
        If the HTTP request fails (status >= 400).
    PIL.UnidentifiedImageError
        If Pillow cannot decode the downloaded bytes.
    """

    # Ensure destination ends with .png for clarity.
    if dest.suffix.lower() != ".png":
        dest = dest.with_suffix(".png")

    dest.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(url, timeout=15, headers=headers)
    response.raise_for_status()

    # Load the image into Pillow.
    with Image.open(io.BytesIO(response.content)) as img:
        # Convert to a consistent mode for PNG.
        if img.mode != PNG_MODE:
            img = img.convert(PNG_MODE)
        # Save with basic optimization; further compression handled in Sprint 5.2.
        img.save(dest, format="PNG", optimize=True)

    # Confirm write.
    if not dest.exists():
        raise OSError(f"Failed to write image to {dest}")


@retry_with_backoff(
    max_attempts=3, base_delay=1.0, exceptions=(requests.RequestException,)
)
def download_marquee(url: str, dest: Path, headers: dict = None) -> None:
    """Download a logo image suitable for the <marquee> XML tag.

    This is a thin wrapper around :pyfunc:`download_image` that additionally
    enforces the 600&nbsp;KB / 500&nbsp;px limits defined in the project
    constraints.
    """

    # Re-use the core download logic and then ensure constraints.
    download_image(url, dest, headers)
    ensure_png_size(dest)


def ensure_png_size(path: Path, *, max_kb: int = 600, max_width: int = 500) -> None:
    """Ensure the PNG at *path* is under *max_kb* and width <= *max_width*.

    The image is modified **in place** if either the file size or width limit
    is exceeded.  Uses Pillow's ``thumbnail`` to preserve aspect ratio.
    """

    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".png":
        raise ValueError("ensure_png_size only supports .png files")

    current_size_kb = path.stat().st_size / 1024
    with Image.open(path) as img:
        width, height = img.size
        needs_resize = width > max_width
        needs_compress = current_size_kb > max_kb

        if not (needs_resize or needs_compress):
            return  # Already within limits

        # Calculate new dimensions – keep aspect ratio.
        if needs_resize:
            new_width = max_width
            new_height = round(height * (new_width / width))
            img = img.resize((new_width, new_height), Image.LANCZOS)

        # Save optimized PNG (overwrite)
        img.save(path, format="PNG", optimize=True)

    # If still too large, attempt a second pass with higher compression.
    if path.stat().st_size / 1024 > max_kb:
        with Image.open(path) as img:
            # Reduce quality by lowering number of colors (quantize)
            img = img.convert("P", palette=Image.ADAPTIVE, colors=256)
            img.save(path, format="PNG", optimize=True)


def create_placeholder_png(
    dest: Path,
    size: tuple[int, int] = (1, 1),
    color: tuple[int, int, int, int] | str = (255, 255, 255, 0),
) -> None:
    """Create a minimal placeholder PNG.

    This helper is useful for tests where real artwork is mocked. The resulting
    image will always satisfy the ≤600 KB size constraint.
    """

    # Ensure the path has a .png suffix for consistency.
    if dest.suffix.lower() != ".png":
        dest = dest.with_suffix(".png")

    dest.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", size, color)  # type: ignore[arg-type]
    img.save(dest, format="PNG", optimize=True)

    # Final sanity: enforce size limit.
    ensure_png_size(dest)  # guarantee size constraints


def create_movies_folder_image(dest: Path) -> None:
    """Create a movies folder image with a film reel icon.

    This creates a proper movies folder image instead of a placeholder.
    The image will be a film reel icon on a dark background.
    """
    # Ensure the path has a .png suffix for consistency.
    if dest.suffix.lower() != ".png":
        dest = dest.with_suffix(".png")

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Create a 400x300 image with a dark background
    width, height = 400, 300
    img = Image.new("RGBA", (width, height), (20, 20, 20, 255))

    # Draw a simple film reel icon (simplified representation)
    # This is a basic implementation - you could make it more sophisticated
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)

    # Draw a large circle for the film reel
    center_x, center_y = width // 2, height // 2
    radius = 80
    draw.ellipse(
        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
        outline=(255, 255, 255, 255),
        width=3,
    )

    # Draw small circles around the edge (film perforations)
    for i in range(8):
        angle = i * (360 / 8)
        x = center_x + int(radius * 0.8 * (angle / 360) * 2 * 3.14159)
        y = center_y + int(radius * 0.8 * (angle / 360) * 2 * 3.14159)
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(255, 255, 255, 255))

    # Add "MOVIES" text
    try:
        from PIL import ImageFont

        # Try to use a system font, fallback to default if not available
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
        draw.text(
            (center_x - 60, center_y + radius + 20),
            "MOVIES",
            fill=(255, 255, 255, 255),
            font=font,
        )
    except ImportError:
        # If ImageFont is not available, just draw text without font
        draw.text(
            (center_x - 60, center_y + radius + 20), "MOVIES", fill=(255, 255, 255, 255)
        )

    img.save(dest, format="PNG", optimize=True)

    # Ensure size constraints
    ensure_png_size(dest)
