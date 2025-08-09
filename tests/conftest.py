import os
from typing import Any, List

import pytest


@pytest.fixture(autouse=True)
def _isolate_ffmpeg_calls(monkeypatch: pytest.MonkeyPatch):
    """Globally isolate external ffmpeg/ffprobe calls in tests.

    - Sets an env flag consumed by code to choose fast paths
    - Stubs subprocess.run for ffmpeg/ffprobe to return immediately
    """
    os.environ.setdefault("MPV_SCRAPER_TEST_MODE", "1")

    import subprocess  # noqa: WPS433

    real_run = subprocess.run

    def fake_run(cmd: Any, *args: Any, **kwargs: Any):  # type: ignore[override]
        try:
            argv: List[str] = cmd if isinstance(cmd, list) else [str(cmd)]
        except Exception:
            argv = []

        if argv and ("ffmpeg" in argv[0] or "ffprobe" in argv[0]):
            # Provide minimal sane stdout for ffprobe width,height parsing
            stdout = "1920,1080" if "ffprobe" in argv[0] else ""
            return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
