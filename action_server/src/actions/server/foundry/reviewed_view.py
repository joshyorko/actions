"""Join immutable authored UI to explicit result review on the official bridge."""

from __future__ import annotations

import asyncio
import copy
from dataclasses import replace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from actions.server.data_queries.review import ReviewExecutionComplete, ReviewProposal
from actions.server.data_queries.review_models import InvoiceReview
from actions.server.deployments.ids import DeploymentId, WorkspaceId
from actions.server.foundry.authoring import FoundryAuthoring
from actions.server.foundry.execution_port import ReviewedCanvasExecution
from actions.server.foundry.mcp import CanvasCaller, CanvasPort, CanvasReply
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.service import (
    AccessDenied,
    _key,
    _now,
    _one,
    _transaction,
)
from actions.server.run_outputs.types import CanvasResultScope, output_id_from_handle


class SavedResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    binding_id: str = Field(alias="bindingId", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    handle: str = Field(pattern=r"^art_[A-Za-z0-9_-]{22}$")


class ViewAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["offer", "decide", "execute"]
    handle: str | None = None
    proposal: ReviewProposal | None = None
    decision: Literal["approve", "reject"] | None = None
    binding_id: str | None = Field(default=None, alias="bindingId")


class ProposalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    proposal: ReviewProposal


class ArtifactInput(ProposalInput):
    kind: Literal["source", "result"] = "result"


class ReviewedCanvasView(CanvasPort):
    """No mount effects: opening reads only; every review/dispatch needs a click."""

    def __init__(self, execution: ReviewedCanvasExecution):
        if not isinstance(execution.authoring, FoundryAuthoring):
            raise ValueError("canonical SQL authoring authority required")
        self.authorization = execution.authoring.authorization
        self.execution = execution
        schemas = copy.deepcopy(dict(execution.schemas))
        properties = schemas["canvas_get"]["properties"]
        if not isinstance(properties, dict):
            raise ValueError("canonical authoring schema required")
        properties["reviewResult"] = SavedResult.model_json_schema()
        schemas["canvas_dispatch"] = ViewAction.model_json_schema()
        for name in (
            "canvas_get_state",
            "canvas_execution_status",
            "canvas_cancel",
            "canvas_artifact",
        ):
            schemas[name] = ProposalInput.model_json_schema()
        self.schemas = schemas
        schemas["canvas_artifact"] = ArtifactInput.model_json_schema()

    async def call(
        self, caller: CanvasCaller, name: str, arguments: dict[str, JsonValue]
    ) -> CanvasReply:
        inputs = dict(arguments)
        if name == "canvas_get" and "reviewResult" in inputs:
            saved = SavedResult.model_validate(inputs.pop("reviewResult"))
            reply = await self.execution.call(caller, name, inputs)
            return await asyncio.to_thread(self._open, caller, saved, reply)
        if name in {
            "canvas_dispatch",
            "canvas_get_state",
            "canvas_execution_status",
            "canvas_cancel",
            "canvas_artifact",
        }:
            return await asyncio.to_thread(self._app_call, caller, name, inputs)
        return await self.execution.call(caller, name, inputs)

    def _open(self, caller: CanvasCaller, saved: SavedResult, reply: CanvasReply):
        domain = self.execution.execution
        if (
            caller.audience != "model"
            or caller.scope is not None
            or reply.view_state is None
        ):
            raise AccessDenied("authorized model reopen required")
        view = reply.view_state
        recovered: dict[str, JsonValue] | None = None
        with domain.db.connect(), _transaction(domain.db):
            current = domain.deployments._repository.current(
                WorkspaceId.model_validate(caller.workspace_id),
                DeploymentId.model_validate(view["applicationId"]),
            )
            if (
                current is None
                or str(current.revision.ref.revision_id.root) != view["revisionId"]
            ):
                raise AccessDenied("exact active Canvas revision required")
            if current.revision.specification.canvas_application is None:
                raise AccessDenied("activated Canvas application required")
            scope = CanvasResultScope(
                deployment=current.revision.ref,
                application=current.revision.specification.canvas_application,
            )
            domain._selected(caller.actor, scope, saved.binding_id)
            binding = domain.reviews._binding(
                caller.actor, scope, saved.handle, open_result=False
            )
            source = _one(domain.db, RunOutput, output_id_from_handle(saved.handle))
            if int(source.expires_ms) > _now(domain.db):
                domain.reviews._binding(caller.actor, scope, saved.handle)
            else:
                rows = domain.db.all(
                    InvoiceReview,
                    where="binding_id=?",
                    values=[
                        _key("actions.invoice-review/v1", domain.reviews._json(binding))
                    ],
                )
                if len(rows) != 1 or rows[0].state != "approved":
                    raise AccessDenied("expired result has no admitted reviewed Run")
                proposal = ReviewProposal(review_id=rows[0].id, binding=binding)
                state = domain.read_execution(caller.actor, scope, proposal)
                if state.phase not in {"completed", "running", "blocked", "failed"}:
                    raise AccessDenied("expired result cannot admit new work")
                recovered = {
                    "proposal": proposal.model_dump(mode="json"),
                    "receipt": domain.reviews.status(
                        caller.actor, scope, proposal
                    ).model_dump(mode="json"),
                }
        return replace(
            reply,
            app_scope=scope,
            app_result=saved.handle,
            app_binding=saved.binding_id,
            interaction=saved.model_dump(mode="json", by_alias=True),
            review=recovered,
        )

    @staticmethod
    def _scope(caller: CanvasCaller, proposal: ReviewProposal):
        if (
            caller.audience != "app"
            or caller.scope != proposal.binding.scope
            or caller.result_handle != proposal.binding.handle
        ):
            raise AccessDenied("exact server-bound View result required")

    def _app_call(self, caller: CanvasCaller, name: str, inputs: dict[str, JsonValue]):
        domain = self.execution.execution
        if (
            caller.audience != "app"
            or caller.scope is None
            or caller.result_handle is None
        ):
            raise AccessDenied("result-scoped app session required")
        scope = caller.scope
        with domain.db.connect():
            self.authorization.require(
                caller,
                "read_application",
                application_id=scope.deployment.deployment_id,
            )
            if name == "canvas_dispatch":
                action = ViewAction.model_validate(inputs)
                if action.action == "offer":
                    if (
                        set(inputs) != {"action", "handle"}
                        or action.handle != caller.result_handle
                    ):
                        raise ValueError("exact saved result required")
                    proposal = domain.reviews.offer(caller.actor, scope, action.handle)
                    receipt = domain.reviews.status(caller.actor, scope, proposal)
                else:
                    if action.proposal is None:
                        raise ValueError("exact review proposal required")
                    self._scope(caller, action.proposal)
                    if action.action == "execute":
                        if set(inputs) != {"action", "bindingId", "proposal"}:
                            raise ValueError("explicit binding and proposal required")
                        if action.binding_id != caller.binding_id:
                            raise AccessDenied("View execution binding differs")
                        if self.execution.runner is None:
                            raise ValueError("trusted RCC runner is not configured")
                        from actions.server.foundry.execution_port import (
                            ReviewedDispatch,
                        )

                        return self.execution._invoke(
                            caller.actor,
                            ReviewedDispatch.model_validate(
                                {
                                    "bindingId": action.binding_id,
                                    "proposal": action.proposal,
                                }
                            ),
                        )
                    if (
                        set(inputs) != {"action", "decision", "proposal"}
                        or action.decision is None
                    ):
                        raise ValueError("explicit decision required")
                    proposal = action.proposal
                    with domain._entry(scope):
                        self.authorization.require(
                            caller,
                            "read_application",
                            application_id=scope.deployment.deployment_id,
                        )
                        current = domain.deployments._repository.current(
                            scope.deployment.workspace_id,
                            scope.deployment.deployment_id,
                        )
                        if current is None or current.revision.ref != scope.deployment:
                            raise AccessDenied(
                                "active revision changed; reopen before review"
                            )
                        receipt = domain.reviews.decide(
                            caller.actor, scope, proposal, action.decision
                        )
                return CanvasReply(
                    "Explicit review recorded.",
                    review={
                        "proposal": proposal.model_dump(mode="json"),
                        "receipt": receipt.model_dump(mode="json"),
                    },
                )
            request = (
                ArtifactInput.model_validate(inputs)
                if name == "canvas_artifact"
                else ProposalInput.model_validate(inputs)
            )
            self._scope(caller, request.proposal)
            if name in {"canvas_get_state", "canvas_cancel"}:
                method = (
                    domain.reviews.cancel
                    if name == "canvas_cancel"
                    else domain.reviews.status
                )
                receipt = method(caller.actor, scope, request.proposal)
                return CanvasReply(
                    "Review state loaded.",
                    review={
                        "proposal": request.proposal.model_dump(mode="json"),
                        "receipt": receipt.model_dump(mode="json"),
                    },
                )
            if isinstance(request, ArtifactInput) and request.kind == "source":
                with domain._entry(scope):
                    domain.reviews._current(
                        caller.actor, scope, request.proposal, open_result=False
                    )
                    with domain.reviews.queries.export(
                        caller.actor,
                        caller.workspace_id,
                        caller.result_handle,
                        canvas_scope=scope,
                    ) as source:
                        if source.size > 128 * 1024:
                            raise ValueError("bounded saved result required")
                        raw = source.read(128 * 1024 + 1)
                        if (
                            len(raw) != source.size
                            or source.digest != request.proposal.binding.result_digest
                        ):
                            raise ValueError("saved result seal differs")
                        return CanvasReply(
                            "Exact saved result loaded.",
                            artifact={
                                "runId": request.proposal.binding.run_id,
                                "handle": caller.result_handle,
                                "digest": source.digest,
                                "mediaType": source.media_type,
                                "content": raw.decode("utf-8", errors="strict"),
                            },
                        )
            state = domain.read_execution(caller.actor, scope, request.proposal)
            if name == "canvas_execution_status":
                return CanvasReply(
                    "Execution state loaded.", execution=state.model_dump(mode="json")
                )
            if not isinstance(state, ReviewExecutionComplete):
                raise ValueError("published execution result required")
            with domain.outputs.resolve(
                caller.actor,
                caller.workspace_id,
                state.artifact.handle,
                canvas_scope=scope,
            ) as result:
                if result.size > 128 * 1024:
                    raise ValueError("bounded View artifact required")
                content = result.read(128 * 1024 + 1).decode("utf-8", errors="strict")
                if len(content.encode()) != result.size:
                    raise ValueError("artifact size differs")
                return CanvasReply(
                    "Authorized execution artifact loaded.",
                    artifact={
                        "runId": state.run_id,
                        "handle": state.artifact.handle,
                        "digest": result.digest,
                        "mediaType": result.media_type,
                        "content": content,
                    },
                )
