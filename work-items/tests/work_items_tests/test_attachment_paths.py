"""Regression tests for filesystem attachment boundaries."""

import sqlite3
from pathlib import Path

import pytest

from actions.work_items import FileAdapter, SQLiteAdapter
from actions.work_items._paths import (
    resolve_attachment_path,
    resolve_item_directory,
    validate_attachment_name,
)


@pytest.mark.parametrize(
    "name",
    [
        "../x", "/tmp/x", "nested/x", r"nested\\x", ".", "..", "", "nul\x00x", "line\r\n", 'quote".txt'
    ],
)
def test_rejects_unsafe_attachment_names(name: str) -> None:
    """Reject names that could escape storage or produce unsafe headers."""
    with pytest.raises(ValueError):
        validate_attachment_name(name)


def test_rejects_uncontained_item_id_and_persisted_path(tmp_path: Path) -> None:
    """Keep caller IDs, JSON IDs, database paths, and symlinks inside storage."""
    storage_root = tmp_path / "storage"
    sentinel = tmp_path / "outside.txt"
    sentinel.write_bytes(b"unchanged")

    with pytest.raises(ValueError):
        resolve_item_directory(storage_root, "../outside")

    item_root = resolve_item_directory(storage_root, "safe-item")
    item_root.mkdir(parents=True)
    escape = item_root / "escape.txt"
    escape.symlink_to(sentinel)
    with pytest.raises(ValueError):
        resolve_attachment_path(item_root, "escape.txt")

    file_adapter = FileAdapter(
        input_path=str(tmp_path / "input"), output_path=str(tmp_path / "output")
    )
    file_adapter._input_items.append({"id": "../outside", "payload": {}, "files": []})
    with pytest.raises(ValueError):
        file_adapter.add_file("../outside", "safe.txt", "safe.txt", b"blocked")

    adapter = SQLiteAdapter(
        db_path=str(tmp_path / "workitems.db"), files_dir=str(storage_root)
    )
    item_id = adapter.seed_input()
    adapter.add_file(item_id, "safe.txt", "safe.txt", b"safe")
    with sqlite3.connect(tmp_path / "workitems.db") as conn:
        conn.execute(
            "UPDATE work_item_files SET file_path = ? WHERE work_item_id = ?",
            (str(sentinel), item_id),
        )
    with pytest.raises(ValueError):
        adapter.get_file(item_id, "safe.txt")
    with pytest.raises(ValueError):
        adapter.remove_file(item_id, "safe.txt")

    assert sentinel.read_bytes() == b"unchanged"
