"""Closed, model-facing projection over the managed Work Items domain port.

This module is deliberately not wired into server startup. The host must supply
an authenticated caller resolver, an explicit publication policy, and the
atomic guard required for queue-targeted operations; absent authority is deny-all.
Domain grants and publication are checked on every call.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Awaitable, Callable, Iterable
from itertools import islice
from typing import Literal, Protocol, cast

from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter
from starlette.concurrency import run_in_threadpool

from actions.server.deployments.foundry_values import ModelPublishedWorkItemOperation
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
    Permission,
    QueuePage,
    QueueRef,
    QueueView,
    Queues,
)
from .model_publication import ModelWorkItemPublicationGuard

MAX_REQUEST_BYTES = 512 * 1024
MAX_RESULT_BYTES = 64 * 1024
MAX_PUBLISHED_WORKSPACES = 100
MAX_PUBLISHED_QUEUES = 100
MAX_QUEUE_SCAN_ROWS = 2048
MAX_QUEUE_SCAN_PAGES = MAX_QUEUE_SCAN_ROWS // 100 + 1
MAX_QUEUE_SCAN_BYTES = 512 * 1024
MAX_QUEUE_CURSOR_BYTES = 512
MAX_QUEUE_PAGE_SIZE = 100

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

    def queues(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, operation: Operation
    ) -> Iterable[QueueRef]:
        """Return the bounded exact Queues published for this operation."""


class _PublishedQueueCursor(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    version: Literal[1]
    workspace_id: str = Field(alias="workspaceId", min_length=36, max_length=36)
    deployment_id: str | None = Field(
        alias="deploymentId", default=None, min_length=36, max_length=36
    )
    offset: int = Field(ge=0, le=MAX_PUBLISHED_QUEUES)
    visible_digest: str = Field(
        alias="visibleDigest", pattern=r"^sha256:[0-9a-f]{64}$"
    )


def _queue_key(queue: QueueRef) -> str:
    return json.dumps(
        queue.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _visible_queue_digest(queues: Iterable[QueueRef]) -> str:
    digest = hashlib.sha256(b"actions.managed-work-items-visible-queues/v1\x00")
    for queue in sorted(queues, key=_queue_key):
        digest.update(_queue_key(queue).encode("utf-8"))
        digest.update(b"\x00")
    return "sha256:" + digest.hexdigest()


def _encode_queue_cursor(
    workspace_id: WorkspaceId,
    deployment_id: str | None,
    offset: int,
    visible_digest: str,
) -> str:
    payload = _PublishedQueueCursor(
        version=1,
        workspaceId=str(workspace_id.root),
        deploymentId=deployment_id,
        offset=offset,
        visibleDigest=visible_digest,
    ).model_dump(mode="json", by_alias=True)
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    if len(encoded) > MAX_QUEUE_CURSOR_BYTES:
        raise ValueError("published Queue cursor exceeds its bound")
    return encoded


def _decode_queue_cursor(
    value: str,
    workspace_id: WorkspaceId,
    deployment_id: str | None,
) -> _PublishedQueueCursor:
    if not isinstance(value, str) or not value or len(value) > MAX_QUEUE_CURSOR_BYTES:
        raise ValueError("invalid published Queue cursor")
    try:
        raw = base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        )
        cursor = _PublishedQueueCursor.model_validate_json(raw)
    except (ValueError, TypeError):
        raise ValueError("invalid published Queue cursor") from None
    if (
        cursor.workspace_id != str(workspace_id.root)
        or cursor.deployment_id != deployment_id
    ):
        raise ValueError("published Queue cursor scope changed")
    return cursor


def _normalize_published_queues(
    values: Iterable[QueueRef], workspace_id: WorkspaceId
) -> dict[str, QueueRef] | None:
    """Validate a finite, exact publication set; ``None`` means deny."""
    try:
        result: dict[str, QueueRef] = {}
        for index, value in enumerate(islice(values, MAX_PUBLISHED_QUEUES + 1)):
            if index == MAX_PUBLISHED_QUEUES or not isinstance(value, QueueRef):
                return None
            queue = QueueRef.model_validate(value)
            if queue.workspace_id != workspace_id:
                return None
            result[_queue_key(queue)] = queue
        return result
    except Exception:
        return None


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
        publication_guard: ModelWorkItemPublicationGuard | None = None,
    ):
        self.port = port
        self.authenticate = authenticate
        self.publication = publication
        self.publication_guard = publication_guard

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

    async def _published_queues(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, operation: Operation
    ) -> dict[str, QueueRef] | None:
        if self.publication is None:
            return None
        try:
            return await run_in_threadpool(
                self._load_published_queues, caller, workspace_id, operation
            )
        except Exception:
            return None

    def _load_published_queues(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, operation: Operation
    ) -> dict[str, QueueRef] | None:
        """Invoke and fully consume the trusted scope iterator off-loop."""
        if self.publication is None:
            return None
        try:
            values = self.publication.queues(caller, workspace_id, operation)
            return _normalize_published_queues(values, workspace_id)
        except Exception:
            return None

    async def _allowed(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, operation: Operation
    ) -> bool:
        if self.port is None or self.publication is None:
            return False
        if self.publication_guard is None:
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
                queues = await self._published_queues(
                    caller, workspace_id, operation
                )
                if queues and await self._allowed(caller, workspace_id, operation):
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
            queues = await self._published_queues(caller, workspace, operation)
            if queues is None or not queues:
                raise ValueError
            if not await self._allowed(caller, workspace, operation):
                raise ValueError
            if operation == Operation.QUEUES:
                if command.deployment_id is not None and not any(
                    queue.deployment.deployment_id == command.deployment_id
                    for queue in queues.values()
                ):
                    raise ValueError
                result, next_cursor = await run_in_threadpool(
                    self._list_visible_queues, caller, command, queues
                )
            else:
                if _queue_key(command.queue) not in queues:
                    raise ValueError
                if self.publication_guard is None:
                    raise ValueError
                result = await run_in_threadpool(
                    self._guarded_domain_call, caller, command, operation
                )
                next_cursor = None
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
            if operation == Operation.QUEUES:
                result["next_cursor"] = next_cursor
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

    def _guarded_domain_call(
        self,
        caller: ManagedCaller,
        command: Inspect | Enqueue | Intervention,
        operation: Operation,
    ) -> dict[str, JsonValue]:
        """Keep the guard and synchronous domain port on one DB worker thread."""
        if self.port is None or self.publication_guard is None:
            raise ValueError("atomic model queue guard unavailable")

        def domain_call(identity, queue, selected_operation):
            if (
                identity != caller
                or queue != command.queue
                or selected_operation != operation.value
            ):
                raise ValueError("guarded model queue target changed")
            return self.port.call(identity, command)

        return self.publication_guard.call(
            caller,
            command.queue,
            cast(ModelPublishedWorkItemOperation, operation.value),
            domain_call,
        )

    def _list_visible_queues(
        self,
        caller: ManagedCaller,
        command: Queues,
        published: dict[str, QueueRef],
    ) -> tuple[dict, str | None]:
        """Scan and filter under the atomic guard, then page the visible set.

        Backend cursors stay inside the facade and are never returned. A client
        cursor binds only the identities the caller can currently see.
        """
        if self.port is None or self.publication_guard is None:
            raise ValueError("atomic model queue-list guard unavailable")

        if command.cursor is None:
            offset = 0
        else:
            cursor = _decode_queue_cursor(
                command.cursor, command.workspace_id, (
                    str(command.deployment_id.root)
                    if command.deployment_id is not None
                    else None
                )
            )
            offset = cursor.offset

        def scan_pages(identity: ManagedCaller) -> tuple[list[QueueView], str]:
            rows: list[QueueView] = []
            backend_cursor: str | None = None
            seen_cursors: set[str] = set()
            scanned = 0
            scan_bytes = 0
            pages = 0
            server_time_ms = "0"
            while True:
                if pages >= MAX_QUEUE_SCAN_PAGES:
                    raise ValueError("queue scan page bound exceeded")
                request = command.model_copy(
                    update={"cursor": backend_cursor, "limit": MAX_QUEUE_PAGE_SIZE}
                )
                raw_page = self.port.call(identity, request)
                if hasattr(raw_page, "__await__") or not isinstance(raw_page, dict):
                    raise ValueError("invalid backend queue page")
                page_raw = json.dumps(
                    raw_page, ensure_ascii=False, allow_nan=False
                ).encode()
                scan_bytes += len(page_raw)
                if (
                    len(page_raw) > MAX_REQUEST_BYTES
                    or scan_bytes > MAX_QUEUE_SCAN_BYTES
                ):
                    raise ValueError("backend queue scan exceeds its bound")
                page = QueuePage.model_validate_json(page_raw)
                pages += 1
                scanned += len(page.queues)
                if scanned > MAX_QUEUE_SCAN_ROWS:
                    raise ValueError("queue scan row bound exceeded")
                rows.extend(page.queues)
                server_time_ms = page.server_time_ms
                next_backend_cursor = page.next_cursor
                if next_backend_cursor is None:
                    break
                if (
                    not isinstance(next_backend_cursor, str)
                    or not next_backend_cursor
                    or len(next_backend_cursor) > 4096
                    or next_backend_cursor in seen_cursors
                    or scanned >= MAX_QUEUE_SCAN_ROWS
                ):
                    raise ValueError("backend queue pagination is not bounded")
                seen_cursors.add(next_backend_cursor)
                backend_cursor = next_backend_cursor
            return rows, server_time_ms

        visible_rows, server_time_ms = self.publication_guard.list_queues(
            caller,
            command.workspace_id,
            scan_pages,
            deployment_id=command.deployment_id,
        )
        visible: dict[str, dict] = {}
        for row in visible_rows:
            key = _queue_key(row.queue)
            if key in published and Permission.READ in row.permissions:
                visible[key] = row.model_dump(mode="json")

        ordered_keys = sorted(visible)
        visible_queues = [published[key] for key in ordered_keys]
        digest = _visible_queue_digest(visible_queues)
        if command.cursor is not None:
            cursor = _decode_queue_cursor(
                command.cursor, command.workspace_id, (
                    str(command.deployment_id.root)
                    if command.deployment_id is not None
                    else None
                )
            )
            if cursor.visible_digest != digest:
                raise ValueError("visible Queue set changed")
        if offset > len(ordered_keys):
            raise ValueError("visible Queue cursor is outside the current set")
        selected = ordered_keys[offset : offset + command.limit]
        end = offset + len(selected)
        next_cursor = (
            _encode_queue_cursor(
                command.workspace_id,
                (
                    str(command.deployment_id.root)
                    if command.deployment_id is not None
                    else None
                ),
                end,
                digest,
            )
            if end < len(ordered_keys)
            else None
        )
        return (
            {
                "queues": [visible[key] for key in selected],
                "next_cursor": None,
                "server_time_ms": server_time_ms,
            },
            next_cursor,
        )
