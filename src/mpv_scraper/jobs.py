"""Lightweight job management for background tasks and progress events.

This module provides a very small abstraction to enqueue callable tasks,
observe their progress via events, and request cancellation. It is purposely
minimal to keep tests fast and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, List, Optional, Tuple
import time
import uuid
import json
from pathlib import Path


ProgressCallback = Callable[[int, Optional[int], Optional[str]], None]
ShouldCancel = Callable[[], bool]


@dataclass
class Job:
    job_id: str
    name: str
    target: Callable[..., Any]
    args: Tuple[Any, ...] = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: str = "queued"  # queued | running | completed | failed | cancelled
    progress: int = 0
    total: Optional[int] = None
    error: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    _cancel: Event = field(default_factory=Event, repr=False)
    _thread: Optional[Thread] = field(default=None, repr=False)

    def should_cancel(self) -> bool:
        return self._cancel.is_set()


class JobManager:
    def __init__(self, history_dir: Optional[Path] = None) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = Lock()
        self._history_dir = history_dir or Path.cwd() / ".mpv-scraper"
        self._history_dir.mkdir(parents=True, exist_ok=True)

    # --- public API ---------------------------------------------------------
    def enqueue(
        self, name: str, target: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = Job(job_id=job_id, name=name, target=target, args=args, kwargs=kwargs)
        with self._lock:
            self._jobs[job_id] = job
        self._persist()

        # Wrap progress callback to record events
        def _progress(
            increment: int, total: Optional[int] = None, message: Optional[str] = None
        ) -> None:
            with self._lock:
                job.progress += int(increment)
                if total is not None:
                    job.total = int(total)
                job.events.append(
                    {
                        "type": "progress",
                        "inc": int(increment),
                        "total": job.total,
                        "message": message,
                    }
                )

        # Compose kwargs
        run_kwargs = dict(kwargs)
        run_kwargs.setdefault("progress_callback", _progress)
        run_kwargs.setdefault("should_cancel", job.should_cancel)

        # Start background thread
        t = Thread(target=self._runner, args=(job_id, run_kwargs), daemon=True)
        job._thread = t
        t.start()
        return job_id

    def observe(self, job_id: str) -> Job:
        with self._lock:
            return self._jobs[job_id]

    def cancel(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status in ("queued", "running"):
                job._cancel.set()
                job.events.append({"type": "cancel_requested"})

    # --- internal -----------------------------------------------------------
    def _runner(self, job_id: str, run_kwargs: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.events.append({"type": "start", "ts": time.time()})
            self._persist()

        try:
            job.target(*job.args, **run_kwargs)
            with self._lock:
                job.status = "cancelled" if job._cancel.is_set() else "completed"
                job.events.append({"type": job.status, "ts": time.time()})
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                job.status = "failed"
                job.error = str(exc)
                job.events.append({"type": "failed", "error": job.error})
        finally:
            self._persist()

    def _persist(self) -> None:
        # Persist a small rolling history for inspection/debugging
        out = self._history_dir / "jobs.json"
        try:
            with out.open("w", encoding="utf-8") as fh:
                json.dump(
                    {
                        jid: {
                            "name": j.name,
                            "status": j.status,
                            "progress": j.progress,
                            "total": j.total,
                            "error": j.error,
                        }
                        for jid, j in self._jobs.items()
                    },
                    fh,
                    indent=2,
                )
        except Exception:
            pass
