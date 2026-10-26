"""Explicit app input selection on existing queue and Run authorities."""
from __future__ import annotations

import json
from typing import Literal
from uuid import uuid4

from actions.work_items import State
from pydantic import BaseModel, ConfigDict, Field

from actions.server.data_queries.invoice_worker import work_item_run_key
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.managed_work_items.contracts import Inspect, Permission, QueueRef
from actions.server.managed_work_items.generic_service import (
    GenericManagedWorkItemsService,
)
from actions.server.run_outputs.models import RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _canonical,
    _key,
    _now,
    _one,
)
from actions.server.run_outputs.types import canonical_uuid


class InputSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    mode: Literal["generic"]
    binding_id: str = Field(alias="bindingId", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    queue: QueueRef


class InputList(InputSelection):
    action: Literal["inputs"]
    cursor: str | None = Field(default=None, max_length=4096)


class InputSubmit(InputSelection):
    action: Literal["submit_input"]
    item_id: str = Field(alias="itemId", pattern=r"^[0-9a-f-]{36}$")
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)


def authorize(service, caller, queue):
    if (
        not isinstance(service, GenericWorkItemExecution)
        or service.policy.input_mode not in ("required", "claim")
        or service.policy.input_queue is None
    ):
        raise AccessDenied("explicit input-consuming policy required")
    service._current(caller)
    if queue != service.queue_ref(service.policy.input_queue):
        raise AccessDenied("selected input queue differs from immutable binding")
    service.authorize(caller, Permission.READ)
    service.authorize(caller, Permission.CLAIM)


def _preview(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {
        "preview": raw[:2048].decode("utf-8", errors="ignore"),
        "previewTruncated": len(raw) > 2048,
    }


def list_inputs(service, caller, request):
    authorize(service, caller, request.queue)
    page = GenericManagedWorkItemsService(service).call(
        caller,
        Inspect(
            operation="items.list", queue=request.queue, cursor=request.cursor, limit=20
        ),
    )
    return {
        "bindingId": request.binding_id,
        "queue": request.queue.model_dump(mode="json"),
        "items": [
            {
                "itemId": item["id"],
                "state": item["queue_state"],
                "inputDigest": item["protected_input_digest"],
                **_preview(item["payload"]),
                "selectable": item["queue_state"] == "PENDING"
                and item["delivery_count"] == 0
                and item["business_state"] != "cancelled",
            }
            for item in page["items"]
        ],
        "nextCursor": page["next_cursor"],
    }


def submit_input(view, caller, service, managed, request):
    """Caller holds canonical counter/workspace transaction: reserve+admit+receipt."""
    authorize(service, managed, request.queue)
    canonical_uuid(request.item_id)
    if len(request.idempotency_key.encode()) > 128:
        raise ValueError("bounded input selection key required")
    scope = caller.scope
    identity = _key(
        "actions.generic-app-input-request/v1",
        caller.workspace_id,
        caller.actor.principal_id,
        _canonical(scope.model_dump(mode="json"), 16384),
        request.binding_id,
        request.idempotency_key,
    )
    fingerprint = _canonical(
        {"queue": request.queue.model_dump(mode="json"), "itemId": request.item_id},
        16384,
    )
    prior = service.db.all(FoundryRequest, where="id=?", values=[identity])
    operation = "generic-app.input-submit"
    if prior:
        saved = prior[0]
        if (
            len(prior) != 1
            or saved.workspace_id != caller.workspace_id
            or saved.principal_id != caller.actor.principal_id
            or saved.operation != operation
            or saved.idempotency_key != request.idempotency_key
            or saved.request_fingerprint != fingerprint
        ):
            raise AccessDenied("input selection changed for existing request")
        audits = service.db.all(
            FoundryAudit, where="foundry_request_id=?", values=[identity]
        )
        if len(audits) != 1:
            raise FenceRejected("input selection audit unavailable")
        audit = audits[0]
        if (
            audit.workspace_id != caller.workspace_id
            or audit.principal_id != caller.actor.principal_id
            or audit.operation != operation
            or audit.deployment_id != str(scope.deployment.deployment_id.root)
            or audit.from_revision_id != scope.deployment.revision_id.root
            or audit.to_revision_id != scope.deployment.revision_id.root
        ):
            raise FenceRejected("input selection audit changed")
        result = json.loads(saved.result_json)
        if set(result) != {"runId", "itemId"} or result["itemId"] != request.item_id:
            raise FenceRejected("input selection receipt changed")
        run, ticket, state = view._read(
            service, managed, result["runId"], request.binding_id, scope
        )
        if ticket.claim is None or ticket.claim.item_id != request.item_id:
            raise FenceRejected("input selection Run differs")
        return run, ticket, state
    service.read_input(managed, request.item_id)
    item = _one(service.db, FencedWorkItem, request.item_id)
    if (
        item.state != State.PENDING.value
        or item.claim_epoch != 0
        or item.cancel_requested
    ):
        raise FenceRejected("selected input is not an unclaimed pending item")
    run_key = work_item_run_key(request.item_id)
    if service.db.all(
        RunPin,
        where="idempotency_id=?",
        values=[
            _key("actions.workspace-run-idempotency/v1", caller.workspace_id, run_key)
        ],
    ):
        raise FenceRejected("selected input already has retained admission")
    claim = service.queue(service.policy.input_queue).reserve_item_fenced(
        request.item_id, managed.worker_id, lease_seconds=60
    )
    ticket = service.dispatch(managed, claim, lease_seconds=60)
    view._record_association(
        managed, scope, request.binding_id, ticket.fence.run_id, request.idempotency_key
    )
    result = _canonical(
        {"runId": ticket.fence.run_id, "itemId": request.item_id}, 16384
    )
    service.db.insert(
        FoundryRequest(
            identity,
            caller.workspace_id,
            caller.actor.principal_id,
            operation,
            request.idempotency_key,
            fingerprint,
            result,
        )
    )
    service.db.insert(
        FoundryAudit(
            str(uuid4()),
            caller.workspace_id,
            str(scope.deployment.deployment_id.root),
            caller.actor.principal_id,
            operation,
            identity,
            scope.deployment.revision_id.root,
            scope.deployment.revision_id.root,
            str(_now(service.db)),
        )
    )
    return view._read(service, managed, ticket.fence.run_id, request.binding_id, scope)
