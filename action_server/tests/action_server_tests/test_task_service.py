"""SDK-free Tasks project common Run authority; no worker/transport simulation."""
import pytest
from action_server_tests import test_detached_action as detached

from actions.server.run_outputs.models import RunExecutionIntent, RunTaskReceipt
from actions.server.run_outputs.task_service import (
    TaskPolicy,
    TaskService,
    TaskUnavailable,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = detached.provider
postgresql_database = detached.postgresql_database
reviewed = detached.reviewed
case = detached.case
pytestmark = detached.pytestmark


class Ready:
    def require_ready(self, actor, snapshot):
        return None


def setup(c, readiness=None):
    owner, service, caller = detached.setup(c)
    return (
        TaskService(
            owner,
            readiness=readiness or Ready(),
            policy=TaskPolicy("test/v1", 60000, 100),
        ),
        owner,
        service,
        caller,
    )


def create(c, tasks, service, caller, key="task"):
    return tasks.create(
        caller.actor,
        service.snapshot.workspace_id,
        service.snapshot,
        {"value": "hello"},
        key,
    )


def test_creation_replay_and_existing_detached_cannot_be_adopted(case):
    c = case
    tasks, owner, service, caller = setup(c)
    first = create(c, tasks, service, caller)
    assert first.status == "working" and first.result is None
    from actions.server.run_outputs.models import RunPin
    from actions.server.run_outputs.service import _one

    assert not _one(c.db, RunPin, first.task_id).current_attempt_id
    assert create(c, tasks, service, caller) == first
    assert len(c.db.all(RunTaskReceipt)) == 1
    owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "old")
    with pytest.raises(TaskUnavailable):
        create(c, tasks, service, caller, "old")
    assert len(c.db.all(RunTaskReceipt)) == 1
    assert len(c.db.all(RunExecutionIntent)) == 2
    tasks.cancel(caller.actor, service.snapshot.workspace_id, first.task_id)
    assert (
        tasks.get(caller.actor, service.snapshot.workspace_id, first.task_id).status
        == "cancelled"
    )


def test_no_host_or_failed_readiness_has_no_admission(case):
    c = case
    tasks, owner, service, caller = setup(c)
    from actions.server._models import Run

    before = len(c.db.all(Run))
    with pytest.raises(ValueError):
        TaskService(owner, readiness=None, policy=TaskPolicy("test", 60000, 100))

    class Unready:
        def require_ready(self, actor, snapshot):
            raise RuntimeError("not configured")

    tasks = TaskService(
        owner, readiness=Unready(), policy=TaskPolicy("test", 60000, 100)
    )
    with pytest.raises(RuntimeError, match="^Task host unavailable$"):
        create(c, tasks, service, caller)
    assert len(c.db.all(Run)) == before
    assert c.db.all(RunExecutionIntent) == [] and c.db.all(RunTaskReceipt) == []


def test_independent_execute_read_cancel_authority(case):
    from actions.server.run_outputs.service import RunOutputControlPlane

    c = case
    tasks, owner, service, caller = setup(c)
    control = RunOutputControlPlane(c.db)
    control.grant(caller.actor, service.snapshot.deployment, {"execute"})
    task = create(c, tasks, service, caller)
    assert create(c, tasks, service, caller) == task
    with pytest.raises(TaskUnavailable):
        tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id)
    control.grant(caller.actor, service.snapshot.deployment, {"cancel"})
    tasks.cancel(caller.actor, service.snapshot.workspace_id, task.task_id)
    with pytest.raises(PermissionError):
        create(c, tasks, service, caller)
    control.grant(caller.actor, service.snapshot.deployment, {"read"})
    assert (
        tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id).status
        == "cancelled"
    )
    with pytest.raises(TaskUnavailable):
        tasks.cancel(caller.actor, service.snapshot.workspace_id, task.task_id)


def test_expiry_keeps_run_and_cannot_refresh_receipt(case, monkeypatch):
    from actions.server._models import Run, RunStatus
    from actions.server.run_outputs import task_service as module
    from actions.server.run_outputs.service import _one

    c = case
    tasks, owner, service, caller = setup(c)
    task = create(c, tasks, service, caller)
    receipt = c.db.all(RunTaskReceipt)[0]
    monkeypatch.setattr(module, "_now", lambda db: task.created_ms + task.ttl_ms)
    for operation in [
        lambda: tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id),
        lambda: tasks.cancel(caller.actor, service.snapshot.workspace_id, task.task_id),
        lambda: create(c, tasks, service, caller),
    ]:
        with pytest.raises(TaskUnavailable):
            operation()
    assert _one(c.db, Run, task.task_id).status == RunStatus.NOT_RUN
    assert c.db.all(RunTaskReceipt) == [receipt]


def test_atomic_insert_and_old_synchronous_adoption_rollback(case, monkeypatch):
    from actions.server._models import Run
    from actions.server.run_outputs import task_service as module
    from actions.server.run_outputs.service import RunOutputControlPlane

    c = case
    tasks, owner, service, caller = setup(c)
    original = module._insert

    def fail(db, row):
        if isinstance(row, RunTaskReceipt):
            raise RuntimeError("receipt insert failed")
        original(db, row)

    monkeypatch.setattr(module, "_insert", fail)
    before = len(c.db.all(Run))
    with pytest.raises(RuntimeError, match="receipt insert failed"):
        create(c, tasks, service, caller)
    assert len(c.db.all(Run)) == before and c.db.all(RunExecutionIntent) == []
    monkeypatch.setattr(module, "_insert", original)
    RunOutputControlPlane(c.db, capabilities=service.registry).register(
        service.snapshot
    )
    c.outputs.admit(caller.actor, service.snapshot, {"value": "hello"}, "sync")
    with pytest.raises(TaskUnavailable):
        create(c, tasks, service, caller, "sync")
    assert c.db.all(RunExecutionIntent) == [] and c.db.all(RunTaskReceipt) == []
    assert len(c.db.all(Run)) == before + 1


def test_concurrent_creation_and_reconstruction(case):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    c = case
    tasks, owner, service, caller = setup(c)
    barrier = Barrier(2)

    def submit():
        with c.db.connect():
            barrier.wait(timeout=10)
            return create(c, tasks, service, caller)

    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda _: submit(), range(2)))
    assert values[0].task_id == values[1].task_id
    assert len(c.db.all(RunTaskReceipt)) == 1
    reconstructed = TaskService(
        owner, readiness=Ready(), policy=TaskPolicy("new-policy", 120000, 200)
    )
    assert (
        reconstructed.get(
            caller.actor, service.snapshot.workspace_id, values[0].task_id
        ).ttl_ms
        == 60000
    )
    with pytest.raises(TaskUnavailable):
        create(c, reconstructed, service, caller)


def test_unknown_actor_workspace_changed_request_and_update_noop(case):
    from uuid import uuid4

    from actions.server.run_outputs.types import Actor

    c = case
    tasks, owner, service, caller = setup(c)
    task = create(c, tasks, service, caller)
    for actor, workspace, taskid in [
        (caller.actor, str(uuid4()), task.task_id),
        (Actor(principal_id=str(uuid4())), service.snapshot.workspace_id, task.task_id),
        (caller.actor, service.snapshot.workspace_id, str(uuid4())),
    ]:
        with pytest.raises(TaskUnavailable):
            tasks.get(actor, workspace, taskid)
    with pytest.raises(ValueError):
        tasks.create(
            caller.actor,
            service.snapshot.workspace_id,
            service.snapshot,
            {"value": "changed"},
            "task",
        )
    tasks.update(
        caller.actor,
        service.snapshot.workspace_id,
        task.task_id,
        {"unknown": {"answer": "ignored"}},
    )
    assert tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id) == task
    with pytest.raises(ValueError):
        tasks.update(
            caller.actor,
            service.snapshot.workspace_id,
            task.task_id,
            {"too-large": "x" * 20000},
        )


def publish(c, owner, service, caller, task, *, failed=False):
    """Synthetic sealed common publication, not genuine RCC execution evidence."""
    import hashlib
    import json
    from uuid import uuid4

    from actions.server._models import RunStatus
    from actions.server.foundry.rcc_execution import GeneratedRccExecution
    from actions.server.run_outputs.service import _canonical

    ticket = owner.claim(caller, task.task_id, service.snapshot.worker)
    compiled = service.registry.load(service.snapshot.capability.package_revision)
    lineage = GeneratedRccExecution._lineage(service.snapshot, None, ticket.fence)
    fixed = {
        "sourceArtifactDigest": compiled.source_artifact_digest,
        "packageRevision": compiled.package_revision_id.root,
        "runtimePlanDigest": service.snapshot.runtime_plan.plan_digest.root,
        "rccSpecificationDigest": compiled.rcc_specification_digest,
        "rccArtifactDigest": compiled.rcc_artifact_digest,
    }
    launch = {
        "id": str(uuid4()),
        "workItemClaim": None,
        "lineage": lineage,
        "inputDigest": "sha256:"
        + hashlib.sha256(_canonical({"value": "hello"}, 262144).encode()).hexdigest(),
        **fixed,
    }
    refs = []
    evidence = []
    for name in [
        "generated-action-result.json",
        "rcc-receipt.json",
        "rcc-stdout.log",
        "rcc-stderr.log",
    ]:
        payload = json.dumps(
            {"private-marker": "not-model-facing", "name": name}
        ).encode()
        if name.endswith(".log"):
            payload = b""
        ref = c.outputs.stage(
            ticket.fence,
            [payload],
            name=name,
            media_type="application/json",
            retention_seconds=3600,
        )
        refs.append(ref)
        evidence.append(
            {
                "name": name,
                "ref": ref.model_dump(mode="json"),
                "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
            }
        )
    execution = {
        "status": "completed",
        "artifactDigest": compiled.rcc_artifact_digest,
        "resultDigest": evidence[0]["digest"],
        "receiptDigest": evidence[1]["digest"],
        "stdout": {
            "digest": evidence[2]["digest"],
            "retainedBytes": evidence[2]["size"],
        },
        "stderr": {
            "digest": evidence[3]["digest"],
            "retainedBytes": evidence[3]["size"],
        },
    }
    record = {
        "version": "actions.generated-rcc-execution/v1",
        "mode": "standalone",
        "claim": None,
        "publicationFence": ticket.fence.model_dump(),
        "lineage": lineage,
        "launch": launch,
        "execution": execution,
        "outputs": evidence,
        "actionResult": {"private-marker": "not-model-facing"},
        **fixed,
    }
    c.outputs.publish(
        caller.actor,
        ticket.fence,
        refs,
        record,
        terminal_status=RunStatus.FAILED if failed else RunStatus.PASSED,
    )
    return ticket, refs


@pytest.mark.parametrize("failed", [False, True])
def test_sealed_terminal_result_is_bounded_and_failed_tool_is_completed(case, failed):
    import json

    from actions.server.run_outputs.service import RunOutputControlPlane

    c = case
    tasks, owner, service, caller = setup(c)
    task = create(c, tasks, service, caller)
    publish(c, owner, service, caller, task, failed=failed)
    result = tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id)
    assert result.status == "completed" and result.result["isError"] is failed
    assert len(result.result["structuredContent"]["outputs"]) == 4
    assert "private-marker" not in json.dumps(result.result)
    assert create(c, tasks, service, caller).result is None
    RunOutputControlPlane(c.db).grant(
        caller.actor, service.snapshot.deployment, {"execute"}
    )
    assert create(c, tasks, service, caller).status == "completed"
    with pytest.raises(TaskUnavailable):
        tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id)


def test_output_expiry_does_not_fabricate_success_or_change_run(case):
    from actions.server._models import Run, RunStatus
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import _one, _update

    c = case
    tasks, owner, service, caller = setup(c)
    task = create(c, tasks, service, caller)
    ticket, refs = publish(c, owner, service, caller, task)
    with c.db.transaction():
        _update(c.db, RunOutput, refs[0].output_id, {"expires_ms": "0"})
    with pytest.raises(TaskUnavailable):
        tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id)
    assert _one(c.db, Run, task.task_id).status == RunStatus.PASSED
    replay = create(c, tasks, service, caller)
    assert replay.status == "completed" and replay.result is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("ttl_ms", "120000"),
        ("original_method", "other"),
        ("created_ms", "1"),
        ("invocation_fingerprint", "changed"),
    ],
)
def test_corrupted_receipt_is_unavailable(case, field, value):
    from actions.server.run_outputs.service import _update

    c = case
    tasks, owner, service, caller = setup(c)
    task = create(c, tasks, service, caller)
    with c.db.transaction():
        _update(c.db, RunTaskReceipt, task.task_id, {field: value})
    with pytest.raises(TaskUnavailable):
        tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id)


def test_host_failure_after_admission_rolls_back(case):
    from actions.server._models import Run

    c = case
    tasks, owner, service, caller = setup(c)

    class FailsAtCommit:
        calls = 0

        def require_ready(self, actor, snapshot):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("worker stopped")

    tasks = TaskService(
        owner, readiness=FailsAtCommit(), policy=TaskPolicy("test", 60000, 100)
    )
    before = len(c.db.all(Run))
    with pytest.raises(RuntimeError, match="^Task host unavailable$"):
        create(c, tasks, service, caller)
    assert (
        len(c.db.all(Run)) == before
        and not c.db.all(RunTaskReceipt)
        and not c.db.all(RunExecutionIntent)
    )


def test_running_cancel_is_pending_and_receipt_clock_is_durable(case):
    c = case
    tasks, owner, service, caller = setup(c)
    task = create(c, tasks, service, caller)
    owner.claim(caller, task.task_id, service.snapshot.worker)
    tasks.cancel(caller.actor, service.snapshot.workspace_id, task.task_id)
    current = tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id)
    assert current.status == "working" and current.result is None
    assert "Cancellation requested" in current.status_message
    assert (
        tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id) == current
    )
    tasks.cancel(caller.actor, service.snapshot.workspace_id, task.task_id)
    assert (
        tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id) == current
    )


@pytest.mark.parametrize(
    "corruption",
    [
        "attempt",
        "fence",
        "outer-version",
        "execution",
        "output-scope",
        "missing-file",
        "boolean-size",
        "boolean-fence",
    ],
)
def test_terminal_corruption_never_yields_success(case, corruption):
    import json

    from actions.server._models import Run
    from actions.server.run_outputs.models import RunAttempt, RunOutput
    from actions.server.run_outputs.service import _canonical, _one, _update

    c = case
    tasks, owner, service, caller = setup(c)
    task = create(c, tasks, service, caller)
    ticket, refs = publish(c, owner, service, caller, task)
    with c.db.transaction():
        if corruption == "attempt":
            _update(c.db, RunAttempt, ticket.fence.attempt_id, {"state": "running"})
        elif corruption == "missing-file":
            _one(c.db, RunOutput, refs[0].output_id)
            # Physical provider loss is simulated through its opener, below.
        else:
            run = _one(c.db, Run, task.task_id)
            record = json.loads(run.result)
            if corruption == "boolean-fence":
                record["result"]["publicationFence"]["epoch"] = True
            if corruption == "fence":
                record["result"]["publicationFence"]["epoch"] += 1
            if corruption == "outer-version":
                record["version"] = True
            if corruption == "execution":
                record["result"]["execution"] = {}
            if corruption == "boolean-size":
                record["result"]["outputs"][2]["size"] = False
            if corruption == "output-scope":
                record["outputs"][0]["run_id"] = record["outputs"][0]["output_id"]
            _update(c.db, Run, run.id, {"result": _canonical(record, 1048576)})
    if corruption == "missing-file":
        from unittest.mock import patch

        provider = c.outputs.providers[service.snapshot.provider_key]
        with patch.object(
            provider, "open", side_effect=FileNotFoundError("private-path")
        ):
            with pytest.raises(TaskUnavailable, match="^Task unavailable$"):
                tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id)
    else:
        with pytest.raises(TaskUnavailable):
            tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id)


def test_workspace_revocation_and_admission_outcome_identity(case):
    from dataclasses import asdict

    from actions.server.run_outputs.models import RunPin, Workspace
    from actions.server.run_outputs.service import _one, _update

    c = case
    tasks, owner, service, caller = setup(c)
    first = owner.admit_outcome(
        caller.actor, service.snapshot, {"value": "hello"}, "ordinary"
    )
    before = asdict(_one(c.db, RunPin, first.run.id))
    assert first.created is True
    assert (
        owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "ordinary")
        == first.run
    )
    assert (
        owner.admit_outcome(
            caller.actor, service.snapshot, {"value": "hello"}, "ordinary"
        ).created
        is False
    )
    assert asdict(_one(c.db, RunPin, first.run.id)) == before
    task = create(c, tasks, service, caller)
    with c.db.transaction():
        _update(c.db, Workspace, service.snapshot.workspace_id, {"state": "inactive"})
    with pytest.raises(TaskUnavailable):
        tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id)
