"""Video conversion utilities for converting MKV to web-optimized MP4.

This module provides functionality to convert MKV files to MP4 format
with web optimization, reducing file size while maintaining quality.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConversionPreset:
    """Preset configuration for video conversion."""
    name: str
    video_codec: str
    audio_codec: str
    subtitle_codec: Optional[str]
    crf: int
    preset: str
    tune: str
    include_subs: bool
    description: str


# Predefined conversion presets
VANILLA_WITH_SUBS = ConversionPreset(
    name="vanilla_with_subs",
    video_codec="libx264",
    audio_codec="copy",
    subtitle_codec="mov_text",
    crf=24,
    preset="faster",
    tune="film",
    include_subs=True,
    description="2 channel audio, soft subs, web optimized, shrink file size by ~2/3"
)

VANILLA_NO_SUBS = ConversionPreset(
    name="vanilla_no_subs",
    video_codec="libx264",
    audio_codec="copy",
    subtitle_codec=None,
    crf=24,
    preset="faster",
    tune="animation",
    include_subs=False,
    description="2 channel audio, no subs, web optimized, shrink file size by ~2/3"
)




def convert_mkv_to_mp4(
    input_path: Path,
    output_path: Path,
    preset: ConversionPreset,
    overwrite: bool = False
) -> bool:
    """
    Convert MKV file to web-optimized MP4 using FFmpeg.
    
    Args:
        input_path: Path to input MKV file
        output_path: Path for output MP4 file
        preset: Conversion preset configuration
        overwrite: Whether to overwrite existing output file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Build ffmpeg command
        cmd = ["ffmpeg", "-i", str(input_path)]
        
        # Add subtitle handling
        if preset.include_subs and preset.subtitle_codec:
            # Include subtitles with specified codec
            cmd.extend(["-map", "0", "-c:s", preset.subtitle_codec])
        else:
            # Exclude subtitles
            cmd.extend(["-map", "0:v:0", "-map", "0:a", "-sn"])
        
        # Add video encoding parameters
        cmd.extend([
            "-c:v", preset.video_codec,
            "-preset", preset.preset,
            "-tune", preset.tune,
            "-crf", str(preset.crf),
            "-pix_fmt", "yuv420p",
            "-c:a", preset.audio_codec,
            "-movflags", "+faststart"
        ])
        
        # Add overwrite flag if requested
        if overwrite:
            cmd.append("-y")
        
        # Add output path
        cmd.append(str(output_path))
        
        logger.info(f"Converting {input_path.name} to MP4 using {preset.name} preset...")
        
        # Run ffmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for video conversion
        )
        
        if result.returncode == 0:
            logger.info(f"✓ Successfully converted {input_path.name} to MP4")
            return True
        else:
            logger.warning(f"ffmpeg failed for {input_path.name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning(f"ffmpeg timeout for {input_path.name}")
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg to enable video conversion.")
        return False
    except Exception as e:
        logger.warning(f"Failed to convert {input_path.name}: {e}")
        return False


def batch_convert_mkv_to_mp4(
    directory: Path,
    preset: ConversionPreset,
    dry_run: bool = False,
    overwrite: bool = False
) -> Tuple[int, int]:
    """
    Batch convert all MKV files in a directory to MP4.
    
    Args:
        directory: Directory containing MKV files
        preset: Conversion preset to use
        dry_run: If True, only show what would be converted
        overwrite: Whether to overwrite existing MP4 files
        
    Returns:
        Tuple of (processed_count, success_count)
    """
    processed = 0
    successful = 0
    
    logger.info(f"Scanning {directory} for MKV files to convert...")
    
    for mkv_file in directory.glob("*.mkv"):
        if not mkv_file.is_file():
            continue
            
        processed += 1
        
        # Create output filename
        output_path = mkv_file.with_suffix('.mp4')
        
        # Check if output already exists
        if output_path.exists() and not overwrite:
            logger.warning(f"Skipping {mkv_file.name} - {output_path.name} already exists")
            continue
        
        if dry_run:
            logger.info(f"[DRY RUN] Would convert {mkv_file.name} -> {output_path.name} "
                       f"using {preset.name} preset")
            successful += 1
            continue
            
        if convert_mkv_to_mp4(mkv_file, output_path, preset, overwrite):
            successful += 1
            
    logger.info(f"Conversion complete: {successful}/{processed} videos converted successfully")
    return processed, successful


def batch_convert_mkv_to_mp4_with_fallback(
    directory: Path,
    dry_run: bool = False,
    overwrite: bool = False
) -> Tuple[int, int]:
    """
    Batch convert all MKV files in a directory to MP4 with automatic fallback.
    
    Attempts conversion with subtitles first, then falls back to no subtitles
    if the conversion fails (e.g., for Blu-ray rips with incompatible subtitle formats).
    
    Args:
        directory: Directory containing MKV files
        dry_run: If True, only show what would be converted
        overwrite: Whether to overwrite existing MP4 files
        
    Returns:
        Tuple of (processed_count, success_count)
    """
    processed = 0
    successful = 0
    
    logger.info(f"Scanning {directory} for MKV files to convert with fallback...")
    
    for mkv_file in directory.glob("*.mkv"):
        if not mkv_file.is_file():
            continue
            
        processed += 1
        
        # Create output filename
        output_path = mkv_file.with_suffix('.mp4')
        
        # Check if output already exists
        if output_path.exists() and not overwrite:
            logger.warning(f"Skipping {mkv_file.name} - {output_path.name} already exists")
            continue
        
        if dry_run:
            logger.info(f"[DRY RUN] Would convert {mkv_file.name} -> {output_path.name} "
                       f"with subtitles first, fallback to no subtitles if needed")
            successful += 1
            continue
            
        # Try with subtitles first
        logger.info(f"Converting {mkv_file.name} with subtitles...")
        if convert_mkv_to_mp4(mkv_file, output_path, VANILLA_WITH_SUBS, overwrite):
            successful += 1
            logger.info(f"✓ Successfully converted {mkv_file.name} with subtitles")
        else:
            # Fallback to no subtitles
            logger.warning(f"Failed to convert {mkv_file.name} with subtitles, trying without subtitles...")
            if convert_mkv_to_mp4(mkv_file, output_path, VANILLA_NO_SUBS, overwrite):
                successful += 1
                logger.info(f"✓ Successfully converted {mkv_file.name} without subtitles (fallback)")
            else:
                logger.error(f"Failed to convert {mkv_file.name} with both subtitle options")
            
    logger.info(f"Conversion complete: {successful}/{processed} videos converted successfully")
    return processed, successful


def get_video_info(video_path: Path) -> Optional[dict]:
    """
    Get detailed video information including codecs and streams.
    
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
            "-show_entries", "stream=width,height,codec_name,bit_rate",
            "-show_entries", "format=duration,size",
            "-of", "json",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            info = {
                'width': int(data['streams'][0]['width']),
                'height': int(data['streams'][0]['height']),
                'video_codec': data['streams'][0]['codec_name'],
                'duration': float(data['format']['duration']),
                'size_mb': int(data['format']['size']) / (1024 * 1024)
            }
            
            return info
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to get video info for {video_path.name}: {e}")
        return None


def estimate_conversion_time(file_size_mb: float, preset: ConversionPreset) -> str:
    """
    Estimate conversion time based on file size and preset.
    
    Args:
        file_size_mb: File size in MB
        preset: Conversion preset
        
    Returns:
        Estimated time as string
    """
    # Rough estimates based on preset
    if preset.preset == "faster":
        mb_per_minute = 200  # ~200MB per minute on faster preset
    elif preset.preset == "medium":
        mb_per_minute = 100  # ~100MB per minute on medium preset
    else:
        mb_per_minute = 50   # ~50MB per minute on slower presets
    
    minutes = file_size_mb / mb_per_minute
    if minutes < 1:
        return "less than 1 minute"
    elif minutes < 60:
        return f"~{int(minutes)} minutes"
    else:
        hours = minutes / 60
        return f"~{hours:.1f} hours"



