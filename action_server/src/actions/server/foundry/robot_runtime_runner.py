"""Canonical Robot runner; no admission, retry or scheduling authority."""
from __future__ import annotations

import hashlib
import json
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Event
from typing import Callable, Protocol

from actions.work_items import State
from actions.work_items._fencing import ClaimRejected

from actions.server._models import Run, RunStatus
from actions.server.foundry.generic_work_item_execution import (
    GenericTicket,
    GenericWorkItemExecution,
)
from actions.server.foundry.robot_execution import (
    DISCRIMINATOR,
    DirectRobotPreparation,
    RccRobotPreparation,
    RobotCancellationStopped,
    RobotExecution,
    RobotExecutionResult,
    RobotSelection,
)
from actions.server.foundry.robot_execution_selection import prepare_robot_selection
from actions.server.foundry.robot_journal import RobotJournal, _launch
from actions.server.foundry.robot_lifecycle import VerifiedRobotLifecycle
from actions.server.foundry.robot_work_item_authority import (
    prepare_robot_work_item_authority,
)
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import ManagedCaller, Permission
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputService,
    _canonical,
    _one,
    _transaction,
)
from actions.server.run_outputs.types import Actor, AttemptFence

TERMINAL_VERSION = "actions.robot-execution/v1"


class RobotAdapter(Protocol):
    def execute(
        self,
        actor: Actor,
        fence: AttemptFence,
        *,
        selection: RobotSelection,
        source_archive: bytes,
        lifecycle: VerifiedRobotLifecycle,
        cancelled: Callable[[], bool],
        timeout_seconds: int,
    ) -> RobotExecutionResult:
        ...


class _RobotOutputs(RunOutputService):
    def __init__(
        self, service, caller, ticket, prepared, publication_cancelled=None, domain=None
    ):
        super().__init__(
            service.db, service.base.providers, capabilities=service.registry
        )
        self.caller, self.ticket, self.prepared = caller, ticket, prepared
        self.publication_cancelled = publication_cancelled
        self.service, self.domain = service, domain

    def _fence(self, fence):
        if self.domain is not None:
            self.domain._check(fence)
        pin = super()._fence(fence)
        if fence != self.ticket.fence:
            raise FenceRejected("different Robot Attempt")
        snapshot, inputs = self.prepared.outputs.execution_context(
            self.caller.actor, fence
        )
        self.prepared(self.caller.actor, fence, snapshot, inputs)
        return pin

    def heartbeat(self, fence, *, lease_seconds):
        if self.domain is None:
            return super().heartbeat(fence, lease_seconds=lease_seconds)
        with self.service._transaction():
            self._fence(fence)
            return self.domain.heartbeat(fence, lease_seconds=lease_seconds)

    def stage(self, fence, chunks, **kwargs):
        # Lifecycle bounds whole payloads; filesystem providers bound each chunk.
        # Keep provider IO in the existing base staging phases, outside SQL.
        def bounded():
            for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise ValueError("Robot output bytes required")
                for offset in range(0, len(chunk), 65536):
                    yield chunk[offset : offset + 65536]

        return super().stage(fence, bounded(), **kwargs)

    def publish_robot(self, result: RobotExecutionResult, journal: RobotJournal) -> Run:
        actor, fence = self.caller.actor, self.ticket.fence
        with (
            self.service._transaction()
            if self.domain is not None
            else _transaction(self.db)
        ):
            self._fence(fence)
            queue = self.domain._check(fence) if self.domain is not None else None
            if queue is not None:
                self.service._permission(
                    self.caller, self.service.policy.input_queue, Permission.COMPLETE
                )
            if (
                type(result) is not RobotExecutionResult
                or result.discriminator != DISCRIMINATOR
                or result.launch != journal.launch_intent(actor, fence)
            ):
                raise FenceRejected("Robot result has no exact acknowledged launch")
            if (
                result.status not in ("PASS", "FAIL")
                or result.return_code != (0 if result.status == "PASS" else 1)
                or not isinstance(result.return_code, int)
                or isinstance(result.return_code, bool)
                or not result.cleanup.execution_stopped
            ):
                raise FenceRejected("Robot terminal status or cleanup is incomplete")
            selection = self.prepared.selection
            expected = {
                "robot-stdout.log": "application/octet-stream",
                "robot-stderr.log": "application/octet-stream",
                "robot-output.xml": "application/xml",
            }
            if selection.plan_kind == "rcc":
                expected["rcc-receipt.json"] = "application/json"
            if len(result.outputs) != len(expected) or {
                value.name for value in result.outputs
            } != set(expected):
                raise FenceRejected("closed Robot artifact inventory required")
            records = []
            for value in result.outputs:
                row = _one(self.db, RunOutput, value.ref.output_id)
                if (
                    value.ref.run_id != fence.run_id
                    or value.ref.workspace_id != selection.snapshot.workspace_id
                    or (
                        row.run_id,
                        row.run_attempt_id,
                        row.epoch,
                        row.name,
                        row.media_type,
                        row.digest,
                        row.size,
                        row.state,
                    )
                    != (
                        fence.run_id,
                        fence.attempt_id,
                        fence.epoch,
                        value.name,
                        expected[value.name],
                        value.digest,
                        value.byte_length,
                        "provisional",
                    )
                    or value.media_type != expected[value.name]
                    or type(value.byte_length) is not int  # noqa: E721 - exact portable scalar
                    or type(value.observed_bytes) is not int  # noqa: E721 - exact portable scalar
                    or value.observed_bytes < value.byte_length
                    or type(value.truncated) is not bool  # noqa: E721 - exact portable scalar
                    or value.truncated != (value.observed_bytes > value.byte_length)
                ):
                    raise FenceRejected("Robot output differs from sealed artifact")
                records.append(
                    {
                        "name": value.name,
                        "ref": value.ref.model_dump(mode="json"),
                        "digest": value.digest,
                        "size": value.byte_length,
                        "observedBytes": value.observed_bytes,
                        "truncated": value.truncated,
                    }
                )
            receipt = {
                "version": TERMINAL_VERSION,
                "mode": "work-items" if self.ticket.claim is not None else "standalone",
                "claim": self.ticket.claim.model_dump(mode="json")
                if self.ticket.claim is not None
                else None,
                "launch": _launch(result.launch),
                "publicationFence": fence.model_dump(mode="json"),
                "packageRevision": selection.snapshot.capability.package_revision.model_dump(
                    mode="json"
                ),
                "runtimePlanDigest": selection.snapshot.runtime_plan.plan_digest.root,
                "sourceArtifactDigest": selection.source_digest,
                "status": result.status,
                "returnCode": result.return_code,
                "cleanup": asdict(result.cleanup),
                "outputs": records,
                "actionResult": {
                    "suite": selection.suite_name,
                    "task": selection.task_name,
                    "status": result.status,
                },
            }
            if self.publication_cancelled is not None and self.publication_cancelled():
                raise FenceRejected("Robot publication cancelled")
            # Base publication performs fresh authority/fence checks and the atomic
            # terminal Run/Attempt/output transition under the same transaction.
            finished = super().publish(
                actor,
                fence,
                [value.ref for value in result.outputs],
                receipt,
                terminal_status=RunStatus.PASSED
                if result.status == "PASS"
                else RunStatus.FAILED,
            )

            if queue is not None:
                queue.finish_fenced(
                    self.ticket.claim.as_claim(),
                    State.DONE if result.status == "PASS" else State.FAILED,
                    outputs=(),
                    message="Robot execution completed"
                    if result.status == "PASS"
                    else "Robot execution failed",
                )
            return finished


@dataclass(frozen=True)
class PinnedRobotRunner:
    preparation: DirectRobotPreparation | RccRobotPreparation
    execution_root: Path
    lease_seconds: int = 60
    retention_seconds: int = 3600
    timeout_seconds: int = 60
    adapter_factory: Callable[
        [Path, DirectRobotPreparation | RccRobotPreparation], RobotAdapter
    ] = RobotExecution

    def require_ready(self, service):
        self._require_ready_declaration(service, "none")

    def require_claimed_ready(self, service):
        if (
            not isinstance(service, GenericWorkItemExecution)
            or service.policy.input_mode != "claim"
            or service.policy.input_queue is None
        ):
            raise AccessDenied("claimed consumer Robot policy required")
        self._require_ready_declaration(service, "consumer")

    def _require_ready_declaration(self, service, mode):
        declaration = service.registry.get_capability(service.snapshot.capability)
        if (
            declaration is None
            or declaration.work_items.mode != mode
            or declaration.work_items.allow_outputs
            or declaration.binding_requirements
        ):
            raise AccessDenied(
                "standalone Robot declaration required"
                if mode == "none"
                else "claimed consumer Robot declaration required"
            )
        if mode == "consumer":
            service.policy.require_declaration(declaration.work_items)
        repository = service.deployments._repository
        with _transaction(service.db):
            retained = repository.current(
                service.snapshot.deployment.workspace_id,
                service.snapshot.deployment.deployment_id,
            )
            if (
                retained is None
                or retained.revision.ref != service.snapshot.deployment
                or not repository.was_activated(service.snapshot.deployment)
            ):
                raise AccessDenied("current activated Robot Deployment required")

    def execute(
        self,
        caller: ManagedCaller,
        ticket: GenericTicket,
        service: StandaloneActionExecution | GenericWorkItemExecution,
        *,
        cancelled: Event | Callable[[], bool] | None = None,
        publication_cancelled: Callable[[], bool] | None = None,
    ) -> Run:
        caller = ManagedCaller.model_validate(caller)
        ticket = GenericTicket.model_validate(ticket)
        if caller.worker_id != ticket.fence.owner_id:
            raise AccessDenied("exact Robot worker required")
        domain = None
        binding = nullcontext()
        if isinstance(service, GenericWorkItemExecution):
            authority = prepare_robot_work_item_authority(service, caller, ticket)
            domain = service.outputs(caller, ticket)
            binding = domain.bind_execution_authority(authority)
        with binding:
            return self._execute(
                caller,
                ticket,
                service,
                cancelled=cancelled,
                publication_cancelled=publication_cancelled,
                domain=domain,
            )

    def _execute(
        self,
        caller: ManagedCaller,
        ticket: GenericTicket,
        service: StandaloneActionExecution | GenericWorkItemExecution,
        *,
        domain=None,
        cancelled: Event | Callable[[], bool] | None = None,
        publication_cancelled: Callable[[], bool] | None = None,
    ) -> Run:
        caller, ticket = (
            ManagedCaller.model_validate(caller),
            GenericTicket.model_validate(ticket),
        )
        if domain is None and ticket.claim is not None:
            raise AccessDenied("claimed Robot unsupported by standalone admission")
        if (
            not isinstance(
                service, (StandaloneActionExecution, GenericWorkItemExecution)
            )
            or caller.worker_id != ticket.fence.owner_id
        ):
            raise AccessDenied("retained Robot admission and exact worker required")
        if service.db.in_transaction():
            raise FenceRejected("Robot execution requires independent journal commit")
        declaration = service.registry.get_capability(service.snapshot.capability)
        if (
            declaration is None
            or declaration.work_items.mode
            not in (
                ("none",)
                if domain is None
                else ("optional", "required-input", "consumer")
            )
            or (
                domain is not None
                and ticket.claim is None
                and declaration.work_items.mode != "optional"
            )
            or declaration.work_items.allow_outputs
            or declaration.binding_requirements
        ):
            raise AccessDenied(
                "Robot requires an admitted input mode without logical or queue outputs"
            )
        resolved = service.deployments.resolve(
            caller.actor,
            service.snapshot.deployment.workspace_id,
            service.snapshot.deployment.deployment_id,
            service.snapshot.capability,
            revision=service.snapshot.deployment,
            runtime_plan=service.snapshot.runtime_plan,
        )
        if resolved.snapshot != service.snapshot:
            raise AccessDenied("exact admitted Robot snapshot required")
        repository = service.deployments._repository
        with _transaction(service.db):
            retained = repository.current(
                service.snapshot.deployment.workspace_id,
                service.snapshot.deployment.deployment_id,
            )
            if (
                retained is None
                or retained.revision.ref != service.snapshot.deployment
                or not repository.was_activated(service.snapshot.deployment)
            ):
                raise AccessDenied("current activated Robot Deployment required")

        def require_current(actor, fence, snapshot):
            if domain is not None:
                domain._check(fence)
            current = repository.current(
                snapshot.deployment.workspace_id, snapshot.deployment.deployment_id
            )
            if (
                actor != caller.actor
                or fence != ticket.fence
                or snapshot != service.snapshot
                or current != retained
                or snapshot
                not in tuple(item.snapshot for item in current.execution_snapshots)
            ):
                raise FenceRejected("Robot current Deployment identity changed")
            if not repository.was_activated(snapshot.deployment):
                raise AccessDenied("Robot Deployment activation unavailable")
            for package in retained.revision.specification.package_revisions:
                service.deployments._authorization.require_reference(
                    actor, package, "execute"
                )
            service.base._authorize(actor, snapshot, "execute")
            run = _one(service.db, Run, fence.run_id)
            if (
                "sha256:"
                + hashlib.sha256(
                    _canonical(json.loads(run.inputs), 262144).encode()
                ).hexdigest()
                != ticket.input_digest
            ):
                raise FenceRejected("Robot ticket input identity changed")

        prepared = prepare_robot_selection(
            service.base,
            service.registry,
            caller.actor,
            ticket.fence,
            require_current=require_current,
        )
        outputs = _RobotOutputs(
            service, caller, ticket, prepared, publication_cancelled, domain
        )

        def selected(actor, fence):
            snapshot, inputs = service.base.execution_context(actor, fence)
            return prepared(actor, fence, snapshot, inputs)

        journal = RobotJournal(outputs, selected)
        lifecycle = VerifiedRobotLifecycle(
            outputs,
            prepared,
            journal,
            lease_seconds=self.lease_seconds,
            retention_seconds=self.retention_seconds,
        )
        # Existing intent must reject before adapter construction or process work.
        if lifecycle.launch_intent(caller.actor, ticket.fence) is not None:
            raise FenceRejected("existing Robot launch requires reconciliation")
        is_cancelled = (
            cancelled if callable(cancelled) else (cancelled or Event()).is_set
        )
        if is_cancelled():
            raise FenceRejected("Robot execution cancelled")
        try:
            result = self.adapter_factory(
                self.execution_root, self.preparation
            ).execute(
                caller.actor,
                ticket.fence,
                selection=prepared.selection,
                source_archive=prepared.source_archive,
                lifecycle=lifecycle,
                cancelled=is_cancelled,
                timeout_seconds=self.timeout_seconds,
            )
        except RobotCancellationStopped as stopped:
            from actions.server.run_outputs.cancellation_confirmation import (
                confirm_claimed_robot_cancellation,
            )

            return confirm_claimed_robot_cancellation(service, caller, ticket, stopped)
        if is_cancelled():
            from actions.server.run_outputs.cancellation_confirmation import (
                confirm_claimed_robot_cancellation,
            )

            return confirm_claimed_robot_cancellation(
                service,
                caller,
                ticket,
                RobotCancellationStopped(
                    result.launch, result.cleanup, directory=self.execution_root
                ),
            )
        try:
            lifecycle.check_live(caller.actor, ticket.fence, prepared.selection)
            return outputs.publish_robot(result, journal)
        except (FenceRejected, ClaimRejected) as error:
            if (
                type(error) not in (FenceRejected, ClaimRejected)
                or is_cancelled() is not True
            ):
                raise
            from actions.server.run_outputs.cancellation_confirmation import (
                confirm_claimed_robot_cancellation,
            )

            return confirm_claimed_robot_cancellation(
                service,
                caller,
                ticket,
                RobotCancellationStopped(
                    result.launch, result.cleanup, directory=self.execution_root
                ),
            )
