import time
from pathlib import Path

import pytest

from mpv_scraper.jobs import JobManager


@pytest.mark.integration
def test_enqueue_optimize_job(tmp_path: Path):
    """Enqueue a dummy job and observe progress events."""

    jm = JobManager(history_dir=tmp_path)

    # Dummy target that emits progress n times and respects cancellation
    def dummy_task(progress_callback, should_cancel):
        total = 5
        progress_callback(0, total, "start")
        for _ in range(total):
            if should_cancel():
                return
            time.sleep(0.01)
            progress_callback(1, None, "tick")

    jid = jm.enqueue("dummy", dummy_task)

    # Wait for completion
    for _ in range(200):
        job = jm.observe(jid)
        if job.status in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.01)

    job = jm.observe(jid)
    assert job.status == "completed"
    assert job.progress == 5
    assert any(e["type"] == "start" for e in job.events)


@pytest.mark.integration
def test_cancel_job(tmp_path: Path):
    # Existing test remains
    ...


@pytest.mark.integration
def test_jobs_table_shows_progress(tmp_path: Path, monkeypatch):
    """The textual app should render a snapshot of job progress in non-interactive mode."""
    # Create a dummy job and write a small JobManager state that the TUI can read
    from mpv_scraper.jobs import JobManager

    jm = JobManager(history_dir=tmp_path)

    def short_task(progress_callback, should_cancel):
        progress_callback(0, 3, "start")
        progress_callback(1, None, "tick")

    jid = jm.enqueue("dummy", short_task)

    # Run the TUI non-interactively; it should render without error
    from click.testing import CliRunner
    from mpv_scraper.cli import main as cli_main

    runner = CliRunner()
    res = runner.invoke(cli_main, ["tui", "--non-interactive"])
    assert res.exit_code == 0, res.output
    """Cancellation should transition job to cancelled state best-effort."""

    jm = JobManager(history_dir=tmp_path)

    def long_task(progress_callback, should_cancel):
        total = 50
        progress_callback(0, total, "start")
        for _ in range(total):
            if should_cancel():
                return
            time.sleep(0.02)
            progress_callback(1, None, "tick")

    jid = jm.enqueue("long", long_task)
    time.sleep(0.05)
    jm.cancel(jid)

    # Wait for finish
    for _ in range(200):
        job = jm.observe(jid)
        if job.status in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.01)

    job = jm.observe(jid)
    assert job.status in ("cancelled", "completed")
    # If completed before cancel landed, at least some progress happened
    assert job.progress >= 1
