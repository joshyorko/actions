"""SQLite adapter for work item storage.

This provides a file-based, cross-platform storage backend for work items
using SQLite. It supports multiple queues, file attachments, and full
work item lifecycle management.
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .._exceptions import EmptyQueue
from .._paths import resolve_attachment_path, resolve_item_directory
from .._types import ExceptionType, JSONType, State
from ._base import BaseAdapter

log = logging.getLogger(__name__)


class SQLiteAdapter(BaseAdapter):
    """SQLite-based storage adapter for work items.

    This adapter stores work items in a SQLite database with file
    attachments stored on the filesystem. It supports:
    - Multiple queues
    - FIFO ordering
    - File attachments
    - Full lifecycle tracking
    """

    def __init__(
        self,
        db_path: str | None = None,
        queue_name: str = "default",
        output_queue_name: str | None = None,
        files_dir: str = "./work_item_files",
    ):
        """Initialize the SQLite adapter.

        Args:
            db_path: Path to SQLite database file.
            queue_name: Name of the input queue.
            output_queue_name: Name of the output queue (default: {queue_name}_output).
            files_dir: Directory for file attachments.
        """
        self._db_path = Path(db_path or os.environ.get("RC_WORKITEM_DB_PATH", "./workitems.db"))
        self._queue_name = queue_name or os.environ.get("RC_WORKITEM_QUEUE_NAME", "default")
        self._output_queue_name = (
            output_queue_name
            or os.environ.get("RC_WORKITEM_OUTPUT_QUEUE_NAME")
            or f"{self._queue_name}_output"
        )
        self._files_dir = Path(files_dir or os.environ.get("RC_WORKITEM_FILES_DIR", "./work_item_files"))

        # Ensure directories exist
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._files_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS work_items (
                    id TEXT PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    parent_id TEXT,
                    state TEXT NOT NULL DEFAULT 'PENDING',
                    payload TEXT,
                    exception_type TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    reserved_at TEXT,
                    released_at TEXT,
                    FOREIGN KEY (parent_id) REFERENCES work_items(id)
                );

                CREATE INDEX IF NOT EXISTS idx_work_items_queue_state
                ON work_items(queue_name, state);

                CREATE INDEX IF NOT EXISTS idx_work_items_parent
                ON work_items(parent_id);

                CREATE TABLE IF NOT EXISTS work_item_files (
                    id TEXT PRIMARY KEY,
                    work_item_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (work_item_id) REFERENCES work_items(id)
                );

                CREATE INDEX IF NOT EXISTS idx_work_item_files_item
                ON work_item_files(work_item_id);

                CREATE UNIQUE INDEX IF NOT EXISTS idx_work_item_files_name
                ON work_item_files(work_item_id, name);
            """
            )
            conn.commit()

            # Backwards-compatible migration from legacy schema in older copies.
            existing = {
                row[1]
                for row in conn.execute("PRAGMA table_info(work_items)")
            }
            if "updated_at" not in existing:
                conn.execute("ALTER TABLE work_items ADD COLUMN updated_at TEXT")
            if "exception_type" not in existing:
                conn.execute("ALTER TABLE work_items ADD COLUMN exception_type TEXT")
            if "error_code" not in existing:
                conn.execute("ALTER TABLE work_items ADD COLUMN error_code TEXT")
            if "error_message" not in existing:
                conn.execute("ALTER TABLE work_items ADD COLUMN error_message TEXT")
            if "reserved_at" not in existing:
                conn.execute("ALTER TABLE work_items ADD COLUMN reserved_at TEXT")
            if "released_at" not in existing:
                conn.execute("ALTER TABLE work_items ADD COLUMN released_at TEXT")
            conn.commit()

            # Normalize legacy reserved state if present.
            conn.execute(
                "UPDATE work_items SET state = ? WHERE state = ?",
                (State.IN_PROGRESS.value, "RESERVED"),
            )
            conn.commit()

    def _now(self) -> str:
        """Get current UTC timestamp as ISO string."""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _public_state(db_state: str) -> str:
        """Normalize DB state to API/public state values."""
        if db_state == "RESERVED":
            return State.IN_PROGRESS.value
        return db_state

    def _normalize_payload(self, payload: str | None) -> JSONType:
        if payload is None:
            return None
        try:
            return json.loads(payload)
        except (TypeError, ValueError) as error:
            raise ValueError("Malformed stored work item payload") from error

    def _require_item(self, conn: sqlite3.Connection, item_id: str) -> None:
        if conn.execute("SELECT 1 FROM work_items WHERE id = ?", (item_id,)).fetchone() is None:
            raise ValueError(f"Work item not found: {item_id}")

    def _item_directory(self, item_id: str) -> Path:
        return resolve_item_directory(self._files_dir, item_id)

    def _stored_attachment_path(self, item_id: str, name: str, file_path: str) -> Path:
        expected = resolve_attachment_path(self._item_directory(item_id), name)
        if Path(file_path).resolve() != expected:
            raise ValueError(f"Invalid stored attachment path for {name}")
        return expected

    def reserve_input(self) -> str:
        """Reserve the next available input work item."""
        with self._get_conn() as conn:
            for _ in range(3):
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    row = conn.execute(
                        """
                        SELECT id FROM work_items
                        WHERE queue_name = ? AND state = ?
                        ORDER BY created_at ASC, rowid ASC
                        LIMIT 1
                        """,
                        (self._queue_name, State.PENDING.value),
                    ).fetchone()

                    if row is None:
                        conn.rollback()
                        raise EmptyQueue(f"No work items available in queue: {self._queue_name}")

                    item_id = row["id"]
                    now = self._now()
                    cursor = conn.execute(
                        """
                        UPDATE work_items
                        SET state = ?, reserved_at = ?, updated_at = ?
                        WHERE id = ? AND queue_name = ? AND state = ?
                        """,
                        (
                            State.IN_PROGRESS.value,
                            now,
                            now,
                            item_id,
                            self._queue_name,
                            State.PENDING.value,
                        ),
                    )
                    if cursor.rowcount == 1:
                        conn.commit()
                        log.debug("Reserved work item %s from queue %s", item_id, self._queue_name)
                        return item_id
                    conn.rollback()
                except Exception:
                    if conn.in_transaction:
                        conn.rollback()
                    raise

            raise EmptyQueue(f"No work items available in queue: {self._queue_name}")

    def release_input(
        self,
        item_id: str,
        state: State,
        exception_type: ExceptionType | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        """Release a reserved input work item."""
        if state not in {State.DONE, State.FAILED}:
            raise ValueError(f"Release state must be DONE or FAILED, got {state}")

        if state == State.FAILED and not message:
            raise ValueError("Exception details required when state=FAILED")

        now = self._now()
        if exception_type is not None:
            exception_code = exception_type.value if hasattr(exception_type, "value") else str(exception_type)
        else:
            exception_code = None

        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE work_items
                SET state = ?,
                    exception_type = ?,
                    error_code = ?,
                    error_message = ?,
                    released_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    state.value,
                    exception_code,
                    code,
                    message,
                    now,
                    now,
                    item_id,
                ),
            )
            conn.commit()

        log.debug("Released work item %s with state %s", item_id, state.value)

    def create_output(
        self,
        parent_id: str,
        payload: JSONType | None = None,
    ) -> str:
        """Create a new output work item."""
        item_id = str(uuid.uuid4())
        now = self._now()
        payload_json = json.dumps(payload) if payload is not None else None

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO work_items
                (id, queue_name, parent_id, state, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    self._output_queue_name,
                    parent_id,
                    State.PENDING.value,
                    payload_json,
                    now,
                    now,
                ),
            )
            conn.commit()

        log.debug("Created output work item %s in queue %s", item_id, self._output_queue_name)
        return item_id

    def seed_input(
        self,
        payload: JSONType | None = None,
        files: dict[str, bytes] | None = None,
        queue_name: str | None = None,
    ) -> str:
        """Seed a new input work item into the queue."""
        item_id = str(uuid.uuid4())
        now = self._now()
        target_queue = queue_name or self._queue_name
        payload_json = json.dumps(payload) if payload is not None else None

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO work_items
                (id, queue_name, state, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    target_queue,
                    State.PENDING.value,
                    payload_json,
                    now,
                    now,
                ),
            )
            conn.commit()

        for name, content in (files or {}).items():
            self.add_file(item_id, name, name, content)

        log.info("Seeded work item %s into queue %s", item_id, target_queue)
        return item_id

    def load_payload(self, item_id: str) -> JSONType:
        """Load the payload of a work item."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT payload FROM work_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()

            if row is None:
                raise ValueError(f"Work item not found: {item_id}")

            payload_json = row["payload"]
            return self._normalize_payload(payload_json)

    def save_payload(self, item_id: str, payload: JSONType) -> None:
        """Save the payload of a work item."""
        payload_json = json.dumps(payload) if payload is not None else None
        now = self._now()

        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                UPDATE work_items
                SET payload = ?, updated_at = ?
                WHERE id = ?
                """,
                (payload_json, now, item_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Work item not found: {item_id}")
            conn.commit()

        log.debug("Saved payload for work item %s", item_id)

    def list_files(self, item_id: str) -> list[str]:
        """List files attached to a work item."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT name FROM work_item_files WHERE work_item_id = ? ORDER BY name",
                (item_id,),
            )
            return [row["name"] for row in cursor.fetchall()]

    def get_file(self, item_id: str, name: str) -> bytes:
        """Get file content from a work item."""
        resolve_attachment_path(self._item_directory(item_id), name)
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT file_path FROM work_item_files WHERE work_item_id = ? AND name = ?",
                (item_id, name),
            )
            row = cursor.fetchone()

            if row is None:
                raise FileNotFoundError(f"File not found: {name} in work item {item_id}")

            file_path = self._stored_attachment_path(item_id, name, row["file_path"])
            if not file_path.exists():
                raise ValueError(f"File missing from filesystem: {file_path}")

            return file_path.read_bytes()

    def add_file(
        self,
        item_id: str,
        name: str,
        original_name: str,
        content: bytes,
    ) -> None:
        """Add a file to a work item."""
        with self._get_conn() as conn:
            self._require_item(conn, item_id)
            item_dir = self._item_directory(item_id)
            file_path = resolve_attachment_path(item_dir, name)
            existing = conn.execute(
                "SELECT id FROM work_item_files WHERE work_item_id = ? AND name = ?",
                (item_id, name),
            ).fetchone()
            if existing is not None:
                raise FileExistsError(f"File already exists: {name} in work item {item_id}")

            item_dir.mkdir(parents=True, exist_ok=True)
            file_id = str(uuid.uuid4())
            now = self._now()
            file_path.write_bytes(content)
            conn.execute(
                """
                INSERT INTO work_item_files
                (id, work_item_id, name, original_name, file_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_id, item_id, name, original_name or name, str(file_path), now),
            )
            conn.commit()

            log.debug("Added file %s to work item %s", name, item_id)

    def remove_file(self, item_id: str, name: str) -> None:
        """Remove a file from a work item."""
        resolve_attachment_path(self._item_directory(item_id), name)
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT file_path FROM work_item_files WHERE work_item_id = ? AND name = ?",
                (item_id, name),
            )
            row = cursor.fetchone()
            if row is None:
                raise FileNotFoundError(f"File not found: {name} (work item: {item_id})")

            file_path = self._stored_attachment_path(item_id, name, row["file_path"])
            if file_path.exists():
                file_path.unlink()

            conn.execute(
                "DELETE FROM work_item_files WHERE work_item_id = ? AND name = ?",
                (item_id, name),
            )
            conn.commit()

            log.debug("Removed file %s from work item %s", name, item_id)

    def list_items(
        self,
        queue_name: str | None = None,
        state: State | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List work items in a queue."""
        target_queue = queue_name or self._queue_name
        query = "SELECT * FROM work_items WHERE queue_name = ?"
        params: list[Any] = [target_queue]

        if state is not None:
            if state == State.IN_PROGRESS:
                query += " AND (state = ? OR state = 'RESERVED')"
                params.append(State.IN_PROGRESS.value)
            else:
                query += " AND state = ?"
                params.append(state.value)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            cursor = conn.execute(query, params)
            items: list[dict[str, Any]] = []
            for row in cursor.fetchall():
                item = dict(row)
                item["id"] = item.pop("id")
                item["state"] = self._public_state(item["state"])
                item["payload"] = self._normalize_payload(item.get("payload"))
                item["files"] = self._files_for_item(item["id"])
                items.append(item)
            return items

    def _files_for_item(self, item_id: str) -> list[str]:
        return self.list_files(item_id)

    def get_item(self, item_id: str) -> dict[str, Any]:
        """Get detailed info about a work item."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM work_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Work item not found: {item_id}")

            item = dict(row)
            item["id"] = item.pop("id")
            item["state"] = self._public_state(item["state"])
            item["payload"] = self._normalize_payload(item.get("payload"))
            item["files"] = self.list_files(item_id)
            if item.get("created_at") is None:
                item["created_at"] = self._now()
            if item.get("updated_at") is None:
                item["updated_at"] = item.get("created_at")
            item.setdefault("error_code", item.get("error_code"))
            item.setdefault("error_message", item.get("error_message"))
            return item

    def delete_item(self, item_id: str) -> None:
        """Delete a work item and its files."""
        with self._get_conn() as conn:
            self._require_item(conn, item_id)
            item_dir = self._item_directory(item_id)
            for row in conn.execute(
                "SELECT name, file_path FROM work_item_files WHERE work_item_id = ?", (item_id,)
            ):
                self._stored_attachment_path(item_id, row["name"], row["file_path"])

            if item_dir.exists():
                import shutil

                shutil.rmtree(item_dir)

            conn.execute(
                "DELETE FROM work_item_files WHERE work_item_id = ?",
                (item_id,),
            )
            conn.execute(
                "DELETE FROM work_items WHERE id = ?",
                (item_id,),
            )
            conn.commit()

        log.info("Deleted work item %s", item_id)

    def get_queue_stats(self, queue_name: str | None = None) -> dict[str, int]:
        """Get statistics for a queue."""
        target_queue = queue_name or self._queue_name

        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT state, COUNT(*) as count
                FROM work_items
                WHERE queue_name = ?
                GROUP BY state
                """,
                (target_queue,),
            )

            stats = {
                "pending": 0,
                "in_progress": 0,
                "done": 0,
                "failed": 0,
                "total": 0,
            }

            for row in cursor.fetchall():
                state = row["state"]
                state_value = self._public_state(state)
                count = row["count"]
                if state_value == State.PENDING.value:
                    stats["pending"] += count
                elif state_value == State.IN_PROGRESS.value:
                    stats["in_progress"] += count
                elif state_value == State.DONE.value:
                    stats["done"] += count
                elif state_value == State.FAILED.value:
                    stats["failed"] += count
                stats["total"] += count

            return stats

    def recover_orphaned_work_items(self) -> list[str]:
        """Recover orphaned work items and return recovered IDs."""
        cutoff = datetime.now(timezone.utc).timestamp() - (30 * 60)
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id FROM work_items
                WHERE state = ? AND reserved_at IS NOT NULL
                """,
                (State.IN_PROGRESS.value,),
            ).fetchall()

            recovered: list[str] = []
            for row in rows:
                reserved_at = row["reserved_at"]
                if not reserved_at:
                    continue
                try:
                    reserved_ts = datetime.fromisoformat(reserved_at).timestamp()
                except (TypeError, ValueError):
                    continue
                if reserved_ts < cutoff:
                    item_id = row["id"]
                    conn.execute(
                        """
                        UPDATE work_items
                        SET state = ?, reserved_at = NULL
                        WHERE id = ?
                        """,
                        (State.PENDING.value, item_id),
                    )
                    recovered.append(item_id)

            conn.commit()
            return recovered
