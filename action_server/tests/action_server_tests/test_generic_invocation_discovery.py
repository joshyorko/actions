"""Model-safe discovery over real canonical SQL; synthetic runner only."""
import asyncio
import json
from uuid import uuid4

import pytest
from action_server_tests import test_generic_work_item_execution as fixtures
from action_server_tests.test_generic_execution_port import SyntheticRunner
from actions.canvas_contract import validate_canvas_spec

from actions.server._models import Run
from actions.server.deployments.foundry_values import (
    CanvasCapabilityBinding,
    DeploymentSpecification,
    canvas_revision_digest,
)
from actions.server.deployments.ids import DeploymentId
from actions.server.foundry.generic_execution_port import GenericCanvasExecution
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.mcp import CanvasCaller, CanvasReply
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.managed_work_items.contracts import Permission
from actions.server.run_outputs.models import RunAdmission
from actions.server.run_outputs.service import (
    AccessDenied,
    RunOutputControlPlane,
    _update,
)
from actions.server.run_outputs.types import CanvasApplicationRef

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def bound(database_location, foundry_package_store, request):
    fixture = fixtures.generic.__wrapped__(database_location, foundry_package_store)
    setup = next(fixture)
    try:
        g = setup("optional")
        old = g.owner.snapshot
        app = DeploymentId(uuid4())
        binding_ids = (
            ["echo"]
            if getattr(request, "param", 1) == 1
            else [f"echo{i}" for i in range(request.param)]
        )
        spec = validate_canvas_spec(
            {
                "schemaVersion": "actions.canvas-spec/v1",
                "title": "Discovery",
                "visibility": ["model", "app"],
                "bindingIds": binding_ids,
                "root": {
                    "type": "stack",
                    "id": "root",
                    "children": [
                        {"type": "status", "id": f"output{i}", "bindingId": binding}
                        for i, binding in enumerate(binding_ids)
                    ],
                },
            }
        )
        bindings = tuple(
            CanvasCapabilityBinding(binding_id=name, capability=old.capability)
            for name in binding_ids
        )
        current = g.owner.deployments._repository.current(
            old.deployment.workspace_id, old.deployment.deployment_id
        )
        values = current.revision.specification.model_dump(mode="json")
        values.update(
            canvas_spec=spec.model_dump(mode="json", by_alias=True),
            canvas_bindings=[binding.model_dump(mode="json") for binding in bindings],
            canvas_application=CanvasApplicationRef(
                workspace_id=old.workspace_id,
                app_id=str(app.root),
                revision_id=canvas_revision_digest(
                    spec, bindings, current.revision.specification.package_revisions
                ),
            ).model_dump(mode="json"),
        )
        selection = DeploymentSpecification.model_validate_json(json.dumps(values))
        revision = g.owner.deployments.create(
            g.caller.actor,
            old.deployment.workspace_id,
            app,
            selection,
            idempotency_key="bound-app",
        )
        grant = fixtures.grant(
            g.db,
            g.caller.actor,
            old.deployment.workspace_id,
            "reference",
            reference_grant_subject(revision.ref),
            ["deploy", "execute", "read_application", *[p.value for p in Permission]],
        )
        snapshot = g.owner.deployments.resolve(
            g.caller.actor, old.deployment.workspace_id, app, old.capability
        ).snapshot
        RunOutputControlPlane(g.db, capabilities=g.owner.registry).grant(
            g.caller.actor, snapshot.deployment, {"execute", "read"}
        )
        g.owner = GenericWorkItemExecution(
            g.owner.deployments,
            g.owner.base,
            snapshot,
            g.owner.policy,
            g.owner.authorization,
        )
        g.grant = grant
        g.caller_model = CanvasCaller(g.caller.actor, snapshot.workspace_id, "model")
        yield g
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


class View:
    schemas: dict[str, dict] = {
        "canvas_dispatch": {},
        "capability_invoke": {},
        "canvas_get": {},
        "canvas_inspect": {},
    }

    def __init__(self, g):
        self.g = g

    async def call(self, caller, name, args):
        snapshot = self.g.owner.snapshot
        return CanvasReply(
            summary="authorized app",
            model_result={
                "applicationId": snapshot.deployment_id,
                "revisionId": snapshot.deployment.revision_id.root,
                "activeRevisionId": snapshot.deployment.revision_id.root,
            },
            view_state={
                "private-result": "must-not-leak",
                "private-token": "not-a-model-descriptor",
                "connection-secret": "synthetic-connection-secret",
                "backend-source": "synthetic-backend-source",
            },
        )


def port(g):
    return GenericCanvasExecution(
        View(g),
        g.owner.deployments,
        g.owner.base,
        g.owner.authorization,
        worker_id=g.caller.worker_id,
        runner=SyntheticRunner(),
    )


def get(g, name="canvas_get"):
    return asyncio.run(
        port(g).call(g.caller_model, name, {"appId": g.owner.snapshot.deployment_id})
    )


def test_descriptor_exact_model_shape_without_admission_or_mutation(bound):
    g = bound
    before = (len(g.db.all(RunAdmission)), len(g.db.all(FoundryAccessGrant)))
    result = get(g)
    descriptors = result.model_result["invocationDescriptors"]
    assert len(descriptors) == 1
    descriptor = descriptors[0]
    assert descriptor["snapshot"] == g.owner.snapshot.model_dump(mode="json")
    assert descriptor["bindingId"] == "echo" and descriptor["standaloneAllowed"]
    assert descriptor["inputQueue"] == g.owner.queue_ref(
        g.owner.policy.input_queue
    ).model_dump(mode="json")
    for private in (
        "private-result",
        "private-token",
        "not-a-model-descriptor",
        "synthetic-connection-secret",
        "synthetic-backend-source",
    ):
        assert private not in json.dumps(descriptor)
    assert "private-result" not in json.dumps(result.model_result)
    assert (len(g.db.all(RunAdmission)), len(g.db.all(FoundryAccessGrant))) == before
    assert not g.db.all(Run)
    assert get(g, "canvas_inspect").model_result["invocationDescriptors"] == descriptors


@pytest.mark.parametrize("revoke", ["run", "foundry"])
def test_descriptor_revocation_exposes_no_private_reference(bound, revoke):
    g = bound
    if revoke == "run":
        RunOutputControlPlane(g.db).revoke(g.caller.actor, g.owner.snapshot.deployment)
    else:
        with g.db.transaction():
            _update(
                g.db,
                FoundryAccessGrant,
                g.grant.id,
                {"operations_json": '["read_application"]'},
            )
    reply = get(g)
    assert reply.model_result["invocationDescriptors"] == []
    assert reply.model_result["invocationAvailability"] == "unavailable"
    assert "package_id" not in json.dumps(reply.model_result)


def test_discovered_descriptor_invokes_and_registers_only_on_dispatch(bound):
    g = bound
    descriptor = get(g).model_result["invocationDescriptors"][0]
    before = len(g.db.all(RunAdmission))
    reply = asyncio.run(
        port(g).call(
            g.caller_model,
            "capability_invoke",
            {
                "mode": "generic",
                "snapshot": descriptor["snapshot"],
                "inputs": {"value": "from descriptor"},
                "idempotencyKey": "invoke-discovered",
            },
        )
    )
    assert reply.model_result["execution"]["state"] == "completed"
    assert len(g.db.all(RunAdmission)) == before + 1 and len(g.db.all(Run)) == 1


def test_denied_dispatch_does_not_register(bound):
    g = bound
    RunOutputControlPlane(g.db).revoke(g.caller.actor, g.owner.snapshot.deployment)
    before = len(g.db.all(RunAdmission))
    with pytest.raises(AccessDenied):
        g.owner.dispatch_standalone(
            g.caller, {"value": "denied"}, "denied", lease_seconds=30
        )
    assert len(g.db.all(RunAdmission)) == before and not g.db.all(Run)


def test_app_audience_never_receives_model_descriptor(bound):
    g = bound
    caller = CanvasCaller(g.caller.actor, g.owner.snapshot.workspace_id, "app")
    reply = asyncio.run(
        port(g).call(caller, "canvas_get", {"appId": g.owner.snapshot.deployment_id})
    )
    assert "invocationDescriptors" not in reply.model_result


def test_nonactive_reported_revision_and_unconfigured_provider_omit_descriptor(bound):
    g = bound
    p = port(g)
    original = p.reviewed.call

    async def stale(caller, name, args):
        from dataclasses import replace

        reply = await original(caller, name, args)
        return replace(
            reply,
            model_result=dict(reply.model_result, revisionId="sha256:" + "f" * 64),
        )

    p.reviewed.call = stale
    reply = asyncio.run(
        p.call(g.caller_model, "canvas_get", {"appId": g.owner.snapshot.deployment_id})
    )
    assert reply.model_result["invocationDescriptors"] == []
    g.owner.base.providers = {}
    assert get(g).model_result["invocationDescriptors"] == []


def test_registration_rolls_back_with_failed_admission(bound, monkeypatch):
    g = bound
    before = len(g.db.all(RunAdmission))
    grants = g.db.all(FoundryAccessGrant)

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic claim failure")

    monkeypatch.setattr(g.owner.base, "claim", fail)
    with pytest.raises(RuntimeError, match="synthetic"):
        g.owner.dispatch_standalone(
            g.caller, {"value": "valid"}, "rollback", lease_seconds=30
        )
    assert len(g.db.all(RunAdmission)) == before
    assert not g.db.all(Run) and g.db.all(FoundryAccessGrant) == grants


def test_registration_is_idempotent_and_never_grants(bound):
    g = bound
    grants = g.db.all(FoundryAccessGrant)
    before = len(g.db.all(RunAdmission))
    one = g.owner.dispatch_standalone(
        g.caller, {"value": "valid"}, "same", lease_seconds=30
    )
    two = g.owner.dispatch_standalone(
        g.caller, {"value": "valid"}, "same", lease_seconds=30
    )
    assert one == two and len(g.db.all(RunAdmission)) == before + 1
    assert len(g.db.all(Run)) == 1 and g.db.all(FoundryAccessGrant) == grants


def test_large_existing_history_preserved_and_readiness_not_claimed(bound):
    g = bound
    p = port(g)
    original = p.reviewed.call
    history = [{"summary": "x" * 1024} for _ in range(150)]

    async def large(caller, name, args):
        from dataclasses import replace

        reply = await original(caller, name, args)
        return replace(reply, model_result=dict(reply.model_result, history=history))

    p.reviewed.call = large
    reply = asyncio.run(
        p.call(
            g.caller_model, "canvas_inspect", {"appId": g.owner.snapshot.deployment_id}
        )
    )
    assert reply.model_result["history"] == history
    assert reply.model_result["invocationAvailability"] == "authorized"
    assert reply.model_result["invocationReadiness"] == "not-checked"


def test_unsupported_output_routing_omitted_before_constructor(bound, monkeypatch):
    import actions.server.foundry.invocation_discovery as discovery

    g = bound
    repository = g.owner.deployments._repository
    original = repository.current

    def unsupported(*args, **kwargs):
        current = original(*args, **kwargs)
        spec = current.revision.specification
        policy = spec.work_item_policies[0].model_copy(
            update={"output_queue": "different-output"}
        )
        changed = spec.model_copy(update={"work_item_policies": (policy,)})
        return current.model_copy(
            update={
                "revision": current.revision.model_copy(
                    update={"specification": changed}
                )
            }
        )

    monkeypatch.setattr(repository, "current", unsupported)

    def forbidden(*args, **kwargs):
        raise AssertionError("unsupported adapter must not be constructed")

    monkeypatch.setattr(discovery, "GenericWorkItemExecution", forbidden)
    assert get(g).model_result["invocationDescriptors"] == []


def test_schema_is_exact_registry_projection(bound):
    g = bound
    descriptor = get(g).model_result["invocationDescriptors"][0]
    assert descriptor["inputSchema"] == json.loads(
        g.owner.registry.schema_for(g.owner.snapshot).input_schema
    )
    assert "input_schema" not in descriptor


@pytest.mark.parametrize("mutation", ["digest", "capability"])
def test_schema_identity_tamper_omits_descriptor(bound, monkeypatch, mutation):
    from dataclasses import replace

    g = bound
    registry = g.owner.registry
    original = registry.schema_for

    def changed(snapshot):
        schema = original(snapshot)
        if mutation == "digest":
            return replace(schema, input_schema='{"type":"object","properties":{}}')
        capability = schema.capability.model_copy(update={"capability_id": "wrong"})
        return replace(schema, capability=capability)

    monkeypatch.setattr(registry, "schema_for", changed)
    assert get(g).model_result["invocationDescriptors"] == []


def test_schema_projection_preserves_property_alias_and_bounds_size(bound, monkeypatch):
    import hashlib
    from dataclasses import replace

    from actions.server.foundry.invocation_discovery import _input_schema

    g = bound
    registry = g.owner.registry
    original_schema = registry.schema_for(g.owner.snapshot)
    original_capability = registry.get_capability(g.owner.snapshot.capability)
    raw = json.dumps(
        {
            "type": "object",
            "properties": {
                "default": {
                    "type": "string",
                    "default": "private-default",
                    "examples": ["private-example"],
                }
            },
            "required": ["default"],
        }
    )
    monkeypatch.setattr(
        registry,
        "schema_for",
        lambda snapshot: replace(original_schema, input_schema=raw),
    )
    monkeypatch.setattr(
        registry,
        "get_capability",
        lambda capability: replace(
            original_capability,
            schema_digest="sha256:" + hashlib.sha256(raw.encode()).hexdigest(),
        ),
    )
    projected = _input_schema(registry, g.owner.snapshot)
    assert projected["properties"] == {"default": {"type": "string"}}
    assert projected["required"] == ["default"]
    raw = json.dumps({"type": "object", "description": "x" * 32768})
    with pytest.raises(AccessDenied, match="discovery bound"):
        _input_schema(registry, g.owner.snapshot)


def test_stored_package_schema_tamper_fails_closed(bound):
    g = bound
    with g.db.transaction():
        g.db.execute(
            "UPDATE foundry_package_revision SET manifest_json='{}' WHERE revision_id=?",
            [g.owner.snapshot.capability.package_revision.revision_id.root],
        )
    assert get(g).model_result["invocationDescriptors"] == []


def test_configured_descriptions_preserve_base_and_explain_reference_boundary(bound):
    p = port(bound)
    for name in ("canvas_get", "canvas_inspect"):
        assert "description" not in p.reviewed.schemas[name]
        assert p.schemas[name] is not p.reviewed.schemas[name]
        description = p.schemas[name]["description"]
        assert "References are not grants" in description
        assert "execution references and input schemas" in description
        assert (
            "Backend source, connection secrets, and app-session metadata remain omitted"
            in description
        )
        assert "not execution readiness" in description


@pytest.mark.parametrize("bound", [32], indirect=True)
def test_valid_multi_binding_aggregate_overflow_preserves_canvas_reply(
    bound, monkeypatch
):
    import actions.server.foundry.invocation_discovery as discovery
    from actions.server.run_outputs.service import _canonical

    g = bound
    schema = {"type": "object", "description": "x" * 8192}
    assert len(_canonical(schema, 32 * 1024)) < 32 * 1024
    monkeypatch.setattr(discovery, "_input_schema", lambda registry, snapshot: schema)
    original = asyncio.run(
        port(g).reviewed.call(
            g.caller_model, "canvas_get", {"appId": g.owner.snapshot.deployment_id}
        )
    )
    reply = get(g)
    assert all(
        reply.model_result[key] == value for key, value in original.model_result.items()
    )
    assert reply.view_state == original.view_state
    assert reply.model_result["invocationDescriptors"] == []
    assert reply.model_result["invocationAvailability"] == "unavailable"
    assert reply.model_result["invocationOmission"] == "aggregate-size-limit"
    assert len(_canonical(reply.model_result, 128 * 1024)) < 128 * 1024
