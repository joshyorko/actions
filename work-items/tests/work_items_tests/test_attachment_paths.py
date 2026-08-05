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


@pytest.mark.parametrize("item_id", ["", "."])
def test_rejects_storage_root_item_ids_without_deleting_sentinels(
    tmp_path: Path, item_id: str
) -> None:
    """Never let a root-valued ID delete sibling or outside storage."""
    storage_root = tmp_path / "storage"
    sibling_sentinel = storage_root / "safe-item" / "keep.txt"
    outside_sentinel = tmp_path / "outside.txt"
    sibling_sentinel.parent.mkdir(parents=True)
    sibling_sentinel.write_bytes(b"sibling")
    outside_sentinel.write_bytes(b"outside")

    adapter = SQLiteAdapter(
        db_path=str(tmp_path / "workitems.db"), files_dir=str(storage_root)
    )
    with sqlite3.connect(tmp_path / "workitems.db") as conn:
        conn.execute(
            """
            INSERT INTO work_items (id, queue_name, state, created_at, updated_at)
            VALUES (?, 'default', 'PENDING', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')
            """,
            (item_id,),
        )

    with pytest.raises(ValueError):
        adapter.delete_item(item_id)

    assert sibling_sentinel.read_bytes() == b"sibling"
    assert outside_sentinel.read_bytes() == b"outside"


def test_delete_item_rejects_persisted_escaped_path_without_removing_files(
    tmp_path: Path,
) -> None:
    """Reject compromised paths before deleting an otherwise valid item directory."""
    storage_root = tmp_path / "storage"
    outside_sentinel = tmp_path / "outside.txt"
    outside_sentinel.write_bytes(b"outside")
    adapter = SQLiteAdapter(
        db_path=str(tmp_path / "workitems.db"), files_dir=str(storage_root)
    )
    item_id = adapter.seed_input()
    adapter.add_file(item_id, "safe.txt", "safe.txt", b"safe")
    safe_file = storage_root / item_id / "safe.txt"
    with sqlite3.connect(tmp_path / "workitems.db") as conn:
        conn.execute(
            "UPDATE work_item_files SET file_path = ? WHERE work_item_id = ?",
            (str(outside_sentinel), item_id),
        )

    with pytest.raises(ValueError):
        adapter.delete_item(item_id)

    assert outside_sentinel.read_bytes() == b"outside"
    assert safe_file.read_bytes() == b"safe"
