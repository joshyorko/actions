"""Trusted request metadata for the stateless MCP HTTP gateway."""

from __future__ import annotations

import contextvars
import inspect
import json
import logging
import math
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MCP_METHOD_HEADER = "mcp-method"
MCP_NAME_HEADER = "mcp-name"
MCP_CORRELATION_ID_HEADER = "x-request-id"
MCP_REQUEST_STATE_KEY = "actions.mcp.request_metadata"
MCP_REQUEST_CONTEXT: contextvars.ContextVar[
    "McpRequestMetadata | None"
] = contextvars.ContextVar("actions_mcp_request_metadata", default=None)

MCP_METHOD_ATTRIBUTE = "actions.mcp.method"
MCP_METHOD_CLASS_ATTRIBUTE = "actions.mcp.method_class"
MCP_NAME_ATTRIBUTE = "actions.mcp.name"
MCP_CORRELATION_ID_ATTRIBUTE = "actions.correlation_id"
MCP_STATUS_ATTRIBUTE = "actions.mcp.status_code"
MCP_LATENCY_ATTRIBUTE = "actions.mcp.latency_ms"
_MAX_NAME_LENGTH = 256
_MAX_BODY_LENGTH = 1024 * 1024
_MAX_HEADER_VALUE_LENGTH = 256
_MAX_OBSERVATION_NAME_LENGTH = 128
_MAX_LATENCY_MS = 24 * 60 * 60 * 1000
_LOGGER = logging.getLogger(__name__)
_REDACTED_IDENTIFIER = "<redacted>"
_SAFE_RESOURCE_SCHEMES = frozenset({"http", "https", "resource"})
_RESOURCE_METHODS = frozenset(
    {"resources/read", "resources/subscribe", "resources/unsubscribe"}
)
_NAMED_METHODS = frozenset({"tools/call", "prompts/get"})
_METHOD_CLASSES = frozenset(
    {
        "batch",
        "completion",
        "elicitation",
        "extension",
        "initialize",
        "logging",
        "notification",
        "ping",
        "prompts",
        "resources",
        "roots",
        "sampling",
        "server",
        "subscriptions",
        "tasks",
        "tools",
    }
)


@dataclass(frozen=True)
class McpRequestMetadata:
    method: str
    name: str | None
    correlation_id: str
    name_is_resource: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", _sanitize_method(self.method))
        if self.name is not None:
            sanitizer = (
                _sanitize_resource_identifier
                if self.name_is_resource
                else _sanitize_identifier
            )
            object.__setattr__(self, "name", sanitizer(self.name))

    @property
    def method_classification(self) -> str:
        if self.method == "batch":
            return "batch"
        if self.method == "initialize":
            return "initialize"
        if self.method == "ping":
            return "ping"
        if self.method.startswith("notifications/"):
            return "notification"
        prefix = self.method.partition("/")[0]
        return prefix if prefix in _METHOD_CLASSES else "extension"

    @property
    def telemetry_attributes(self) -> dict[str, str]:
        attributes = {
            MCP_METHOD_ATTRIBUTE: self.method,
            MCP_CORRELATION_ID_ATTRIBUTE: self.correlation_id,
        }
        if self.name is not None:
            attributes[MCP_NAME_ATTRIBUTE] = self.name
        return attributes


@dataclass(frozen=True)
class McpRequestObservation:
    metadata: McpRequestMetadata
    status_code: int
    latency_ms: float

    @property
    def telemetry_attributes(self) -> dict[str, Any]:
        return {
            **self.metadata.telemetry_attributes,
            MCP_METHOD_CLASS_ATTRIBUTE: self.metadata.method_classification,
            MCP_STATUS_ATTRIBUTE: self.status_code,
            MCP_LATENCY_ATTRIBUTE: self.latency_ms,
        }


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
    if values and len(values[0]) > _MAX_HEADER_VALUE_LENGTH:
        raise ValueError(f"{name} header is too long")
    return values[0] if values else None


def _valid_method(method: Any) -> bool:
    if not isinstance(method, str) or not method:
        return False
    try:
        method_bytes = method.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return len(method_bytes) <= _MAX_NAME_LENGTH


def _valid_jsonrpc_id(value: Any) -> bool:
    if value is _LARGE_NUMBER:
        return True
    if value is None or isinstance(value, (str, int)) and not isinstance(value, bool):
        return True
    return isinstance(value, float) and math.isfinite(value)


def _is_response(entry: Any) -> bool:
    if not isinstance(entry, dict) or entry.get("jsonrpc") != "2.0":
        return False
    if "method" in entry or "id" not in entry or not _valid_jsonrpc_id(entry["id"]):
        return False
    return ("result" in entry) != ("error" in entry)


def _is_request(entry: Any) -> bool:
    if not isinstance(entry, dict) or entry.get("jsonrpc") != "2.0":
        return False
    if "method" not in entry or not _valid_method(entry["method"]):
        return False
    if "result" in entry or "error" in entry:
        return False
    return "id" not in entry or _valid_jsonrpc_id(entry["id"])


def _request_name(entry: dict[str, Any]) -> Any:
    params = entry.get("params")
    if not isinstance(params, dict):
        return None
    method = entry["method"]
    if method in _NAMED_METHODS:
        key = "name"
    elif method in _RESOURCE_METHODS:
        key = "uri"
    elif "name" in params:
        key = "name"
    elif "uri" in params:
        key = "uri"
    else:
        return None
    name = params.get(key)
    if name is None:
        return None
    if (
        not isinstance(name, str)
        or not name
        or len(name.encode("utf-8")) > _MAX_NAME_LENGTH
    ):
        return _INVALID_NAME
    return name, key == "uri"


_INVALID_NAME = object()


@dataclass(frozen=True)
class _PayloadInspection:
    identity: tuple[str, str | None, bool] | None
    response_only: bool
    is_batch: bool


def _inspect_payload(payload: Any) -> _PayloadInspection:
    entries = payload if isinstance(payload, list) else [payload]
    if not entries:
        return _PayloadInspection(None, False, False)

    requests: list[dict[str, Any]] = []
    for entry in entries:
        if _is_response(entry):
            continue
        if not _is_request(entry):
            return _PayloadInspection(None, False, isinstance(payload, list))
        requests.append(entry)

    if not requests:
        return _PayloadInspection(None, True, isinstance(payload, list))

    first_method = requests[0]["method"]
    method = (
        first_method
        if all(entry["method"] == first_method for entry in requests)
        else "batch"
    )
    first_name: str | None = None
    first_name_is_resource = False
    multiple_names = False
    for entry in requests:
        name = _request_name(entry)
        if name is _INVALID_NAME:
            return _PayloadInspection(None, False, isinstance(payload, list))
        if name is None:
            continue
        name, name_is_resource = name
        if first_name is None:
            first_name = name
            first_name_is_resource = name_is_resource
        elif name != first_name:
            multiple_names = True
    return _PayloadInspection(
        (
            method,
            None if multiple_names else first_name,
            first_name_is_resource and not multiple_names,
        ),
        False,
        isinstance(payload, list),
    )


def _sanitize_identifier(value: str) -> str:
    value = "".join(
        character if ord(character) >= 0x20 and ord(character) != 0x7F else "_"
        for character in value
    )
    return value[:_MAX_OBSERVATION_NAME_LENGTH]


def _sanitize_resource_identifier(value: str) -> str:
    try:
        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        if (
            scheme not in _SAFE_RESOURCE_SCHEMES
            or not parsed.netloc
            or any(
                ord(character) < 0x20 or ord(character) == 0x7F for character in value
            )
            or "%" in value
            or parsed.query
            or parsed.fragment
        ):
            return _REDACTED_IDENTIFIER
        if parsed.username is not None or parsed.password is not None:
            return _REDACTED_IDENTIFIER
        host = parsed.hostname or ""
        if not host or any(
            character
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_~"
            for character in host
        ):
            return _REDACTED_IDENTIFIER
        parsed.port
    except ValueError:
        return _REDACTED_IDENTIFIER
    return scheme


def _sanitize_method(value: str) -> str:
    return "".join(
        character if ord(character) >= 0x20 and ord(character) != 0x7F else "_"
        for character in value
    )[:_MAX_NAME_LENGTH]


_LARGE_NUMBER = object()


def _parse_int(value: str) -> int | object:
    if len(value) > 64:
        return _LARGE_NUMBER
    try:
        return int(value)
    except (ValueError, OverflowError):
        return _LARGE_NUMBER


def _parse_float(value: str) -> float | object:
    try:
        parsed = float(value)
    except (ValueError, OverflowError):
        return _LARGE_NUMBER
    return parsed if math.isfinite(parsed) else _LARGE_NUMBER


def _parse_constant(_value: str) -> object:
    return _LARGE_NUMBER


def _correlation_id(value: str | None) -> str:
    if value is not None:
        try:
            parsed = uuid.UUID(value)
        except (ValueError, AttributeError, TypeError, OverflowError):
            pass
        else:
            if str(parsed) == value:
                return value
    return str(uuid.uuid4())


async def _reject(send: Send, status: int = 400) -> None:
    await send({"type": "http.response.start", "status": status, "headers": []})
    await send({"type": "http.response.body", "body": b"Invalid MCP request metadata"})


async def _notify_observer(
    observer: Callable[[Any], Any], value: Any, observer_name: str
) -> None:
    try:
        result = observer(value)
        if inspect.isawaitable(result):
            await result
    except Exception as exc:
        diagnostic = type(exc).__name__[:64] or "Exception"
        try:
            _LOGGER.warning("MCP %s observer failed (%s)", observer_name, diagnostic)
        except Exception:
            pass


class McpRequestMetadataMiddleware:
    """Validate MCP identity headers once and expose trusted request state."""

    def __init__(
        self,
        app: ASGIApp,
        metadata_observer: Callable[[McpRequestMetadata], Any] | None = None,
        request_observer: Callable[[McpRequestObservation], Any] | None = None,
    ):
        self.app = app
        self.metadata_observer = metadata_observer
        self.request_observer = request_observer

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or scope.get("path") != "/mcp":
            await self.app(scope, receive, send)
            return

        try:
            declared_length = _header(scope, "content-length")
        except ValueError:
            await _reject(send)
            return
        if declared_length is not None:
            try:
                if int(declared_length) > _MAX_BODY_LENGTH:
                    await _reject(send, 413)
                    return
            except (TypeError, ValueError, OverflowError):
                pass

        messages: list[Message] = []
        body = bytearray()
        while True:
            message = await receive()
            chunk = message.get("body", b"")
            if not isinstance(chunk, (bytes, bytearray)):
                await _reject(send)
                return
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
            inspection = _inspect_payload(
                json.loads(
                    body,
                    parse_int=_parse_int,
                    parse_float=_parse_float,
                    parse_constant=_parse_constant,
                )
            )
        except Exception:
            inspection = _PayloadInspection(None, False, False)

        identity = inspection.identity

        if identity is None:
            if (
                method_header is not None
                or name_header is not None
                or correlation_header is not None
            ) and not inspection.response_only:
                await _reject(send)
                return
        else:
            method, raw_name, _name_is_resource = identity
            if (
                method_header is not None
                and method_header != method
                and not (inspection.is_batch and method_header == "batch")
            ):
                await _reject(send)
                return
            if name_header is not None and name_header != raw_name:
                await _reject(send)
                return

        metadata = None
        if identity is not None:
            metadata = McpRequestMetadata(
                identity[0],
                identity[1],
                _correlation_id(correlation_header),
                identity[2],
            )
            scope.setdefault("state", {})[MCP_REQUEST_STATE_KEY] = metadata

        async def replay() -> Message:
            return (
                messages.pop(0)
                if messages
                else {"type": "http.request", "body": b"", "more_body": False}
            )

        response_status: int | None = None

        async def response(message: Message) -> None:
            nonlocal response_status
            if metadata is not None and message["type"] == "http.response.start":
                status = message.get("status")
                if isinstance(status, int):
                    response_status = status
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != MCP_CORRELATION_ID_HEADER.encode()
                ]
                headers.append(
                    (
                        MCP_CORRELATION_ID_HEADER.encode(),
                        metadata.correlation_id.encode(),
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        token = MCP_REQUEST_CONTEXT.set(metadata)
        started = time.perf_counter()
        try:
            if metadata is not None and self.metadata_observer is not None:
                await _notify_observer(self.metadata_observer, metadata, "metadata")
            await self.app(scope, replay, response)
        finally:
            if metadata is not None and self.request_observer is not None:
                elapsed_ms = min(
                    _MAX_LATENCY_MS,
                    max(0.0, round((time.perf_counter() - started) * 1000, 3)),
                )
                await _notify_observer(
                    self.request_observer,
                    McpRequestObservation(metadata, response_status or 500, elapsed_ms),
                    "request",
                )
            MCP_REQUEST_CONTEXT.reset(token)
