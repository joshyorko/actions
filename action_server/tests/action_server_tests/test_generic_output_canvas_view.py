"""Bound output-child projection: SQL/domain evidence, no actual RCC."""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests import test_generic_canvas_view as app_tests
from action_server_tests.test_generic_canvas_view import fixtures, grant
from action_server_tests.test_generic_work_item_execution import synthetic_completion

from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.mcp import CanvasCaller
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _canonical,
    _update,
)

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
    registry._executor = OutputExecutor()
    compiled = registry.compile_trusted_source(
        _generated_action_entries(),
        logical_package_key="app-" + mode,
        logical_name="App " + mode,
        trusted_actor=c.actor,
        workspace_id=c.scope.deployment.workspace_id,
        application_id=c.scope.deployment.deployment_id,
        work_items=WorkItemDeclaration(mode=mode, allow_outputs=True),
    )
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


@pytest.fixture
def output_count(request):
    return getattr(request, "param", 1)


@pytest.fixture(params=["producer", "consumer"])
def produced(case, request, output_count):
    c = configure(case, request.param)
    service, managed = c.port._selected(c.app, "run")
    c.output_service = service
    c.output_caller = managed

    class Runner:
        calls = 0

        def execute(self, caller, ticket, service):
            self.calls += 1
            value = {
                "result": "hello",
                "workItems": [
                    {"value": "child " + str(index)} for index in range(output_count)
                ],
            }
            guarded, output, result = synthetic_completion(
                SimpleNamespace(owner=service, caller=caller, db=c.db), ticket, value
            )
            return guarded.publish(caller.actor, ticket.fence, [output], result)

    c.output_runner = Runner()
    c.port.execution.runner = c.output_runner
    if request.param == "producer":
        state = app_tests.submit(c)
    else:
        item = service.enqueue(managed, {"value": "hello"}, "producing-input")
        state = app_tests.call(
            c,
            "canvas_dispatch",
            dict(
                mode="generic",
                action="submit_input",
                bindingId="run",
                queue=service.queue_ref(service.policy.input_queue).model_dump(
                    mode="json"
                ),
                itemId=item,
                idempotencyKey="producing-selection",
            ),
        ).execution
    c.done = app_tests.call(
        c, "canvas_dispatch", app_tests.request(state, action="execute")
    ).execution
    c.output_request = app_tests.request(c.done, action="outputs")
    return c


def read(c, **extra):
    return app_tests.call(
        c, "canvas_get_state", dict(c.output_request, **extra)
    ).execution


def test_exact_produced_children_are_read_only(produced):
    c = produced
    before = len(c.db.all(FencedWorkItem))
    page = read(c)
    opened = app_tests.call(c, "canvas_get", {}, c.model)
    assert opened.generic_interaction["outputBindings"] == [
        {"bindingId": "run", "queue": page["queue"]}
    ]
    assert page["runId"] == c.done["runId"] and page["attemptId"] == c.done["attemptId"]
    assert page["queue"] == c.output_service.queue_ref(
        c.output_service.policy.output_queue
    ).model_dump(mode="json")
    assert len(page["items"]) == 1 and "child" in page["items"][0]["preview"]
    assert page["items"][0]["parentId"] == c.done.get("workItemId")
    assert (
        read(c) == page
        and len(c.db.all(FencedWorkItem)) == before
        and c.output_runner.calls == 1
    )


def child_row(c):
    rows = c.db.all(
        FencedWorkItem,
        where="workspace_id=? AND queue_name=?",
        values=[
            c.output_service.snapshot.workspace_id,
            c.output_service.policy.output_queue,
        ],
    )
    assert len(rows) == 1
    return rows[0]


@pytest.mark.parametrize(
    "corruption",
    ["snapshot", "fence", "digest", "parent", "row_parent", "payload", "extra"],
)
def test_output_lineage_and_retained_publication_are_required(produced, corruption):
    c = produced
    row = child_row(c)
    value = json.loads(row.payload)
    if corruption == "snapshot":
        value["produced_by"]["snapshot"]["deployment"]["revision_id"] = (
            "sha256:" + "f" * 64
        )
    elif corruption == "fence":
        value["produced_by"]["fence"]["epoch"] += 1
    elif corruption == "digest":
        value["produced_by"]["input_digest"] = "sha256:" + "0" * 64
    elif corruption == "parent":
        value["produced_by"]["parent_id"] = str(uuid4())
    elif corruption == "payload":
        value["payload"] = {"value": "forged"}
    elif corruption == "extra":
        value["untrusted"] = True
    with c.db.transaction():
        _update(
            c.db,
            FencedWorkItem,
            row.id,
            {"parent_id": str(uuid4())}
            if corruption == "row_parent"
            else {"payload": _canonical(value, 262144)},
        )
    with pytest.raises((FenceRejected, ValueError)):
        read(c)


def test_foreign_run_and_cursor_cannot_disclose_children(produced):
    c = produced
    first = read(c)
    if c.output_service.policy.input_queue is None:
        state = app_tests.submit(c, key="second-producer")
    else:
        item = c.output_service.enqueue(
            c.output_caller, {"value": "other"}, "other-parent"
        )
        state = app_tests.call(
            c,
            "canvas_dispatch",
            dict(
                mode="generic",
                action="submit_input",
                bindingId="run",
                queue=c.output_service.queue_ref(
                    c.output_service.policy.input_queue
                ).model_dump(mode="json"),
                itemId=item,
                idempotencyKey="second-selected",
            ),
        ).execution
    done = app_tests.call(
        c, "canvas_dispatch", app_tests.request(state, action="execute")
    ).execution
    other = app_tests.call(
        c, "canvas_get_state", app_tests.request(done, action="outputs")
    ).execution
    assert first["items"][0]["itemId"] != other["items"][0]["itemId"]
    assert read(c) == first
    with pytest.raises(AccessDenied):
        read(c, cursor=other["items"][0]["itemId"])
    with pytest.raises(AccessDenied):
        read(c, runId=str(uuid4()))


@pytest.mark.parametrize("permission", ["read", "artifact"])
def test_output_queue_permissions_remain_live(produced, permission):
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.managed_work_items.contracts import Permission

    c = produced
    read(c)
    revoked = (
        Permission.READ.value
        if permission == "read"
        else Permission.ARTIFACT_READ.value
    )
    with c.db.transaction():
        for row in c.db.all(FoundryAccessGrant):
            permissions = json.loads(row.operations_json)
            if revoked in permissions:
                _update(
                    c.db,
                    FoundryAccessGrant,
                    row.id,
                    {
                        "operations_json": json.dumps(
                            [p for p in permissions if p != revoked]
                        )
                    },
                )
    with pytest.raises(AccessDenied):
        read(c)


@pytest.mark.parametrize("output_count", [21], indirect=True)
def test_output_pagination_is_bounded_and_read_only(produced):
    from actions.server.foundry.models import FoundryRequest

    c = produced
    counts = (
        len(c.db.all(Run)),
        len(c.db.all(FencedWorkItem)),
        len(c.db.all(FoundryRequest)),
    )
    page = read(c)
    assert len(page["items"]) == 20 and page["nextCursor"]
    second = read(c, cursor=page["nextCursor"])
    assert len(second["items"]) == 1 and second["nextCursor"] is None
    assert not {v["itemId"] for v in page["items"]} & {
        v["itemId"] for v in second["items"]
    }
    assert (
        len(c.db.all(Run)),
        len(c.db.all(FencedWorkItem)),
        len(c.db.all(FoundryRequest)),
    ) == counts
    assert c.output_runner.calls == 1


def test_output_inspection_requires_app_scope_and_exact_run(produced):
    from pydantic import ValidationError

    c = produced
    with pytest.raises(AccessDenied):
        app_tests.call(c, "canvas_get_state", c.output_request, c.model)
    with pytest.raises(AccessDenied):
        read(c, bindingId="foreign")
    with pytest.raises(ValidationError):
        read(c, itemId=str(uuid4()))
    with pytest.raises(ValidationError):
        read(c, adopt=True)


def test_output_scan_fails_closed_at_bounded_storage_size(produced):
    from dataclasses import replace

    c = produced
    row = child_row(c)
    with c.db.transaction():
        c.db.insert(replace(row, id=str(uuid4()), parent_id="", payload="x" * 1048577))
    with pytest.raises(FenceRejected, match="bounded projection"):
        read(c)


def test_matching_lineage_cannot_invent_extra_published_children(produced):
    from dataclasses import replace

    c = produced
    row = child_row(c)
    with c.db.transaction():
        c.db.insert(replace(row, id=str(uuid4())))
    with pytest.raises(FenceRejected, match="retained publication"):
        read(c)
