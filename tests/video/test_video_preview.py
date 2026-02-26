"""
Tests for ES-DE video preview clip generation.

Video previews are 30-second clips extracted from the 25% mark of each video,
stored in /mpv/videos/ as {stem}-preview.mp4, targeting <1 MB for ES-DE.
"""

import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from mpv_scraper.video_preview import (
    extract_preview_clip,
    get_preview_path,
    ensure_preview,
)


class TestExtractPreviewClip:
    """Test extract_preview_clip function."""

    @patch("mpv_scraper.video_preview.subprocess.run")
    @patch("mpv_scraper.video_preview.get_video_duration")
    def test_extract_preview_clip_creates_file(self, mock_duration, mock_run):
        """Preview clip is created when ffmpeg succeeds."""
        mock_duration.return_value = 600.0  # 10 min video, 25% = 150s
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "episode.mp4"
            outp = tmp / "episode-preview.mp4"
            inp.write_bytes(b"fake")
            result = extract_preview_clip(inp, outp)

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args
        assert "-ss" in call_args
        assert "-t" in call_args
        assert str(outp) in call_args

    @patch("mpv_scraper.video_preview.subprocess.run")
    @patch("mpv_scraper.video_preview.get_video_duration")
    def test_extract_preview_clip_returns_false_on_failure(
        self, mock_duration, mock_run
    ):
        """Returns False when ffmpeg fails."""
        mock_duration.return_value = 600.0
        mock_run.return_value = Mock(returncode=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "episode.mp4"
            outp = tmp / "episode-preview.mp4"
            inp.write_bytes(b"fake")
            result = extract_preview_clip(inp, outp)

        assert result is False

    @patch("mpv_scraper.video_preview.subprocess.run")
    @patch("mpv_scraper.video_preview.get_video_duration")
    def test_extract_preview_clip_short_video_handling(self, mock_duration, mock_run):
        """Short videos (< 30s) are handled without extending past end."""
        mock_duration.return_value = 45.0  # 45 sec video
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "short.mp4"
            outp = tmp / "short-preview.mp4"
            inp.write_bytes(b"fake")
            result = extract_preview_clip(inp, outp)

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "-ss" in call_args

    @patch("mpv_scraper.video_preview.subprocess.run")
    @patch("mpv_scraper.video_preview.get_video_duration")
    def test_extract_preview_clip_start_at_25_percent(self, mock_duration, mock_run):
        """Start time is 25% of video duration."""
        mock_duration.return_value = 1200.0  # 20 min
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "long.mp4"
            outp = tmp / "long-preview.mp4"
            inp.write_bytes(b"fake")
            extract_preview_clip(inp, outp)

        call_args = mock_run.call_args[0][0]
        ss_idx = call_args.index("-ss") + 1 if "-ss" in call_args else -1
        assert ss_idx >= 0
        start_val = call_args[ss_idx]
        assert float(start_val) == pytest.approx(300.0, abs=1.0)


class TestGetPreviewPath:
    """Test preview path convention."""

    def test_preview_output_path_convention(self):
        """Preview path is videos_dir / {stem}-preview.mp4."""
        videos_dir = Path("/mpv/videos")
        stem = "Show - S01E01 - Title"
        path = get_preview_path(videos_dir, stem)
        assert path == Path("/mpv/videos/Show - S01E01 - Title-preview.mp4")

    def test_preview_path_with_extension_stem(self):
        """Stem without extension produces correct path."""
        videos_dir = Path("/mpv/videos")
        path = get_preview_path(videos_dir, "Movie Title (1985)")
        assert path.name == "Movie Title (1985)-preview.mp4"


class TestEnsurePreview:
    """Test ensure_preview (generate if missing)."""

    @patch("mpv_scraper.video_preview.extract_preview_clip")
    def test_ensure_preview_skips_when_exists(self, mock_extract):
        """Does not extract when preview already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            videos_dir = tmp / "videos"
            videos_dir.mkdir()
            existing = videos_dir / "ep-preview.mp4"
            existing.write_bytes(b"x" * 100)

            result = ensure_preview(
                video_path=tmp / "ep.mp4",
                videos_dir=videos_dir,
                stem="ep",
            )

        assert result == "./videos/ep-preview.mp4"
        mock_extract.assert_not_called()

    @patch("mpv_scraper.video_preview.extract_preview_clip")
    def test_ensure_preview_generates_when_missing(self, mock_extract):
        """Extracts when preview does not exist."""
        mock_extract.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            videos_dir = tmp / "videos"
            videos_dir.mkdir()
            video = tmp / "ep.mp4"
            video.write_bytes(b"fake")

            result = ensure_preview(
                video_path=video,
                videos_dir=videos_dir,
                stem="ep",
            )

        assert result == "./videos/ep-preview.mp4"
        mock_extract.assert_called_once()
        assert mock_extract.call_args[0][1].name == "ep-preview.mp4"

    def test_videos_directory_created(self):
        """ensure_preview creates videos_dir if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            videos_dir = tmp / "videos"
            assert not videos_dir.exists()
            video = tmp / "ep.mp4"
            video.write_bytes(b"fake")

            with patch(
                "mpv_scraper.video_preview.extract_preview_clip",
                return_value=True,
            ):
                result = ensure_preview(
                    video_path=video,
                    videos_dir=videos_dir,
                    stem="ep",
                )

            assert result == "./videos/ep-preview.mp4"
            assert videos_dir.exists()
