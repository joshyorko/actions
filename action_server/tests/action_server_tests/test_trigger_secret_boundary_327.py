"""Focused public webhook and trigger-secret authorization boundaries."""

import hashlib
import hmac

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

API_KEY = "owned-trigger-boundary-key"
TRIGGER_ID = "owned-webhook-trigger"
WEBHOOK_SECRET = "owned-webhook-signing-secret"
PAYLOAD = {"probe": "owned-fixture"}


@pytest.fixture
def trigger_runtime(monkeypatch, tmp_path):
    from actions.server import _models, _triggers
    from actions.server._api_triggers import (
        public_triggers_api_router,
        triggers_api_router,
    )
    from actions.server._models import Trigger, create_db
    from actions.server._server import _ConfiguredAPIKeyMiddleware
    from actions.server._triggers import TriggerEngine

    app = FastAPI()
    app.include_router(triggers_api_router)
    app.include_router(public_triggers_api_router)
    app.add_middleware(_ConfiguredAPIKeyMiddleware, api_key=API_KEY)
    engine = TriggerEngine()
    monkeypatch.setattr(_triggers, "get_trigger_engine", lambda: engine)
    dispatched = []

    async def create_work_item(trigger, inputs):
        dispatched.append((trigger.id, inputs))
        return "owned-work-item"

    monkeypatch.setattr(engine, "_create_work_item", create_work_item)

    trigger = Trigger(
        id=TRIGGER_ID,
        name="owned webhook",
        description=None,
        action_id=None,
        execution_mode="work_item",
        work_item_queue="owned-queue",
        inputs_template_json="{}",
        trigger_type="webhook",
        webhook_secret=WEBHOOK_SECRET,
        webhook_method="POST",
        enabled=True,
        created_at="2026-10-26T00:00:00+00:00",
        updated_at="2026-10-26T00:00:00+00:00",
        last_triggered_at=None,
        trigger_count=0,
        rate_limit_enabled=False,
        rate_limit_max_per_minute=60,
    )

    with create_db(tmp_path / "triggers.sqlite") as db:
        with db.transaction():
            db.insert(trigger)
        with TestClient(app) as client:
            yield {
                "client": client,
                "db": db,
                "models": _models,
                "engine": engine,
                "trigger": trigger,
                "dispatched": dispatched,
            }


def _signature(secret: str, payload: dict[str, str]) -> str:
    import json

    raw_payload = json.dumps(payload, separators=(",", ":")).encode()
    return (
        "sha256=" + hmac.new(secret.encode(), raw_payload, hashlib.sha256).hexdigest()
    )


def _trigger(runtime):
    from actions.server._models import Trigger

    return runtime["db"].first(
        Trigger, "SELECT * FROM trigger WHERE id = ?", [TRIGGER_ID]
    )


def _invocations(runtime):
    from actions.server._models import TriggerInvocation

    return runtime["db"].select(
        TriggerInvocation,
        "SELECT * FROM trigger_invocation WHERE trigger_id = ? ORDER BY invoked_at",
        [TRIGGER_ID],
    )


@pytest.mark.parametrize("method", ["POST", "PUT"])
@pytest.mark.parametrize("signature", [None, "sha256=wrong"])
def test_public_webhook_rejects_missing_or_wrong_nonempty_secret_without_dispatch(
    trigger_runtime, method, signature
):
    runtime = trigger_runtime
    headers = {} if signature is None else {"X-Webhook-Signature": signature}

    response = runtime["client"].request(
        method,
        f"/api/triggers/webhook/{TRIGGER_ID}",
        json=PAYLOAD,
        headers=headers,
    )

    assert response.status_code == 401, response.text
    assert runtime["dispatched"] == []
    trigger = _trigger(runtime)
    assert trigger.trigger_count == 0
    assert trigger.last_triggered_at is None
    invocations = _invocations(runtime)
    assert len(invocations) == 1
    assert invocations[0].status == "rejected"
    assert invocations[0].error_message == "Invalid signature"
    assert invocations[0].run_id is None
    assert invocations[0].work_item_id is None


@pytest.mark.parametrize("method", ["POST", "PUT"])
def test_public_webhook_valid_nonempty_secret_dispatches_once(trigger_runtime, method):
    runtime = trigger_runtime

    response = runtime["client"].request(
        method,
        f"/api/triggers/webhook/{TRIGGER_ID}",
        json=PAYLOAD,
        headers={"X-Webhook-Signature": _signature(WEBHOOK_SECRET, PAYLOAD)},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"
    assert response.json()["work_item_id"] == "owned-work-item"
    assert len(runtime["dispatched"]) == 1
    dispatched_trigger_id, dispatched_inputs = runtime["dispatched"][0]
    assert dispatched_trigger_id == TRIGGER_ID
    assert dispatched_inputs == {}
    trigger = _trigger(runtime)
    assert trigger.trigger_count == 1
    assert trigger.last_triggered_at is not None
    invocations = _invocations(runtime)
    assert len(invocations) == 1
    assert invocations[0].status == "accepted"
    assert invocations[0].work_item_id == "owned-work-item"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", f"/api/triggers/{TRIGGER_ID}/secret"),
        ("POST", f"/api/triggers/{TRIGGER_ID}/regenerate-secret"),
    ],
)
@pytest.mark.parametrize("credential", [None, "Bearer wrong"])
def test_trigger_secret_read_and_rotation_reject_before_database_or_secret_access(
    trigger_runtime, monkeypatch, method, path, credential
):
    runtime = trigger_runtime
    database_accesses = []
    engine_accesses = []
    original_get_db = runtime["models"].get_db

    def observed_get_db():
        database_accesses.append(True)
        return original_get_db()

    original_get_engine = runtime["engine"].generate_webhook_secret

    def observed_generate_secret(*args, **kwargs):
        engine_accesses.append(True)
        return original_get_engine(*args, **kwargs)

    monkeypatch.setattr(runtime["models"], "get_db", observed_get_db)
    monkeypatch.setattr(
        runtime["engine"], "generate_webhook_secret", observed_generate_secret
    )
    before = _trigger(runtime)
    headers = {} if credential is None else {"Authorization": credential}

    response = runtime["client"].request(method, path, headers=headers)

    assert response.status_code == 403
    assert database_accesses == []
    assert engine_accesses == []
    after = _trigger(runtime)
    assert after.webhook_secret == before.webhook_secret == WEBHOOK_SECRET
    assert after.trigger_count == before.trigger_count == 0
    assert after.updated_at == before.updated_at
