"""Explicit reviewed execution through the common Canvas and capability facade.

The host supplies the RCC preparation and worker identity. No request can supply
code, execution profiles, replacement input, an approval or an audience grant.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from threading import Event

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from actions.server._models import Run, RunStatus
from actions.server.data_queries.review import ReviewProposal
from actions.server.deployments.package_revision_compiler import PreparedRccEnvironment
from actions.server.foundry.activated_execution import ActivatedReviewedExecution
from actions.server.foundry.mcp import CanvasCaller, CanvasPort, CanvasReply
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.foundry.work_item_execution import (
    GeneratedWorkItemTicket,
    ReviewedGeneratedRun,
)
from actions.server.run_outputs.service import AccessDenied, _one
from actions.server.run_outputs.types import Actor


class ReviewedDispatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    binding_id: str = Field(alias="bindingId", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    proposal: ReviewProposal


@dataclass(frozen=True)
class PinnedReviewedRccRunner:
    """Trusted host execution context; never derived from MCP arguments."""

    prepared: PreparedRccEnvironment
    rcc: Path
    execution_root: Path

    def execute(
        self,
        actor: Actor,
        ticket: GeneratedWorkItemTicket,
        service: ReviewedGeneratedRun,
    ) -> Run:
        registry = service.base.capabilities
        if not isinstance(registry, FoundryPackageRegistry):
            raise ValueError("common Package registry required")
        return GeneratedRccExecution(
            registry,
            service.outputs(actor, ticket),
            self.prepared,
            self.rcc,
            self.execution_root,
        ).execute(actor, ticket.fence, cancelled=Event())


_DISPATCH_SCHEMA = ReviewedDispatch.model_json_schema()
_DISPATCH_SCHEMA["description"] = (
    "Explicitly execute an already human-approved immutable result through the "
    "active app binding. This operation never approves a result or accepts "
    "replacement inputs, code, profiles or arbitrary commands. A prior uncertain "
    "launch requires reconciliation and is never automatically retried."
)


class ReviewedCanvasExecution(CanvasPort):
    """One fixed execution route; app sessions remain scoped and app-only."""

    def __init__(
        self,
        authoring: CanvasPort,
        execution: ActivatedReviewedExecution,
        *,
        runner: PinnedReviewedRccRunner | None = None,
    ):
        if {"canvas_dispatch", "capability_invoke"} & authoring.schemas.keys():
            raise ValueError("one canonical execution projection required")
        self.authoring, self.execution, self.runner = authoring, execution, runner
        self.schemas = dict(
            authoring.schemas,
            canvas_dispatch=_DISPATCH_SCHEMA,
            capability_invoke=_DISPATCH_SCHEMA,
        )

    async def call(
        self, caller: CanvasCaller, name: str, arguments: dict[str, JsonValue]
    ) -> CanvasReply:
        if name not in {"canvas_dispatch", "capability_invoke"}:
            return await self.authoring.call(caller, name, arguments)
        request = ReviewedDispatch.model_validate(arguments)
        scope = request.proposal.binding.scope
        if caller.workspace_id != scope.application.workspace_id:
            raise AccessDenied("execution outside authenticated Workspace")
        if name == "canvas_dispatch":
            if caller.audience != "app" or caller.scope != scope:
                raise AccessDenied("exact server-bound app session required")
        elif caller.audience != "model" or caller.scope is not None:
            raise AccessDenied("model capability context required")
        if self.runner is None:
            raise ValueError("trusted RCC runner is not configured")
        return await asyncio.to_thread(self._invoke, caller.actor, request)

    def _invoke(self, actor: Actor, request: ReviewedDispatch) -> CanvasReply:
        scope = request.proposal.binding.scope
        with self.execution.db.connect():
            ticket = self.execution.dispatch(
                actor, scope, request.binding_id, request.proposal
            )
            service = self.execution.resume(actor, ticket)
            run = _one(self.execution.db, Run, ticket.fence.run_id)
            if run.status in (RunStatus.PASSED, RunStatus.FAILED):
                state = "completed" if run.status == RunStatus.PASSED else "failed"
            else:
                record = json.loads(run.result or "null")
                if not isinstance(record, dict):
                    raise ValueError("retained dispatch journal required")
                if record.get("launch") is not None:
                    state = "reconciliation_required"
                else:
                    if self.runner is None:
                        raise ValueError("trusted RCC runner is not configured")
                    run = self.runner.execute(actor, ticket, service)
                    state = "completed" if run.status == RunStatus.PASSED else "failed"
            return CanvasReply(
                summary=f"Reviewed execution {state}.",
                model_result={
                    "execution": {
                        "state": state,
                        "runId": ticket.fence.run_id,
                        "attemptId": ticket.fence.attempt_id,
                        "workItemId": ticket.claim.item_id,
                    }
                },
            )
