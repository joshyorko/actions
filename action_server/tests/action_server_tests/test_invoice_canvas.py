"""Real query/output bytes constrained to a pinned Canvas application revision."""

import json
import os
import sys
import threading
from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest
from action_server_tests.run_outputs import test_transport as transport_fixtures
from pydantic import ValidationError

from actions.server.data_queries.canvas import InvoiceCanvasFacade
from actions.server.data_queries.invoices import DuckDBInvoices
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.run_outputs.service import AccessDenied
from actions.server.run_outputs.transport import RunOutputTransport
from actions.server.run_outputs.types import CanvasResultScope, ExecutionSnapshot

store = transport_fixtures.store
runtime = transport_fixtures.runtime
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux sealed output proof"
)


def published(store, tmp_path):
    if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
        import duckdb
    else:
        duckdb = pytest.importorskip(
            "duckdb", reason="install Runtime data-duckdb extra"
        )

    _, control, outputs, snap, actor, *_ = store
    source = tmp_path / "invoice-source.duckdb"
    with duckdb.connect(str(source), config={"threads": 1}) as conn:
        conn.execute(
            "CREATE TABLE invoices(invoice_id VARCHAR, customer VARCHAR, amount_cents BIGINT, days_overdue INTEGER)"
        )
        conn.execute(
            "INSERT INTO invoices VALUES ('one','Synthetic A',1200,45),('two','Synthetic B',900,32)"
        )
    payload = snap.model_dump(mode="json")
    payload["deployment"]["revision_id"] = "sha256:" + "a" * 64
    payload["data_binding"] = {
        "provider": payload["output_provider"],
        "source_version": "sha256:" + "b" * 64,
    }
    payload["canvas_application"] = {
        "workspace_id": snap.workspace_id,
        "app_id": str(uuid4()),
        "revision_id": "sha256:" + "c" * 64,
    }
    snap = ExecutionSnapshot.model_validate(payload)
    control.register(snap)
    queries = InvoiceQueryService(
        outputs, {snap.data_binding.key: DuckDBInvoices(source)}
    )
    run = outputs.admit(actor, snap, {"min_days": 30}, "canvas-invoice")
    handle = queries.execute(
        actor, outputs.claim(run.id, str(uuid4()), lease_seconds=30), threading.Event()
    )
    scope = CanvasResultScope(
        deployment=snap.deployment, application=snap.canvas_application
    )
    return queries, scope, handle, snap


def test_canvas_page_and_export_use_same_authorized_real_result(store, tmp_path):
    *_, actor, provider, root = store
    queries, scope, handle, _ = published(store, tmp_path)
    facade = InvoiceCanvasFacade(queries, scope)
    result = facade.page(actor, handle, offset=0, limit=1)
    assert result == {
        "rows": [
            {
                "invoice_id": "one",
                "customer": "Synthetic A",
                "amount_cents": 1200,
                "days_overdue": 45,
            }
        ],
        "artifact": {"handle": handle},
        "error": None,
    }
    assert (
        facade.page(actor, handle, offset=1, limit=1)["rows"][0]["invoice_id"] == "two"
    )
    with facade.export(actor, handle) as output:
        assert output.media_type == "application/x-ndjson"
        assert len([json.loads(line) for line in output.read().splitlines()]) == 2


def test_canvas_facade_keeps_its_registered_scope_immutable(store, tmp_path):
    queries, scope, _, _ = published(store, tmp_path)
    facade = InvoiceCanvasFacade(queries, scope)
    with pytest.raises(FrozenInstanceError):
        facade.scope = None


@pytest.mark.parametrize(
    "field", ["app_id", "application_revision", "deployment_revision"]
)
def test_canvas_scope_substitution_denied_before_provider_open(
    store, tmp_path, monkeypatch, field
):
    *_, actor, provider, root = store
    queries, scope, handle, _ = published(store, tmp_path)
    payload = scope.model_dump(mode="json")
    if field == "app_id":
        payload["application"]["app_id"] = str(uuid4())
    elif field == "application_revision":
        payload["application"]["revision_id"] = "sha256:" + "d" * 64
    else:
        payload["deployment"]["revision_id"] = "sha256:" + "d" * 64

    def forbidden(*args):
        pytest.fail("wrong Canvas scope reached provider")

    monkeypatch.setattr(provider, "open", forbidden)
    facade = InvoiceCanvasFacade(queries, CanvasResultScope.model_validate(payload))
    with pytest.raises(AccessDenied):
        facade.page(actor, handle, offset=0, limit=1)
    with pytest.raises(AccessDenied):
        with facade.export(actor, handle):
            pytest.fail("wrong scope exported bytes")


def test_canvas_scope_does_not_replace_current_actor_grants(
    store, tmp_path, monkeypatch
):
    _, control, _, _, actor, provider, _ = store
    queries, scope, handle, snap = published(store, tmp_path)
    control.revoke(actor, snap.deployment)

    def forbidden(*args):
        pytest.fail("revoked actor reached provider")

    monkeypatch.setattr(provider, "open", forbidden)
    with pytest.raises(AccessDenied):
        InvoiceCanvasFacade(queries, scope).page(actor, handle, offset=0, limit=1)


def test_canvas_reference_requires_same_workspace_and_immutable_admission(
    store, tmp_path
):
    _, control, *_ = store
    _, scope, _, snap = published(store, tmp_path)
    payload = scope.model_dump(mode="json")
    payload["application"]["workspace_id"] = str(uuid4())
    with pytest.raises(ValidationError):
        CanvasResultScope.model_validate(payload)
    changed = snap.model_dump(mode="json")
    changed["canvas_application"]["revision_id"] = "sha256:" + "d" * 64
    with pytest.raises(ValueError, match="immutable"):
        control.register(ExecutionSnapshot.model_validate(changed))


def test_existing_runtime_download_enforces_server_canvas_scope(runtime, tmp_path):
    _, _, outputs, _, actor, *_ = runtime.store
    queries, scope, handle, snap = published(runtime.store, tmp_path)
    config = RunOutputTransport(
        outputs, runtime.config.authenticate, canvas_scope=scope
    )
    client = runtime.build(custom_config=config)
    path = f"/api/workspaces/{snap.workspace_id}/outputs/{handle}"
    response = runtime.request(
        "GET",
        path=path,
        client=client,
        headers=transport_fixtures.AUTHORIZED,
        expected_counts=(1, 1, 1),
    )
    assert response.status_code == 200
    assert len(response.content.splitlines()) == 2
    assert response.headers["cache-control"] == "no-store"
    # An authorized legacy handle has no application pin and cannot fall back.
    response = runtime.request(
        "GET",
        client=client,
        headers={**transport_fixtures.AUTHORIZED, "X-App-ID": scope.application.app_id},
        expected_counts=(1, 0, 0),
    )
    assert response.status_code == 404
