from __future__ import annotations

from pathlib import Path

import pytest

from actions.server.canvas_lifecycle import (
    CanvasAuthorizationError,
    CanvasResourceGrant,
    CanvasRevisionError,
    CanvasRevisionStore,
)


def make_store(root: Path, *, allowed_workspace: str = "workspace-a"):
    validated: list[tuple[str, dict[str, bytes]]] = []

    def validate(app_id, files):
        validated.append((app_id, dict(files)))
        if "app.json" not in files:
            raise CanvasRevisionError("app.json is required")

    store = CanvasRevisionStore(
        root,
        validator=validate,
        authorize_resource=lambda grant: (
            grant.workspace_id == allowed_workspace
            and grant.deployment_revision_id == "sha256:" + "d" * 64
        ),
    )
    return store, validated


def grant(revision_id: str, *, workspace: str = "workspace-a"):
    return CanvasResourceGrant(
        workspace_id=workspace,
        deployment_revision_id="sha256:" + "d" * 64,
        app_id="invoice-review",
        app_revision_id=revision_id,
    )


def test_stage_activate_pin_restart_and_rollback(tmp_path):
    store, validated = make_store(tmp_path / "canvas")
    first = store.stage("invoice-review", {"app.json": b'{"version":1}'})
    assert validated == [
        ("invoice-review", {"app.json": b'{"version":1}'})
    ]
    store.activate("invoice-review", first.revision_id, expected_current=None)
    pinned = store.pin_active("invoice-review")

    second = store.stage(
        "invoice-review", {"app.json": b'{"version":2}', "views/main.json": b"{}"}
    )
    store.activate(
        "invoice-review", second.revision_id, expected_current=first.revision_id
    )
    # An invocation retains the revision resolved before activation.
    assert pinned.revision_id == first.revision_id
    assert pinned.files["app.json"] == b'{"version":1}'

    reopened, _ = make_store(tmp_path / "canvas")
    assert reopened.pin_active("invoice-review").revision_id == second.revision_id
    assert (
        reopened.rollback("invoice-review", expected_current=second.revision_id)
        == first.revision_id
    )
    assert reopened.pin_active("invoice-review").files["app.json"] == b'{"version":1}'


def test_activation_is_compare_and_swap(tmp_path):
    store, _ = make_store(tmp_path / "canvas")
    first = store.stage("invoice-review", {"app.json": b"one"})
    other = store.stage("invoice-review", {"app.json": b"two"})
    store.activate("invoice-review", first.revision_id, expected_current=None)
    with pytest.raises(CanvasRevisionError, match="active revision changed"):
        store.activate("invoice-review", other.revision_id, expected_current=None)
    assert store.pin_active("invoice-review").revision_id == first.revision_id


def test_stage_validates_paths_and_validator_before_persisting(tmp_path):
    store, _ = make_store(tmp_path / "canvas")
    with pytest.raises(CanvasRevisionError, match="unsafe revision path"):
        store.stage("invoice-review", {"../escape": b"x"})
    with pytest.raises(CanvasRevisionError, match="app.json is required"):
        store.stage("invoice-review", {"main.py": b"pass"})
    assert not list((tmp_path / "canvas" / "revisions").rglob("sha256"))


def test_resource_read_requires_server_authorized_exact_revision(tmp_path):
    store, _ = make_store(tmp_path / "canvas")
    revision = store.stage(
        "invoice-review", {"app.json": b"ok", "view.html": b"<p>ok</p>"}
    )
    assert store.read_resource(grant(revision.revision_id), "view.html") == b"<p>ok</p>"
    with pytest.raises(CanvasAuthorizationError):
        store.read_resource(
            grant(revision.revision_id, workspace="workspace-b"), "view.html"
        )
    with pytest.raises(CanvasAuthorizationError):
        store.read_resource(grant(revision.revision_id), "missing.html")
    with pytest.raises(CanvasRevisionError, match="unsafe revision path"):
        store.read_resource(grant(revision.revision_id), "../app.json")


def test_tampered_revision_is_rejected_on_pinned_invocation(tmp_path):
    store, _ = make_store(tmp_path / "canvas")
    revision = store.stage("invoice-review", {"app.json": b"original"})
    store.activate("invoice-review", revision.revision_id, expected_current=None)
    target = (
        tmp_path
        / "canvas"
        / "revisions"
        / "invoice-review"
        / revision.revision_id[7:]
        / "app.json"
    )
    target.chmod(0o600)
    target.write_bytes(b"tampered")
    with pytest.raises(CanvasRevisionError, match="digest verification"):
        store.pin_active("invoice-review")
