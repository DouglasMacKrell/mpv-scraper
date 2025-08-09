"""
Tests for video cleaner functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import platform

from mpv_scraper.video_cleaner import (
    VideoAnalysis,
    OptimizationPreset,
    HANDHELD_OPTIMIZED,
    COMPATIBILITY_MODE,
    analyze_video_file,
    batch_analyze_videos,
    optimize_video_file,
    batch_optimize_videos,
)


class TestVideoAnalysis:
    """Test VideoAnalysis dataclass."""

    def test_video_analysis_creation(self):
        """Test creating VideoAnalysis with valid parameters."""
        analysis = VideoAnalysis(
            file_path=Path("/test/video.mp4"),
            codec="hevc",
            profile="main",
            width=1920,
            height=1080,
            bitrate=6000000,
            pixel_format="yuv420p10le",
            file_size_mb=1024,
            duration_seconds=1800,
            is_problematic=True,
            issues=["HEVC codec", "10-bit color", "High bitrate"],
            optimization_score=0.95,
        )

        assert analysis.file_path == Path("/test/video.mp4")
        assert analysis.codec == "hevc"
        assert analysis.width == 1920
        assert analysis.height == 1080
        assert analysis.bitrate == 6000000
        assert analysis.pixel_format == "yuv420p10le"
        assert analysis.file_size_mb == 1024
        assert analysis.optimization_score == 0.95
        assert analysis.issues == ["HEVC codec", "10-bit color", "High bitrate"]


class TestOptimizationPreset:
    """Test OptimizationPreset dataclass."""

    def test_optimization_preset_creation(self):
        """Test creating OptimizationPreset with valid parameters."""
        preset = OptimizationPreset(
            name="test_preset",
            description="Test preset",
            target_codec="libx264",
            target_profile="high",
            target_bitrate=1500000,
            target_resolution=(1280, 720),
            crf=23,
            preset="faster",
            tune="film",
            audio_codec="aac",
            audio_bitrate=128000,
        )

        assert preset.name == "test_preset"
        assert preset.target_codec == "libx264"
        assert preset.target_profile == "high"
        assert preset.target_bitrate == 1500000
        assert preset.target_resolution == (1280, 720)
        assert preset.crf == 23
        assert preset.preset == "faster"
        assert preset.tune == "film"
        assert preset.audio_codec == "aac"
        assert preset.audio_bitrate == 128000

    def test_handheld_optimized_preset(self):
        """Test HANDHELD_OPTIMIZED preset configuration."""
        assert HANDHELD_OPTIMIZED.name == "handheld_optimized"
        assert HANDHELD_OPTIMIZED.target_codec == "libx264"
        assert HANDHELD_OPTIMIZED.target_profile == "high10"
        assert HANDHELD_OPTIMIZED.target_bitrate == 1500000
        assert HANDHELD_OPTIMIZED.target_resolution == (1280, 720)
        assert HANDHELD_OPTIMIZED.crf == 23
        assert HANDHELD_OPTIMIZED.preset == "faster"
        assert HANDHELD_OPTIMIZED.tune == "film"
        assert HANDHELD_OPTIMIZED.audio_codec == "aac"
        assert HANDHELD_OPTIMIZED.audio_bitrate == 128000

    def test_compatibility_mode_preset(self):
        """Test COMPATIBILITY_MODE preset configuration."""
        assert COMPATIBILITY_MODE.name == "compatibility_mode"
        assert COMPATIBILITY_MODE.target_codec == "libx264"
        assert COMPATIBILITY_MODE.target_profile == "baseline"
        assert COMPATIBILITY_MODE.target_bitrate == 800000
        assert COMPATIBILITY_MODE.target_resolution == (854, 480)
        assert COMPATIBILITY_MODE.crf == 25
        assert COMPATIBILITY_MODE.preset == "ultrafast"
        assert COMPATIBILITY_MODE.tune == "fastdecode"
        assert COMPATIBILITY_MODE.audio_codec == "aac"
        assert COMPATIBILITY_MODE.audio_bitrate == 96000


class TestAnalyzeVideoFile:
    """Test video file analysis."""

    @patch("mpv_scraper.video_cleaner.subprocess.run")
    def test_analyze_video_file_problematic(self, mock_run):
        """Test analysis of problematic video file."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""{
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "hevc",
                        "width": 1920,
                        "height": 1080,
                        "bit_rate": "6000000",
                        "pix_fmt": "yuv420p10le"
                    }
                ],
                "format": {
                    "size": "1073741824"
                }
            }""",
        )

        analysis = analyze_video_file(Path("/test/video.mp4"))

        assert analysis is not None
        assert analysis.codec == "hevc"
        assert analysis.width == 1920
        assert analysis.height == 1080
        assert analysis.bitrate == 6000000
        assert analysis.pixel_format == "yuv420p10le"
        assert analysis.file_size_mb == 1024
        assert analysis.is_problematic is True
        assert any("HEVC" in issue for issue in analysis.issues)

    @patch("mpv_scraper.video_cleaner.subprocess.run")
    def test_analyze_video_file_optimized(self, mock_run):
        """Test analysis of already optimized video file."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""{
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 1280,
                        "height": 720,
                        "bit_rate": "1500000",
                        "pix_fmt": "yuv420p"
                    }
                ],
                "format": {
                    "size": "209715200"
                }
            }""",
        )

        analysis = analyze_video_file(Path("/test/video.mp4"))

        assert analysis is not None
        assert analysis.codec == "h264"
        assert analysis.width == 1280
        assert analysis.height == 720
        assert analysis.bitrate == 1500000
        assert analysis.pixel_format == "yuv420p"
        assert analysis.file_size_mb == 200
        assert analysis.is_problematic is False
        assert len(analysis.issues) == 0

    @patch("mpv_scraper.video_cleaner.subprocess.run")
    def test_analyze_video_file_missing_info(self, mock_run):
        """Test analysis with missing video information."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""{
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 1280,
                        "height": 720
                    }
                ],
                "format": {
                    "size": "104857600"
                }
            }""",
        )

        analysis = analyze_video_file(Path("/test/video.mp4"))

        assert analysis is not None
        assert analysis.codec == "h264"
        assert analysis.width == 1280
        assert analysis.height == 720
        assert analysis.bitrate == 0  # Default when missing
        assert analysis.pixel_format == "unknown"  # Default when missing
        assert analysis.file_size_mb == 100

    @patch("mpv_scraper.video_cleaner.subprocess.run")
    def test_analyze_video_file_no_video_stream(self, mock_run):
        """Test analysis of file with no video stream."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""{
                "streams": [
                    {
                        "codec_type": "audio",
                        "codec_name": "aac"
                    }
                ],
                "format": {
                    "size": "10485760"
                }
            }""",
        )

        analysis = analyze_video_file(Path("/test/audio.mp3"))
        assert analysis is None


class TestBatchAnalyzeVideos:
    """Test batch video analysis."""

    @patch("mpv_scraper.video_cleaner.analyze_video_file")
    def test_batch_analyze_success(self, mock_analyze):
        """Test successful batch analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test video files
            test_video1 = temp_path / "video1.mp4"
            test_video2 = temp_path / "video2.mp4"
            test_video1.touch()
            test_video2.touch()

            # Mock analysis results
            mock_analyze.side_effect = [
                VideoAnalysis(
                    file_path=test_video1,
                    codec="hevc",
                    profile="main",
                    width=1920,
                    height=1080,
                    bitrate=6000000,
                    pixel_format="yuv420p10le",
                    file_size_mb=1024,
                    duration_seconds=1800,
                    is_problematic=True,
                    issues=["HEVC codec", "10-bit color"],
                    optimization_score=0.95,
                ),
                VideoAnalysis(
                    file_path=test_video2,
                    codec="h264",
                    profile="high",
                    width=1280,
                    height=720,
                    bitrate=1500000,
                    pixel_format="yuv420p",
                    file_size_mb=200,
                    duration_seconds=1800,
                    is_problematic=False,
                    issues=[],
                    optimization_score=0.2,
                ),
            ]

            results = batch_analyze_videos(temp_path)

            assert len(results[0]) == 2  # all_videos
            assert len(results[1]) == 1  # problematic_videos
            assert results[0][0].optimization_score == 0.95
            assert results[0][1].optimization_score == 0.2
            assert mock_analyze.call_count == 2

    @patch("mpv_scraper.video_cleaner.analyze_video_file")
    def test_batch_analyze_partial_failure(self, mock_analyze):
        """Test batch analysis with some failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test video files
            test_video1 = temp_path / "video1.mp4"
            test_video2 = temp_path / "video2.mp4"
            test_video1.touch()
            test_video2.touch()

            # Mock analysis: first succeeds, second fails
            mock_analyze.side_effect = [
                VideoAnalysis(
                    file_path=test_video1,
                    codec="hevc",
                    profile="main",
                    width=1920,
                    height=1080,
                    bitrate=6000000,
                    pixel_format="yuv420p10le",
                    file_size_mb=1024,
                    duration_seconds=1800,
                    is_problematic=True,
                    issues=["HEVC codec"],
                    optimization_score=0.95,
                ),
                None,  # Second analysis fails and returns None
            ]

            results = batch_analyze_videos(temp_path)

            assert len(results[0]) == 1  # all_videos
            assert len(results[1]) == 1  # problematic_videos
            assert results[0][0].optimization_score == 0.95
            assert mock_analyze.call_count == 2

    def test_batch_analyze_no_videos(self):
        """Test batch analysis with no video files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            results = batch_analyze_videos(temp_path)

            assert len(results[0]) == 0  # all_videos
            assert len(results[1]) == 0  # problematic_videos

    def test_batch_analyze_skip_apple_double_files(self):
        """Test that AppleDouble files (._) are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create regular video and AppleDouble video files
            regular_video = temp_path / "video1.mp4"
            apple_double_video = temp_path / "._video1.mp4"
            regular_video.touch()
            apple_double_video.touch()

            with patch("mpv_scraper.video_cleaner.analyze_video_file") as mock_analyze:
                mock_analyze.return_value = VideoAnalysis(
                    file_path=regular_video,
                    codec="h264",
                    profile="high",
                    width=1280,
                    height=720,
                    bitrate=1500000,
                    pixel_format="yuv420p",
                    file_size_mb=200,
                    duration_seconds=1800,
                    is_problematic=False,
                    issues=[],
                    optimization_score=0.2,
                )

                results = batch_analyze_videos(temp_path)

            # Should only analyze regular video file
            assert len(results[0]) == 1  # all_videos
            assert len(results[1]) == 0  # problematic_videos
            assert results[0][0].file_path == regular_video
            mock_analyze.assert_called_once()


class TestOptimizeVideoFile:
    """Test video file optimization."""

    @patch("mpv_scraper.video_cleaner.subprocess.run")
    def test_optimize_video_success(self, mock_run):
        """Test successful video optimization."""
        mock_run.return_value = Mock(returncode=0)

        input_path = Path("/test/input.mp4")
        output_path = Path("/test/output_optimized.mp4")

        result = optimize_video_file(input_path, output_path, HANDHELD_OPTIMIZED)

        assert result is True
        mock_run.assert_called_once()

        # Check ffmpeg command
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args[0]
        assert "-i" in call_args
        assert str(input_path) in call_args
        assert str(output_path) in call_args
        assert "-c:v" in call_args
        # On macOS hardware acceleration is used first; elsewhere software path is used
        if platform.system() == "Darwin":
            assert "h264_videotoolbox" in call_args
            assert "-profile:v" in call_args
        else:
            # Software encoder path
            assert "libx264" in call_args
            assert "-preset" in call_args

    @patch("mpv_scraper.video_cleaner.subprocess.run")
    def test_optimize_video_failure(self, mock_run):
        """Test video optimization failure."""
        mock_run.return_value = Mock(returncode=1, stderr=b"Optimization failed")

        input_path = Path("/test/input.mp4")
        output_path = Path("/test/output_optimized.mp4")

        result = optimize_video_file(input_path, output_path, HANDHELD_OPTIMIZED)

        assert result is False

    @patch("mpv_scraper.video_cleaner.subprocess.run")
    def test_optimize_video_timeout(self, mock_run):
        """Test video optimization timeout."""
        mock_run.side_effect = TimeoutError("Process timed out")

        input_path = Path("/test/input.mp4")
        output_path = Path("/test/output_optimized.mp4")

        result = optimize_video_file(input_path, output_path, HANDHELD_OPTIMIZED)

        assert result is False

    @patch("mpv_scraper.video_cleaner.subprocess.run")
    def test_optimize_video_ffmpeg_parameters(self, mock_run):
        """Test that FFmpeg parameters are correctly set."""
        mock_run.return_value = Mock(returncode=0)

        input_path = Path("/test/input.mp4")
        output_path = Path("/test/output_optimized.mp4")

        optimize_video_file(input_path, output_path, HANDHELD_OPTIMIZED)

        call_args = mock_run.call_args[0][0]
        args_str = " ".join(call_args)

        # Check essential parameters depending on platform
        if platform.system() == "Darwin":
            assert "-c:v h264_videotoolbox" in args_str
            assert "-profile:v high" in args_str
            assert "-b:v 1500000" in args_str
        else:
            assert "-c:v libx264" in args_str
            assert "-preset" in args_str
            assert "-crf 23" in args_str
            assert "-tune film" in args_str
        assert "-pix_fmt yuv420p" in args_str
        assert "-c:a aac" in args_str
        assert "-b:a 128000" in args_str

    @patch("mpv_scraper.video_cleaner.subprocess.run")
    def test_optimize_video_compatibility_preset(self, mock_run):
        """Test compatibility preset parameters."""
        mock_run.return_value = Mock(returncode=0)

        input_path = Path("/test/input.mp4")
        output_path = Path("/test/output_optimized.mp4")

        optimize_video_file(input_path, output_path, COMPATIBILITY_MODE)

        call_args = mock_run.call_args[0][0]
        args_str = " ".join(call_args)

        # Check compatibility parameters
        if platform.system() == "Darwin":
            assert "-c:v h264_videotoolbox" in args_str
            assert "-profile:v high" in args_str
            assert "-b:v 800000" in args_str
        else:
            assert "-c:v libx264" in args_str
            assert "-preset ultrafast" in args_str
            assert "-crf 25" in args_str
            assert "-tune fastdecode" in args_str


class TestBatchOptimizeVideos:
    """Test batch video optimization."""

    @patch("mpv_scraper.video_cleaner.optimize_video_file")
    @patch("mpv_scraper.video_cleaner.batch_analyze_videos")
    def test_batch_optimize_success(self, mock_batch_analyze, mock_optimize):
        """Test successful batch optimization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test video files
            test_video1 = temp_path / "video1.mp4"
            test_video2 = temp_path / "video2.mp4"
            test_video1.touch()
            test_video2.touch()

            # Mock analysis results
            mock_batch_analyze.return_value = (
                [
                    VideoAnalysis(
                        file_path=test_video1,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    ),
                    VideoAnalysis(
                        file_path=test_video2,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    ),
                ],
                [
                    VideoAnalysis(
                        file_path=test_video1,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    ),
                    VideoAnalysis(
                        file_path=test_video2,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    ),
                ],
            )

            mock_optimize.return_value = True

            result = batch_optimize_videos(temp_path, HANDHELD_OPTIMIZED)

            assert result[0] == 2  # processed
            assert result[1] == 2  # successful
            assert mock_optimize.call_count == 2

    @patch("mpv_scraper.video_cleaner.optimize_video_file")
    @patch("mpv_scraper.video_cleaner.batch_analyze_videos")
    def test_batch_optimize_partial_failure(self, mock_batch_analyze, mock_optimize):
        """Test batch optimization with some failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test video files
            test_video1 = temp_path / "video1.mp4"
            test_video2 = temp_path / "video2.mp4"
            test_video1.touch()
            test_video2.touch()

            # Mock analysis results
            mock_batch_analyze.return_value = (
                [
                    VideoAnalysis(
                        file_path=test_video1,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    ),
                    VideoAnalysis(
                        file_path=test_video2,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    ),
                ],
                [
                    VideoAnalysis(
                        file_path=test_video1,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    ),
                    VideoAnalysis(
                        file_path=test_video2,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    ),
                ],
            )

            # Mock optimization: first succeeds, second fails
            mock_optimize.side_effect = [True, False]

            result = batch_optimize_videos(temp_path, HANDHELD_OPTIMIZED)

            assert result[0] == 2  # processed
            assert result[1] == 1  # successful

    def test_batch_optimize_no_videos(self):
        """Test batch optimization with no video files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            result = batch_optimize_videos(temp_path, HANDHELD_OPTIMIZED)

            assert result[0] == 0  # processed
            assert result[1] == 0  # successful

    def test_batch_optimize_skip_existing(self):
        """Test that existing optimized files are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create original and optimized files
            original_video = temp_path / "video1.mp4"
            optimized_video = temp_path / "video1_optimized.mp4"
            original_video.touch()
            optimized_video.touch()

            with patch(
                "mpv_scraper.video_cleaner.optimize_video_file"
            ) as mock_optimize:
                result = batch_optimize_videos(
                    temp_path, HANDHELD_OPTIMIZED, overwrite=False
                )

            # Should skip existing optimized file
            assert result[0] == 0  # processed
            assert result[1] == 0  # successful
            mock_optimize.assert_not_called()

    @patch("mpv_scraper.video_cleaner.batch_analyze_videos")
    def test_batch_optimize_overwrite_existing(self, mock_batch_analyze):
        """Test that existing optimized files are overwritten when requested."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create original and optimized files
            original_video = temp_path / "video1.mp4"
            optimized_video = temp_path / "video1_optimized.mp4"
            original_video.touch()
            optimized_video.touch()

            # Mock analysis results
            mock_batch_analyze.return_value = (
                [
                    VideoAnalysis(
                        file_path=original_video,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    )
                ],
                [
                    VideoAnalysis(
                        file_path=original_video,
                        codec="hevc",
                        profile="main",
                        width=1920,
                        height=1080,
                        bitrate=6000000,
                        pixel_format="yuv420p10le",
                        file_size_mb=1024,
                        duration_seconds=1800,
                        is_problematic=True,
                        issues=["HEVC codec"],
                        optimization_score=0.95,
                    )
                ],
            )

            with patch(
                "mpv_scraper.video_cleaner.optimize_video_file"
            ) as mock_optimize:
                mock_optimize.return_value = True
                result = batch_optimize_videos(
                    temp_path, HANDHELD_OPTIMIZED, overwrite=True
                )

            # Should process existing optimized file
            assert result[0] == 1  # processed
            assert result[1] == 1  # successful
            mock_optimize.assert_called_once()

    def test_batch_optimize_skip_apple_double_files(self):
        """Test that AppleDouble files (._) are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create regular video and AppleDouble video files
            regular_video = temp_path / "video1.mp4"
            apple_double_video = temp_path / "._video1.mp4"
            regular_video.touch()
            apple_double_video.touch()

            with patch(
                "mpv_scraper.video_cleaner.optimize_video_file"
            ) as mock_optimize:
                mock_optimize.return_value = True
                result = batch_optimize_videos(temp_path, HANDHELD_OPTIMIZED)

            # Should only process regular video file
            assert result[0] == 0  # processed (no problematic videos found)
            assert result[1] == 0  # successful
            mock_optimize.assert_not_called()
