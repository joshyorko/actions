# ruff: noqa: F811, F401
"""Public standalone admission must select Robot receipts without manual seeding."""
import json

import pytest
from actions.server._models import Run
from actions.server.foundry.logical_receipts import (
    generated_output_names,
    validate_bound_record,
    versions_for_selection,
)
from actions.server.run_outputs.service import FenceRejected, _one

from action_server_tests.test_robot_package_admission import admitted, disable_feedback
from action_server_tests.test_robot_runtime_runner import case

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def test_public_dispatch_and_terminal_receipt_join(case, monkeypatch):
    c = case
    ticket = c.service.dispatch_standalone(c.caller, {"value": "joined"}, "public-join")
    run = _one(c.db, Run, ticket.fence.run_id)
    assert json.loads(run.result)["version"] == "actions.robot-dispatch/v1"
    run = c.runner.execute(c.caller, ticket, c.service)
    assert c.service.ticket(c.caller, run) == ticket
    outer = json.loads(run.result)

    def no_provider(*args, **kwargs):
        raise AssertionError("retained receipt read must use SQL only")

    monkeypatch.setattr(c.provider, "open", no_provider)
    monkeypatch.setattr(c.registry, "get_capability", no_provider)
    validate_bound_record(
        c.db,
        c.registry,
        c.service.snapshot,
        run,
        ticket.fence,
        outer["result"],
        claim=None,
        terminal=True,
        outputs=outer["outputs"],
    )
    assert generated_output_names(outer["result"]) == {
        "robot-stdout.log",
        "robot-stderr.log",
        "robot-output.xml",
    }


def test_robot_versions_come_from_retained_kind(case):
    c = case
    assert versions_for_selection(c.registry, c.service.snapshot) == (
        "actions.robot-dispatch/v1",
        "actions.robot-execution/v1",
    )


def test_python_version_cannot_downgrade_robot_validation(case):
    c = case
    run = _one(c.db, Run, c.ticket.fence.run_id)
    record = json.loads(run.result)
    record["version"] = "actions.generated-rcc-dispatch/v1"
    with c.db.transaction():
        c.db.update_by_id(Run, run.id, {"result": json.dumps(record)})
    run = _one(c.db, Run, run.id)
    with pytest.raises((FenceRejected, ValueError)):
        validate_bound_record(
            c.db,
            c.registry,
            c.service.snapshot,
            run,
            c.ticket.fence,
            record,
            claim=None,
            terminal=False,
        )


def test_detached_worker_uses_robot_runner(case, tmp_path):
    from actions.server.foundry.robot_runtime_profile import RuntimeCapabilityRunner
    from actions.server.run_outputs.detached import (
        DetachedActions,
        DetachedActionWorker,
    )

    c = case

    class NoPython:
        def execute(self, *args):
            raise AssertionError("Robot must not enter generated Python execution")

    runners = RuntimeCapabilityRunner(NoPython(), direct_robot=c.runner)
    authority = DetachedActions(c.service.deployments, c.service.base)
    run = authority.admit(
        c.actor, c.service.snapshot, {"value": "detached"}, "detached-robot"
    )
    worker = DetachedActionWorker(
        authority,
        c.actor,
        c.caller.worker_id,
        c.service.snapshot.worker,
        capability_runner=runners,
    )
    ticket = worker.claim(run.id)
    result = worker.execute(
        ticket, prepared=None, rcc=tmp_path / "unused", execution_root=tmp_path
    )
    assert (
        json.loads(result.result)["result"]["version"] == "actions.robot-execution/v1"
    )


def test_robot_cancellation_callable_blocks_launch(case):
    c = case
    with pytest.raises(FenceRejected, match="cancelled"):
        c.runner.execute(c.caller, c.ticket, c.service, cancelled=lambda: True)
    assert json.loads(_one(c.db, Run, c.ticket.fence.run_id).result)["launch"] is None


def test_robot_task_result_uses_sealed_robot_inventory(case, tmp_path):
    from actions.server.foundry.robot_runtime_profile import RuntimeCapabilityRunner
    from actions.server.run_outputs.detached import (
        DetachedActions,
        DetachedActionWorker,
    )
    from actions.server.run_outputs.task_service import (
        TaskPolicy,
        TaskService,
        TaskUnavailable,
    )

    c = case

    class Ready:
        def require_ready(self, actor, snapshot):
            assert actor == c.actor and snapshot == c.service.snapshot

    from uuid import uuid4

    from actions.server.foundry.models import FoundryAccessGrant

    with c.db.transaction():
        c.db.insert(
            FoundryAccessGrant(
                str(uuid4()),
                c.service.snapshot.workspace_id,
                c.actor.principal_id,
                "workspace",
                c.service.snapshot.workspace_id,
                '["read_application"]',
            )
        )
    owner = DetachedActions(c.service.deployments, c.service.base)
    tasks = TaskService(
        owner, readiness=Ready(), policy=TaskPolicy("robot-test/v1", 60000, 100)
    )
    task = tasks.create(
        c.actor,
        c.service.snapshot.workspace_id,
        c.service.snapshot,
        {"value": "task"},
        "robot-task",
    )
    worker = DetachedActionWorker(
        owner,
        c.actor,
        c.caller.worker_id,
        c.service.snapshot.worker,
        capability_runner=RuntimeCapabilityRunner(None, direct_robot=c.runner),
    )
    ticket = worker.claim(task.task_id)
    assert (
        tasks.get(c.actor, c.service.snapshot.workspace_id, task.task_id).status
        == "working"
    )
    worker.execute(
        ticket, prepared=None, rcc=tmp_path / "unused", execution_root=tmp_path
    )
    completed = tasks.get(c.actor, c.service.snapshot.workspace_id, task.task_id)
    assert completed.status == "completed"
    assert completed.result["isError"] is False
    assert len(completed.result["structuredContent"]["outputs"]) == 3
    c.control.grant(c.actor, c.service.snapshot.deployment, {"execute"})
    with pytest.raises(TaskUnavailable):
        tasks.get(c.actor, c.service.snapshot.workspace_id, task.task_id)


def test_robot_host_stop_at_publication_keeps_outputs_provisional(case):
    from actions.server._models import RunStatus
    from actions.server.run_outputs.models import RunOutput

    c = case
    with pytest.raises(FenceRejected, match="publication cancelled"):
        c.runner.execute(
            c.caller,
            c.ticket,
            c.service,
            publication_cancelled=lambda: True,
        )
    assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.RUNNING
    assert all(row.state == "provisional" for row in c.db.all(RunOutput))


def test_robot_readiness_requires_current_activated_deployment(case, monkeypatch):
    c = case
    c.runner.require_ready(c.service)
    monkeypatch.setattr(
        c.service.deployments._repository, "was_activated", lambda ref: False
    )
    with pytest.raises(PermissionError, match="activated"):
        c.runner.require_ready(c.service)


def test_model_handles_validate_zero_requirement_robot_receipt(case):
    from uuid import uuid4

    from actions.server.foundry.generic_execution_port import GenericCanvasExecution
    from actions.server.foundry.models import FoundryAccessGrant

    c = case
    with c.db.transaction():
        c.db.insert(
            FoundryAccessGrant(
                str(uuid4()),
                c.service.snapshot.workspace_id,
                c.actor.principal_id,
                "workspace",
                c.service.snapshot.workspace_id,
                '["read_application"]',
            )
        )
    run = c.runner.execute(c.caller, c.ticket, c.service)
    port = object.__new__(GenericCanvasExecution)
    assert len(port._handles(c.caller, c.service, run)) == 3
    outer = json.loads(run.result)
    outer["result"]["returnCode"] = False
    with c.db.transaction():
        c.db.update_by_id(Run, run.id, {"result": json.dumps(outer)})
    with pytest.raises(FenceRejected):
        port._handles(c.caller, c.service, _one(c.db, Run, run.id))


def test_canvas_profile_accepts_only_verified_direct_robot(case, monkeypatch):
    from actions.server.deployments.foundry_values import AccessDenied
    from actions.server.foundry.execution_profiles import (
        select_canvas_execution_profile,
        select_rcc_execution_profile,
    )

    c = case
    snapshot = c.service.snapshot
    assert snapshot.runtime_kind == "direct"
    with pytest.raises(AccessDenied, match="Pinned RCC Runtime"):
        select_rcc_execution_profile(
            c.service.deployments, c.actor, snapshot.deployment, snapshot.capability
        )
    result = select_canvas_execution_profile(
        c.service.deployments,
        c.actor,
        snapshot.deployment,
        snapshot.capability,
        registry=c.registry,
    )
    assert result.snapshot == snapshot
    monkeypatch.setattr(c.registry, "selection_for", lambda *args: object())
    with pytest.raises(AccessDenied, match="verified direct Robot"):
        select_canvas_execution_profile(
            c.service.deployments,
            c.actor,
            snapshot.deployment,
            snapshot.capability,
            registry=c.registry,
        )


def test_direct_canvas_profile_keeps_registry_and_profile_authority(case, monkeypatch):
    import copy

    from actions.server.deployments.foundry_values import AccessDenied
    from actions.server.foundry.execution_profiles import (
        select_canvas_execution_profile,
    )

    c = case
    snapshot = c.service.snapshot
    args = (c.service.deployments, c.actor, snapshot.deployment, snapshot.capability)
    with pytest.raises(AccessDenied, match="verified direct Robot"):
        select_canvas_execution_profile(*args, registry=copy.copy(c.registry))
    resolved = c.service.deployments.resolve(
        c.actor,
        snapshot.deployment.workspace_id,
        snapshot.deployment.deployment_id,
        snapshot.capability,
        revision=snapshot.deployment,
    )
    forged = resolved.model_copy(
        update={
            "snapshot": resolved.snapshot.model_copy(
                update={
                    "worker": snapshot.worker.model_copy(
                        update={
                            "revision_id": type(snapshot.worker.revision_id)(
                                "sha256:" + "9" * 64
                            )
                        }
                    )
                }
            )
        }
    )
    monkeypatch.setattr(c.service.deployments, "resolve", lambda *a, **kw: forged)
    with pytest.raises(AccessDenied, match="profile identity differs"):
        select_canvas_execution_profile(*args, registry=c.registry)


def test_direct_canvas_profile_rejects_retained_plan_kind_mismatch(case, monkeypatch):
    from dataclasses import replace

    from actions.server.deployments.foundry_values import AccessDenied
    from actions.server.foundry.execution_profiles import (
        select_canvas_execution_profile,
    )

    c = case
    snapshot = c.service.snapshot
    selected = c.registry.selection_for(snapshot.capability, snapshot.runtime_plan)
    wrong_plan = replace(selected.robot.robot.plan, runtime_kind="rcc")
    wrong = replace(
        selected,
        robot=replace(
            selected.robot, robot=replace(selected.robot.robot, plan=wrong_plan)
        ),
    )
    monkeypatch.setattr(c.registry, "selection_for", lambda *args: wrong)
    with pytest.raises(AccessDenied, match="verified direct Robot"):
        select_canvas_execution_profile(
            c.service.deployments,
            c.actor,
            snapshot.deployment,
            snapshot.capability,
            registry=c.registry,
        )
