"""Opt-in actual RCC app input/output qualification; no process-restart claim."""
import json
import os
from pathlib import Path

import pytest
from action_server_tests import test_generic_canvas_view as app_tests
from action_server_tests.test_generic_canvas_view import fixtures, grant

from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.deployments.package_revision_compiler import (
    PinnedRccPackageBuildExecutor,
    load_prepared_rcc_environment,
)
from actions.server.foundry.generic_execution_port import PinnedGenericRccRunner
from actions.server.foundry.mcp import CanvasCaller
from actions.server.run_outputs.models import RunAttempt
from actions.server.run_outputs.service import _one

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = app_tests.provider
postgresql_database = app_tests.postgresql_database
reviewed = app_tests.reviewed
pytestmark = app_tests.pytestmark


def configure(case, mode, prepared):
    from contract_tests.test_package_revision_compiler import _generated_action_entries

    from actions.server.deployments.foundry_values import (
        CapabilityPlanPolicy,
        CapabilityWorkItemPolicy,
        DeploymentSpecification,
        WorkItemDeclaration,
    )
    from actions.server.foundry.authoring_values import CanvasBinding
    from actions.server.foundry.sql_authorization import reference_grant_subject
    from actions.server.managed_work_items.contracts import Permission
    from actions.server.run_outputs.service import RunOutputControlPlane
    from actions.server.run_outputs.types import CanvasResultScope

    c = case
    registry = c.outputs.capabilities
    registry._executor = PinnedRccPackageBuildExecutor(prepared)
    entries = _generated_action_entries(
        b"from actions import action\n@action\ndef generated_echo(value: str) -> dict:\n    return {'result': value, 'workItems': [{'value': value + ' child'}]}\n"
    )
    from contract_tests.test_package_revision_compiler import _entry

    entries[-1] = _entry(
        "tests/test_generated_action.py",
        b"import unittest\nfrom generated_actions import generated_echo\nclass GenericTest(unittest.TestCase):\n    def test_echo(self):\n        self.assertEqual(generated_echo('synthetic')['result'], 'synthetic')\n",
    )
    compiled = registry.compile_trusted_source(
        entries,
        logical_package_key="app-" + mode,
        logical_name="App " + mode,
        trusted_actor=c.actor,
        workspace_id=c.scope.deployment.workspace_id,
        application_id=c.scope.deployment.deployment_id,
        work_items=WorkItemDeclaration(mode=mode, allow_outputs=True),
    )
    assert compiled.evidence.ready, compiled.evidence
    package = registry.admit_compiled(
        c.actor, c.scope.deployment.workspace_id, compiled.compiled_package
    )
    capability = registry.capability_refs(package)[0]
    plan = registry.get_capability(capability).runtime_plans[0]
    policy = CapabilityWorkItemPolicy(
        capability=capability,
        input_mode="none" if mode == "producer" else "claim",
        input_queue=None if mode == "producer" else "input",
        output_queue="output" if mode == "producer" else "input_output",
        max_output_items=32,
        max_output_bytes=1024,
    )
    selection = DeploymentSpecification(
        package_revisions=(package,),
        capability_plans=(
            CapabilityPlanPolicy(
                capability=capability,
                mode="locked",
                allowed_plans=(plan,),
                default_plan=plan,
            ),
        ),
        worker=c.selection.worker,
        policy=c.selection.policy,
        output_provider=c.selection.output_provider,
        work_item_policies=(policy,),
    )
    revised = c.authority.apply(
        c.actor,
        c.staged.ref.workspace_id,
        c.staged.application_id,
        c.staged.ref,
        json.dumps(c.spec).encode(),
        (CanvasBinding("run", capability),),
        (package,),
        selection,
        registry.evidence(package),
        fixtures.fingerprint(mode),
        idempotency_key=mode,
    )
    c.authority.release(
        c.actor,
        c.staged.ref.workspace_id,
        c.staged.application_id,
        revised.ref,
        c.staged.ref,
        fixtures.fingerprint(mode + "-release"),
        idempotency_key=mode + "-release",
    )
    stored = c.repository.get_revision(revised.ref)
    c.scope = CanvasResultScope(
        deployment=revised.ref,
        application=stored.revision.specification.canvas_application,
    )
    c.app = CanvasCaller(c.actor, c.scope.application.workspace_id, "app", c.scope)
    grant(
        c.db,
        c.actor,
        c.scope.deployment.workspace_id,
        "workspace",
        c.scope.application.workspace_id,
        [p.value for p in Permission],
    )
    grant(
        c.db,
        c.actor,
        c.scope.deployment.workspace_id,
        "reference",
        reference_grant_subject(revised.ref),
        ["execute", *[p.value for p in Permission]],
    )
    RunOutputControlPlane(c.db, capabilities=registry).grant(
        c.actor, revised.ref, {"execute", "read", "cancel"}
    )

    return c


@pytest.mark.parametrize("mode", ["consumer", "producer"])
def test_actual_input_output_app(reviewed, foundry_package_store, tmp_path, mode):
    if os.environ.get("ACTIONS_GENERIC_INPUT_OUTPUT_REAL_RCC") != "1":
        pytest.skip("exclusive prepared input/output RCC cache required")
    prepared = load_prepared_rcc_environment(
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
    )
    c = configure(
        app_tests.case.__wrapped__(reviewed, foundry_package_store), mode, prepared
    )
    execution_root = tmp_path / "execution"
    execution_root.mkdir()
    trusted = PinnedGenericRccRunner(
        prepared, Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]), execution_root
    )

    class Runner:
        calls = 0

        def execute(self, caller, ticket, service):
            self.calls += 1
            return trusted.execute(caller, ticket, service)

    runner = Runner()
    c.port.execution.runner = runner
    service, caller = c.port._selected(c.app, "run")
    parent = None
    submit = dict(
        mode="generic",
        action="submit",
        bindingId="run",
        inputs={"value": "hello"},
        idempotencyKey="actual-output",
    )
    if mode == "consumer":
        parent = service.enqueue(caller, {"value": "hello"}, "actual-input")
        queue = service.queue_ref(service.policy.input_queue).model_dump(mode="json")
        page = app_tests.call(
            c,
            "canvas_get_state",
            dict(mode="generic", action="inputs", bindingId="run", queue=queue),
        ).execution
        assert parent in [item["itemId"] for item in page["items"]]
        submit = dict(
            mode="generic",
            action="submit_input",
            bindingId="run",
            queue=queue,
            itemId=parent,
            idempotencyKey="actual-selection",
        )
    else:
        assert not c.db.all(FencedWorkItem)
    before_runs = len(c.db.all(Run))
    state = app_tests.call(c, "canvas_dispatch", submit).execution
    assert state["state"] == "ready" and runner.calls == 0
    assert len(c.db.all(Run)) == before_runs + 1
    assert (
        app_tests.call(c, "canvas_dispatch", submit).execution["runId"]
        == state["runId"]
    )
    done = app_tests.call(
        c, "canvas_dispatch", app_tests.request(state, action="execute")
    ).execution
    assert done["state"] == "completed" and runner.calls == 1
    attempt = _one(c.db, RunAttempt, done["attemptId"])
    assert attempt.state == "succeeded"
    children = [
        row
        for row in c.db.all(FencedWorkItem)
        if row.queue_name == service.policy.output_queue
    ]
    assert len(children) == 1
    child = children[0]
    payload = json.loads(child.payload)
    assert payload["payload"] == {"value": "hello child"}
    assert payload["produced_by"]["snapshot"] == service.snapshot.model_dump(
        mode="json"
    )
    assert payload["produced_by"]["fence"]["run_id"] == done["runId"]
    assert payload["produced_by"]["fence"]["attempt_id"] == done["attemptId"]
    assert payload["produced_by"]["parent_id"] == parent
    ticket = c.port._ticket(service, caller, _one(c.db, Run, done["runId"]))
    assert payload["produced_by"]["fence"] == ticket.fence.model_dump(mode="json")
    assert payload["produced_by"]["input_digest"] == ticket.input_digest
    if parent:
        row = _one(c.db, FencedWorkItem, parent)
        assert row.state == "COMPLETED" and not row.claim_owner
        assert row.claim_epoch == ticket.claim.epoch
    assert child.parent_id == (parent or "")
    result = json.loads(_one(c.db, Run, done["runId"]).result)
    assert result["result"]["actionResult"]["result"] == "hello"
    page = app_tests.call(
        c, "canvas_get_state", app_tests.request(done, action="outputs")
    ).execution
    assert [item["itemId"] for item in page["items"]] == [child.id]
    counts = (
        len(c.db.all(Run)),
        len(c.db.all(RunAttempt)),
        len(c.db.all(FencedWorkItem)),
    )
    assert (
        app_tests.call(
            c, "canvas_dispatch", app_tests.request(state, action="execute")
        ).execution
        == done
    )
    assert (
        app_tests.call(c, "canvas_dispatch", submit).execution["runId"] == done["runId"]
    )
    assert runner.calls == 1
    assert counts == (
        len(c.db.all(Run)),
        len(c.db.all(RunAttempt)),
        len(c.db.all(FencedWorkItem)),
    )
    # Reopen projection in the same service instance, not process restart.
    reopened = app_tests.call(c, "canvas_get", {}, c.model).generic_interaction[
        "executions"
    ][0]
    assert reopened["runId"] == done["runId"] and reopened["outputs"] == done["outputs"]
    for output in reopened["outputs"]:
        artifact = app_tests.call(
            c, "canvas_artifact", app_tests.request(reopened, handle=output["handle"])
        ).artifact
        assert artifact is not None
    assert runner.calls == 1
