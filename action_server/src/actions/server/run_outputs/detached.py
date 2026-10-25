"""Explicit ordinary-Action detached admission on canonical Run authority.

No Task protocol, scheduler, default worker, grant provisioning or automatic
recovery. Hosts configure bounded workers and retain their connection lifecycle.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from actions.work_items._fencing import WorkItemClaim

from actions.server._models import Run, RunStatus
from actions.server.data_queries.invoice_worker import work_item_run_key
from actions.server.foundry.generic_work_item_execution import (
    GenericInput,
    GenericWorkItemExecution,
)
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.foundry.robot_retained_projection import retained_robot_projection
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import ClaimRef, ManagedCaller
from actions.server.run_outputs.claimed_intent import ClaimedTaskIntent, claimed_intent
from actions.server.run_outputs.claimed_task_state import validate_claimed_cancellation
from actions.server.run_outputs.models import (
    RunAttempt,
    RunExecutionIntent,
    RunPin,
    RunTaskReceipt,
)
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunAdmissionOutcome,
    RunOutputControlPlane,
    _advance_lifecycle,
    _canonical,
    _insert,
    _key,
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
    def __init__(self, deployments, outputs, queue_authorization=None):
        self.deployments, self.outputs, self.db = deployments, outputs, outputs.db
        self.queue_authorization = queue_authorization

    def claimed(self, run_id) -> ClaimedTaskIntent | None:
        return claimed_intent(_one(self.db, RunExecutionIntent, run_id).envelope_json)

    def claimed_service(self, snapshot) -> GenericWorkItemExecution:
        projection = retained_robot_projection(self.db, snapshot)
        stored = self.deployments._repository.get_revision(snapshot.deployment)
        if (
            projection.work_items.mode != "consumer"
            or projection.work_items.allow_outputs
            or stored is None
        ):
            raise AccessDenied("claimed consumer Robot required")
        policies = [
            p
            for p in stored.revision.specification.work_item_policies
            if p.capability == snapshot.capability
        ]
        if len(policies) != 1 or policies[0].input_mode != "claim":
            raise AccessDenied("exact claimed policy required")
        return GenericWorkItemExecution(
            self.deployments,
            self.outputs,
            snapshot,
            policies[0],
            self.queue_authorization,
        )

    def admit_claimed(
        self, caller: ManagedCaller, snapshot, claim: ClaimRef
    ) -> RunAdmissionOutcome:
        service = self.claimed_service(snapshot)
        with service._transaction():
            service._current(caller)
            name = service.policy.input_queue
            if name is None:
                raise AccessDenied("claimed input queue required")
            if caller.worker_id != claim.owner_id or claim.queue != service.queue_ref(
                name
            ):
                raise AccessDenied("claimed Task owner or queue differs")
            identity = _key(
                "actions.workspace-run-idempotency/v1",
                snapshot.workspace_id,
                work_item_run_key(claim.item_id),
            )
            pins = self.db.all(RunPin, where="idempotency_id=?", values=[identity])
            if pins:
                if len(pins) != 1:
                    raise FenceRejected("claimed Task admission differs")
                run_id = pins[0].run_id
                retained = self.claimed(run_id)
                snapshot0, run, pin = self._integrity(caller.actor, run_id)
                if (
                    retained is None
                    or retained.claim != claim
                    or snapshot0 != snapshot
                    or len(self.db.all(RunTaskReceipt, where="id=?", values=[run_id]))
                    != 1
                ):
                    raise FenceRejected("existing Run is not this claimed Task")
                if pin.cancel_requested:
                    from actions.server.run_outputs.types import AttemptFence

                    fence = None
                    if pin.current_attempt_id:
                        attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
                        fence = AttemptFence(
                            run_id=run.id,
                            attempt_id=attempt.id,
                            owner_id=attempt.owner_id,
                            epoch=attempt.epoch,
                        )
                    state = validate_claimed_cancellation(
                        service, retained, run, pin, fence
                    )
                    expected = "active_unconfirmed" if fence else "pending_cancelled"
                    if state != expected:
                        raise FenceRejected("claimed cancellation replay differs")
                    return RunAdmissionOutcome(run, False)
                if run.status in (RunStatus.PASSED, RunStatus.FAILED):
                    return RunAdmissionOutcome(run, False)
            outcome = service.admit_claimed(
                caller,
                WorkItemClaim(
                    item_id=claim.item_id, owner_id=claim.owner_id, epoch=claim.epoch
                ),
            )
            expected = ClaimedTaskIntent.create(
                snapshot, claim, json.loads(outcome.run.inputs)
            ).canonical()
            if outcome.created:
                _insert(
                    self.db,
                    RunExecutionIntent(
                        outcome.run.id,
                        snapshot.workspace_id,
                        caller.actor.principal_id,
                        expected,
                    ),
                )
            elif (
                _one(self.db, RunExecutionIntent, outcome.run.id).envelope_json
                != expected
            ):
                raise FenceRejected("claimed Task intent differs")
            return outcome

    def _service(self, actor, snapshot):
        service = StandaloneActionExecution(self.deployments, self.outputs, snapshot)
        service.current(ManagedCaller(actor=actor))
        if snapshot.capability_authority != "package-revision":
            raise AccessDenied("verified ordinary Package capability required")
        if snapshot.runtime_kind != "rcc":
            from actions.server.foundry.robot_retained_projection import (
                robot_projection_if_present,
            )

            if (
                snapshot.runtime_kind != "direct"
                or robot_projection_if_present(self.db, snapshot) is None
            ):
                raise AccessDenied("verified RCC or direct Robot capability required")
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
        claimed = claimed_intent(intent.envelope_json)
        expected = (
            ClaimedTaskIntent.create(
                snapshot, claimed.claim, json.loads(run.inputs)
            ).canonical()
            if claimed is not None
            else self._envelope(snapshot, json.loads(run.inputs))
        )
        if claimed is not None:
            service = self.claimed_service(snapshot)
            envelope = GenericInput.model_validate(
                service.queue(service.policy.input_queue).load_payload(
                    claimed.claim.item_id
                )
            )
            if (
                claimed.snapshot != snapshot
                or envelope.snapshot != snapshot
                or envelope.policy != service.policy
                or envelope.input_digest != claimed.input_digest
                or claimed.claim.queue != service.queue_ref(service.policy.input_queue)
                or _canonical(envelope.inputs, 262144)
                != _canonical(json.loads(run.inputs), 262144)
            ):
                raise FenceRejected("claimed Task payload differs")
        if (
            intent.workspace_id != snapshot.workspace_id
            or intent.envelope_json != expected
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
        return (
            (
                self.claimed_service(snapshot)
                if self.claimed(run_id) is not None
                else self._service(actor, snapshot)
            ),
            run,
            pin,
        )

    def pending(
        self,
        actor,
        workspace_id,
        worker_profile,
        *,
        limit=20,
        after=None,
        worker_id=None,
    ):
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
                intent = self.claimed(row[0])
                if intent is not None:
                    if worker_id is None or intent.claim.owner_id != worker_id:
                        continue
                    service = self.claimed_service(snapshot)
                    service._current(ManagedCaller(actor=actor, worker_id=worker_id))
                else:
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
        intent = self.claimed(run_id)
        if intent is not None:
            service = self.claimed_service(intent.snapshot)
            with service._transaction():
                snapshot, run, _ = self._integrity(caller.actor, run_id)
                if run.status not in (RunStatus.NOT_RUN, RunStatus.RUNNING):
                    raise FenceRejected("claimed Task Run is terminal")
                if (
                    snapshot.worker != worker_profile
                    or caller.worker_id != intent.claim.owner_id
                ):
                    raise AccessDenied("claimed Task worker differs")
                return service.dispatch(
                    caller,
                    WorkItemClaim(
                        item_id=intent.claim.item_id,
                        owner_id=intent.claim.owner_id,
                        epoch=intent.claim.epoch,
                    ),
                    lease_seconds=lease_seconds,
                )
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
            from actions.server.foundry.logical_receipts import versions_for_selection

            dispatch_version = versions_for_selection(
                service.registry, service.snapshot
            )[0]
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
                            "version": dispatch_version,
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

    def __init__(
        self,
        authority,
        actor,
        worker_id,
        profile,
        *,
        stop_requested=None,
        logical_execution=None,
        capability_runner=None,
    ):
        canonical_uuid(worker_id)
        if stop_requested is not None and not callable(stop_requested):
            raise ValueError("trusted stop callback required")
        self.logical_execution = logical_execution
        self.capability_runner = capability_runner
        self._stop_requested = stop_requested
        self.authority, self.profile = authority, profile
        self.caller = ManagedCaller(actor=actor, worker_id=worker_id)

    def run_once(self, *, prepared, rcc: Path, execution_root: Path, after=None):
        """Consume one bounded page; host owns polling and connection lifetime."""
        page = self.authority.pending(
            self.caller.actor,
            str(self.profile.workspace_id.root),
            self.profile,
            after=after,
            worker_id=self.caller.worker_id,
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
        if self._stop_requested is not None and self._stop_requested():
            return True
        intent = self.authority.claimed(ticket.fence.run_id)
        if intent is not None:
            service = self.authority.claimed_service(intent.snapshot)
            with service._transaction():
                snapshot, run, pin = self.authority._integrity(
                    self.caller.actor, ticket.fence.run_id
                )
                if (
                    snapshot.worker != self.profile
                    or intent.claim.owner_id != self.caller.worker_id
                ):
                    raise FenceRejected("claimed worker binding differs")
                if pin.cancel_requested:
                    validate_claimed_cancellation(
                        service, intent, run, pin, ticket.fence
                    )
                    return True
                claim = WorkItemClaim(
                    item_id=intent.claim.item_id,
                    owner_id=intent.claim.owner_id,
                    epoch=intent.claim.epoch,
                )
                if service._ticket(self.caller, claim, run) != ticket:
                    raise FenceRejected("claimed worker ticket differs")
                service.outputs(self.caller, ticket)._fence(ticket.fence)
                return False
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
        from actions.server.foundry.logical_receipts import requirement_ids

        if self.cancelled(ticket):
            raise FenceRejected("detached cancellation requested")
        service, _, _ = self.authority._load(self.caller.actor, ticket.fence.run_id)
        if self.capability_runner is not None:
            robot = self.capability_runner.robot_for(service.registry, service.snapshot)
            if robot is not None:
                return robot.execute(
                    self.caller,
                    ticket,
                    service,
                    cancelled=lambda: self.cancelled(ticket),
                    publication_cancelled=self._stop_requested,
                )
        return GeneratedRccExecution(
            service.registry,
            service.outputs(self.caller, ticket),
            prepared,
            rcc,
            execution_root,
            **(
                {"logical_execution": self.logical_execution}
                if self.logical_execution is not None
                else {}
            ),
        ).execute(
            self.caller.actor,
            ticket.fence,
            cancelled=lambda: self.cancelled(ticket),
            **(
                {"publication_cancelled": self._stop_requested}
                if self.logical_execution is not None
                and self._stop_requested is not None
                and requirement_ids(service.registry, service.snapshot)
                else {}
            ),
        )
