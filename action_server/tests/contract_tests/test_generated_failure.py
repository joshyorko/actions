"""Canonical failed-child publication contracts; synthetic receipt, no RCC claim."""

import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests import test_generic_work_item_execution as generic_tests
from action_server_tests import test_task_service as task_tests

from actions.server._models import Run, RunStatus
from actions.server.foundry.logical_receipts import FAILURE_V1
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.run_outputs.models import RunAttempt, RunOutput
from actions.server.run_outputs.service import (
    FenceRejected,
    RunOutputControlPlane,
    _canonical,
    _one,
)
from actions.server.run_outputs.task_service import TaskUnavailable

pytest_plugins = ["action_server_tests.foundry_fixtures"]
generic = generic_tests.generic
dispatch = generic_tests.dispatch
provider = task_tests.provider
postgresql_database = task_tests.postgresql_database
reviewed = task_tests.reviewed
case = task_tests.case


def prepare(service, caller, ticket, *, logical_summary=None):
    outputs = service.outputs(caller, ticket)
    db, snapshot = service.db, service.snapshot
    compiled = service.registry.load(snapshot.capability.package_revision)
    run = _one(db, Run, ticket.fence.run_id)
    claim = ticket.claim.model_dump() if ticket.claim else None
    lineage = GeneratedRccExecution._lineage(snapshot, claim, ticket.fence)
    fixed = dict(
        sourceArtifactDigest=compiled.source_artifact_digest,
        packageRevision=compiled.package_revision_id.root,
        runtimePlanDigest=snapshot.runtime_plan.plan_digest.root,
        rccSpecificationDigest=compiled.rcc_specification_digest,
        rccArtifactDigest=compiled.rcc_artifact_digest,
    )
    launch = dict(
        id=str(uuid4()),
        workItemClaim=claim,
        lineage=lineage,
        inputDigest="sha256:"
        + hashlib.sha256(
            _canonical(json.loads(run.inputs), 262144).encode()
        ).hexdigest(),
        **fixed,
    )
    if logical_summary is not None:
        launch["logicalReads"] = logical_summary
    journal = json.loads(run.result)
    journal.pop("execution", None)
    journal["launch"] = launch
    with db.transaction():
        db.update_by_id(Run, run.id, {"result": _canonical(journal, 65536)})
    refs = []
    records = []
    payloads = {
        "rcc-receipt.json": b'{"status":"failed","exitCode":1}',
        "rcc-stdout.log": b"",
        "rcc-stderr.log": b"TypeError: synthetic bounded diagnostic\n",
    }
    for name, payload in payloads.items():
        ref = outputs.stage(
            ticket.fence,
            [payload],
            name=name,
            media_type="application/json"
            if name.endswith(".json")
            else "application/octet-stream",
            retention_seconds=3600,
        )
        refs.append(ref)
        records.append(
            dict(
                name=name,
                ref=ref.model_dump(mode="json"),
                digest="sha256:" + hashlib.sha256(payload).hexdigest(),
                size=len(payload),
            )
        )

    def measured(name):
        payload = payloads[name]
        return dict(
            observedBytes=len(payload),
            retainedBytes=len(payload),
            discardedObservedBytes=0,
            streamComplete=True,
            truncated=False,
            digest="sha256:" + hashlib.sha256(payload).hexdigest(),
        )

    execution = dict(
        status="failed",
        exitCode=1,
        artifactDigest=compiled.rcc_artifact_digest,
        receiptDigest=records[0]["digest"],
        cleanup=dict(
            wrapperReaped=True, descendantSnapshotComplete=True, executionStopped=True
        ),
        stdout=measured("rcc-stdout.log"),
        stderr=measured("rcc-stderr.log"),
    )
    record = dict(
        version=FAILURE_V1,
        mode=journal["mode"],
        claim=claim,
        lineage=lineage,
        launch=launch,
        publicationFence=ticket.fence.model_dump(),
        execution=execution,
        outputs=records,
        **fixed,
    )
    return SimpleNamespace(
        service=service,
        caller=caller,
        ticket=ticket,
        outputs=outputs,
        db=db,
        run=run,
        refs=refs,
        record=record,
    )


def publish(f):
    with f.outputs.bind_generated_failure(f.record):
        return f.outputs.publish(
            f.caller.actor,
            f.ticket.fence,
            f.refs,
            f.record,
            terminal_status=RunStatus.FAILED,
        )


def ordinary(c):
    tasks, owner, service, caller = task_tests.setup(c)
    task = task_tests.create(c, tasks, service, caller)
    ticket = owner.claim(caller, task.task_id, service.snapshot.worker)
    return prepare(service, caller, ticket), tasks, task


def test_ordinary_failure_is_terminal_readable_task_without_result(case, monkeypatch):
    f, tasks, task = ordinary(case)
    with f.outputs.bind_generated_failure(f.record):
        with monkeypatch.context() as m:
            m.setattr(
                f.service.registry,
                "load_verified",
                lambda *a, **k: pytest.fail("artifact I/O in publication"),
            )
            m.setattr(
                f.service.registry,
                "schema_for",
                lambda *a, **k: pytest.fail("schema I/O in publication"),
            )
            for provider in f.outputs.providers.values():
                m.setattr(
                    provider,
                    "open",
                    lambda *a, **k: pytest.fail("provider I/O in publication"),
                )
            result = f.outputs.publish(
                f.caller.actor,
                f.ticket.fence,
                f.refs,
                f.record,
                terminal_status=RunStatus.FAILED,
            )
    assert result.status == RunStatus.FAILED
    assert _one(f.db, RunAttempt, f.ticket.fence.attempt_id).state == "failed"
    fresh = (
        type(tasks)(tasks.detached, readiness=task_tests.Ready(), policy=tasks.policy)
        if hasattr(tasks, "detached")
        else tasks
    )
    terminal = fresh.get(f.caller.actor, f.service.snapshot.workspace_id, task.task_id)
    assert terminal.result["isError"] is True
    assert terminal.result["structuredContent"]["state"] == "failed"
    assert len(terminal.result["structuredContent"]["outputs"]) == 3
    assert "actionResult" not in json.loads(result.result)["result"]
    assert all(
        row.name != "generated-action-result.json" for row in f.db.all(RunOutput)
    )
    RunOutputControlPlane(f.db).grant(
        f.caller.actor, f.service.snapshot.deployment, {"execute"}
    )
    with pytest.raises(TaskUnavailable):
        tasks.get(f.caller.actor, f.service.snapshot.workspace_id, task.task_id)


@pytest.mark.parametrize(
    "field",
    [
        "version",
        "exit",
        "cleanup",
        "result",
        "source",
        "plan",
        "claim",
        "lineage",
        "fence",
        "digest",
        "size",
        "extra-output",
    ],
)
def test_failure_receipt_mutation_does_not_terminalize(case, field):
    f, _, _ = ordinary(case)
    if field == "version":
        f.record["version"] = "actions.generated-rcc-failure/v2"
    elif field == "exit":
        f.record["execution"]["exitCode"] = 0
    elif field == "cleanup":
        f.record["execution"]["cleanup"]["executionStopped"] = False
    elif field == "result":
        f.record["actionResult"] = "fabricated"
    elif field == "source":
        f.record["sourceArtifactDigest"] = "sha256:" + "a" * 64
    elif field == "plan":
        f.record["runtimePlanDigest"] = "sha256:" + "a" * 64
    elif field == "claim":
        f.record["claim"] = {}
    elif field == "lineage":
        f.record["lineage"] = {}
    elif field == "fence":
        f.record["publicationFence"]["epoch"] += 1
    elif field == "digest":
        f.record["execution"]["receiptDigest"] = "sha256:" + "a" * 64
    elif field == "size":
        f.record["outputs"][0]["size"] = True
    else:
        f.record["outputs"].append(f.record["outputs"][0])
    with pytest.raises((ValueError, PermissionError, FenceRejected)):
        publish(f)
    assert _one(f.db, Run, f.run.id).status == RunStatus.RUNNING
    assert all(
        _one(f.db, RunOutput, ref.output_id).state == "provisional" for ref in f.refs
    )


@pytest.mark.parametrize("change", ["cancel", "lease", "grant"])
def test_failed_publish_rechecks_live_fence(case, change):
    f, _, _ = ordinary(case)
    if change == "cancel":
        f.service.base.cancel(f.caller.actor, f.run.id)
    elif change == "lease":
        with f.db.transaction():
            f.db.update_by_id(
                RunAttempt, f.ticket.fence.attempt_id, {"lease_deadline_ms": "0"}
            )
    else:
        RunOutputControlPlane(f.db).revoke(
            f.caller.actor, f.service.snapshot.deployment
        )
    with pytest.raises((ValueError, PermissionError, FenceRejected)):
        publish(f)
    assert _one(f.db, Run, f.run.id).status == RunStatus.RUNNING


def test_generic_failure_finishes_same_claim_without_children(generic):
    from actions.server.data_queries.review_models import FencedWorkItem

    g = generic(outputs=True)
    ticket, claim = dispatch(g)
    f = prepare(g.owner, g.caller, ticket)
    assert publish(f).status == RunStatus.FAILED
    items = g.db.all(FencedWorkItem)
    assert len(items) == 1 and items[0].state == "FAILED"
    assert g.owner.retained_ticket(g.caller, claim) == ticket


def test_failure_claim_completion_is_atomic(generic, monkeypatch):
    from actions.server.data_queries.review_models import FencedWorkItem

    g = generic(outputs=True)
    ticket, claim = dispatch(g)
    f = prepare(g.owner, g.caller, ticket)
    initial = g.db.all(FencedWorkItem)[0].state
    queue = g.owner.queue(g.owner.policy.input_queue)

    def unavailable(*args, **kwargs):
        raise RuntimeError("synthetic queue commit failure")

    monkeypatch.setattr(type(queue), "finish_fenced", unavailable)
    with pytest.raises(RuntimeError, match="synthetic queue commit failure"):
        publish(f)
    assert _one(f.db, Run, f.run.id).status == RunStatus.RUNNING
    assert g.db.all(FencedWorkItem)[0].state == initial
    assert all(
        _one(f.db, RunOutput, ref.output_id).state == "provisional" for ref in f.refs
    )


def test_failure_requires_issued_binding_and_rechecks_package_sql(case):
    from actions.server.foundry.models import FoundryPackageRevision

    f, _, _ = ordinary(case)
    with pytest.raises(FenceRejected, match="issued failed execution"):
        f.outputs.publish(
            f.caller.actor,
            f.ticket.fence,
            f.refs,
            f.record,
            terminal_status=RunStatus.FAILED,
        )
    with f.outputs.bind_generated_failure(f.record):
        row = f.db.all(FoundryPackageRevision)[-1]
        with f.db.transaction():
            f.db.update_by_id(FoundryPackageRevision, row.id, {"manifest_json": "{}"})
        with pytest.raises((ValueError, PermissionError, FenceRejected)):
            f.outputs.publish(
                f.caller.actor,
                f.ticket.fence,
                f.refs,
                f.record,
                terminal_status=RunStatus.FAILED,
            )
    assert _one(f.db, Run, f.run.id).status == RunStatus.RUNNING


@pytest.mark.parametrize(
    "corruption", ["version", "attempt", "output-scope", "expired"]
)
def test_terminal_failure_task_read_denies_tampering(case, corruption):
    f, tasks, task = ordinary(case)
    publish(f)
    with f.db.transaction():
        if corruption == "version":
            run = _one(f.db, Run, f.run.id)
            carrier = json.loads(run.result)
            carrier["result"]["version"] = "actions.generated-rcc-failure/v2"
            f.db.update_by_id(
                Run, run.id, {"result": _canonical(carrier, 2 * 1024 * 1024)}
            )
        elif corruption == "attempt":
            f.db.update_by_id(
                RunAttempt,
                f.ticket.fence.attempt_id,
                {"epoch": f.ticket.fence.epoch + 1},
            )
        elif corruption == "output-scope":
            f.db.update_by_id(
                RunOutput, f.refs[0].output_id, {"epoch": f.ticket.fence.epoch + 1}
            )
        else:
            f.db.update_by_id(RunOutput, f.refs[0].output_id, {"expires_ms": "0"})
    with pytest.raises(TaskUnavailable):
        tasks.get(f.caller.actor, f.service.snapshot.workspace_id, task.task_id)


def test_runner_failure_publication_uses_canonical_wrapper(case):
    f, tasks, task = ordinary(case)
    runner = object.__new__(GeneratedRccExecution)
    runner.outputs = f.outputs
    runner.registry = f.service.registry
    compiled = f.service.registry.load(f.service.snapshot.capability.package_revision)
    journal = json.loads(_one(f.db, Run, f.run.id).result)
    capture = dict(
        observedBytes=0, streamComplete=True, discardedObservedBytes=0, truncated=False
    )
    result = runner._publish_failed(
        f.caller.actor,
        f.ticket.fence,
        f.service.snapshot,
        compiled,
        journal,
        f.record["launch"],
        b'{"status":"failed","exitCode":1}',
        1,
        SimpleNamespace(
            execution_stopped=True,
            wrapper_reaped=True,
            descendant_snapshot_complete=True,
        ),
        b"",
        b"",
        capture,
        capture,
    )
    assert result.status == RunStatus.FAILED
    terminal = tasks.get(f.caller.actor, f.service.snapshot.workspace_id, task.task_id)
    assert terminal.result["isError"] is True
