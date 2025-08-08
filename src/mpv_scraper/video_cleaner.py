"""
Video cleaner module for detecting and optimizing problematic video files.

This module identifies videos that are likely to cause playback issues on handheld
devices (slow frame rate, audio sync problems) and provides optimization options.
"""

import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
import json
import platform

logger = logging.getLogger(__name__)

@dataclass
class VideoAnalysis:
    """Analysis results for a video file."""
    file_path: Path
    codec: str
    profile: str
    width: int
    height: int
    bitrate: int
    pixel_format: str
    file_size_mb: float
    duration_seconds: float
    is_problematic: bool
    issues: List[str]
    optimization_score: float  # 0.0 = perfect, 1.0 = needs optimization

@dataclass
class OptimizationPreset:
    """Preset for video optimization."""
    name: str
    description: str
    target_codec: str
    target_profile: str
    target_bitrate: int
    target_resolution: Tuple[int, int]
    crf: int
    preset: str
    tune: str
    audio_codec: str
    audio_bitrate: int

# Optimization presets for handheld compatibility
HANDHELD_OPTIMIZED = OptimizationPreset(
    name="handheld_optimized",
    description="Optimized for handheld devices - H.264, moderate bitrate, 720p max",
    target_codec="libx264",
    target_profile="high10",  # Changed from "high" to "high10" to support 10-bit input
    target_bitrate=1500000,  # 1.5 Mbps
    target_resolution=(1280, 720),  # 720p max
    crf=23,
    preset="faster",
    tune="film",
    audio_codec="aac",
    audio_bitrate=128000  # 128 kbps
)

COMPATIBILITY_MODE = OptimizationPreset(
    name="compatibility_mode",
    description="Maximum compatibility - H.264, lower bitrate, 480p max",
    target_codec="libx264",
    target_profile="baseline",
    target_bitrate=800000,  # 800 kbps
    target_resolution=(854, 480),  # 480p max
    crf=25,
    preset="ultrafast",
    tune="fastdecode",
    audio_codec="aac",
    audio_bitrate=96000  # 96 kbps
)

def analyze_video_file(video_path: Path) -> Optional[VideoAnalysis]:
    """
    Analyze a video file to determine if it's problematic for handheld playback.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        VideoAnalysis object with detailed analysis, or None if analysis fails
    """
    try:
        # Get detailed video information using ffprobe
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.error(f"Failed to analyze {video_path}: {result.stderr}")
            return None
            
        data = json.loads(result.stdout)
        
        # Find video stream
        video_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break
                
        if not video_stream:
            logger.error(f"No video stream found in {video_path}")
            return None
            
        # Extract video properties
        codec = video_stream.get("codec_name", "unknown")
        profile = video_stream.get("profile", "unknown")
        width = video_stream.get("width", 0)
        height = video_stream.get("height", 0)
        bitrate = int(video_stream.get("bit_rate", 0))
        pixel_format = video_stream.get("pix_fmt", "unknown")
        
        # Get file size and duration
        format_info = data.get("format", {})
        file_size_mb = float(format_info.get("size", 0)) / (1024 * 1024)
        duration_seconds = float(format_info.get("duration", 0))
        
        # Determine if file is problematic
        issues = []
        optimization_score = 0.0
        
        # Check for problematic codecs
        if codec in ["hevc", "h265"]:
            issues.append("HEVC/H.265 codec (CPU intensive)")
            optimization_score += 0.3
            
        # Check for 10-bit color depth
        if "10" in pixel_format:
            issues.append("10-bit color depth (requires more processing)")
            optimization_score += 0.2
            
        # Check for high bitrate
        if bitrate > 3000000:  # > 3 Mbps
            issues.append(f"High bitrate ({bitrate/1000000:.1f} Mbps)")
            optimization_score += 0.2
            
        # Check for high resolution
        if width > 1280 or height > 720:
            issues.append(f"High resolution ({width}x{height})")
            optimization_score += 0.2
            
        # Check for complex profiles
        if profile in ["Main 10", "Main", "High 10"]:
            issues.append(f"Complex profile ({profile})")
            optimization_score += 0.1
            
        # Check for large file size relative to duration
        if duration_seconds > 0:
            mb_per_minute = file_size_mb / (duration_seconds / 60)
            if mb_per_minute > 50:  # > 50 MB per minute
                issues.append(f"Large file size ({mb_per_minute:.1f} MB/min)")
                optimization_score += 0.2
                
        # Cap optimization score at 1.0
        optimization_score = min(optimization_score, 1.0)
        
        is_problematic = optimization_score > 0.3  # Threshold for "problematic"
        
        return VideoAnalysis(
            file_path=video_path,
            codec=codec,
            profile=profile,
            width=width,
            height=height,
            bitrate=bitrate,
            pixel_format=pixel_format,
            file_size_mb=file_size_mb,
            duration_seconds=duration_seconds,
            is_problematic=is_problematic,
            issues=issues,
            optimization_score=optimization_score
        )
        
    except Exception as e:
        logger.error(f"Error analyzing {video_path}: {e}")
        return None

def check_disk_space(directory: Path, required_gb: float = 1.0) -> bool:
    """
    Check if there's enough disk space available.
    
    Args:
        directory: Directory to check space for
        required_gb: Required space in GB
        
    Returns:
        True if enough space available, False otherwise
    """
    try:
        total, used, free = shutil.disk_usage(directory)
        free_gb = free / (1024**3)  # Convert to GB
        logger.info(f"Available disk space: {free_gb:.2f} GB")
        return free_gb >= required_gb
    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
        return True  # Assume OK if we can't check


def optimize_video_file(
    input_path: Path,
    output_path: Path,
    preset: OptimizationPreset,
    overwrite: bool = False
) -> bool:
    """
    Optimize a video file for handheld playback.
    
    Args:
        input_path: Path to input video file
        output_path: Path for optimized output file
        preset: Optimization preset to use
        overwrite: Whether to overwrite existing output file
        
    Returns:
        True if optimization succeeded, False otherwise
    """
    try:
        # If an output exists but is empty, force overwrite to fix previous failed runs
        if output_path.exists():
            try:
                if output_path.stat().st_size == 0:
                    logger.warning(f"Existing output {output_path} is empty – will overwrite")
                    overwrite = True
            except Exception:
                # If stat fails, fall back to overwriting
                overwrite = True
        if output_path.exists() and not overwrite:
            logger.warning(f"Output file {output_path} already exists, skipping")
            return False

        is_macos = platform.system() == "Darwin"

        # Build ffmpeg command with optional hardware acceleration on macOS
        # Prefer hardware encoder for speed; fall back to software if it fails
        def build_cmd(use_hardware: bool) -> List[str]:
            cmd_parts: List[str] = ["ffmpeg"]
            if use_hardware and is_macos:
                cmd_parts += ["-hwaccel", "videotoolbox"]
            cmd_parts += ["-i", str(input_path)]

            vf_chain: List[str] = []
            # Always emit 8-bit for maximum compatibility on handhelds
            vf_chain.append("format=yuv420p")
            if preset.target_resolution:
                vf_chain.append(
                    f"scale={preset.target_resolution[0]}:{preset.target_resolution[1]}:force_original_aspect_ratio=decrease"
                )

            if use_hardware and is_macos:
                # h264_videotoolbox uses bitrate-based control
                cmd_parts += [
                    "-c:v", "h264_videotoolbox",
                    "-profile:v", "high",
                    "-b:v", str(preset.target_bitrate),
                    "-maxrate", str(preset.target_bitrate),
                    "-bufsize", str(preset.target_bitrate * 2),
                    "-pix_fmt", "yuv420p",
                ]
            else:
                # Software x264 with CRF
                cmd_parts += [
                    "-c:v", "libx264",
                    "-profile:v", "high",
                    "-preset", preset.preset,
                    "-crf", str(preset.crf),
                    "-tune", preset.tune,
                    "-pix_fmt", "yuv420p",
                    "-threads", "0",
                ]

            # Attach filters, audio and container flags
            if vf_chain:
                cmd_parts += ["-vf", ",".join(vf_chain)]
            cmd_parts += [
                "-c:a", preset.audio_codec,
                "-b:a", str(preset.audio_bitrate),
                "-movflags", "+faststart",
                "-y" if overwrite else "-n",
                str(output_path),
            ]
            return cmd_parts

        # Try hardware first (on macOS), then fallback to software
        attempts: List[Tuple[str, List[str]]] = []
        if is_macos:
            attempts.append(("hardware (h264_videotoolbox)", build_cmd(True)))
        attempts.append(("software (libx264)", build_cmd(False)))

        for label, cmd in attempts:
            logger.info(f"Optimizing {input_path.name} using {preset.name} preset via {label}...")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            if result.returncode == 0:
                logger.info(f"✓ Successfully optimized {input_path.name} using {label}")
                return True
            else:
                logger.warning(
                    f"Attempt with {label} failed for {input_path.name}: {result.stderr.splitlines()[-1] if result.stderr else 'unknown error'}"
                )
                # If this was hardware attempt and it failed, ensure we overwrite the broken target on retry
                try:
                    if output_path.exists() and output_path.stat().st_size == 0:
                        output_path.unlink(missing_ok=True)
                except Exception:
                    pass

        logger.error(f"Failed to optimize {input_path.name} after all attempts")
        return False

    except subprocess.TimeoutExpired:
        logger.error(f"Optimization of {input_path.name} timed out")
        return False
    except Exception as e:
        logger.error(f"Error optimizing {input_path.name}: {e}")
        return False

def batch_analyze_videos(
    directory: Path,
    dry_run: bool = False
) -> Tuple[List[VideoAnalysis], List[VideoAnalysis]]:
    """
    Analyze all video files in a directory.
    
    Args:
        directory: Directory to scan
        dry_run: If True, only analyze without processing
        
    Returns:
        Tuple of (all_videos, problematic_videos)
    """
    all_videos = []
    problematic_videos = []
    
    logger.info(f"Analyzing videos in {directory}...")
    
    # Find all video files
    video_extensions = [".mp4", ".mkv", ".avi", ".mov", ".m4v"]
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(directory.glob(f"*{ext}"))
        
    logger.info(f"Found {len(video_files)} video files to analyze")
    
    for video_file in video_files:
        if not video_file.is_file():
            continue
        # Skip AppleDouble files and previously optimized outputs
        name = video_file.name
        if name.startswith("._"):
            continue
        if name.endswith("_optimized.mp4") or name.endswith("_optimized.mkv"):
            continue
            
        analysis = analyze_video_file(video_file)
        if analysis:
            all_videos.append(analysis)
            
            if analysis.is_problematic:
                problematic_videos.append(analysis)
                logger.warning(f"Problematic file: {video_file.name}")
                logger.warning(f"  Issues: {', '.join(analysis.issues)}")
                logger.warning(f"  Optimization score: {analysis.optimization_score:.2f}")
                
    logger.info(f"Analysis complete: {len(problematic_videos)}/{len(all_videos)} files are problematic")
    return all_videos, problematic_videos

def batch_optimize_videos(
    directory: Path,
    preset: OptimizationPreset = HANDHELD_OPTIMIZED,
    dry_run: bool = False,
    overwrite: bool = False
) -> Tuple[int, int]:
    """
    Batch optimize problematic videos in a directory.
    
    Args:
        directory: Directory containing videos
        preset: Optimization preset to use
        dry_run: If True, only show what would be optimized
        overwrite: Whether to overwrite existing optimized files
        
    Returns:
        Tuple of (processed_count, success_count)
    """
    processed = 0
    successful = 0
    
    # First analyze all videos
    all_videos, problematic_videos = batch_analyze_videos(directory, dry_run)
    
    if not problematic_videos:
        logger.info("No problematic videos found - no optimization needed")
        return 0, 0
        
    logger.info(f"Found {len(problematic_videos)} videos that need optimization")
    
    for analysis in problematic_videos:
        processed += 1
        
        # Create output filename
        output_path = analysis.file_path.with_name(
            f"{analysis.file_path.stem}_optimized{analysis.file_path.suffix}"
        )
        
        if dry_run:
            logger.info(f"[DRY RUN] Would optimize {analysis.file_path.name} -> {output_path.name}")
            logger.info(f"  Issues: {', '.join(analysis.issues)}")
            logger.info(f"  Using preset: {preset.name}")
            successful += 1
            continue
            
        if optimize_video_file(analysis.file_path, output_path, preset, overwrite):
            successful += 1
            
    logger.info(f"Optimization complete: {successful}/{processed} videos optimized successfully")
    return processed, successful

def get_optimization_recommendation(analysis: VideoAnalysis) -> str:
    """
    Get a human-readable recommendation for video optimization.
    
    Args:
        analysis: Video analysis results
        
    Returns:
        Recommendation string
    """
    if not analysis.is_problematic:
        return "No optimization needed - file should play smoothly on handheld devices"
        
    recommendations = []
    
    if analysis.codec in ["hevc", "h265"]:
        recommendations.append("Convert to H.264 for better compatibility")
        
    if "10" in analysis.pixel_format:
        recommendations.append("Convert to 8-bit color depth")
        
    if analysis.bitrate > 3000000:
        recommendations.append("Reduce bitrate to ~1.5 Mbps")
        
    if analysis.width > 1280 or analysis.height > 720:
        recommendations.append("Scale down to 720p or lower")
        
    if analysis.optimization_score > 0.7:
        recommendations.append("Use compatibility mode preset for maximum compatibility")
    else:
        recommendations.append("Use handheld optimized preset for good balance")
        
    return "; ".join(recommendations)
