"""Bound app uses common SQL; fake runner does not claim actual RCC/host proof."""
import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests import test_activated_reviewed_execution as fixtures
from action_server_tests.test_generic_work_item_execution import (
    grant,
    synthetic_completion,
)

from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.generic_view import GenericCanvasView
from actions.server.foundry.mcp import CanvasCaller, CanvasReply
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.managed_work_items.authorization import SqlQueueAuthorization
from actions.server.run_outputs.service import AccessDenied, _one, _update

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = fixtures.pytestmark


class Runner:
    calls = 0

    def execute(self, caller, ticket, service):
        self.calls += 1
        g = SimpleNamespace(owner=service, caller=caller, db=service.db)
        guarded, output, result = synthetic_completion(g, ticket, "hello")
        return guarded.publish(caller.actor, ticket.fence, [output], result)


@pytest.fixture
def case(reviewed, foundry_package_store):
    c = fixtures.setup_activated(reviewed, foundry_package_store)
    fixtures.release(c)
    grant(
        c.db,
        c.actor,
        c.scope.deployment.workspace_id,
        "workspace",
        c.scope.application.workspace_id,
        ["cancel_execution"],
    )
    c.worker = str(uuid4())
    c.runner = Runner()
    c.model = CanvasCaller(c.actor, c.scope.application.workspace_id, "model")
    c.app = CanvasCaller(c.actor, c.scope.application.workspace_id, "app", c.scope)

    class Port:
        schemas = {
            "canvas_get": {"type": "object", "properties": {}},
            "canvas_dispatch": {},
            "canvas_get_state": {},
            "canvas_execution_status": {},
            "canvas_cancel": {},
            "canvas_artifact": {},
        }
        deployments = c.deployments
        outputs = c.outputs
        worker_id = c.worker
        runner = c.runner
        authorization = SqlQueueAuthorization(c.db)

        async def call(self, caller, name, args):
            return CanvasReply(
                "canonical view fixture",
                view_state={
                    "applicationId": str(c.scope.deployment.deployment_id.root),
                    "revisionId": c.scope.deployment.revision_id.root,
                },
            )

    c.port = GenericCanvasView(Port())
    return c


def call(c, name, args, caller=None):
    return asyncio.run(c.port.call(caller or c.app, name, args))


def submit(c, key="form"):
    return call(
        c,
        "canvas_dispatch",
        {
            "mode": "generic",
            "action": "submit",
            "bindingId": "run",
            "inputs": {"value": "hello"},
            "idempotencyKey": key,
        },
    ).execution


def request(state, **extra):
    return {"mode": "generic", "bindingId": "run", "runId": state["runId"], **extra}


def test_none_form_admits_without_work_item_and_executes_once(case):
    c = case
    before = len(c.db.all(FencedWorkItem))
    opened = call(c, "canvas_get", {}, c.model)
    assert opened.app_scope == c.scope and opened.generic_interaction["bindingIds"] == [
        "run"
    ]
    state = submit(c)
    assert state["state"] == "ready" and c.runner.calls == 0
    assert len(c.db.all(FencedWorkItem)) == before
    done = call(c, "canvas_dispatch", request(state, action="execute")).execution
    assert done["state"] == "completed" and c.runner.calls == 1
    assert (
        call(c, "canvas_dispatch", request(state, action="execute")).execution == done
    )
    assert submit(c)["runId"] == done["runId"]
    artifact = call(
        c, "canvas_artifact", request(state, handle=done["outputs"][0]["handle"])
    ).artifact
    assert artifact["text"] == "owned"
    assert c.runner.calls == 1


def test_app_scope_binding_and_model_denials(case):
    c = case
    args = {
        "mode": "generic",
        "action": "submit",
        "bindingId": "run",
        "inputs": {"value": "hello"},
        "idempotencyKey": "form",
    }
    with pytest.raises(AccessDenied):
        call(c, "canvas_dispatch", args, c.model)
    with pytest.raises(AccessDenied):
        call(c, "canvas_dispatch", dict(args, bindingId="foreign"))
    with pytest.raises(Exception):
        call(c, "canvas_dispatch", dict(args, snapshot={}))
    opened = call(c, "canvas_get", {}, c.model)
    assert opened.app_scope == c.scope


def test_cancel_is_requested_without_false_process_stopped_claim(case):
    c = case
    state = submit(c)
    result = call(c, "canvas_cancel", request(state)).execution
    assert result["cancelRequested"] and result["state"] == "cancel_requested"
    assert (
        call(c, "canvas_dispatch", request(state, action="execute")).execution["state"]
        == "cancel_requested"
    )
    assert c.runner.calls == 0


def test_changed_submission_and_foreign_run_fail_closed(case):
    c = case
    submit(c)
    with pytest.raises(ValueError):
        call(
            c,
            "canvas_dispatch",
            {
                "mode": "generic",
                "action": "submit",
                "bindingId": "run",
                "inputs": {"value": "different"},
                "idempotencyKey": "form",
            },
        )
    with pytest.raises(Exception):
        call(c, "canvas_execution_status", request({"runId": str(uuid4())}))
    assert c.runner.calls == 0


def test_new_activation_blocks_old_app_session(case):
    from actions.server.foundry.authoring_values import CanvasBinding

    c = case
    state = submit(c)
    revised = dict(c.spec, title="New active app")
    next_revision = c.authority.apply(
        c.actor,
        c.staged.ref.workspace_id,
        c.staged.application_id,
        c.staged.ref,
        json.dumps(revised).encode(),
        (CanvasBinding("run", c.selection.capability_plans[0].capability),),
        c.staged.package_revisions,
        c.selection,
        c.staged.compilation,
        fixtures.fingerprint("revised"),
        idempotency_key="revised",
    )
    c.authority.release(
        c.actor,
        c.staged.ref.workspace_id,
        c.staged.application_id,
        next_revision.ref,
        c.staged.ref,
        fixtures.fingerprint("release-next"),
        idempotency_key="release-next",
    )
    with pytest.raises(AccessDenied):
        call(c, "canvas_dispatch", request(state, action="execute"))
    with pytest.raises(AccessDenied):
        call(c, "canvas_execution_status", request(state))
    assert c.runner.calls == 0


def test_none_admission_registers_without_minting_grants(case):
    from actions.server.foundry.rcc_execution import GeneratedRccExecution
    from actions.server.run_outputs.models import RunAccessGrant, RunAdmission

    c = case
    grants = len(c.db.all(FoundryAccessGrant)) + len(c.db.all(RunAccessGrant))
    admissions = len(c.db.all(RunAdmission))
    state = submit(c)
    assert len(c.db.all(RunAdmission)) == admissions + 1
    assert len(c.db.all(FoundryAccessGrant)) + len(c.db.all(RunAccessGrant)) == grants
    with c.db.connect():
        service, managed = c.port._selected(c.app, "run")
        row, ticket, _ = c.port._read(service, managed, state["runId"], "run", c.scope)
        runner = object.__new__(GeneratedRccExecution)
        runner.outputs = service.outputs(managed, ticket)
        assert runner._read_journal(ticket.fence)["mode"] == "standalone"
        runner.outputs = service.base
        with pytest.raises(Exception):
            runner._read_journal(ticket.fence)


def test_inflight_status_and_cancellation_keep_actual_stop_unclaimed(case):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from actions.server.run_outputs.service import _canonical

    c = case
    entered, finish = Event(), Event()

    class BlockingRunner:
        def execute(self, caller, ticket, service):
            row = _one(service.db, Run, ticket.fence.run_id)
            journal = json.loads(row.result)
            journal["launch"] = {"id": "controlled-owned-fixture"}
            with service.db.transaction():
                _update(service.db, Run, row.id, {"result": _canonical(journal, 65536)})
            entered.set()
            assert finish.wait(10)
            raise RuntimeError("owned fixture stopped without terminal proof")

    c.port.execution.runner = BlockingRunner()
    state = submit(c)
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(
            call, c, "canvas_dispatch", request(state, action="execute")
        )
        try:
            assert entered.wait(10)
            assert (
                call(c, "canvas_execution_status", request(state)).execution["state"]
                == "running"
            )
            assert (
                call(c, "canvas_cancel", request(state)).execution["state"]
                == "cancel_requested"
            )
        finally:
            finish.set()
        with pytest.raises(RuntimeError):
            future.result()
    assert (
        call(c, "canvas_execution_status", request(state)).execution["state"]
        == "cancel_requested"
    )


@pytest.mark.parametrize("mode", ["optional", "producer"])
def test_explicit_generic_policy_uses_same_app_path(case, mode):
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
        input_mode="none" if mode == "producer" else "optional",
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

    class PolicyRunner:
        def execute(self, caller, ticket, service):
            value = (
                {"result": "hello", "workItems": [{"value": "child"}]}
                if mode == "producer"
                else "hello"
            )
            guarded, output, result = synthetic_completion(
                SimpleNamespace(owner=service, caller=caller, db=c.db), ticket, value
            )
            return guarded.publish(caller.actor, ticket.fence, [output], result)

    c.port.execution.runner = PolicyRunner()
    state = submit(c)
    assert (
        call(c, "canvas_dispatch", request(state, action="execute")).execution["state"]
        == "completed"
    )


def test_model_run_cannot_spoof_app_receipt(case):
    from actions.server.run_outputs.service import _key

    c = case
    service, managed = c.port._selected(c.app, "run")
    key = _key(
        "actions.generic-app-submit/v1",
        c.actor.principal_id,
        json.dumps(c.scope.model_dump(mode="json"), sort_keys=True),
        "run",
        "form",
    )
    ticket = service.dispatch_standalone(managed, {"value": "hello"}, key)
    with pytest.raises(AccessDenied, match="receipt"):
        submit(c)
    with pytest.raises(AccessDenied, match="receipt"):
        call(c, "canvas_execution_status", request({"runId": ticket.fence.run_id}))


def test_receipt_binding_and_audit_are_required(case):
    from actions.server.foundry.models import FoundryAudit, FoundryRequest

    c = case
    state = submit(c)
    service, managed = c.port._selected(c.app, "run")
    with pytest.raises(AccessDenied, match="receipt differs"):
        c.port._association(managed, c.scope, "alias", state["runId"])
    row = c.db.all(FoundryRequest, where="operation=?", values=["generic-app.submit"])[
        0
    ]
    audit = c.db.all(FoundryAudit, where="foundry_request_id=?", values=[row.id])[0]
    with c.db.transaction():
        _update(c.db, FoundryAudit, audit.id, {"principal_id": str(uuid4())})
    with pytest.raises(AccessDenied, match="audit differs"):
        call(c, "canvas_execution_status", request(state))


def test_app_receipt_failure_rolls_back_common_admission(case, monkeypatch):
    c = case
    before = len(c.db.all(Run))

    def fail(*args):
        raise RuntimeError("receipt persistence fault")

    monkeypatch.setattr(c.port, "_record_association", fail)
    with pytest.raises(RuntimeError, match="persistence fault"):
        submit(c)
    assert len(c.db.all(Run)) == before


def test_advertised_closed_union_accepts_transport_session(case):
    import jsonschema

    from actions.server.foundry.mcp import CanvasMcp

    schema = CanvasMcp._input_schema(
        "canvas_dispatch", case.port.schemas["canvas_dispatch"]
    )
    args = dict(
        mode="generic",
        action="submit",
        bindingId="run",
        inputs={"value": "hello"},
        idempotencyKey="form",
        appSession="a" * 43,
    )
    jsonschema.validate(args, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dict(args, snapshot={}), schema)


def test_official_facade_keeps_app_session_private_and_actor_bound(case):
    from actions.server.foundry.mcp import MODEL_TOOLS, CanvasMcp
    from actions.server.run_outputs.types import Actor

    c = case
    for name in MODEL_TOOLS:
        c.port.schemas.setdefault(name, {"type": "object", "properties": {}})

    async def authenticate(ctx):
        return ctx

    transport = CanvasMcp(c.port, authenticate, "<html>fixture</html>")
    opened = asyncio.run(transport.call(c.model, "canvas_get", {}))
    assert not opened.is_error
    assert opened.structured_content is None
    token = opened.meta["actions.appSession"]["token"]
    assert token not in opened.content[0].text
    args = dict(
        mode="generic",
        action="submit",
        bindingId="run",
        inputs={"value": "hello"},
        idempotencyKey="official",
    )
    assert asyncio.run(transport.call(c.model, "canvas_dispatch", args)).is_error
    result = asyncio.run(
        transport.call(c.model, "canvas_dispatch", dict(args, appSession=token))
    )
    assert not result.is_error and result.meta["actions.execution"]["state"] == "ready"
    assert result.structured_content is None
    stranger = CanvasCaller(
        Actor(principal_id=str(uuid4())), c.model.workspace_id, "model"
    )
    assert asyncio.run(
        transport.call(stranger, "canvas_dispatch", dict(args, appSession=token))
    ).is_error


def test_reopen_recovers_existing_app_receipt_without_launch(case):
    c = case
    state = submit(c)
    reopened = call(c, "canvas_get", {}, c.model)
    assert reopened.generic_interaction["executions"] == [state]
    assert c.runner.calls == 0
    call(c, "canvas_dispatch", request(state, action="execute"))
    c.port = GenericCanvasView(c.port.execution)
    reopened = call(c, "canvas_get", {}, c.model)
    recovered = reopened.generic_interaction["executions"][0]
    assert recovered["runId"] == state["runId"] and recovered["state"] == "completed"
    assert c.runner.calls == 1


def test_alias_binding_resolving_same_snapshot_cannot_read_app_run(case, monkeypatch):
    c = case
    state = submit(c)
    original = c.port._selected

    def same_snapshot(caller, binding):
        return original(caller, "run" if binding == "alias" else binding)

    monkeypatch.setattr(c.port, "_selected", same_snapshot)
    with pytest.raises(AccessDenied, match="receipt differs"):
        call(c, "canvas_execution_status", dict(request(state), bindingId="alias"))
    with pytest.raises(AccessDenied, match="receipt differs"):
        call(c, "canvas_cancel", dict(request(state), bindingId="alias"))


def test_caller_workspace_must_match_bound_scope(case):
    from dataclasses import replace

    c = case
    with pytest.raises(ValueError):
        replace(c.app, workspace_id=str(uuid4()))
    foreign = replace(c.app)
    object.__setattr__(foreign, "workspace_id", str(uuid4()))
    with pytest.raises(AccessDenied):
        c.port._selected(foreign, "run")
    with pytest.raises(AccessDenied):
        call(
            c,
            "canvas_dispatch",
            dict(
                mode="generic",
                action="submit",
                bindingId="run",
                inputs={"value": "hello"},
                idempotencyKey="x",
            ),
            foreign,
        )


@pytest.mark.parametrize(
    "corruption",
    [
        "attempt-workspace",
        "mode",
        "epoch",
        "attempt-state",
        "cancel-terminal",
        "foreign-output",
    ],
)
def test_corrupt_retained_state_fails_closed(case, corruption):
    from actions.server.run_outputs.models import RunAttempt, RunPin
    from actions.server.run_outputs.service import _canonical

    c = case
    state = submit(c)
    terminal = corruption in ("cancel-terminal", "foreign-output")
    if terminal:
        call(c, "canvas_dispatch", request(state, action="execute"))
    with c.db.transaction():
        row = _one(c.db, Run, state["runId"])
        pin = _one(c.db, RunPin, row.id)
        if corruption == "attempt-workspace":
            from actions.server.run_outputs.models import Workspace

            workspace = str(uuid4())
            c.db.insert(Workspace(workspace, "active", 0))
            _update(c.db, RunAttempt, state["attemptId"], {"workspace_id": workspace})
        elif corruption == "attempt-state":
            _update(c.db, RunAttempt, state["attemptId"], {"state": "failed"})
        elif corruption == "epoch":
            _update(c.db, RunPin, pin.id, {"epoch": pin.epoch + 1})
        elif corruption == "cancel-terminal":
            _update(c.db, RunPin, pin.id, {"cancel_requested": 1})
        else:
            value = json.loads(row.result)
            if corruption == "mode":
                value["mode"] = "consumer"
            else:
                value["outputs"].append(dict(value["outputs"][0], run_id=str(uuid4())))
            _update(c.db, Run, row.id, {"result": _canonical(value, 524288)})
    with pytest.raises((AccessDenied, ValueError, RuntimeError)):
        call(c, "canvas_execution_status", request(state))


def test_read_only_actor_is_not_advertised_runnable_binding(case, monkeypatch):
    c = case
    original = c.outputs._authorize

    def authorize(actor, snapshot, permission):
        if permission == "execute":
            raise AccessDenied("execution grant revoked")
        return original(actor, snapshot, permission)

    monkeypatch.setattr(c.outputs, "_authorize", authorize)
    opened = call(c, "canvas_get", {}, c.model)
    assert opened.generic_interaction is None and opened.app_scope is None
