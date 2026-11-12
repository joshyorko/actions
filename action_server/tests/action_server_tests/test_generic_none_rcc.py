"""Opt-in real ordinary generated package app execution, with common SQL authority."""
import os
from pathlib import Path

import pytest
from action_server_tests import test_generic_canvas_view as app_tests
from contract_tests.test_package_revision_compiler import _generated_action_entries

from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.deployments.package_revision_compiler import (
    load_prepared_rcc_environment,
)
from actions.server.foundry.generic_execution_port import PinnedGenericRccRunner
from actions.server.run_outputs.models import RunAttempt
from actions.server.run_outputs.service import _one

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = app_tests.provider
postgresql_database = app_tests.postgresql_database
reviewed = app_tests.reviewed
pytestmark = app_tests.pytestmark


def test_actual_none_app_submit_execute_replay(
    reviewed, foundry_package_store, tmp_path, monkeypatch
):
    if os.environ.get("ACTIONS_GENERIC_NONE_REAL_RCC") != "1":
        pytest.skip("exclusive prepared ordinary RCC cache required")
    original = app_tests.fixtures.setup_activated
    monkeypatch.setattr(
        app_tests.fixtures,
        "setup_activated",
        lambda r, store: original(
            r,
            store,
            real=True,
            backend_entries=_generated_action_entries(),
            logical_key="ordinary-generic-echo",
        ),
    )
    c = app_tests.case.__wrapped__(reviewed, foundry_package_store)
    root = tmp_path / "ordinary-execution"
    root.mkdir()
    trusted = PinnedGenericRccRunner(
        load_prepared_rcc_environment(
            Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
        ),
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]),
        root,
    )

    class Runner:
        calls = 0

        def execute(self, caller, ticket, service):
            self.calls += 1
            return trusted.execute(caller, ticket, service)

    runner = Runner()
    c.port.execution.runner = runner
    before = len(c.db.all(FencedWorkItem))
    state = app_tests.submit(c)
    assert state["state"] == "ready" and runner.calls == 0
    service, _ = c.port._selected(c.app, "run")
    declaration = service.registry.get_capability(
        service.snapshot.capability
    ).work_items
    assert declaration.mode == "none" and not declaration.allow_outputs
    revision = c.repository.get_revision(c.scope.deployment)
    assert not revision.revision.specification.work_item_policies
    done = app_tests.call(
        c, "canvas_dispatch", app_tests.request(state, action="execute")
    ).execution
    assert done["state"] == "completed" and len(done["outputs"]) == 4
    assert _one(c.db, RunAttempt, done["attemptId"]).state == "succeeded"
    assert len(c.db.all(FencedWorkItem)) == before
    assert (
        app_tests.call(
            c, "canvas_dispatch", app_tests.request(state, action="execute")
        ).execution
        == done
    )
    assert app_tests.submit(c)["runId"] == done["runId"]
    assert runner.calls == 1
    import json

    result = json.loads(_one(c.db, Run, done["runId"]).result)
    assert result["result"]["actionResult"] == "hello"

    import asyncio

    from action_server_tests.test_generic_execution_port import ReviewedStub

    from actions.server.foundry.generic_execution_port import GenericCanvasExecution
    from actions.server.managed_work_items.authorization import SqlQueueAuthorization

    model = GenericCanvasExecution(
        ReviewedStub(),
        c.deployments,
        c.outputs,
        SqlQueueAuthorization(c.db),
        worker_id=c.worker,
        runner=runner,
    )
    request = dict(
        mode="generic",
        snapshot=service.snapshot.model_dump(mode="json"),
        inputs={"value": "headless"},
        idempotencyKey="actual-ordinary-model",
    )
    headless = asyncio.run(model.call(c.model, "capability_invoke", request))
    execution = headless.model_result["execution"]
    assert execution["state"] == "completed" and execution["workItemId"] is None
    assert len(execution["outputs"]) == 4
    assert (
        asyncio.run(model.call(c.model, "capability_invoke", request)).model_result
        == headless.model_result
    )
    assert runner.calls == 2 and len(c.db.all(FencedWorkItem)) == before
    assert execution["runId"] != done["runId"]
