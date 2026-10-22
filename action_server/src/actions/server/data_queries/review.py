"""Explicit human decisions over sealed results, using the existing SQL authority.

Trusted transport supplies Actor and application scope. No decision is inferred
from reading a result. Approval and the installed SDK queue insert share the
same connection/transaction. Run and Attempt admission/execution remain separate.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Literal
from uuid import uuid4

from actions.work_items._adapters._sql_review import SQLReviewQueue
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from actions.server._database import Database
from actions.server._models import RUN_ID_COUNTER, Run
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.service import (
    AccessDenied,
    _canonical,
    _insert,
    _key,
    _lock_run,
    _lock_workspace,
    _now,
    _one,
    _returning,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import (
    Actor,
    CanvasResultScope,
    output_id_from_handle,
)

from .review_models import InvoiceReview
from .service import InvoiceQueryService


class ReviewConflict(ValueError):
    """The decision or exact result differs from the retained proposal."""


class ReviewBinding(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )
    scope: CanvasResultScope
    handle: str = Field(min_length=1, max_length=1024)
    run_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    result_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    input_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_version: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_fingerprint: str = Field(min_length=1, max_length=256)


class ReviewProposal(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )
    review_id: str
    binding: ReviewBinding


class ReviewReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    review_id: str
    state: Literal["pending", "approved", "rejected", "cancelled"]
    work_item_id: str | None


class _SQLStore:
    def __init__(self, db: Database, workspace: str):
        self.db, self.workspace = db, workspace
        self.backend_name = db.backend_name

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with _transaction(self.db):
            _lock_workspace(self.db, self.workspace)
            yield

    def execute(self, sql: str, values: list[Any]) -> list[tuple[Any, ...]]:
        if not self.db.in_transaction():
            raise RuntimeError("review queue requires the owning SQL transaction")
        with self.db.cursor() as cursor:
            if sql.startswith("SELECT"):
                self.db.execute_query(cursor, sql, values)
            else:
                self.db.execute_update_returning(cursor, sql, values)
            return cursor.fetchall()


class InvoiceReviewService:
    def __init__(self, queries: InvoiceQueryService):
        self.queries = queries
        self.outputs = queries.outputs
        self.db = self.outputs.db

    def queue(self, scope: CanvasResultScope) -> SQLReviewQueue:
        scope = CanvasResultScope.model_validate(scope)
        workspace = scope.application.workspace_id
        return SQLReviewQueue(
            _SQLStore(self.db, workspace),
            workspace,
            _key("invoice-review-queue/v1", scope.model_dump_json()),
        )

    def _binding(
        self,
        actor: Actor,
        scope: CanvasResultScope,
        handle: str,
        *,
        open_result: bool = True,
    ) -> ReviewBinding:
        scope = CanvasResultScope.model_validate(scope)
        # Preserve Counter -> Workspace lock order and obtain SQLite's writer
        # before the first output read, including across independent processes.
        if not _returning(
            self.db,
            "UPDATE counter SET value=value WHERE id=? RETURNING id",
            [RUN_ID_COUNTER],
        ):
            raise RuntimeError("Run counter unavailable")
        output = _one(self.db, RunOutput, output_id_from_handle(handle))
        pin = _lock_run(self.db, output.run_id)
        snapshot = self.outputs._pinned(pin)
        if (
            snapshot.deployment != scope.deployment
            or snapshot.canvas_application != scope.application
            or snapshot.data_binding is None
        ):
            raise AccessDenied("review result unavailable or access denied")
        self.outputs._authorize(actor, snapshot, "read")
        if open_result:
            with self.queries.export(
                actor, scope.application.workspace_id, handle, canvas_scope=scope
            ) as result:
                if result.digest != output.digest:
                    raise ReviewConflict("result digest changed")
        run = _one(self.db, Run, output.run_id)
        return ReviewBinding(
            scope=scope,
            handle=handle,
            run_id=run.id,
            result_digest=output.digest,
            input_digest="sha256:" + hashlib.sha256(run.inputs.encode()).hexdigest(),
            source_version=snapshot.data_binding.source_version,
            request_fingerprint=pin.request_fingerprint,
        )

    @staticmethod
    def _json(binding: ReviewBinding) -> str:
        return _canonical(binding.model_dump(mode="json"), 65536)

    @staticmethod
    def _receipt(row: InvoiceReview) -> ReviewReceipt:
        return ReviewReceipt(
            review_id=row.id,
            state=TypeAdapter(
                Literal["pending", "approved", "rejected", "cancelled"]
            ).validate_python(row.state),
            work_item_id=row.work_item_id or None,
        )

    def offer(
        self, actor: Actor, scope: CanvasResultScope, handle: str
    ) -> ReviewProposal:
        with _transaction(self.db):
            binding = self._binding(actor, scope, handle)
            encoded = self._json(binding)
            key = _key("actions.invoice-review/v1", encoded)
            rows = self.db.all(InvoiceReview, where="binding_id=?", values=[key])
            if rows:
                row = rows[0]
                if row.binding_json != encoded:
                    raise ReviewConflict("review binding identity conflict")
            else:
                row = InvoiceReview(
                    str(uuid4()),
                    scope.application.workspace_id,
                    binding.run_id,
                    key,
                    encoded,
                    "pending",
                    "",
                    "",
                    "",
                )
                _insert(self.db, row)
            return ReviewProposal(review_id=row.id, binding=binding)

    def _current(
        self,
        actor: Actor,
        scope: CanvasResultScope,
        proposal: ReviewProposal,
        *,
        open_result: bool = True,
    ) -> InvoiceReview:
        proposal = ReviewProposal.model_validate(proposal)
        binding = self._binding(
            actor, scope, proposal.binding.handle, open_result=open_result
        )
        row = _one(self.db, InvoiceReview, proposal.review_id)
        if row.workspace_id != scope.application.workspace_id:
            raise AccessDenied("review result unavailable or access denied")
        if row.binding_json != self._json(
            proposal.binding
        ) or row.binding_json != self._json(binding):
            raise ReviewConflict(
                "review binding differs from the exact retained result"
            )
        return row

    def decide(
        self,
        actor: Actor,
        scope: CanvasResultScope,
        proposal: ReviewProposal,
        decision: Literal["approve", "reject"],
    ) -> ReviewReceipt:
        if decision not in ("approve", "reject"):
            raise ValueError("explicit approve or reject decision required")
        with _transaction(self.db):
            row = self._current(actor, scope, proposal, open_result=False)
            pin = _lock_run(self.db, row.run_id)
            self.outputs._authorize(actor, self.outputs._pinned(pin), "review")
            target = "approved" if decision == "approve" else "rejected"
            if row.state == target:
                return self._receipt(row)
            if row.state != "pending":
                raise ReviewConflict("review decision is already terminal")
            self._current(actor, scope, proposal)
            item_id = ""
            if decision == "approve":
                item_id = str(uuid4())
                self.queue(scope).seed_input(
                    {
                        "schema": "actions.invoice-review/v1",
                        "review_id": row.id,
                        "binding": proposal.binding.model_dump(mode="json"),
                    },
                    item_id=item_id,
                )
            _update(
                self.db,
                InvoiceReview,
                row.id,
                {
                    "state": target,
                    "work_item_id": item_id,
                    "decision_json": _canonical(
                        {
                            "decision": decision,
                            "actor": actor.principal_id,
                            "at_ms": _now(self.db),
                        },
                        4096,
                    ),
                },
            )
            return self._receipt(_one(self.db, InvoiceReview, row.id))

    def status(
        self, actor: Actor, scope: CanvasResultScope, proposal: ReviewProposal
    ) -> ReviewReceipt:
        with _transaction(self.db):
            return self._receipt(
                self._current(actor, scope, proposal, open_result=False)
            )

    def cancel(
        self, actor: Actor, scope: CanvasResultScope, proposal: ReviewProposal
    ) -> ReviewReceipt:
        with _transaction(self.db):
            row = self._current(actor, scope, proposal, open_result=False)
            pin = _lock_run(self.db, row.run_id)
            self.outputs._authorize(actor, self.outputs._pinned(pin), "cancel")
            if row.state == "cancelled":
                return self._receipt(row)
            if row.state not in ("pending", "approved"):
                raise ReviewConflict("review cannot be cancelled")
            if row.work_item_id and not self.queue(scope).cancel(row.work_item_id):
                raise ReviewConflict("completed Work Item cannot be cancelled")
            _update(
                self.db,
                InvoiceReview,
                row.id,
                {
                    "state": "cancelled",
                    "cancellation_json": _canonical(
                        {"actor": actor.principal_id, "at_ms": _now(self.db)}, 4096
                    ),
                },
            )
            return self._receipt(_one(self.db, InvoiceReview, row.id))
