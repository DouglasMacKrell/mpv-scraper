"""Video cropping utilities for removing letterboxing and pillarboxing.

This module provides functionality to detect and crop videos that have been
formatted for 16:9 displays but contain 4:3 content with black bars.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CropInfo:
    """Information about video cropping parameters."""
    width: int
    height: int
    crop_x: int
    crop_y: int
    crop_width: int
    crop_height: int
    target_aspect: float = 4/3  # 4:3 aspect ratio


def detect_letterboxing(video_path: Path) -> Optional[CropInfo]:
    """
    Detect if a video has letterboxing (black bars on left/right for 4:3 content in 16:9).
    
    Args:
        video_path: Path to the video file
        
    Returns:
        CropInfo if letterboxing is detected, None otherwise
    """
    try:
        # Get video dimensions
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            logger.warning(f"ffprobe failed for {video_path.name}: {result.stderr}")
            return None
            
        # Parse dimensions
        width, height = map(int, result.stdout.strip().split(','))
        
        # Check if this is a 16:9 video that might contain 4:3 content
        current_aspect = width / height
        target_aspect = 4/3
        
        # If video is 16:9 (aspect ~1.78) and we want 4:3 (aspect ~1.33)
        if abs(current_aspect - 16/9) < 0.1:  # Allow small tolerance
            # Calculate crop dimensions for 4:3
            # For 1920x1080, we want to crop to ~1440x1080 (4:3)
            crop_width = int(height * target_aspect)
            crop_height = height
            crop_x = (width - crop_width) // 2  # Center the crop
            crop_y = 0
            
            logger.info(f"Detected letterboxing in {video_path.name}: "
                       f"{width}x{height} -> {crop_width}x{crop_height} "
                       f"(crop {crop_x},{crop_y})")
            
            return CropInfo(
                width=width,
                height=height,
                crop_x=crop_x,
                crop_y=crop_y,
                crop_width=crop_width,
                crop_height=crop_height
            )
        
        return None
        
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
        logger.warning(f"Failed to detect letterboxing for {video_path.name}: {e}")
        return None


def crop_video_to_4_3(
    input_path: Path,
    output_path: Path,
    crop_info: CropInfo,
    quality: str = "high"
) -> bool:
    """
    Crop a video to 4:3 aspect ratio using FFmpeg.
    
    Args:
        input_path: Path to input video file
        output_path: Path for output video file
        crop_info: Crop parameters
        quality: Quality preset ('fast', 'medium', 'high')
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Quality presets
        quality_settings = {
            'fast': ['-preset', 'ultrafast', '-crf', '23'],
            'medium': ['-preset', 'medium', '-crf', '20'],
            'high': ['-preset', 'slow', '-crf', '18']
        }
        
        # Build crop filter
        crop_filter = f"crop={crop_info.crop_width}:{crop_info.crop_height}:{crop_info.crop_x}:{crop_info.crop_y}"
        
        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-vf", crop_filter,
            "-c:v", "libx264",  # H.264 codec
            "-c:a", "copy",     # Copy audio without re-encoding
            "-y",               # Overwrite output
            *quality_settings.get(quality, quality_settings['medium']),
            str(output_path)
        ]
        
        logger.info(f"Cropping {input_path.name} to 4:3...")
        
        # Run ffmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout for video processing
        )
        
        if result.returncode == 0:
            logger.info(f"✓ Successfully cropped {input_path.name} to 4:3")
            return True
        else:
            logger.warning(f"ffmpeg failed for {input_path.name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning(f"ffmpeg timeout for {input_path.name}")
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg to enable video cropping.")
        return False
    except Exception as e:
        logger.warning(f"Failed to crop {input_path.name}: {e}")
        return False


def batch_crop_videos_to_4_3(
    directory: Path,
    quality: str = "medium",
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Batch crop all videos in a directory to 4:3 aspect ratio.
    
    Args:
        directory: Directory containing video files
        quality: Quality preset for encoding
        dry_run: If True, only detect and report without cropping
        
    Returns:
        Tuple of (processed_count, success_count)
    """
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    processed = 0
    successful = 0
    
    logger.info(f"Scanning {directory} for videos to crop...")
    
    for video_file in directory.iterdir():
        if not video_file.is_file() or video_file.suffix.lower() not in video_extensions:
            continue
            
        crop_info = detect_letterboxing(video_file)
        if not crop_info:
            continue
            
        processed += 1
        
        if dry_run:
            logger.info(f"[DRY RUN] Would crop {video_file.name} "
                       f"({crop_info.width}x{crop_info.height} -> "
                       f"{crop_info.crop_width}x{crop_info.crop_height})")
            successful += 1
            continue
            
        # Create output filename
        output_path = video_file.parent / f"{video_file.stem}_4x3{video_file.suffix}"
        
        if crop_video_to_4_3(video_file, output_path, crop_info, quality):
            successful += 1
            
    logger.info(f"Crop processing complete: {successful}/{processed} videos processed successfully")
    return processed, successful


def get_video_info(video_path: Path) -> Optional[dict]:
    """
    Get detailed video information including aspect ratios.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dictionary with video info or None if failed
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,sample_aspect_ratio,display_aspect_ratio",
            "-of", "json",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            stream = data['streams'][0]
            
            return {
                'width': int(stream['width']),
                'height': int(stream['height']),
                'sample_aspect_ratio': stream.get('sample_aspect_ratio', '1:1'),
                'display_aspect_ratio': stream.get('display_aspect_ratio', '1:1')
            }
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to get video info for {video_path.name}: {e}")
        return None
