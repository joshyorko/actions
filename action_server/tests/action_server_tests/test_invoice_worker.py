"""Review-to-Run composition against both SQL stores and real invoice providers."""

import hashlib
import json
import os
import sys
import threading
from pathlib import Path
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_review as fixtures
from action_server_tests.run_outputs import test_service as runs

from actions.server._models import Action, Run
from actions.server._rcc_runtime_adapter import (
    RccRuntimeDescriptor,
    compute_source_generation,
    environment_spec_fingerprint,
)
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.types import ExecutionSnapshot

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = fixtures.pytestmark


@pytest.fixture(autouse=True)
def retain_worker_cell(request, tmp_path):
    yield
    destination = os.environ.get("ACTIONS_INVOICE_WORKER_EVIDENCE_DIR")
    if destination and (tmp_path / "execution").exists():
        import shutil

        target = (
            Path(destination)
            / hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:16]
        )
        target.mkdir(parents=True, exist_ok=False)
        inventory = {}
        for directory in ("execution", "objects"):
            for source in (tmp_path / directory).rglob("*"):
                if (
                    source.is_file()
                    and not source.is_symlink()
                    and source.stat().st_size <= 2 * 1024 * 1024
                ):
                    relative = source.relative_to(tmp_path)
                    output = target / relative
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, output)
                    inventory[str(relative)] = hashlib.sha256(
                        output.read_bytes()
                    ).hexdigest()
        (target / "cell.json").write_text(
            json.dumps({"nodeid": request.node.nodeid, "sha256": inventory}, indent=2)
            + "\n"
        )


def worker(reviewed, tmp_path, *, real=False):
    from actions.server.data_queries import invoice_worker

    db, control, queries, reviews, actor, scope, handle, query_snapshot = reviewed
    source = tmp_path / "worker-source"
    source.mkdir()
    source.joinpath("_invoice_task.py").write_bytes(
        Path(invoice_worker.__file__).with_name("_invoice_task.py").read_bytes()
    )
    if real:
        config = os.environ.get("ACTIONS_INVOICE_WORKER_ENVIRONMENT")
        if not config:
            if os.environ.get("ACTIONS_REQUIRE_INVOICE_WORKER") == "1":
                pytest.fail("owned RCC invoice runtime required")
            pytest.skip("owned RCC invoice runtime not configured")
        runtime = json.loads(Path(config).read_text())
        source.joinpath("package.yaml").write_bytes(
            Path(runtime["environment"]).read_bytes()
        )
    else:
        source.joinpath("package.yaml").write_text(
            "spec-version: v2\ndependencies: {}\n"
        )
    generation = compute_source_generation(source)
    descriptor = RccRuntimeDescriptor(
        artifact_digest=runtime["artifact_digest"] if real else "sha256:" + "a" * 64,
        provider_reference="local" if real else None,
        source_generation=generation,
        source_hash=generation,
        environment_fingerprint=environment_spec_fingerprint(source / "package.yaml"),
    )
    sdk_hash = runtime["sdk_wheel_sha256"] if real else "b" * 64
    payload = query_snapshot.model_dump(mode="json")
    package = payload["capability"]["package_revision"]
    package["package_id"] = str(uuid4())
    package["revision_id"] = "sha256:" + generation
    payload["runtime_plan"]["package_revision"] = dict(package)
    payload["runtime_plan"]["plan_digest"] = invoice_worker.plan_digest(
        descriptor, sdk_hash
    )
    payload["action_id"] = "worker-" + str(uuid4())
    payload["capability"]["capability_id"] = "invoice_task"
    payload["runtime_kind"] = invoice_worker.RUNTIME_KIND
    schema = invoice_worker.WorkerInput.model_json_schema()
    encoded = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    payload["capability_schema_digest"] = (
        "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()
    )
    snapshot = ExecutionSnapshot.model_validate(payload)
    runs.insert_action(db, snapshot)
    with db.transaction():
        db.update_by_id(
            Action,
            snapshot.action_id,
            {"input_schema": encoded, "file": "_invoice_task.py"},
        )
    control.register(snapshot)
    plan = invoice_worker.InvoiceWorkerPlan(snapshot, descriptor, source, sdk_hash)
    service = invoice_worker.InvoiceWorkerService(
        reviews,
        plan,
        tmp_path / "execution",
        Path(runtime["rcc"]) if real else Path("/workspace/actions-cloud/bin/rcc"),
        Path(runtime["rcc_home"]) if real else tmp_path / "worker-rcc",
    )
    return service, actor, scope, handle


def test_dispatch_reuses_one_distinct_run_and_attempt_for_approved_result(
    reviewed, tmp_path
):
    service, actor, scope, handle = worker(reviewed, tmp_path)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    receipt = reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=30)
    first = service.dispatch(actor, proposal, claim, lease_seconds=30)
    second = service.dispatch(actor, proposal, claim, lease_seconds=30)
    assert first == second
    assert first.fence.run_id != proposal.binding.run_id
    assert first.claim.item_id == receipt.work_item_id
    assert len(db.all(Run)) == 2 and len(db.all(RunAttempt)) == 2
    run = db.first(Run, "SELECT * FROM run WHERE id=?", [first.fence.run_id])
    inputs = json.loads(run.inputs)
    assert inputs["proposal"] == proposal.model_dump(mode="json")
    assert inputs["initial_claim"]["epoch"] == claim.epoch
    assert inputs["initial_claim"]["item_id"] == claim.item_id
    pin = db.first(RunPin, "SELECT * FROM run_pin WHERE run_id=?", [run.id])
    assert pin.current_attempt_id == first.fence.attempt_id
    assert len(reviews.queue(scope).list_items()) == 1


def test_reclaimed_work_item_cannot_reuse_an_attempt_even_with_same_owner(
    reviewed, tmp_path
):
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import FenceRejected

    service, actor, scope, handle = worker(reviewed, tmp_path)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    queue = reviews.queue(scope)
    old = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    service.dispatch(actor, proposal, old, lease_seconds=30)
    with db.transaction():
        db.update_by_id(FencedWorkItem, old.item_id, {"claim_deadline_ms": "0"})
    current = queue.reserve_fenced(old.owner_id, lease_seconds=30)
    assert current.epoch == old.epoch + 1
    with pytest.raises(FenceRejected):
        service.dispatch(actor, proposal, current, lease_seconds=30)


@pytest.mark.integration_test
def test_real_rcc_executes_exact_reviewed_result_and_replays_without_dispatch(
    reviewed, tmp_path
):
    from actions.work_items import State

    from actions.server._models import RunStatus

    service, actor, scope, handle = worker(reviewed, tmp_path, real=True)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    approved = reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=120)
    service.launch(actor, ticket, threading.Event(), lease_seconds=120)
    receipt = service.complete(actor, ticket)
    assert receipt.run_id == ticket.fence.run_id
    assert receipt.attempt_id == ticket.fence.attempt_id
    assert receipt.work_item_id == approved.work_item_id
    assert service.complete(actor, ticket) == receipt
    from actions.server.run_outputs.service import FenceRejected

    forged = ticket.model_copy(
        update={"fence": ticket.fence.model_copy(update={"attempt_id": str(uuid4())})}
    )
    with pytest.raises(FenceRejected):
        service.complete(actor, forged)
    assert service.dispatch(actor, proposal, claim, lease_seconds=120) == ticket
    run = db.first(Run, "SELECT * FROM run WHERE id=?", [receipt.run_id])
    assert run.status == RunStatus.PASSED
    assert reviews.queue(scope).list_items()[0]["state"] == State.DONE.value
    with service.outputs.resolve(
        actor, scope.application.workspace_id, receipt.handle, canvas_scope=scope
    ) as output:
        data = json.loads(output.read())
    assert data["task"]["invoice_count"] == 2
    assert data["task"]["total_cents"] == 12900
    assert data["task"]["binding"] == proposal.binding.model_dump(mode="json")
    assert data["task"]["sdk"]["version"] == "0.5.0a1"
    assert data["task"]["sdk"]["wheel_sha256"] == service.plan.sdk_wheel_sha256
    assert (
        data["rcc_receipt"]["artifactDigest"] == service.plan.descriptor.artifact_digest
    )
    assert data["rcc_receipt"]["status"] == "completed"


def test_review_cancellation_fences_linked_run_and_work_item(reviewed, tmp_path):
    service, actor, scope, handle = worker(reviewed, tmp_path)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=30)
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=30)
    reviews.cancel(actor, scope, proposal)
    pin = db.first(
        RunPin, "SELECT * FROM run_pin WHERE run_id=?", [ticket.fence.run_id]
    )
    assert pin.cancel_requested == 1
    from actions.server.run_outputs.service import FenceRejected

    with pytest.raises(FenceRejected):
        service.outputs.heartbeat(ticket.fence, lease_seconds=30)


def expired_claim(reviewed, ticket):
    from actions.server.data_queries.review_models import FencedWorkItem

    db, _, _, reviews, _, scope, *_ = reviewed
    with db.transaction():
        db.update_by_id(
            FencedWorkItem, ticket.claim.item_id, {"claim_deadline_ms": "0"}
        )
        db.update_by_id(RunAttempt, ticket.fence.attempt_id, {"lease_deadline_ms": "0"})
    return reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)


def test_explicit_reconciliation_recovers_unlaunched_attempt_without_new_run(
    reviewed, tmp_path
):
    from actions.work_items._fencing import ClaimRejected

    from actions.server.data_queries.invoice_worker import WorkerTicket

    service, actor, scope, handle = worker(reviewed, tmp_path)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    first = service.dispatch(actor, proposal, claim, lease_seconds=120)
    newer = expired_claim(reviewed, first)
    recovered = service.reconcile(actor, proposal, newer, lease_seconds=120)
    assert isinstance(recovered, WorkerTicket)
    assert recovered.fence.run_id == first.fence.run_id
    assert recovered.fence.epoch == first.fence.epoch + 1
    assert recovered.claim.epoch == first.claim.epoch + 1
    assert recovered.fence.owner_id == newer.owner_id
    assert len(db.all(Run)) == 2 and len(db.all(RunAttempt)) == 3
    with pytest.raises(ClaimRejected):
        service.complete(actor, first)


@pytest.mark.integration_test
def test_completed_private_result_reconciles_after_lease_loss_without_reexecution(
    reviewed, tmp_path
):
    from actions.server.data_queries.invoice_worker import (
        InvoiceWorkerService,
        WorkerReceipt,
    )
    from actions.server.run_outputs.service import FenceRejected

    service, actor, scope, handle = worker(reviewed, tmp_path, real=True)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    first = service.dispatch(actor, proposal, claim, lease_seconds=120)
    service.launch(actor, first, threading.Event(), lease_seconds=120)
    newer = expired_claim(reviewed, first)
    restarted = InvoiceWorkerService(
        reviews, service.plan, service.execution_root, service.rcc, service.rcc_home
    )
    receipt = restarted.reconcile(actor, proposal, newer, lease_seconds=120)
    assert isinstance(receipt, WorkerReceipt)
    assert (
        receipt.run_id == first.fence.run_id
        and receipt.attempt_id != first.fence.attempt_id
    )
    assert len(list(service.execution_root.glob("*/*/*/rcc.json"))) == 1
    run = db.first(Run, "SELECT * FROM run WHERE id=?", [receipt.run_id])
    result = json.loads(run.result)["result"]
    assert result["executed_fence"] == first.fence.model_dump()
    assert result["publication_fence"]["owner_id"] == newer.owner_id
    with pytest.raises(FenceRejected):
        restarted.complete(actor, first)


@pytest.mark.integration_test
def test_unknown_or_altered_execution_receipt_never_authorizes_retry(
    reviewed, tmp_path
):
    from actions.server.data_queries.review import ReviewConflict

    service, actor, scope, handle = worker(reviewed, tmp_path, real=True)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    first = service.dispatch(actor, proposal, claim, lease_seconds=120)
    service.launch(actor, first, threading.Event(), lease_seconds=120)
    next(service.execution_root.glob("*/*/*/rcc.json")).unlink()
    newer = expired_claim(reviewed, first)
    before = len(db.all(RunAttempt))
    with pytest.raises(ReviewConflict):
        service.reconcile(actor, proposal, newer, lease_seconds=120)
    assert len(db.all(RunAttempt)) == before
    assert not list(service.execution_root.glob("*/*/*/reconciled.json"))


@pytest.mark.parametrize(
    "change",
    [
        "approval",
        "review_grant",
        "inputs",
        "application_revision",
        "schema",
        "source",
        "claim",
    ],
)
def test_dispatch_denials_create_no_run_or_attempt(reviewed, tmp_path, change):
    from actions.work_items._fencing import ClaimRejected, WorkItemClaim

    from actions.server.data_queries.review import ReviewConflict
    from actions.server.run_outputs.service import AccessDenied

    service, actor, scope, handle = worker(reviewed, tmp_path)
    db, control, _, reviews, _, _, _, query_snapshot = reviewed
    proposal = reviews.offer(actor, scope, handle)
    if change != "approval":
        reviews.decide(actor, scope, proposal, "approve")
        claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=30)
    else:
        claim = WorkItemClaim(str(uuid4()), str(uuid4()), 1)
    if change == "review_grant":
        control.grant(actor, query_snapshot.deployment, {"read", "execute"})
    elif change == "inputs":
        with db.transaction():
            db.update_by_id(Run, proposal.binding.run_id, {"inputs": '{"min_days":99}'})
    elif change == "application_revision":
        value = proposal.model_dump(mode="json")
        value["binding"]["scope"]["application"]["revision_id"] = "sha256:" + "f" * 64
        from actions.server.data_queries.review import ReviewProposal

        proposal = ReviewProposal.model_validate(value)
    elif change == "schema":
        with db.transaction():
            db.update_by_id(
                Action,
                service.plan.snapshot.action_id,
                {"input_schema": '{"type":"array"}'},
            )
    elif change == "source":
        with service.plan.source_directory.joinpath("_invoice_task.py").open(
            "a"
        ) as stream:
            stream.write("\n# altered pinned source\n")
    elif change == "claim":
        claim = WorkItemClaim(claim.item_id, str(uuid4()), claim.epoch)
    before = (len(db.all(Run)), len(db.all(RunAttempt)))
    with pytest.raises((AccessDenied, ReviewConflict, ClaimRejected)):
        service.dispatch(actor, proposal, claim, lease_seconds=30)
    assert (len(db.all(Run)), len(db.all(RunAttempt))) == before
    assert not service.execution_root.exists()


@pytest.mark.integration_test
def test_work_item_expiry_rolls_back_run_publication_and_outputs(reviewed, tmp_path):
    from actions.work_items._fencing import ClaimRejected

    from actions.server._models import RunStatus
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import AccessDenied
    from actions.server.run_outputs.types import OutputRef

    service, actor, scope, handle = worker(reviewed, tmp_path, real=True)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=120)
    service.launch(actor, ticket, threading.Event(), lease_seconds=120)
    with db.transaction():
        if db.backend_name == "sqlite":
            db.execute(
                "CREATE TRIGGER expire_worker_output AFTER INSERT ON fenced_work_item WHEN NEW.parent_id <> '' BEGIN UPDATE fenced_work_item SET claim_deadline_ms=0 WHERE id=NEW.parent_id; END"
            )
        else:
            db.execute(
                "CREATE FUNCTION expire_worker_output() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN UPDATE fenced_work_item SET claim_deadline_ms=0 WHERE id=NEW.parent_id; RETURN NEW; END $$"
            )
            db.execute(
                "CREATE TRIGGER expire_worker_output AFTER INSERT ON fenced_work_item FOR EACH ROW WHEN (NEW.parent_id <> '') EXECUTE FUNCTION expire_worker_output()"
            )
    with pytest.raises(ClaimRejected):
        service.complete(actor, ticket)
    run = db.first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id])
    assert run.status == RunStatus.RUNNING
    assert db.all(FencedWorkItem, where="parent_id=?", values=[claim.item_id]) == []
    provisional = db.all(RunOutput, where="run_id=?", values=[run.id])
    assert len(provisional) == 1 and provisional[0].state == "provisional"
    ref = OutputRef(
        workspace_id=scope.application.workspace_id,
        run_id=run.id,
        output_id=provisional[0].id,
    )
    with pytest.raises(AccessDenied):
        with service.outputs.resolve(actor, scope.application.workspace_id, ref.handle):
            pass
    with db.transaction():
        db.execute(
            "DROP TRIGGER expire_worker_output"
            + (" ON fenced_work_item" if db.backend_name == "postgresql" else "")
        )
    receipt = service.complete(actor, ticket)
    assert receipt.run_id == run.id
    assert (
        len(db.all(RunOutput, where="run_id=? AND state='final'", values=[run.id])) == 1
    )
    assert len(list(service.execution_root.glob("*/*/*/rcc.json"))) == 1


def controller_context(service, actor, ticket, tmp_path):
    path = tmp_path / "controller.json"
    path.write_text(
        json.dumps(
            {
                "database": str(service.db.db_path),
                "objects": str(tmp_path / "objects"),
                "snapshot": service.plan.snapshot.model_dump(mode="json"),
                "descriptor": service.plan.descriptor.to_dict(),
                "source": str(service.plan.source_directory),
                "sdk": service.plan.sdk_wheel_sha256,
                "root": str(service.execution_root),
                "rcc": str(service.rcc),
                "rcc_home": str(service.rcc_home),
                "actor": actor.model_dump(mode="json"),
                "ticket": ticket.model_dump(mode="json"),
            }
        )
    )
    return path


CONTROLLER = """
import json,os,sys,threading
from pathlib import Path
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import Actor,ExecutionSnapshot
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.invoice_worker import InvoiceWorkerService,InvoiceWorkerPlan,WorkerTicket
value=json.load(open(sys.argv[1]));db=Database(value['database']);fd=os.open(value['objects'],os.O_RDONLY|os.O_DIRECTORY)
try:
 with db.connect(), FilesystemOutputProvider(fd) as objects:
  db.register_classes(get_all_model_classes())
  snapshot=ExecutionSnapshot.model_validate(value['snapshot'])
  outputs=RunOutputService(db,{snapshot.provider_key:objects})
  reviews=InvoiceReviewService(InvoiceQueryService(outputs,{}))
  plan=InvoiceWorkerPlan(snapshot,RccRuntimeDescriptor.from_dict(value['descriptor']),Path(value['source']),value['sdk'])
  service=InvoiceWorkerService(reviews,plan,Path(value['root']),Path(value['rcc']),Path(value['rcc_home']))
  actor=Actor.model_validate(value['actor']);ticket=WorkerTicket.model_validate(value['ticket'])
  if sys.argv[2]=='crash-after-rcc':
   service.launch(actor,ticket,threading.Event(),lease_seconds=120)
   os._exit(23)
  else:
   print(service.complete(actor,ticket).model_dump_json())
finally:os.close(fd)
"""


@pytest.mark.integration_test
def test_real_controller_crash_then_new_interpreter_finishes_durable_result(
    reviewed, tmp_path
):
    import subprocess

    from actions.server._models import RunStatus

    service, actor, scope, handle = worker(reviewed, tmp_path, real=True)
    db, _, _, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=120)
    context = controller_context(service, actor, ticket, tmp_path)
    crashed = subprocess.run(
        [sys.executable, "-I", "-c", CONTROLLER, str(context), "crash-after-rcc"],
        capture_output=True,
        text=True,
        timeout=150,
    )
    assert crashed.returncode == 23, crashed.stderr
    assert (
        db.first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id]).status
        == RunStatus.RUNNING
    )
    restarted = subprocess.run(
        [sys.executable, "-I", "-c", CONTROLLER, str(context), "complete"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert restarted.returncode == 0, restarted.stderr
    receipt = json.loads(restarted.stdout)
    assert receipt["run_id"] == ticket.fence.run_id
    assert receipt["attempt_id"] == ticket.fence.attempt_id
    assert len(list(service.execution_root.glob("*/*/*/rcc.json"))) == 1
    assert len(db.all(Run)) == 2


@pytest.mark.integration_test
def test_cancel_stops_a_real_owned_rcc_wrapper_and_prevents_publication(
    reviewed, tmp_path, monkeypatch
):
    import os
    import signal
    from concurrent.futures import ThreadPoolExecutor

    from actions.work_items._fencing import ClaimRejected

    import actions.server.data_queries.invoice_worker as implementation
    from actions.server._database import Database
    from actions.server._models import get_all_model_classes
    from actions.server.data_queries.invoice_worker import InvoiceWorkerService
    from actions.server.data_queries.review import InvoiceReviewService, ReviewConflict
    from actions.server.data_queries.service import InvoiceQueryService
    from actions.server.run_outputs.service import FenceRejected, RunOutputService

    service, actor, scope, handle = worker(reviewed, tmp_path, real=True)
    db, _, queries, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=120)
    real_popen = implementation.subprocess.Popen
    started = threading.Event()
    processes = []

    def stop_at_spawn(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        # An actual task-owned RCC process is suspended before cancellation.
        # This controls the race without replacing RCC or either SQL backend.
        command = args[0]
        if isinstance(command, list) and command[1:3] == ["env", "exec"]:
            os.kill(process.pid, signal.SIGSTOP)
            processes.append(process)
            started.set()
        return process

    def launch():
        connection = Database(db.db_path)
        with connection.connect():
            connection.register_classes(get_all_model_classes())
            outputs = RunOutputService(connection, queries.outputs.providers)
            instance = InvoiceWorkerService(
                InvoiceReviewService(InvoiceQueryService(outputs, {})),
                service.plan,
                service.execution_root,
                service.rcc,
                service.rcc_home,
            )
            instance.launch(actor, ticket, threading.Event(), lease_seconds=120)

    monkeypatch.setattr(implementation.subprocess, "Popen", stop_at_spawn)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(launch)
        assert started.wait(timeout=30), "real RCC wrapper did not start"
        reviews.cancel(actor, scope, proposal)
        with pytest.raises((ReviewConflict, FenceRejected, ClaimRejected)):
            running.result(timeout=20)
    assert len(processes) == 1 and processes[0].poll() is not None
    with pytest.raises((ReviewConflict, FenceRejected, ClaimRejected)):
        service.complete(actor, ticket)


def test_parallel_dispatch_connections_share_one_run_and_attempt(reviewed, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    from actions.server._database import Database
    from actions.server._models import get_all_model_classes
    from actions.server.data_queries.invoice_worker import InvoiceWorkerService
    from actions.server.data_queries.review import InvoiceReviewService
    from actions.server.data_queries.service import InvoiceQueryService
    from actions.server.run_outputs.service import RunOutputService

    service, actor, scope, handle = worker(reviewed, tmp_path)
    db, _, queries, reviews, *_ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    barrier = threading.Barrier(2)

    def dispatch():
        connection = Database(db.db_path)
        with connection.connect():
            connection.register_classes(get_all_model_classes())
            instance = InvoiceWorkerService(
                InvoiceReviewService(
                    InvoiceQueryService(
                        RunOutputService(connection, queries.outputs.providers), {}
                    )
                ),
                service.plan,
                service.execution_root,
                service.rcc,
                service.rcc_home,
            )
            barrier.wait(timeout=15)
            return instance.dispatch(actor, proposal, claim, lease_seconds=120)

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(dispatch) for _ in range(2)]
        tickets = [item.result(timeout=30) for item in pending]
    assert tickets[0] == tickets[1]
    assert len(db.all(Run)) == 2 and len(db.all(RunAttempt)) == 2
    assert not service.execution_root.exists()


@pytest.mark.integration_test
def test_revoked_authority_cannot_publish_already_executed_task(reviewed, tmp_path):
    from actions.server._models import RunStatus
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import AccessDenied

    service, actor, scope, handle = worker(reviewed, tmp_path, real=True)
    db, control, _, reviews, _, _, _, snapshot = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=120)
    service.launch(actor, ticket, threading.Event(), lease_seconds=120)
    control.grant(actor, snapshot.deployment, {"read"})
    with pytest.raises(AccessDenied):
        service.complete(actor, ticket)
    assert (
        db.first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id]).status
        == RunStatus.RUNNING
    )
    assert db.all(RunOutput, where="run_id=?", values=[ticket.fence.run_id]) == []
    control.grant(actor, snapshot.deployment, {"read", "execute", "review", "cancel"})
    assert service.complete(actor, ticket).run_id == ticket.fence.run_id
    assert len(list(service.execution_root.glob("*/*/*/rcc.json"))) == 1


def test_source_symlink_is_refused_before_hashing_any_target(
    reviewed, tmp_path, monkeypatch
):
    from actions.server.run_outputs.service import AccessDenied

    service, _, _, _ = worker(reviewed, tmp_path)
    target = tmp_path / "owned-synthetic-target.txt"
    target.write_text("synthetic outside source")
    service.plan.source_directory.joinpath("linked.py").symlink_to(target)
    read = Path.read_bytes

    def reject_target(path):
        if path.resolve() == target:
            raise AssertionError("source hashing followed a symlink")
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", reject_target)
    with pytest.raises(AccessDenied):
        service.plan.validate()
