"""Owned synthetic effect reconciliation, never a third-party effect or scheduler."""

import json
import sqlite3
import subprocess
import sys
import threading
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_worker as fixtures

from actions.server._models import Run, RunStatus
from actions.server.run_outputs.models import RunAttempt

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
retain_worker_cell = fixtures.retain_worker_cell
pytestmark = fixtures.pytestmark


@pytest.fixture(autouse=True)
def retain_effect_target(tmp_path, retain_worker_cell):
    yield
    target = tmp_path / "target.db"
    if target.is_file() and (tmp_path / "execution").is_dir():
        with sqlite3.connect(target) as db:
            audit = {
                table: db.execute("SELECT * FROM " + table).fetchall()
                for table in ("target", "delivery", "effect", "closed")
            }
        (tmp_path / "execution/effect-target.json").write_text(
            json.dumps(audit, indent=2) + "\n"
        )


def effect_worker(reviewed, tmp_path, *, real=False, max_attempts=2, idempotent=True):
    from actions.server.data_queries.invoice_effects import SyntheticEffectPolicy

    policy = SyntheticEffectPolicy(
        target_id=str(uuid4()), max_attempts=max_attempts, idempotent=idempotent
    )
    return fixtures.worker(reviewed, tmp_path, real=real, effect_policy=policy)


def test_pre_effect_retries_exhaust_to_one_audited_scoped_dead_letter(
    reviewed, tmp_path
):
    from actions.server.data_queries.invoice_worker import WorkerReceipt, WorkerTicket
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import AccessDenied
    from actions.server.run_outputs.types import Actor

    worker, actor, scope, handle = effect_worker(reviewed, tmp_path)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    first = worker.dispatch(actor, proposal, claim, lease_seconds=120)
    newer = fixtures.expired_claim(reviewed, first)
    second = worker.reconcile(actor, proposal, newer, lease_seconds=120)
    assert isinstance(second, WorkerTicket)
    assert second.fence.run_id == first.fence.run_id
    assert second.fence.attempt_id != first.fence.attempt_id
    final_claim = fixtures.expired_claim(reviewed, second)
    dead = worker.reconcile(actor, proposal, final_claim, lease_seconds=120)
    assert isinstance(dead, WorkerReceipt)
    assert dead.disposition == "dead_letter"
    assert worker.reconcile(actor, proposal, final_claim, lease_seconds=120) == dead
    run = db.first(Run, "SELECT * FROM run WHERE id=?", [dead.run_id])
    item = db.first(
        FencedWorkItem, "SELECT * FROM fenced_work_item WHERE id=?", [claim.item_id]
    )
    assert run.status == RunStatus.FAILED and item.state == "FAILED"
    assert len(db.all(Run)) == 2  # original query plus the single logical worker Run
    assert len(db.all(RunAttempt, where="run_id=?", values=[dead.run_id])) == 3
    status = reviews.execution(actor, scope, proposal)
    assert status.phase == "dead_letter" and status.artifact.handle == dead.handle
    with worker.outputs.resolve(
        actor, scope.application.workspace_id, dead.handle, canvas_scope=scope
    ) as output:
        failure = json.loads(output.read())
    assert failure["disposition"] == "dead_letter"
    assert [event["disposition"] for event in failure["reconciliations"]] == [
        "no-effect-intent",
        "bounded-retry-exhausted",
    ]
    assert failure["proposal"] == proposal.model_dump(mode="json")
    with pytest.raises(AccessDenied):
        with worker.outputs.resolve(
            Actor(principal_id=str(uuid4())),
            scope.application.workspace_id,
            dead.handle,
        ):
            pass
    assert not worker.execution_root.exists()  # no RCC or target effect admitted


def ready_effect(reviewed, tmp_path, *, idempotent=True, fault=None, max_attempts=2):
    from action_server_tests.invoice_effect_fixture import OwnedEffectTarget

    worker, actor, scope, handle = effect_worker(
        reviewed, tmp_path, real=True, idempotent=idempotent, max_attempts=max_attempts
    )
    worker.effect_target = OwnedEffectTarget(
        tmp_path / "target.db",
        worker.plan.effect_policy.target_id,
        idempotent=idempotent,
        fault=fault,
    )
    reviews = reviewed[3]
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    ticket = worker.dispatch(actor, proposal, claim, lease_seconds=120)
    worker.launch(actor, ticket, threading.Event(), lease_seconds=120)
    assert worker.effect_target.counts() == (0, 0)
    return worker, actor, ticket


@pytest.mark.integration_test
def test_explicit_effect_and_terminal_delivery_reuse_one_durable_target_receipt(
    reviewed, tmp_path
):
    from actions.server.data_queries.review import ReviewConflict

    worker, actor, ticket = ready_effect(reviewed, tmp_path)
    with pytest.raises(ReviewConflict, match="effect"):
        worker.complete(actor, ticket)
    effect = worker.apply_effect(actor, ticket)
    assert effect.request.proposal == ticket.proposal
    assert effect.request.work_item_id == ticket.claim.item_id
    assert worker.apply_effect(actor, ticket) == effect
    receipt = worker.complete(actor, ticket)
    assert receipt.disposition == "completed"
    assert worker.complete(actor, ticket) == receipt
    assert worker.effect_target.counts() == (1, 1)
    with worker.outputs.resolve(
        actor,
        worker.scope.application.workspace_id,
        receipt.handle,
        canvas_scope=worker.scope,
    ) as output:
        result = json.loads(output.read())
    assert result["effect_receipt"] == effect.model_dump(mode="json")


@pytest.mark.integration_test
def test_idempotent_absent_effect_retries_with_same_key_without_rerunning_rcc(
    reviewed, tmp_path
):
    from actions.server.data_queries.invoice_effects import EffectUncertain
    from actions.server.data_queries.invoice_worker import WorkerTicket

    worker, actor, ticket = ready_effect(reviewed, tmp_path, fault="before_effect")
    with pytest.raises(EffectUncertain):
        worker.apply_effect(actor, ticket)
    prior = json.loads(
        reviewed[0]
        .first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id])
        .result
    )
    key = prior["effect"]["request"]["effect_key"]
    newer = fixtures.expired_claim(reviewed, ticket)
    recovered = worker.reconcile(actor, ticket.proposal, newer, lease_seconds=120)
    assert isinstance(recovered, WorkerTicket)
    worker.effect_target.fault = None
    effect = worker.apply_effect(actor, recovered)
    assert effect.request.effect_key == key
    receipt = worker.complete(actor, recovered)
    assert receipt.run_id == ticket.fence.run_id
    assert worker.effect_target.counts() == (2, 1)
    assert len(list(worker.execution_root.glob("*/*/*/rcc.json"))) == 1
    with worker.outputs.resolve(
        actor, worker.scope.application.workspace_id, receipt.handle
    ) as output:
        artifact = json.loads(output.read())
    assert artifact["task"]["fence"] == ticket.fence.model_dump()


@pytest.mark.integration_test
def test_lost_ack_is_observed_and_published_without_redelivery_even_at_budget(
    reviewed, tmp_path
):
    from actions.server.data_queries.invoice_effects import EffectUncertain
    from actions.server.data_queries.invoice_worker import WorkerReceipt

    worker, actor, ticket = ready_effect(
        reviewed, tmp_path, fault="lost_ack", max_attempts=1
    )
    with pytest.raises(EffectUncertain):
        worker.apply_effect(actor, ticket)
    assert worker.effect_target.counts() == (1, 1)
    newer = fixtures.expired_claim(reviewed, ticket)
    receipt = worker.reconcile(actor, ticket.proposal, newer, lease_seconds=120)
    assert isinstance(receipt, WorkerReceipt) and receipt.disposition == "completed"
    assert worker.effect_target.counts() == (1, 1)
    run = reviewed[0].first(Run, "SELECT * FROM run WHERE id=?", [receipt.run_id])
    result = json.loads(run.result)["result"]
    assert result["executed_fence"] == ticket.fence.model_dump()
    assert result["publication_fence"]["epoch"] == ticket.fence.epoch + 1
    assert (
        result["reconciliations"][-1]["disposition"] == "observed-applied-no-redelivery"
    )


@pytest.mark.integration_test
def test_unknown_or_nonidempotent_absent_effect_stays_blocked_before_exhaustion(
    reviewed, tmp_path
):
    from actions.server.data_queries.invoice_effects import EffectUncertain

    worker, actor, ticket = ready_effect(
        reviewed, tmp_path, idempotent=False, fault="before_effect", max_attempts=1
    )
    with pytest.raises(EffectUncertain):
        worker.apply_effect(actor, ticket)
    newer = fixtures.expired_claim(reviewed, ticket)
    for fault in ("unavailable", None):
        worker.effect_target.fault = fault
        with pytest.raises(EffectUncertain):
            worker.reconcile(actor, ticket.proposal, newer, lease_seconds=120)
        assert (
            worker.reviews.execution(actor, worker.scope, ticket.proposal).phase
            == "blocked"
        )
    assert worker.effect_target.counts() == (1, 0)
    run = reviewed[0].first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id])
    assert run.status == RunStatus.RUNNING
    assert len(reviewed[0].all(RunAttempt, where="run_id=?", values=[run.id])) == 1


@pytest.mark.integration_test
def test_proven_safe_retry_exhaustion_preserves_failure_artifact_and_effect_audit(
    reviewed, tmp_path
):
    from actions.server.data_queries.invoice_effects import EffectUncertain

    worker, actor, first = ready_effect(reviewed, tmp_path, fault="before_effect")
    with pytest.raises(EffectUncertain):
        worker.apply_effect(actor, first)
    second = worker.reconcile(
        actor,
        first.proposal,
        fixtures.expired_claim(reviewed, first),
        lease_seconds=120,
    )
    with pytest.raises(EffectUncertain):
        worker.apply_effect(actor, second)
    dead = worker.reconcile(
        actor,
        second.proposal,
        fixtures.expired_claim(reviewed, second),
        lease_seconds=120,
    )
    assert dead.disposition == "dead_letter" and worker.effect_target.counts() == (2, 0)
    with worker.outputs.resolve(
        actor, worker.scope.application.workspace_id, dead.handle
    ) as output:
        failure = json.loads(output.read())
    assert failure["effect_observation"]["state"] == "closed_absent"
    assert failure["effect_observation"]["barrier_id"].startswith("sha256:")
    assert failure["executions"] == 2
    assert failure["effect_request"]["proposal"] == first.proposal.model_dump(
        mode="json"
    )


@pytest.mark.integration_test
def test_inflight_old_owner_and_retry_share_one_conditional_effect_key(
    reviewed, tmp_path
):
    from actions.work_items._fencing import ClaimRejected

    from actions.server.run_outputs.service import FenceRejected

    entered, release = threading.Event(), threading.Event()

    def pause():
        entered.set()
        assert release.wait(30)

    worker, actor, first = ready_effect(reviewed, tmp_path, fault=pause)
    failures = []

    def old_delivery():
        try:
            with worker.db.connect():
                worker.apply_effect(actor, first)
        except Exception as exc:
            failures.append(exc)

    thread = threading.Thread(target=old_delivery)
    thread.start()
    try:
        assert entered.wait(15)
        newer = fixtures.expired_claim(reviewed, first)
        second = worker.reconcile(actor, first.proposal, newer, lease_seconds=120)
        worker.effect_target.fault = None
        worker.apply_effect(actor, second)
        result = worker.complete(actor, second)
    finally:
        release.set()
        thread.join(15)
    assert not thread.is_alive() and len(failures) == 1
    assert isinstance(failures[0], (ClaimRejected, FenceRejected))
    assert worker.effect_target.counts() == (2, 1)
    assert worker.complete(actor, second) == result


@pytest.mark.integration_test
@pytest.mark.parametrize(
    "change", ["revoked", "stale_claim", "cancelled", "policy", "target"]
)
def test_denied_effect_entry_never_reaches_the_owned_target(reviewed, tmp_path, change):
    from dataclasses import replace

    from actions.work_items._fencing import ClaimRejected

    from actions.server.data_queries.invoice_effects import SyntheticEffectPolicy
    from actions.server.data_queries.review import ReviewConflict
    from actions.server.run_outputs.service import AccessDenied, FenceRejected

    worker, actor, ticket = ready_effect(reviewed, tmp_path)
    if change == "revoked":
        reviewed[1].revoke(actor, worker.scope.deployment)
    elif change == "stale_claim":
        fixtures.expired_claim(reviewed, ticket)
    elif change == "cancelled":
        worker.reviews.cancel(actor, worker.scope, ticket.proposal)
    elif change == "policy":
        policy = worker.plan.effect_policy.model_dump(mode="json")
        policy["max_attempts"] += 1
        worker.plan = replace(
            worker.plan, effect_policy=SyntheticEffectPolicy.model_validate(policy)
        )
    else:
        worker.effect_target.target_id = str(uuid4())
    with pytest.raises((AccessDenied, FenceRejected, ClaimRejected, ReviewConflict)):
        worker.apply_effect(actor, ticket)
    assert worker.effect_target.counts() == (0, 0)


@pytest.mark.integration_test
def test_cancellation_during_admitted_effect_retains_outcome_and_prevents_publication(
    reviewed, tmp_path
):
    from actions.work_items._fencing import ClaimRejected

    from actions.server.data_queries.review import ReviewConflict
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import AccessDenied, FenceRejected

    worker, actor, ticket = ready_effect(reviewed, tmp_path)
    worker.effect_target.fault = lambda: worker.reviews.cancel(
        actor, worker.scope, ticket.proposal
    )
    with pytest.raises((AccessDenied, FenceRejected, ClaimRejected, ReviewConflict)):
        worker.apply_effect(actor, ticket)
    assert worker.effect_target.counts() == (
        1,
        1,
    )  # admission cannot undo a committed external effect
    with pytest.raises(ReviewConflict):
        worker.complete(actor, ticket)
    assert (
        reviewed[0].all(
            RunOutput, where="run_id=? AND state='final'", values=[ticket.fence.run_id]
        )
        == []
    )
    assert (
        worker.reviews.execution(actor, worker.scope, ticket.proposal).phase
        == "cancelled"
    )


EFFECT_CONTROLLER = """
import json,os,sys,threading
from pathlib import Path
value=json.load(open(sys.argv[1]));sys.path.insert(0,value['tests'])
from action_server_tests.invoice_effect_fixture import OwnedEffectTarget
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import Actor,ExecutionSnapshot
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.invoice_worker import InvoiceWorkerService,InvoiceWorkerPlan,WorkerTicket
from actions.server.data_queries.invoice_effects import SyntheticEffectPolicy
from actions.work_items._fencing import WorkItemClaim
db=Database(value['database']);fd=os.open(value['objects'],os.O_RDONLY|os.O_DIRECTORY)
try:
 with db.connect(), FilesystemOutputProvider(fd) as objects:
  db.register_classes(get_all_model_classes())
  snapshot=ExecutionSnapshot.model_validate(value['snapshot'])
  outputs=RunOutputService(db,{snapshot.provider_key:objects})
  reviews=InvoiceReviewService(InvoiceQueryService(outputs,{}))
  policy=SyntheticEffectPolicy.model_validate(value['policy'])
  plan=InvoiceWorkerPlan(snapshot,RccRuntimeDescriptor.from_dict(value['descriptor']),Path(value['source']),value['sdk'],policy)
  target=OwnedEffectTarget(Path(value['target']),policy.target_id,idempotent=policy.idempotent,fault='crash_after_effect' if sys.argv[2]=='crash' else None)
  worker=InvoiceWorkerService(reviews,plan,Path(value['root']),Path(value['rcc']),Path(value['rcc_home']),effect_target=target)
  actor=Actor.model_validate(value['actor']);ticket=WorkerTicket.model_validate(value['ticket'])
  if sys.argv[2]=='crash':
   worker.launch(actor,ticket,threading.Event(),lease_seconds=120)
   worker.apply_effect(actor,ticket)
   raise AssertionError('missing abrupt exit')
  else:
   print(worker.reconcile(actor,ticket.proposal,WorkItemClaim(**value['claim']),lease_seconds=120).model_dump_json())
finally:os.close(fd)
"""


@pytest.mark.integration_test
def test_real_controller_crash_after_effect_then_fresh_process_reconciles_without_redelivery(
    reviewed, tmp_path
):
    from pathlib import Path

    from action_server_tests.invoice_effect_fixture import OwnedEffectTarget

    from actions.server.data_queries.invoice_worker import WorkerReceipt

    worker, actor, scope, handle = effect_worker(
        reviewed, tmp_path, real=True, max_attempts=1
    )
    worker.effect_target = OwnedEffectTarget(
        tmp_path / "target.db", worker.plan.effect_policy.target_id
    )
    reviews = reviewed[3]
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    ticket = worker.dispatch(actor, proposal, claim, lease_seconds=120)
    context = fixtures.controller_context(worker, actor, ticket, tmp_path)
    value = json.loads(context.read_text())
    value.update(
        policy=worker.plan.effect_policy.model_dump(mode="json"),
        target=str(tmp_path / "target.db"),
        tests=str(Path(fixtures.__file__).parents[1]),
    )
    context.write_text(json.dumps(value))
    crashed = subprocess.run(
        [sys.executable, "-I", "-c", EFFECT_CONTROLLER, str(context), "crash"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert crashed.returncode == 24, crashed.stderr
    assert worker.effect_target.counts() == (1, 1)
    newer = fixtures.expired_claim(reviewed, ticket)
    value["claim"] = {
        "item_id": newer.item_id,
        "owner_id": newer.owner_id,
        "epoch": newer.epoch,
    }
    context.write_text(json.dumps(value))
    restarted = subprocess.run(
        [sys.executable, "-I", "-c", EFFECT_CONTROLLER, str(context), "recover"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert restarted.returncode == 0, restarted.stderr
    result = WorkerReceipt.model_validate_json(restarted.stdout)
    assert result.disposition == "completed" and worker.effect_target.counts() == (1, 1)
    assert (
        worker.reviews.execution(actor, scope, proposal).artifact.handle
        == result.handle
    )


@pytest.mark.integration_test
def test_dead_letter_barrier_prevents_a_late_admitted_delivery_from_committing(
    reviewed, tmp_path
):
    from actions.server.data_queries.invoice_effects import (
        EffectUncertain,
        SyntheticEffectRequest,
    )

    entered, release = threading.Event(), threading.Event()

    def pause():
        entered.set()
        assert release.wait(30)

    worker, actor, first = ready_effect(reviewed, tmp_path, fault=pause)
    failures = []

    def old_delivery():
        try:
            with worker.db.connect():
                worker.apply_effect(actor, first)
        except Exception as exc:
            failures.append(exc)

    thread = threading.Thread(target=old_delivery)
    thread.start()
    try:
        assert entered.wait(15)
        second = worker.reconcile(
            actor,
            first.proposal,
            fixtures.expired_claim(reviewed, first),
            lease_seconds=120,
        )
        worker.effect_target.fault = "before_effect"
        with pytest.raises(EffectUncertain):
            worker.apply_effect(actor, second)
        dead = worker.reconcile(
            actor,
            second.proposal,
            fixtures.expired_claim(reviewed, second),
            lease_seconds=120,
        )
    finally:
        release.set()
        thread.join(15)
    assert not thread.is_alive() and len(failures) == 1
    assert worker.effect_target.counts() == (2, 0)
    with worker.outputs.resolve(
        actor, worker.scope.application.workspace_id, dead.handle
    ) as output:
        failure = json.loads(output.read())
    request = SyntheticEffectRequest.model_validate(failure["effect_request"])
    observation = worker.effect_target.observe(request)
    assert observation.state == "closed_absent"
    assert failure["effect_observation"] == observation.model_dump(mode="json")


def test_dead_letter_publication_failure_rolls_back_and_resumes_same_finalizer(
    reviewed, tmp_path
):
    from actions.work_items._fencing import ClaimRejected

    from actions.server.data_queries.invoice_worker import WorkerTicket
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import AccessDenied
    from actions.server.run_outputs.types import OutputRef

    worker, actor, scope, handle = effect_worker(reviewed, tmp_path, max_attempts=1)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    first = worker.dispatch(
        actor,
        proposal,
        reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120),
        lease_seconds=120,
    )
    newer = fixtures.expired_claim(reviewed, first)
    with db.transaction():
        if db.backend_name == "sqlite":
            db.execute(
                "CREATE TRIGGER expire_dead_letter AFTER INSERT ON fenced_work_item WHEN NEW.parent_id <> '' BEGIN UPDATE fenced_work_item SET claim_deadline_ms=0 WHERE id=NEW.parent_id; END"
            )
        else:
            db.execute(
                "CREATE FUNCTION expire_dead_letter() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN UPDATE fenced_work_item SET claim_deadline_ms=0 WHERE id=NEW.parent_id; RETURN NEW; END $$"
            )
            db.execute(
                "CREATE TRIGGER expire_dead_letter AFTER INSERT ON fenced_work_item FOR EACH ROW WHEN (NEW.parent_id <> '') EXECUTE FUNCTION expire_dead_letter()"
            )
    with pytest.raises(ClaimRejected):
        worker.reconcile(actor, proposal, newer, lease_seconds=120)
    run = db.first(Run, "SELECT * FROM run WHERE id=?", [first.fence.run_id])
    assert run.status == RunStatus.RUNNING
    provisional = db.all(RunOutput, where="run_id=?", values=[run.id])
    assert len(provisional) == 1 and provisional[0].state == "provisional"
    ref = OutputRef(
        workspace_id=scope.application.workspace_id,
        run_id=run.id,
        output_id=provisional[0].id,
    )
    with pytest.raises(AccessDenied):
        with worker.outputs.resolve(actor, scope.application.workspace_id, ref.handle):
            pass
    with db.transaction():
        db.execute(
            "DROP TRIGGER expire_dead_letter"
            + (" ON fenced_work_item" if db.backend_name == "postgresql" else "")
        )
    record = json.loads(run.result)
    finalizer = WorkerTicket(
        proposal=proposal, work_item_claim=record["claim"], fence=record["fence"]
    )
    receipt = worker.complete(actor, finalizer)
    assert receipt.disposition == "dead_letter"
    assert len(db.all(RunAttempt, where="run_id=?", values=[run.id])) == 2
    assert (
        len(db.all(RunOutput, where="run_id=? AND state='final'", values=[run.id])) == 1
    )


@pytest.mark.integration_test
def test_unknown_effect_record_cannot_be_adopted_as_a_completed_effect(
    reviewed, tmp_path
):
    from actions.server.data_queries.review import ReviewConflict

    worker, actor, ticket = ready_effect(reviewed, tmp_path)
    worker.apply_effect(actor, ticket)
    newer = fixtures.expired_claim(reviewed, ticket)
    db = reviewed[0]
    with db.transaction():
        run = db.first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id])
        record = json.loads(run.result)
        record["effect"]["state"] = "future_success"
        db.update_by_id(
            Run,
            run.id,
            {"result": json.dumps(record, sort_keys=True, separators=(",", ":"))},
        )
    with pytest.raises(ReviewConflict):
        worker.reconcile(actor, ticket.proposal, newer, lease_seconds=120)
    assert worker.effect_target.counts() == (1, 1)
    assert (
        db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).status
        == RunStatus.RUNNING
    )


def test_legacy_worker_defaults_preserve_absent_effect_fields(reviewed, tmp_path):
    from actions.server.data_queries.invoice_worker import WorkerReceipt

    worker, actor, scope, handle = fixtures.worker(reviewed, tmp_path)
    proposal = worker.reviews.offer(actor, scope, handle)
    worker.reviews.decide(actor, scope, proposal, "approve")
    claim = worker.reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    ticket = worker.dispatch(actor, proposal, claim, lease_seconds=120)
    run = reviewed[0].first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id])
    assert "effect_policy" not in json.loads(run.inputs)
    receipt = WorkerReceipt(
        run_id=run.id,
        attempt_id=ticket.fence.attempt_id,
        work_item_id=claim.item_id,
        handle=handle,
    )
    assert "disposition" not in receipt.model_dump(mode="json")
