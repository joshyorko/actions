"""Explicit ordinary-Action detached admission on canonical Run authority.

No Task protocol, scheduler, default worker, grant provisioning or automatic
recovery. Hosts configure bounded workers and retain their connection lifecycle.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from actions.server._models import Run, RunStatus
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.models import RunAttempt, RunExecutionIntent, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    _advance_lifecycle,
    _canonical,
    _insert,
    _lock_run,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import canonical_uuid


@dataclass(frozen=True)
class PendingActions:
    run_ids: tuple[str, ...]
    next_cursor: str | None


class DetachedActions:
    def __init__(self, deployments, outputs):
        self.deployments, self.outputs, self.db = deployments, outputs, outputs.db

    def _service(self, actor, snapshot):
        service = StandaloneActionExecution(self.deployments, self.outputs, snapshot)
        service.current(ManagedCaller(actor=actor))
        if (
            snapshot.runtime_kind != "rcc"
            or snapshot.capability_authority != "package-revision"
        ):
            raise AccessDenied("verified ordinary RCC Action required")
        return service

    def _envelope(self, snapshot, inputs):
        return _canonical(
            {
                "version": "actions.detached-ordinary-action/v1",
                "snapshot": snapshot.model_dump(mode="json"),
                "inputDigest": "sha256:"
                + hashlib.sha256(_canonical(inputs, 262144).encode()).hexdigest(),
            },
            131072,
        )

    def admit(self, actor, snapshot, inputs, key):
        return self.admit_outcome(actor, snapshot, inputs, key).run

    def admit_outcome(self, actor, snapshot, inputs, key):
        with _transaction(self.db):
            service = self._service(actor, snapshot)
            RunOutputControlPlane(self.db, capabilities=service.registry).register(
                snapshot
            )
            outcome = self.outputs.admit_outcome(actor, snapshot, inputs, key)
            run = outcome.run
            pin = _one(self.db, RunPin, run.id)
            if pin.admission_principal_id != actor.principal_id:
                raise AccessDenied("detached admission principal differs")
            envelope = self._envelope(snapshot, json.loads(run.inputs))
            rows = self.db.all(RunExecutionIntent, where="id=?", values=[run.id])
            if rows:
                self._load(actor, run.id)
                if rows[0].envelope_json != envelope:
                    raise FenceRejected("detached replay metadata differs")
            else:
                if (
                    pin.current_attempt_id
                    or run.status != RunStatus.NOT_RUN
                    or run.result
                ):
                    raise FenceRejected(
                        "existing synchronous Run cannot become detached"
                    )
                _insert(
                    self.db,
                    RunExecutionIntent(
                        run.id, snapshot.workspace_id, actor.principal_id, envelope
                    ),
                )
            return outcome

    def _integrity(self, actor, run_id):
        canonical_uuid(run_id)
        intent = _one(self.db, RunExecutionIntent, run_id)
        pin = _one(self.db, RunPin, run_id)
        if (
            intent.actor_id != actor.principal_id
            or pin.admission_principal_id != actor.principal_id
        ):
            raise AccessDenied("detached principal unavailable")
        snapshot = self.outputs._pinned(pin)
        run = _one(self.db, Run, run_id)
        if (
            intent.workspace_id != snapshot.workspace_id
            or intent.envelope_json != self._envelope(snapshot, json.loads(run.inputs))
        ):
            raise FenceRejected("detached immutable metadata differs")
        if not pin.current_attempt_id and (
            pin.epoch != 0
            or run.result is not None
            or run.status not in (RunStatus.NOT_RUN, RunStatus.CANCELLED)
        ):
            raise FenceRejected("unclaimed detached Run contains execution evidence")
        return snapshot, run, pin

    def _load(self, actor, run_id):
        snapshot, run, pin = self._integrity(actor, run_id)
        return self._service(actor, snapshot), run, pin

    def pending(self, actor, workspace_id, worker_profile, *, limit=20, after=None):
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            raise ValueError("bounded scan limit required")
        if str(worker_profile.workspace_id.root) != workspace_id:
            raise AccessDenied("worker workspace differs")
        if after is not None and (
            not isinstance(after, str)
            or not after.isascii()
            or not after.isdecimal()
            or len(after) > 19
            or str(int(after)) != after
            or int(after) > 9223372036854775807
        ):
            raise ValueError("bounded scan ordinal required")
        # A bounded candidate scan, not an exhaustive list; caller advances via
        # scan_after when candidates are ineligible. Only initial Runs are polled.
        with self.db.cursor() as cursor:
            self.db.execute_query(
                cursor,
                "SELECT i.id,r.numbered_id FROM run_execution_intent i JOIN run_pin p ON p.run_id=i.id JOIN run r ON r.id=i.id WHERE i.workspace_id=? AND i.actor_id=? AND p.current_attempt_id='' AND p.cancel_requested=0 AND r.status=? AND r.numbered_id>? ORDER BY r.numbered_id LIMIT ?",
                [
                    workspace_id,
                    actor.principal_id,
                    RunStatus.NOT_RUN,
                    int(after) if after is not None else 0,
                    limit,
                ],
            )
            rows = cursor.fetchall()
        selected = []
        for row in rows:
            # Integrity is checked outside the authorization exception handler:
            # corrupted metadata must not be hidden as an ordinary denied row.
            snapshot, _, _ = self._integrity(actor, row[0])
            try:
                service = self._service(actor, snapshot)
            except PermissionError:
                continue
            if service.snapshot.worker == worker_profile:
                selected.append(row[0])
        return PendingActions(
            tuple(selected), str(rows[-1][1]) if len(rows) == limit else None
        )

    def claim(self, caller, run_id, worker_profile, *, lease_seconds=60):
        if caller.worker_id is None:
            raise AccessDenied("trusted worker identity required")
        with _transaction(self.db):
            _lock_run(self.db, run_id)
            service, run, pin = self._load(caller.actor, run_id)
            if service.snapshot.worker != worker_profile:
                raise AccessDenied("worker profile differs")
            if run.status not in (RunStatus.NOT_RUN, RunStatus.RUNNING):
                raise FenceRejected("detached Run is terminal")
            if pin.current_attempt_id:
                attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
                if pin.recovery_epoch != pin.epoch or not pin.recovery_receipt:
                    if attempt.owner_id != caller.worker_id:
                        raise FenceRejected("another worker owns Attempt")
                    ticket = service.ticket(caller, run)
                    self.outputs._fence(ticket.fence)
                    return ticket
            if pin.current_attempt_id:
                # This prerequisite recovers only a verified pre-launch loss.
                # Launch/effect reconciliation must retain its own evidence;
                # even an operator receipt does not authorize discarding it here.
                old_caller = ManagedCaller(
                    actor=caller.actor, worker_id=attempt.owner_id
                )
                service.ticket(old_caller, run)
                record = json.loads(run.result or "null")
                if (
                    not isinstance(record, dict)
                    or set(record) != {"version", "mode", "claim", "fence", "launch"}
                    or record.get("launch") is not None
                ):
                    raise FenceRejected(
                        "retained launch requires explicit reconciliation"
                    )
            fence = self.outputs.claim(
                run.id, caller.worker_id, lease_seconds=lease_seconds
            )
            _update(
                self.db,
                Run,
                run.id,
                {
                    "result": _canonical(
                        {
                            "version": "actions.generated-rcc-dispatch/v1",
                            "mode": "standalone",
                            "claim": None,
                            "fence": fence.model_dump(),
                            "launch": None,
                        },
                        65536,
                    )
                },
            )
            return service.ticket(caller, _one(self.db, Run, run.id))

    def cancel(self, actor, run_id):
        with _transaction(self.db):
            _lock_run(self.db, run_id)
            _, run, pin = self._integrity(actor, run_id)
            accepted = self.outputs.cancel(actor, run_id)
            if accepted and not pin.current_attempt_id:
                if run.status != RunStatus.NOT_RUN or run.result:
                    raise FenceRejected("unclaimed cancellation evidence differs")
                _update(self.db, Run, run_id, {"status": RunStatus.CANCELLED})
                if pin.cancel_requested:
                    # A prior intent is distinct from this terminal confirmation.
                    _advance_lifecycle(self.db, run_id)
            return accepted


class DetachedActionWorker:
    """Trusted host object; never constructed from request worker/profile fields."""

    def __init__(self, authority, actor, worker_id, profile):
        canonical_uuid(worker_id)
        self.authority, self.profile = authority, profile
        self.caller = ManagedCaller(actor=actor, worker_id=worker_id)

    def run_once(self, *, prepared, rcc: Path, execution_root: Path, after=None):
        """Consume one bounded page; host owns polling and connection lifetime."""
        page = self.authority.pending(
            self.caller.actor,
            str(self.profile.workspace_id.root),
            self.profile,
            after=after,
        )
        if not page.run_ids:
            return None, page.next_cursor
        ticket = self.claim(page.run_ids[0])
        return self.execute(
            ticket, prepared=prepared, rcc=rcc, execution_root=execution_root
        ), str(_one(self.authority.db, Run, page.run_ids[0]).numbered_id)

    def claim(self, run_id, *, lease_seconds=60):
        return self.authority.claim(
            self.caller, run_id, self.profile, lease_seconds=lease_seconds
        )

    def cancelled(self, ticket):
        with _transaction(self.authority.db):
            service, run, pin = self.authority._load(
                self.caller.actor, ticket.fence.run_id
            )
            if (
                service.snapshot.worker != self.profile
                or service.ticket(self.caller, run) != ticket
            ):
                raise FenceRejected("worker execution binding differs")
            if pin.cancel_requested:
                return True
            self.authority.outputs._fence(ticket.fence)
            return False

    def execute(self, ticket, *, prepared, rcc: Path, execution_root: Path):
        if self.cancelled(ticket):
            raise FenceRejected("detached cancellation requested")
        service, _, _ = self.authority._load(self.caller.actor, ticket.fence.run_id)
        return GeneratedRccExecution(
            service.registry,
            service.outputs(self.caller, ticket),
            prepared,
            rcc,
            execution_root,
        ).execute(
            self.caller.actor, ticket.fence, cancelled=lambda: self.cancelled(ticket)
        )
