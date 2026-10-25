"""Protocol-neutral ordinary Action Tasks over common SQL Run authority.

No scheduler, transport advertisement, interaction store or worker bootstrap.
Hosts supply readiness and explicit policy; model callers cannot supply either.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from actions.work_items._fencing import ClaimRejected, WorkItemClaim

from actions.server._models import Run, RunStatus
from actions.server.foundry.logical_receipts import (
    FAILURE_V1,
    validate_bound_record,
    versions_for_selection,
)
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.managed_work_items.contracts import (
    ClaimRef,
    ManagedCaller,
    Permission,
)
from actions.server.run_outputs.claimed_intent import ClaimedTaskIntent
from actions.server.run_outputs.claimed_task_state import validate_claimed_cancellation
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import (
    RunAttempt,
    RunOutput,
    RunPin,
    RunTaskReceipt,
)
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _advance_lifecycle,
    _canonical,
    _insert,
    _key,
    _lock_run,
    _lock_workspace,
    _now,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    ExecutionSnapshot,
    OutputRef,
    canonical_uuid,
)

RECEIPT_VERSION = "actions.run-task-receipt/v1"
CLAIMED_RECEIPT_VERSION = "actions.run-task-receipt/claimed-v1"
RESULT_CONTRACT = "actions.detached-invocation-result/v1"
_MAX_MS = 9223372036854775807


class TaskUnavailable(AccessDenied):
    """Unknown, denied, expired or inconsistent Task; no existence disclosure."""


class TaskHostUnavailable(RuntimeError):
    """Configured consumption path is absent or unavailable; no private detail."""


class TaskHostReadiness(Protocol):
    def require_ready(self, actor: Actor, snapshot: ExecutionSnapshot) -> None:
        """Require an eligible configured consumption path; never grant authority."""
        ...


def _bounded_text(value: str) -> bool:
    return isinstance(value, str) and 1 <= len(value.encode()) <= 128


def _milliseconds(value: str) -> int:
    if (
        not isinstance(value, str)
        or not value.isascii()
        or not value.isdecimal()
        or str(int(value)) != value
    ):
        raise ValueError("canonical milliseconds required")
    result = int(value)
    if not 0 < result <= _MAX_MS:
        raise ValueError("bounded milliseconds required")
    return result


@dataclass(frozen=True)
class TaskPolicy:
    policy_id: str
    ttl_ms: int
    poll_interval_ms: int

    def __post_init__(self):
        if (
            not _bounded_text(self.policy_id)
            or not isinstance(self.ttl_ms, int)
            or isinstance(self.ttl_ms, bool)
            or not 1 <= self.ttl_ms <= 2147483647
            or not isinstance(self.poll_interval_ms, int)
            or isinstance(self.poll_interval_ms, bool)
            or not 1 <= self.poll_interval_ms <= min(60000, self.ttl_ms)
        ):
            raise ValueError("explicit bounded Task policy required")


@dataclass(frozen=True)
class TaskSnapshot:
    task_id: str
    status: Literal["working", "completed", "cancelled"]
    created_ms: int
    last_updated_ms: int
    ttl_ms: int
    poll_interval_ms: int
    status_message: str
    result: dict[str, Any] | None = None


class TaskService:
    def __init__(
        self,
        detached: DetachedActions,
        *,
        readiness: TaskHostReadiness,
        policy: TaskPolicy,
    ):
        if not callable(getattr(readiness, "require_ready", None)) or not isinstance(
            policy, TaskPolicy
        ):
            raise ValueError("trusted worker readiness and explicit policy required")
        self.detached, self.outputs, self.db = detached, detached.outputs, detached.db
        self.readiness, self.policy = readiness, policy

    def _require_ready(self, actor: Actor, snapshot: ExecutionSnapshot) -> None:
        try:
            check: Callable[
                [Actor, ExecutionSnapshot], object
            ] = self.readiness.require_ready
            if check(actor, snapshot) is not None:
                raise ValueError("readiness contract differs")
        except Exception:
            raise TaskHostUnavailable("Task host unavailable") from None

    @staticmethod
    def _fingerprint(pin, policy_id, ttl_ms, intent: ClaimedTaskIntent | None = None):
        if intent is not None:
            return _key(
                "actions.task-invocation/claimed-v1",
                pin.request_fingerprint,
                CLAIMED_RECEIPT_VERSION,
                "tools/call",
                "capability_invoke",
                RESULT_CONTRACT,
                policy_id,
                str(ttl_ms),
                hashlib.sha256(intent.canonical().encode()).hexdigest(),
            )
        return _key(
            "actions.task-invocation/v1",
            pin.request_fingerprint,
            RECEIPT_VERSION,
            "tools/call",
            "capability_invoke",
            RESULT_CONTRACT,
            policy_id,
            str(ttl_ms),
        )

    def create(
        self,
        actor: Actor,
        workspace_id: str,
        snapshot: ExecutionSnapshot,
        inputs: Any,
        idempotency_key: str,
    ) -> TaskSnapshot:
        actor = Actor.model_validate(actor)
        snapshot = ExecutionSnapshot.model_validate(snapshot)
        if workspace_id != snapshot.workspace_id or not _bounded_text(idempotency_key):
            raise TaskUnavailable("Task unavailable")
        # Readiness is host configuration, not a request-provided callback or grant.
        self._require_ready(actor, snapshot)
        with _transaction(self.db):
            outcome = self.detached.admit_outcome(
                actor, snapshot, inputs, idempotency_key
            )
            self._require_ready(actor, snapshot)
            return self._record_admission(actor, workspace_id, outcome)

    def _require_claimed_ready(self, actor, snapshot, claim, *, scope_only=False):
        try:
            check = getattr(
                self.readiness,
                "require_claimed_scope" if scope_only else "require_claimed_ready",
                None,
            )
            if not callable(check):
                raise ValueError("claimed readiness unavailable")
            if check(actor, snapshot, claim) is not None:
                raise ValueError("claimed readiness contract differs")
        except Exception:
            raise TaskHostUnavailable("Task host unavailable") from None

    def create_claimed(self, actor, workspace_id, snapshot, claim: ClaimRef):
        try:
            return self._create_claimed(actor, workspace_id, snapshot, claim)
        except ClaimRejected:
            raise TaskUnavailable("Task unavailable") from None

    def _create_claimed(self, actor, workspace_id, snapshot, claim: ClaimRef):
        actor = Actor.model_validate(actor)
        snapshot = ExecutionSnapshot.model_validate(snapshot)
        claim = ClaimRef.model_validate(claim)
        if workspace_id != snapshot.workspace_id:
            raise TaskUnavailable("Task unavailable")
        self._require_claimed_ready(actor, snapshot, claim)
        service = self.detached.claimed_service(snapshot)
        # Match the existing Generic lock order before any Run row lock.
        with service._transaction():
            self._require_claimed_ready(actor, snapshot, claim, scope_only=True)
            outcome = self.detached.admit_claimed(
                ManagedCaller(actor=actor, worker_id=claim.owner_id), snapshot, claim
            )
            self._require_claimed_ready(actor, snapshot, claim, scope_only=True)
            return self._record_admission(actor, workspace_id, outcome)

    def _record_admission(self, actor, workspace_id, outcome):
        run = outcome.run
        intent = self.detached.claimed(run.id)
        pin = _one(self.db, RunPin, run.id)
        receipts = self.db.all(RunTaskReceipt, where="id=?", values=[run.id])
        if outcome.created:
            if receipts:
                raise TaskUnavailable("Task unavailable")
            created = _milliseconds(pin.state_updated_ms)
            if created + self.policy.ttl_ms > _MAX_MS:
                raise TaskUnavailable("Task unavailable")
            _insert(
                self.db,
                RunTaskReceipt(
                    run.id,
                    run.id,
                    workspace_id,
                    actor.principal_id,
                    CLAIMED_RECEIPT_VERSION if intent is not None else RECEIPT_VERSION,
                    "tools/call",
                    "capability_invoke",
                    RESULT_CONTRACT,
                    self._fingerprint(
                        pin, self.policy.policy_id, self.policy.ttl_ms, intent
                    ),
                    str(created),
                    str(self.policy.ttl_ms),
                    self.policy.policy_id,
                ),
            )
        elif (
            len(receipts) != 1
            or receipts[0].ttl_policy_id != self.policy.policy_id
            or receipts[0].ttl_ms != str(self.policy.ttl_ms)
        ):
            raise TaskUnavailable("Task unavailable")
        loaded = self._load(actor, workspace_id, run.id, "execute")
        return self._project(actor, loaded, include_result=False)

    def _load(self, actor, workspace_id, task_id, permission):
        try:
            canonical_uuid(workspace_id)
            canonical_uuid(task_id)
            _lock_workspace(self.db, workspace_id)
            pin = _lock_run(self.db, task_id)
            receipt = _one(self.db, RunTaskReceipt, task_id)
            snapshot, run, checked = self.detached._integrity(actor, task_id)
            self.outputs._authorize(actor, snapshot, permission)
            intent = self.detached.claimed(task_id)
            if intent is not None and permission == "read":
                self.detached.claimed_service(snapshot).authorize(
                    ManagedCaller(actor=actor), Permission.READ
                )
            if pin.cancel_requested not in (0, 1):
                raise ValueError("cancellation flag differs")
            if pin != checked or (
                receipt.id,
                receipt.run_id,
                receipt.workspace_id,
                receipt.admission_principal_id,
                receipt.receipt_version,
                receipt.original_method,
                receipt.original_tool_name,
                receipt.result_contract_version,
            ) != (
                task_id,
                task_id,
                workspace_id,
                actor.principal_id,
                CLAIMED_RECEIPT_VERSION if intent is not None else RECEIPT_VERSION,
                "tools/call",
                "capability_invoke",
                RESULT_CONTRACT,
            ):
                raise ValueError("receipt identity differs")
            created, ttl, updated = (
                _milliseconds(receipt.created_ms),
                _milliseconds(receipt.ttl_ms),
                _milliseconds(pin.state_updated_ms),
            )
            start = datetime.datetime.fromisoformat(run.start_time)
            if start.tzinfo is None:
                raise ValueError("UTC admission time required")
            elapsed = start - datetime.datetime(
                1970, 1, 1, tzinfo=datetime.timezone.utc
            )
            started_ms = (
                elapsed.days * 86400000
                + elapsed.seconds * 1000
                + elapsed.microseconds // 1000
            )
            if (
                snapshot.workspace_id != workspace_id
                or not _bounded_text(receipt.ttl_policy_id)
                or ttl > 2147483647
                or created + ttl > _MAX_MS
                or elapsed.microseconds % 1000
                or started_ms != created
                or updated < created
                or _now(self.db) >= created + ttl
                or receipt.invocation_fingerprint
                != self._fingerprint(pin, receipt.ttl_policy_id, ttl, intent)
            ):
                raise ValueError("receipt lifetime or invocation differs")
            return receipt, snapshot, run, pin
        except (AccessDenied, FenceRejected, ValueError, TypeError, KeyError):
            raise TaskUnavailable("Task unavailable") from None

    def get(self, actor: Actor, workspace_id: str, task_id: str) -> TaskSnapshot:
        with _transaction(self.db):
            return self._project(
                actor, self._load(actor, workspace_id, task_id, "read")
            )

    def cancel(self, actor: Actor, workspace_id: str, task_id: str) -> None:
        intent = self.detached.claimed(task_id)
        if intent is not None:
            return self._cancel_claimed(actor, workspace_id, task_id, intent)
        with _transaction(self.db):
            self._load(actor, workspace_id, task_id, "cancel")
            self.detached.cancel(actor, task_id)

    def _cancel_claimed(self, actor, workspace_id, task_id, intent):
        try:
            return self._cancel_claimed_checked(actor, workspace_id, task_id, intent)
        except ClaimRejected:
            raise TaskUnavailable("Task unavailable") from None

    def _cancel_claimed_checked(self, actor, workspace_id, task_id, intent):
        service = self.detached.claimed_service(intent.snapshot)
        caller = ManagedCaller(actor=actor, worker_id=intent.claim.owner_id)
        with service._transaction():
            _, snapshot, run, pin = self._load(actor, workspace_id, task_id, "cancel")
            queue_name = service.policy.input_queue
            if queue_name is None:
                raise TaskUnavailable("Task unavailable")
            service._permission(caller, queue_name, Permission.CANCEL)
            if pin.cancel_requested:
                fence = None
                if pin.current_attempt_id:
                    attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
                    fence = AttemptFence(
                        run_id=run.id,
                        attempt_id=attempt.id,
                        owner_id=attempt.owner_id,
                        epoch=attempt.epoch,
                    )
                validate_claimed_cancellation(service, intent, run, pin, fence)
                return
            if run.status in (RunStatus.PASSED, RunStatus.FAILED):
                self._project(
                    actor,
                    self._load(actor, workspace_id, task_id, "cancel"),
                    include_result=False,
                )
                return
            claim = WorkItemClaim(
                intent.claim.item_id, intent.claim.owner_id, intent.claim.epoch
            )
            queue = service.queue(queue_name)
            # The owner transaction shares the canonical queue workspace lock.
            queue._require(claim)
            fence = None
            if pin.current_attempt_id:
                attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
                fence = AttemptFence(
                    run_id=run.id,
                    attempt_id=attempt.id,
                    owner_id=attempt.owner_id,
                    epoch=attempt.epoch,
                )
                self.outputs._fence(fence)
            elif run.status != RunStatus.NOT_RUN or run.result is not None:
                raise FenceRejected("claimed pending cancellation differs")
            if not self.outputs.cancel(actor, run.id) or not queue.cancel(
                claim.item_id
            ):
                raise FenceRejected("claimed cancellation changed")
            if fence is None:
                _update(self.db, Run, run.id, {"status": RunStatus.CANCELLED})
                _advance_lifecycle(self.db, run.id)
            # Validate all retained facts before committing either SQL mutation.
            # Failure rolls back both owners; this grants no execution authority.
            outcome = validate_claimed_cancellation(
                service,
                intent,
                _one(self.db, Run, run.id),
                _one(self.db, RunPin, run.id),
                fence,
            )
            if outcome != (
                "pending_cancelled" if fence is None else "active_unconfirmed"
            ):
                raise FenceRejected("claimed cancellation evidence differs")

    def update(
        self,
        actor: Actor,
        workspace_id: str,
        task_id: str,
        input_responses: Mapping[str, object],
    ) -> None:
        if not isinstance(input_responses, Mapping) or len(input_responses) > 64:
            raise ValueError("bounded input responses required")
        _canonical(dict(input_responses), 16384)
        with _transaction(self.db):
            self._load(actor, workspace_id, task_id, "read")
        # Ordinary Actions have no outstanding interactions. Unknown answers do
        # not change execution, resume work, create interactions or extend TTL.

    def _project(self, actor, loaded, *, include_result=True):
        receipt, snapshot, run, pin = loaded
        status, message, result = "working", "Queued for configured worker.", None
        try:
            intent = self.detached.claimed(run.id)
            claim = (
                {
                    "item_id": intent.claim.item_id,
                    "owner_id": intent.claim.owner_id,
                    "epoch": intent.claim.epoch,
                }
                if intent is not None
                else None
            )
            if intent is not None and pin.cancel_requested:
                fence = None
                if pin.current_attempt_id:
                    attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
                    fence = AttemptFence(
                        run_id=run.id,
                        attempt_id=attempt.id,
                        owner_id=attempt.owner_id,
                        epoch=attempt.epoch,
                    )
                cancellation = validate_claimed_cancellation(
                    self.detached.claimed_service(snapshot), intent, run, pin, fence
                )
                return TaskSnapshot(
                    run.id,
                    "cancelled" if cancellation == "pending_cancelled" else "working",
                    int(receipt.created_ms),
                    int(pin.state_updated_ms),
                    int(receipt.ttl_ms),
                    self.policy.poll_interval_ms,
                    "Cancelled before execution."
                    if cancellation == "pending_cancelled"
                    else "Cancellation requested; outcome not confirmed.",
                    None,
                )
            if not pin.current_attempt_id:
                if run.status == RunStatus.CANCELLED and pin.cancel_requested == 1:
                    status, message = "cancelled", "Cancelled before execution."
                elif run.status != RunStatus.NOT_RUN:
                    raise ValueError("unclaimed state differs")
                elif pin.cancel_requested:
                    message = "Cancellation requested; outcome not confirmed."
            else:
                attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
                fence = AttemptFence(
                    run_id=run.id,
                    attempt_id=attempt.id,
                    owner_id=attempt.owner_id,
                    epoch=attempt.epoch,
                )
                expected = {
                    RunStatus.RUNNING: "running",
                    RunStatus.PASSED: "succeeded",
                    RunStatus.FAILED: "failed",
                }
                if (
                    attempt.run_id != run.id
                    or attempt.workspace_id != snapshot.workspace_id
                    or pin.epoch != attempt.epoch
                    or attempt.state != expected.get(run.status)
                ):
                    raise ValueError("Attempt differs")
                outer = json.loads(run.result or "null")
                terminal = run.status in (RunStatus.PASSED, RunStatus.FAILED)
                record = (
                    outer.get("result")
                    if terminal and isinstance(outer, dict)
                    else outer
                )
                if (
                    not isinstance(record, dict)
                    or record.get("mode")
                    != ("work-items" if claim is not None else "standalone")
                    or record.get("claim") != claim
                    or (
                        record.get("version")
                        != (
                            versions_for_selection(self.outputs.capabilities, snapshot)[
                                1 if terminal else 0
                            ]
                        )
                        and not (
                            run.status == RunStatus.FAILED
                            and record.get("version") == FAILURE_V1
                        )
                    )
                    or AttemptFence.model_validate(
                        record.get("publicationFence" if terminal else "fence")
                    )
                    != fence
                ):
                    raise ValueError("journal differs")
                validate_bound_record(
                    self.db,
                    self.outputs.capabilities,
                    snapshot,
                    run,
                    fence,
                    record,
                    claim=claim,
                    terminal=terminal,
                    outputs=outer.get("outputs") if terminal else None,
                    _allow_expired_terminal=terminal and not include_result,
                )
                if terminal:
                    if (
                        pin.cancel_requested
                        or not isinstance(outer.get("version"), int)
                        or isinstance(outer.get("version"), bool)
                        or outer["version"] != 1
                    ):
                        raise ValueError("terminal authority differs")
                    # Terminal replay creation may omit result but cannot fabricate
                    # a new execution. Reads resolve the complete sealed inventory.
                    verified_result = self._result(
                        actor,
                        snapshot,
                        run,
                        fence,
                        outer,
                        record,
                        resolve=include_result,
                        claim=claim,
                    )
                    if include_result:
                        result = verified_result
                    status, message = (
                        "completed",
                        "Execution failed."
                        if run.status == RunStatus.FAILED
                        else "Execution completed.",
                    )
                else:
                    launch = record.get("launch")
                    if set(record) - {
                        "version",
                        "mode",
                        "claim",
                        "fence",
                        "launch",
                        "execution",
                    }:
                        raise ValueError("unknown dispatch evidence")
                    if launch is None:
                        if record.get("execution") is not None:
                            raise ValueError("execution without launch")
                    elif record["version"] == "actions.robot-dispatch/v1":
                        # Strict Robot launch/selection equality was checked above
                        # against retained SQL metadata, not Python lineage fields.
                        pass
                    elif (
                        not isinstance(launch, dict)
                        or _canonical(launch.get("lineage"), 16384)
                        != _canonical(
                            GeneratedRccExecution._lineage(snapshot, None, fence), 16384
                        )
                        or launch.get("workItemClaim") is not None
                        or launch.get("packageRevision")
                        != snapshot.capability.package_revision.revision_id.root
                        or launch.get("runtimePlanDigest")
                        != snapshot.runtime_plan.plan_digest.root
                        or launch.get("inputDigest")
                        != "sha256:"
                        + hashlib.sha256(
                            _canonical(json.loads(run.inputs), 262144).encode()
                        ).hexdigest()
                    ):
                        raise ValueError("dispatch lineage differs")
                    else:
                        canonical_uuid(launch["id"])
                    message = (
                        "Cancellation requested; outcome not confirmed."
                        if pin.cancel_requested
                        else (
                            "Launch recorded; outcome not confirmed."
                            if record.get("launch") is not None
                            else "Worker claim recorded; outcome not confirmed."
                        )
                    )
            return TaskSnapshot(
                run.id,
                status,
                int(receipt.created_ms),
                int(pin.state_updated_ms),
                int(receipt.ttl_ms),
                self.policy.poll_interval_ms,
                message,
                result,
            )
        except (
            AccessDenied,
            FenceRejected,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            OSError,
        ):
            raise TaskUnavailable("Task unavailable") from None

    def _result(
        self, actor, snapshot, run, fence, outer, record, *, resolve=True, claim=None
    ):
        validate_bound_record(
            self.db,
            self.outputs.capabilities,
            snapshot,
            run,
            fence,
            record,
            claim=claim,
            terminal=True,
            outputs=outer.get("outputs"),
            _allow_expired_terminal=not resolve,
        )
        if record["version"] == "actions.robot-execution/v1":
            handles = []
            if resolve:
                for evidence in record["outputs"]:
                    ref = OutputRef.model_validate(evidence["ref"])
                    with self.outputs.resolve(
                        actor, snapshot.workspace_id, ref.handle
                    ) as sealed:
                        row = _one(self.db, RunOutput, ref.output_id)
                        if (
                            (sealed.run_id, sealed.digest, sealed.size)
                            != (run.id, evidence["digest"], evidence["size"])
                            or row.run_attempt_id != fence.attempt_id
                            or row.epoch != fence.epoch
                        ):
                            raise ValueError("resolved Robot output differs")
                        handles.append({"handle": ref.handle})
            return self._result_payload(run, fence, handles)
        if claim is not None:
            raise ValueError("claimed Task requires Robot terminal evidence")
        lineage = GeneratedRccExecution._lineage(snapshot, None, fence)
        from actions.server.foundry.execution_selection import compiled_for_snapshot

        compiled = compiled_for_snapshot(self.outputs.capabilities, snapshot)
        launch = record.get("launch")
        fixed = {
            "sourceArtifactDigest": compiled.source_artifact_digest,
            "packageRevision": snapshot.capability.package_revision.revision_id.root,
            "runtimePlanDigest": snapshot.runtime_plan.plan_digest.root,
            "rccSpecificationDigest": compiled.rcc_specification_digest,
            "rccArtifactDigest": compiled.rcc_artifact_digest,
        }
        digest = (
            "sha256:"
            + hashlib.sha256(
                _canonical(json.loads(run.inputs), 262144).encode()
            ).hexdigest()
        )
        if (
            _canonical(record.get("lineage"), 16384) != _canonical(lineage, 16384)
            or not isinstance(launch, dict)
            or _canonical(launch.get("lineage"), 16384) != _canonical(lineage, 16384)
            or launch.get("workItemClaim") is not None
            or launch.get("inputDigest") != digest
            or any(
                record.get(key) != value or launch.get(key) != value
                for key, value in fixed.items()
            )
        ):
            raise ValueError("terminal lineage differs")
        canonical_uuid(launch["id"])
        raw = outer.get("outputs")
        declared = record.get("outputs")
        if (
            not isinstance(raw, list)
            or not 1 <= len(raw) <= 64
            or not isinstance(declared, list)
            or len(raw) != len(declared)
        ):
            raise ValueError("sealed output inventory required")
        refs = [OutputRef.model_validate(value) for value in raw]
        if len({ref.handle for ref in refs}) != len(refs):
            raise ValueError("duplicate output")
        handles = []
        for ref, evidence in zip(refs, declared):
            if (
                not isinstance(evidence, dict)
                or set(evidence) != {"name", "ref", "digest", "size"}
                or not isinstance(evidence.get("size"), int)
                or isinstance(evidence.get("size"), bool)
                or evidence["size"] < 0
                or ref.run_id != run.id
                or ref.workspace_id != snapshot.workspace_id
                or evidence.get("ref") != ref.model_dump(mode="json")
            ):
                raise ValueError("output scope differs")
            if resolve:
                with self.outputs.resolve(
                    actor, snapshot.workspace_id, ref.handle
                ) as sealed:
                    row = _one(self.db, RunOutput, ref.output_id)
                    if (sealed.run_id, sealed.digest, sealed.size) != (
                        row.run_id,
                        row.digest,
                        row.size,
                    ):
                        raise ValueError("resolved output differs")
                    if (
                        row.run_attempt_id != fence.attempt_id
                        or row.epoch != fence.epoch
                        or (
                            evidence.get("name"),
                            evidence.get("digest"),
                            evidence.get("size"),
                        )
                        != (row.name, row.digest, row.size)
                    ):
                        raise ValueError("sealed publication differs")
                    handles.append({"handle": ref.handle})
        by_name = {item["name"]: item for item in declared}
        from actions.server.foundry.logical_receipts import generated_output_names

        expected_names = generated_output_names(record)
        execution = record.get("execution")
        if (
            set(by_name) != expected_names
            or len(declared) != len(expected_names)
            or not isinstance(execution, dict)
            or execution.get("status")
            != ("failed" if record.get("version") == FAILURE_V1 else "completed")
            or execution.get("artifactDigest") != compiled.rcc_artifact_digest
            or (
                record.get("version") != FAILURE_V1
                and execution.get("resultDigest")
                != by_name["generated-action-result.json"]["digest"]
            )
            or execution.get("receiptDigest") != by_name["rcc-receipt.json"]["digest"]
        ):
            raise ValueError("complete measured execution evidence required")
        for stream in ("stdout", "stderr"):
            measured = execution.get(stream)
            evidence = by_name[f"rcc-{stream}.log"]
            if not isinstance(measured, dict) or (
                measured.get("digest"),
                measured.get("retainedBytes"),
            ) != (evidence["digest"], evidence["size"]):
                raise ValueError("stream publication differs")
        return self._result_payload(run, fence, handles)

    @staticmethod
    def _result_payload(run, fence, handles):
        receipt = {
            "version": RESULT_CONTRACT,
            "runId": run.id,
            "attemptId": fence.attempt_id,
            "state": "failed" if run.status == RunStatus.FAILED else "completed",
            "outputs": handles,
        }
        message = (
            "Execution failed."
            if run.status == RunStatus.FAILED
            else "Execution completed."
        )
        result = {
            "content": [{"type": "text", "text": message}],
            "structuredContent": receipt,
            "isError": run.status == RunStatus.FAILED,
        }
        _canonical(result, 65536)
        return result
