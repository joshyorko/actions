"""Opt-in real Task host consumption/shutdown; no MCP or process-restart claim."""
import json
import os
import time
from pathlib import Path

import pytest
from action_server_tests import test_generic_canvas_view as app_tests
from action_server_tests.test_invoice_worker import (
    retain_worker_cell as retain_worker_cell,
)
from contract_tests.test_package_revision_compiler import _generated_action_entries

from actions.server._models import Run, RunStatus
from actions.server.deployments.package_revision_compiler import (
    load_prepared_rcc_environment,
)
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import _one
from actions.server.run_outputs.task_host import DetachedTaskHost
from actions.server.run_outputs.task_service import (
    TaskHostUnavailable,
    TaskPolicy,
    TaskService,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = app_tests.provider
postgresql_database = app_tests.postgresql_database
reviewed = app_tests.reviewed
pytestmark = app_tests.pytestmark


def observe(predicate, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.05)
    pytest.fail("bounded real host observation timed out")


@pytest.mark.parametrize(
    "stop_active,allow_cancel", [(False, True), (True, True), (True, False)]
)
def test_actual_task_host_consumes_and_stops(
    reviewed, foundry_package_store, tmp_path, monkeypatch, stop_active, allow_cancel
):
    if os.environ.get("ACTIONS_TASK_HOST_REAL_RCC") != "1":
        pytest.skip("exclusive prepared Task host RCC fixture required")
    action = b"""from actions import action
import os,time
from pathlib import Path
@action
def generated_echo(value: str) -> str:
    if value == "pause":
        (Path(os.environ["TMPDIR"])/"task-host-entered").write_text("owned synthetic test")
        time.sleep(30)
    if value == "hello":
        time.sleep(0.25)
    return value
"""
    original = app_tests.fixtures.setup_activated
    monkeypatch.setattr(
        app_tests.fixtures,
        "setup_activated",
        lambda r, store: original(
            r,
            store,
            real=True,
            backend_entries=_generated_action_entries(action),
            logical_key="real-task-host",
        ),
    )
    c = app_tests.case.__wrapped__(reviewed, foundry_package_store)
    service, caller = c.port._selected(c.app, "run")
    authority = DetachedActions(c.deployments, c.outputs)
    root = tmp_path / "execution"
    root.mkdir()
    host = DetachedTaskHost(
        authority,
        actor=caller.actor,
        worker_id=caller.worker_id,
        profile=service.snapshot.worker,
        prepared=load_prepared_rcc_environment(
            Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
        ),
        rcc=Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]),
        execution_root=root,
        policy=TaskPolicy("real-host/v1", 600000, 50),
    )
    tasks = TaskService(authority, readiness=host, policy=host.policy)
    if not allow_cancel:
        from actions.server.run_outputs.service import RunOutputControlPlane

        RunOutputControlPlane(c.db).grant(
            caller.actor, service.snapshot.deployment, {"execute", "read"}
        )
    host.start()
    try:
        task = tasks.create(
            caller.actor,
            service.snapshot.workspace_id,
            service.snapshot,
            {"value": "pause" if stop_active else "hello"},
            "actual-host",
        )
        assert task.status == "working" and task.result is None
        assert _one(c.db, Run, task.task_id).status != RunStatus.PASSED
        if stop_active:
            # Written by actual generated Python in its private TMPDIR; no source
            # mutation or arbitrary external effect. This proves entry, not a mock.
            observe(
                lambda: list((root / task.task_id).glob("*/*/tmp/task-host-entered"))
            )
            assert host.close(20)
            current = tasks.get(
                caller.actor, service.snapshot.workspace_id, task.task_id
            )
            assert current.status == "working" and current.result is None
            row = _one(c.db, Run, task.task_id)
            assert row.status == RunStatus.RUNNING and json.loads(row.result)["launch"]
            assert _one(c.db, RunPin, task.task_id).cancel_requested == int(
                allow_cancel
            )
            assert (
                "Cancellation requested" if allow_cancel else "Launch recorded"
            ) in current.status_message
            assert not host.failed
            with pytest.raises(TaskHostUnavailable):
                tasks.create(
                    caller.actor,
                    service.snapshot.workspace_id,
                    service.snapshot,
                    {"value": "hello"},
                    "after-close",
                )
        else:
            completed = observe(
                lambda: (
                    state
                    if (
                        state := tasks.get(
                            caller.actor, service.snapshot.workspace_id, task.task_id
                        )
                    ).status
                    == "completed"
                    else None
                )
            )
            assert completed.result["isError"] is False
            outputs = completed.result["structuredContent"]["outputs"]
            assert len(outputs) == 4
            found = False
            for item in outputs:
                with c.outputs.resolve(
                    caller.actor, service.snapshot.workspace_id, item["handle"]
                ) as output:
                    if output.name == "generated-action-result.json":
                        assert json.loads(output.read()) == "hello"
                        found = True
            assert found
            replay = tasks.create(
                caller.actor,
                service.snapshot.workspace_id,
                service.snapshot,
                {"value": "hello"},
                "actual-host",
            )
            assert replay.task_id == task.task_id and replay.result is None
        pin = _one(c.db, RunPin, task.task_id)
        assert len(c.db.all(RunAttempt, where="run_id=?", values=[task.task_id])) == 1
        assert _one(c.db, RunAttempt, pin.current_attempt_id).state == (
            "running" if stop_active else "succeeded"
        )
    finally:
        assert host.close(30), "retain provider: Task worker has not stopped"
