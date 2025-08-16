"""Test jobs module coverage for Sprint 18.9."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import time

from mpv_scraper.jobs import Job, JobManager


def create_job_manager_with_mocks():
    """Helper function to create JobManager with proper mocks."""
    with patch("pathlib.Path.mkdir") as mock_mkdir:
        with patch("builtins.open", create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            jm = JobManager()
            return jm, mock_mkdir, mock_open, mock_file


class TestJobCoverage:
    """Test Job functionality to improve coverage."""

    def test_job_initialization(self):
        """Test Job initialization with default values."""

        def dummy_target():
            return "test"

        job = Job(job_id="test123", name="Test Job", target=dummy_target)

        assert job.job_id == "test123"
        assert job.name == "Test Job"
        assert job.target == dummy_target
        assert job.status == "queued"
        assert job.progress == 0
        assert job.total is None
        assert job.error is None
        assert job.events == []
        assert not job.should_cancel()

    def test_job_initialization_with_args_kwargs(self):
        """Test Job initialization with args and kwargs."""

        def dummy_target(arg1, arg2, kwarg1=None):
            return f"{arg1}_{arg2}_{kwarg1}"

        job = Job(
            job_id="test123",
            name="Test Job",
            target=dummy_target,
            args=("value1", "value2"),
            kwargs={"kwarg1": "kwvalue1"},
        )

        assert job.args == ("value1", "value2")
        assert job.kwargs == {"kwarg1": "kwvalue1"}

    def test_job_should_cancel(self):
        """Test Job should_cancel functionality."""
        job = Job(job_id="test123", name="Test Job", target=lambda: None)

        # Initially should not be cancelled
        assert not job.should_cancel()

        # Set cancel flag
        job._cancel.set()
        assert job.should_cancel()

    def test_job_repr(self):
        """Test Job string representation."""
        job = Job(job_id="test123", name="Test Job", target=lambda: None)

        # Test that repr doesn't include private fields
        repr_str = repr(job)
        assert "test123" in repr_str
        assert "Test Job" in repr_str
        assert "_cancel" not in repr_str
        assert "_thread" not in repr_str


class TestJobManagerCoverage:
    """Test JobManager functionality to improve coverage."""

    def test_job_manager_initialization_default(self):
        """Test JobManager initialization with default history directory."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                mock_cwd.return_value = Path("/test/cwd")

                jm = JobManager()

                assert jm._jobs == {}
                assert jm._history_dir == Path("/test/cwd/.mpv-scraper")
                mock_mkdir.assert_called_once()

    def test_job_manager_initialization_custom_dir(self):
        """Test JobManager initialization with custom history directory."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            custom_dir = Path("/custom/history")

            jm = JobManager(history_dir=custom_dir)

            assert jm._jobs == {}
            assert jm._history_dir == custom_dir
            mock_mkdir.assert_called_once()

    def test_job_manager_enqueue(self):
        """Test JobManager enqueue functionality."""
        with patch("pathlib.Path.mkdir"):
            with patch("builtins.open", create=True) as mock_open:
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file

                jm = JobManager()

                def dummy_target(*args, **kwargs):
                    return "completed"

                job_id = jm.enqueue("Test Job", dummy_target, "arg1", kwarg1="value1")

                # Should return a job ID
                assert isinstance(job_id, str)
                assert len(job_id) == 12

                # Should create job in manager
                job = jm.observe(job_id)
                assert job.name == "Test Job"
                assert job.target == dummy_target
                assert job.args == ("arg1",)
                assert job.kwargs == {"kwarg1": "value1"}
                # Job might be running or completed by now, so check it's not failed
                assert job.status != "failed"

    def test_job_manager_observe(self):
        """Test JobManager observe functionality."""
        with patch("pathlib.Path.mkdir"):
            with patch("builtins.open", create=True) as mock_open:
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file

                jm = JobManager()

                def dummy_target():
                    return "completed"

                job_id = jm.enqueue("Test Job", dummy_target)
                job = jm.observe(job_id)

                assert job.name == "Test Job"
                assert job.target == dummy_target

    def test_job_manager_observe_nonexistent(self):
        """Test JobManager observe with nonexistent job."""
        with patch("pathlib.Path.mkdir"):
            jm = JobManager()

            # Should raise KeyError for nonexistent job
            with pytest.raises(KeyError):
                jm.observe("nonexistent")

    def test_job_manager_cancel_queued(self):
        """Test JobManager cancel functionality for queued job."""
        with patch("pathlib.Path.mkdir"):
            with patch("builtins.open", create=True) as mock_open:
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file

                jm = JobManager()

                def dummy_target(progress_callback=None, should_cancel=None):
                    time.sleep(0.1)  # Simulate work
                    return "completed"

                job_id = jm.enqueue("Test Job", dummy_target)

                # Cancel the job
                jm.cancel(job_id)

                # Check that cancel was requested
                job = jm.observe(job_id)
                assert any(event["type"] == "cancel_requested" for event in job.events)

    def test_job_manager_cancel_nonexistent(self):
        """Test JobManager cancel with nonexistent job."""
        jm, _, _, _ = create_job_manager_with_mocks()

        # Should not raise error for nonexistent job
        jm.cancel("nonexistent")

    def test_job_manager_cancel_completed(self):
        """Test JobManager cancel for completed job."""
        jm, _, _, _ = create_job_manager_with_mocks()

        def dummy_target(progress_callback=None, should_cancel=None):
            return "completed"

        job_id = jm.enqueue("Test Job", dummy_target)

        # Wait for completion
        for _ in range(10):
            job = jm.observe(job_id)
            if job.status in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.01)

        # Try to cancel completed job
        jm.cancel(job_id)

        # Should not add cancel event for completed job
        job = jm.observe(job_id)
        cancel_events = [e for e in job.events if e["type"] == "cancel_requested"]
        assert len(cancel_events) == 0

    def test_job_manager_runner_success(self):
        """Test JobManager _runner with successful completion."""
        jm, _, _, _ = create_job_manager_with_mocks()

        def dummy_target(progress_callback=None, should_cancel=None):
            if progress_callback:
                progress_callback(10, 100, "Working...")
            return "completed"

        job_id = jm.enqueue("Test Job", dummy_target)

        # Wait for completion
        for _ in range(50):
            job = jm.observe(job_id)
            if job.status in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.01)

        job = jm.observe(job_id)
        assert job.status == "completed"
        assert job.progress == 10
        assert job.total == 100
        assert any(event["type"] == "start" for event in job.events)
        assert any(event["type"] == "completed" for event in job.events)

    def test_job_manager_runner_failure(self):
        """Test JobManager _runner with exception."""
        jm, _, _, _ = create_job_manager_with_mocks()

        def failing_target(progress_callback=None, should_cancel=None):
            raise ValueError("Test error")

        job_id = jm.enqueue("Test Job", failing_target)

        # Wait for completion
        for _ in range(50):
            job = jm.observe(job_id)
            if job.status in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.01)

        job = jm.observe(job_id)
        assert job.status == "failed"
        assert "Test error" in job.error
        assert any(event["type"] == "failed" for event in job.events)

    def test_job_manager_runner_cancelled(self):
        """Test JobManager _runner with cancellation."""
        jm, _, _, _ = create_job_manager_with_mocks()

        def long_target(progress_callback=None, should_cancel=None):
            for i in range(10):
                if should_cancel and should_cancel():
                    return "cancelled"
                if progress_callback:
                    progress_callback(1, 10, f"Step {i}")
                time.sleep(0.01)
            return "completed"

        job_id = jm.enqueue("Test Job", long_target)

        # Cancel after a short delay
        time.sleep(0.02)
        jm.cancel(job_id)

        # Wait for completion
        for _ in range(50):
            job = jm.observe(job_id)
            if job.status in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.01)

        job = jm.observe(job_id)
        assert job.status in ("cancelled", "completed")
        assert job.progress > 0

    def test_job_manager_persist_success(self):
        """Test JobManager _persist functionality."""
        jm, _, _, _ = create_job_manager_with_mocks()

        def dummy_target():
            return "completed"

        job_id = jm.enqueue("Test Job", dummy_target)

        # Trigger persist by accessing job
        job = jm.observe(job_id)

        # Should be able to access job without errors
        assert job.name == "Test Job"
        assert job.target == dummy_target

    def test_job_manager_persist_failure(self):
        """Test JobManager _persist with file system error."""
        with patch("pathlib.Path.mkdir"):
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                jm = JobManager()

                def dummy_target():
                    return "completed"

                # Should not raise exception when persist fails
                job_id = jm.enqueue("Test Job", dummy_target)
                job = jm.observe(job_id)

                # Should still work despite persist failure
                assert job.name == "Test Job"

    def test_job_manager_progress_callback(self):
        """Test JobManager progress callback functionality."""
        jm, _, _, _ = create_job_manager_with_mocks()

        def target_with_progress(progress_callback=None, should_cancel=None):
            progress_callback(5, 20, "Starting...")
            progress_callback(10, 20, "Halfway...")
            progress_callback(5, 20, "Finishing...")
            return "completed"

        job_id = jm.enqueue("Test Job", target_with_progress)

        # Wait for completion
        for _ in range(50):
            job = jm.observe(job_id)
            if job.status in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.01)

        job = jm.observe(job_id)
        assert job.status == "completed"
        assert job.progress == 20
        assert job.total == 20

        # Check progress events
        progress_events = [e for e in job.events if e["type"] == "progress"]
        assert len(progress_events) == 3
        assert progress_events[0]["message"] == "Starting..."
        assert progress_events[1]["message"] == "Halfway..."
        assert progress_events[2]["message"] == "Finishing..."

    def test_job_manager_multiple_jobs(self):
        """Test JobManager with multiple concurrent jobs."""
        jm, _, _, _ = create_job_manager_with_mocks()

        def quick_target(progress_callback=None, should_cancel=None):
            if progress_callback:
                progress_callback(1, 1, "Done")
            return "completed"

        # Create multiple jobs
        job_ids = []
        for i in range(3):
            job_id = jm.enqueue(f"Job {i}", quick_target)
            job_ids.append(job_id)

        # Wait for all to complete
        for _ in range(50):
            all_completed = True
            for job_id in job_ids:
                job = jm.observe(job_id)
                if job.status not in ("completed", "failed", "cancelled"):
                    all_completed = False
                    break
            if all_completed:
                break
            time.sleep(0.01)

        # Check all jobs completed
        for job_id in job_ids:
            job = jm.observe(job_id)
            assert job.status == "completed"
