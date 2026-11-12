"""Private composition of existing Canvas activation and SQL invoice authorities.

This binds one generated revision of the existing renderer and typed query.
It registers no public lifecycle API, renderer, scheduler or business-state store.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from actions.work_items._fencing import WorkItemClaim
from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field

from actions.server._models import RunStatus
from actions.server.canvas_lifecycle import (
    CanvasAuthorizationError,
    CanvasResourceGrant,
    CanvasRevisionError,
    CanvasRevisionStore,
)
from actions.server.run_outputs.service import AccessDenied
from actions.server.run_outputs.transport import RunOutputTransport
from actions.server.run_outputs.types import (
    Actor,
    CanvasResultScope,
    ExecutionSnapshot,
    InvoiceBinding,
    OutputRef,
)

from .canvas import InvoiceCanvasFacade
from .canvas_mcp import InvoiceCanvasMcp, InvoiceCanvasPrincipal
from .invoice_worker import InvoiceWorkerService
from .invoices import InvoiceQuery
from .review import InvoiceReviewService, ReviewProposal
from .service import InvoiceQueryService


class InvoiceRevisionInputs(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    version: Literal["actions.generated-invoice/v1"] = "actions.generated-invoice/v1"
    inputs: InvoiceQuery
    data_binding: InvoiceBinding
    renderer_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def invoice_revision_files(
    html: bytes, binding: InvoiceBinding, inputs: InvoiceQuery
) -> dict[str, bytes]:
    config = InvoiceRevisionInputs(
        inputs=inputs,
        data_binding=binding,
        renderer_sha256=hashlib.sha256(html).hexdigest(),
    )
    return {"canvas.html": html, "invoice.json": config.model_dump_json().encode()}


def validate_invoice_revision(app_id: str, files: Mapping[str, bytes]) -> None:
    if set(files) != {"canvas.html", "invoice.json"}:
        raise CanvasRevisionError("exact invoice renderer and typed inputs required")
    config = InvoiceRevisionInputs.model_validate_json(files["invoice.json"])
    if config.renderer_sha256 != hashlib.sha256(files["canvas.html"]).hexdigest():
        raise CanvasRevisionError("invoice renderer differs from generated revision")
    if not files["canvas.html"] or len(files["invoice.json"]) > 65536:
        raise CanvasRevisionError("bounded generated invoice revision required")
    files["canvas.html"].decode("utf-8", errors="strict")


@dataclass(frozen=True)
class GeneratedInvoiceApp:
    store: CanvasRevisionStore
    queries: InvoiceQueryService
    snapshot: ExecutionSnapshot

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "snapshot", ExecutionSnapshot.model_validate(self.snapshot)
        )
        if (
            self.snapshot.runtime_kind != "invoice/generated-query/v1"
            or self.snapshot.canvas_application is None
            or self.snapshot.data_binding is None
        ):
            raise ValueError("pinned generated application and data binding required")

    @property
    def scope(self) -> CanvasResultScope:
        assert self.snapshot.canvas_application is not None
        return CanvasResultScope(
            deployment=self.snapshot.deployment,
            application=self.snapshot.canvas_application,
        )

    def _active(self, actor: Actor):
        scope = self.scope
        with self.queries.outputs.db.connect():
            self.queries.outputs._authorize(actor, self.snapshot, "read")
            revision = self.store.pin_active(
                actor,
                scope.application.workspace_id,
                scope.deployment.revision_id.root,
                scope.application.app_id,
            )
        if revision.revision_id != scope.application.revision_id:
            raise AccessDenied("generated application revision is no longer active")
        validate_invoice_revision(revision.app_id, revision.files)
        config = InvoiceRevisionInputs.model_validate_json(
            revision.files["invoice.json"]
        )
        if config.data_binding != self.snapshot.data_binding:
            raise AccessDenied(
                "generated source binding differs from admitted deployment"
            )
        return revision, config

    def require_current(self, actor: Actor) -> None:
        self._active(actor)

    @property
    def facade(self) -> InvoiceCanvasFacade:
        return InvoiceCanvasFacade(self.queries, self.scope, self.require_current)

    def invoke(
        self,
        actor: Actor,
        idempotency_key: str,
        owner_id: str,
        cancelled: threading.Event,
    ) -> str:
        _, config = self._active(actor)
        outputs = self.queries.outputs
        with outputs.db.connect():
            run = outputs.admit(
                actor,
                self.snapshot,
                config.inputs.model_dump(mode="json"),
                idempotency_key,
            )
            if run.status == RunStatus.PASSED:
                envelope = json.loads(run.result or "null")
                output = OutputRef.model_validate(envelope["outputs"][0])
                with self.facade.export(actor, output.handle):
                    return output.handle
            return self.queries.execute(
                actor, outputs.claim(run.id, owner_id, lease_seconds=30), cancelled
            )

    def renderer(self, actor: Actor) -> str:
        revision, _ = self._active(actor)
        scope = self.scope
        with self.queries.outputs.db.connect():
            return self.store.read_resource(
                CanvasResourceGrant(
                    actor,
                    scope.application.workspace_id,
                    scope.deployment.revision_id.root,
                    scope.application.app_id,
                    revision.revision_id,
                ),
                "canvas.html",
            ).decode("utf-8")

    def mcp(
        self,
        actor: Actor,
        authenticate: Callable[
            [dict[str, str], dict[str, str]], Awaitable[InvoiceCanvasPrincipal | None]
        ],
        *,
        reviews: InvoiceReviewService,
        download_base_url: str | None = None,
        initial_page_size: int = 20,
    ) -> InvoiceCanvasMcp:
        async def current(headers, cookies):
            principal = await authenticate(headers, cookies)
            if principal is not None:
                self.require_current(principal.actor)
            return principal

        return InvoiceCanvasMcp(
            self.facade,
            current,
            self.renderer(actor),
            reviews=reviews,
            download_base_url=download_base_url,
            resource_revision=self.scope.application.revision_id,
            initial_page_size=initial_page_size,
        )

    def output_transport(
        self, authenticate: Callable[[Request], Awaitable[Actor | None]]
    ) -> RunOutputTransport:
        async def current(request: Request):
            actor = await authenticate(request)
            if actor is not None:
                try:
                    self.require_current(actor)
                except (AccessDenied, CanvasAuthorizationError, CanvasRevisionError):
                    return None
            return actor

        return RunOutputTransport(
            self.queries.outputs, current, canvas_scope=self.scope
        )

    def dispatch(
        self,
        actor: Actor,
        worker: InvoiceWorkerService,
        proposal: ReviewProposal,
        claim: WorkItemClaim,
        *,
        lease_seconds: int,
    ):
        self.require_current(actor)
        if worker.scope != self.scope or worker.reviews.queries is not self.queries:
            raise AccessDenied(
                "generated worker differs from pinned application authority"
            )
        return worker.dispatch(actor, proposal, claim, lease_seconds=lease_seconds)
