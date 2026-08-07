"""Tests for the SQLite adapter."""

import multiprocessing
import sqlite3
import tempfile
from pathlib import Path

import pytest

from actions.work_items import EmptyQueue, SQLiteAdapter, State


def _reserve_input_in_process(db_path, files_dir, start, results):
    """Reserve one input after the parent releases all competing workers."""
    adapter = SQLiteAdapter(
        db_path=db_path,
        queue_name="test_queue",
        files_dir=files_dir,
    )
    start.wait()
    try:
        results.put(("reserved", adapter.reserve_input()))
    except EmptyQueue:
        results.put(("empty", None))
    except Exception as error:
        results.put(("error", type(error).__name__))


def _concurrent_reservations(db_path, files_dir, workers):
    """Run independent SQLiteAdapter reservations at the same instant."""
    context = multiprocessing.get_context()
    start = context.Event()
    results = context.Queue()
    processes = [
        context.Process(
            target=_reserve_input_in_process,
            args=(str(db_path), str(files_dir), start, results),
        )
        for _ in range(workers)
    ]
    for process in processes:
        process.start()
    start.set()
    outcomes = [results.get(timeout=10) for _ in processes]
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0
    return outcomes


def _legacy_reserve_input_in_process(db_path, barrier, results):
    """Reproduce the former select-then-update reservation sequence."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    blocked = False

    def block_after_select(statement):
        nonlocal blocked
        if not blocked and "SELECT id FROM work_items" in statement:
            blocked = True
            barrier.wait(timeout=10)

    conn.set_trace_callback(block_after_select)
    row = conn.execute(
        """
        SELECT id FROM work_items
        WHERE queue_name = ? AND state = ?
        ORDER BY created_at ASC
        LIMIT 1
        """,
        ("test_queue", State.PENDING.value),
    ).fetchone()
    item_id = row[0]
    conn.execute(
        """
        UPDATE work_items
        SET state = ?
        WHERE id = ?
        """,
        (State.IN_PROGRESS.value, item_id),
    )
    conn.commit()
    conn.close()
    results.put(item_id)


def _legacy_concurrent_reservations(db_path):
    """Run the synchronized legacy reservation race once."""
    context = multiprocessing.get_context()
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(target=_legacy_reserve_input_in_process, args=(str(db_path), barrier, results))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    outcomes = [results.get(timeout=10) for _ in processes]
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0
    return outcomes


@pytest.fixture
def adapter():
    """Create a temporary SQLite adapter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        files_dir = Path(tmpdir) / "files"
        yield SQLiteAdapter(
            db_path=str(db_path),
            queue_name="test_queue",
            files_dir=str(files_dir),
        )


def test_seed_and_reserve(adapter):
    """Test seeding and reserving work items."""
    # Seed an item
    item_id = adapter.seed_input(
        payload={"key": "value"},
    )
    assert item_id

    # Reserve it
    reserved_id = adapter.reserve_input()
    assert reserved_id == item_id

    # No more items
    with pytest.raises(EmptyQueue):
        adapter.reserve_input()


def test_concurrent_reservation_claims_item_once(adapter):
    """Competing consumers claim one pending item once without lock errors."""
    item_id = adapter.seed_input()

    outcomes = _concurrent_reservations(adapter._db_path, adapter._files_dir, workers=2)

    assert outcomes.count(("reserved", item_id)) == 1
    assert outcomes.count(("empty", None)) == 1


def test_legacy_reservation_claims_item_twice(adapter):
    """The trace seam deterministically demonstrates the former duplicate claim."""
    item_id = adapter.seed_input()

    outcomes = _legacy_concurrent_reservations(adapter._db_path)

    assert outcomes == [item_id, item_id]


def test_reservation_locks_before_selecting_pending_item(adapter, monkeypatch):
    """Reservation obtains its write lock before reading the FIFO candidate."""
    statements = []
    original_get_conn = adapter._get_conn

    def traced_connection():
        conn = original_get_conn()
        conn.set_trace_callback(statements.append)
        return conn

    monkeypatch.setattr(adapter, "_get_conn", traced_connection)
    adapter.seed_input()

    adapter.reserve_input()

    begin_index = next(
        index for index, statement in enumerate(statements) if statement == "BEGIN IMMEDIATE"
    )
    select_index = next(
        index
        for index, statement in enumerate(statements)
        if "SELECT id FROM work_items" in statement
    )
    assert begin_index < select_index


def test_reservation_rolls_back_on_update_error(adapter, monkeypatch):
    """An update failure leaves the selected input available for a later worker."""
    item_id = adapter.seed_input()

    class FailingUpdateConnection(sqlite3.Connection):
        def execute(self, statement, parameters=()):
            if statement.lstrip().startswith("UPDATE work_items"):
                raise sqlite3.OperationalError("update failed")
            return super().execute(statement, parameters)

    def failing_connection():
        conn = sqlite3.connect(
            str(adapter._db_path), timeout=30.0, factory=FailingUpdateConnection
        )
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(adapter, "_get_conn", failing_connection)

    with pytest.raises(sqlite3.OperationalError, match="update failed"):
        adapter.reserve_input()

    monkeypatch.undo()
    assert adapter.get_item(item_id)["state"] == State.PENDING.value


def test_concurrent_reservation_preserves_fifo_for_two_items(adapter):
    """Competing consumers claim both pending items in FIFO order."""
    first_id = adapter.seed_input()
    second_id = adapter.seed_input()

    outcomes = _concurrent_reservations(adapter._db_path, adapter._files_dir, workers=2)

    assert sorted(item_id for status, item_id in outcomes if status == "reserved") == sorted(
        [first_id, second_id]
    )
    assert all(status == "reserved" for status, _ in outcomes)
    with sqlite3.connect(adapter._db_path) as conn:
        reserved_ids = [
            row[0]
            for row in conn.execute(
                "SELECT id FROM work_items WHERE state = ? ORDER BY reserved_at",
                (State.IN_PROGRESS.value,),
            )
        ]
    assert reserved_ids == [first_id, second_id]


def test_reservation_preserves_insertion_order_when_timestamps_tie(adapter, monkeypatch):
    """A shared creation timestamp still reserves the first inserted item first."""
    statements = []
    original_get_conn = adapter._get_conn

    def traced_connection():
        conn = original_get_conn()
        conn.set_trace_callback(statements.append)
        return conn

    monkeypatch.setattr(adapter, "_get_conn", traced_connection)
    monkeypatch.setattr(adapter, "_now", lambda: "2026-08-05T00:00:00+00:00")
    first_id = adapter.seed_input()
    second_id = adapter.seed_input()

    assert adapter.reserve_input() == first_id
    assert second_id != first_id
    select_statement = next(statement for statement in statements if "SELECT id FROM work_items" in statement)
    assert "ORDER BY created_at ASC, rowid ASC" in select_statement


def test_load_save_payload(adapter):
    """Test loading and saving payloads."""
    item_id = adapter.seed_input(payload={"initial": "data"})

    # Load
    payload = adapter.load_payload(item_id)
    assert payload == {"initial": "data"}

    # Save
    adapter.save_payload(item_id, {"updated": "data"})
    payload = adapter.load_payload(item_id)
    assert payload == {"updated": "data"}


@pytest.mark.parametrize("payload", [None, "text", 42, 3.5, True, False, [1, "two"], {"a": 1}])
def test_sqlite_preserves_arbitrary_json_payload(adapter, payload):
    """SQLite round-trips every supported JSON shape without wrapping it."""
    item_id = adapter.seed_input(payload=payload)

    assert adapter.load_payload(item_id) == payload
    assert adapter.get_item(item_id)["payload"] == payload
    assert adapter.list_items()[0]["payload"] == payload

    adapter.save_payload(item_id, payload)
    assert adapter.load_payload(item_id) == payload

    output_id = adapter.create_output(item_id, payload=payload)
    assert adapter.get_item(output_id)["payload"] == payload


def test_sqlite_rejects_malformed_legacy_payload(adapter):
    """Malformed stored JSON fails explicitly instead of silently changing shape."""
    item_id = adapter.seed_input(payload={})
    with adapter._get_conn() as conn:
        conn.execute("UPDATE work_items SET payload = ? WHERE id = ?", ("{broken", item_id))
        conn.commit()

    with pytest.raises(ValueError, match="Malformed stored work item payload"):
        adapter.load_payload(item_id)


def test_release_done(adapter):
    """Test releasing items as done."""
    item_id = adapter.seed_input()
    adapter.reserve_input()

    adapter.release_input(item_id, State.DONE)

    item = adapter.get_item(item_id)
    assert item["state"] == "DONE"


def test_release_failed(adapter):
    """Test releasing items as failed."""
    item_id = adapter.seed_input()
    adapter.reserve_input()

    adapter.release_input(
        item_id,
        State.FAILED,
        code="ERR001",
        message="Test error",
    )

    item = adapter.get_item(item_id)
    assert item["state"] == "FAILED"
    assert item["error_code"] == "ERR001"
    assert item["error_message"] == "Test error"


def test_create_output(adapter):
    """Test creating output items."""
    input_id = adapter.seed_input(payload={"input": "data"})
    adapter.reserve_input()

    output_id = adapter.create_output(input_id, payload={"output": "data"})

    assert output_id
    output_item = adapter.get_item(output_id)
    assert output_item["parent_id"] == input_id
    assert output_item["queue_name"] == "test_queue_output"
    assert output_item["payload"] == {"output": "data"}


def test_files(adapter):
    """Test file operations."""
    item_id = adapter.seed_input()

    # Add file
    content = b"Hello, World!"
    adapter.add_file(item_id, "test.txt", "test.txt", content)

    # List files
    files = adapter.list_files(item_id)
    assert "test.txt" in files

    # Get file
    retrieved = adapter.get_file(item_id, "test.txt")
    assert retrieved == content

    # Remove file
    adapter.remove_file(item_id, "test.txt")
    files = adapter.list_files(item_id)
    assert "test.txt" not in files


def test_list_items(adapter):
    """Test listing items."""
    # Seed multiple items
    adapter.seed_input(payload={"id": 1})
    adapter.seed_input(payload={"id": 2})
    adapter.seed_input(payload={"id": 3})

    # List all
    items = adapter.list_items()
    assert len(items) == 3

    # List by state
    pending = adapter.list_items(state=State.PENDING)
    assert len(pending) == 3

    # Reserve one
    adapter.reserve_input()
    in_progress = adapter.list_items(state=State.IN_PROGRESS)
    assert len(in_progress) == 1


def test_delete_item(adapter):
    """Test deleting items."""
    item_id = adapter.seed_input(payload={"data": "test"})
    adapter.add_file(item_id, "test.txt", "test.txt", b"content")

    adapter.delete_item(item_id)

    with pytest.raises(ValueError):
        adapter.get_item(item_id)


def test_queue_stats(adapter):
    """Test queue statistics."""
    adapter.seed_input()
    adapter.seed_input()
    adapter.seed_input()

    reserved_id = adapter.reserve_input()
    adapter.release_input(reserved_id, State.DONE)

    stats = adapter.get_queue_stats()
    assert stats["pending"] == 2
    assert stats["done"] == 1
    assert stats["total"] == 3


def test_migrates_historical_custom_schema_transactionally(tmp_path):
    """The versioned custom-adapter schema upgrades without losing item or file data."""
    db_path = tmp_path / "legacy.db"
    files_dir = tmp_path / "files"
    item_dir = files_dir / "legacy-item"
    item_dir.mkdir(parents=True)
    file_path = item_dir / "report.txt"
    file_path.write_bytes(b"legacy")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE work_items (
                id TEXT PRIMARY KEY, queue_name TEXT NOT NULL, parent_id TEXT,
                payload TEXT, state TEXT, created_at TEXT,
                exception_type TEXT, exception_code TEXT, exception_message TEXT,
                reserved_at TEXT, released_at TEXT, updated_at TEXT
            );
            CREATE TABLE work_item_files (
                work_item_id TEXT NOT NULL, filename TEXT NOT NULL,
                filepath TEXT NOT NULL UNIQUE, created_at TEXT,
                PRIMARY KEY (work_item_id, filename)
            );
            CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT);
            INSERT INTO schema_version(version) VALUES (4);
            """
        )
        conn.execute(
            """INSERT INTO work_items
            (id, queue_name, parent_id, payload, state, created_at, exception_type,
             exception_code, exception_message, reserved_at, released_at, updated_at)
            VALUES (?, ?, NULL, ?, 'RESERVED', ?, NULL, ?, ?, ?, NULL, NULL)""",
            ("legacy-item", "test_queue", '{"legacy": true}', None, "E1", "failed", "2026-01-01T00:01:00+00:00"),
        )
        conn.execute(
            "INSERT INTO work_item_files VALUES (?, ?, ?, ?)",
            ("legacy-item", "report.txt", str(file_path), "2026-01-01T00:00:00+00:00"),
        )

    migrated = SQLiteAdapter(str(db_path), "test_queue", files_dir=str(files_dir))

    item = migrated.get_item("legacy-item")
    assert item["state"] == State.IN_PROGRESS.value
    assert item["error_code"] == "E1"
    assert item["error_message"] == "failed"
    assert item["created_at"] is not None
    assert item["updated_at"] is not None
    assert migrated.get_file("legacy-item", "report.txt") == b"legacy"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 5
    SQLiteAdapter(str(db_path), "test_queue", files_dir=str(files_dir))


def test_migrates_current_unversioned_schema_without_losing_data(tmp_path):
    """The current unversioned schema is adopted and versioned in place."""
    db_path = tmp_path / "current.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE work_items (
                id TEXT PRIMARY KEY, queue_name TEXT NOT NULL, parent_id TEXT,
                state TEXT NOT NULL DEFAULT 'PENDING', payload TEXT,
                created_at TEXT NOT NULL, updated_at TEXT
            );
            CREATE TABLE work_item_files (
                id TEXT PRIMARY KEY, work_item_id TEXT NOT NULL, name TEXT NOT NULL,
                original_name TEXT NOT NULL, file_path TEXT NOT NULL, created_at TEXT NOT NULL
            );
            INSERT INTO work_items VALUES
                ('existing', 'test_queue', NULL, 'PENDING', '[1, 2]', '2026-01-01', NULL);
            """
        )

    migrated = SQLiteAdapter(str(db_path), "test_queue", files_dir=str(tmp_path / "files"))

    assert migrated.load_payload("existing") == [1, 2]
    assert migrated.reserve_input() == "existing"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 5


def test_recovery_uses_configured_orphan_timeout(tmp_path, monkeypatch):
    """SQLite orphan recovery honors RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES."""
    monkeypatch.setenv("RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES", "0")
    adapter = SQLiteAdapter(
        str(tmp_path / "items.db"), "test_queue", files_dir=str(tmp_path / "files")
    )
    item_id = adapter.seed_input()
    adapter.reserve_input()

    assert adapter.recover_orphaned_work_items() == [item_id]


def test_rejects_unknown_historical_file_schema_without_data_loss(tmp_path):
    """Unknown attachment metadata is rejected before tables are renamed or dropped."""
    db_path = tmp_path / "unknown.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE work_items (
                id TEXT PRIMARY KEY, queue_name TEXT NOT NULL, payload TEXT,
                state TEXT, created_at TEXT
            );
            CREATE TABLE work_item_files (
                work_item_id TEXT NOT NULL, opaque_reference TEXT NOT NULL
            );
            INSERT INTO work_items VALUES ('item-1', 'test_queue', '{}', 'PENDING', NULL);
            INSERT INTO work_item_files VALUES ('item-1', 'must-survive');
            """
        )

    with pytest.raises(ValueError, match="Unsupported work_item_files schema"):
        SQLiteAdapter(str(db_path), "test_queue", files_dir=str(tmp_path / "files"))

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT opaque_reference FROM work_item_files").fetchone()[0] == "must-survive"
        assert conn.execute("SELECT id FROM work_items").fetchone()[0] == "item-1"


def test_rejects_recognized_file_schema_with_unknown_extension_without_data_loss(tmp_path):
    """A known attachment layout plus an unknown column is not silently truncated."""
    db_path = tmp_path / "extended.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE work_items (
                id TEXT PRIMARY KEY, queue_name TEXT NOT NULL, payload TEXT,
                state TEXT, created_at TEXT
            );
            CREATE TABLE work_item_files (
                work_item_id TEXT NOT NULL, filename TEXT NOT NULL,
                filepath TEXT NOT NULL, created_at TEXT, retention_policy TEXT NOT NULL
            );
            INSERT INTO work_items VALUES ('item-1', 'test_queue', '{}', 'PENDING', NULL);
            INSERT INTO work_item_files VALUES
                ('item-1', 'proof.txt', '/tmp/proof.txt', NULL, 'must-survive');
            """
        )

    with pytest.raises(ValueError, match="Unsupported work_item_files schema"):
        SQLiteAdapter(str(db_path), "test_queue", files_dir=str(tmp_path / "files"))

    with sqlite3.connect(db_path) as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(work_item_files)")]
        row = conn.execute(
            "SELECT filename, retention_policy FROM work_item_files"
        ).fetchone()
        assert columns == [
            "work_item_id",
            "filename",
            "filepath",
            "created_at",
            "retention_policy",
        ]
        assert row == ("proof.txt", "must-survive")


def test_mid_migration_failure_rolls_back_schema_and_rows(tmp_path, monkeypatch):
    """An injected failure after table rename leaves the historical database untouched."""
    db_path = tmp_path / "interrupted.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE work_items (
                id TEXT PRIMARY KEY, queue_name TEXT NOT NULL, payload TEXT,
                state TEXT, created_at TEXT
            );
            INSERT INTO work_items VALUES ('item-1', 'test_queue', '{}', 'PENDING', NULL);
            """
        )

    def fail_after_rename(conn):
        raise RuntimeError("injected migration interruption")

    monkeypatch.setattr(SQLiteAdapter, "_create_schema", staticmethod(fail_after_rename))
    with pytest.raises(RuntimeError, match="injected migration interruption"):
        SQLiteAdapter(str(db_path), "test_queue", files_dir=str(tmp_path / "files"))

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT id FROM work_items").fetchone()[0] == "item-1"
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'work_items_migration_source'"
        ).fetchone() is None
