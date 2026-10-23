"""Scoped transport admission uses real common SQL and no automatic approval."""

import asyncio

import pytest
from action_server_tests import test_activated_reviewed_execution as fixtures

from actions.server._models import Run
from actions.server.foundry.authoring import FoundryAuthoring
from actions.server.foundry.bootstrap import _ExecutionNotConfigured
from actions.server.foundry.mcp import CanvasCaller
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = fixtures.pytestmark
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def make_port(case, runner=None):
    from actions.server.foundry.execution_port import ReviewedCanvasExecution

    registry = case.outputs.capabilities
    authoring = FoundryAuthoring(
        case.authority,
        SqlFoundryAuthorization(case.db),
        registry,
        registry,
        _ExecutionNotConfigured(),
    )
    return ReviewedCanvasExecution(authoring, fixtures.adapter(case), runner=runner)


def request(case):
    return {"bindingId": "run", "proposal": case.proposal.model_dump(mode="json")}


@pytest.mark.parametrize("audience", ["model", "app"])
def test_execution_without_explicit_host_runner_does_not_claim_or_admit(
    reviewed, foundry_package_store, audience
):
    case = fixtures.setup_activated(reviewed, foundry_package_store)
    fixtures.release(case)
    case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    caller = CanvasCaller(
        case.actor,
        case.scope.application.workspace_id,
        audience,
        scope=case.scope if audience == "app" else None,
    )
    before = len(case.db.all(Run))
    with pytest.raises(ValueError, match="configured"):
        asyncio.run(
            make_port(case).call(
                caller,
                "canvas_dispatch" if audience == "app" else "capability_invoke",
                request(case),
            )
        )
    assert len(case.db.all(Run)) == before
    assert all(
        item["claim_epoch"] == 0 for item in case.reviews.queue(case.scope).list_items()
    )


@pytest.mark.parametrize(
    "failure",
    [
        "model-to-app",
        "unscoped-app",
        "wrong-revision",
        "cross-workspace",
        "replacement-input",
    ],
)
def test_transport_denials_precede_dispatch(reviewed, foundry_package_store, failure):
    case = fixtures.setup_activated(reviewed, foundry_package_store)
    fixtures.release(case)
    body = request(case)
    scope = case.scope
    if failure == "wrong-revision":
        scope = scope.model_copy(
            update={
                "application": scope.application.model_copy(
                    update={"revision_id": "sha256:" + "0" * 64}
                )
            }
        )
    caller = CanvasCaller(
        case.actor,
        scope.application.workspace_id,
        "app",
        scope=None if failure == "unscoped-app" else scope,
    )
    if failure == "model-to-app":
        caller = CanvasCaller(case.actor, scope.application.workspace_id, "model")
    if failure == "cross-workspace":
        from uuid import uuid4

        caller = CanvasCaller(case.actor, str(uuid4()), "model")
    if failure == "replacement-input":
        body["inputs"] = {"value": "altered result"}
    before = len(case.db.all(Run))
    with pytest.raises((ValueError, PermissionError)):
        asyncio.run(
            make_port(case).call(
                caller,
                "capability_invoke"
                if failure == "cross-workspace"
                else "canvas_dispatch",
                body,
            )
        )
    assert len(case.db.all(Run)) == before
    assert case.reviews.queue(case.scope).list_items() == []
