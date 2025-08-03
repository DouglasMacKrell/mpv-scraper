"""Transaction logging & undo utilities.

Extended in Sprint 7.2 with *revert_transaction* helper that consumes a
transaction log and reverses the operations in reverse order.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Literal, TypedDict, List, Union

OperationType = Literal["create", "modify"]


class _LogEntry(TypedDict):
    timestamp: float
    op: OperationType
    path: str
    backup: Union[str, None]


class TransactionLogger:
    """Simple JSONL transaction logger."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.entries: List[_LogEntry] = []
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    # Public logging helpers
    def log_create(self, path: Path):
        self._record("create", path, backup=None)

    def log_modify(self, path: Path, *, backup: Path):
        self._record("modify", path, backup=str(backup))

    # ------------------------------------------------------------------
    # Internals
    def _record(self, op: OperationType, path: Path, backup: Union[str, None]):
        entry: _LogEntry = {
            "timestamp": time.time(),
            "op": op,
            "path": str(path.resolve()),  # Use absolute path
            "backup": backup,
        }
        self.entries.append(entry)
        with self.log_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry) + "\n")

    # Context-manager helpers
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False  # propagate exceptions


# ---------------------------------------------------------------------------
# Undo helpers
# ---------------------------------------------------------------------------


def revert_transaction(log_path: Path) -> None:
    """Reverse all operations recorded in *log_path* then delete the log.

    Operations are applied *in reverse order* to faithfully undo filesystem
    changes.
    """

    if not log_path.exists():
        raise FileNotFoundError(log_path)

    # Read all lines into memory (small file) and reverse.
    with log_path.open("r", encoding="utf-8") as fp:
        lines = fp.readlines()

    for line in reversed(lines):
        entry: _LogEntry = json.loads(line)
        op = entry["op"]
        target = Path(entry["path"])
        backup = Path(entry["backup"]) if entry.get("backup") else None

        if op == "create":
            if target.exists():
                if target.is_file():
                    target.unlink()
                elif target.is_dir():
                    shutil.rmtree(target)
        elif op == "modify":
            if backup and backup.exists():
                shutil.move(str(backup), str(target))

    # Remove the log after successful revert
    log_path.unlink()
