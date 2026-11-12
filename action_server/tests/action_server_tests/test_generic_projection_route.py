"""App-only routing over existing authorities; helper has separate byte tests."""

import json
import sys

import pytest
from action_server_tests import test_generic_canvas_view as fixtures

from actions.server.foundry.generic_projection import GeneratedProjection
from actions.server.foundry.mcp import APP_TOOLS, MODEL_TOOLS
from actions.server.run_outputs.service import AccessDenied

case = fixtures.case
postgresql_database = fixtures.postgresql_database
provider = fixtures.provider
reviewed = fixtures.reviewed
call = fixtures.call
request = fixtures.request
submit = fixtures.submit

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="owned filesystem provider qualifies Linux"
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def test_projection_has_app_only_closed_schema(case):
    assert "canvas_projection" in APP_TOOLS
    assert "canvas_projection" not in MODEL_TOOLS
    schema = case.port.schemas["canvas_projection"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {"mode", "bindingId", "runId"}


def test_projection_denies_model_foreign_binding_and_missing_association(case):
    state = submit(case)
    with pytest.raises(AccessDenied):
        call(case, "canvas_projection", request(state), case.model)
    with pytest.raises(AccessDenied):
        call(case, "canvas_projection", request(state, bindingId="foreign"))
    with pytest.raises(Exception):
        call(
            case,
            "canvas_projection",
            request(state, runId="00000000-0000-4000-8000-000000000000"),
        )
    with pytest.raises(AccessDenied):
        call(case, "canvas_projection", request(state))


def test_projection_wire_uses_host_selected_identity_and_live_callback(
    case, monkeypatch
):
    state = submit(case)
    done = call(case, "canvas_dispatch", request(state, action="execute")).execution
    seen = []

    def project(outputs, actor, **kwargs):
        assert not outputs.db.in_transaction()
        with outputs.db.transaction():
            kwargs["require_current"]()
        seen.append((actor, kwargs["snapshot"], kwargs["run_id"], kwargs["attempt_id"]))
        return GeneratedProjection(
            "run", kwargs["run_id"], kwargs["attempt_id"], '{"value":3}'
        )

    monkeypatch.setattr(
        "actions.server.foundry.generic_projection.project_generated_result", project
    )
    reply = call(case, "canvas_projection", request(state))
    assert reply.projection == {
        "bindingId": "run",
        "runId": done["runId"],
        "attemptId": done["attemptId"],
        "canonicalJson": '{"value":3}',
        "data": {"value": 3},
    }
    assert reply.model_result is None
    assert len(seen) == 1 and seen[0][0] == case.actor


def test_route_pins_validated_receipt_before_helper_entry(case, monkeypatch):
    from actions.server._models import Run
    from actions.server.run_outputs.service import _one

    state = submit(case)
    call(case, "canvas_dispatch", request(state, action="execute"))

    def mutate_before_helper(outputs, actor, **kwargs):
        with outputs.db.transaction():
            run = _one(outputs.db, Run, kwargs["run_id"])
            value = json.loads(run.result)
            value["result"]["sourceArtifactDigest"] = "sha256:" + "f" * 64
            outputs.db.update_by_id(Run, run.id, {"result": json.dumps(value)})
        with outputs.db.transaction():
            kwargs["require_current"]()
        raise AssertionError("mutated validated receipt was accepted")

    monkeypatch.setattr(
        "actions.server.foundry.generic_projection.project_generated_result",
        mutate_before_helper,
    )
    with pytest.raises(AccessDenied, match="validated terminal identity"):
        call(case, "canvas_projection", request(state))
