"""
Tests for parallel video cleaner functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import platform
import multiprocessing

from mpv_scraper.video_cleaner_parallel import (
    ParallelOptimizationTask,
    optimize_single_file_worker,
    get_optimal_worker_count,
    parallel_optimize_videos,
    estimate_parallel_processing_time,
)


class TestParallelOptimizationTask:
    """Test ParallelOptimizationTask dataclass."""

    def test_parallel_optimization_task_creation(self):
        """Test creating ParallelOptimizationTask with valid parameters."""
        task = ParallelOptimizationTask(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_optimized.mp4"),
            preset_name="test_preset",
            preset_config={
                "name": "test_preset",
                "target_codec": "libx264",
                "target_profile": "high",
                "target_bitrate": 1500000,
                "target_resolution": (1280, 720),
                "crf": 23,
                "preset": "faster",
                "tune": "film",
                "audio_codec": "aac",
                "audio_bitrate": 128000,
                "timeout": 1800
            }
        )
        
        assert task.input_path == Path("/test/input.mp4")
        assert task.output_path == Path("/test/output_optimized.mp4")
        assert task.preset_name == "test_preset"
        assert task.preset_config["name"] == "test_preset"
        assert task.preset_config["target_codec"] == "libx264"
        assert task.preset_config["target_profile"] == "high"
        assert task.preset_config["target_bitrate"] == 1500000
        assert task.preset_config["target_resolution"] == (1280, 720)
        assert task.preset_config["crf"] == 23
        assert task.preset_config["preset"] == "faster"
        assert task.preset_config["tune"] == "film"
        assert task.preset_config["audio_codec"] == "aac"
        assert task.preset_config["audio_bitrate"] == 128000
        assert task.preset_config["timeout"] == 1800


class TestOptimizeSingleFileWorker:
    """Test single file optimization worker."""

    @patch('mpv_scraper.video_cleaner_parallel.subprocess.run')
    def test_optimize_single_file_worker_success_hardware(self, mock_run):
        """Test successful optimization with hardware acceleration."""
        mock_run.return_value = Mock(returncode=0)
        
        task = ParallelOptimizationTask(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_optimized.mp4"),
            preset_config={
                "name": "test_preset",
                "target_codec": "libx264",
                "target_profile": "high",
                "target_bitrate": 1500000,
                "target_resolution": (1280, 720),
                "crf": 23,
                "preset": "faster",
                "tune": "film",
                "audio_codec": "aac",
                "audio_bitrate": 128000,
                "timeout": 1800
            }
        )
        
        result = optimize_single_file_worker(task)
        
        assert result[0] == Path("/test/input.mp4")
        assert result[1] is True
        assert "Hardware acceleration" in result[2]
        mock_run.assert_called_once()
        
        # Check that hardware encoder was used
        call_args = mock_run.call_args[0][0]
        args_str = " ".join(call_args)
        assert "-c:v h264_videotoolbox" in args_str

    @patch('mpv_scraper.video_cleaner_parallel.subprocess.run')
    def test_optimize_single_file_worker_success_software(self, mock_run):
        """Test successful optimization with software encoding (hardware fallback)."""
        # First call fails (hardware not available), second succeeds (software)
        mock_run.side_effect = [
            Mock(returncode=1, stderr=b"Hardware encoder not available"),
            Mock(returncode=0)
        ]
        
        task = ParallelOptimizationTask(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_optimized.mp4"),
            preset_config={
                "name": "test_preset",
                "target_codec": "libx264",
                "target_profile": "high",
                "target_bitrate": 1500000,
                "target_resolution": (1280, 720),
                "crf": 23,
                "preset": "faster",
                "tune": "film",
                "audio_codec": "aac",
                "audio_bitrate": 128000,
                "timeout": 1800
            }
        )
        
        result = optimize_single_file_worker(task)
        
        assert result[0] == Path("/test/input.mp4")
        assert result[1] is True
        assert "Software encoding" in result[2]
        assert mock_run.call_count == 2
        
        # Check that software encoder was used on second attempt
        second_call_args = mock_run.call_args_list[1][0][0]
        args_str = " ".join(second_call_args)
        assert "-c:v libx264" in args_str

    @patch('mpv_scraper.video_cleaner_parallel.subprocess.run')
    def test_optimize_single_file_worker_failure(self, mock_run):
        """Test optimization failure."""
        mock_run.return_value = Mock(returncode=1, stderr=b"Optimization failed")
        
        task = ParallelOptimizationTask(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_optimized.mp4"),
            preset_config={
                "name": "test_preset",
                "target_codec": "libx264",
                "target_profile": "high",
                "target_bitrate": 1500000,
                "target_resolution": (1280, 720),
                "crf": 23,
                "preset": "faster",
                "tune": "film",
                "audio_codec": "aac",
                "audio_bitrate": 128000,
                "timeout": 1800
            }
        )
        
        result = optimize_single_file_worker(task)
        
        assert result[0] == Path("/test/input.mp4")
        assert result[1] is False
        assert "Optimization failed" in result[2]

    @patch('mpv_scraper.video_cleaner_parallel.subprocess.run')
    def test_optimize_single_file_worker_timeout(self, mock_run):
        """Test optimization timeout."""
        mock_run.side_effect = TimeoutError("Process timed out")
        
        task = ParallelOptimizationTask(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_optimized.mp4"),
            preset_config={
                "name": "test_preset",
                "target_codec": "libx264",
                "target_profile": "high",
                "target_bitrate": 1500000,
                "target_resolution": (1280, 720),
                "crf": 23,
                "preset": "faster",
                "tune": "film",
                "audio_codec": "aac",
                "audio_bitrate": 128000,
                "timeout": 1800
            }
        )
        
        result = optimize_single_file_worker(task)
        
        assert result[0] == Path("/test/input.mp4")
        assert result[1] is False
        assert "timeout" in result[2].lower()

    @patch('mpv_scraper.video_cleaner_parallel.subprocess.run')
    def test_optimize_single_file_worker_overwrite_zero_byte(self, mock_run):
        """Test overwriting zero-byte output files."""
        # First call creates zero-byte file, second call succeeds
        mock_run.side_effect = [
            Mock(returncode=0),  # Creates zero-byte file
            Mock(returncode=0)   # Successful retry
        ]
        
        task = ParallelOptimizationTask(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_optimized.mp4"),
            preset_config={
                "name": "test_preset",
                "target_codec": "libx264",
                "target_profile": "high",
                "target_bitrate": 1500000,
                "target_resolution": (1280, 720),
                "crf": 23,
                "preset": "faster",
                "tune": "film",
                "audio_codec": "aac",
                "audio_bitrate": 128000,
                "timeout": 1800
            }
        )
        
        # Mock zero-byte file
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=0)
            
            result = optimize_single_file_worker(task)
        
        assert result[0] == Path("/test/input.mp4")
        assert result[1] is True
        assert mock_run.call_count == 2

    @patch('mpv_scraper.video_cleaner_parallel.subprocess.run')
    def test_optimize_single_file_worker_ffmpeg_parameters(self, mock_run):
        """Test that FFmpeg parameters are correctly set."""
        mock_run.return_value = Mock(returncode=0)
        
        task = ParallelOptimizationTask(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_optimized.mp4"),
            preset_config={
                "name": "test_preset",
                "target_codec": "libx264",
                "target_profile": "high",
                "target_bitrate": 1500000,
                "target_resolution": (1280, 720),
                "crf": 23,
                "preset": "faster",
                "tune": "film",
                "audio_codec": "aac",
                "audio_bitrate": 128000,
                "timeout": 1800
            }
        )
        
        optimize_single_file_worker(task)
        
        call_args = mock_run.call_args[0][0]
        args_str = " ".join(call_args)
        
        # Check essential parameters
        assert "-c:v h264_videotoolbox" in args_str or "-c:v libx264" in args_str
        assert "-profile:v high" in args_str
        assert "-crf 23" in args_str
        assert "-preset faster" in args_str
        assert "-tune film" in args_str
        assert "-pix_fmt yuv420p" in args_str
        assert "-c:a aac" in args_str
        assert "-b:a 128k" in args_str


class TestGetOptimalWorkerCount:
    """Test optimal worker count calculation."""

    @patch('multiprocessing.cpu_count')
    def test_get_optimal_worker_count(self, mock_cpu_count):
        """Test optimal worker count calculation."""
        mock_cpu_count.return_value = 8
        
        worker_count = get_optimal_worker_count()
        
        # Should be CPU count - 1, but at least 1
        assert worker_count == 7

    @patch('multiprocessing.cpu_count')
    def test_get_optimal_worker_count_single_core(self, mock_cpu_count):
        """Test optimal worker count with single core."""
        mock_cpu_count.return_value = 1
        
        worker_count = get_optimal_worker_count()
        
        # Should be at least 1
        assert worker_count == 1

    @patch('multiprocessing.cpu_count')
    def test_get_optimal_worker_count_high_core_count(self, mock_cpu_count):
        """Test optimal worker count with high core count."""
        mock_cpu_count.return_value = 32
        
        worker_count = get_optimal_worker_count()
        
        # Should be CPU count - 1
        assert worker_count == 31


class TestParallelOptimizeVideos:
    """Test parallel video optimization."""

    @patch('mpv_scraper.video_cleaner_parallel.ProcessPoolExecutor')
    @patch('mpv_scraper.video_cleaner_parallel.get_optimal_worker_count')
    def test_parallel_optimize_videos_success(self, mock_worker_count, mock_executor):
        """Test successful parallel optimization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test video files
            test_video1 = temp_path / "video1.mp4"
            test_video2 = temp_path / "video2.mp4"
            test_video1.touch()
            test_video2.touch()
            
            # Mock worker count
            mock_worker_count.return_value = 2
            
            # Mock executor context manager
            mock_executor_instance = Mock()
            mock_executor.return_value.__enter__ = Mock(return_value=mock_executor_instance)
            mock_executor.return_value.__exit__ = Mock(return_value=None)
            
            # Mock futures
            future1 = Mock()
            future2 = Mock()
            future1.result.return_value = (test_video1, True, "Success")
            future2.result.return_value = (test_video2, True, "Success")
            
            # Mock submit to return futures
            mock_executor_instance.submit.side_effect = [future1, future2]
            
            # Mock as_completed to return the futures in order
            with patch('mpv_scraper.video_cleaner_parallel.as_completed') as mock_as_completed:
                mock_as_completed.return_value = [future1, future2]
                
                result = parallel_optimize_videos(
                    directory=temp_path,
                    preset_config={
                        "name": "test_preset",
                        "target_codec": "libx264",
                        "target_profile": "high",
                        "target_bitrate": 1500000,
                        "target_resolution": (1280, 720),
                        "crf": 23,
                        "preset": "faster",
                        "tune": "film",
                        "audio_codec": "aac",
                        "audio_bitrate": 128000,
                        "timeout": 1800
                    },
                    max_workers=2
                )
            
            assert result[0] == 2  # total
            assert result[1] == 2  # successful
            assert result[2] == []  # errors

    @patch('mpv_scraper.video_cleaner_parallel.ProcessPoolExecutor')
    @patch('mpv_scraper.video_cleaner_parallel.get_optimal_worker_count')
    def test_parallel_optimize_videos_partial_failure(self, mock_worker_count, mock_executor):
        """Test parallel optimization with some failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test video files
            test_video1 = temp_path / "video1.mp4"
            test_video2 = temp_path / "video2.mp4"
            test_video1.touch()
            test_video2.touch()
            
            # Mock worker count
            mock_worker_count.return_value = 2
            
            # Mock executor context manager
            mock_executor_instance = Mock()
            mock_executor.return_value.__enter__ = Mock(return_value=mock_executor_instance)
            mock_executor.return_value.__exit__ = Mock(return_value=None)
            
            # Mock futures: first succeeds, second fails
            future1 = Mock()
            future2 = Mock()
            future1.result.return_value = (test_video1, True, "Success")
            future2.result.return_value = (test_video2, False, "Failed")
            
            mock_executor_instance.submit.side_effect = [future1, future2]
            
            # Mock as_completed
            with patch('mpv_scraper.video_cleaner_parallel.as_completed') as mock_as_completed:
                mock_as_completed.return_value = [future1, future2]
                
                result = parallel_optimize_videos(
                    directory=temp_path,
                    preset_config={
                        "name": "test_preset",
                        "target_codec": "libx264",
                        "target_profile": "high",
                        "target_bitrate": 1500000,
                        "target_resolution": (1280, 720),
                        "crf": 23,
                        "preset": "faster",
                        "tune": "film",
                        "audio_codec": "aac",
                        "audio_bitrate": 128000,
                        "timeout": 1800
                    },
                    max_workers=2
                )
            
            assert result[0] == 2  # total
            assert result[1] == 1  # successful
            assert len(result[2]) == 1  # errors

    @patch('mpv_scraper.video_cleaner_parallel.ProcessPoolExecutor')
    @patch('mpv_scraper.video_cleaner_parallel.get_optimal_worker_count')
    def test_parallel_optimize_videos_exception(self, mock_worker_count, mock_executor):
        """Test parallel optimization with exceptions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test video file
            test_video = temp_path / "video1.mp4"
            test_video.touch()
            
            # Mock worker count
            mock_worker_count.return_value = 1
            
            # Mock executor context manager
            mock_executor_instance = Mock()
            mock_executor.return_value.__enter__ = Mock(return_value=mock_executor_instance)
            mock_executor.return_value.__exit__ = Mock(return_value=None)
            
            # Mock future that raises exception
            future = Mock()
            future.result.side_effect = Exception("Processing failed")
            
            mock_executor_instance.submit.return_value = future
            
            # Mock as_completed
            with patch('mpv_scraper.video_cleaner_parallel.as_completed') as mock_as_completed:
                mock_as_completed.return_value = [future]
                
                result = parallel_optimize_videos(
                    directory=temp_path,
                    preset_config={
                        "name": "test_preset",
                        "target_codec": "libx264",
                        "target_profile": "high",
                        "target_bitrate": 1500000,
                        "target_resolution": (1280, 720),
                        "crf": 23,
                        "preset": "faster",
                        "tune": "film",
                        "audio_codec": "aac",
                        "audio_bitrate": 128000,
                        "timeout": 1800
                    },
                    max_workers=1
                )
            
            assert result[0] == 1  # total
            assert result[1] == 0  # successful
            assert len(result[2]) == 1  # errors

    @patch('mpv_scraper.video_cleaner_parallel.ProcessPoolExecutor')
    def test_parallel_optimize_videos_no_videos(self, mock_executor):
        """Test parallel optimization with no video files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock executor context manager (shouldn't be called)
            mock_executor_instance = Mock()
            mock_executor.return_value.__enter__ = Mock(return_value=mock_executor_instance)
            mock_executor.return_value.__exit__ = Mock(return_value=None)
            
            result = parallel_optimize_videos(
                directory=temp_path,
                preset_config={
                    "name": "test_preset",
                    "target_codec": "libx264",
                    "target_profile": "high",
                    "target_bitrate": 1500000,
                    "target_resolution": (1280, 720),
                    "crf": 23,
                    "preset": "faster",
                    "tune": "film",
                    "audio_codec": "aac",
                    "audio_bitrate": 128000,
                    "timeout": 1800
                }
            )
            
            assert result[0] == 0  # total
            assert result[1] == 0  # successful
            assert result[2] == []  # errors
            # Should not have called submit since no files
            mock_executor_instance.submit.assert_not_called()

    @patch('mpv_scraper.video_cleaner_parallel.ProcessPoolExecutor')
    @patch('mpv_scraper.video_cleaner_parallel.get_optimal_worker_count')
    def test_parallel_optimize_videos_skip_existing(self, mock_worker_count, mock_executor):
        """Test that existing optimized files are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create original and optimized files
            original_video = temp_path / "video1.mp4"
            optimized_video = temp_path / "video1_optimized.mp4"
            original_video.touch()
            optimized_video.touch()
            
            result = parallel_optimize_videos(
                directory=temp_path,
                preset_config={
                    "name": "test_preset",
                    "target_codec": "libx264",
                    "target_profile": "high",
                    "target_bitrate": 1500000,
                    "target_resolution": (1280, 720),
                    "crf": 23,
                    "preset": "faster",
                    "tune": "film",
                    "audio_codec": "aac",
                    "audio_bitrate": 128000,
                    "timeout": 1800
                }
            )
            
            # Should skip existing optimized file
            assert result[0] == 1  # total
            assert result[1] == 0  # successful
            assert result[2] == []  # errors

    @patch('mpv_scraper.video_cleaner_parallel.ProcessPoolExecutor')
    @patch('mpv_scraper.video_cleaner_parallel.get_optimal_worker_count')
    def test_parallel_optimize_videos_replace_originals(self, mock_worker_count, mock_executor):
        """Test replacing original files after successful optimization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test video file
            test_video = temp_path / "video1.mp4"
            test_video.touch()
            
            # Mock worker count
            mock_worker_count.return_value = 1
            
            # Mock executor and futures
            mock_executor_instance = Mock()
            mock_executor.return_value.__enter__.return_value = mock_executor_instance
            
            # Mock successful future
            future = Mock()
            future.result.return_value = (test_video, True, "Success")
            
            mock_executor_instance.submit.return_value = future
            
            # Mock as_completed
            with patch('mpv_scraper.video_cleaner_parallel.as_completed') as mock_as_completed:
                mock_as_completed.return_value = [future]
                
                # Mock optimized file exists and is valid
                with patch('pathlib.Path.exists', return_value=True), \
                     patch('pathlib.Path.stat') as mock_stat, \
                     patch('pathlib.Path.unlink') as mock_unlink:
                    mock_stat.return_value = Mock(st_size=1024 * 1024)  # 1MB
                    
                    result = parallel_optimize_videos(
                        directory=temp_path,
                        preset_config={
                            "name": "test_preset",
                            "target_codec": "libx264",
                            "target_profile": "high",
                            "target_bitrate": 1500000,
                            "target_resolution": (1280, 720),
                            "crf": 23,
                            "preset": "faster",
                            "tune": "film",
                            "audio_codec": "aac",
                            "audio_bitrate": 128000,
                            "timeout": 1800
                        },
                        max_workers=1,
                        replace_originals=True
                    )
                
                assert result[0] == 1  # total
                assert result[1] == 1  # successful
                assert result[2] == []  # errors
                mock_unlink.assert_called_once()  # Original file should be deleted

    @patch('mpv_scraper.video_cleaner_parallel.ProcessPoolExecutor')
    def test_parallel_optimize_videos_skip_apple_double_files(self, mock_executor):
        """Test that AppleDouble files (._) are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create regular video and AppleDouble video files
            regular_video = temp_path / "video1.mp4"
            apple_double_video = temp_path / "._video1.mp4"
            regular_video.touch()
            apple_double_video.touch()
            
            # Mock executor context manager
            mock_executor_instance = Mock()
            mock_executor.return_value.__enter__ = Mock(return_value=mock_executor_instance)
            mock_executor.return_value.__exit__ = Mock(return_value=None)
            
            # Mock future
            future = Mock()
            future.result.return_value = (regular_video, True, "Success")
            mock_executor_instance.submit.return_value = future
            
            # Mock as_completed
            with patch('mpv_scraper.video_cleaner_parallel.as_completed') as mock_as_completed:
                mock_as_completed.return_value = [future]
                
                result = parallel_optimize_videos(
                    directory=temp_path,
                    preset_config={
                        "name": "test_preset",
                        "target_codec": "libx264",
                        "target_profile": "high",
                        "target_bitrate": 1500000,
                        "target_resolution": (1280, 720),
                        "crf": 23,
                        "preset": "faster",
                        "tune": "film",
                        "audio_codec": "aac",
                        "audio_bitrate": 128000,
                        "timeout": 1800
                    }
                )
            
            # Should only process regular video file
            assert result[0] == 1  # total
            assert result[1] == 1  # successful
            assert result[2] == []  # errors


class TestEstimateParallelProcessingTime:
    """Test parallel processing time estimation."""

    def test_estimate_parallel_processing_time(self):
        """Test time estimation calculation."""
        # 10 files, 2 minutes per file, 4 workers
        estimated_time = estimate_parallel_processing_time(10, 2.0, 4)
        
        # Should be roughly (10 * 2) / 4 = 5 minutes
        assert estimated_time == "5.0 minutes"

    def test_estimate_parallel_processing_time_single_worker(self):
        """Test time estimation with single worker."""
        # 5 files, 3 minutes per file, 1 worker
        estimated_time = estimate_parallel_processing_time(5, 3.0, 1)
        
        # Should be 5 * 3 = 15 minutes
        assert estimated_time == "15.0 minutes"

    def test_estimate_parallel_processing_time_high_worker_count(self):
        """Test time estimation with high worker count."""
        # 20 files, 1 minute per file, 10 workers
        estimated_time = estimate_parallel_processing_time(20, 1.0, 10)
        
        # Should be roughly (20 * 1) / 10 = 2 minutes
        assert estimated_time == "2.0 minutes"

    def test_estimate_parallel_processing_time_fractional_result(self):
        """Test time estimation with fractional result."""
        # 7 files, 1.5 minutes per file, 3 workers
        estimated_time = estimate_parallel_processing_time(7, 1.5, 3)
        
        # Should be roughly (7 * 1.5) / 3 = 3.5 minutes
        assert estimated_time == "3.5 minutes"
