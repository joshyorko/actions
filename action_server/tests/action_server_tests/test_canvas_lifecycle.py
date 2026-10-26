from __future__ import annotations

from pathlib import Path

import pytest

from actions.server.canvas_lifecycle import (
    CanvasAuthorizationError,
    CanvasResourceGrant,
    CanvasRevisionError,
    CanvasRevisionStore,
)
from actions.server.run_outputs.types import Actor

WORKSPACE = "workspace-a"
DEPLOYMENT = "sha256:" + "d" * 64
APP_ID = "invoice-review"
ACTOR = Actor(principal_id="00000000-0000-4000-8000-000000000001")
OTHER_ACTOR = Actor(principal_id="00000000-0000-4000-8000-000000000002")


def make_store(root: Path, *, allowed_workspace: str = "workspace-a"):
    validated: list[tuple[str, dict[str, bytes]]] = []
    authorized: list[tuple[str, CanvasResourceGrant]] = []

    def validate(app_id, files):
        validated.append((app_id, dict(files)))
        if "app.json" not in files:
            raise CanvasRevisionError("app.json is required")

    def authorize(grant, operation):
        authorized.append((operation, grant))
        return (
            grant.actor == ACTOR
            and grant.workspace_id == allowed_workspace
            and grant.deployment_revision_id == DEPLOYMENT
            and (operation != "read_resource" or grant.app_revision_id != "")
        )

    store = CanvasRevisionStore(
        root,
        validator=validate,
        authorize=authorize,
    )
    return store, validated, authorized


def grant(revision_id: str, *, workspace: str = "workspace-a"):
    return CanvasResourceGrant(
        actor=ACTOR,
        workspace_id=workspace,
        deployment_revision_id=DEPLOYMENT,
        app_id=APP_ID,
        app_revision_id=revision_id,
    )


def test_stage_activate_pin_restart_and_rollback(tmp_path):
    store, validated, authorized = make_store(tmp_path / "canvas")
    first = store.stage(
        ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b'{"version":1}'}
    )
    assert validated == [("invoice-review", {"app.json": b'{"version":1}'})]
    store.activate(
        ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, first.revision_id, expected_current=None
    )
    pinned = store.pin_active(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID)

    second = store.stage(
        ACTOR,
        WORKSPACE,
        DEPLOYMENT,
        APP_ID,
        {"app.json": b'{"version":2}', "views/main.json": b"{}"},
    )
    store.activate(
        ACTOR,
        WORKSPACE,
        DEPLOYMENT,
        APP_ID,
        second.revision_id,
        expected_current=first.revision_id,
    )
    # An invocation retains the revision resolved before activation.
    assert pinned.revision_id == first.revision_id
    assert pinned.files["app.json"] == b'{"version":1}'

    reopened, _, reopened_authorized = make_store(tmp_path / "canvas")
    assert (
        reopened.pin_active(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID).revision_id
        == second.revision_id
    )
    assert (
        reopened.rollback(
            ACTOR,
            WORKSPACE,
            DEPLOYMENT,
            APP_ID,
            expected_current=second.revision_id,
        )
        == first.revision_id
    )
    assert (
        reopened.pin_active(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID).files["app.json"]
        == b'{"version":1}'
    )
    assert {operation for operation, _ in authorized + reopened_authorized} == {
        "stage",
        "activate",
        "invoke",
        "rollback",
    }


def test_activation_is_compare_and_swap(tmp_path):
    store, _, _ = make_store(tmp_path / "canvas")
    first = store.stage(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"one"})
    other = store.stage(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"two"})
    store.activate(
        ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, first.revision_id, expected_current=None
    )
    with pytest.raises(CanvasRevisionError, match="active revision changed"):
        store.activate(
            ACTOR,
            WORKSPACE,
            DEPLOYMENT,
            APP_ID,
            other.revision_id,
            expected_current=None,
        )
    assert (
        store.pin_active(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID).revision_id
        == first.revision_id
    )
    with pytest.raises(CanvasRevisionError, match="app has no active revision"):
        store.pin_active(ACTOR, "workspace-b", DEPLOYMENT, APP_ID)


def test_stage_validates_paths_and_validator_before_persisting(tmp_path):
    store, _, _ = make_store(tmp_path / "canvas")
    with pytest.raises(CanvasRevisionError, match="unsafe revision path"):
        store.stage(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"../escape": b"x"})
    with pytest.raises(CanvasRevisionError, match="app.json is required"):
        store.stage(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"main.py": b"pass"})
    assert not list((tmp_path / "canvas" / "revisions").rglob("sha256"))


def test_resource_read_requires_server_authorized_exact_revision(tmp_path):
    store, _, _ = make_store(tmp_path / "canvas")
    revision = store.stage(
        ACTOR,
        WORKSPACE,
        DEPLOYMENT,
        APP_ID,
        {"app.json": b"ok", "view.html": b"<p>ok</p>"},
    )
    assert store.read_resource(grant(revision.revision_id), "view.html") == b"<p>ok</p>"
    with pytest.raises(CanvasAuthorizationError):
        store.read_resource(
            CanvasResourceGrant(
                actor=OTHER_ACTOR,
                workspace_id=WORKSPACE,
                deployment_revision_id=DEPLOYMENT,
                app_id=APP_ID,
                app_revision_id=revision.revision_id,
            ),
            "view.html",
        )
    with pytest.raises(CanvasAuthorizationError):
        store.read_resource(
            grant(revision.revision_id, workspace="workspace-b"), "view.html"
        )
    with pytest.raises(CanvasAuthorizationError):
        store.read_resource(
            CanvasResourceGrant(
                actor=ACTOR,
                workspace_id=WORKSPACE,
                deployment_revision_id="sha256:" + "e" * 64,
                app_id=APP_ID,
                app_revision_id=revision.revision_id,
            ),
            "view.html",
        )
    with pytest.raises(CanvasAuthorizationError):
        store.read_resource(grant(revision.revision_id), "missing.html")
    with pytest.raises(CanvasRevisionError, match="unsafe revision path"):
        store.read_resource(grant(revision.revision_id), "../app.json")


def test_revision_is_bound_to_exact_workspace_and_deployment(tmp_path):
    store, _, _ = make_store(tmp_path / "canvas")
    revision = store.stage(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"one"})
    store.activate(
        ACTOR,
        WORKSPACE,
        DEPLOYMENT,
        APP_ID,
        revision.revision_id,
        expected_current=None,
    )
    with pytest.raises(CanvasRevisionError, match="app has no active revision"):
        store.pin_active(ACTOR, "workspace-b", DEPLOYMENT, APP_ID)
    with pytest.raises(CanvasRevisionError, match="app has no active revision"):
        store.pin_active(ACTOR, WORKSPACE, "sha256:" + "e" * 64, APP_ID)


def test_denied_stage_and_activation_leave_pointer_unchanged(tmp_path):
    store, _, _ = make_store(tmp_path / "canvas", allowed_workspace="workspace-b")
    with pytest.raises(CanvasAuthorizationError):
        store.stage(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"denied"})

    allowed, _, _ = make_store(tmp_path / "canvas-allowed")
    first = allowed.stage(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"first"})
    allowed.activate(
        ACTOR,
        WORKSPACE,
        DEPLOYMENT,
        APP_ID,
        first.revision_id,
        expected_current=None,
    )
    staged = allowed.stage(
        ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"second"}
    )
    denied = CanvasRevisionStore(
        tmp_path / "canvas-allowed",
        validator=lambda app_id, files: None,
        authorize=lambda grant, operation: False,
    )
    with pytest.raises(CanvasAuthorizationError):
        denied.activate(
            ACTOR,
            WORKSPACE,
            DEPLOYMENT,
            APP_ID,
            staged.revision_id,
            expected_current=first.revision_id,
        )
    assert (
        allowed.pin_active(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID).revision_id
        == first.revision_id
    )


def test_tampered_revision_is_rejected_on_pinned_invocation(tmp_path):
    store, _, _ = make_store(tmp_path / "canvas")
    revision = store.stage(
        ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"original"}
    )
    store.activate(
        ACTOR,
        WORKSPACE,
        DEPLOYMENT,
        APP_ID,
        revision.revision_id,
        expected_current=None,
    )
    target = (
        tmp_path
        / "canvas"
        / "revisions"
        / WORKSPACE
        / DEPLOYMENT[7:]
        / APP_ID
        / revision.revision_id[7:]
        / "app.json"
    )
    target.chmod(0o600)
    target.write_bytes(b"tampered")
    with pytest.raises(CanvasRevisionError, match="digest verification"):
        store.pin_active(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID)


def test_rollback_requires_authority_for_the_revision_being_restored(tmp_path):
    store, _, _ = make_store(tmp_path / "canvas")
    first = store.stage(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"first"})
    second = store.stage(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"second"})
    store.activate(
        ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, first.revision_id, expected_current=None
    )
    store.activate(
        ACTOR,
        WORKSPACE,
        DEPLOYMENT,
        APP_ID,
        second.revision_id,
        expected_current=first.revision_id,
    )
    restricted = CanvasRevisionStore(
        tmp_path / "canvas",
        validator=store.validator,
        authorize=lambda grant, operation: grant.app_revision_id != first.revision_id,
    )
    with pytest.raises(CanvasAuthorizationError):
        restricted.rollback(
            ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, expected_current=second.revision_id
        )
    assert (
        store.pin_active(ACTOR, WORKSPACE, DEPLOYMENT, APP_ID).revision_id
        == second.revision_id
    )


@pytest.mark.parametrize("name", ["C:/escape.json", "C:escape.json"])
def test_stage_rejects_drive_qualified_resource_names(tmp_path, name):
    store, _, _ = make_store(tmp_path / "canvas")
    with pytest.raises(CanvasRevisionError, match="unsafe revision path"):
        store.stage(
            ACTOR, WORKSPACE, DEPLOYMENT, APP_ID, {"app.json": b"{}", name: b"x"}
        )


@pytest.mark.parametrize("workspace", ["C:", "C:escape"])
def test_stage_rejects_drive_qualified_workspace_paths(tmp_path, workspace):
    store, _, _ = make_store(tmp_path / "canvas", allowed_workspace=workspace)
    with pytest.raises(CanvasRevisionError, match="invalid workspace ID"):
        store.stage(ACTOR, workspace, DEPLOYMENT, APP_ID, {"app.json": b"{}"})
