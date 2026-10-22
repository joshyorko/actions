"""Explicit exact-result review under one SQL authority, using both real providers."""

import os
import threading
import sys
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_providers as data_fixtures
from action_server_tests.run_outputs import test_service as runs
from actions.work_items import State
from actions.work_items._fencing import ClaimRejected

from actions.server._models import Run, create_db
from actions.server.data_queries.review import InvoiceReviewService, ReviewConflict
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import (
    AccessDenied,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor, CanvasResultScope, ExecutionSnapshot

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="review proof uses owned POSIX filesystem output provider",
)

provider = data_fixtures.provider
postgresql_database = data_fixtures.postgresql_database


@pytest.fixture(params=["sqlite", "postgresql"])
def reviewed(request, tmp_path, provider):
    from action_server_tests.test_database_shared import _postgresql_schema_url

    location = tmp_path / "review.db"
    if request.param == "postgresql":
        base = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
        if not base:
            if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
                pytest.fail("owned PostgreSQL control plane required")
            pytest.skip("owned PostgreSQL control plane not configured")
        import psycopg

        schema = "review_test_" + uuid4().hex
        with psycopg.connect(base, autocommit=True) as owner:
            owner.execute(f'CREATE SCHEMA "{schema}"')
        location = _postgresql_schema_url(base, schema)
    root = tmp_path / "objects"
    root.mkdir()
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with create_db(location) as db, FilesystemOutputProvider(fd) as objects:
            payload = runs.snapshot().model_dump(mode="json")
            payload["data_binding"] = {
                "provider": payload["output_provider"],
                "source_version": "sha256:" + "b" * 64,
            }
            payload["canvas_application"] = {
                "workspace_id": payload["deployment"]["workspace_id"],
                "app_id": str(uuid4()),
                "revision_id": "sha256:" + "c" * 64,
            }
            snap = ExecutionSnapshot.model_validate(payload)
            runs.insert_action(db, snap)
            control = RunOutputControlPlane(db)
            control.register(snap)
            actor = Actor(principal_id=str(uuid4()))
            control.grant(
                actor, snap.deployment, {"read", "execute", "review", "cancel"}
            )
            outputs = RunOutputService(db, {snap.provider_key: objects})
            queries = InvoiceQueryService(outputs, {snap.data_binding.key: provider})
            run = outputs.admit(actor, snap, {"min_days": 0}, "synthetic-invoice")
            handle = queries.execute(
                actor,
                outputs.claim(run.id, str(uuid4()), lease_seconds=30),
                threading.Event(),
            )
            scope = CanvasResultScope(
                deployment=snap.deployment, application=snap.canvas_application
            )
            yield (
                db,
                control,
                queries,
                InvoiceReviewService(queries),
                actor,
                scope,
                handle,
                snap,
            )
    finally:
        os.close(fd)
        if request.param == "postgresql":
            with psycopg.connect(base, autocommit=True) as owner:
                owner.execute(f'DROP SCHEMA "{schema}" CASCADE')


def test_explicit_approval_creates_one_fenced_item_after_service_restart(reviewed):
    db, _, queries, reviews, actor, scope, handle, _ = reviewed
    from actions.server.run_outputs.models import RunAttempt

    before = (len(db.all(Run)), len(db.all(RunAttempt)))
    proposal = reviews.offer(actor, scope, handle)
    assert reviews.queue(scope).list_items() == []
    receipt = reviews.decide(actor, scope, proposal, "approve")
    assert receipt.state == "approved" and receipt.work_item_id
    assert (len(db.all(Run)), len(db.all(RunAttempt))) == before
    assert (
        InvoiceReviewService(queries).decide(actor, scope, proposal, "approve")
        == receipt
    )
    queue = InvoiceReviewService(queries).queue(scope)
    assert len(queue.list_items()) == 1
    claim = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    assert claim.item_id == receipt.work_item_id and claim.epoch == 1
    assert queue.load_payload(claim.item_id)["review_id"] == proposal.review_id
    queue.finish_fenced(claim, State.DONE, outputs=({"synthetic": "receipt"},))
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(claim, State.DONE)


def test_review_requires_current_review_authority_and_exact_scope(reviewed):
    _, control, _, reviews, actor, scope, handle, snap = reviewed
    proposal = reviews.offer(actor, scope, handle)
    control.grant(actor, snap.deployment, {"read"})
    with pytest.raises(AccessDenied):
        reviews.decide(actor, scope, proposal, "approve")
    with pytest.raises(AccessDenied):
        reviews.decide(Actor(principal_id=str(uuid4())), scope, proposal, "approve")
    control.grant(actor, snap.deployment, {"read", "review", "cancel"})
    changed = scope.model_dump(mode="json")
    changed["application"]["revision_id"] = "sha256:" + "d" * 64
    with pytest.raises(AccessDenied):
        reviews.decide(
            actor, CanvasResultScope.model_validate(changed), proposal, "approve"
        )
    assert reviews.queue(scope).list_items() == []


def test_altered_result_or_input_cannot_be_approved(reviewed):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    changed = proposal.model_copy(
        update={
            "binding": proposal.binding.model_copy(
                update={"result_digest": "sha256:" + "e" * 64}
            )
        }
    )
    with pytest.raises(ReviewConflict):
        reviews.decide(actor, scope, changed, "approve")
    with db.transaction():
        db.update_by_id(Run, proposal.binding.run_id, {"inputs": '{"min_days":99}'})
    with pytest.raises(AccessDenied):
        reviews.decide(actor, scope, proposal, "approve")
    assert reviews.queue(scope).list_items() == []


def test_cancellation_fences_claim_and_never_reapproves(reviewed):
    _, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    approved = reviews.decide(actor, scope, proposal, "approve")
    queue = reviews.queue(scope)
    claim = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    cancelled = reviews.cancel(actor, scope, proposal)
    assert (
        cancelled.state == "cancelled"
        and cancelled.work_item_id == approved.work_item_id
    )
    assert reviews.cancel(actor, scope, proposal) == cancelled
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(claim, State.DONE, outputs=({"stale": True},))
    with pytest.raises(ReviewConflict):
        reviews.decide(actor, scope, proposal, "approve")
    assert len(queue.list_items()) == 1


def test_rejection_creates_no_work_item(reviewed):
    _, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    assert reviews.decide(actor, scope, proposal, "reject").state == "rejected"
    with pytest.raises(ReviewConflict):
        reviews.decide(actor, scope, proposal, "approve")
    assert reviews.queue(scope).list_items() == []


def test_pending_cancel_and_expired_result_never_approve(reviewed):
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.types import output_id_from_handle

    db, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    with db.transaction():
        db.update_by_id(RunOutput, output_id_from_handle(handle), {"expires_ms": "0"})
    with pytest.raises(AccessDenied):
        reviews.decide(actor, scope, proposal, "approve")
    assert reviews.cancel(actor, scope, proposal).state == "cancelled"
    assert reviews.queue(scope).list_items() == []


def test_approval_update_failure_rolls_back_work_item_and_decision(reviewed):
    from actions.server._database import DBError

    db, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    with db.transaction():
        if db.backend_name == "sqlite":
            db.execute(
                "CREATE TRIGGER fail_review BEFORE UPDATE ON invoice_review WHEN NEW.state='approved' BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END"
            )
        else:
            db.execute(
                "CREATE FUNCTION fail_review() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rollback'; END $$"
            )
            db.execute(
                "CREATE TRIGGER fail_review BEFORE UPDATE ON invoice_review FOR EACH ROW WHEN (NEW.state='approved') EXECUTE FUNCTION fail_review()"
            )
    with pytest.raises(DBError):
        reviews.decide(actor, scope, proposal, "approve")
    assert reviews.queue(scope).list_items() == []
    assert reviews.status(actor, scope, proposal).state == "pending"
    with db.transaction():
        db.execute(
            "DROP TRIGGER fail_review"
            + (" ON invoice_review" if db.backend_name == "postgresql" else "")
        )
    assert reviews.decide(actor, scope, proposal, "approve").work_item_id


def test_approved_receipt_survives_a_real_interpreter_restart(reviewed, tmp_path):
    import json
    import subprocess
    import sys

    db, _, _, reviews, actor, scope, handle, snap = reviewed
    proposal = reviews.offer(actor, scope, handle)
    first = reviews.decide(actor, scope, proposal, "approve")
    context = tmp_path / "restart.json"
    context.write_text(
        json.dumps(
            {
                "database": str(db.db_path),
                "objects": str(tmp_path / "objects"),
                "provider_key": snap.provider_key,
                "actor": actor.model_dump(mode="json"),
                "scope": scope.model_dump(mode="json"),
                "proposal": proposal.model_dump(mode="json"),
            }
        )
    )
    probe = """
import json,os,sys
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import Actor, CanvasResultScope
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.data_queries.review import InvoiceReviewService, ReviewProposal
data=json.load(open(sys.argv[1])); db=Database(data['database']); fd=os.open(data['objects'],os.O_RDONLY|os.O_DIRECTORY)
try:
 with db.connect(), FilesystemOutputProvider(fd) as objects:
  db.register_classes(get_all_model_classes())
  service=InvoiceReviewService(InvoiceQueryService(RunOutputService(db,{data['provider_key']:objects}),{}))
  result=service.decide(Actor.model_validate(data['actor']),CanvasResultScope.model_validate(data['scope']),ReviewProposal.model_validate(data['proposal']),'approve')
  print(result.model_dump_json())
finally: os.close(fd)
"""
    result = subprocess.run(
        [sys.executable, "-c", probe, str(context)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["work_item_id"] == first.work_item_id
    assert len(reviews.queue(scope).list_items()) == 1


def test_reclaimed_review_work_item_rejects_stale_owner_and_outputs(reviewed):
    from actions.server.data_queries.review_models import FencedWorkItem

    db, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    receipt = reviews.decide(actor, scope, proposal, "approve")
    queue = reviews.queue(scope)
    old = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    with db.transaction():
        db.update_by_id(
            FencedWorkItem, receipt.work_item_id, {"claim_deadline_ms": "0"}
        )
    current = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=30)
    assert current.epoch == old.epoch + 1
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(old, State.DONE, outputs=({"stale": True},))
    with pytest.raises(ClaimRejected):
        queue.renew_fenced(old, lease_seconds=30)
    assert db.all(FencedWorkItem, where="parent_id=?", values=[old.item_id]) == []
    queue.finish_fenced(current, State.DONE, outputs=({"current": True},))
    assert len(db.all(FencedWorkItem, where="parent_id=?", values=[old.item_id])) == 1


def test_parallel_duplicate_decisions_share_one_sql_commit(reviewed):
    from concurrent.futures import ThreadPoolExecutor
    from actions.server._database import Database
    from actions.server._models import get_all_model_classes

    db, _, queries, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    barrier = threading.Barrier(2)

    def decide():
        connection = Database(db.db_path)
        with connection.connect():
            connection.register_classes(get_all_model_classes())
            service = InvoiceReviewService(
                InvoiceQueryService(
                    RunOutputService(connection, queries.outputs.providers), {}
                )
            )
            barrier.wait(timeout=15)
            return service.decide(actor, scope, proposal, "approve")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(decide) for _ in range(2)]
        receipts = [future.result(timeout=30) for future in futures]
    assert receipts[0] == receipts[1]
    assert len(reviews.queue(scope).list_items()) == 1


@pytest.mark.parametrize(
    "change", ["workspace", "app", "deployment", "deployment_revision"]
)
def test_cross_scope_decision_cannot_enqueue(reviewed, change):
    _, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    value = scope.model_dump(mode="json")
    if change == "workspace":
        value["application"]["workspace_id"] = value["deployment"][
            "workspace_id"
        ] = str(uuid4())
    elif change == "app":
        value["application"]["app_id"] = str(uuid4())
    elif change == "deployment":
        value["deployment"]["deployment_id"] = str(uuid4())
    else:
        value["deployment"]["revision_id"] = "sha256:" + "e" * 64
    with pytest.raises(AccessDenied):
        reviews.decide(
            actor, CanvasResultScope.model_validate(value), proposal, "approve"
        )
    assert reviews.queue(scope).list_items() == []


def test_replay_after_expiry_requires_current_authority(reviewed):
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.types import output_id_from_handle

    db, control, _, reviews, actor, scope, handle, snap = reviewed
    proposal = reviews.offer(actor, scope, handle)
    receipt = reviews.decide(actor, scope, proposal, "approve")
    with db.transaction():
        db.update_by_id(RunOutput, output_id_from_handle(handle), {"expires_ms": "0"})
    assert reviews.decide(actor, scope, proposal, "approve") == receipt
    control.grant(actor, snap.deployment, {"read"})
    with pytest.raises(AccessDenied):
        reviews.decide(actor, scope, proposal, "approve")
    assert len(reviews.queue(scope).list_items()) == 1


def test_expiry_during_output_insert_rolls_back_entire_publication(reviewed):
    from actions.server.data_queries.review_models import FencedWorkItem

    db, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    queue = reviews.queue(scope)
    claim = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    with db.transaction():
        if db.backend_name == "sqlite":
            db.execute(
                "CREATE TRIGGER expire_review_output AFTER INSERT ON fenced_work_item WHEN NEW.parent_id <> '' BEGIN UPDATE fenced_work_item SET claim_deadline_ms=0 WHERE id=NEW.parent_id; END"
            )
        else:
            db.execute(
                "CREATE FUNCTION expire_review_output() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN UPDATE fenced_work_item SET claim_deadline_ms=0 WHERE id=NEW.parent_id; RETURN NEW; END $$"
            )
            db.execute(
                "CREATE TRIGGER expire_review_output AFTER INSERT ON fenced_work_item FOR EACH ROW WHEN (NEW.parent_id <> '') EXECUTE FUNCTION expire_review_output()"
            )
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(claim, State.DONE, outputs=({"rolled_back": True},))
    assert db.all(FencedWorkItem, where="parent_id=?", values=[claim.item_id]) == []
    assert queue.list_items()[0]["state"] == State.IN_PROGRESS.value
    queue.renew_fenced(claim, lease_seconds=30)


def test_unknown_review_row_format_fails_closed(reviewed):
    from actions.server.data_queries.review_models import FencedWorkItem

    db, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    receipt = reviews.decide(actor, scope, proposal, "approve")
    with db.transaction():
        db.update_by_id(FencedWorkItem, receipt.work_item_id, {"format": "future/v999"})
    with pytest.raises(ValueError, match="unknown review Work Item format"):
        reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=30)
    assert db.all(FencedWorkItem)[0].claim_epoch == 0
