"""Test utilities for image generation.

Contains helpers that are **only** used inside the test-suite to avoid shipping
non-production code in the main package.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from mpv_scraper.images import ensure_png_size


def create_placeholder_png(
    dest: Path,
    size: tuple[int, int] = (1, 1),
    color: tuple[int, int, int, int] | str = (255, 255, 255, 0),
) -> None:
    """Create a tiny PNG (<1 KB) that satisfies project constraints."""

    if dest.suffix.lower() != ".png":
        dest = dest.with_suffix(".png")

    dest.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", size, color)  # type: ignore[arg-type]
    img.save(dest, format="PNG", optimize=True)

    ensure_png_size(dest)
