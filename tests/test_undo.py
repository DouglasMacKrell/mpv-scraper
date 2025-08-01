from pathlib import Path
import json


from mpv_scraper.transaction import TransactionLogger, revert_transaction


def test_log_file_creation(tmp_path: Path):
    log_path = tmp_path / "transaction.log"
    target = tmp_path / "new_file.txt"

    with TransactionLogger(log_path) as logger:
        logger.log_create(target)

    entry = json.loads(log_path.read_text().strip())
    assert entry["op"] == "create"
    assert entry["path"] == str(target)


def test_log_file_modification(tmp_path: Path):
    log_path = tmp_path / "transaction.log"
    target = tmp_path / "existing.txt"
    backup = tmp_path / "existing.bak"

    with TransactionLogger(log_path) as logger:
        logger.log_modify(target, backup=backup)

    last = json.loads(log_path.read_text().strip())
    assert last["op"] == "modify"
    assert last["backup"] == str(backup)


def test_undo_reverts_created_files(tmp_path: Path):
    log_path = tmp_path / "transaction.log"
    created = tmp_path / "temp.txt"
    created.write_text("dummy")

    with TransactionLogger(log_path) as logger:
        logger.log_create(created)

    assert created.exists()
    revert_transaction(log_path)
    assert not created.exists()
    assert not log_path.exists()


def test_undo_restores_modified_files(tmp_path: Path):
    log_path = tmp_path / "transaction.log"
    orig = tmp_path / "file.txt"
    backup = tmp_path / "file.bak"

    orig.write_text("new")
    backup.write_text("old")

    with TransactionLogger(log_path) as logger:
        logger.log_modify(orig, backup=backup)

    # Ensure orig has new content before undo
    assert orig.read_text() == "new"

    revert_transaction(log_path)

    # After undo, orig should contain old content, backup removed
    assert orig.read_text() == "old"
    assert not backup.exists()
    assert not log_path.exists()
