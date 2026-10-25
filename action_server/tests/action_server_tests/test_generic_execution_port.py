"""Model wrapper contracts; synthetic runners are not installed/RCC proof."""
import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_generic_work_item_execution import (
    generic as _generic_fixture,
)
from action_server_tests.test_generic_work_item_execution import synthetic_completion
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from actions.server._models import Run
from actions.server.foundry.execution_port import ReviewedDispatch
from actions.server.foundry.generic_execution_port import GenericCanvasExecution
from actions.server.foundry.mcp import CanvasCaller, CanvasReply
from actions.server.managed_work_items.contracts import ClaimRef
from actions.server.run_outputs.service import AccessDenied, _canonical, _one, _update

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def generic(database_location, foundry_package_store):
    yield from _generic_fixture.__wrapped__(database_location, foundry_package_store)


def test_wrapper_requires_explicit_host_context():
    import pytest

    with pytest.raises(TypeError):
        GenericCanvasExecution(None, None, None, None, worker_id=None, runner=None)


class ReviewedStub:
    schemas = {
        "canvas_dispatch": ReviewedDispatch.model_json_schema(),
        "capability_invoke": ReviewedDispatch.model_json_schema(),
    }

    def __init__(self):
        self.calls = []

    async def call(self, caller, name, arguments):
        self.calls.append((caller, name, arguments))
        return CanvasReply(
            summary="reviewed unchanged", model_result={"reviewed": True}
        )


class SyntheticRunner:
    """Publishes synthetic domain evidence; not actual RCC execution proof."""

    def __init__(self):
        self.calls = 0

    def execute(self, caller, ticket, service):
        self.calls += 1
        g = SimpleNamespace(owner=service, caller=caller, db=service.db)
        value = json.loads(_one(service.db, Run, ticket.fence.run_id).inputs)["value"]
        if service.registry.get_capability(
            service.snapshot.capability
        ).work_items.allow_outputs:
            value = {"result": value, "workItems": [{"value": "child"}]}
        guarded, output, result = synthetic_completion(g, ticket, value)
        return guarded.publish(caller.actor, ticket.fence, [output], result)


def wrapper(g, runner=None):
    reviewed = ReviewedStub()
    runner = runner or SyntheticRunner()
    port = GenericCanvasExecution(
        reviewed,
        g.owner.deployments,
        g.owner.base,
        g.owner.authorization,
        worker_id=g.caller.worker_id,
        runner=runner,
    )
    caller = CanvasCaller(g.caller.actor, g.owner.snapshot.workspace_id, "model")
    return port, caller, runner, reviewed


def standalone(g):
    return {
        "mode": "generic",
        "snapshot": g.owner.snapshot.model_dump(mode="json"),
        "inputs": {"value": "hello"},
        "idempotencyKey": "model-call",
    }


def invoke(port, caller, arguments, name="capability_invoke"):
    return asyncio.run(port.call(caller, name, arguments))


def test_closed_request_union_and_preserved_reviewed_schema(generic):
    g = generic("optional")
    port, caller, runner, reviewed = wrapper(g)
    request = standalone(g)
    assert port.schemas["capability_invoke"]["type"] == "object"
    Draft202012Validator.check_schema(port.schemas["capability_invoke"])
    Draft202012Validator(port.schemas["capability_invoke"]).validate(request)
    assert port.schemas["canvas_dispatch"] == reviewed.schemas["canvas_dispatch"]
    for addition in ({"workerId": str(uuid4())}, {"claim": {}}, {"source": "code"}):
        with pytest.raises(ValidationError):
            invoke(port, caller, dict(request, **addition))
    assert not g.db.all(Run)
    legacy = {"existing": "reviewed passthrough"}
    assert invoke(port, caller, legacy).model_result == {"reviewed": True}
    assert reviewed.calls[-1][2] == legacy
    assert invoke(port, caller, request, "canvas_dispatch").model_result == {
        "reviewed": True
    }


@pytest.mark.parametrize("mode", ["optional", "producer"])
def test_model_standalone_completion_replays_without_launch(generic, mode):
    g = generic(mode, outputs=mode == "producer")
    port, caller, runner, _ = wrapper(g)
    first = invoke(port, caller, standalone(g))
    execution = first.model_result["execution"]
    assert execution["state"] == "completed"
    assert execution["workItemId"] is None
    assert execution["outputs"][0]["handle"].startswith("art_")
    assert "owned" not in json.dumps(first.model_result)
    assert invoke(port, caller, standalone(g)).model_result == first.model_result
    assert runner.calls == 1


def test_exact_claim_input_and_trusted_worker(generic):
    g = generic()
    item = g.owner.enqueue(g.caller, {"value": "hello"}, "input")
    claim = g.owner.queue(g.owner.policy.input_queue).reserve_item_fenced(
        item, g.caller.worker_id, lease_seconds=60
    )
    request = {
        "mode": "generic",
        "snapshot": g.owner.snapshot.model_dump(mode="json"),
        "claim": ClaimRef(
            queue=g.owner.queue_ref(g.owner.policy.input_queue),
            item_id=item,
            owner_id=claim.owner_id,
            epoch=claim.epoch,
        ).model_dump(mode="json"),
    }
    port, caller, runner, _ = wrapper(g)
    for addition in (
        {"inputs": {"value": "changed"}},
        {"idempotencyKey": "replacement"},
    ):
        with pytest.raises(ValidationError):
            invoke(port, caller, dict(request, **addition))
    forged = json.loads(json.dumps(request))
    forged["claim"]["owner_id"] = str(uuid4())
    with pytest.raises(AccessDenied):
        invoke(port, caller, forged)
    result = invoke(port, caller, request)
    assert result.model_result["execution"]["workItemId"] == item
    assert invoke(port, caller, request).model_result == result.model_result
    assert runner.calls == 1


def test_model_only_and_exact_snapshot(generic):
    g = generic("optional")
    port, caller, runner, _ = wrapper(g)
    request = standalone(g)
    with pytest.raises(AccessDenied):
        invoke(port, CanvasCaller(caller.actor, caller.workspace_id, "app"), request)
    with pytest.raises(AccessDenied):
        invoke(port, CanvasCaller(caller.actor, str(uuid4()), "model"), request)
    changed = json.loads(json.dumps(request))
    changed["snapshot"]["action_id"] = "changed"
    with pytest.raises(AccessDenied):
        invoke(port, caller, changed)
    assert not g.db.all(Run)
    assert runner.calls == 0


def test_prior_launch_returns_reconciliation_without_retry(generic):
    g = generic("optional")
    ticket = g.owner.dispatch_standalone(
        g.caller, {"value": "hello"}, "model-call", lease_seconds=60
    )
    run = _one(g.db, Run, ticket.fence.run_id)
    journal = json.loads(run.result)
    journal["launch"] = {"id": "uncertain"}
    with g.db.transaction():
        _update(g.db, Run, run.id, {"result": _canonical(journal, 65536)})
    port, caller, runner, _ = wrapper(g)
    result = invoke(port, caller, standalone(g))
    assert result.model_result["execution"]["state"] == "reconciliation_required"
    assert "outputs" not in result.model_result["execution"]
    assert runner.calls == 0


def test_replay_reauthorizes_without_disclosing_revoked_artifacts(generic):
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.managed_work_items.contracts import Permission

    g = generic("optional")
    port, caller, runner, _ = wrapper(g)
    request = standalone(g)
    first = invoke(port, caller, request)
    assert first.model_result["execution"]["outputs"]
    operations = [
        "execute",
        "read_application",
        "cancel_execution",
        *[p.value for p in Permission if p != Permission.ARTIFACT_READ],
    ]
    with g.db.transaction():
        _update(
            g.db,
            FoundryAccessGrant,
            g.grant.id,
            {"operations_json": json.dumps(operations)},
        )
    replay = invoke(port, caller, request)
    assert replay.model_result["execution"]["state"] == "completed"
    assert "outputs" not in replay.model_result["execution"]
    with g.db.transaction():
        _update(g.db, FoundryAccessGrant, g.grant.id, {"operations_json": "[]"})
    with pytest.raises(Exception):
        invoke(port, caller, request)
    assert runner.calls == 1


def test_changed_standalone_replay_and_oversized_key_rejected(generic):
    g = generic("optional")
    port, caller, runner, _ = wrapper(g)
    request = standalone(g)
    invoke(port, caller, request)
    with pytest.raises(ValueError):
        invoke(port, caller, dict(request, inputs={"value": "changed"}))
    with pytest.raises(ValidationError):
        invoke(port, caller, dict(request, idempotencyKey="é" * 100))
    assert runner.calls == 1


def test_optin_actual_rcc_model_wrapper(generic, tmp_path):
    import os
    from pathlib import Path

    from actions.server.deployments.package_revision_compiler import (
        load_prepared_rcc_environment,
    )
    from actions.server.foundry.generic_execution_port import PinnedGenericRccRunner

    if not os.environ.get("ACTIONS_GENERIC_WRAPPER_REAL_RCC"):
        pytest.skip("exclusive prepared RCC home required")
    g = generic("optional", real=True)
    runner = PinnedGenericRccRunner(
        load_prepared_rcc_environment(
            Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
        ),
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]),
        tmp_path / "model-execution",
    )
    port, caller, _, _ = wrapper(g, runner)
    first = invoke(port, caller, standalone(g))
    assert first.model_result["execution"]["state"] == "completed"
    assert len(first.model_result["execution"]["outputs"]) == 4
    assert invoke(port, caller, standalone(g)).model_result == first.model_result


def test_terminal_claim_projection_checks_independent_current_epoch(generic):
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import FenceRejected

    g = generic()
    item = g.owner.enqueue(g.caller, {"value": "hello"}, "input")
    claim = g.owner.queue(g.owner.policy.input_queue).reserve_item_fenced(
        item, g.caller.worker_id, lease_seconds=60
    )
    request = {
        "mode": "generic",
        "snapshot": g.owner.snapshot.model_dump(mode="json"),
        "claim": ClaimRef(
            queue=g.owner.queue_ref(g.owner.policy.input_queue),
            item_id=item,
            owner_id=claim.owner_id,
            epoch=claim.epoch,
        ).model_dump(mode="json"),
    }
    port, caller, runner, _ = wrapper(g)
    result = invoke(port, caller, request)
    assert result.model_result["execution"]["workItemState"] == "COMPLETED"
    with g.db.transaction():
        _update(g.db, FencedWorkItem, item, {"claim_epoch": claim.epoch + 1})
    with pytest.raises(FenceRejected):
        invoke(port, caller, request)
    assert runner.calls == 1


def test_failed_launch_is_not_retried(generic):
    class UncertainRunner:
        calls = 0

        def execute(self, caller, ticket, service):
            self.calls += 1
            run = _one(service.db, Run, ticket.fence.run_id)
            record = json.loads(run.result)
            record["launch"] = {"id": "retained-uncertain-fixture"}
            with service.db.transaction():
                _update(service.db, Run, run.id, {"result": _canonical(record, 65536)})
            raise RuntimeError("fixture process outcome uncertain")

    g = generic("optional")
    port, caller, runner, _ = wrapper(g, UncertainRunner())
    with pytest.raises(RuntimeError, match="uncertain"):
        invoke(port, caller, standalone(g))
    assert (
        invoke(port, caller, standalone(g)).model_result["execution"]["state"]
        == "reconciliation_required"
    )
    assert runner.calls == 1


@pytest.mark.parametrize(
    "corruption", ["attempt", "item_owner", "item_cancel", "pin_cancel"]
)
def test_terminal_projection_rejects_state_corruption(generic, corruption):
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.models import RunAttempt, RunPin
    from actions.server.run_outputs.service import FenceRejected

    g = generic()
    item = g.owner.enqueue(g.caller, {"value": "hello"}, "input")
    claim = g.owner.queue(g.owner.policy.input_queue).reserve_item_fenced(
        item, g.caller.worker_id, lease_seconds=60
    )
    request = {
        "mode": "generic",
        "snapshot": g.owner.snapshot.model_dump(mode="json"),
        "claim": ClaimRef(
            queue=g.owner.queue_ref(g.owner.policy.input_queue),
            item_id=item,
            owner_id=claim.owner_id,
            epoch=claim.epoch,
        ).model_dump(mode="json"),
    }
    port, caller, runner, _ = wrapper(g)
    execution = invoke(port, caller, request).model_result["execution"]
    with g.db.transaction():
        if corruption == "attempt":
            _update(g.db, RunAttempt, execution["attemptId"], {"state": "running"})
        elif corruption == "item_owner":
            _update(g.db, FencedWorkItem, item, {"claim_owner": g.caller.worker_id})
        elif corruption == "item_cancel":
            _update(g.db, FencedWorkItem, item, {"cancel_requested": 1})
        else:
            _update(g.db, RunPin, execution["runId"], {"cancel_requested": 1})
    with pytest.raises(FenceRejected):
        invoke(port, caller, request)
    assert runner.calls == 1


@pytest.mark.parametrize("corruption", ["attempt", "pin_cancel"])
def test_uncertain_running_projection_rejects_state_corruption(generic, corruption):
    from actions.server.run_outputs.models import RunAttempt, RunPin
    from actions.server.run_outputs.service import FenceRejected

    g = generic("optional")
    ticket = g.owner.dispatch_standalone(
        g.caller, {"value": "hello"}, "model-call", lease_seconds=60
    )
    row = _one(g.db, Run, ticket.fence.run_id)
    record = json.loads(row.result)
    record["launch"] = {"id": "uncertain"}
    with g.db.transaction():
        _update(g.db, Run, row.id, {"result": _canonical(record, 65536)})
        if corruption == "attempt":
            _update(g.db, RunAttempt, ticket.fence.attempt_id, {"state": "succeeded"})
        else:
            _update(g.db, RunPin, row.id, {"cancel_requested": 1})
    port, caller, runner, _ = wrapper(g)
    with pytest.raises(FenceRejected):
        invoke(port, caller, standalone(g))
    assert runner.calls == 0
