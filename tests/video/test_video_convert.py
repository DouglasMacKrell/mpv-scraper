"""
Tests for video conversion functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from mpv_scraper.video_convert import (
    ConversionPreset,
    VANILLA_WITH_SUBS,
    VANILLA_NO_SUBS,
    convert_mkv_to_mp4,
    batch_convert_mkv_to_mp4,
)


class TestConversionPreset:
    """Test ConversionPreset dataclass."""

    def test_conversion_preset_creation(self):
        """Test creating ConversionPreset with valid parameters."""
        preset = ConversionPreset(
            name="test_preset",
            video_codec="libx264",
            audio_codec="aac",
            subtitle_codec="mov_text",
            crf=24,
            preset="faster",
            tune="film",
            include_subtitles=True
        )
        
        assert preset.name == "test_preset"
        assert preset.video_codec == "libx264"
        assert preset.audio_codec == "aac"
        assert preset.subtitle_codec == "mov_text"
        assert preset.crf == 24
        assert preset.preset == "faster"
        assert preset.tune == "film"
        assert preset.include_subtitles is True

    def test_vanilla_with_subs_preset(self):
        """Test VANILLA_WITH_SUBS preset configuration."""
        assert VANILLA_WITH_SUBS.name == "vanilla_with_subs"
        assert VANILLA_WITH_SUBS.video_codec == "libx264"
        assert VANILLA_WITH_SUBS.audio_codec == "copy"
        assert VANILLA_WITH_SUBS.subtitle_codec == "mov_text"
        assert VANILLA_WITH_SUBS.crf == 24
        assert VANILLA_WITH_SUBS.preset == "faster"
        assert VANILLA_WITH_SUBS.tune == "film"
        assert VANILLA_WITH_SUBS.include_subtitles is True

    def test_vanilla_no_subs_preset(self):
        """Test VANILLA_NO_SUBS preset configuration."""
        assert VANILLA_NO_SUBS.name == "vanilla_no_subs"
        assert VANILLA_NO_SUBS.video_codec == "libx264"
        assert VANILLA_NO_SUBS.audio_codec == "copy"
        assert VANILLA_NO_SUBS.subtitle_codec is None
        assert VANILLA_NO_SUBS.crf == 24
        assert VANILLA_NO_SUBS.preset == "faster"
        assert VANILLA_NO_SUBS.tune == "animation"
        assert VANILLA_NO_SUBS.include_subtitles is False


class TestConvertMkvToMp4:
    """Test MKV to MP4 conversion."""

    @patch('mpv_scraper.video_convert.subprocess.run')
    def test_convert_mkv_success_with_subs(self, mock_run):
        """Test successful MKV conversion with subtitles."""
        mock_run.return_value = Mock(returncode=0)
        
        input_path = Path("/test/input.mkv")
        output_path = Path("/test/output.mp4")
        
        result = convert_mkv_to_mp4(input_path, output_path, VANILLA_WITH_SUBS)
        
        assert result is True
        mock_run.assert_called_once()
        
        # Check ffmpeg command
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args[0]
        assert "-i" in call_args
        assert str(input_path) in call_args
        assert str(output_path) in call_args
        assert "-map" in call_args
        assert "0" in call_args  # Map all streams
        assert "-c:s" in call_args
        assert "mov_text" in call_args

    @patch('mpv_scraper.video_convert.subprocess.run')
    def test_convert_mkv_success_without_subs(self, mock_run):
        """Test successful MKV conversion without subtitles."""
        mock_run.return_value = Mock(returncode=0)
        
        input_path = Path("/test/input.mkv")
        output_path = Path("/test/output.mp4")
        
        result = convert_mkv_to_mp4(input_path, output_path, VANILLA_NO_SUBS)
        
        assert result is True
        mock_run.assert_called_once()
        
        # Check ffmpeg command
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args[0]
        assert "-i" in call_args
        assert str(input_path) in call_args
        assert str(output_path) in call_args
        assert "-map" in call_args
        assert "0:v:0" in call_args  # Map video stream
        assert "0:a" in call_args    # Map audio streams
        assert "-sn" in call_args    # Skip subtitles

    @patch('mpv_scraper.video_convert.subprocess.run')
    def test_convert_mkv_failure(self, mock_run):
        """Test MKV conversion failure."""
        mock_run.return_value = Mock(returncode=1, stderr=b"Conversion failed")
        
        input_path = Path("/test/input.mkv")
        output_path = Path("/test/output.mp4")
        
        result = convert_mkv_to_mp4(input_path, output_path, VANILLA_WITH_SUBS)
        
        assert result is False

    @patch('mpv_scraper.video_convert.subprocess.run')
    def test_convert_mkv_timeout(self, mock_run):
        """Test MKV conversion timeout."""
        mock_run.side_effect = TimeoutError("Process timed out")
        
        input_path = Path("/test/input.mkv")
        output_path = Path("/test/output.mp4")
        
        result = convert_mkv_to_mp4(input_path, output_path, VANILLA_WITH_SUBS)
        
        assert result is False

    @patch('mpv_scraper.video_convert.subprocess.run')
    def test_convert_mkv_overwrite_existing(self, mock_run):
        """Test MKV conversion with overwrite."""
        mock_run.return_value = Mock(returncode=0)
        
        input_path = Path("/test/input.mkv")
        output_path = Path("/test/output.mp4")
        
        # Create existing output file
        with patch('pathlib.Path.exists', return_value=True):
            result = convert_mkv_to_mp4(input_path, output_path, VANILLA_WITH_SUBS, overwrite=True)
        
        assert result is True
        mock_run.assert_called_once()

    @patch('mpv_scraper.video_convert.subprocess.run')
    def test_convert_mkv_skip_existing(self, mock_run):
        """Test MKV conversion skipping existing file."""
        input_path = Path("/test/input.mkv")
        output_path = Path("/test/output.mp4")
        
        # Create existing output file
        with patch('pathlib.Path.exists', return_value=True):
            result = convert_mkv_to_mp4(input_path, output_path, VANILLA_WITH_SUBS, overwrite=False)
        
        assert result is True
        mock_run.assert_not_called()

    @patch('mpv_scraper.video_convert.subprocess.run')
    def test_convert_mkv_ffmpeg_parameters(self, mock_run):
        """Test that FFmpeg parameters are correctly set."""
        mock_run.return_value = Mock(returncode=0)
        
        input_path = Path("/test/input.mkv")
        output_path = Path("/test/output.mp4")
        
        convert_mkv_to_mp4(input_path, output_path, VANILLA_WITH_SUBS)
        
        call_args = mock_run.call_args[0][0]
        args_str = " ".join(call_args)
        
        # Check essential parameters
        assert "-c:v libx264" in args_str
        assert "-crf 24" in args_str
        assert "-preset faster" in args_str
        assert "-tune film" in args_str
        assert "-pix_fmt yuv420p" in args_str
        assert "-movflags +faststart" in args_str


class TestBatchConvertMkvToMp4:
    """Test batch MKV to MP4 conversion."""

    @patch('mpv_scraper.video_convert.convert_mkv_to_mp4')
    def test_batch_convert_success(self, mock_convert):
        """Test successful batch conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test MKV files
            test_mkv1 = temp_path / "video1.mkv"
            test_mkv2 = temp_path / "video2.mkv"
            test_mkv1.touch()
            test_mkv2.touch()
            
            mock_convert.return_value = True
            
            result = batch_convert_mkv_to_mp4(temp_path, VANILLA_WITH_SUBS)
            
            assert result["total"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert len(result["errors"]) == 0
            assert mock_convert.call_count == 2

    @patch('mpv_scraper.video_convert.convert_mkv_to_mp4')
    def test_batch_convert_partial_failure(self, mock_convert):
        """Test batch conversion with some failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test MKV files
            test_mkv1 = temp_path / "video1.mkv"
            test_mkv2 = temp_path / "video2.mkv"
            test_mkv1.touch()
            test_mkv2.touch()
            
            # Mock conversion: first succeeds, second fails
            mock_convert.side_effect = [True, False]
            
            result = batch_convert_mkv_to_mp4(temp_path, VANILLA_WITH_SUBS)
            
            assert result["total"] == 2
            assert result["successful"] == 1
            assert result["failed"] == 1
            assert len(result["errors"]) == 1

    @patch('mpv_scraper.video_convert.convert_mkv_to_mp4')
    def test_batch_convert_fallback_to_no_subs(self, mock_convert):
        """Test fallback from with-subs to without-subs on failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test MKV file
            test_mkv = temp_path / "video1.mkv"
            test_mkv.touch()
            
            # Mock conversion: with-subs fails, without-subs succeeds
            mock_convert.side_effect = [False, True]
            
            result = batch_convert_mkv_to_mp4(temp_path, VANILLA_WITH_SUBS)
            
            assert result["total"] == 1
            assert result["successful"] == 1
            assert result["failed"] == 0
            assert len(result["errors"]) == 0
            assert mock_convert.call_count == 2
            
            # Check that both presets were tried
            calls = mock_convert.call_args_list
            assert calls[0][0][2] == VANILLA_WITH_SUBS  # First call with subs
            assert calls[1][0][2] == VANILLA_NO_SUBS    # Second call without subs

    @patch('mpv_scraper.video_convert.convert_mkv_to_mp4')
    def test_batch_convert_both_presets_fail(self, mock_convert):
        """Test when both with-subs and without-subs fail."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test MKV file
            test_mkv = temp_path / "video1.mkv"
            test_mkv.touch()
            
            # Mock conversion: both presets fail
            mock_convert.return_value = False
            
            result = batch_convert_mkv_to_mp4(temp_path, VANILLA_WITH_SUBS)
            
            assert result["total"] == 1
            assert result["successful"] == 0
            assert result["failed"] == 1
            assert len(result["errors"]) == 1
            assert mock_convert.call_count == 2

    @patch('mpv_scraper.video_convert.convert_mkv_to_mp4')
    def test_batch_convert_no_fallback_for_no_subs_preset(self, mock_convert):
        """Test that no-subs preset doesn't trigger fallback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test MKV file
            test_mkv = temp_path / "video1.mkv"
            test_mkv.touch()
            
            # Mock conversion failure
            mock_convert.return_value = False
            
            result = batch_convert_mkv_to_mp4(temp_path, VANILLA_NO_SUBS)
            
            assert result["total"] == 1
            assert result["successful"] == 0
            assert result["failed"] == 1
            assert len(result["errors"]) == 1
            assert mock_convert.call_count == 1  # Only one attempt

    def test_batch_convert_no_mkv_files(self):
        """Test batch conversion with no MKV files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            result = batch_convert_mkv_to_mp4(temp_path, VANILLA_WITH_SUBS)
            
            assert result["total"] == 0
            assert result["successful"] == 0
            assert result["failed"] == 0
            assert len(result["errors"]) == 0

    def test_batch_convert_skip_existing(self):
        """Test that existing MP4 files are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create MKV and existing MP4 files
            mkv_file = temp_path / "video1.mkv"
            mp4_file = temp_path / "video1.mp4"
            mkv_file.touch()
            mp4_file.touch()
            
            with patch('mpv_scraper.video_convert.convert_mkv_to_mp4') as mock_convert:
                result = batch_convert_mkv_to_mp4(temp_path, VANILLA_WITH_SUBS, overwrite=False)
            
            # Should skip existing MP4 file
            assert result["total"] == 1
            assert result["successful"] == 0
            assert result["failed"] == 0
            assert len(result["errors"]) == 0
            mock_convert.assert_not_called()

    def test_batch_convert_overwrite_existing(self):
        """Test that existing MP4 files are overwritten when requested."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create MKV and existing MP4 files
            mkv_file = temp_path / "video1.mkv"
            mp4_file = temp_path / "video1.mp4"
            mkv_file.touch()
            mp4_file.touch()
            
            with patch('mpv_scraper.video_convert.convert_mkv_to_mp4') as mock_convert:
                mock_convert.return_value = True
                result = batch_convert_mkv_to_mp4(temp_path, VANILLA_WITH_SUBS, overwrite=True)
            
            # Should process existing MP4 file
            assert result["total"] == 1
            assert result["successful"] == 1
            assert result["failed"] == 0
            mock_convert.assert_called_once()

    def test_batch_convert_skip_apple_double_files(self):
        """Test that AppleDouble files (._) are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create regular MKV and AppleDouble MKV files
            regular_mkv = temp_path / "video1.mkv"
            apple_double_mkv = temp_path / "._video1.mkv"
            regular_mkv.touch()
            apple_double_mkv.touch()
            
            with patch('mpv_scraper.video_convert.convert_mkv_to_mp4') as mock_convert:
                mock_convert.return_value = True
                result = batch_convert_mkv_to_mp4(temp_path, VANILLA_WITH_SUBS)
            
            # Should only process regular MKV file
            assert result["total"] == 1
            assert result["successful"] == 1
            assert result["failed"] == 0
            mock_convert.assert_called_once()
            
            # Check that only regular file was processed
            call_args = mock_convert.call_args[0]
            assert call_args[0] == regular_mkv
