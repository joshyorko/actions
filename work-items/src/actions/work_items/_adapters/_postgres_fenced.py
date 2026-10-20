"""Opt-in private PostgreSQL FencedQueue, not a legacy ManagedAdapter.

One authoritative Work Item row owns the business state and claim. No queue is
selected implicitly. The operator supplies a DSN and a dedicated owned schema;
initialization is explicit and refuses to adopt existing tables. This format is
independent of SQLite schema 6. There is no automatic cross-backend migration,
remote authentication, external effect executor, or exactly-once guarantee.
"""

import json
import re
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import uuid4

from .._exceptions import EmptyQueue
from .._fencing import (
    ClaimRejected,
    QueueStorageError,
    ReceiptVerifier,
    RetryEvidence,
    WorkItemClaim,
    retry_record,
    validate_lease,
    validate_owner,
    verify_retry,
)
from .._types import JSONType, State

SCHEMA_VERSION = 1
FORMAT = "actions.work-items.fenced-postgresql/v1"
_CLOCK_MS = "floor(extract(epoch FROM clock_timestamp())*1000)::bigint"


class PostgreSQLFencedQueue:
    def __init__(
        self,
        dsn: str,
        *,
        schema: str,
        queue_name: str = "default",
        output_queue_name: str | None = None,
    ):
        if not isinstance(dsn, str) or not 0 < len(dsn) <= 8192:
            raise ValueError("trusted PostgreSQL connection configuration required")
        if not isinstance(schema, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", schema):
            raise ValueError("canonical dedicated schema required")
        self._validate_queue(queue_name)
        output_queue_name = output_queue_name or queue_name + "_output"
        self._validate_queue(output_queue_name)
        self._dsn = dsn
        self._schema = schema
        self._queue_name = queue_name
        self._output_queue_name = output_queue_name
        # Identifier interpolation follows the strict schema parser above. All
        # business values use driver parameters; callers cannot supply SQL.
        self._table = f'"{schema}".work_items'
        self._metadata = f'"{schema}".fenced_queue_schema'
        self._retry_log = f'"{schema}".actions_fenced_retry_v1'

    @staticmethod
    def _validate_queue(value: str) -> None:
        if not isinstance(value, str) or not 0 < len(value) <= 256:
            raise ValueError("bounded explicit queue identity required")

    @contextmanager
    def _transaction(self, *, check_schema: bool = True):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError:
            raise RuntimeError("Install the locked actions-work-items postgres extra") from None
        try:
            with psycopg.connect(
                self._dsn,
                connect_timeout=5,
                row_factory=dict_row,
                options="-c statement_timeout=5000 -c lock_timeout=5000",
            ) as conn:
                if check_schema:
                    self._check_schema(conn)
                yield conn
        except psycopg.Error:
            raise QueueStorageError("Work Item PostgreSQL operation unavailable") from None

    def _check_schema(self, conn: Any) -> None:
        row = conn.execute(
            f"SELECT version,format FROM {self._metadata} WHERE singleton=1 FOR SHARE"
        ).fetchone()
        if row is None or row["version"] != SCHEMA_VERSION or row["format"] != FORMAT:
            raise ValueError("Unsupported fenced PostgreSQL schema; no automatic migration")
        present = conn.execute("SELECT to_regclass(%s) AS present", (self._retry_log,)).fetchone()
        if present is None or present["present"] is None:
            raise ValueError("Incomplete fenced PostgreSQL schema; no automatic migration")

    def initialize_empty_schema(self) -> None:
        """Initialize only an empty schema owned by this connection's DB role.

        No schema/database is created or existing Work Items adopted. Compatible
        repeat initialization validates the format; it does not migrate it.
        """
        with self._transaction(check_schema=False) as conn:
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                ("actions.fenced-schema:" + self._schema,),
            )
            owner = conn.execute(
                "SELECT pg_get_userbyid(nspowner)=current_user AS owned FROM pg_namespace WHERE nspname=%s",
                (self._schema,),
            ).fetchone()
            if owner is None or not owner["owned"]:
                raise ValueError("An existing owned dedicated schema is required")
            objects = conn.execute(
                "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relkind IN ('r','p','v','m','f','S')",
                (self._schema,),
            ).fetchall()
            if objects:
                if {row["relname"] for row in objects} != {
                    "work_items",
                    "fenced_queue_schema",
                    "actions_fenced_retry_v1",
                }:
                    raise ValueError("Refusing to adopt or migrate a nonempty schema")
                self._check_schema(conn)
                return
            conn.execute(
                f"CREATE TABLE {self._metadata} (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL, format TEXT NOT NULL)"
            )
            conn.execute(f"""CREATE TABLE {self._table} (
                id TEXT PRIMARY KEY, queue_name TEXT NOT NULL, parent_id TEXT REFERENCES {self._table}(id),
                state TEXT NOT NULL, payload JSONB, error_message TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
                reserved_at TIMESTAMPTZ, released_at TIMESTAMPTZ,
                claim_owner TEXT, claim_epoch BIGINT NOT NULL DEFAULT 0 CHECK(claim_epoch>=0),
                claim_deadline_ms BIGINT
            )""")
            conn.execute(f"CREATE INDEX ON {self._table} (queue_name,state,created_at,id)")
            conn.execute(
                f"CREATE TABLE {self._retry_log} (item_id TEXT NOT NULL REFERENCES {self._table}(id), epoch BIGINT NOT NULL, record JSONB NOT NULL, format TEXT NOT NULL CHECK(format='actions.work-item-retry/v1'), created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY(item_id,epoch))"
            )
            conn.execute(f"INSERT INTO {self._metadata} VALUES (1,%s,%s)", (SCHEMA_VERSION, FORMAT))

    def seed_input(self, payload: JSONType | None = None) -> str:
        serialized = json.dumps(payload, allow_nan=False)
        if len(serialized.encode()) > 256 * 1024:
            raise ValueError("input payload byte limit exceeded")
        item = str(uuid4())
        with self._transaction() as conn:
            conn.execute(
                f"INSERT INTO {self._table}(id,queue_name,state,payload) VALUES (%s,%s,%s,%s::jsonb)",
                (item, self._queue_name, State.PENDING.value, serialized),
            )
        return item

    def reserve_fenced(self, owner_id: str, *, lease_seconds: int) -> WorkItemClaim:
        validate_owner(owner_id)
        validate_lease(lease_seconds)
        with self._transaction() as conn:
            row = conn.execute(
                f"""WITH candidate AS (
                SELECT id FROM {self._table} WHERE queue_name=%s AND
                (state=%s OR (state=%s AND claim_epoch>0 AND claim_deadline_ms<={_CLOCK_MS}))
                ORDER BY created_at,id LIMIT 1 FOR UPDATE SKIP LOCKED
            ) UPDATE {self._table} w SET state=%s,claim_owner=%s,claim_epoch=w.claim_epoch+1,
                claim_deadline_ms={_CLOCK_MS}+%s, reserved_at=clock_timestamp(),updated_at=clock_timestamp()
                FROM candidate c WHERE w.id=c.id RETURNING w.id,w.claim_epoch""",
                (
                    self._queue_name,
                    State.PENDING.value,
                    State.IN_PROGRESS.value,
                    State.IN_PROGRESS.value,
                    owner_id,
                    lease_seconds * 1000,
                ),
            ).fetchone()
            if row is None:
                raise EmptyQueue("No claimable Work Item")
            return WorkItemClaim(row["id"], owner_id, row["claim_epoch"])

    def _require_claim(self, conn: Any, claim: WorkItemClaim) -> None:
        if not isinstance(claim, WorkItemClaim):
            raise ClaimRejected("typed Work Item claim required")
        row = conn.execute(
            f"""SELECT id FROM {self._table} WHERE id=%s AND queue_name=%s AND state=%s
            AND claim_owner=%s AND claim_epoch=%s AND claim_deadline_ms>{_CLOCK_MS} FOR UPDATE""",
            (claim.item_id, self._queue_name, State.IN_PROGRESS.value, claim.owner_id, claim.epoch),
        ).fetchone()
        if row is None:
            raise ClaimRejected("Work Item claim is not current")

    def renew_fenced(self, claim: WorkItemClaim, *, lease_seconds: int) -> None:
        validate_lease(lease_seconds)
        with self._transaction() as conn:
            self._require_claim(conn, claim)
            changed = conn.execute(
                f"""UPDATE {self._table} SET claim_deadline_ms={_CLOCK_MS}+%s
                WHERE id=%s AND claim_deadline_ms>{_CLOCK_MS}""",
                (lease_seconds * 1000, claim.item_id),
            )
            if changed.rowcount != 1:
                raise ClaimRejected("Work Item claim expired during renewal")

    def finish_fenced(
        self,
        claim: WorkItemClaim,
        state: State,
        *,
        outputs: tuple[JSONType, ...] = (),
        message: str | None = None,
    ) -> list[str]:
        if state not in (State.DONE, State.FAILED) or (state == State.FAILED and not message):
            raise ValueError("DONE or FAILED with failure message required")
        if len(outputs) > 64:
            raise ValueError("at most 64 output Work Items")
        serialized = [json.dumps(payload, allow_nan=False) for payload in outputs]
        if sum(len(payload.encode()) for payload in serialized) > 256 * 1024:
            raise ValueError("output payload byte limit exceeded")
        ids = [str(uuid4()) for _ in outputs]
        with self._transaction() as conn:
            self._require_claim(conn, claim)
            for item, payload in zip(ids, serialized, strict=False):
                conn.execute(
                    f"INSERT INTO {self._table}(id,queue_name,parent_id,state,payload) VALUES (%s,%s,%s,%s,%s::jsonb)",
                    (item, self._output_queue_name, claim.item_id, State.PENDING.value, payload),
                )
            changed = conn.execute(
                f"""UPDATE {self._table} SET state=%s,error_message=%s,
                released_at=clock_timestamp(),updated_at=clock_timestamp(),claim_owner=NULL,claim_deadline_ms=NULL
                WHERE id=%s AND claim_deadline_ms>{_CLOCK_MS}""",
                (state.value, message, claim.item_id),
            )
            if changed.rowcount != 1:
                raise ClaimRejected("Work Item claim expired before publication")
        return ids

    def retry_fenced(
        self,
        claim: WorkItemClaim,
        *,
        evidence: RetryEvidence,
        verify_receipt: ReceiptVerifier,
        max_claims: int,
    ) -> None:
        verify_retry(claim, evidence, verify_receipt)
        with self._transaction() as conn:
            self._require_claim(conn, claim)
            payload = conn.execute(
                f"SELECT payload FROM {self._table} WHERE id=%s", (claim.item_id,)
            ).fetchone()["payload"]
            record = retry_record(claim, evidence, payload, max_claims)
            conn.execute(
                f"INSERT INTO {self._retry_log}(item_id,epoch,record,format) VALUES (%s,%s,%s::jsonb,%s)",
                (claim.item_id, claim.epoch, json.dumps(record), "actions.work-item-retry/v1"),
            )
            changed = conn.execute(
                f"UPDATE {self._table} SET state=%s,claim_owner=NULL,claim_deadline_ms=NULL,updated_at=clock_timestamp() WHERE id=%s AND claim_deadline_ms>{_CLOCK_MS}",
                (State.PENDING.value, claim.item_id),
            )
            if changed.rowcount != 1:
                raise ClaimRejected("Work Item claim expired before retry release")

    def retry_history(self, item_id: str) -> list[dict]:
        with self._transaction() as conn:
            rows = conn.execute(
                f"SELECT format,record FROM {self._retry_log} WHERE item_id=%s ORDER BY epoch LIMIT 100",
                (item_id,),
            ).fetchall()
            if any(row["format"] != "actions.work-item-retry/v1" for row in rows):
                raise ValueError("Unknown retry audit format")
            return [row["record"] for row in rows]

    @staticmethod
    def _public_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in row.items()
        }

    def get_item(self, item_id: str) -> dict[str, Any]:
        with self._transaction() as conn:
            row = conn.execute(f"SELECT * FROM {self._table} WHERE id=%s", (item_id,)).fetchone()
            if row is None:
                raise ValueError("Work Item unavailable")
            return self._public_row(row)

    def load_payload(self, item_id: str) -> JSONType:
        return self.get_item(item_id)["payload"]

    def list_items(self, *, queue_name: str | None = None) -> list[dict[str, Any]]:
        queue_name = queue_name or self._queue_name
        self._validate_queue(queue_name)
        with self._transaction() as conn:
            return [
                self._public_row(row)
                for row in conn.execute(
                    f"SELECT * FROM {self._table} WHERE queue_name=%s ORDER BY created_at,id LIMIT 100",
                    (queue_name,),
                ).fetchall()
            ]
