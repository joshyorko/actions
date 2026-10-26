"""Reopen terminal handles are live-authorized projections, never copied cache."""
import json
from uuid import uuid4

import pytest
from action_server_tests import test_generic_canvas_view as app_tests

from actions.server._models import Run
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.managed_work_items.contracts import Permission
from actions.server.run_outputs.service import FenceRejected, _canonical, _one, _update

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = app_tests.provider
postgresql_database = app_tests.postgresql_database
reviewed = app_tests.reviewed
case = app_tests.case
pytestmark = app_tests.pytestmark


def complete(c):
    state = app_tests.submit(c)
    return app_tests.call(
        c, "canvas_dispatch", app_tests.request(state, action="execute")
    ).execution


def test_reopen_resolves_handles_and_artifact_without_relaunch(case, monkeypatch):
    c = case
    done = complete(c)
    calls = []
    original = c.outputs.resolve

    def resolve(actor, workspace, handle):
        calls.append(handle)
        return original(actor, workspace, handle)

    monkeypatch.setattr(c.outputs, "resolve", resolve)
    reopened = app_tests.call(c, "canvas_get", {}, c.model).generic_interaction[
        "executions"
    ][0]
    assert reopened["outputs"] == done["outputs"] and calls
    artifact = app_tests.call(
        c,
        "canvas_artifact",
        app_tests.request(reopened, handle=reopened["outputs"][0]["handle"]),
    ).artifact
    assert artifact["text"] == "owned" and c.runner.calls == 1


def test_reopen_omits_handles_when_output_queue_artifact_grant_revoked(case):
    c = case
    app_tests.test_explicit_generic_policy_uses_same_app_path(c, "producer")
    opened = app_tests.call(c, "canvas_get", {}, c.model).generic_interaction[
        "executions"
    ][0]
    assert opened["outputs"]
    with c.db.transaction():
        for row in c.db.all(FoundryAccessGrant):
            permissions = json.loads(row.operations_json)
            if Permission.ARTIFACT_READ.value in permissions:
                _update(
                    c.db,
                    FoundryAccessGrant,
                    row.id,
                    {
                        "operations_json": json.dumps(
                            [
                                p
                                for p in permissions
                                if p != Permission.ARTIFACT_READ.value
                            ]
                        )
                    },
                )
    reopened = app_tests.call(c, "canvas_get", {}, c.model).generic_interaction[
        "executions"
    ][0]
    assert reopened["state"] == "completed" and "outputs" not in reopened


def test_reopen_rejects_mixed_run_inventory(case):
    c = case
    done = complete(c)
    row = _one(c.db, Run, done["runId"])
    result = json.loads(row.result)
    result["outputs"].append(dict(result["outputs"][0], run_id=str(uuid4())))
    with c.db.transaction():
        _update(c.db, Run, row.id, {"result": _canonical(result, 524288)})
    with pytest.raises(FenceRejected):
        app_tests.call(c, "canvas_get", {}, c.model)
