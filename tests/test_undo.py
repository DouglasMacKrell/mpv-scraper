from pathlib import Path
import json

from mpv_scraper.transaction import TransactionLogger


def test_log_file_creation(tmp_path: Path):
    log_path = tmp_path / "transaction.log"
    target = tmp_path / "new_file.png"

    with TransactionLogger(log_path) as logger:
        logger.log_create(target)

    # Read back last line
    last = json.loads(log_path.read_text().strip())
    assert last["op"] == "create"
    assert last["path"] == str(target)
    assert last["backup"] is None


def test_log_file_modification(tmp_path: Path):
    log_path = tmp_path / "transaction.log"
    target = tmp_path / "existing.xml"
    backup = tmp_path / "existing.bak"

    with TransactionLogger(log_path) as logger:
        logger.log_modify(target, backup=backup)

    last = json.loads(log_path.read_text().strip().split("\n")[-1])
    assert last["op"] == "modify"
    assert last["backup"] == str(backup)
