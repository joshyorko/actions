"""Saved-result View handoff retains SQL review authority on a model connection."""

import asyncio
import json
from uuid import uuid4

import pytest
from action_server_tests import test_activated_reviewed_execution as fixtures
from action_server_tests.test_reviewed_canvas_execution import make_port

from actions.server._models import Run
from actions.server.foundry.mcp import CanvasCaller, CanvasMcp

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = fixtures.pytestmark
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def test_forwarded_view_review_requires_separate_human_decision_and_dispatch(
    reviewed, foundry_package_store
):
    from actions.server.foundry.reviewed_view import ReviewedCanvasView

    case = fixtures.setup_activated(reviewed, foundry_package_store)
    fixtures.release(case)
    port = ReviewedCanvasView(make_port(case))
    owner = CanvasCaller(case.actor, case.scope.application.workspace_id, "model")

    async def authenticate(_):
        return owner

    canvas = CanvasMcp(port, authenticate, "<html>owned renderer</html>")
    before = len(case.db.all(Run))

    async def check():
        opened = await canvas.call(
            None,
            "canvas_get",
            {
                "appId": str(case.staged.application_id.root),
                "revisionId": case.scope.deployment.revision_id.root,
                "reviewResult": {
                    "bindingId": "run",
                    "handle": case.proposal.binding.handle,
                },
            },
        )
        assert not opened.is_error
        token = opened.meta["actions.appSession"]["token"]
        assert opened.meta["actions.reviewedExecution"] == {
            "bindingId": "run",
            "handle": case.proposal.binding.handle,
        }
        assert not case.reviews.queue(case.scope).list_items()
        offered = await canvas.call(
            None,
            "canvas_dispatch",
            {
                "appSession": token,
                "action": "offer",
                "handle": case.proposal.binding.handle,
            },
        )
        assert not offered.is_error
        review = offered.meta["actions.review"]
        assert review["receipt"]["state"] == "pending"
        assert not case.reviews.queue(case.scope).list_items()
        inspected = await canvas.call(
            None,
            "canvas_artifact",
            {"appSession": token, "proposal": review["proposal"], "kind": "source"},
        )
        assert not inspected.is_error
        assert (
            inspected.meta["actions.artifact"]["digest"]
            == case.proposal.binding.result_digest
        )
        assert inspected.meta["actions.artifact"]["mediaType"] == "application/x-ndjson"
        assert not case.reviews.queue(case.scope).list_items()
        assert (
            await canvas.call(
                None,
                "canvas_dispatch",
                {
                    "action": "decide",
                    "proposal": review["proposal"],
                    "decision": "approve",
                },
            )
        ).is_error
        approved = await canvas.call(
            None,
            "canvas_dispatch",
            {
                "appSession": token,
                "action": "decide",
                "proposal": review["proposal"],
                "decision": "approve",
            },
        )
        assert not approved.is_error
        assert approved.meta["actions.review"]["receipt"]["state"] == "approved"
        assert len(case.reviews.queue(case.scope).list_items()) == 1
        assert len(case.db.all(Run)) == before
        # Runner absence fails before claim, including after explicit approval.
        assert (
            await canvas.call(
                None,
                "canvas_dispatch",
                {
                    "appSession": token,
                    "action": "execute",
                    "bindingId": "run",
                    "proposal": review["proposal"],
                },
            )
        ).is_error
        assert case.reviews.queue(case.scope).list_items()[0]["claim_epoch"] == 0
        status = await canvas.call(
            None,
            "canvas_execution_status",
            {
                "appSession": token,
                "proposal": review["proposal"],
            },
        )
        assert not status.is_error
        assert status.meta["actions.execution"]["phase"] == "queued"
        cancelled = await canvas.call(
            None,
            "canvas_cancel",
            {
                "appSession": token,
                "proposal": review["proposal"],
            },
        )
        assert not cancelled.is_error
        assert cancelled.meta["actions.review"]["receipt"]["state"] == "cancelled"

    asyncio.run(check())


@pytest.mark.parametrize(
    "failure", ["altered-result", "wrong-binding", "revoked", "stale-revision"]
)
def test_view_grant_does_not_replace_live_sql_policy(
    reviewed, foundry_package_store, failure
):
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.foundry.reviewed_view import ReviewedCanvasView

    case = fixtures.setup_activated(reviewed, foundry_package_store)
    fixtures.release(case)
    port = ReviewedCanvasView(make_port(case))
    caller = CanvasCaller(
        case.actor,
        case.scope.application.workspace_id,
        "app",
        case.scope,
        case.proposal.binding.handle,
        "run",
    )
    body = {
        "action": "decide",
        "proposal": case.proposal.model_dump(mode="json"),
        "decision": "approve",
    }
    if failure == "altered-result":
        body["proposal"]["binding"]["result_digest"] = "sha256:" + "0" * 64
    elif failure == "wrong-binding":
        body = {
            "action": "execute",
            "bindingId": "other",
            "proposal": case.proposal.model_dump(mode="json"),
        }
    elif failure == "revoked":
        for grant in case.db.all(FoundryAccessGrant):
            if (
                grant.principal_id == case.actor.principal_id
                and grant.subject_kind == "workspace"
            ):
                operations = json.loads(grant.operations_json)
                if "read_application" in operations:
                    with case.db.transaction():
                        from actions.server.run_outputs.service import _update

                        _update(
                            case.db,
                            FoundryAccessGrant,
                            grant.id,
                            {
                                "operations_json": json.dumps(
                                    [
                                        value
                                        for value in operations
                                        if value != "read_application"
                                    ]
                                )
                            },
                        )
    else:
        from actions.server.foundry.authoring_values import CanvasBinding

        next_revision = case.authority.apply(
            case.actor,
            case.staged.ref.workspace_id,
            case.staged.application_id,
            case.staged.ref,
            json.dumps(dict(case.spec, title="Changed view")).encode(),
            (CanvasBinding("run", case.selection.capability_plans[0].capability),),
            case.staged.package_revisions,
            case.selection,
            case.staged.compilation,
            fixtures.fingerprint("view-revision"),
            idempotency_key=str(uuid4()),
        )
        case.authority.release(
            case.actor,
            case.staged.ref.workspace_id,
            case.staged.application_id,
            next_revision.ref,
            case.staged.ref,
            fixtures.fingerprint("view-release"),
            idempotency_key=str(uuid4()),
        )
    with pytest.raises((PermissionError, ValueError)):
        asyncio.run(port.call(caller, "canvas_dispatch", body))
    assert not case.reviews.queue(case.scope).list_items()


@pytest.mark.parametrize("approved", [False, True])
def test_expired_result_without_admitted_run_cannot_gain_view_session(
    reviewed, foundry_package_store, approved
):
    from actions.server.foundry.reviewed_view import ReviewedCanvasView
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import _update
    from actions.server.run_outputs.types import output_id_from_handle

    case = fixtures.setup_activated(reviewed, foundry_package_store)
    fixtures.release(case)
    if approved:
        case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    before = len(case.db.all(Run))
    with case.db.transaction():
        _update(
            case.db,
            RunOutput,
            output_id_from_handle(case.proposal.binding.handle),
            {"expires_ms": "0"},
        )
    caller = CanvasCaller(case.actor, case.scope.application.workspace_id, "model")
    with pytest.raises(PermissionError):
        asyncio.run(
            ReviewedCanvasView(make_port(case)).call(
                caller,
                "canvas_get",
                {
                    "appId": str(case.staged.application_id.root),
                    "reviewResult": {
                        "bindingId": "run",
                        "handle": case.proposal.binding.handle,
                    },
                },
            )
        )
    assert len(case.db.all(Run)) == before
    assert all(
        item["claim_epoch"] == 0 for item in case.reviews.queue(case.scope).list_items()
    )
