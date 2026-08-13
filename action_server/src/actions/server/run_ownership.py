"""Durable ownership and control coordination for Action Runs.

The execution handle remains process-local.  This store contains only the
server-issued owner lease and durable control intent, so another Runtime can
observe or control a run without addressing the owning process directly.
"""

from dataclasses import dataclass
import sqlite3
import time
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RunLease:
    run_id: str
    owner_id: str
    epoch: int
    expires_at: float


@dataclass(frozen=True)
class RunOwnership:
    run_id: str
    owner_id: Optional[str]
    epoch: int
    expires_at: Optional[float]
    control: Optional[str]
    status: str


class RunOwnershipStore:
    """SQLite-backed lease/control store shared by Runtime processes."""

    def __init__(
        self, db_path: str | Path, *, owner_id: str, lease_seconds: float = 30.0
    ) -> None:
        if not owner_id:
            raise ValueError("owner_id is required")
        self.db_path = str(db_path)
        self.owner_id = owner_id
        self.lease_seconds = lease_seconds
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS run_ownership (
                    run_id TEXT PRIMARY KEY,
                    owner_id TEXT,
                    owner_epoch INTEGER NOT NULL DEFAULT 0,
                    lease_expires_at REAL,
                    control TEXT,
                    status TEXT NOT NULL DEFAULT 'not_run'
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        db.execute("PRAGMA busy_timeout = 30000")
        return db

    def create_run(self, run_id: str) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO run_ownership(run_id) VALUES (?) ON CONFLICT(run_id) DO NOTHING",
                (run_id,),
            )

    def get(self, run_id: str) -> RunOwnership:
        with self._connect() as db:
            row = db.execute(
                "SELECT run_id, owner_id, owner_epoch, lease_expires_at, control, status "
                "FROM run_ownership WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return RunOwnership(*row)

    def claim(self, run_id: str) -> RunLease:
        now = time.time()
        expires_at = now + self.lease_seconds
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT owner_id, owner_epoch, lease_expires_at FROM run_ownership "
                    "WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(run_id)
                current_owner, current_epoch, current_expiry = row
                if current_owner not in (None, self.owner_id) and (
                    current_expiry is not None and current_expiry > now
                ):
                    raise RuntimeError(
                        f"run {run_id} is owned by another live Runtime"
                    )
                epoch = current_epoch + 1
                db.execute(
                    "UPDATE run_ownership SET owner_id=?, owner_epoch=?, lease_expires_at=? "
                    "WHERE run_id=?",
                    (self.owner_id, epoch, expires_at, run_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
        return RunLease(run_id, self.owner_id, epoch, expires_at)

    def renew(self, run_id: str, epoch: int) -> bool:
        with self._connect() as db:
            result = db.execute(
                "UPDATE run_ownership SET lease_expires_at=? WHERE run_id=? "
                "AND owner_id=? AND owner_epoch=?",
                (time.time() + self.lease_seconds, run_id, self.owner_id, epoch),
            )
        return result.rowcount == 1

    def request_cancel(self, run_id: str) -> bool:
        with self._connect() as db:
            result = db.execute(
                "UPDATE run_ownership SET control='cancel' WHERE run_id=? "
                "AND status IN ('not_run', 'running')",
                (run_id,),
            )
        return result.rowcount == 1

    def set_status(self, run_id: str, epoch: int, status: str) -> bool:
        with self._connect() as db:
            result = db.execute(
                "UPDATE run_ownership SET status=? WHERE run_id=? AND owner_id=? "
                "AND owner_epoch=?",
                (status, run_id, self.owner_id, epoch),
            )
        return result.rowcount == 1

    def control_requested(self, run_id: str, epoch: int) -> Optional[str]:
        with self._connect() as db:
            row = db.execute(
                "SELECT control FROM run_ownership WHERE run_id=? AND owner_id=? "
                "AND owner_epoch=? AND lease_expires_at > ?",
                (run_id, self.owner_id, epoch, time.time()),
            ).fetchone()
        return row[0] if row else None

    def reconcile(self, run_id: str, epoch: int, status: str) -> str:
        if status not in {"not_run", "running"}:
            raise ValueError("only active run states can be reconciled")
        with self._connect() as db:
            result = db.execute(
                "UPDATE run_ownership SET status='reconciled', control=NULL "
                "WHERE run_id=? AND owner_id=? AND owner_epoch=?",
                (run_id, self.owner_id, epoch),
            )
        return "reconciled" if result.rowcount == 1 else "stale"

    def release(self, run_id: str, epoch: int) -> bool:
        with self._connect() as db:
            result = db.execute(
                "UPDATE run_ownership SET owner_id=NULL, lease_expires_at=NULL "
                "WHERE run_id=? AND owner_id=? AND owner_epoch=?",
                (run_id, self.owner_id, epoch),
            )
        return result.rowcount == 1
