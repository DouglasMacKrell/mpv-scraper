"""
Tests for video processing CLI commands.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from click.testing import CliRunner

from mpv_scraper.cli import main


class TestCropCommand:
    """Test crop command functionality."""

    def test_crop_command_help(self):
        """Test crop command help output."""
        runner = CliRunner()
        result = runner.invoke(main, ['crop', '--help'])
        assert result.exit_code == 0
        assert "Crop videos to 4:3 aspect ratio" in result.output

    @patch('mpv_scraper.video_crop.batch_crop_videos_to_4_3')
    def test_crop_command_success(self, mock_batch_crop):
        """Test successful crop command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock successful cropping
            mock_batch_crop.return_value = {
                "total": 2,
                "successful": 2,
                "failed": 0,
                "errors": []
            }
            
            runner = CliRunner()
            result = runner.invoke(main, ['crop', str(temp_path), '--quality', 'medium'])
            
            assert result.exit_code == 0
            assert "2 videos cropped successfully" in result.output
            mock_batch_crop.assert_called_once_with(temp_path, "medium", overwrite=False)

    @patch('mpv_scraper.video_crop.batch_crop_videos_to_4_3')
    def test_crop_command_partial_failure(self, mock_batch_crop):
        """Test crop command with partial failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock partial failure
            mock_batch_crop.return_value = {
                "total": 3,
                "successful": 2,
                "failed": 1,
                "errors": ["Failed to crop video1.mp4"]
            }
            
            runner = CliRunner()
            result = runner.invoke(main, ['crop', str(temp_path), '--quality', 'high'])
            
            assert result.exit_code == 0
            assert "2/3 videos cropped successfully" in result.output
            assert "1 failed" in result.output

    @patch('mpv_scraper.video_crop.batch_crop_videos_to_4_3')
    def test_crop_command_overwrite(self, mock_batch_crop):
        """Test crop command with overwrite flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            mock_batch_crop.return_value = {
                "total": 1,
                "successful": 1,
                "failed": 0,
                "errors": []
            }
            
            runner = CliRunner()
            result = runner.invoke(main, ['crop', str(temp_path), '--overwrite'])
            
            assert result.exit_code == 0
            mock_batch_crop.assert_called_once_with(temp_path, "medium", overwrite=True)

    def test_crop_command_invalid_quality(self):
        """Test crop command with invalid quality option."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            runner = CliRunner()
            result = runner.invoke(main, ['crop', str(temp_path), '--quality', 'invalid'])
            
            assert result.exit_code != 0
            assert "Invalid value" in result.output

    def test_crop_command_dry_run(self):
        """Test crop command with dry run flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            runner = CliRunner()
            result = runner.invoke(main, ['crop', str(temp_path), '--dry-run'])
            
            assert result.exit_code == 0
            assert "DRY RUN" in result.output


class TestConvertCommands:
    """Test convert command functionality."""

    def test_convert_with_subs_command_help(self):
        """Test convert-with-subs command help output."""
        runner = CliRunner()
        result = runner.invoke(main, ['convert-with-subs', '--help'])
        assert result.exit_code == 0
        assert "Convert MKV to MP4 with subtitles" in result.output

    def test_convert_without_subs_command_help(self):
        """Test convert-without-subs command help output."""
        runner = CliRunner()
        result = runner.invoke(main, ['convert-without-subs', '--help'])
        assert result.exit_code == 0
        assert "Convert MKV to MP4 without subtitles" in result.output

    @patch('mpv_scraper.video_convert.batch_convert_mkv_to_mp4')
    def test_convert_with_subs_success(self, mock_batch_convert):
        """Test successful convert-with-subs command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock successful conversion
            mock_batch_convert.return_value = {
                "total": 3,
                "successful": 3,
                "failed": 0,
                "errors": []
            }
            
            runner = CliRunner()
            result = runner.invoke(main, ['convert-with-subs', str(temp_path)])
            
            assert result.exit_code == 0
            assert "3 videos converted successfully" in result.output
            mock_batch_convert.assert_called_once()

    @patch('mpv_scraper.video_convert.batch_convert_mkv_to_mp4')
    def test_convert_without_subs_success(self, mock_batch_convert):
        """Test successful convert-without-subs command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock successful conversion
            mock_batch_convert.return_value = {
                "total": 2,
                "successful": 2,
                "failed": 0,
                "errors": []
            }
            
            runner = CliRunner()
            result = runner.invoke(main, ['convert-without-subs', str(temp_path)])
            
            assert result.exit_code == 0
            assert "2 videos converted successfully" in result.output
            mock_batch_convert.assert_called_once()

    @patch('mpv_scraper.video_convert.batch_convert_mkv_to_mp4')
    def test_convert_commands_overwrite(self, mock_batch_convert):
        """Test convert commands with overwrite flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            mock_batch_convert.return_value = {
                "total": 1,
                "successful": 1,
                "failed": 0,
                "errors": []
            }
            
            runner = CliRunner()
            
            # Test convert-with-subs with overwrite
            result = runner.invoke(main, ['convert-with-subs', str(temp_path), '--overwrite'])
            assert result.exit_code == 0
            calls = mock_batch_convert.call_args_list
            assert len(calls) == 1
            assert calls[0][1]['overwrite'] is True
            
            # Test convert-without-subs with overwrite
            result = runner.invoke(main, ['convert-without-subs', str(temp_path), '--overwrite'])
            assert result.exit_code == 0
            calls = mock_batch_convert.call_args_list
            assert len(calls) == 2
            assert calls[1][1]['overwrite'] is True

    def test_convert_commands_dry_run(self):
        """Test convert commands with dry run flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            runner = CliRunner()
            
            # Test convert-with-subs dry run
            result = runner.invoke(main, ['convert-with-subs', str(temp_path), '--dry-run'])
            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            
            # Test convert-without-subs dry run
            result = runner.invoke(main, ['convert-without-subs', str(temp_path), '--dry-run'])
            assert result.exit_code == 0
            assert "DRY RUN" in result.output


class TestAnalyzeCommand:
    """Test analyze command functionality."""

    def test_analyze_command_help(self):
        """Test analyze command help output."""
        runner = CliRunner()
        result = runner.invoke(main, ['analyze', '--help'])
        assert result.exit_code == 0
        assert "Analyze videos for handheld compatibility" in result.output

    @patch('mpv_scraper.video_cleaner.batch_analyze_videos')
    def test_analyze_command_success(self, mock_batch_analyze):
        """Test successful analyze command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock analysis results
            from mpv_scraper.video_cleaner import VideoAnalysis
            
            mock_batch_analyze.return_value = [
                VideoAnalysis(
                    file_path=temp_path / "video1.mp4",
                    codec="hevc",
                    resolution=(1920, 1080),
                    bitrate=6000000,
                    pixel_format="yuv420p10le",
                    file_size_mb=1024,
                    optimization_score=0.95,
                    issues=["HEVC codec", "10-bit color", "High bitrate"]
                ),
                VideoAnalysis(
                    file_path=temp_path / "video2.mp4",
                    codec="h264",
                    resolution=(1280, 720),
                    bitrate=1500000,
                    pixel_format="yuv420p",
                    file_size_mb=200,
                    optimization_score=0.2,
                    issues=[]
                )
            ]
            
            runner = CliRunner()
            result = runner.invoke(main, ['analyze', str(temp_path)])
            
            assert result.exit_code == 0
            assert "Found 2 video files to analyze" in result.output
            assert "HEVC codec" in result.output
            assert "10-bit color" in result.output
            assert "High bitrate" in result.output
            mock_batch_analyze.assert_called_once_with(temp_path)

    def test_analyze_command_dry_run(self):
        """Test analyze command with dry run flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            runner = CliRunner()
            result = runner.invoke(main, ['analyze', str(temp_path), '--dry-run'])
            
            assert result.exit_code == 0
            assert "DRY RUN" in result.output


class TestOptimizeCommands:
    """Test optimize command functionality."""

    def test_optimize_command_help(self):
        """Test optimize command help output."""
        runner = CliRunner()
        result = runner.invoke(main, ['optimize', '--help'])
        assert result.exit_code == 0
        assert "Optimize videos for handheld devices" in result.output

    def test_optimize_parallel_command_help(self):
        """Test optimize-parallel command help output."""
        runner = CliRunner()
        result = runner.invoke(main, ['optimize-parallel', '--help'])
        assert result.exit_code == 0
        assert "Optimize videos using parallel processing" in result.output

    @patch('mpv_scraper.video_cleaner.batch_optimize_videos')
    def test_optimize_command_success(self, mock_batch_optimize):
        """Test successful optimize command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock successful optimization
            mock_batch_optimize.return_value = {
                "total": 4,
                "successful": 4,
                "failed": 0,
                "errors": []
            }
            
            runner = CliRunner()
            result = runner.invoke(main, ['optimize', str(temp_path), '--preset', 'handheld'])
            
            assert result.exit_code == 0
            assert "4 videos optimized successfully" in result.output
            mock_batch_optimize.assert_called_once()

    @patch('mpv_scraper.video_cleaner_parallel.parallel_optimize_videos')
    @patch('mpv_scraper.video_cleaner_parallel.get_optimal_worker_count')
    def test_optimize_parallel_command_success(self, mock_worker_count, mock_parallel_optimize):
        """Test successful optimize-parallel command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock worker count
            mock_worker_count.return_value = 4
            
            # Mock successful parallel optimization
            mock_parallel_optimize.return_value = (5, 5, [])
            
            runner = CliRunner()
            result = runner.invoke(main, ['optimize-parallel', str(temp_path), '--preset', 'handheld'])
            
            assert result.exit_code == 0
            assert "Auto-detected optimal worker count: 4" in result.output
            assert "5/5 videos optimized successfully" in result.output
            mock_parallel_optimize.assert_called_once()

    @patch('mpv_scraper.video_cleaner_parallel.parallel_optimize_videos')
    def test_optimize_parallel_command_custom_workers(self, mock_parallel_optimize):
        """Test optimize-parallel command with custom worker count."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock successful parallel optimization
            mock_parallel_optimize.return_value = (3, 3, [])
            
            runner = CliRunner()
            result = runner.invoke(main, ['optimize-parallel', str(temp_path), '--workers', '8'])
            
            assert result.exit_code == 0
            assert "Using 8 workers" in result.output
            assert "3/3 videos optimized successfully" in result.output
            mock_parallel_optimize.assert_called_once()

    @patch('mpv_scraper.video_cleaner_parallel.parallel_optimize_videos')
    @patch('mpv_scraper.video_cleaner_parallel.get_optimal_worker_count')
    def test_optimize_parallel_command_replace_originals(self, mock_worker_count, mock_parallel_optimize):
        """Test optimize-parallel command with replace-originals flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock worker count
            mock_worker_count.return_value = 2
            
            # Mock successful parallel optimization
            mock_parallel_optimize.return_value = (2, 2, [])
            
            runner = CliRunner()
            result = runner.invoke(main, [
                'optimize-parallel', 
                str(temp_path), 
                '--preset', 'handheld',
                '--replace-originals'
            ])
            
            assert result.exit_code == 0
            assert "WARNING: --replace-originals flag is enabled!" in result.output
            assert "Original files will be PERMANENTLY DELETED" in result.output
            assert "2/2 videos optimized successfully" in result.output
            
            # Check that replace_originals was passed to parallel_optimize_videos
            call_args = mock_parallel_optimize.call_args
            assert call_args[1]['replace_originals'] is True

    def test_optimize_commands_invalid_preset(self):
        """Test optimize commands with invalid preset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            runner = CliRunner()
            
            # Test optimize command
            result = runner.invoke(main, ['optimize', str(temp_path), '--preset', 'invalid'])
            assert result.exit_code != 0
            assert "Invalid value" in result.output
            
            # Test optimize-parallel command
            result = runner.invoke(main, ['optimize-parallel', str(temp_path), '--preset', 'invalid'])
            assert result.exit_code != 0
            assert "Invalid value" in result.output

    def test_optimize_commands_dry_run(self):
        """Test optimize commands with dry run flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            runner = CliRunner()
            
            # Test optimize command dry run
            result = runner.invoke(main, ['optimize', str(temp_path), '--dry-run'])
            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            
            # Test optimize-parallel command dry run
            result = runner.invoke(main, ['optimize-parallel', str(temp_path), '--dry-run'])
            assert result.exit_code == 0
            assert "DRY RUN" in result.output

    @patch('mpv_scraper.video_cleaner_parallel.parallel_optimize_videos')
    @patch('mpv_scraper.video_cleaner_parallel.get_optimal_worker_count')
    def test_optimize_parallel_command_compatibility_preset(self, mock_worker_count, mock_parallel_optimize):
        """Test optimize-parallel command with compatibility preset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock worker count
            mock_worker_count.return_value = 3
            
            # Mock successful parallel optimization
            mock_parallel_optimize.return_value = (1, 1, [])
            
            runner = CliRunner()
            result = runner.invoke(main, ['optimize-parallel', str(temp_path), '--preset', 'compatibility'])
            
            assert result.exit_code == 0
            assert "1/1 videos optimized successfully" in result.output
            
            # Check that compatibility preset was used
            call_args = mock_parallel_optimize.call_args
            preset_config = call_args[1]['preset_config']
            assert preset_config['name'] == 'compatibility_optimized'
            assert preset_config['target_profile'] == 'baseline'
            assert preset_config['target_resolution'] == (854, 480)
            assert preset_config['crf'] == 28


class TestCommandIntegration:
    """Test integration between video processing commands."""

    def test_all_video_commands_exist(self):
        """Test that all video processing commands are available."""
        runner = CliRunner()
        
        # Test that all commands are recognized
        commands = ['crop', 'convert-with-subs', 'convert-without-subs', 'analyze', 'optimize', 'optimize-parallel']
        
        for command in commands:
            result = runner.invoke(main, [command, '--help'])
            assert result.exit_code == 0, f"Command '{command}' not found or has invalid help"

    def test_command_argument_validation(self):
        """Test command argument validation."""
        runner = CliRunner()
        
        # Test invalid paths
        result = runner.invoke(main, ['crop', '/nonexistent/path'])
        assert result.exit_code != 0
        assert "does not exist" in result.output
        
        result = runner.invoke(main, ['analyze', '/nonexistent/path'])
        assert result.exit_code != 0
        assert "does not exist" in result.output
        
        result = runner.invoke(main, ['optimize', '/nonexistent/path'])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_command_option_consistency(self):
        """Test that common options are consistent across commands."""
        runner = CliRunner()
        
        # Test that all commands support --dry-run
        commands = ['crop', 'convert-with-subs', 'convert-without-subs', 'analyze', 'optimize', 'optimize-parallel']
        
        for command in commands:
            result = runner.invoke(main, [command, '--help'])
            assert result.exit_code == 0
            assert "--dry-run" in result.output, f"Command '{command}' missing --dry-run option"
        
        # Test that relevant commands support --overwrite
        overwrite_commands = ['crop', 'convert-with-subs', 'convert-without-subs', 'optimize']
        
        for command in overwrite_commands:
            result = runner.invoke(main, [command, '--help'])
            assert result.exit_code == 0
            assert "--overwrite" in result.output, f"Command '{command}' missing --overwrite option"
