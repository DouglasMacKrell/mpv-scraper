"""Video capture utilities for generating screenshots from video files.

This module provides functionality to extract frames from video files
at specific timestamps, useful for creating episode images when API
data is unavailable.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def capture_video_frame(
    video_path: Path,
    output_path: Path,
    timestamp: str = "25%",
    width: int = 640,
    height: int = 480,
) -> bool:
    """
    Capture a frame from a video file using ffmpeg.

    Args:
        video_path: Path to the input video file
        output_path: Path where the screenshot will be saved
        timestamp: When to capture the frame (e.g., "25%", "00:01:30", "60")
        width: Output image width
        height: Output image height

    Returns:
        True if successful, False otherwise
    """
    try:
        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-ss",
            timestamp,
            "-vframes",
            "1",
            "-vf",
            f"scale={width}:{height}",
            "-y",  # Overwrite output file
            str(output_path),
        ]

        # Run ffmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
        )

        if result.returncode == 0:
            logger.info(
                f"Successfully captured frame from {video_path.name} at {timestamp}"
            )
            return True
        else:
            logger.warning(f"ffmpeg failed for {video_path.name}: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.warning(f"ffmpeg timeout for {video_path.name}")
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg to enable video capture.")
        return False
    except Exception as e:
        logger.warning(f"Failed to capture frame from {video_path.name}: {e}")
        return False


def get_video_duration(video_path: Path) -> Optional[float]:
    """
    Get the duration of a video file in seconds.

    Args:
        video_path: Path to the video file

    Returns:
        Duration in seconds, or None if failed
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(video_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            return float(result.stdout.strip())
        else:
            logger.warning(f"ffprobe failed for {video_path.name}: {result.stderr}")
            return None

    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
        logger.warning(f"Failed to get duration for {video_path.name}: {e}")
        return None


def capture_at_percentage(
    video_path: Path,
    output_path: Path,
    percentage: float = 25.0,
    width: int = 640,
    height: int = 480,
) -> bool:
    """
    Capture a frame at a specific percentage through the video.

    Args:
        video_path: Path to the input video file
        output_path: Path where the screenshot will be saved
        percentage: Percentage through the video (0-100)
        width: Output image width
        height: Output image height

    Returns:
        True if successful, False otherwise
    """
    # Get video duration
    duration = get_video_duration(video_path)
    if not duration:
        return False

    # Calculate timestamp
    timestamp_seconds = (duration * percentage) / 100.0
    timestamp = f"{timestamp_seconds:.2f}"

    return capture_video_frame(video_path, output_path, timestamp, width, height)
