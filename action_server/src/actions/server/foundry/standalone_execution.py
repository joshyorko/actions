"""Ordinary mode=none admission on the existing Run journal, without a Work Item."""
from __future__ import annotations

import hashlib
import json

from actions.server._models import Run, RunStatus
from actions.server.foundry.generic_work_item_execution import GenericTicket
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
    _canonical,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import AttemptFence


class StandaloneActionExecution:
    def __init__(self, deployments, outputs, snapshot):
        if deployments._repository._db is not outputs.db or not isinstance(
            outputs.capabilities, FoundryPackageRegistry
        ):
            raise ValueError("common Package/Deployment/Run authority required")
        self.deployments, self.base, self.snapshot = deployments, outputs, snapshot
        self.db, self.registry = outputs.db, outputs.capabilities

    def current(self, caller):
        s = self.snapshot
        resolved = self.deployments.resolve(
            caller.actor,
            s.deployment.workspace_id,
            s.deployment.deployment_id,
            s.capability,
            revision=s.deployment,
            runtime_plan=s.runtime_plan,
        )
        declaration = self.registry.get_capability(s.capability)
        if (
            resolved.snapshot != s
            or declaration is None
            or declaration.work_items.mode != "none"
            or declaration.work_items.allow_outputs
        ):
            raise AccessDenied("ordinary no-Work-Item declaration required")
        self.base._authorize(caller.actor, s, "execute")

    def ticket(self, caller, run):
        self.current(caller)
        pin = _one(self.db, RunPin, run.id)
        attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
        fence = AttemptFence(
            run_id=run.id,
            attempt_id=attempt.id,
            owner_id=attempt.owner_id,
            epoch=attempt.epoch,
        )
        outer = json.loads(run.result or "null")
        terminal = run.status in (RunStatus.PASSED, RunStatus.FAILED)
        if terminal:
            if (
                not isinstance(outer, dict)
                or not isinstance(outer.get("version"), int)
                or isinstance(outer.get("version"), bool)
                or outer.get("version") != 1
            ):
                raise FenceRejected("ordinary output version differs")
            record = outer.get("result")
        else:
            record = outer
        if (
            not isinstance(record, dict)
            or record.get("version")
            != (
                "actions.generated-rcc-execution/v1"
                if terminal
                else "actions.generated-rcc-dispatch/v1"
            )
            or record.get("claim") is not None
            or record.get("publicationFence" if terminal else "fence")
            != fence.model_dump()
            or pin.epoch != fence.epoch
            or caller.worker_id != fence.owner_id
            or self.base._pinned(pin) != self.snapshot
            or attempt.run_id != run.id
            or attempt.workspace_id != str(self.snapshot.deployment.workspace_id.root)
            or pin.workspace_id != attempt.workspace_id
            or (not terminal and record.get("mode") != "standalone")
        ):
            raise FenceRejected("ordinary retained dispatch differs")
        return GenericTicket(
            claim=None,
            fence=fence,
            input_digest="sha256:"
            + hashlib.sha256(
                _canonical(json.loads(run.inputs), 262144).encode()
            ).hexdigest(),
        )

    def dispatch_standalone(self, caller, inputs, key, *, lease_seconds=60):
        with _transaction(self.db):
            self.current(caller)
            if caller.worker_id is None:
                raise AccessDenied("trusted worker required")
            RunOutputControlPlane(self.db, capabilities=self.registry).register(
                self.snapshot
            )
            run = self.base.admit(caller.actor, self.snapshot, inputs, key)
            pin = _one(self.db, RunPin, run.id)
            if not pin.current_attempt_id:
                fence = self.base.claim(
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
                run = _one(self.db, Run, run.id)
            return self.ticket(caller, run)

    def outputs(self, caller, ticket):
        return _StandaloneOutputs(self, caller, ticket)


class _StandaloneOutputs(RunOutputService):
    def __init__(self, owner, caller, ticket):
        super().__init__(owner.db, owner.base.providers, capabilities=owner.registry)
        self.owner, self.caller, self.ticket = owner, caller, ticket

    def _fence(self, fence):
        if (
            fence != self.ticket.fence
            or self.owner.ticket(self.caller, _one(self.db, Run, fence.run_id))
            != self.ticket
        ):
            raise FenceRejected("ordinary Run ticket differs")
        return super()._fence(fence)

    def publish(
        self, actor, fence, outputs, result, *, terminal_status=RunStatus.PASSED
    ):
        if actor != self.caller.actor or terminal_status != RunStatus.PASSED:
            raise AccessDenied("ordinary success-only RCC publication required")
        with _transaction(self.db):
            self.owner.current(self.caller)
            run = _one(self.db, Run, fence.run_id)
            if (
                self.owner.ticket(self.caller, run) != self.ticket
                or fence != self.ticket.fence
            ):
                raise FenceRejected("ordinary retained ticket differs")
            if (
                not isinstance(result, dict)
                or result.get("version") != "actions.generated-rcc-execution/v1"
                or result.get("claim") is not None
                or result.get("publicationFence") != fence.model_dump()
            ):
                raise FenceRejected("ordinary RCC lineage required")
            if run.status != RunStatus.PASSED:
                journal = json.loads(run.result)
                if (
                    not journal.get("launch")
                    or not journal.get("execution")
                    or result.get("launch") != journal["launch"]
                    or result.get("execution") != journal["execution"]
                ):
                    raise FenceRejected("completed ordinary RCC journal required")
            from jsonschema import validate

            validate(
                result.get("actionResult"),
                json.loads(
                    self.owner.registry.schema_for(self.owner.snapshot).output_schema
                ),
            )
            return super().publish(
                actor, fence, outputs, result, terminal_status=terminal_status
            )
