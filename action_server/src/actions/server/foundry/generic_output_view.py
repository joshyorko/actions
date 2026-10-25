"""Read-only child projection from an app-associated successful producing Run."""
from __future__ import annotations

import json
from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from actions.server._models import RunStatus
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.generic_input_view import _preview
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.managed_work_items.contracts import Permission
from actions.server.run_outputs.service import AccessDenied, FenceRejected, _canonical
from actions.server.run_outputs.types import (
    AttemptFence,
    ExecutionSnapshot,
    canonical_uuid,
)


class OutputList(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    mode: Literal["generic"]
    action: Literal["outputs"]
    binding_id: str = Field(alias="bindingId", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    run_id: str = Field(alias="runId", pattern=r"^[0-9a-f-]{36}$")
    cursor: str | None = Field(default=None, max_length=36)


class ProducedBy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    snapshot: ExecutionSnapshot
    fence: AttemptFence
    input_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parent_id: str | None


class OutputEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["actions.generic-work-item-output/v1"] = Field(
        alias="schema"
    )
    payload: dict[str, JsonValue]
    produced_by: ProducedBy


def authorize_outputs(service, caller):
    if not isinstance(service, GenericWorkItemExecution):
        raise AccessDenied("explicit generic output policy required")
    declaration = service._current(caller)
    if not declaration.allow_outputs or service.policy.output_queue is None:
        raise AccessDenied("binding does not produce a declared output queue")
    service.base._authorize(caller.actor, service.snapshot, "read")
    for permission in (Permission.READ, Permission.ARTIFACT_READ):
        service._permission(caller, service.policy.output_queue, permission)
    return service.queue_ref(service.policy.output_queue)


def list_outputs(service, caller, run, ticket, request):
    queue = authorize_outputs(service, caller)
    if (
        run.status != RunStatus.PASSED
        or run.id != request.run_id
        or ticket.fence.run_id != run.id
    ):
        raise AccessDenied("exact successful producing Run required")
    if request.cursor is not None:
        canonical_uuid(request.cursor)
    retained = json.loads(run.result)
    action_result = retained["result"].get("actionResult")
    if (
        not isinstance(action_result, dict)
        or set(action_result) != {"result", "workItems"}
        or not isinstance(action_result["workItems"], list)
    ):
        raise FenceRejected("retained producing result differs")
    expected = action_result["workItems"]
    if len(expected) > service.policy.max_output_items or any(
        not isinstance(value, dict) for value in expected
    ):
        raise FenceRejected("retained child count differs from immutable policy")
    _canonical(expected, service.policy.max_output_bytes)
    # Match existing bounded selected-policy scan semantics; do not leak a
    # foreign child's identifier as a cursor or infer ownership from queue names.
    values = [service.snapshot.workspace_id, service.policy.output_queue]
    with service.db.cursor() as cursor:
        service.db.execute_query(
            cursor,
            "SELECT COUNT(*), COALESCE(SUM(n),0) FROM (SELECT length(payload) AS n FROM fenced_work_item WHERE workspace_id=? AND queue_name=? LIMIT 1001) AS bounded",
            values,
        )
        count, characters = cursor.fetchone()
    if count > 1000 or characters > 1048576:
        raise FenceRejected("produced-child queue exceeds bounded projection scan")
    rows = service.db.select(
        FencedWorkItem,
        "SELECT * FROM fenced_work_item WHERE workspace_id=? AND queue_name=? ORDER BY id LIMIT 1001",
        values,
    )
    parent = ticket.claim.item_id if ticket.claim else None
    matched = []
    payloads = []
    for row in rows:
        try:
            raw = json.loads(row.payload)
        except (ValueError, TypeError):
            if parent is not None and row.parent_id == parent:
                raise FenceRejected("produced child envelope malformed") from None
            continue
        provenance = raw.get("produced_by") if isinstance(raw, dict) else None
        fence = provenance.get("fence") if isinstance(provenance, dict) else None
        candidate = (isinstance(fence, dict) and fence.get("run_id") == run.id) or (
            parent is not None and row.parent_id == parent
        )
        if not candidate:
            continue
        child = OutputEnvelope.model_validate(raw)
        if (
            child.produced_by.snapshot != service.snapshot
            or child.produced_by.fence != ticket.fence
            or child.produced_by.input_digest != ticket.input_digest
            or child.produced_by.parent_id != parent
            or (row.parent_id or None) != parent
        ):
            raise FenceRejected("produced child lineage differs from exact Run")
        canonical_uuid(row.id)
        payloads.append(_canonical(child.payload, service.policy.max_output_bytes))
        matched.append(
            {
                "itemId": row.id,
                "parentId": parent,
                "queueState": row.state,
                "cancelRequested": bool(row.cancel_requested),
                **_preview(child.payload),
            }
        )
    if Counter(payloads) != Counter(
        _canonical(value, service.policy.max_output_bytes) for value in expected
    ):
        raise FenceRejected(
            "produced child inventory differs from retained publication"
        )
    if request.cursor is not None and request.cursor not in {
        item["itemId"] for item in matched
    }:
        raise AccessDenied("cursor is outside producing Run")
    eligible = [
        item
        for item in matched
        if request.cursor is None or item["itemId"] > request.cursor
    ]
    page = eligible[:20]
    return {
        "bindingId": request.binding_id,
        "runId": run.id,
        "attemptId": ticket.fence.attempt_id,
        "queue": queue.model_dump(mode="json"),
        "items": page,
        "nextCursor": page[-1]["itemId"] if len(eligible) > 20 else None,
    }
