"""Managed HTTP with live common SQL policy and actual owned data/control stores."""

import json
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_review as fixtures
from fastapi import FastAPI
from fastapi.testclient import TestClient

from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.managed_work_items.api import create_router
from actions.server.managed_work_items.contracts import (
    API_PREFIX,
    ManagedCaller,
    Permission,
)
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = fixtures.pytestmark


def configured(
    reviewed, *, worker=True, perimeter=False, executor=None, worker_id=None
):
    from actions.server.managed_work_items.authorization import (
        SqlQueueAuthorization,
        bearer_authenticator,
    )

    db, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    operations = [permission.value for permission in Permission]
    with db.transaction():
        for kind, subject in (
            ("workspace", scope.application.workspace_id),
            ("reference", reference_grant_subject(scope.deployment)),
        ):
            db.insert(
                FoundryAccessGrant(
                    str(uuid4()),
                    scope.application.workspace_id,
                    actor.principal_id,
                    kind,
                    subject,
                    json.dumps(operations),
                )
            )
    identity = ManagedCaller(
        actor=actor, worker_id=(worker_id or str(uuid4())) if worker else None
    )
    service = SQLManagedWorkItemsService(
        reviews,
        SqlQueueAuthorization(db),
        worker_for=(lambda scope: executor) if executor is not None else None,
    )
    authenticate = bearer_authenticator("owned-managed-key", identity)
    app = FastAPI()
    app.include_router(create_router(service, authenticate))
    if perimeter:
        from actions.server._server import _ConfiguredAPIKeyMiddleware

        app.add_middleware(
            _ConfiguredAPIKeyMiddleware,
            api_key="different-owned-admin-key",
            managed_authenticate=authenticate,
        )

        @app.get("/api/owned-admin-probe")
        def admin_probe():
            return {"admin": True}

    queue = {
        "workspace_id": scope.application.workspace_id,
        "deployment": scope.deployment.model_dump(mode="json"),
        "queue_id": reviews.queue(scope).queue_name,
    }
    return TestClient(app), identity, queue, proposal


def call(client, operation, queue, **fields):
    return client.post(
        API_PREFIX + "/operations",
        headers={"authorization": "Bearer owned-managed-key"},
        json={"operation": operation, "queue": queue, **fields},
    )


def test_real_managed_http_uses_live_sql_scope_and_trusted_worker(reviewed):
    client, identity, queue, proposal = configured(reviewed)
    bad = client.get(
        API_PREFIX + "/schema",
        headers={
            "authorization": "Bearer wrong",
            "x-actor": identity.actor.principal_id,
        },
    )
    assert bad.status_code == 401
    schema = client.get(
        API_PREFIX + "/schema", headers={"authorization": "Bearer owned-managed-key"}
    )
    assert schema.status_code == 200
    approve = call(
        client,
        "reviews.decide",
        queue,
        idempotency_key="http-approve",
        proposal=proposal.model_dump(mode="json"),
        decision="approve",
    )
    assert approve.status_code == 200, approve.text
    claimed = call(
        client, "items.claim", queue, idempotency_key="http-claim", lease_seconds=30
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["result"]["claim"]["owner_id"] == identity.worker_id
    again = call(
        client, "items.claim", queue, idempotency_key="http-claim", lease_seconds=30
    )
    assert again.status_code == 200
    assert again.json()["result"]["claim"] == claimed.json()["result"]["claim"]
    duplicate = client.get(
        API_PREFIX + "/schema",
        headers=[
            ("authorization", "Bearer owned-managed-key"),
            ("authorization", "Bearer wrong"),
        ],
    )
    assert duplicate.status_code == 401


def test_managed_worker_identity_is_not_inferred_from_headers(reviewed):
    client, identity, queue, proposal = configured(reviewed, worker=False)
    approve = call(
        client,
        "reviews.decide",
        queue,
        idempotency_key="approve",
        proposal=proposal.model_dump(mode="json"),
        decision="approve",
    )
    assert approve.status_code == 200
    denied = client.post(
        API_PREFIX + "/operations",
        headers={
            "authorization": "Bearer owned-managed-key",
            "x-worker-id": str(uuid4()),
        },
        json={
            "operation": "items.claim",
            "queue": queue,
            "idempotency_key": "no-worker",
            "lease_seconds": 30,
        },
    )
    assert denied.status_code == 403


def test_managed_sql_permission_revocation_and_cross_workspace_are_denied(reviewed):
    client, identity, queue, _ = configured(reviewed)
    denied = client.get(
        API_PREFIX + "/capabilities",
        params={"workspace_id": str(uuid4())},
        headers={"authorization": "Bearer owned-managed-key"},
    )
    assert denied.status_code == 403

    db = reviewed[0]
    with db.transaction():
        db.execute(
            "DELETE FROM foundry_access_grant WHERE principal_id=?",
            [identity.actor.principal_id],
        )
    denied = client.get(
        API_PREFIX + "/capabilities",
        params={"workspace_id": queue["workspace_id"]},
        headers={"authorization": "Bearer owned-managed-key"},
    )
    assert denied.status_code == 403


def test_managed_identity_perimeter_never_authorizes_other_runtime_apis(reviewed):
    client, _, _, _ = configured(reviewed, perimeter=True)
    assert (
        client.get(
            API_PREFIX + "/schema",
            headers={"authorization": "Bearer owned-managed-key"},
        ).status_code
        == 200
    )
    assert (
        client.get(
            API_PREFIX + "/schema", headers={"authorization": "Bearer wrong"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/owned-admin-probe",
            headers={"authorization": "Bearer owned-managed-key"},
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/owned-admin-probe",
            headers={"authorization": "Bearer different-owned-admin-key"},
        ).status_code
        == 200
    )


def test_concurrent_http_claim_delivery_preserves_one_claim_and_audit(reviewed):
    from concurrent.futures import ThreadPoolExecutor

    from actions.server.foundry.models import FoundryAudit

    client, identity, queue, proposal = configured(reviewed, perimeter=True)
    approved = call(
        client,
        "reviews.decide",
        queue,
        idempotency_key="concurrent-approve",
        proposal=proposal.model_dump(mode="json"),
        decision="approve",
    )
    assert approved.status_code == 200, approved.text
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: call(
                    client,
                    "items.claim",
                    queue,
                    idempotency_key="concurrent-claim",
                    lease_seconds=120,
                ),
                range(2),
            )
        )
    assert [response.status_code for response in responses] == [200, 200]
    assert (
        responses[0].json()["result"]["claim"] == responses[1].json()["result"]["claim"]
    )
    audits = reviewed[0].all(
        FoundryAudit,
        where="principal_id=? AND operation=?",
        values=[identity.actor.principal_id, "managed-work-items/v1/items.claim"],
    )
    assert len(audits) == 1


@pytest.mark.integration_test
def test_real_managed_completion_uses_retained_rcc_evidence(reviewed, tmp_path):
    import threading

    from action_server_tests.test_invoice_worker import worker
    from actions.work_items._fencing import WorkItemClaim

    executor, actor, scope, _ = worker(reviewed, tmp_path, real=True)
    client, _, queue, proposal = configured(reviewed, executor=executor, perimeter=True)
    approved = call(
        client,
        "reviews.decide",
        queue,
        idempotency_key="complete-approve",
        proposal=proposal.model_dump(mode="json"),
        decision="approve",
    )
    assert approved.status_code == 200, approved.text
    reserved = call(
        client,
        "items.claim",
        queue,
        idempotency_key="complete-claim",
        lease_seconds=120,
    )
    assert reserved.status_code == 200, reserved.text
    claim = reserved.json()["result"]["claim"]
    ticket = executor.dispatch(
        actor,
        proposal,
        WorkItemClaim(claim["item_id"], claim["owner_id"], claim["epoch"]),
        lease_seconds=120,
    )
    # No completion is accepted before actual execution has durable evidence.
    missing = call(
        client,
        "items.complete",
        queue,
        idempotency_key="complete-missing",
        claim=claim,
        outcome="done",
    )
    assert missing.status_code == 409, missing.text
    executor.launch(actor, ticket, threading.Event(), lease_seconds=120)
    completed = call(
        client,
        "items.complete",
        queue,
        idempotency_key="complete-rcc",
        claim=claim,
        outcome="done",
    )
    assert completed.status_code == 200, completed.text
    item = completed.json()["result"]["item"]
    assert item["queue_state"] == "DONE"
    assert ticket.fence.run_id in item["run_ids"]
    # Transport duplication returns the retained receipt without relaunching RCC.
    replay = call(
        client,
        "items.complete",
        queue,
        idempotency_key="complete-rcc",
        claim=claim,
        outcome="done",
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["result"]["item"] == completed.json()["result"]["item"]
    assert replay.json()["result"]["replay"] is True
    receipt = executor.complete(actor, ticket)
    with executor.outputs.resolve(
        actor, scope.application.workspace_id, receipt.handle, canvas_scope=scope
    ) as output:
        result = json.loads(output.read())
    assert result["task"]["invoice_count"] == 2
    assert result["task"]["total_cents"] == 12900
    assert result["rcc_receipt"]["status"] == "completed"


def test_source_run_without_native_log_outputs_returns_an_empty_page(reviewed):
    client, _, queue, proposal = configured(reviewed)
    response = call(client, "runs.logs", queue, run_id=proposal.binding.run_id)
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["run_id"] == proposal.binding.run_id
    assert result["lines"] == []
    assert result["next_cursor"] is None
