"""Exact selected input app admission; synthetic completion only, no RCC."""
import json
from uuid import uuid4

import pytest
from action_server_tests import test_generic_canvas_view as app_tests
from action_server_tests.test_generic_canvas_view import fixtures, grant

from actions.server.foundry.mcp import CanvasCaller

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = app_tests.provider
postgresql_database = app_tests.postgresql_database
reviewed = app_tests.reviewed
case = app_tests.case
pytestmark = app_tests.pytestmark


def configure(case, mode):
    from action_server_tests.test_generic_work_item_execution import OutputExecutor
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
    if mode == "producer":
        registry._executor = OutputExecutor()
    compiled = registry.compile_trusted_source(
        _generated_action_entries(),
        logical_package_key="app-" + mode,
        logical_name="App " + mode,
        trusted_actor=c.actor,
        workspace_id=c.scope.deployment.workspace_id,
        application_id=c.scope.deployment.deployment_id,
        work_items=WorkItemDeclaration(mode=mode, allow_outputs=mode == "producer"),
    )
    package = registry.admit_compiled(
        c.actor, c.scope.deployment.workspace_id, compiled.compiled_package
    )
    capability = registry.capability_refs(package)[0]
    plan = registry.get_capability(capability).runtime_plans[0]
    policy = CapabilityWorkItemPolicy(
        capability=capability,
        input_mode="claim" if mode == "consumer" else "required",
        input_queue=None if mode == "producer" else "input",
        output_queue="output" if mode == "producer" else None,
        max_output_items=2 if mode == "producer" else 0,
        max_output_bytes=1024 if mode == "producer" else 0,
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


@pytest.fixture(params=["required-input", "consumer"])
def consumer(case, request):
    c = configure(case, request.param)
    c.mode = request.param
    return c


def test_explicit_selected_item_admits_without_replacing_input(consumer):
    c = consumer
    service, caller = c.port._selected(c.app, "run")
    queue = service.queue_ref(service.policy.input_queue).model_dump(mode="json")
    first = service.enqueue(caller, {"value": "hello"}, "first")
    second = service.enqueue(caller, {"value": "second"}, "second")
    response = app_tests.call(
        c,
        "canvas_get_state",
        dict(mode="generic", action="inputs", bindingId="run", queue=queue),
    ).execution
    assert {item["itemId"] for item in response["items"]} == {first, second}
    args = dict(
        mode="generic",
        action="submit_input",
        bindingId="run",
        queue=queue,
        itemId=second,
        idempotencyKey="selected",
    )
    admitted = app_tests.call(c, "canvas_dispatch", args).execution
    assert admitted["state"] == "ready" and c.runner.calls == 0
    assert admitted["workItemId"] == second
    assert service.queue(service.policy.input_queue).load_payload(first)
    done = app_tests.call(
        c, "canvas_dispatch", app_tests.request(admitted, action="execute")
    ).execution
    assert done["state"] == "completed"
    assert (
        app_tests.call(c, "canvas_dispatch", args).execution["runId"] == done["runId"]
    )
    assert c.runner.calls == 1
    next_args = dict(args, itemId=first, idempotencyKey="next-selection")
    next_run = app_tests.call(c, "canvas_dispatch", next_args).execution
    assert next_run["runId"] != done["runId"] and c.runner.calls == 1
    finished = app_tests.call(
        c, "canvas_dispatch", app_tests.request(next_run, action="execute")
    ).execution
    assert finished["state"] == "completed" and c.runner.calls == 2


def selected(c, key="selection"):
    service, managed = c.port._selected(c.app, "run")
    item = service.enqueue(managed, {"value": "owned"}, key + "-input")
    args = dict(
        mode="generic",
        action="submit_input",
        bindingId="run",
        queue=service.queue_ref(service.policy.input_queue).model_dump(mode="json"),
        itemId=item,
        idempotencyKey=key,
    )
    return service, managed, item, args


def test_changed_selection_is_not_a_new_admission(consumer):
    from actions.server.run_outputs.service import AccessDenied

    c = consumer
    service, managed, item, args = selected(c)
    admitted = app_tests.call(c, "canvas_dispatch", args).execution
    other = service.enqueue(managed, {"value": "other"}, "other")
    with pytest.raises(AccessDenied):
        app_tests.call(c, "canvas_dispatch", dict(args, itemId=other))
    queue = dict(args["queue"], queue_id="other")
    with pytest.raises(AccessDenied):
        app_tests.call(c, "canvas_dispatch", dict(args, queue=queue))
    assert (
        app_tests.call(c, "canvas_dispatch", args).execution["runId"]
        == admitted["runId"]
    )


@pytest.mark.parametrize("mutation", ["cancelled", "claimed", "old_epoch"])
def test_selected_unavailable_item_never_falls_back_to_next(consumer, mutation):
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import FenceRejected, _one, _update

    c = consumer
    service, managed, item, args = selected(c)
    other = service.enqueue(managed, {"value": "other"}, "other")
    if mutation == "claimed":
        service.queue(service.policy.input_queue).reserve_item_fenced(
            item, str(uuid4()), lease_seconds=60
        )
    else:
        with c.db.transaction():
            _update(
                c.db,
                FencedWorkItem,
                item,
                {"cancel_requested": 1}
                if mutation == "cancelled"
                else {"claim_epoch": 1},
            )
    with pytest.raises(FenceRejected):
        app_tests.call(c, "canvas_dispatch", args)
    assert _one(c.db, FencedWorkItem, other).claim_epoch == 0 and c.runner.calls == 0


def test_claim_admission_receipt_failure_rolls_back_everything(consumer, monkeypatch):
    from actions.server._models import Run
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import _one

    c = consumer
    _, _, item, args = selected(c)
    count = len(c.db.all(Run))

    def fail(*args):
        raise RuntimeError("receipt unavailable")

    monkeypatch.setattr(c.port, "_record_association", fail)
    with pytest.raises(RuntimeError):
        app_tests.call(c, "canvas_dispatch", args)
    row = _one(c.db, FencedWorkItem, item)
    assert row.state == "PENDING" and row.claim_epoch == 0 and not row.claim_owner
    assert len(c.db.all(Run)) == count


@pytest.mark.parametrize("revocation", ["execute", "read", "claim"])
def test_selection_replay_reauthorizes_current_grants(
    consumer, monkeypatch, revocation
):
    from actions.server.managed_work_items.contracts import Permission
    from actions.server.run_outputs.service import AccessDenied

    c = consumer
    service, managed, _, args = selected(c)
    app_tests.call(c, "canvas_dispatch", args)
    if revocation == "execute":
        original = c.outputs._authorize

        def deny(actor, snapshot, permission):
            if permission == "execute":
                raise AccessDenied("revoked")
            return original(actor, snapshot, permission)

        monkeypatch.setattr(c.outputs, "_authorize", deny)
    else:
        target = Permission.READ if revocation == "read" else Permission.CLAIM
        original = c.port.execution.authorization.require_queue

        def deny(caller, queue, permission):
            if permission == target:
                raise AccessDenied("revoked")
            return original(caller, queue, permission)

        monkeypatch.setattr(c.port.execution.authorization, "require_queue", deny)
    with pytest.raises(AccessDenied):
        app_tests.call(c, "canvas_dispatch", args)
    assert c.runner.calls == 0


def test_concurrent_exact_selection_admits_once_without_next_item(consumer):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import FenceRejected, _one

    c = consumer
    service, managed, _, args = selected(c)
    other = service.enqueue(managed, {"value": "other"}, "other")
    barrier = Barrier(2)

    def send(key):
        barrier.wait()
        try:
            return app_tests.call(
                c, "canvas_dispatch", dict(args, idempotencyKey=key)
            ).execution
        except FenceRejected:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(send, key) for key in ["first", "second"]]
        results = [future.result() for future in futures]
    assert sum(result is not None for result in results) == 1
    assert _one(c.db, FencedWorkItem, other).claim_epoch == 0 and c.runner.calls == 0


def test_terminal_input_epoch_and_payload_are_not_replaceable(consumer):
    from pydantic import ValidationError

    from actions.server._models import Run
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import FenceRejected, _one, _update

    c = consumer
    _, _, item, args = selected(c)
    for field, value in [
        ("inputs", {"value": "replacement"}),
        ("workerId", str(uuid4())),
        ("epoch", 2),
    ]:
        with pytest.raises(ValidationError):
            app_tests.call(c, "canvas_dispatch", dict(args, **{field: value}))
    admitted = app_tests.call(c, "canvas_dispatch", args).execution
    assert json.loads(_one(c.db, Run, admitted["runId"]).inputs) == {"value": "owned"}
    app_tests.call(c, "canvas_dispatch", app_tests.request(admitted, action="execute"))
    with c.db.transaction():
        _update(c.db, FencedWorkItem, item, {"claim_epoch": 2})
    with pytest.raises(FenceRejected):
        app_tests.call(c, "canvas_dispatch", args)
    assert c.runner.calls == 1


def test_input_list_is_bounded_read_only_and_requires_exact_scope(consumer):
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import AccessDenied, _one

    c = consumer
    service, managed, _, args = selected(c)
    for index in range(20):
        service.enqueue(managed, {"value": str(index)}, "page-" + str(index))
    command = dict(
        mode="generic", action="inputs", bindingId="run", queue=args["queue"]
    )
    page = app_tests.call(c, "canvas_get_state", command).execution
    assert len(page["items"]) == 20 and page["nextCursor"]
    next_page = app_tests.call(
        c, "canvas_get_state", dict(command, cursor=page["nextCursor"])
    ).execution
    assert len(next_page["items"]) == 1 and not next_page["nextCursor"]
    assert not {v["itemId"] for v in page["items"]} & {
        v["itemId"] for v in next_page["items"]
    }
    assert all(
        _one(c.db, FencedWorkItem, item["itemId"]).claim_epoch == 0
        for item in page["items"]
    )
    with pytest.raises(AccessDenied):
        app_tests.call(
            c,
            "canvas_get_state",
            dict(command, queue=dict(args["queue"], queue_id="foreign")),
        )
    with pytest.raises(AccessDenied):
        app_tests.call(c, "canvas_get_state", command, c.model)


def test_input_discovery_and_closed_tool_schema(consumer):
    import jsonschema

    from actions.server.foundry.mcp import CanvasMcp

    c = consumer
    _, _, _, args = selected(c)
    opened = app_tests.call(c, "canvas_get", {}, c.model)
    assert opened.generic_interaction["inputBindings"] == [
        {
            "bindingId": "run",
            "queue": args["queue"],
            "inputMode": "claim" if c.mode == "consumer" else "required",
        }
    ]
    listing = dict(
        mode="generic",
        action="inputs",
        bindingId="run",
        queue=args["queue"],
        appSession="a" * 43,
    )
    jsonschema.validate(
        listing,
        CanvasMcp._input_schema("canvas_get_state", c.port.schemas["canvas_get_state"]),
    )
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            listing,
            CanvasMcp._input_schema("canvas_cancel", c.port.schemas["canvas_cancel"]),
        )
    with pytest.raises(ValueError):
        app_tests.call(c, "canvas_dispatch", dict(args, itemId="-" * 36))
    assert c.runner.calls == 0


def test_non_bmp_preview_is_utf8_bounded(consumer):
    c = consumer
    service, managed, _, args = selected(c)
    item = service.enqueue(managed, {"value": "😀" * 1300}, "unicode-preview")
    page = app_tests.call(
        c,
        "canvas_get_state",
        dict(mode="generic", action="inputs", bindingId="run", queue=args["queue"]),
    ).execution
    projected = next(value for value in page["items"] if value["itemId"] == item)
    assert len(projected["preview"].encode("utf-8")) <= 2048
    assert (
        projected["previewTruncated"] is True and "\ufffd" not in projected["preview"]
    )


def test_expired_input_claim_is_not_ready_even_with_live_attempt(consumer):
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import _update

    c = consumer
    _, _, item, args = selected(c)
    admitted = app_tests.call(c, "canvas_dispatch", args).execution
    with c.db.transaction():
        _update(c.db, FencedWorkItem, item, {"claim_deadline_ms": "0"})
    status = app_tests.call(
        c, "canvas_execution_status", app_tests.request(admitted)
    ).execution
    assert status["state"] == "expired"
    assert (
        app_tests.call(
            c, "canvas_dispatch", app_tests.request(admitted, action="execute")
        ).execution["state"]
        == "expired"
    )
    assert c.runner.calls == 0
