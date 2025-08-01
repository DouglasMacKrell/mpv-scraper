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

__all__ = ["download_image", "ensure_png_size"]

# PIL recommends using RGBA for universal compatibility.
PNG_MODE: Final[str] = "RGBA"


def download_image(url: str, dest: Path) -> None:
    """Download an image and save it as PNG.

    The function will create the *parent* directories for *dest* if they do
    not yet exist.

    Parameters
    ----------
    url:
        The remote image URL.
    dest:
        Full destination path, including the desired ``.png`` filename.

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

    response = requests.get(url, timeout=15)
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
