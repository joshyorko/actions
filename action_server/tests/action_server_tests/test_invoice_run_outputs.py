"""Typed invoice data uses existing Run pins, grants, fences and sealed outputs."""

import json
import os
import sys
import threading
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_providers as data_fixtures
from action_server_tests.run_outputs import test_service as run_fixtures
from action_server_tests.run_outputs.test_service import publish
from pydantic import ValidationError

from actions.server._database import Database
from actions.server._models import Run, RunStatus, get_all_model_classes
from actions.server.data_queries.invoices import InvoiceQuery, QueryRejected
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.models import RunAdmission, RunAttempt
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor, ExecutionSnapshot

store = run_fixtures.store
provider = data_fixtures.provider
postgresql_database = data_fixtures.postgresql_database

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux sealed output-provider proof"
)


def test_query_output_survives_new_database_and_provider_instances(store, provider):
    db, _, outputs, _, actor, _, root = store
    service, snap, run = bound(store, provider)
    handle = service.execute(
        actor, outputs.claim(run.id, str(uuid4()), lease_seconds=30), threading.Event()
    )
    fresh = Database(db.db_path)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with fresh.connect(), FilesystemOutputProvider(fd) as objects:
            fresh.initialize(get_all_model_classes())
            reopened = InvoiceQueryService(
                RunOutputService(fresh, {snap.provider_key: objects}), {}
            )
            assert [
                row.invoice_id
                for row in reopened.page(
                    actor, snap.workspace_id, handle, offset=0, limit=100
                )
            ] == ["inv-001", "inv-002"]
    finally:
        os.close(fd)


def bound(store, provider):
    db, control, outputs, snap, actor, *_ = store
    payload = snap.model_dump(mode="json")
    payload["deployment"]["revision_id"] = "sha256:" + "a" * 64
    payload["data_binding"] = {
        "provider": payload["output_provider"],
        "source_version": "sha256:" + "b" * 64,
        "limits": {"max_rows": 100, "max_bytes": 4096, "timeout_ms": 5000},
    }
    snap = ExecutionSnapshot.model_validate(payload)
    control.register(snap)
    service = InvoiceQueryService(outputs, {snap.data_binding.key: provider})
    run = outputs.admit(actor, snap, {"min_days": 0}, "invoice-one")
    return service, snap, run


def test_real_query_materializes_pages_and_exports_after_reopen(store, provider):
    db, _, outputs, _, actor, output_provider, _ = store
    service, snap, run = bound(store, provider)
    fence = outputs.claim(run.id, str(uuid4()), lease_seconds=30)
    handle = service.execute(actor, fence, threading.Event())
    persisted = db.first(Run, "SELECT * FROM run WHERE id=?", [run.id])
    assert persisted.status == RunStatus.PASSED
    result = json.loads(persisted.result)["result"]
    assert result["operation"] == "invoices.overdue/v1"
    assert result["row_count"] == 2
    assert result["provider_kind"] == provider.kind
    assert result["source_version"] == snap.data_binding.source_version
    assert "rows" not in result
    # Reconstruct services without any query/provider registry or old result cache.
    reopened = InvoiceQueryService(
        RunOutputService(db, {snap.provider_key: output_provider}), {}
    )
    assert (
        reopened.page(actor, snap.workspace_id, handle, offset=0, limit=1)[0].invoice_id
        == "inv-001"
    )
    assert (
        reopened.page(actor, snap.workspace_id, handle, offset=1, limit=1)[0].invoice_id
        == "inv-002"
    )
    assert reopened.page(actor, snap.workspace_id, handle, offset=2, limit=1) == []
    with reopened.outputs.resolve(actor, snap.workspace_id, handle) as exported:
        rows = [json.loads(line) for line in exported.read().splitlines()]
        assert rows[0]["amount_cents"] == 12500
        assert len(rows) == 2
    with pytest.raises(AccessDenied):
        reopened.page(
            Actor(principal_id=str(uuid4())),
            snap.workspace_id,
            handle,
            offset=0,
            limit=1,
        )
    with pytest.raises(AccessDenied):
        reopened.page(actor, str(uuid4()), handle, offset=0, limit=1)


def test_denied_actor_cannot_execute_bound_query(store, provider):
    _, _, outputs, _, _, *_ = store
    service, _, run = bound(store, provider)
    fence = outputs.claim(run.id, str(uuid4()), lease_seconds=30)
    with pytest.raises(AccessDenied):
        service.execute(Actor(principal_id=str(uuid4())), fence, threading.Event())


def test_binding_is_immutable_and_missing_pinned_provider_never_falls_back(
    store, provider
):
    _, control, outputs, _, actor, *_ = store
    service, snap, run = bound(store, provider)
    changed = snap.model_dump(mode="json")
    changed["data_binding"]["source_version"] = "sha256:" + "c" * 64
    with pytest.raises(ValueError, match="immutable"):
        control.register(ExecutionSnapshot.model_validate(changed))
    fence = outputs.claim(run.id, str(uuid4()), lease_seconds=30)
    unavailable = InvoiceQueryService(outputs, {})
    with pytest.raises(AccessDenied):
        unavailable.execute(actor, fence, threading.Event())
    assert service.outputs is outputs


def test_replacement_owner_rejects_old_query_before_publication(store, provider):
    db, control, outputs, _, actor, *_ = store
    service, _, run = bound(store, provider)
    old = outputs.claim(run.id, str(uuid4()), lease_seconds=30)
    with db.transaction():
        db.update_by_id(RunAttempt, old.attempt_id, {"lease_deadline_ms": "0"})
    control.authorize_recovery(run.id, old.epoch, receipt="no-effect/read-only-query")
    new = outputs.claim(run.id, str(uuid4()), lease_seconds=30)
    assert new.epoch > old.epoch
    with pytest.raises(FenceRejected):
        service.execute(actor, old, threading.Event())
    assert service.execute(actor, new, threading.Event()).startswith("art_")


def test_legacy_admission_keeps_original_canonical_snapshot(store):
    db, _, outputs, snap, actor, *_ = store
    run = outputs.admit(actor, snap, {"query": "legacy"}, "legacy")
    assert "data_binding" not in json.loads(db.first(RunAdmission).snapshot_json)
    assert "canvas_application" not in json.loads(db.first(RunAdmission).snapshot_json)
    assert outputs.claim(run.id, str(uuid4()), lease_seconds=30).epoch == 1


def test_cross_workspace_binding_is_invalid(store):
    *_, snap, actor, provider, root = store
    payload = snap.model_dump(mode="json")
    payload["data_binding"] = {
        "provider": payload["output_provider"],
        "source_version": "sha256:" + "b" * 64,
    }
    payload["data_binding"]["provider"]["workspace_id"] = str(uuid4())
    with pytest.raises(ValidationError):
        ExecutionSnapshot.model_validate(payload)


def test_constructed_query_is_revalidated_before_provider_access(tmp_path):
    from actions.server.data_queries.invoices import DuckDBInvoices, InvoiceLimits

    invalid = InvoiceQuery.model_construct(min_days=-1)
    with pytest.raises(ValidationError):
        with DuckDBInvoices(tmp_path / "absent").query(
            invalid, InvoiceLimits(), threading.Event()
        ):
            pytest.fail("invalid constructed query was admitted")


def test_paging_rejects_an_authorized_non_invoice_output(store):
    _, _, outputs, snap, actor, *_ = store
    _, _, output = publish(
        store,
        body=b'{"invoice_id":"one","customer":"x","amount_cents":1,"days_overdue":2}\n',
    )
    with pytest.raises(QueryRejected, match="not an invoice"):
        InvoiceQueryService(outputs, {}).page(
            actor, snap.workspace_id, output.handle, offset=0, limit=1
        )
