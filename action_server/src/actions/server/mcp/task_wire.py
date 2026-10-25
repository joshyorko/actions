"""Released current Task extension wire boundary; no execution authority here."""
from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, Literal

from mcp import MCPError
from mcp.shared.inbound import decode_header_value
from mcp.types import InputResponses, RequestParams
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    field_validator,
    model_validator,
)

from actions.server.managed_work_items.contracts import ClaimRef
from actions.server.run_outputs.service import _canonical
from actions.server.run_outputs.types import ExecutionSnapshot, canonical_uuid

TASK_EXTENSION = "io.modelcontextprotocol/tasks"
TASK_PROTOCOL = "2026-07-28"


class DetachedInvocation(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    mode: Literal["detached"]
    snapshot: ExecutionSnapshot
    inputs: dict[str, JsonValue]
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)

    @model_validator(mode="after")
    def bounds(self):
        if len(self.idempotency_key.encode()) > 128:
            raise ValueError("bounded idempotency key required")
        _canonical(self.inputs, 262144)
        return self


class ClaimedDetachedInvocation(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    mode: Literal["detached-claimed"]
    snapshot: ExecutionSnapshot
    claim: ClaimRef


DETACHED_INVOCATION: TypeAdapter[
    DetachedInvocation | ClaimedDetachedInvocation
] = TypeAdapter(DetachedInvocation | ClaimedDetachedInvocation)


class TaskParams(RequestParams):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        populate_by_name=False,
        validate_by_name=False,
        validate_by_alias=True,
    )
    task_id: str = Field(alias="taskId")
    _identity = field_validator("task_id")(canonical_uuid)


class TaskUpdateParams(TaskParams):
    input_responses: InputResponses = Field(alias="inputResponses", max_length=32)

    @model_validator(mode="after")
    def bounds(self):
        _canonical(self.model_dump(mode="json", by_alias=True), 65536)
        return self


def require_current_tasks(ctx: Any, *, task_id: str | None = None) -> None:
    """Gate each request, including extension routing the SDK cannot infer."""
    meta = getattr(ctx, "meta", None)
    if (
        getattr(ctx, "protocol_version", None) != TASK_PROTOCOL
        or not isinstance(meta, Mapping)
        or meta.get("io.modelcontextprotocol/protocolVersion") != TASK_PROTOCOL
    ):
        raise MCPError(-32602, "Task protocol unavailable")
    capabilities = meta.get("io.modelcontextprotocol/clientCapabilities")
    extensions = (
        capabilities.get("extensions") if isinstance(capabilities, Mapping) else None
    )
    if not isinstance(extensions, Mapping) or not isinstance(
        extensions.get(TASK_EXTENSION), Mapping
    ):
        raise MCPError(
            -32021,
            "Task extension capability required",
            {"requiredCapabilities": {"extensions": {TASK_EXTENSION: {}}}},
        )
    request = getattr(ctx, "request", None)
    if request is not None and task_id is not None:
        headers = getattr(request, "headers", None)
        if headers is None:
            raise MCPError(-32602, "Task routing unavailable")
        raw = getattr(headers, "raw", None)
        if raw is not None and sum(name.lower() == b"mcp-name" for name, _ in raw) != 1:
            raise MCPError(-32602, "Task routing unavailable")
        if decode_header_value(headers.get("mcp-name")) != task_id:
            raise MCPError(-32602, "Task routing unavailable")


def _timestamp(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("canonical lifecycle timestamp required")
    try:
        result = datetime.datetime.fromtimestamp(value // 1000, datetime.timezone.utc)
        result += datetime.timedelta(milliseconds=value % 1000)
    except (OverflowError, ValueError, OSError):
        raise ValueError("canonical lifecycle timestamp required") from None
    return result.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def task_result(snapshot: Any, *, creation: bool = False) -> dict[str, Any]:
    """Project a verified service snapshot without poll-derived lifecycle data."""
    canonical_uuid(snapshot.task_id)
    if snapshot.status not in ("working", "completed", "cancelled"):
        raise ValueError("unsupported durable Task state")
    if snapshot.last_updated_ms < snapshot.created_ms:
        raise ValueError("Task lifecycle precedes creation")
    for value in (snapshot.ttl_ms, snapshot.poll_interval_ms):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 < value <= 9007199254740991
        ):
            raise ValueError("bounded Task policy required")
    if (
        not isinstance(snapshot.status_message, str)
        or len(snapshot.status_message.encode()) > 512
    ):
        raise ValueError("bounded Task message required")
    result: dict[str, Any] = {
        "resultType": "task" if creation else "complete",
        "taskId": snapshot.task_id,
        "status": snapshot.status,
        "createdAt": _timestamp(snapshot.created_ms),
        "lastUpdatedAt": _timestamp(snapshot.last_updated_ms),
        "ttlMs": snapshot.ttl_ms,
        "pollIntervalMs": snapshot.poll_interval_ms,
        "statusMessage": snapshot.status_message,
    }
    if not creation and snapshot.status == "completed":
        if not isinstance(snapshot.result, dict):
            raise ValueError("completed Task requires original result")
        result["result"] = {**snapshot.result, "resultType": "complete"}
    elif snapshot.status != "completed" and snapshot.result is not None:
        raise ValueError("nonterminal Task cannot contain a result")
    _canonical(result, 131072)
    return result
