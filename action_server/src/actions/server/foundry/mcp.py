"""Stable native Canvas MCP projection over a trusted, separately tested port.

This adapter creates no database, compiler, queue, actor grant or default trust.
It is enabled only when the host supplies both the domain port and authenticator.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from mcp.types import CallToolResult, Resource, TextContent, Tool, ToolAnnotations
from pydantic import JsonValue, TypeAdapter

from actions.server.deployments.canonical import canonicalize_json
from actions.server.run_outputs.types import Actor, canonical_uuid

URI = "ui://action-canvas/v1/canvas.html"
MODEL_TOOLS = frozenset(
    {
        "canvas_create",
        "canvas_get",
        "canvas_apply",
        "canvas_preview",
        "canvas_inspect",
        "canvas_release",
        "canvas_open",
    }
)
APP_TOOLS = frozenset(
    {
        "canvas_dispatch",
        "canvas_get_manifest",
        "canvas_get_state",
        "canvas_execution_status",
        "canvas_cancel",
        "canvas_artifact",
    }
)
RESERVED_TOOLS = MODEL_TOOLS | APP_TOOLS | {"canvas_query", "canvas_page"}
_READ_ONLY = frozenset(
    {
        "canvas_open",
        "canvas_get",
        "canvas_preview",
        "canvas_inspect",
        "canvas_get_manifest",
        "canvas_get_state",
        "canvas_execution_status",
        "canvas_artifact",
    }
)
_JSON = TypeAdapter(dict[str, JsonValue])
_EMPTY = {"type": "object", "properties": {}, "additionalProperties": False}


def _object(value: object, limit: int) -> dict[str, JsonValue]:
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
    if len(encoded) > limit:
        raise ValueError("bounded Canvas object required")
    return _JSON.validate_json(canonicalize_json(encoded), strict=True)


def _tool_description(name: str, schema: dict[str, JsonValue]) -> str:
    if name == "canvas_open":
        return "Open the app library without changing state."
    description = schema.get("description")
    return (
        description
        if isinstance(description, str) and description
        else "Authorized native Canvas operation."
    )


@dataclass(frozen=True)
class CanvasCaller:
    """Server-authenticated scope, never constructed from tool arguments."""

    actor: Actor
    workspace_id: str
    audience: Literal["model", "app"]

    def __post_init__(self):
        object.__setattr__(self, "actor", Actor.model_validate(self.actor))
        canonical_uuid(self.workspace_id)
        if self.audience not in ("model", "app"):
            raise ValueError("known Canvas audience required")


@dataclass(frozen=True)
class CanvasReply:
    """Separate intentional model authoring data from authorized private UI data."""

    summary: str
    model_result: dict[str, JsonValue] | None = None
    view_state: dict[str, JsonValue] | None = None


class CanvasPort(Protocol):
    schemas: Mapping[str, dict[str, JsonValue]]

    async def call(
        self, caller: CanvasCaller, name: str, arguments: dict[str, JsonValue]
    ) -> CanvasReply:
        ...


class CanvasMcp:
    def __init__(
        self,
        port: CanvasPort,
        authenticate: Callable[[object], Awaitable[CanvasCaller | None]],
        html: str,
    ):
        schemas = {name: _object(value, 65536) for name, value in port.schemas.items()}
        if set(schemas) - (MODEL_TOOLS | APP_TOOLS):
            raise ValueError("unknown Canvas operation")
        if not MODEL_TOOLS <= set(schemas):
            raise ValueError("complete model-visible Canvas facade required")
        if any(schema.get("type") != "object" for schema in schemas.values()):
            raise ValueError("Canvas tool object schema required")
        if (
            not isinstance(html, str)
            or not html
            or len(html.encode()) > 4 * 1024 * 1024
        ):
            raise ValueError("bounded static Canvas renderer required")
        schemas["canvas_open"] = _object(_EMPTY, 1024)
        self._schemas = schemas
        self.port, self.authenticate, self.html = port, authenticate, html
        self.uri = URI
        self.resource = Resource(
            uri=URI,
            name="Canvas",
            mime_type="text/html;profile=mcp-app",
            _meta={
                "ui": {"csp": {"connectDomains": [], "resourceDomains": []}},
                "actions.canvas.rendererSha256": hashlib.sha256(
                    html.encode()
                ).hexdigest(),
            },
        )
        identity = {
            "schemas": schemas,
            "uri": URI,
            "renderer": hashlib.sha256(html.encode()).hexdigest(),
        }
        self.catalog_identity = hashlib.sha256(
            canonicalize_json(json.dumps(identity).encode())
        ).hexdigest()

    async def principal(self, ctx: object) -> CanvasCaller | None:
        try:
            caller = await self.authenticate(ctx)
            return caller if isinstance(caller, CanvasCaller) else None
        except Exception:
            return None

    async def tools(self, ctx: object) -> list[Tool]:
        caller = await self.principal(ctx)
        if caller is None:
            return []
        return [
            Tool(
                name=name,
                description=_tool_description(name, schema),
                input_schema=schema,
                annotations=ToolAnnotations(
                    read_only_hint=name in _READ_ONLY,
                    idempotent_hint=name in _READ_ONLY,
                    open_world_hint=False,
                ),
                _meta={
                    "ui": {
                        "resourceUri": URI,
                        "visibility": ["model", "app"]
                        if name in MODEL_TOOLS
                        else ["app"],
                    }
                },
            )
            for name, schema in sorted(self._schemas.items())
            if name in MODEL_TOOLS or caller.audience == "app"
        ]

    async def call(self, ctx: object, name: str, arguments: object) -> CallToolResult:
        caller = await self.principal(ctx)
        try:
            if (
                caller is None
                or name not in self._schemas
                or (name in APP_TOOLS and caller.audience != "app")
            ):
                raise ValueError("Canvas operation denied")
            inputs = _object(arguments, 1024 * 1024)
            if name == "canvas_open" and inputs:
                raise ValueError("empty launcher input required")
            # Domain authorization, exact app/revision/binding checks and request
            # validation belong to the real port, not tool visibility metadata.
            reply = await self.port.call(caller, name, inputs)
            if (
                not isinstance(reply, CanvasReply)
                or not isinstance(reply.summary, str)
                or len(reply.summary.encode()) > 4096
            ):
                raise ValueError("invalid Canvas reply")
            model = (
                _object(reply.model_result, 128 * 1024)
                if reply.model_result is not None
                else None
            )
            view = (
                _object(reply.view_state, 1024 * 1024)
                if reply.view_state is not None
                else None
            )
            return CallToolResult(
                content=[TextContent(type="text", text=reply.summary)],
                structured_content=model,
                _meta={"actions.canvas": view} if view is not None else None,
            )
        except Exception:
            # Do not expose provider exceptions, source paths or credentials.
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="Canvas request unavailable, invalid or access denied.",
                    )
                ],
                is_error=True,
            )
