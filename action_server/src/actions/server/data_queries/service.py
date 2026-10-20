"""Private invoice operation using the existing Run/output authority exclusively.

Not installed in HTTP/MCP by default. Trusted server code supplies verified Actor
identity and version-keyed providers. Typed references never authenticate callers.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Protocol

from actions.server.run_outputs.service import (
    AccessDenied,
    ResolvedOutput,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor, AttemptFence, CanvasResultScope

from .invoices import (
    COLUMNS,
    OPERATION,
    Invoice,
    InvoiceLimits,
    InvoiceQuery,
    InvoiceResult,
    QueryRejected,
)


class InvoiceProvider(Protocol):
    kind: str

    def query(
        self, query: InvoiceQuery, limits: InvoiceLimits, cancelled: threading.Event
    ) -> AbstractContextManager[InvoiceResult]:
        ...


class InvoiceQueryService:
    def __init__(
        self, outputs: RunOutputService, providers: dict[str, InvoiceProvider]
    ):
        self.outputs = outputs
        self.providers = dict(providers)

    def execute(
        self, actor: Actor, fence: AttemptFence, cancelled: threading.Event
    ) -> str:
        snapshot, inputs = self.outputs.execution_context(actor, fence)
        binding = snapshot.data_binding
        if binding is None or binding.key not in self.providers:
            raise AccessDenied("pinned invoice data binding unavailable")
        provider = self.providers[binding.key]
        query = InvoiceQuery.model_validate(inputs)
        receipt: dict[str, Any] = {
            "operation": OPERATION,
            "columns": list(COLUMNS),
            "provider_kind": provider.kind,
            "provider": binding.provider.model_dump(mode="json"),
            "source_version": binding.source_version,
            "source_version_authority": "operator-claim",
            "limits": binding.limits.model_dump(),
            "row_count": 0,
        }

        def chunks() -> Iterator[bytes]:
            with provider.query(query, binding.limits, cancelled) as result:
                if result.columns != COLUMNS:
                    raise QueryRejected("invoice schema mismatch")
                receipt["source_snapshot"] = result.source_snapshot
                for row in result.rows:
                    receipt["row_count"] += 1
                    yield row.model_dump_json().encode("utf-8") + b"\n"

        output = self.outputs.stage(
            fence,
            chunks(),
            name="invoices.ndjson",
            media_type="application/x-ndjson",
            retention_seconds=3600,
        )
        self.outputs.publish(actor, fence, [output], receipt)
        return output.handle

    def page(
        self,
        actor: Actor,
        workspace_id: str,
        handle: str,
        *,
        offset: int,
        limit: int,
        canvas_scope: CanvasResultScope | None = None,
    ) -> list[Invoice]:
        if (
            not isinstance(offset, int)
            or isinstance(offset, bool)
            or not 0 <= offset <= 100000
            or not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= 100
        ):
            raise ValueError("bounded integer page offset/limit required")
        page = []
        with self.export(
            actor, workspace_id, handle, canvas_scope=canvas_scope
        ) as output:
            pending = b""
            index = 0
            while chunk := output.read(8192):
                pending += chunk
                while b"\n" in pending:
                    line, pending = pending.split(b"\n", 1)
                    if len(line) > 8192:
                        raise QueryRejected("invalid invoice result record")
                    try:
                        row = Invoice.model_validate_json(line)
                    except Exception:
                        raise QueryRejected("invalid invoice result schema") from None
                    if index >= offset:
                        page.append(row)
                        if len(page) == limit:
                            return page
                    index += 1
                if len(pending) > 8192:
                    raise QueryRejected("invalid invoice result record")
            if pending:
                raise QueryRejected("incomplete invoice result record")
        return page

    @contextmanager
    def export(
        self,
        actor: Actor,
        workspace_id: str,
        handle: str,
        *,
        canvas_scope: CanvasResultScope | None = None,
    ) -> Iterator[ResolvedOutput]:
        with self.outputs.resolve(
            actor, workspace_id, handle, canvas_scope=canvas_scope
        ) as output:
            if (
                output.media_type != "application/x-ndjson"
                or output.name != "invoices.ndjson"
            ):
                raise QueryRejected("output is not an invoice result")
            yield output
