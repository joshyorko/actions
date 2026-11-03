"""Closed, model-facing projection over the managed Work Items domain port.

This module is deliberately not wired into server startup. The host must supply
an authenticated caller resolver and an explicit publication policy; absent
policy is deny-all. Domain grants and publication are checked on every call.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Iterable
from itertools import islice
from typing import Protocol

from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations
from pydantic import JsonValue, TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool

from actions.server.deployments.ids import WorkspaceId

from .contracts import (
    OPERATION_PERMISSION,
    RESULT_MODELS,
    CONTRACT_VERSION,
    Capabilities,
    Enqueue,
    Inspect,
    Intervention,
    ManagedCaller,
    ManagedWorkItemsPort,
    Operation,
    Queues,
)

MAX_REQUEST_BYTES = 512 * 1024
MAX_RESULT_BYTES = 64 * 1024

_TOOL_OPERATIONS = {
    "managed_queues_list": Operation.QUEUES,
    "managed_items_list": Operation.LIST,
    "managed_items_get": Operation.GET,
    "managed_runs_get": Operation.RUN,
    "managed_runs_logs": Operation.LOGS,
    "managed_artifacts_read": Operation.ARTIFACT,
    "managed_items_enqueue": Operation.ENQUEUE,
    "managed_items_cancel": Operation.CANCEL,
}
_READ_ONLY = frozenset(
    name
    for name, operation in _TOOL_OPERATIONS.items()
    if operation not in {Operation.ENQUEUE, Operation.CANCEL}
)
_ARGUMENT_MODELS = {
    Operation.QUEUES: Queues,
    Operation.LIST: Inspect,
    Operation.GET: Inspect,
    Operation.RUN: Inspect,
    Operation.LOGS: Inspect,
    Operation.ARTIFACT: Inspect,
    Operation.ENQUEUE: Enqueue,
    Operation.CANCEL: Intervention,
}
_ARGUMENT_ADAPTERS = {
    operation: TypeAdapter(model) for operation, model in _ARGUMENT_MODELS.items()
}
_JSON = TypeAdapter(dict[str, JsonValue])
_QUEUE_STATES = frozenset({"PENDING", "IN_PROGRESS", "DONE", "FAILED"})


class ModelPublicationPolicy(Protocol):
    """Trusted host policy for explicitly published model-facing operations."""

    def workspaces(self, caller: ManagedCaller) -> Iterable[str]:
        """Return the bounded workspaces in which this caller may discover tools."""

    def allows(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, operation: Operation
    ) -> bool:
        """Return whether the operation is explicitly published to this model."""


Authenticate = Callable[[object], Awaitable[ManagedCaller | None]]


def _safe_projection(value: object) -> object:
    """Keep only schema-validated output references from the artifact DTO."""
    artifact = value["artifact"]
    return {
        "artifact": {
            "handle": artifact["handle"],
            "run_id": artifact["run_id"],
            "digest": artifact["digest"],
            "size": artifact["size"],
        },
        "offset": value["offset"],
        "eof": value["eof"],
        "next_cursor": value.get("next_cursor"),
    }


def _queue_ref(value: dict) -> dict:
    deployment = value["deployment"]
    return {
        "workspace_id": value["workspace_id"],
        "deployment": {
            "workspace_id": deployment["workspace_id"],
            "deployment_id": deployment["deployment_id"],
            "revision_id": deployment["revision_id"],
        },
        "queue_id": value["queue_id"],
    }


def _item_view(value: dict) -> dict:
    fields = (
        "id", "parent_id", "queue_state", "business_state", "delivery_count",
        "available_after_ms", "created_ms", "run_ids", "child_ids", "review_id",
    )
    result = {key: value[key] for key in fields if key in value}
    result["queue"] = _queue_ref(value["queue"])
    return result


def _run_view(value: dict) -> dict:
    artifacts = [
        {
            "handle": artifact["handle"],
            "run_id": artifact["run_id"],
            "digest": artifact["digest"],
            "size": artifact["size"],
        }
        for artifact in value.get("artifacts", [])
    ]
    return {"id": value["id"], "state": value["state"], "artifacts": artifacts}


def _project_result(operation: Operation, result: dict) -> dict:
    """Project each validated result DTO explicitly; never recurse over free text."""
    if operation == Operation.QUEUES:
        return {
            "queues": [
                {
                    "queue": _queue_ref(entry["queue"]),
                    "mode": entry["mode"],
                    "counts": {
                        key: count
                        for key, count in entry["counts"].items()
                        if key in _QUEUE_STATES
                    },
                }
                for entry in result["queues"]
            ],
            "next_cursor": result.get("next_cursor"),
            "server_time_ms": result["server_time_ms"],
        }
    if operation == Operation.LIST:
        return {
            "items": [_item_view(item) for item in result["items"]],
            "next_cursor": result.get("next_cursor"),
            "server_time_ms": result["server_time_ms"],
        }
    if operation in {Operation.GET, Operation.ENQUEUE, Operation.CANCEL}:
        return {
            "item": _item_view(result["item"]),
            "replay": result["replay"],
            "server_time_ms": result["server_time_ms"],
        }
    if operation == Operation.RUN:
        return {
            "run": _run_view(result["run"]),
            "server_time_ms": result["server_time_ms"],
        }
    if operation == Operation.LOGS:
        return {
            "run_id": result["run_id"],
            "lines": [{"offset": line["offset"]} for line in result["lines"]],
            "next_cursor": result.get("next_cursor"),
            "server_time_ms": result["server_time_ms"],
        }
    if operation == Operation.ARTIFACT:
        return _safe_projection(result)
    raise ValueError("operation has no model-safe result projection")


def _schema(operation: Operation) -> dict[str, JsonValue]:
    model = _ARGUMENT_MODELS[operation]
    schema = model.model_json_schema()
    schema["additionalProperties"] = False
    schema["properties"].pop("schema_version", None)
    if operation == Operation.ENQUEUE:
        schema["properties"].pop("review", None)
    if operation == Operation.CANCEL:
        schema["properties"].pop("reconciliation_receipt", None)
    schema["properties"]["operation"] = {"const": operation.value, "type": "string"}
    return schema


class ManagedWorkItemsMcp:
    """MCP facade requiring current grants and explicit publication.

    Synchronous policy/port methods run in a worker thread. The host port owns
    its connection lifecycle and must enter/exit DB contexts inside each call;
    thread-bound connections and cursors must not cross this boundary.
    """

    def __init__(
        self,
        port: ManagedWorkItemsPort | None,
        authenticate: Authenticate | None,
        publication: ModelPublicationPolicy | None = None,
    ):
        self.port = port
        self.authenticate = authenticate
        self.publication = publication

    async def _caller(self, ctx: object) -> ManagedCaller | None:
        if self.authenticate is None:
            return None
        try:
            caller = await self.authenticate(ctx)
            if not isinstance(caller, ManagedCaller) or caller.worker_id is not None:
                return None
            return ManagedCaller.model_validate(caller)
        except Exception:
            return None

    def _normalize_published_workspaces(self, caller: ManagedCaller) -> set[str]:
        if self.publication is None:
            return set()
        try:
            values = self.publication.workspaces(caller)
            result = set()
            for index, value in enumerate(islice(values, 101)):
                if index == 100:
                    return set()
                workspace_id = WorkspaceId.model_validate(value)
                result.add(str(workspace_id.root))
            return result
        except Exception:
            return set()

    async def _published_workspaces(self, caller: ManagedCaller) -> set[str]:
        if self.publication is None:
            return set()
        try:
            return await run_in_threadpool(
                self._normalize_published_workspaces, caller
            )
        except Exception:
            return set()

    async def _allowed(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, operation: Operation
    ) -> bool:
        if self.port is None or self.publication is None:
            return False
        try:
            published = await run_in_threadpool(
                self.publication.allows, caller, workspace_id, operation
            )
            if not published:
                return False
            capabilities = await run_in_threadpool(
                self.port.capabilities, caller, workspace_id
            )
            if not isinstance(capabilities, Capabilities):
                return False
            if capabilities.workspace_id != workspace_id:
                return False
            permission = OPERATION_PERMISSION[operation]
            return (
                operation in capabilities.operations
                and permission in capabilities.permissions
            )
        except Exception:
            return False

    async def tools(self, ctx: object) -> list[Tool]:
        caller = await self._caller(ctx)
        if caller is None:
            return []
        workspaces = await self._published_workspaces(caller)
        visible = set()
        for workspace in workspaces:
            workspace_id = WorkspaceId.model_validate(workspace)
            for operation in _TOOL_OPERATIONS.values():
                if await self._allowed(caller, workspace_id, operation):
                    visible.add(operation)
        return [
            Tool(
                name=name,
                description=f"Managed Work Items operation: {operation.value}.",
                input_schema=_schema(operation),
                annotations=ToolAnnotations(
                    read_only_hint=name in _READ_ONLY,
                    idempotent_hint=name in _READ_ONLY,
                    open_world_hint=False,
                ),
                _meta={"visibility": ["model"]},
            )
            for name, operation in _TOOL_OPERATIONS.items()
            if operation in visible
        ]

    async def call(self, ctx: object, name: str, arguments: object) -> CallToolResult:
        try:
            caller = await self._caller(ctx)
            operation = _TOOL_OPERATIONS.get(name)
            if caller is None or operation is None:
                raise ValueError
            raw = json.dumps(arguments, ensure_ascii=False, allow_nan=False).encode()
            if len(raw) > MAX_REQUEST_BYTES:
                raise ValueError
            parsed = _JSON.validate_json(raw, strict=True)
            if parsed.get("operation") != operation.value:
                raise ValueError
            if "schema_version" in parsed and (
                parsed.pop("schema_version") != CONTRACT_VERSION
            ):
                raise ValueError
            if operation == Operation.ENQUEUE and "review" in parsed:
                raise ValueError
            if (
                operation == Operation.CANCEL
                and "reconciliation_receipt" in parsed
            ):
                raise ValueError
            command_raw = json.dumps(
                parsed, ensure_ascii=False, allow_nan=False
            ).encode()
            # Validate through the JSON path so strict UUID root models accept
            # canonical UUID strings from the MCP wire representation.
            command = _ARGUMENT_ADAPTERS[operation].validate_json(
                command_raw, strict=True
            )
            workspace = (
                command.workspace_id
                if operation == Operation.QUEUES
                else command.queue.workspace_id
            )
            if str(workspace.root) not in await self._published_workspaces(caller):
                raise ValueError
            if not await self._allowed(caller, workspace, operation):
                raise ValueError
            result = await run_in_threadpool(self.port.call, caller, command)
            if hasattr(result, "__await__") or not isinstance(result, dict):
                raise ValueError
            result_raw = json.dumps(
                result, ensure_ascii=False, allow_nan=False
            ).encode()
            if len(result_raw) > MAX_REQUEST_BYTES:
                raise ValueError
            result = (
                RESULT_MODELS[operation]
                .model_validate_json(result_raw)
                .model_dump(mode="json")
            )
            projected = _project_result(operation, result)
            encoded = json.dumps(projected, ensure_ascii=False, allow_nan=False).encode()
            if len(encoded) > MAX_RESULT_BYTES:
                raise ValueError
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", text=f"Managed operation {operation.value} completed."
                    )
                ],
                structured_content=_JSON.validate_python(projected),
            )
        except Exception:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="Managed Work Items request unavailable, invalid or denied.",
                    )
                ],
                is_error=True,
            )
