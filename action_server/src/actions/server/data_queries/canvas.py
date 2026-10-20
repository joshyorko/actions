"""Read-only Canvas result facade over existing query/output services.

Trusted server code supplies the application/deployment scope and authenticated
Actor. Nothing here registers or generates apps, executes on mount, defines a
second CanvasSpec/renderer, or proves an MCP bridge or actual ChatGPT host.
"""

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any

from actions.server.run_outputs.service import ResolvedOutput
from actions.server.run_outputs.types import Actor, CanvasResultScope

from .service import InvoiceQueryService


@dataclass(frozen=True)
class InvoiceCanvasFacade:
    queries: InvoiceQueryService
    scope: CanvasResultScope

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", CanvasResultScope.model_validate(self.scope))

    def page(
        self, actor: Actor, handle: str, *, offset: int, limit: int
    ) -> dict[str, Any]:
        rows = self.queries.page(
            actor,
            self.scope.application.workspace_id,
            handle,
            offset=offset,
            limit=limit,
            canvas_scope=self.scope,
        )
        return {
            "rows": [row.model_dump(mode="json") for row in rows],
            "artifact": {"handle": handle},
            "error": None,
        }

    def export(
        self, actor: Actor, handle: str
    ) -> AbstractContextManager[ResolvedOutput]:
        return self.queries.export(
            actor, self.scope.application.workspace_id, handle, canvas_scope=self.scope
        )
