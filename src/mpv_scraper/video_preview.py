"""
ES-DE video preview clip generation.

Extracts 30-second preview clips from the 25% mark of each video,
stored in /mpv/videos/ as {stem}-preview.mp4, targeting <1 MB for ES-DE.
"""

from __future__ import annotations

import subprocess
import logging
from pathlib import Path
from typing import Optional

from mpv_scraper.video_capture import get_video_duration

logger = logging.getLogger(__name__)

# ES-DE recommendation: <1 MB per preview for handhelds
DEFAULT_MAX_SIZE_BYTES = 1024 * 1024
DEFAULT_START_PERCENT = 25.0
DEFAULT_DURATION_SEC = 30
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480


def get_preview_path(videos_dir: Path, stem: str) -> Path:
    """
    Return the path for a preview file given the videos directory and stem.

    Args:
        videos_dir: Directory where previews are stored (e.g. /mpv/videos)
        stem: Filename stem without extension (e.g. "Show - S01E01 - Title")

    Returns:
        Path to the preview file: videos_dir / "{stem}-preview.mp4"
    """
    return videos_dir / f"{stem}-preview.mp4"


def extract_preview_clip(
    input_path: Path,
    output_path: Path,
    start_pct: float = DEFAULT_START_PERCENT,
    duration_sec: int = DEFAULT_DURATION_SEC,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> bool:
    """
    Extract a preview clip from a video file.

    Starts at start_pct of duration, extracts duration_sec seconds.
    Output: H.264 MP4, scaled to width x height, targeting <1 MB.

    Args:
        input_path: Source video file
        output_path: Output path for the preview MP4
        start_pct: Start position as percentage of duration (default 25)
        duration_sec: Length of clip in seconds (default 30)
        width: Output width (default 640)
        height: Output height (default 480)

    Returns:
        True if successful, False otherwise
    """
    if not input_path.exists():
        logger.warning(f"Input video not found: {input_path}")
        return False

    duration = get_video_duration(input_path)
    if duration is None:
        logger.warning(f"Could not get duration for {input_path.name}")
        return False

    start_sec = (duration * start_pct) / 100.0
    # Cap duration to not exceed video end
    actual_duration = min(duration_sec, max(0, duration - start_sec))
    if actual_duration <= 0:
        logger.warning(f"Video too short for preview: {input_path.name}")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Bitrate target for ~1 MB: 1MB / 30s ≈ 280 kbps, use 256k for safety
        target_bitrate = 256000
        cmd = [
            "ffmpeg",
            "-ss",
            f"{start_sec:.2f}",
            "-i",
            str(input_path),
            "-t",
            f"{actual_duration:.2f}",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-b:v",
            str(target_bitrate),
            "-maxrate",
            str(target_bitrate),
            "-bufsize",
            str(target_bitrate * 2),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ac",
            "2",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            "-y",
            str(output_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            logger.info(f"Created preview: {output_path.name}")
            return True
        logger.warning(f"ffmpeg failed for {input_path.name}: {result.stderr}")
        return False

    except subprocess.TimeoutExpired:
        logger.warning(f"Preview extraction timeout for {input_path.name}")
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found")
        return False
    except Exception as e:
        logger.warning(f"Preview extraction failed for {input_path.name}: {e}")
        return False


def ensure_preview(
    video_path: Path,
    videos_dir: Path,
    stem: str,
    *,
    generate: bool = True,
) -> Optional[str]:
    """
    Ensure a preview exists for the video; return relative path for gamelist.

    If preview already exists, returns the relative path without re-extracting.
    If generate is True and preview is missing, attempts to create it.

    Args:
        video_path: Path to the source video file
        videos_dir: Directory for previews (e.g. root / "videos")
        stem: Filename stem for the preview (e.g. from file_path.stem)
        generate: If True, extract when preview is missing

    Returns:
        Relative path like "./videos/{stem}-preview.mp4" or None if unavailable
    """
    preview_path = get_preview_path(videos_dir, stem)

    if preview_path.exists() and preview_path.stat().st_size > 0:
        return f"./videos/{stem}-preview.mp4"

    if not generate or not video_path.exists():
        return None

    videos_dir.mkdir(parents=True, exist_ok=True)
    if extract_preview_clip(video_path, preview_path):
        return f"./videos/{stem}-preview.mp4"
    return None
