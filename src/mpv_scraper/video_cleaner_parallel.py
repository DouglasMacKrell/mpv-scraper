"""
Parallel video cleaner module for processing multiple files simultaneously.

This module provides parallel processing capabilities for the video cleaner,
allowing multiple files to be optimized concurrently for faster processing.
"""

import subprocess
import logging
import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from dataclasses import dataclass
import platform
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class ParallelOptimizationTask:
    """Task for parallel video optimization."""

    input_path: Path
    output_path: Path
    preset_name: str
    preset_config: dict


def get_optimal_worker_count() -> int:
    """Determine optimal number of worker processes based on system resources."""
    cpu_count = mp.cpu_count()

    # For video processing, we want to balance CPU cores with memory/disk I/O
    # Too many concurrent FFmpeg processes can overwhelm the system
    if cpu_count <= 4:
        return max(1, cpu_count - 1)  # Leave one core for system
    elif cpu_count <= 8:
        return cpu_count - 2  # Leave two cores for system
    else:
        return min(cpu_count - 2, 6)  # Cap at 6 workers for stability


def optimize_single_file_worker(
    task: ParallelOptimizationTask,
) -> Tuple[Path, bool, str]:
    """
    Worker function for optimizing a single video file.

    Args:
        task: Optimization task containing file paths and preset configuration

    Returns:
        Tuple of (input_path, success, error_message)
    """
    try:
        # Check if output already exists and is valid
        if (
            task.output_path.exists() and task.output_path.stat().st_size > 1024 * 1024
        ):  # > 1MB
            return (task.input_path, True, "Already optimized")

        # Determine platform
        is_macos = platform.system() == "Darwin"

        # Prepare common parameters
        target_profile = task.preset_config.get("target_profile", "high")
        target_bitrate = int(task.preset_config.get("target_bitrate", 1500000))
        target_resolution = task.preset_config.get("target_resolution", (1280, 720))
        audio_codec = task.preset_config.get("audio_codec", "aac")
        audio_bitrate = int(task.preset_config.get("audio_bitrate", 128000))
        crf = str(task.preset_config.get("crf", 23))
        x264_preset = task.preset_config.get("preset", "faster")
        tune = task.preset_config.get("tune")

        # Build hardware (videotoolbox) command using bitrate control
        hw_cmd: List[str] = [
            "ffmpeg",
            "-i",
            str(task.input_path),
            "-c:v",
            "h264_videotoolbox",
            "-profile:v",
            target_profile,
            "-b:v",
            str(target_bitrate),
            "-maxrate",
            str(target_bitrate),
            "-bufsize",
            str(target_bitrate * 2),
            "-vf",
            f"scale={target_resolution[0]}:{target_resolution[1]}:force_original_aspect_ratio=decrease",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            audio_codec,
            "-b:a",
            str(audio_bitrate),
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            "-y",
            str(task.output_path),
        ]

        # Build software (libx264) command using CRF
        sw_cmd: List[str] = [
            "ffmpeg",
            "-i",
            str(task.input_path),
            "-c:v",
            "libx264",
            "-profile:v",
            target_profile,
            "-preset",
            x264_preset,
            "-crf",
            crf,
            "-vf",
            f"scale={target_resolution[0]}:{target_resolution[1]}:force_original_aspect_ratio=decrease",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            audio_codec,
            "-b:a",
            str(audio_bitrate),
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            "-threads",
            "0",
            "-y",
            str(task.output_path),
        ]
        if tune:
            # Insert tune right after the CRF/preset for clarity
            sw_cmd.extend(["-tune", tune])
            # tune is not used for videotoolbox

        # Choose attempt order
        attempts: List[Tuple[str, List[str]]] = []
        if is_macos:
            attempts.append(("hardware (h264_videotoolbox)", hw_cmd))
        attempts.append(("software (libx264)", sw_cmd))

        # Run FFmpeg with timeout
        timeout = task.preset_config.get("timeout", 1800)  # 30 minutes default

        last_error = None
        for label, cmd in attempts:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout
                )
                if (
                    result.returncode == 0
                    and task.output_path.exists()
                    and task.output_path.stat().st_size > 1024 * 1024
                ):
                    return (task.input_path, True, f"Success via {label}")
                # Clean up broken/empty outputs between attempts
                try:
                    if (
                        task.output_path.exists()
                        and task.output_path.stat().st_size < 1024 * 1024
                    ):
                        task.output_path.unlink(missing_ok=True)
                except Exception:
                    pass
                last_error = result.stderr[-500:] if result.stderr else "Unknown error"
            except subprocess.TimeoutExpired:
                return (task.input_path, False, f"Timeout during {label}")

        return (task.input_path, False, f"Conversion failed: {last_error}")

    except Exception as e:
        return (task.input_path, False, f"Exception: {str(e)}")


def parallel_optimize_videos(
    directory: Path,
    preset_config: dict,
    max_workers: Optional[int] = None,
    dry_run: bool = False,
    replace_originals: bool = False,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Tuple[int, int, List[str]]:
    """
    Optimize multiple video files in parallel.

    Args:
        directory: Directory containing video files
        preset_config: Optimization preset configuration
        max_workers: Maximum number of worker processes (auto-detect if None)
        dry_run: If True, only show what would be processed

    Returns:
        Tuple of (total_processed, successful_count, error_messages)
    """
    if max_workers is None:
        max_workers = get_optimal_worker_count()

    logger.info(f"Starting parallel optimization with {max_workers} workers")

    # Find all video files
    video_files = []
    for ext in [".mp4", ".mkv", ".avi", ".mov"]:
        video_files.extend(directory.glob(f"*{ext}"))

    # Filter out already optimized files and AppleDouble files
    tasks = []
    for video_file in video_files:
        if video_file.name.startswith("._") or video_file.name.endswith(
            "_optimized.mp4"
        ):
            continue

        output_path = video_file.with_name(f"{video_file.stem}_optimized.mp4")

        task = ParallelOptimizationTask(
            input_path=video_file,
            output_path=output_path,
            preset_name=preset_config.get("name", "handheld"),
            preset_config=preset_config,
        )
        tasks.append(task)

    if dry_run:
        logger.info(
            f"DRY RUN: Would process {len(tasks)} video files with {max_workers} workers"
        )
        return len(tasks), 0, []

    if not tasks:
        logger.info("No video files found to optimize")
        return 0, 0, []

    # Process files in parallel
    successful = 0
    errors = []
    successful_tasks = (
        []
    )  # Track successful tasks for end-of-run replacement when needed

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(optimize_single_file_worker, task): task for task in tasks
        }

        # Process completed tasks
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                input_path, success, message = future.result()
                if success:
                    successful += 1
                    logger.info(f"✅ Optimized: {input_path.name} - {message}")

                    # Incremental replacement: delete original immediately if requested
                    if replace_originals and not dry_run:
                        try:
                            if (
                                task.output_path.exists()
                                and task.output_path.stat().st_size > 1024 * 1024
                            ):
                                # Atomically replace original with optimized
                                os.replace(str(task.output_path), str(task.input_path))
                                logger.info(
                                    f"🗑️  Replaced immediately: {task.input_path.name}"
                                )
                            else:
                                logger.warning(
                                    f"⚠️  Skipped immediate replacement: {task.input_path.name} (optimized file invalid)"
                                )
                        except Exception as e:
                            logger.error(
                                f"❌ Immediate replacement failed for {task.input_path.name}: {str(e)}"
                            )
                            # Fall back to end-of-run sweep attempt
                            successful_tasks.append(task)
                    else:
                        # Track for end-of-run sweep only when not doing immediate replacement
                        successful_tasks.append(task)
                else:
                    errors.append(f"❌ Failed: {input_path.name} - {message}")
                    logger.warning(f"Failed to optimize {input_path.name}: {message}")
            except Exception as e:
                errors.append(f"❌ Exception: {task.input_path.name} - {str(e)}")
                logger.error(f"Exception processing {task.input_path.name}: {str(e)}")

            # Advance progress bar (if provided) after each completed task
            if progress_callback is not None:
                try:
                    progress_callback(1)
                except Exception:
                    # Never let UI callback break processing
                    pass

    # End-of-run sweep replacement for any tasks that weren't replaced immediately
    if replace_originals and not dry_run and successful_tasks:
        logger.info(
            f"Replacing {len(successful_tasks)} remaining original files with optimized versions..."
        )
        replaced_count = 0

        for task in successful_tasks:
            try:
                # Verify optimized file exists and is valid
                if (
                    task.output_path.exists()
                    and task.output_path.stat().st_size > 1024 * 1024
                ):
                    # Atomically replace original with optimized
                    os.replace(str(task.output_path), str(task.input_path))
                    replaced_count += 1
                    logger.info(f"🗑️  Replaced: {task.input_path.name}")
                else:
                    logger.warning(
                        f"⚠️  Skipped replacement: {task.input_path.name} (optimized file invalid)"
                    )
            except Exception as e:
                logger.error(f"❌ Failed to replace {task.input_path.name}: {str(e)}")

        logger.info(f"Replaced {replaced_count}/{len(successful_tasks)} original files")

    logger.info(
        f"Parallel optimization complete: {successful}/{len(tasks)} videos optimized successfully"
    )
    return len(tasks), successful, errors


def estimate_parallel_processing_time(
    file_count: int, avg_file_size_gb: float = 1.0, worker_count: Optional[int] = None
) -> str:
    """
    Estimate processing time for parallel optimization.

    Args:
        file_count: Number of files to process
        avg_file_size_gb: Average file size in GB
        worker_count: Number of workers (auto-detect if None)

    Returns:
        Estimated time as string
    """
    if worker_count is None:
        worker_count = get_optimal_worker_count()

    # Rough estimate: 1GB file takes ~3-5 minutes on modern hardware
    # With parallel processing, we can process multiple files simultaneously
    minutes_per_gb = 4  # Conservative estimate
    total_minutes = (file_count * avg_file_size_gb * minutes_per_gb) / worker_count

    if total_minutes < 60:
        return f"~{int(total_minutes)} minutes"
    elif total_minutes < 1440:  # Less than 24 hours
        hours = total_minutes / 60
        return f"~{hours:.1f} hours"
    else:
        days = total_minutes / 1440
        return f"~{days:.1f} days"


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) != 2:
        print("Usage: python video_cleaner_parallel.py <directory>")
        sys.exit(1)

    directory = Path(sys.argv[1])
    if not directory.exists():
        print(f"Directory {directory} does not exist")
        sys.exit(1)

    # Handheld optimization preset
    preset_config = {
        "name": "handheld_optimized",
        "target_codec": "libx264",
        "target_profile": "high",
        "target_bitrate": 1500000,
        "target_resolution": (1280, 720),
        "crf": 23,
        "preset": "faster",
        "tune": "film",
        "audio_codec": "aac",
        "audio_bitrate": 128000,
        "timeout": 1800,
    }

    print(f"Starting parallel optimization of {directory}")
    print(f"Optimal worker count: {get_optimal_worker_count()}")

    total, successful, errors = parallel_optimize_videos(directory, preset_config)

    print("\nResults:")
    print(f"Total processed: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(errors)}")

    if errors:
        print("\nErrors:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
