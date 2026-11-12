"""Ordinary none model discovery/invocation joins the same Run authority."""
import asyncio
import json
from uuid import uuid4

import pytest
from action_server_tests import test_generic_canvas_view as app_tests
from action_server_tests.test_generic_execution_port import (
    ReviewedStub,
    SyntheticRunner,
)

from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.generic_execution_port import GenericCanvasExecution
from actions.server.foundry.invocation_discovery import GenericInvocationDiscovery
from actions.server.foundry.mcp import CanvasReply
from actions.server.managed_work_items.authorization import SqlQueueAuthorization
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import AccessDenied, FenceRejected, _update

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = app_tests.provider
postgresql_database = app_tests.postgresql_database
reviewed = app_tests.reviewed
case = app_tests.case
pytestmark = app_tests.pytestmark


def wrapper(c):
    runner = SyntheticRunner()
    port = GenericCanvasExecution(
        ReviewedStub(),
        c.deployments,
        c.outputs,
        SqlQueueAuthorization(c.db),
        worker_id=c.worker,
        runner=runner,
    )
    service, _ = c.port._selected(c.app, "run")
    request = dict(
        mode="generic",
        snapshot=service.snapshot.model_dump(mode="json"),
        inputs={"value": "hello"},
        idempotencyKey="ordinary-model",
    )
    return port, runner, request


def invoke(c, port, request):
    return asyncio.run(port.call(c.model, "capability_invoke", request))


def test_none_descriptor_invokes_without_queue_policy_or_item(case):
    c = case
    before = len(c.db.all(FencedWorkItem))
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.run_outputs.models import RunAccessGrant

    grants = len(c.db.all(FoundryAccessGrant)) + len(c.db.all(RunAccessGrant))
    port, runner, request = wrapper(c)
    discovery = GenericInvocationDiscovery(
        c.deployments, c.outputs, SqlQueueAuthorization(c.db)
    )
    reply = CanvasReply(
        "canonical",
        model_result={
            "applicationId": str(c.scope.deployment.deployment_id.root),
            "revisionId": c.scope.deployment.revision_id.root,
        },
    )
    described = discovery.describe(
        c.model,
        "canvas_get",
        {"appId": str(c.scope.deployment.deployment_id.root)},
        reply,
    )
    descriptor = described.model_result["invocationDescriptors"][0]
    assert (
        descriptor["inputMode"] == "none"
        and descriptor["inputQueue"] is None
        and descriptor["standaloneAllowed"]
    )
    assert descriptor["snapshot"] == request["snapshot"]
    assert "appSession" not in json.dumps(descriptor)
    result = invoke(c, port, request)
    assert result.model_result["execution"]["state"] == "completed"
    assert result.model_result["execution"]["workItemId"] is None
    assert result.model_result["execution"]["outputs"]
    assert invoke(c, port, request).model_result == result.model_result
    assert runner.calls == 1 and len(c.db.all(FencedWorkItem)) == before
    assert len(c.db.all(FoundryAccessGrant)) + len(c.db.all(RunAccessGrant)) == grants


@pytest.mark.parametrize(
    "corruption", ["attempt-state", "epoch", "cancel", "journal-version"]
)
def test_none_terminal_replay_rejects_corruption(case, corruption):
    from actions.server._models import Run
    from actions.server.run_outputs.service import _canonical, _one

    c = case
    port, runner, request = wrapper(c)
    result = invoke(c, port, request).model_result["execution"]
    with c.db.transaction():
        if corruption == "attempt-state":
            _update(c.db, RunAttempt, result["attemptId"], {"state": "running"})
        elif corruption == "epoch":
            _update(
                c.db, RunPin, result["runId"], {"epoch": result["attemptEpoch"] + 1}
            )
        elif corruption == "cancel":
            _update(c.db, RunPin, result["runId"], {"cancel_requested": 1})
        else:
            row = _one(c.db, Run, result["runId"])
            value = json.loads(row.result)
            value["version"] = True
            _update(c.db, Run, row.id, {"result": _canonical(value, 524288)})
    with pytest.raises(FenceRejected):
        invoke(c, port, request)
    assert runner.calls == 1


def test_none_claim_and_app_audience_fail_closed(case):
    c = case
    port, runner, request = wrapper(c)
    with pytest.raises(AccessDenied):
        asyncio.run(port.call(c.app, "capability_invoke", request))
    from actions.server.managed_work_items.contracts import ClaimRef, QueueRef

    service, _ = c.port._selected(c.app, "run")
    request.pop("inputs")
    request.pop("idempotencyKey")
    request["claim"] = ClaimRef(
        queue=QueueRef(
            workspace_id=c.scope.deployment.workspace_id,
            deployment=c.scope.deployment,
            queue_id="invented",
        ),
        item_id=str(uuid4()),
        owner_id=c.worker,
        epoch=1,
    ).model_dump(mode="json")
    with pytest.raises(AccessDenied):
        invoke(c, port, request)
    assert runner.calls == 0


def test_none_discovery_and_replay_reauthorize_execute(case, monkeypatch):
    c = case
    port, runner, request = wrapper(c)
    invoke(c, port, request)
    original = c.outputs._authorize

    def authorize(actor, snapshot, permission):
        if permission == "execute":
            raise AccessDenied("ordinary execution grant revoked")
        return original(actor, snapshot, permission)

    monkeypatch.setattr(c.outputs, "_authorize", authorize)
    reply = CanvasReply(
        "canonical",
        model_result={
            "applicationId": str(c.scope.deployment.deployment_id.root),
            "revisionId": c.scope.deployment.revision_id.root,
        },
    )
    discovery = GenericInvocationDiscovery(
        c.deployments, c.outputs, SqlQueueAuthorization(c.db)
    )
    assert (
        discovery.describe(
            c.model,
            "canvas_get",
            {"appId": str(c.scope.deployment.deployment_id.root)},
            reply,
        ).model_result["invocationDescriptors"]
        == []
    )
    with pytest.raises(AccessDenied):
        invoke(c, port, request)
    assert runner.calls == 1


def test_none_retained_uncertain_launch_is_never_retried(case):
    from actions.server._models import Run
    from actions.server.run_outputs.service import _canonical, _one

    c = case
    port, _, request = wrapper(c)

    class Uncertain:
        calls = 0

        def execute(self, caller, ticket, service):
            self.calls += 1
            row = _one(service.db, Run, ticket.fence.run_id)
            value = json.loads(row.result)
            value["launch"] = {"id": "retained-fixture"}
            with service.db.transaction():
                _update(service.db, Run, row.id, {"result": _canonical(value, 65536)})
            raise RuntimeError("uncertain ordinary launch")

    runner = Uncertain()
    port.runner = runner
    with pytest.raises(RuntimeError, match="uncertain"):
        invoke(c, port, request)
    assert (
        invoke(c, port, request).model_result["execution"]["state"]
        == "reconciliation_required"
    )
    assert runner.calls == 1
