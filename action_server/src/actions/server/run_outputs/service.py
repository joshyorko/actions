"""Private, DB-backed common Run authority and authorized output resolver.

Only trusted control-plane/transport code calls this module. Snapshot registration
is not compiler admission, and Actor/owner IDs are not authentication protocols.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
from collections.abc import Iterable, Iterator
from contextlib import ExitStack, contextmanager
from typing import Any, Protocol, TypeVar
from uuid import uuid4

from actions.server._database import Database, DBError
from actions.server._models import RUN_ID_COUNTER, Action, ActionPackage, Run, RunStatus
from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.ids import DeploymentRevisionRef
from actions.server.run_outputs.models import (
    RunAccessGrant,
    RunAdmission,
    RunAttempt,
    RunOutput,
    RunPin,
    Workspace,
)
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    ExecutionSnapshot,
    OutputRef,
    SealReceipt,
    StagedSeal,
    canonical_uuid,
    output_id_from_handle,
)

MAX_INPUT_BYTES = 256 * 1024
MAX_RESULT_BYTES = 1024 * 1024
MAX_OUTPUTS = 64
OPERATIONS = frozenset({"execute", "read", "cancel"})
T = TypeVar("T")


class AccessDenied(PermissionError):
    """Object unavailable or current actor not authorized; no provider disclosure."""


class FenceRejected(RuntimeError):
    """Attempt is expired, superseded, cancelled or otherwise not current."""


class OutputReader(Protocol):
    def read(self, size: int = -1) -> bytes:
        ...


class OutputProvider(Protocol):
    def stage(self, chunks: Iterable[bytes]) -> StagedSeal:
        ...

    def open(self, object_ref: str, digest: str, size: int) -> Any:
        ...

    def discard(self, staged: StagedSeal) -> None:
        ...


def _private_diagnostics(db: Database) -> None:
    if db.verbose:
        raise ValueError("common Run service rejects raw SQL bind diagnostics")


@contextmanager
def _transaction(db: Database) -> Iterator[None]:
    _private_diagnostics(db)
    with db.transaction():
        try:
            yield
        except DBError:
            # Catch before Database.transaction logs the exception/traceback.
            raise DBError(
                "common Run SQL operation failed; bind values redacted"
            ) from None


def _insert(db: Database, record: Any) -> None:
    _private_diagnostics(db)
    db.insert(record)


def _update(db: Database, cls: type, key: str, changes: dict) -> None:
    _private_diagnostics(db)
    db.update_by_id(cls, key, changes)


def _canonical(value: Any, limit: int) -> str:
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(raw) > limit:
        raise ValueError("metadata exceeds byte limit")
    return canonicalize_json(raw).decode("utf-8")


def _key(domain: str, *parts: str) -> str:
    return hashlib.sha256(
        _canonical([domain, *parts], MAX_RESULT_BYTES).encode()
    ).hexdigest()


def _snapshot(snapshot: ExecutionSnapshot) -> ExecutionSnapshot:
    return ExecutionSnapshot.model_validate(snapshot.model_dump(mode="json"))


def _admission(snapshot: ExecutionSnapshot) -> tuple[str, str]:
    canonical = _canonical(snapshot.model_dump(mode="json"), MAX_INPUT_BYTES)
    return _key(
        "actions.run-admission/v1",
        snapshot.workspace_id,
        snapshot.deployment_id,
        snapshot.deployment.revision_id.root,
        _canonical(snapshot.capability.model_dump(mode="json"), MAX_INPUT_BYTES),
    ), canonical


def _one(db: Database, cls: type[T], key: str) -> T:
    _private_diagnostics(db)
    rows = db.all(cls, where="id=?", values=[key])
    if len(rows) != 1:
        raise AccessDenied("Run/output unavailable or access denied")
    return rows[0]


def _action_identity(db: Database, snapshot: ExecutionSnapshot) -> Action:
    action = _one(db, Action, snapshot.action_id)
    package_id = str(snapshot.capability.package_revision.package_id.root)
    package = _one(db, ActionPackage, package_id)
    if (
        not action.enabled
        or action.action_package_id != package.id
        or action.name != snapshot.capability.capability_id.root
    ):
        raise AccessDenied("admitted Action/Package identity is unavailable")
    return action


def _now_sql(db: Database) -> str:
    if db.backend_name == "postgresql":
        return "CAST(EXTRACT(EPOCH FROM clock_timestamp()) * 1000 AS BIGINT)"
    if db.backend_name == "sqlite":
        return "CAST((julianday('now') - 2440587.5) * 86400000 AS BIGINT)"
    raise RuntimeError("unsupported Database backend")


def _now(db: Database) -> int:
    with db.cursor() as cursor:
        db.execute_query(cursor, "SELECT " + _now_sql(db))
        return int(cursor.fetchone()[0])


def _returning(db: Database, sql: str, values: list) -> list:
    _private_diagnostics(db)
    with db.cursor() as cursor:
        db.execute_update_returning(cursor, sql, values)
        return cursor.fetchall()


def _lock_workspace(db: Database, workspace_id: str) -> None:
    if not _returning(
        db,
        "UPDATE workspace SET lock_version=lock_version WHERE id=? AND state='active' RETURNING id",
        [workspace_id],
    ):
        raise AccessDenied("Run/output unavailable or access denied")


def _lock_run(db: Database, run_id: str) -> RunPin:
    # SQLite deferred transactions must obtain the DB writer before any read.
    # Reading a pin first permits an interprocess read->write upgrade deadlock.
    if db.backend_name == "sqlite":
        if not _returning(
            db,
            "UPDATE counter SET value=value WHERE id=? RETURNING id",
            [RUN_ID_COUNTER],
        ):
            raise RuntimeError("Run counter unavailable")
    pin = _one(db, RunPin, run_id)
    _lock_workspace(db, pin.workspace_id)
    return _one(db, RunPin, run_id)


def _lease_duration(seconds: int) -> int:
    if (
        not isinstance(seconds, int)
        or isinstance(seconds, bool)
        or not 1 <= seconds <= 3600
    ):
        raise ValueError("lease duration must be 1..3600 seconds")
    return seconds * 1000


class RunOutputControlPlane:
    """Trusted admin operations; never installed as an Action/package API."""

    def __init__(self, db: Database):
        _private_diagnostics(db)
        self.db = db

    def register(self, snapshot: ExecutionSnapshot) -> str:
        snapshot = _snapshot(snapshot)
        key, canonical = _admission(snapshot)
        with _transaction(self.db):
            # A single installation lock serializes first Workspace insertion too.
            if not _returning(
                self.db,
                "UPDATE counter SET value=value WHERE id=? RETURNING id",
                [RUN_ID_COUNTER],
            ):
                raise RuntimeError("Run counter unavailable")
            rows = self.db.all(Workspace, where="id=?", values=[snapshot.workspace_id])
            if not rows:
                _insert(self.db, Workspace(snapshot.workspace_id, "active", 0))
            _lock_workspace(self.db, snapshot.workspace_id)
            _action_identity(self.db, snapshot)
            admissions = self.db.all(RunAdmission, where="id=?", values=[key])
            if admissions:
                if (
                    admissions[0].snapshot_json != canonical
                    or admissions[0].workspace_id != snapshot.workspace_id
                ):
                    raise ValueError("immutable admission identity conflict")
            else:
                _insert(
                    self.db,
                    RunAdmission(
                        key, snapshot.workspace_id, snapshot.deployment_id, canonical
                    ),
                )
        return key

    def grant(
        self, actor: Actor, deployment: DeploymentRevisionRef, operations: set[str]
    ) -> None:
        actor = Actor.model_validate(actor)
        if not operations or not operations <= OPERATIONS:
            raise ValueError("unsupported grant operation")
        ws, dep = str(deployment.workspace_id.root), str(deployment.deployment_id.root)
        key = _key("actions.run-access/v1", ws, dep, actor.principal_id)
        with _transaction(self.db):
            _lock_workspace(self.db, ws)
            existing = self.db.all(RunAccessGrant, where="id=?", values=[key])
            if existing and (
                existing[0].workspace_id,
                existing[0].deployment_id,
                existing[0].principal_id,
            ) != (ws, dep, actor.principal_id):
                raise ValueError("grant identity collision")
            payload = _canonical(sorted(operations), 1024)
            if existing:
                _update(self.db, RunAccessGrant, key, {"operations_json": payload})
            else:
                _insert(
                    self.db, RunAccessGrant(key, ws, dep, actor.principal_id, payload)
                )

    def revoke(self, actor: Actor, deployment: DeploymentRevisionRef) -> None:
        ws, dep = str(deployment.workspace_id.root), str(deployment.deployment_id.root)
        key = _key("actions.run-access/v1", ws, dep, actor.principal_id)
        with _transaction(self.db):
            _lock_workspace(self.db, ws)
            self.db.execute("DELETE FROM run_access_grant WHERE id=?", [key])

    def authorize_recovery(
        self, run_id: str, expired_epoch: int, *, receipt: str
    ) -> None:
        """Operator-verified no-effect recovery; no automatic worker retry policy."""
        if not receipt or len(receipt.encode()) > 1024:
            raise ValueError("bounded recovery receipt required")
        with _transaction(self.db):
            pin = _lock_run(self.db, run_id)
            attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
            if pin.epoch != expired_epoch or int(attempt.lease_deadline_ms) > _now(
                self.db
            ):
                raise FenceRejected("recovery must identify an expired current epoch")
            _update(
                self.db,
                RunPin,
                run_id,
                {"recovery_epoch": expired_epoch, "recovery_receipt": receipt},
            )


class ResolvedOutput:
    def __init__(self, output: RunOutput, reader: OutputReader):
        self.run_id = output.run_id
        self.name = output.name
        self.media_type = output.media_type
        self.size = output.size
        self.digest = output.digest
        self._reader = reader

    def read(self, size: int = -1) -> bytes:
        return self._reader.read(size)


class RunOutputService:
    def __init__(self, db: Database, providers: dict[str, OutputProvider]):
        _private_diagnostics(db)
        self.db = db
        self.providers = dict(providers)

    def _authorize(
        self, actor: Actor, snapshot: ExecutionSnapshot, operation: str
    ) -> None:
        actor = Actor.model_validate(actor)
        grant = _one(
            self.db,
            RunAccessGrant,
            _key(
                "actions.run-access/v1",
                snapshot.workspace_id,
                snapshot.deployment_id,
                actor.principal_id,
            ),
        )
        if (grant.workspace_id, grant.deployment_id, grant.principal_id) != (
            snapshot.workspace_id,
            snapshot.deployment_id,
            actor.principal_id,
        ):
            raise AccessDenied("Run/output unavailable or access denied")
        try:
            operations = json.loads(grant.operations_json)
            if (
                not isinstance(operations, list)
                or not all(
                    isinstance(op, str) and op in OPERATIONS for op in operations
                )
                or operation not in operations
            ):
                raise ValueError("invalid or missing operation")
        except (ValueError, TypeError) as exc:
            raise AccessDenied("Run/output unavailable or access denied") from exc

    def _pinned(self, pin: RunPin) -> ExecutionSnapshot:
        row = _one(self.db, RunAdmission, pin.run_admission_id)
        snapshot = ExecutionSnapshot.model_validate_json(row.snapshot_json)
        key, canonical = _admission(snapshot)
        if (
            key != row.id
            or canonical != row.snapshot_json
            or row.workspace_id != pin.workspace_id
            or snapshot.workspace_id != pin.workspace_id
            or row.deployment_id != snapshot.deployment_id
            or pin.run_id != pin.id
        ):
            raise AccessDenied("Run/output unavailable or access denied")
        run = _one(self.db, Run, pin.run_id)
        if pin.request_fingerprint != _key(
            "actions.run-request/v1", canonical, run.inputs
        ):
            raise AccessDenied("immutable Run admission payload changed")
        return snapshot

    def admit(
        self,
        actor: Actor,
        snapshot: ExecutionSnapshot,
        inputs: Any,
        idempotency_key: str,
    ) -> Run:
        snapshot = _snapshot(snapshot)
        if (
            not isinstance(idempotency_key, str)
            or not 1 <= len(idempotency_key.encode()) <= 256
        ):
            raise ValueError("bounded idempotency key required")
        key, payload = _admission(snapshot)
        input_json = _canonical(inputs, MAX_INPUT_BYTES)
        fingerprint = _key("actions.run-request/v1", payload, input_json)
        idem = _key(
            "actions.workspace-run-idempotency/v1",
            snapshot.workspace_id,
            idempotency_key,
        )
        with _transaction(self.db):
            # Registration also takes Counter before Workspace. Admission will
            # allocate numbered_id, so preserve that order on PostgreSQL too.
            if not _returning(
                self.db,
                "UPDATE counter SET value=value WHERE id=? RETURNING id",
                [RUN_ID_COUNTER],
            ):
                raise RuntimeError("Run counter unavailable")
            _lock_workspace(self.db, snapshot.workspace_id)
            row = _one(self.db, RunAdmission, key)
            if (row.workspace_id, row.deployment_id, row.snapshot_json) != (
                snapshot.workspace_id,
                snapshot.deployment_id,
                payload,
            ):
                raise AccessDenied("Run/output unavailable or access denied")
            self._authorize(actor, snapshot, "execute")
            action = _action_identity(self.db, snapshot)
            from jsonschema import validate
            from jsonschema.exceptions import SchemaError, ValidationError

            try:
                validate(json.loads(input_json), json.loads(action.input_schema))
            except (SchemaError, ValidationError):
                raise ValidationError(
                    "input does not match admitted Action schema"
                ) from None
            existing = self.db.all(RunPin, where="idempotency_id=?", values=[idem])
            if existing:
                pin = existing[0]
                if (
                    pin.workspace_id != snapshot.workspace_id
                    or pin.idempotency_key != idempotency_key
                    or pin.request_fingerprint != fingerprint
                ):
                    raise ValueError("idempotency key conflicts with changed request")
                self._authorize(actor, self._pinned(pin), "execute")
                return _one(self.db, Run, pin.run_id)
            run_id = str(uuid4())
            numbered = _returning(
                self.db,
                "UPDATE counter SET value=value+1 WHERE id=? RETURNING value",
                [RUN_ID_COUNTER],
            )
            if len(numbered) != 1:
                raise RuntimeError("Run counter unavailable")
            run = Run(
                id=run_id,
                status=RunStatus.NOT_RUN,
                action_id=snapshot.action_id,
                start_time=datetime.datetime.fromtimestamp(
                    _now(self.db) / 1000, datetime.timezone.utc
                ).isoformat(),
                run_time=None,
                inputs=input_json,
                result=None,
                error_message=None,
                relative_artifacts_dir="",
                numbered_id=numbered[0][0],
                request_id="",
            )
            _insert(self.db, run)
            _insert(
                self.db,
                RunPin(
                    run_id,
                    run_id,
                    snapshot.workspace_id,
                    key,
                    actor.principal_id,
                    fingerprint,
                    idem,
                    idempotency_key,
                    "",
                    0,
                    0,
                    -1,
                    "",
                ),
            )
            return run

    def _fence(self, fence: AttemptFence) -> RunPin:
        fence = AttemptFence.model_validate(fence)
        _lock_run(self.db, fence.run_id)
        rows = _returning(
            self.db,
            "UPDATE run SET status=status WHERE id=? AND status=? AND EXISTS (SELECT 1 FROM run_pin p JOIN run_attempt a ON a.id=p.current_attempt_id WHERE p.run_id=run.id AND p.id=p.run_id AND p.cancel_requested=0 AND p.epoch=? AND a.id=? AND a.owner_id=? AND a.epoch=p.epoch AND a.run_id=run.id AND a.workspace_id=p.workspace_id AND a.state='running' AND CAST(a.lease_deadline_ms AS BIGINT)>"
            + _now_sql(self.db)
            + ") RETURNING id",
            [
                fence.run_id,
                RunStatus.RUNNING,
                fence.epoch,
                fence.attempt_id,
                fence.owner_id,
            ],
        )
        if not rows:
            raise FenceRejected("Attempt is not current, live and uncancelled")
        return _one(self.db, RunPin, fence.run_id)

    def claim(self, run_id: str, owner_id: str, *, lease_seconds: int) -> AttemptFence:
        canonical_uuid(owner_id)
        duration = _lease_duration(lease_seconds)
        with _transaction(self.db):
            pin = _lock_run(self.db, run_id)
            run = _one(self.db, Run, run_id)
            if (
                pin.cancel_requested
                or pin.epoch >= 2_147_483_647
                or run.status not in (RunStatus.NOT_RUN, RunStatus.RUNNING)
            ):
                raise FenceRejected("Run cannot be claimed")
            if pin.current_attempt_id:
                old = _one(self.db, RunAttempt, pin.current_attempt_id)
                if (
                    int(old.lease_deadline_ms) > _now(self.db)
                    or pin.recovery_epoch != pin.epoch
                    or not pin.recovery_receipt
                ):
                    raise FenceRejected(
                        "live owner or missing explicit no-effect recovery"
                    )
                _update(self.db, RunAttempt, old.id, {"state": "lost"})
            now = _now(self.db)
            attempt = RunAttempt(
                str(uuid4()),
                run_id,
                pin.workspace_id,
                owner_id,
                pin.epoch + 1,
                str(now + duration),
                str(now),
                "running",
            )
            _insert(self.db, attempt)
            _update(
                self.db,
                RunPin,
                run_id,
                {
                    "current_attempt_id": attempt.id,
                    "epoch": attempt.epoch,
                    "recovery_epoch": -1,
                },
            )
            _update(self.db, Run, run_id, {"status": RunStatus.RUNNING})
            return AttemptFence(
                run_id=run_id,
                attempt_id=attempt.id,
                owner_id=owner_id,
                epoch=attempt.epoch,
            )

    def heartbeat(self, fence: AttemptFence, *, lease_seconds: int) -> None:
        duration = _lease_duration(lease_seconds)
        with _transaction(self.db):
            self._fence(fence)
            now = _now(self.db)
            if not _returning(
                self.db,
                "UPDATE run_attempt SET lease_deadline_ms=?, heartbeat_ms=? WHERE id=? AND CAST(lease_deadline_ms AS BIGINT)>"
                + _now_sql(self.db)
                + " RETURNING id",
                [str(now + duration), str(now), fence.attempt_id],
            ):
                raise FenceRejected("expired Attempt cannot renew")

    def stage(
        self,
        fence: AttemptFence,
        chunks: Iterable[bytes],
        *,
        name: str,
        media_type: str,
        retention_seconds: int,
    ) -> OutputRef:
        if (
            not isinstance(name, str)
            or not 1 <= len(name.encode()) <= 255
            or any(c in name for c in ("/", "\\", "\x00"))
            or name in {".", ".."}
        ):
            raise ValueError("portable output display name required")
        if (
            not isinstance(media_type, str)
            or not 1 <= len(media_type) <= 128
            or any(ord(c) < 32 for c in media_type)
        ):
            raise ValueError("bounded media type required")
        if (
            not isinstance(retention_seconds, int)
            or isinstance(retention_seconds, bool)
            or not 1 <= retention_seconds <= 86400 * 365
        ):
            raise ValueError("bounded retention required")
        with _transaction(self.db):
            pin = self._fence(fence)
            snapshot = self._pinned(pin)
            self._authorize(
                Actor(principal_id=pin.admission_principal_id), snapshot, "execute"
            )
            with self.db.cursor() as cursor:
                self.db.execute_query(
                    cursor,
                    "SELECT COUNT(*) FROM run_output WHERE run_id=?",
                    [fence.run_id],
                )
                if cursor.fetchone()[0] >= MAX_OUTPUTS:
                    raise ValueError("Run output count bound exceeded")
            provider = self.providers.get(snapshot.provider_key)
            if provider is None:
                raise AccessDenied("configured output provider unavailable")
            output_id = str(uuid4())
            output = RunOutput(
                output_id,
                fence.run_id,
                pin.workspace_id,
                fence.attempt_id,
                fence.epoch,
                snapshot.provider_key,
                "",
                "",
                0,
                name,
                media_type,
                "provisional",
                str(_now(self.db) + retention_seconds * 1000),
            )
            _insert(self.db, output)
        staged: StagedSeal | None = None
        seal: SealReceipt | None = None
        try:
            staged = provider.stage(chunks)
            seal = SealReceipt.model_validate(staged.receipt)
            with _transaction(self.db):
                self._fence(fence)
                _update(self.db, RunOutput, output_id, seal.model_dump())
        except BaseException as failure:
            try:
                discardable = self._abort_stage(output, seal)
            except BaseException:
                failure.add_note(
                    "Output abort outcome is uncertain; no provider discard was attempted."
                )
                logging.getLogger(__name__).warning(
                    "Output abort outcome uncertain: %s", output_id
                )
            else:
                if staged is not None and seal is not None and discardable:
                    try:
                        provider.discard(staged)
                    except BaseException:
                        failure.add_note(
                            "Aborted output retains its measured seal for reconciliation; discard failed."
                        )
                        logging.getLogger(__name__).warning(
                            "Aborted output discard failed: %s", output_id
                        )
                elif staged is not None:
                    failure.add_note(
                        "Provider discard skipped: output cleanup was not proven safe."
                    )
            raise
        return OutputRef(
            workspace_id=pin.workspace_id, run_id=fence.run_id, output_id=output_id
        )

    def _abort_stage(self, expected: RunOutput, seal: SealReceipt | None) -> bool:
        """Commit an abort receipt; return discard eligibility only after commit."""
        with _transaction(self.db):
            _lock_run(self.db, expected.run_id)
            row = _one(self.db, RunOutput, expected.id)
            if (
                row.run_id,
                row.workspace_id,
                row.run_attempt_id,
                row.epoch,
                row.provider_key,
            ) != (
                expected.run_id,
                expected.workspace_id,
                expected.run_attempt_id,
                expected.epoch,
                expected.provider_key,
            ):
                return False
            if row.state not in ("provisional", "aborted"):
                return False
            run = _one(self.db, Run, expected.run_id)
            if run.status == RunStatus.PASSED:
                result = json.loads(run.result or "null")
                if not isinstance(result, dict) or not isinstance(
                    result.get("outputs"), list
                ):
                    return False
                ref = OutputRef(
                    workspace_id=row.workspace_id, run_id=row.run_id, output_id=row.id
                ).model_dump()
                if ref in result["outputs"]:
                    return False
            changes: dict[str, Any] = {"state": "aborted"}
            discardable = False
            if seal is not None:
                if (row.object_ref, row.digest, row.size) not in (
                    ("", "", 0),
                    (seal.object_ref, seal.digest, seal.size),
                ):
                    return False
                changes.update(seal.model_dump())
                with self.db.cursor() as cursor:
                    self.db.execute_query(
                        cursor,
                        "SELECT COUNT(*) FROM run_output WHERE provider_key=? AND object_ref=? AND id<>?",
                        [row.provider_key, seal.object_ref, row.id],
                    )
                    discardable = cursor.fetchone()[0] == 0
            _update(self.db, RunOutput, row.id, changes)
        return discardable

    def publish(
        self, actor: Actor, fence: AttemptFence, outputs: list[OutputRef], result: Any
    ) -> Run:
        if not 1 <= len(outputs) <= MAX_OUTPUTS or len(
            {o.output_id for o in outputs}
        ) != len(outputs):
            raise ValueError("bounded unique outputs required")
        outputs = [OutputRef.model_validate(o) for o in outputs]
        envelope = _canonical(
            {
                "version": 1,
                "result": result,
                "outputs": [o.model_dump() for o in outputs],
            },
            MAX_RESULT_BYTES,
        )
        with _transaction(self.db):
            pin = _lock_run(self.db, fence.run_id)
            snapshot = self._pinned(pin)
            self._authorize(actor, snapshot, "execute")
            run = _one(self.db, Run, fence.run_id)
            attempt = _one(self.db, RunAttempt, fence.attempt_id)
            if run.status == RunStatus.PASSED:
                if (
                    run.result == envelope
                    and pin.current_attempt_id == fence.attempt_id
                    and pin.epoch == fence.epoch
                    and attempt.owner_id == fence.owner_id
                ):
                    return run
                raise FenceRejected("terminal publication differs or owner is stale")
            self._fence(fence)
            for ref in outputs:
                output = _one(self.db, RunOutput, ref.output_id)
                if (
                    (
                        ref.workspace_id,
                        ref.run_id,
                        output.workspace_id,
                        output.run_id,
                        output.run_attempt_id,
                        output.epoch,
                        output.provider_key,
                    )
                    != (
                        pin.workspace_id,
                        run.id,
                        pin.workspace_id,
                        run.id,
                        fence.attempt_id,
                        fence.epoch,
                        snapshot.provider_key,
                    )
                    or output.state != "provisional"
                    or not output.object_ref
                    or not output.digest
                    or int(output.expires_ms) <= _now(self.db)
                ):
                    raise FenceRejected(
                        "output is not a sealed current provisional object"
                    )
            # The live-lease predicate is evaluated at the terminal write itself.
            self._fence(fence)
            if not _returning(
                self.db,
                "UPDATE run SET status=?, result=? WHERE id=? AND status=? AND EXISTS (SELECT 1 FROM run_pin p JOIN run_attempt a ON a.id=p.current_attempt_id WHERE p.run_id=run.id AND p.current_attempt_id=? AND p.epoch=? AND p.cancel_requested=0 AND a.owner_id=? AND a.state='running' AND CAST(a.lease_deadline_ms AS BIGINT)>"
                + _now_sql(self.db)
                + ") RETURNING id",
                [
                    RunStatus.PASSED,
                    envelope,
                    run.id,
                    RunStatus.RUNNING,
                    fence.attempt_id,
                    fence.epoch,
                    fence.owner_id,
                ],
            ):
                raise FenceRejected("publication lease expired")
            for ref in outputs:
                _update(self.db, RunOutput, ref.output_id, {"state": "final"})
            _update(self.db, RunAttempt, fence.attempt_id, {"state": "succeeded"})
            return _one(self.db, Run, run.id)

    def cancel(self, actor: Actor, run_id: str) -> bool:
        with _transaction(self.db):
            pin = _lock_run(self.db, run_id)
            self._authorize(actor, self._pinned(pin), "cancel")
            run = _one(self.db, Run, run_id)
            if run.status not in (RunStatus.NOT_RUN, RunStatus.RUNNING):
                return False
            _update(self.db, RunPin, run_id, {"cancel_requested": 1})
            return True

    @contextmanager
    def resolve(
        self, actor: Actor, workspace_id: str, handle: str
    ) -> Iterator[ResolvedOutput]:
        try:
            canonical_uuid(workspace_id)
            output_id = output_id_from_handle(handle)
        except ValueError as exc:
            raise AccessDenied("Run/output unavailable or access denied") from exc
        with ExitStack() as owned:
            with _transaction(self.db):
                _lock_workspace(self.db, workspace_id)
                output = _one(self.db, RunOutput, output_id)
                pin = _one(self.db, RunPin, output.run_id)
                if (
                    output.workspace_id != workspace_id
                    or pin.workspace_id != workspace_id
                ):
                    raise AccessDenied("Run/output unavailable or access denied")
                snapshot = self._pinned(pin)
                self._authorize(actor, snapshot, "read")
                run = _one(self.db, Run, output.run_id)
                try:
                    attached = json.loads(run.result or "null")
                    ref = OutputRef(
                        workspace_id=workspace_id, run_id=run.id, output_id=output.id
                    ).model_dump()
                    if (
                        run.status != RunStatus.PASSED
                        or output.state != "final"
                        or int(output.expires_ms) <= _now(self.db)
                        or not isinstance(attached, dict)
                        or attached.get("version") != 1
                        or ref not in attached.get("outputs", [])
                    ):
                        raise ValueError("not attached final output")
                except (ValueError, TypeError) as exc:
                    raise AccessDenied(
                        "Run/output unavailable or access denied"
                    ) from exc
                provider = self.providers.get(output.provider_key)
                if provider is None or output.provider_key != snapshot.provider_key:
                    raise AccessDenied("Run/output unavailable or access denied")
                # Authorization and descriptor acquisition share the grant lock.
                # Revocation affects future resolutions, not this authorized stream.
                reader = owned.enter_context(
                    provider.open(output.object_ref, output.digest, output.size)
                )
            yield ResolvedOutput(output, reader)
