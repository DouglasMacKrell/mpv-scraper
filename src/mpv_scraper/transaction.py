"""Transaction logging utilities (Sprint 7.1).

`TransactionLogger` records file operations performed during a scraper run
so they can be undone later (Sprint 7.2).

Each log is a JSON Lines (ND-JSON) file to make streaming writes trivial and
append-only.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal, TypedDict, List

OperationType = Literal["create", "modify"]


class _LogEntry(TypedDict):
    timestamp: float
    op: OperationType
    path: str
    backup: str | None


class TransactionLogger:
    """Simple JSONL transaction logger."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.entries: List[_LogEntry] = []
        # Ensure directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_create(self, path: Path):
        self._record("create", path, backup=None)

    def log_modify(self, path: Path, *, backup: Path):
        self._record("modify", path, backup=str(backup))

    # Internal helpers -----------------------------------------------------
    def _record(self, op: OperationType, path: Path, backup: str | None):
        entry: _LogEntry = {
            "timestamp": time.time(),
            "op": op,
            "path": str(path),
            "backup": backup,
        }
        self.entries.append(entry)
        # Append line immediately
        with self.log_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry) + "\n")

    # Context-manager sugar
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Nothing special for now; could write summary header/footer
        return False  # propagate exceptions
