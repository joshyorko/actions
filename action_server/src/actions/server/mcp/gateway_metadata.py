"""Trusted request metadata for the stateless MCP HTTP gateway."""

from __future__ import annotations

import contextvars
import json
import uuid
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MCP_METHOD_HEADER = "mcp-method"
MCP_NAME_HEADER = "mcp-name"
MCP_CORRELATION_ID_HEADER = "x-request-id"
MCP_REQUEST_STATE_KEY = "actions.mcp.request_metadata"
MCP_REQUEST_CONTEXT: contextvars.ContextVar[
    "McpRequestMetadata | None"
] = contextvars.ContextVar("actions_mcp_request_metadata", default=None)

MCP_METHOD_ATTRIBUTE = "actions.mcp.method"
MCP_NAME_ATTRIBUTE = "actions.mcp.name"
MCP_CORRELATION_ID_ATTRIBUTE = "actions.correlation_id"
_MAX_NAME_LENGTH = 256
_MAX_BODY_LENGTH = 1024 * 1024
_MCP_METHODS = frozenset(
    {
        "initialize",
        "notifications/initialized",
        "notifications/cancelled",
        "notifications/progress",
        "notifications/message",
        "notifications/roots/list_changed",
        "notifications/tools/list_changed",
        "notifications/resources/list_changed",
        "notifications/resources/updated",
        "ping",
        "tools/list",
        "tools/call",
        "resources/list",
        "resources/read",
        "resources/templates/list",
        "resources/subscribe",
        "resources/unsubscribe",
        "prompts/list",
        "prompts/get",
        "completion/complete",
        "logging/setLevel",
        "roots/list",
        "sampling/createMessage",
        "elicitation/create",
        "tasks/get",
        "tasks/result",
        "tasks/cancel",
    }
)


@dataclass(frozen=True)
class McpRequestMetadata:
    method: str
    name: str | None
    correlation_id: str

    @property
    def telemetry_attributes(self) -> dict[str, str]:
        attributes = {
            MCP_METHOD_ATTRIBUTE: self.method,
            MCP_CORRELATION_ID_ATTRIBUTE: self.correlation_id,
        }
        if self.name is not None:
            attributes[MCP_NAME_ATTRIBUTE] = self.name
        return attributes


def get_mcp_request_metadata() -> McpRequestMetadata | None:
    """Return trusted metadata for the current request, if one is active."""
    return MCP_REQUEST_CONTEXT.get()


def _header(scope: Scope, name: str) -> str | None:
    target = name.encode("ascii")
    values = []
    for key, value in scope.get("headers", []):
        if key.lower() == target:
            values.append(value.decode("latin-1"))
    if len(values) > 1:
        raise ValueError(f"duplicate {name} header")
    if values and values[0] != values[0].strip():
        raise ValueError(f"whitespace in {name} header")
    return values[0] if values else None


def _request_identity(payload: Any) -> tuple[str, str | None] | None:
    entries = payload if isinstance(payload, list) else [payload]
    if not entries or not all(
        isinstance(entry, dict) and entry.get("jsonrpc") == "2.0" for entry in entries
    ):
        return None

    methods = [entry.get("method") for entry in entries]
    if not methods or not all(
        isinstance(method, str)
        and len(method) <= _MAX_NAME_LENGTH
        and method in _MCP_METHODS
        for method in methods
    ):
        return None
    method = methods[0] if len(set(methods)) == 1 else "batch"

    names: set[str] = set()
    for entry in entries:
        entry_method = entry["method"]
        params = entry.get("params")
        if not isinstance(params, dict):
            continue
        if entry_method in {"tools/call", "prompts/get"}:
            name = params.get("name")
        elif entry_method in {
            "resources/read",
            "resources/subscribe",
            "resources/unsubscribe",
        }:
            name = params.get("uri")
        else:
            name = None
        if name is not None:
            if not isinstance(name, str) or not name or len(name) > _MAX_NAME_LENGTH:
                return None
            names.add(name)
    return method, next(iter(names)) if len(names) == 1 else None


def _correlation_id(value: str | None) -> str:
    if value is not None:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError):
            pass
        else:
            if str(parsed) == value:
                return value
    return str(uuid.uuid4())


async def _reject(send: Send, status: int = 400) -> None:
    await send({"type": "http.response.start", "status": status, "headers": []})
    await send({"type": "http.response.body", "body": b"Invalid MCP request metadata"})


class McpRequestMetadataMiddleware:
    """Validate MCP identity headers once and expose trusted request state."""

    def __init__(
        self,
        app: ASGIApp,
        metadata_observer: Callable[[McpRequestMetadata], Any] | None = None,
    ):
        self.app = app
        self.metadata_observer = metadata_observer

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or scope.get("path") != "/mcp":
            await self.app(scope, receive, send)
            return

        messages: list[Message] = []
        body = bytearray()
        while True:
            message = await receive()
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > _MAX_BODY_LENGTH:
                await _reject(send, 413)
                return
            messages.append(message)
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        try:
            method_header = _header(scope, MCP_METHOD_HEADER)
            name_header = _header(scope, MCP_NAME_HEADER)
            correlation_header = _header(scope, MCP_CORRELATION_ID_HEADER)
        except ValueError:
            await _reject(send)
            return

        try:
            identity = _request_identity(json.loads(body))
        except (json.JSONDecodeError, UnicodeDecodeError):
            identity = None

        if identity is None:
            if (
                method_header is not None
                or name_header is not None
                or correlation_header is not None
            ):
                await _reject(send)
                return
        else:
            method, name = identity
            if method_header is not None and method_header != method:
                await _reject(send)
                return
            if name_header is not None and name_header != name:
                await _reject(send)
                return

        metadata = None
        if identity is not None:
            metadata = McpRequestMetadata(
                identity[0], identity[1], _correlation_id(correlation_header)
            )
            scope.setdefault("state", {})[MCP_REQUEST_STATE_KEY] = metadata
            if self.metadata_observer is not None:
                self.metadata_observer(metadata)

        async def replay() -> Message:
            return (
                messages.pop(0)
                if messages
                else {"type": "http.request", "body": b"", "more_body": False}
            )

        async def response(message: Message) -> None:
            if metadata is not None and message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append(
                    (
                        MCP_CORRELATION_ID_HEADER.encode(),
                        metadata.correlation_id.encode(),
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        token = MCP_REQUEST_CONTEXT.set(metadata)
        try:
            await self.app(scope, replay, response)
        finally:
            MCP_REQUEST_CONTEXT.reset(token)
