"""Host-only status and cancellation for explicitly delegated child Runs."""

from __future__ import annotations

from actions.internal_runtime import ChildRunHandle, ChildRunState, ChildRunStatus

from actions.server._models import RUN_ID_COUNTER, Run, RunStatus
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import (
    RunAttempt,
    RunChildLineage,
    RunPin,
    RunTaskReceipt,
)
from actions.server.run_outputs.service import (
    AccessDenied,
    _one,
    _returning,
    _transaction,
)
from actions.server.run_outputs.types import Actor, AttemptFence


class InternalChildRunLifecycle:
    """Read or request cancellation for a child selected by a live parent.

    The caller is the trusted per-Action host adapter. Parent and Actor identity
    are derived from the live AttemptFence and persisted Run state; the Action
    supplies only its binding name and opaque child handle.
    """

    def __init__(self, detached: DetachedActions):
        if not isinstance(detached, DetachedActions):
            raise TypeError("DetachedActions authority required")
        self.detached = detached
        self.deployments = detached.deployments
        self.outputs = detached.outputs
        self.db = detached.db

    def status(
        self, parent_fence: AttemptFence, binding_name: str, handle: ChildRunHandle
    ) -> ChildRunStatus:
        with self._child_operation(parent_fence, binding_name, handle, "read") as value:
            run, pin = value["run"], value["child_pin"]
            return self._project_status(self.db, handle, run, pin)

    def cancel(
        self, parent_fence: AttemptFence, binding_name: str, handle: ChildRunHandle
    ) -> ChildRunStatus:
        with self._child_operation(
            parent_fence, binding_name, handle, "cancel"
        ) as value:
            self.detached.cancel(value["actor"], handle.id)
            run = _one(self.db, Run, handle.id)
            pin = _one(self.db, RunPin, handle.id)
            return self._project_status(self.db, handle, run, pin)

    def _child_operation(
        self,
        parent_fence: AttemptFence,
        binding_name: str,
        handle: ChildRunHandle,
        operation: str,
    ):
        from contextlib import contextmanager

        if operation not in ("read", "cancel"):
            raise ValueError("closed child operation required")
        parent_fence = AttemptFence.model_validate(parent_fence)
        if (
            type(binding_name) is not str  # noqa: E721 - strict host protocol
            or not 1 <= len(binding_name.encode("utf-8", errors="strict")) <= 64
            or type(handle) is not ChildRunHandle  # noqa: E721 - typed opaque handle
        ):
            raise AccessDenied("Internal child unavailable or not authorized")

        @contextmanager
        def operation_context():
            # The host owns one thread-local connection and transaction for the
            # parent fence, current policy, lineage, child permission, and any
            # cancellation mutation. Counter -> Workspace is the existing Run
            # admission order; SQLite needs the writer before its first read.
            with self.db.connect(), _transaction(self.db):
                if not _returning(
                    self.db,
                    "UPDATE counter SET value=value WHERE id=? RETURNING id",
                    [RUN_ID_COUNTER],
                ):
                    raise AccessDenied("Internal child unavailable or not authorized")
                parent_pin = _one(self.db, RunPin, parent_fence.run_id)
                actor = Actor(principal_id=parent_pin.admission_principal_id)
                parent_snapshot = self.outputs._pinned(parent_pin)
                if parent_pin.id != parent_fence.run_id or (
                    parent_snapshot.workspace_id != parent_pin.workspace_id
                ):
                    raise AccessDenied("Internal child unavailable or not authorized")

                # _fence obtains the common Workspace lock and validates the
                # live parent Attempt. The lock serializes current Deployment
                # publication and same-Workspace grant revocation.
                self.outputs._fence(parent_fence)
                if self.db.backend_name == "postgresql":
                    self.db.select(
                        FoundryAccessGrant,
                        "SELECT * FROM foundry_access_grant "
                        "WHERE workspace_id=? AND principal_id=? "
                        "ORDER BY id LIMIT 129 FOR SHARE",
                        [parent_pin.workspace_id, actor.principal_id],
                    )
                self.outputs._authorize(actor, parent_snapshot, "execute")
                parent_run = _one(self.db, Run, parent_fence.run_id)
                if parent_run.status != RunStatus.RUNNING:
                    raise AccessDenied("Internal child unavailable or not authorized")

                current = self.deployments._repository.current(
                    parent_snapshot.deployment.workspace_id,
                    parent_snapshot.deployment.deployment_id,
                )
                if (
                    current is None
                    or current.revision.ref != parent_snapshot.deployment
                ):
                    raise AccessDenied("Internal child unavailable or not authorized")
                specification = current.revision.specification
                policies = [
                    policy
                    for policy in specification.internal_robot_delegations
                    if policy.parent_capability == parent_snapshot.capability
                ]
                if len(policies) != 1:
                    raise AccessDenied("Internal child unavailable or not authorized")
                binding = next(
                    (
                        item
                        for item in policies[0].bindings
                        if item.name == binding_name
                    ),
                    None,
                )
                if binding is None:
                    raise AccessDenied("Internal child unavailable or not authorized")
                self.deployments._validate_internal_robot_delegations(
                    actor, specification
                )
                target = self.deployments.resolve(
                    actor,
                    parent_snapshot.deployment.workspace_id,
                    binding.target_deployment.deployment_id,
                    binding.target_capability,
                    revision=binding.target_deployment,
                    runtime_plan=binding.target_runtime_plan,
                ).snapshot
                if target.runtime_kind != "rcc":
                    raise AccessDenied("Internal child unavailable or not authorized")

                lineage = self.db.all(
                    RunChildLineage,
                    where="parent_run_id=? AND child_run_id=?",
                    values=[parent_fence.run_id, handle.id],
                )
                if len(lineage) != 1:
                    raise AccessDenied("Internal child unavailable or not authorized")
                row = lineage[0]
                if (
                    row.workspace_id != parent_pin.workspace_id
                    or row.binding_name != binding_name
                    or row.parent_run_id != parent_fence.run_id
                    or row.child_run_id != handle.id
                    or self.db.all(
                        RunChildLineage,
                        where="child_run_id=?",
                        values=[parent_fence.run_id],
                    )
                ):
                    raise AccessDenied("Internal child unavailable or not authorized")
                if self.db.all(RunTaskReceipt, where="run_id=?", values=[handle.id]):
                    raise AccessDenied("Internal child unavailable or not authorized")

                child_snapshot, run, child_pin = self.detached._integrity(
                    actor, handle.id
                )
                if (
                    child_snapshot != target
                    or child_pin.run_id != handle.id
                    or child_pin.workspace_id != row.workspace_id
                    or child_pin.admission_principal_id != actor.principal_id
                    or run.id != handle.id
                ):
                    raise AccessDenied("Internal child unavailable or not authorized")
                self.outputs._authorize(actor, child_snapshot, operation)
                self.outputs._fence(parent_fence)
                yield {
                    "actor": actor,
                    "run": run,
                    "child_pin": child_pin,
                    "snapshot": child_snapshot,
                }

        return operation_context()

    @staticmethod
    def _project_status(
        db, handle: ChildRunHandle, run: Run, pin: RunPin
    ) -> ChildRunStatus:
        """Project canonical lifecycle only; never expose result or output data."""
        if pin.cancel_requested not in (0, 1):
            raise AccessDenied("Internal child lifecycle unavailable")
        attempts = db.all(RunAttempt, where="run_id=?", values=[run.id])
        if pin.id != run.id or pin.run_id != run.id:
            raise AccessDenied("Internal child lifecycle unavailable")
        if pin.current_attempt_id:
            # Recovery preserves prior Attempts as `lost`. Validate the full
            # epoch history and current identity; never mistake a historical
            # lost Attempt for current cancellation confirmation.
            if (
                pin.epoch < 1
                or len(attempts) != pin.epoch
                or {attempt.epoch for attempt in attempts}
                != set(range(1, pin.epoch + 1))
                or any(
                    attempt.run_id != run.id
                    or attempt.workspace_id != pin.workspace_id
                    or (attempt.epoch != pin.epoch and attempt.state != "lost")
                    for attempt in attempts
                )
            ):
                raise AccessDenied("Internal child lifecycle unavailable")
            attempt = next(
                (item for item in attempts if item.id == pin.current_attempt_id),
                None,
            )
            if attempt is None or attempt.epoch != pin.epoch:
                raise AccessDenied("Internal child lifecycle unavailable")
            expected_attempt = {
                RunStatus.RUNNING: "running",
                RunStatus.PASSED: "succeeded",
                RunStatus.FAILED: "failed",
            }.get(run.status)
            # Active cancellation confirmation is specific to Task receipts in
            # the current Runtime. Never infer a stopped child process from a
            # cancellation request or an untyped terminal Run state.
            if expected_attempt is None or attempt.state != expected_attempt:
                raise AccessDenied("Internal child lifecycle unavailable")
        elif attempts or pin.epoch != 0:
            raise AccessDenied("Internal child lifecycle unavailable")

        status_by_run = {
            RunStatus.NOT_RUN: ChildRunState.PENDING,
            RunStatus.PASSED: ChildRunState.SUCCEEDED,
            RunStatus.FAILED: ChildRunState.FAILED,
            RunStatus.CANCELLED: ChildRunState.CANCELLED,
        }
        state: ChildRunState | None
        if run.status == RunStatus.RUNNING:
            state = (
                ChildRunState.CANCEL_PENDING
                if pin.cancel_requested
                else ChildRunState.RUNNING
            )
        else:
            state = status_by_run.get(run.status)
            if state is None:
                raise AccessDenied("Internal child lifecycle unavailable")
        if state is ChildRunState.CANCELLED and pin.cancel_requested != 1:
            raise AccessDenied("Internal child lifecycle unavailable")
        if state is ChildRunState.PENDING and (
            pin.cancel_requested != 0 or run.result is not None
        ):
            raise AccessDenied("Internal child lifecycle unavailable")
        if state is ChildRunState.CANCELLED and (
            pin.current_attempt_id or run.result is not None
        ):
            raise AccessDenied("Internal child lifecycle unavailable")
        return ChildRunStatus(handle=handle, state=state)
