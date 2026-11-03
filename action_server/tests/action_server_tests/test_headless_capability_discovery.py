"""Bounded headless discovery requires an explicit active model selection."""

import base64
import json
from uuid import uuid4

import pytest
from action_server_tests import test_generic_work_item_execution as fixtures

from actions.server.deployments.foundry_values import DeploymentSpecification
from actions.server.deployments.ids import DeploymentId, WorkspaceId
from actions.server.foundry import headless_discovery
from actions.server.foundry.headless_discovery import (
    HeadlessCapabilityDiscovery,
    MAX_CURSOR_OFFSET,
    MAX_PAGE_SIZE,
    _encode_cursor,
)
from actions.server.foundry.mcp import CanvasCaller
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.managed_work_items.contracts import Permission
from actions.server.run_outputs.models import RunAdmission
from actions.server.run_outputs.service import AccessDenied, RunOutputControlPlane

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def world(database_location, foundry_package_store, request):
    fixture = fixtures.generic.__wrapped__(database_location, foundry_package_store)
    setup = next(fixture)
    try:
        yield setup(getattr(request, "param", "optional"))
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def _published(world, deployment_id=None):
    old_snapshot = world.owner.snapshot
    workspace_id = old_snapshot.deployment.workspace_id
    deployments = world.owner.deployments
    deployment_id = deployment_id or old_snapshot.deployment_id
    current = deployments._repository.current(
        workspace_id, old_snapshot.deployment_id
    )
    values = current.revision.specification.model_dump(mode="json", by_alias=True)
    values["model_published_capabilities"] = [
        old_snapshot.capability.model_dump(mode="json")
    ]
    selection = DeploymentSpecification.model_validate_json(json.dumps(values))
    if deployment_id == old_snapshot.deployment_id:
        # Publishing a replacement revision requires deploy authority on the
        # currently active revision as well as the new revision. Use the same
        # normal grant fixture as the execution tests; do not bypass policy.
        fixtures.grant(
            world.db,
            world.caller.actor,
            workspace_id,
            "reference",
            reference_grant_subject(current.revision.ref),
            ["deploy"],
        )
        revision = deployments.publish(
            world.caller.actor,
            workspace_id,
            deployment_id,
            current.revision.ref,
            selection,
            idempotency_key="headless-publish-existing",
        )
    else:
        revision = deployments.create(
            world.caller.actor,
            workspace_id,
            deployment_id,
            selection,
            idempotency_key="headless-publish-" + str(deployment_id.root),
        )
    fixtures.grant(
        world.db,
        world.caller.actor,
        workspace_id,
        "reference",
        reference_grant_subject(revision.ref),
        ["deploy", "execute", "read_application", *[p.value for p in Permission]],
    )
    snapshot = deployments.resolve(
        world.caller.actor,
        workspace_id,
        deployment_id,
        old_snapshot.capability,
        revision=revision.ref,
    ).snapshot
    control = RunOutputControlPlane(world.db, capabilities=world.owner.registry)
    control.register(snapshot)
    control.grant(world.caller.actor, snapshot.deployment, {"execute", "read"})
    return snapshot


def _discovery(world):
    return HeadlessCapabilityDiscovery(
        world.owner.deployments, world.owner.base, world.owner.authorization
    )


def _model_caller(snapshot, actor):
    return CanvasCaller(
        actor=actor,
        workspace_id=snapshot.workspace_id,
        audience="model",
    )


def test_unpublished_headless_capability_is_not_discovered(world):
    snapshot = world.owner.snapshot
    page = _discovery(world).page(_model_caller(snapshot, world.caller.actor))
    assert page.descriptors == ()
    assert page.availability == "unavailable"
    assert page.readiness == "not-checked"
    assert page.next_cursor is None


@pytest.mark.parametrize(
    ("world", "standalone_allowed", "claim_allowed"),
    [("optional", True, False), ("consumer", False, True)],
    indirect=["world"],
)
def test_active_model_publication_returns_exact_typed_snapshot(
    world, standalone_allowed, claim_allowed
):
    snapshot = _published(world)
    grants_before = world.db.all(FoundryAccessGrant)
    admissions_before = world.db.all(RunAdmission)
    page = _discovery(world).page(_model_caller(snapshot, world.caller.actor))
    assert page.availability == "authorized"
    assert len(page.descriptors) == 1
    descriptor = page.descriptors[0]
    assert descriptor.snapshot == snapshot
    assert descriptor.mode == "generic"
    assert descriptor.standalone_allowed is standalone_allowed
    assert descriptor.claim_allowed is claim_allowed
    assert descriptor.readiness == "not-checked"
    assert descriptor.input_schema["type"] == "object"
    assert "default" not in json.dumps(descriptor.input_schema)
    assert world.db.all(RunAdmission) == admissions_before
    assert world.db.all(FoundryAccessGrant) == grants_before


def test_projection_drops_untrusted_schema_descriptions_and_unknown_metadata(
    monkeypatch,
):
    marker = "private-schema-marker"
    schema_value = {
        "type": "object",
        "title": marker,
        "description": marker,
        "examples": [marker],
        "x-private-metadata": marker,
        "properties": {
            "value": {
                "type": "string",
                "description": marker,
                "default": marker,
                "example": marker,
                "pattern": "^[a-z]+$",
                "enum": ["approved", "pending"],
                "x-private-metadata": marker,
            }
        },
    }
    monkeypatch.setattr(
        headless_discovery,
        "_input_schema",
        lambda _registry, _snapshot: schema_value,
    )

    projected = headless_discovery._model_input_schema(None, None)
    assert marker not in json.dumps(projected)
    assert projected["properties"]["value"]["enum"] == [
        "approved",
        "pending",
    ]
    assert (
        projected["properties"]["value"]["pattern"] == "^[a-z]+$"
    )


def test_projection_preserves_supported_assertions_and_internal_references(
    monkeypatch,
):
    from jsonschema import Draft202012Validator

    schema_value = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": {"positive": {"type": "string", "minLength": 2}},
        "type": "object",
        "dependentRequired": {"credit_card": ["billing_address"]},
        "properties": {
            "value": {"$ref": "#/$defs/positive"},
            "rows": {
                "type": "array",
                "contains": {"type": "integer", "minimum": 0},
                "minContains": 2,
                "maxContains": 4,
            },
        },
    }
    monkeypatch.setattr(
        headless_discovery,
        "_input_schema",
        lambda _registry, _snapshot: schema_value,
    )

    projected = headless_discovery._model_input_schema(None, None)

    assert projected["dependentRequired"] == {
        "credit_card": ["billing_address"]
    }
    assert projected["properties"]["rows"]["minContains"] == 2
    assert projected["properties"]["rows"]["maxContains"] == 4
    assert projected["properties"]["value"]["$ref"] == "#/$defs/positive"
    assert projected["$defs"]["positive"] == {
        "type": "string",
        "minLength": 2,
    }
    validator = Draft202012Validator(projected)
    assert not validator.is_valid({"credit_card": "present"})
    assert not validator.is_valid({"rows": [1]})
    assert not validator.is_valid({"rows": [1, 2, 3, 4, 5]})
    assert not validator.is_valid({"value": "x"})
    assert validator.is_valid(
        {
            "credit_card": "present",
            "billing_address": "x",
            "rows": [1, 2],
            "value": "ok",
        }
    )


@pytest.mark.parametrize(
    "schema_value",
    [
        {"type": "object", "unknownAssertion": True},
        {"$ref": "https://private.example/schema.json"},
        {"$ref": "#private-marker"},
        {"$schema": "http://json-schema.org/draft-07/schema#"},
        {"$vocabulary": {"https://example.test/custom": True}},
        {
            "$id": "https://private.example/schema.json",
            "$defs": {"private": {"type": "string"}},
            "$ref": "#/$defs/private",
        },
        {"$anchor": "private-marker"},
        {"$dynamicAnchor": "private-marker"},
        {"$dynamicRef": "#private-marker"},
    ],
)
def test_projection_rejects_unsupported_schema_semantics(monkeypatch, schema_value):
    monkeypatch.setattr(
        headless_discovery,
        "_input_schema",
        lambda _registry, _snapshot: schema_value,
    )

    with pytest.raises(AccessDenied):
        headless_discovery._model_input_schema(None, None)


def test_revoked_run_authority_omits_cached_publication(world):
    snapshot = _published(world)
    discovery = _discovery(world)
    caller = _model_caller(snapshot, world.caller.actor)
    assert discovery.page(caller).descriptors
    RunOutputControlPlane(world.db).revoke(
        world.caller.actor, snapshot.deployment
    )
    page = discovery.page(caller)
    assert page.descriptors == ()
    assert page.availability == "unavailable"


def test_cursor_is_workspace_bound_and_page_size_is_bounded(world):
    snapshot = world.owner.snapshot
    discovery = _discovery(world)
    caller = _model_caller(snapshot, world.caller.actor)
    with pytest.raises(ValueError, match="page size"):
        discovery.page(caller, limit=MAX_PAGE_SIZE + 1)
    with pytest.raises(AccessDenied, match="cursor"):
        discovery.page(caller, cursor="not-a-cursor")
    foreign_cursor = _encode_cursor(
        WorkspaceId(uuid4()), 0, 0, "sha256:" + "0" * 64
    )
    with pytest.raises(AccessDenied, match="outside authenticated Workspace"):
        discovery.page(caller, cursor=foreign_cursor)
    with pytest.raises(AccessDenied, match="model context"):
        discovery.page(
            CanvasCaller(
                actor=world.caller.actor,
                workspace_id=snapshot.workspace_id,
                audience="app",
            )
        )


def test_pagination_reprocesses_no_prior_published_descriptor(world):
    first = _published(world)
    second = _published(world, DeploymentId(uuid4()))
    discovery = _discovery(world)
    caller = _model_caller(first, world.caller.actor)
    one = discovery.page(caller, limit=1)
    assert len(one.descriptors) == 1
    assert one.next_cursor is not None
    same_first_page = discovery.page(caller, limit=1)
    assert same_first_page.descriptors == one.descriptors
    cursor_payload = base64.urlsafe_b64decode(
        one.next_cursor + "=" * (-len(one.next_cursor) % 4)
    ).decode()
    assert set(json.loads(cursor_payload)) == {
        "workspaceId",
        "deploymentOffset",
        "candidateOffset",
        "inventoryDigest",
    }
    assert str(first.deployment_id) not in cursor_payload
    assert first.capability.capability_id.root not in cursor_payload
    two = discovery.page(caller, limit=1, cursor=one.next_cursor)
    assert len(two.descriptors) == 1
    assert {
        one.descriptors[0].snapshot.deployment_id,
        two.descriptors[0].snapshot.deployment_id,
    } == {first.deployment_id, second.deployment_id}


def test_cursor_rejects_head_insertion_and_excessive_offsets(world):
    first = _published(world)
    _published(world, DeploymentId(uuid4()))
    discovery = _discovery(world)
    caller = _model_caller(first, world.caller.actor)
    page = discovery.page(caller, limit=1)
    assert page.next_cursor is not None

    _published(world, DeploymentId(uuid4()))
    with pytest.raises(AccessDenied, match="catalog changed"):
        discovery.page(caller, limit=1, cursor=page.next_cursor)

    oversized = base64.urlsafe_b64encode(
        json.dumps(
            {
                "workspaceId": first.workspace_id,
                "deploymentOffset": MAX_CURSOR_OFFSET + 1,
                "candidateOffset": 0,
                "inventoryDigest": "sha256:" + "0" * 64,
            }
        ).encode()
    ).decode().rstrip("=")
    with pytest.raises(AccessDenied, match="cursor"):
        discovery.page(caller, cursor=oversized)


def test_cursor_rechecks_grants_after_page(world):
    snapshots = [
        _published(world),
        _published(world, DeploymentId(uuid4())),
    ]
    discovery = _discovery(world)
    caller = _model_caller(snapshots[0], world.caller.actor)
    first_page = discovery.page(caller, limit=1)
    assert first_page.next_cursor is not None
    remaining = next(
        snapshot
        for snapshot in snapshots
        if snapshot.deployment_id
        != first_page.descriptors[0].snapshot.deployment_id
    )
    RunOutputControlPlane(world.db).revoke(
        world.caller.actor, remaining.deployment
    )
    second_page = discovery.page(caller, limit=1, cursor=first_page.next_cursor)
    assert second_page.descriptors == ()


def test_workspace_inventory_digest_has_a_fail_closed_bound(world, monkeypatch):
    snapshot = world.owner.snapshot
    monkeypatch.setattr(headless_discovery, "MAX_CURSOR_OFFSET", 0)
    with pytest.raises(AccessDenied, match="catalog exceeds its bound"):
        _discovery(world).page(_model_caller(snapshot, world.caller.actor))
