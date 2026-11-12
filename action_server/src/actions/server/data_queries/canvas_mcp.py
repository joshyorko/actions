"""Default-off invoice projection on the existing MCP server and Canvas renderer.

Trusted server composition supplies the immutable view and credential verifier.
MCP visibility is discovery metadata, never app authorization. The authenticator
must distinguish a verified app bridge from a model connection independently of
caller arguments/headers claiming app identity. No public identity protocol is
provided here. Result reads never execute another query or admit a Run.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal
from urllib.parse import urlsplit

from mcp.types import CallToolResult, Resource, TextContent, Tool, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from actions.server.run_outputs.types import Actor, output_id_from_handle

from .canvas import InvoiceCanvasFacade
from .review import InvoiceReviewService, ReviewProposal

PAGE_KEY = "actions.invoicePage"
TOOL_NAMES = frozenset(
    {
        "invoice_result",
        "invoice_result_page",
        "invoice_result_export",
        "invoice_review_offer",
        "invoice_review_decide",
        "invoice_review_cancel",
        "invoice_review_execution",
    }
)
REVIEW_TOOLS = frozenset(
    {"invoice_review_offer", "invoice_review_decide", "invoice_review_cancel"}
)


class ResultInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    handle: str


class PageInput(ResultInput):
    offset: int = Field(ge=0, le=100000)
    limit: int = Field(ge=1, le=99)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    proposal: ReviewProposal


class DecisionInput(ReviewInput):
    decision: Literal["approve", "reject"]


@dataclass(frozen=True)
class InvoiceCanvasPrincipal:
    actor: Actor
    audience: Literal["model", "app"]

    def __post_init__(self) -> None:
        if not isinstance(self.actor, Actor) or self.audience not in ("model", "app"):
            raise ValueError("verified actor and audience required")


@dataclass(frozen=True)
class InvoiceCanvasMcp:
    @staticmethod
    def _row_description(row: dict) -> str:
        if row.get("reconciliation") is not None:
            from .reconciliation import description

            return description(row["reconciliation"])
        return f'{row["amount_cents"]} cents; {row["days_overdue"]} days overdue'

    facade: InvoiceCanvasFacade
    authenticate: Callable[
        [dict[str, str], dict[str, str]], Awaitable[InvoiceCanvasPrincipal | None]
    ]
    html: str
    download_base_url: str | None = None
    initial_page_size: int = 20
    reviews: InvoiceReviewService | None = None
    resource_revision: str | None = None

    def __post_init__(self) -> None:
        if (
            self.resource_revision is not None
            and self.resource_revision != self.facade.scope.application.revision_id
        ):
            raise ValueError("resource revision differs from pinned application")
        if self.reviews is not None and self.reviews.queries is not self.facade.queries:
            raise ValueError("review must use the same query/output authority")
        if (
            not isinstance(self.initial_page_size, int)
            or isinstance(self.initial_page_size, bool)
            or not 1 <= self.initial_page_size <= 99
        ):
            raise ValueError("bounded initial page size required")
        if not isinstance(self.facade, InvoiceCanvasFacade) or not callable(
            self.authenticate
        ):
            raise TypeError("trusted facade and authenticator required")
        if (
            not isinstance(self.html, str)
            or not 0 < len(self.html.encode()) <= 4 * 1024 * 1024
        ):
            raise ValueError("bounded immutable renderer HTML required")
        if self.download_base_url is not None:
            parsed = urlsplit(self.download_base_url)
            if (
                not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.scheme not in ("http", "https")
                or (
                    parsed.scheme == "http"
                    and parsed.hostname not in ("127.0.0.1", "localhost", "::1")
                )
                or parsed.port == 0
            ):
                raise ValueError("trusted HTTPS or loopback download origin required")

    @property
    def uri(self) -> str:
        digest = sha256(self.html.encode()).hexdigest()
        revision = (
            self.resource_revision.removeprefix("sha256:") + "/"
            if self.resource_revision
            else ""
        )
        return f"ui://action-canvas/invoice/v1/{revision}{digest}.html"

    @property
    def resource(self) -> Resource:
        return Resource(
            uri=self.uri,
            name="invoice_result_view",
            mime_type="text/html;profile=mcp-app",
            _meta={
                "ui": {"csp": {}},
                "actions.application": self.facade.scope.application.model_dump(
                    mode="json"
                ),
            },
        )

    async def principal(self, ctx: Any) -> InvoiceCanvasPrincipal | None:
        request = ctx.request
        if request is None:
            return None
        try:
            principal = await self.authenticate(
                dict(request.headers), dict(request.cookies)
            )
            return principal if isinstance(principal, InvoiceCanvasPrincipal) else None
        except Exception:
            return None

    async def tools(self, ctx: Any) -> list[Tool]:
        principal = await self.principal(ctx)
        if principal is None:
            return []
        result = []
        for name in sorted(TOOL_NAMES):
            if principal.audience == "model" and name != "invoice_result":
                continue
            if (
                name in REVIEW_TOOLS or name == "invoice_review_execution"
            ) and self.reviews is None:
                continue
            schema = (
                DecisionInput
                if name == "invoice_review_decide"
                else ReviewInput
                if name in ("invoice_review_cancel", "invoice_review_execution")
                else PageInput
                if name == "invoice_result_page"
                else ResultInput
            )
            result.append(
                Tool(
                    name=name,
                    description=(
                        "Explicitly review this exact saved result. Approval creates one Work Item, without executing it."
                        if name in REVIEW_TOOLS
                        else "Read an already-published, authorized invoice result. No query execution."
                    ),
                    input_schema=schema.model_json_schema(),
                    annotations=ToolAnnotations(
                        read_only_hint=name not in REVIEW_TOOLS,
                        destructive_hint=name == "invoice_review_cancel",
                        idempotent_hint=True,
                        open_world_hint=False,
                    ),
                    _meta={
                        "ui": {
                            "resourceUri": self.uri,
                            "visibility": ["model", "app"]
                            if name == "invoice_result"
                            else ["app"],
                        }
                    },
                )
            )
        return result

    async def call(
        self, ctx: Any, name: str, arguments: dict[str, Any]
    ) -> CallToolResult:
        principal = await self.principal(ctx)
        try:
            if principal is None or (
                name != "invoice_result" and principal.audience != "app"
            ):
                raise PermissionError
            if name == "invoice_review_execution":
                if self.reviews is None:
                    raise PermissionError
                request_execution = ReviewInput.model_validate(arguments)
                with self.facade.queries.outputs.db.connect():
                    execution = self.reviews.execution(
                        principal.actor, self.facade.scope, request_execution.proposal
                    )
                payload = execution.model_dump(mode="json")
                if (
                    execution.phase in ("completed", "dead_letter")
                    and self.download_base_url is not None
                ):
                    workspace = self.facade.scope.application.workspace_id
                    payload["artifact"][
                        "uri"
                    ] = f"{self.download_base_url}/api/workspaces/{workspace}/outputs/{execution.artifact.handle}"
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="Authorized execution status is available.",
                        )
                    ],
                    structured_content={
                        "schemaVersion": "actions.invoice-execution-status/v1",
                        "phase": execution.phase,
                    },
                    _meta={"actions.invoiceExecution": payload},
                )
            if name in REVIEW_TOOLS:
                if self.reviews is None:
                    raise PermissionError
                with self.facade.queries.outputs.db.connect():
                    if name == "invoice_review_offer":
                        request = ResultInput.model_validate(arguments)
                        proposal = self.reviews.offer(
                            principal.actor, self.facade.scope, request.handle
                        )
                        receipt = self.reviews.status(
                            principal.actor, self.facade.scope, proposal
                        )
                    elif name == "invoice_review_decide":
                        decision = DecisionInput.model_validate(arguments)
                        proposal = decision.proposal
                        receipt = self.reviews.decide(
                            principal.actor,
                            self.facade.scope,
                            proposal,
                            decision.decision,
                        )
                    else:
                        request_cancel = ReviewInput.model_validate(arguments)
                        proposal = request_cancel.proposal
                        receipt = self.reviews.cancel(
                            principal.actor, self.facade.scope, proposal
                        )
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text", text="Explicit result review recorded."
                            )
                        ],
                        structured_content={
                            "schemaVersion": "actions.invoice-review/v1",
                            "state": receipt.state,
                        },
                        _meta={
                            "actions.invoiceReview": {
                                "proposal": proposal.model_dump(mode="json"),
                                "receipt": receipt.model_dump(mode="json"),
                            }
                        },
                    )
            inputs = (
                PageInput if name == "invoice_result_page" else ResultInput
            ).model_validate(arguments)
            output_id_from_handle(inputs.handle)
            # Database connections are thread-local; the current MCP request owns
            # this context. No synchronous provider query or worker runs here.
            with self.facade.queries.outputs.db.connect():
                if name == "invoice_result_export":
                    with self.facade.export(principal.actor, inputs.handle) as output:
                        descriptor = {
                            "handle": inputs.handle,
                            "digest": output.digest,
                            "size": output.size,
                            "mediaType": output.media_type,
                        }
                        if self.download_base_url is not None:
                            workspace = self.facade.scope.application.workspace_id
                            descriptor[
                                "uri"
                            ] = f"{self.download_base_url}/api/workspaces/{workspace}/outputs/{inputs.handle}"
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text", text="Authorized invoice export is ready."
                            )
                        ],
                        structured_content={
                            "schemaVersion": "actions.invoice-export/v1",
                            "handle": inputs.handle,
                        },
                        _meta={"actions.invoiceExport": descriptor},
                    )
                offset, limit = (
                    (inputs.offset, inputs.limit)
                    if isinstance(inputs, PageInput)
                    else (0, self.initial_page_size)
                )
                data = self.facade.page(
                    principal.actor, inputs.handle, offset=offset, limit=limit + 1
                )
                rows = data["rows"][:limit]
                page = {
                    "schemaVersion": "actions.invoice-page/v1",
                    "rows": [
                        {
                            "id": row["invoice_id"],
                            "title": row["customer"],
                            "category": self._row_description(row),
                            **(
                                {"reconciliation": row["reconciliation"]}
                                if "reconciliation" in row
                                else {}
                            ),
                        }
                        for row in rows
                    ],
                    "artifact": data["artifact"],
                    "error": None,
                    "offset": offset,
                    "nextOffset": offset + limit if len(data["rows"]) > limit else None,
                }
                if self.reviews is not None:
                    page["reviewAvailable"] = True
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Authorized invoice result: {len(rows)} rows in this page.",
                        )
                    ],
                    structured_content={
                        "schemaVersion": "actions.invoice-summary/v1",
                        "handle": inputs.handle,
                        "pageRows": len(rows),
                    },
                    _meta={PAGE_KEY: page},
                )
        except Exception:
            # No provider paths, secrets, row values or authorization oracle.
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", text="Invoice result unavailable or access denied."
                    )
                ],
                is_error=True,
            )
