"""
Tests for video cropping functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from mpv_scraper.video_crop import (
    CropInfo,
    detect_letterboxing,
    crop_video_to_4_3,
    batch_crop_videos_to_4_3,
    get_video_info,
)


class TestCropInfo:
    """Test CropInfo dataclass."""

    def test_crop_info_creation(self):
        """Test creating CropInfo with valid parameters."""
        crop_info = CropInfo(
            width=1920,
            height=1080,
            crop_width=1440,
            crop_height=1080,
            crop_x=240,
            crop_y=0
        )
        
        assert crop_info.width == 1920
        assert crop_info.height == 1080
        assert crop_info.crop_width == 1440
        assert crop_info.crop_height == 1080
        assert crop_info.crop_x == 240
        assert crop_info.crop_y == 0
        assert crop_info.target_aspect == 4/3


class TestGetVideoInfo:
    """Test video information retrieval."""

    @patch('mpv_scraper.video_crop.subprocess.run')
    def test_get_video_info_success(self, mock_run):
        """Test successful video info retrieval."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=b'''{
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 1920,
                        "height": 1080,
                        "codec_name": "h264"
                    }
                ]
            }'''
        )
        
        result = get_video_info(Path("/test/video.mp4"))
        
        assert result["streams"][0]["width"] == 1920
        assert result["streams"][0]["height"] == 1080
        assert result["streams"][0]["codec_name"] == "h264"
        mock_run.assert_called_once()

    @patch('mpv_scraper.video_crop.subprocess.run')
    def test_get_video_info_failure(self, mock_run):
        """Test video info retrieval failure."""
        mock_run.return_value = Mock(returncode=1, stderr=b"File not found")
        
        with pytest.raises(RuntimeError, match="Failed to get video info"):
            get_video_info(Path("/test/nonexistent.mp4"))


class TestDetectLetterboxing:
    """Test letterboxing detection."""

    @patch('mpv_scraper.video_crop.subprocess.run')
    def test_detect_letterboxing_16x9_to_4x3(self, mock_run):
        """Test detecting letterboxing in 16:9 video with 4:3 content."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="1920,1080"
        )
        
        crop_info = detect_letterboxing(Path("/test/video.mp4"))
        
        assert crop_info.crop_width == 1440  # 1920 * 3/4
        assert crop_info.crop_height == 1080
        assert crop_info.crop_x == 240  # (1920 - 1440) / 2
        assert crop_info.crop_y == 0

    @patch('mpv_scraper.video_crop.subprocess.run')
    def test_detect_letterboxing_already_4x3(self, mock_run):
        """Test video that's already 4:3 aspect ratio."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="1440,1080"
        )
        
        crop_info = detect_letterboxing(Path("/test/video.mp4"))
        
        # Should return None if already 4:3
        assert crop_info is None

    @patch('mpv_scraper.video_crop.subprocess.run')
    def test_detect_letterboxing_vertical_letterboxing(self, mock_run):
        """Test video with vertical letterboxing (pillarboxing)."""
        mock_get_info.return_value = {
            "streams": [{"width": 1080, "height": 1920}]  # 9:16 aspect ratio
        }
        
        crop_info = detect_letterboxing(Path("/test/video.mp4"), "medium")
        
        # Should crop to 4:3 (1440x1080)
        assert crop_info.crop_width == 1080
        assert crop_info.crop_height == 810  # 1080 * 3/4
        assert crop_info.crop_x == 0
        assert crop_info.crop_y == 555  # (1920 - 810) / 2


class TestCropVideoTo4x3:
    """Test video cropping functionality."""

    @patch('mpv_scraper.video_crop.subprocess.run')
    def test_crop_video_success(self, mock_run):
        """Test successful video cropping."""
        mock_run.return_value = Mock(returncode=0)
        
        crop_info = CropInfo(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_4x3.mp4"),
            crop_width=1440,
            crop_height=1080,
            crop_x=240,
            crop_y=0,
            quality="medium"
        )
        
        result = crop_video_to_4_3(crop_info)
        
        assert result is True
        mock_run.assert_called_once()
        
        # Check that ffmpeg command includes crop filter
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args[0]
        assert "-vf" in call_args
        assert "crop=1440:1080:240:0" in " ".join(call_args)

    @patch('mpv_scraper.video_crop.subprocess.run')
    def test_crop_video_failure(self, mock_run):
        """Test video cropping failure."""
        mock_run.return_value = Mock(returncode=1, stderr=b"Crop failed")
        
        crop_info = CropInfo(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_4x3.mp4"),
            crop_width=1440,
            crop_height=1080,
            crop_x=240,
            crop_y=0,
            quality="medium"
        )
        
        result = crop_video_to_4_3(crop_info)
        
        assert result is False

    @patch('mpv_scraper.video_crop.subprocess.run')
    def test_crop_video_timeout(self, mock_run):
        """Test video cropping timeout."""
        mock_run.side_effect = TimeoutError("Process timed out")
        
        crop_info = CropInfo(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_4x3.mp4"),
            crop_width=1440,
            crop_height=1080,
            crop_x=240,
            crop_y=0,
            quality="medium"
        )
        
        result = crop_video_to_4_3(crop_info)
        
        assert result is False

    @patch('mpv_scraper.video_crop.subprocess.run')
    def test_crop_video_quality_presets(self, mock_run):
        """Test different quality presets."""
        mock_run.return_value = Mock(returncode=0)
        
        # Test fast quality
        crop_info = CropInfo(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output_4x3.mp4"),
            crop_width=1440,
            crop_height=1080,
            crop_x=240,
            crop_y=0,
            quality="fast"
        )
        
        crop_video_to_4_3(crop_info)
        call_args = mock_run.call_args[0][0]
        assert "-preset" in call_args
        assert "ultrafast" in call_args

        # Test high quality
        crop_info.quality = "high"
        crop_video_to_4_3(crop_info)
        call_args = mock_run.call_args[0][0]
        assert "-preset" in call_args
        assert "slow" in call_args


class TestBatchCropVideosTo4x3:
    """Test batch video cropping."""

    @patch('mpv_scraper.video_crop.detect_letterboxing')
    @patch('mpv_scraper.video_crop.crop_video_to_4_3')
    def test_batch_crop_success(self, mock_crop, mock_detect):
        """Test successful batch cropping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test video files
            test_video1 = temp_path / "video1.mp4"
            test_video2 = temp_path / "video2.mp4"
            test_video1.touch()
            test_video2.touch()
            
            # Mock detection and cropping
            mock_detect.return_value = CropInfo(
                input_path=test_video1,
                output_path=test_video1.with_name("video1_4x3.mp4"),
                crop_width=1440,
                crop_height=1080,
                crop_x=240,
                crop_y=0,
                quality="medium"
            )
            mock_crop.return_value = True
            
            result = batch_crop_videos_to_4_3(temp_path, "medium")
            
            assert result["total"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert len(result["errors"]) == 0

    @patch('mpv_scraper.video_crop.detect_letterboxing')
    @patch('mpv_scraper.video_crop.crop_video_to_4_3')
    def test_batch_crop_partial_failure(self, mock_crop, mock_detect):
        """Test batch cropping with some failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test video files
            test_video1 = temp_path / "video1.mp4"
            test_video2 = temp_path / "video2.mp4"
            test_video1.touch()
            test_video2.touch()
            
            # Mock detection
            mock_detect.return_value = CropInfo(
                input_path=test_video1,
                output_path=test_video1.with_name("video1_4x3.mp4"),
                crop_width=1440,
                crop_height=1080,
                crop_x=240,
                crop_y=0,
                quality="medium"
            )
            
            # Mock cropping: first succeeds, second fails
            mock_crop.side_effect = [True, False]
            
            result = batch_crop_videos_to_4_3(temp_path, "medium")
            
            assert result["total"] == 2
            assert result["successful"] == 1
            assert result["failed"] == 1
            assert len(result["errors"]) == 1

    @patch('mpv_scraper.video_crop.detect_letterboxing')
    def test_batch_crop_detection_failure(self, mock_detect):
        """Test batch cropping with detection failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test video file
            test_video = temp_path / "video1.mp4"
            test_video.touch()
            
            # Mock detection failure
            mock_detect.side_effect = RuntimeError("Detection failed")
            
            result = batch_crop_videos_to_4_3(temp_path, "medium")
            
            assert result["total"] == 1
            assert result["successful"] == 0
            assert result["failed"] == 1
            assert len(result["errors"]) == 1

    def test_batch_crop_no_videos(self):
        """Test batch cropping with no video files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            result = batch_crop_videos_to_4_3(temp_path, "medium")
            
            assert result["total"] == 0
            assert result["successful"] == 0
            assert result["failed"] == 0
            assert len(result["errors"]) == 0

    def test_batch_crop_skip_existing(self):
        """Test that existing cropped files are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create original and cropped files
            original_video = temp_path / "video1.mp4"
            cropped_video = temp_path / "video1_4x3.mp4"
            original_video.touch()
            cropped_video.touch()
            
            result = batch_crop_videos_to_4_3(temp_path, "medium", overwrite=False)
            
            # Should skip existing cropped file
            assert result["total"] == 1
            assert result["successful"] == 0
            assert result["failed"] == 0
            assert len(result["errors"]) == 0

    def test_batch_crop_overwrite_existing(self):
        """Test that existing cropped files are overwritten when requested."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create original and cropped files
            original_video = temp_path / "video1.mp4"
            cropped_video = temp_path / "video1_4x3.mp4"
            original_video.touch()
            cropped_video.touch()
            
            with patch('mpv_scraper.video_crop.detect_letterboxing') as mock_detect, \
                 patch('mpv_scraper.video_crop.crop_video_to_4_3') as mock_crop:
                
                mock_detect.return_value = CropInfo(
                    input_path=original_video,
                    output_path=cropped_video,
                    crop_width=1440,
                    crop_height=1080,
                    crop_x=240,
                    crop_y=0,
                    quality="medium"
                )
                mock_crop.return_value = True
                
                result = batch_crop_videos_to_4_3(temp_path, "medium", overwrite=True)
                
                # Should process existing cropped file
                assert result["total"] == 1
                assert result["successful"] == 1
                assert result["failed"] == 0
