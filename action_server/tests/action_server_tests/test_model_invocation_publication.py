"""Atomic publication guard tests using the real Deployment/Run SQL fixture."""

import json

import pytest
from actions.canvas_contract import validate_canvas_spec
from action_server_tests import test_generic_work_item_execution as fixtures

import actions.server.foundry.model_invocation_publication as publication_module
from actions.server.deployments.foundry_values import (
    CanvasCapabilityBinding,
    DeploymentSpecification,
    canvas_revision_digest,
)
from actions.server.deployments.ids import WorkspaceId
from actions.server.deployments.foundry_values import AccessDenied
from actions.server.foundry.model_invocation_publication import (
    ModelInvocationPublicationGuard,
)
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.managed_work_items.contracts import Permission
from actions.server.run_outputs.models import RunAdmission
from actions.server.run_outputs.types import CanvasApplicationRef

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def generic_world(database_location, foundry_package_store):
    source = fixtures.generic.__wrapped__(database_location, foundry_package_store)
    setup = next(source)
    try:
        yield setup("optional")
    finally:
        try:
            next(source)
        except StopIteration:
            pass


def _publish(g, selection, idempotency_key):
    old = g.owner.snapshot
    current = g.owner.deployments._repository.current(
        old.deployment.workspace_id, old.deployment.deployment_id
    )
    fixtures.grant(
        g.db,
        g.caller.actor,
        old.deployment.workspace_id,
        "reference",
        reference_grant_subject(current.revision.ref),
        ["deploy"],
    )
    revision = g.owner.deployments.publish(
        g.caller.actor,
        old.deployment.workspace_id,
        old.deployment.deployment_id,
        current.revision.ref,
        selection,
        idempotency_key=idempotency_key,
    )
    fixtures.grant(
        g.db,
        g.caller.actor,
        old.deployment.workspace_id,
        "reference",
        reference_grant_subject(revision.ref),
        ["deploy", "execute", "read_application", *[p.value for p in Permission]],
    )
    snapshot = g.owner.deployments.resolve(
        g.caller.actor,
        old.deployment.workspace_id,
        old.deployment.deployment_id,
        old.capability,
        revision=revision.ref,
    ).snapshot
    return snapshot


def _selection(g, *, model_publish=False, canvas_visibility=None):
    old = g.owner.snapshot
    current = g.owner.deployments._repository.current(
        old.deployment.workspace_id, old.deployment.deployment_id
    )
    value = current.revision.specification.model_dump(mode="json", by_alias=True)
    if model_publish:
        value["model_published_capabilities"] = [
            old.capability.model_dump(mode="json")
        ]
    if canvas_visibility is not None:
        binding_ids = ["lookup"]
        spec = validate_canvas_spec(
            {
                "schemaVersion": "actions.canvas-spec/v1",
                "title": "Model publication test",
                "visibility": [canvas_visibility],
                "bindingIds": binding_ids,
                "root": {
                    "type": "stack",
                    "id": "root",
                    "children": [
                        {
                            "type": "status",
                            "id": "result",
                            "bindingId": "lookup",
                        }
                    ],
                },
            }
        )
        bindings = (CanvasCapabilityBinding(binding_id="lookup", capability=old.capability),)
        app_id = old.deployment.deployment_id
        value["canvas_spec"] = spec.model_dump(mode="json", by_alias=True)
        value["canvas_bindings"] = [binding.model_dump(mode="json") for binding in bindings]
        value["canvas_application"] = CanvasApplicationRef(
            workspace_id=old.workspace_id,
            app_id=str(app_id.root),
            revision_id=canvas_revision_digest(
                spec, bindings, current.revision.specification.package_revisions
            ),
        ).model_dump(mode="json")
    return DeploymentSpecification.model_validate_json(json.dumps(value))


def test_unpublished_internal_capability_is_denied_before_admission(generic_world):
    g = generic_world
    snapshot = g.owner.snapshot
    before = g.db.all(RunAdmission)
    invoked = []
    guard = ModelInvocationPublicationGuard(g.owner.deployments)
    with pytest.raises(AccessDenied):
        guard.admit(g.caller.actor, snapshot, lambda resolved: invoked.append(resolved))
    assert invoked == []
    assert g.db.all(RunAdmission) == before


def test_missing_common_workspace_fails_closed_without_synthesizing_authority(
    monkeypatch,
):
    class EmptyDatabase:
        workspace_rows = []

        def in_transaction(self):
            return True

    db = EmptyDatabase()
    locked = []
    monkeypatch.setattr(
        publication_module,
        "_returning",
        lambda database, sql, values: [("run-counter",)],
    )

    def lock_workspace(database, workspace_id):
        locked.append(workspace_id)
        if not database.workspace_rows:
            raise AccessDenied("Run/output unavailable or access denied")

    monkeypatch.setattr(publication_module, "_lock_workspace", lock_workspace)
    guard = object.__new__(ModelInvocationPublicationGuard)
    guard.db = db
    workspace_id = WorkspaceId("00000000-0000-4000-8000-000000000123")
    with pytest.raises(AccessDenied):
        guard._lock_admission_workspace(workspace_id)
    assert locked == [str(workspace_id.root)]
    assert db.workspace_rows == []


def test_explicit_headless_publication_reauthorizes_exact_current_snapshot(
    generic_world,
):
    g = generic_world
    selection = _selection(g, model_publish=True)
    snapshot = _publish(g, selection, "guard-headless")
    before = g.db.all(RunAdmission)
    guard = ModelInvocationPublicationGuard(g.owner.deployments)

    def admitted(resolved):
        assert g.db.in_transaction()
        assert resolved.snapshot == snapshot
        return resolved.snapshot

    assert guard.admit(g.caller.actor, snapshot, admitted) == snapshot
    assert g.db.all(RunAdmission) == before


def test_current_model_visible_canvas_binding_preserves_model_invocation(
    generic_world,
):
    g = generic_world
    selection = _selection(g, canvas_visibility="model")
    snapshot = _publish(g, selection, "guard-canvas-model")
    guard = ModelInvocationPublicationGuard(g.owner.deployments)
    result = guard.admit(g.caller.actor, snapshot, lambda resolved: resolved.snapshot)
    assert result == snapshot


def test_app_only_canvas_binding_is_not_model_publication(generic_world):
    g = generic_world
    selection = _selection(g, canvas_visibility="app")
    snapshot = _publish(g, selection, "guard-canvas-app")
    invoked = []
    guard = ModelInvocationPublicationGuard(g.owner.deployments)
    with pytest.raises(AccessDenied):
        guard.admit(g.caller.actor, snapshot, lambda resolved: invoked.append(resolved))
    assert invoked == []


def test_stale_and_revoked_snapshots_fail_before_admission(generic_world):
    g = generic_world
    published = _publish(
        g, _selection(g, model_publish=True), "guard-before-revocation"
    )
    current = g.owner.deployments._repository.current(
        published.deployment.workspace_id, published.deployment.deployment_id
    )
    unpublished = DeploymentSpecification.model_validate_json(
        json.dumps(current.revision.specification.model_dump(mode="json"))
    )
    _publish(g, unpublished, "guard-revoke-publication")
    stale_called = []
    guard = ModelInvocationPublicationGuard(g.owner.deployments)
    with pytest.raises(AccessDenied):
        guard.admit(
            g.caller.actor, published, lambda resolved: stale_called.append(resolved)
        )
    assert stale_called == []

    current_snapshot = g.owner.deployments.resolve(
        g.caller.actor,
        published.deployment.workspace_id,
        published.deployment.deployment_id,
        published.capability,
    ).snapshot
    current_revision = current_snapshot.deployment
    grants = g.db.all(
        FoundryAccessGrant,
        where="subject_kind=? AND subject_id=?",
        values=("reference", reference_grant_subject(current_revision)),
    )
    assert len(grants) == 1
    with g.db.transaction():
        g.db.update_by_id(
            FoundryAccessGrant, grants[0].id, {"operations_json": '["deploy"]'}
        )
    revoked_called = []
    with pytest.raises(AccessDenied):
        guard.admit(
            g.caller.actor,
            current_snapshot,
            lambda resolved: revoked_called.append(resolved),
        )
    assert revoked_called == []
