"""Explicit v2 admission through existing immutable deployment/SQL authorities."""
import json
from pathlib import Path
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_deployments import _spec as selection_for
from action_server_tests.test_foundry_sql_authoring import (
    _authority,
    _create,
    _fingerprint,
    _grant,
    _spec,
)
from actions.canvas_contract import CanvasSpec, CanvasSpecV2, validate_canvas_spec
from jsonschema import Draft202012Validator, ValidationError

from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.deployments.foundry_values import (
    CanvasCapabilityBinding,
    DeploymentSpecification,
    canvas_revision_digest,
)
from actions.server.foundry.authoring import SCHEMAS
from actions.server.foundry.authoring_values import (
    AuthoringValidationError,
    public_spec_document,
    public_spec_json,
)
from actions.server.foundry.models import FoundryDeploymentRevision
from actions.server.run_outputs.types import Actor, CanvasApplicationRef

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def v2():
    return json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "docs/contracts/canvas/fixtures/semantic-v2.fixture.json"
        ).read_bytes()
    )


def test_v1_bytes_and_digest_are_unchanged():
    raw = _spec("Blank app")
    spec = CanvasSpec.from_json(raw)
    assert public_spec_document(public_spec_json(json.loads(raw))) == json.loads(raw)
    expected = b'{"bindings":[],"packages":[],"spec":{"bindingIds":[],"root":{"children":[],"id":"main","type":"stack"},"schemaVersion":"actions.canvas-spec/v1","title":"Blank app","visibility":["model","app"]}}'
    import hashlib

    assert (
        canvas_revision_digest(spec, (), ())
        == "sha256:"
        + hashlib.sha256(b"actions.canvas-application/v1\x00" + expected).hexdigest()
    )
    assert public_spec_json(json.loads(raw)) == spec.to_json().encode()


@pytest.mark.parametrize(
    "version", ["actions.canvas-spec/v1", "actions.canvas-spec/v2"]
)
def test_mcp_union_schema_resolves_recursive_refs(version):
    spec = v2() if version.endswith("v2") else json.loads(_spec("V1"))
    for name in ["canvas_apply", "canvas_preview"]:
        schema = SCHEMAS[name]
        Draft202012Validator.check_schema(schema)
        args = {"spec": spec}
        if name == "canvas_apply":
            args.update(
                appId=str(uuid4()),
                expectedBase=None,
                bindings=[],
                idempotencyKey="schema",
            )
        Draft202012Validator(schema).validate(args)
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(
                {**args, "spec": {**spec, "schemaVersion": "actions.canvas-spec/v3"}}
            )
    if version.endswith("v2"):
        with pytest.raises(ValidationError):
            Draft202012Validator(SCHEMAS["canvas_preview"]).validate(
                {"spec": {**spec, "schemaVersion": "actions.canvas-spec/v1"}}
            )


@pytest.mark.parametrize(
    "change",
    [
        "unknown-version",
        "card-duplicate",
        "undeclared-binding",
        "unreferenced-binding",
        "extra-field",
    ],
)
def test_public_v2_admission_is_closed(change):
    doc = v2()
    if change == "unknown-version":
        doc["schemaVersion"] = "actions.canvas-spec/v3"
    elif change == "card-duplicate":
        doc["root"]["children"][0]["id"] = doc["root"]["id"]
    elif change == "undeclared-binding":
        doc["root"]["children"][0]["bindingId"] = "missing"
    elif change == "unreferenced-binding":
        doc["bindingIds"].append("unused")
    else:
        doc["root"]["url"] = "https://example.invalid"
    with pytest.raises(AuthoringValidationError):
        public_spec_json(doc)
    with pytest.raises(AuthoringValidationError):
        public_spec_document(json.dumps(doc).encode())


def test_v2_typed_selection_revalidates_bindings_and_digest():
    refs = _refs()
    doc = v2()
    spec = validate_canvas_spec(doc)
    assert isinstance(spec, CanvasSpecV2)
    binding = CanvasCapabilityBinding(binding_id="data", capability=refs.capability)
    app = CanvasApplicationRef(
        workspace_id=str(refs.workspace.root),
        app_id=str(refs.deployment_id.root),
        revision_id=canvas_revision_digest(spec, (binding,), (refs.package,)),
    )
    values = selection_for(refs).model_dump(mode="json", by_alias=True)
    values.update(
        canvas_spec=doc,
        canvas_application=app.model_dump(mode="json"),
        canvas_bindings=[binding.model_dump(mode="json")],
    )
    selected = DeploymentSpecification.model_validate_json(json.dumps(values))
    assert isinstance(selected.canvas_spec, CanvasSpecV2)
    assert selected.canvas_spec.to_json() == spec.to_json()
    assert (
        DeploymentSpecification.model_validate(selected).canvas_spec
        == selected.canvas_spec
    )
    values["canvas_spec"]["root"]["title"] = "Changed"
    with pytest.raises(ValueError, match="differs from immutable source"):
        DeploymentSpecification.model_validate_json(json.dumps(values))


def test_sql_v1_create_explicit_v2_apply_read_replay_rollback_restart(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    doc = v2()
    doc["bindingIds"] = []
    doc["root"]["children"] = [{"type": "text", "id": "child", "text": "Retained card"}]
    raw = public_spec_json(doc)
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        authority = _authority(db, refs)
        first = _create(authority, refs, actor)
        assert (
            public_spec_document(first.spec_json)["schemaVersion"]
            == "actions.canvas-spec/v1"
        )
        args = (
            actor,
            refs.workspace,
            first.application_id,
            first.ref,
            raw,
            (),
            (),
            None,
            None,
            _fingerprint("v2"),
        )
        second = authority.apply(*args, idempotency_key="v2")
        assert public_spec_document(second.spec_json) == doc
        assert authority.apply(*args, idempotency_key="v2").ref == second.ref
        assert (
            public_spec_document(
                authority.get(
                    actor, refs.workspace, first.application_id, first.ref
                ).spec_json
            )["schemaVersion"]
            == "actions.canvas-spec/v1"
        )
        assert (
            authority.get(
                actor, refs.workspace, first.application_id, second.ref
            ).spec_json
            == raw
        )
        released = authority.release(
            actor,
            refs.workspace,
            first.application_id,
            second.ref,
            None,
            _fingerprint("release"),
            idempotency_key="release",
        )
        assert released.active
        authority.rollback(
            actor,
            refs.workspace,
            first.application_id,
            first.ref,
            second.ref,
            _fingerprint("rollback"),
            idempotency_key="rollback",
        )
        assert (
            authority.current(actor, refs.workspace, first.application_id).ref
            == first.ref
        )
        assert len(db.all(FoundryDeploymentRevision)) == 2
    restarted = Database(database_location)
    with restarted.connect():
        restarted.initialize(get_all_model_classes())
        authority = _authority(restarted, refs)
        assert (
            authority.current(actor, refs.workspace, first.application_id).ref
            == first.ref
        )
        assert (
            authority.get(
                actor, refs.workspace, first.application_id, second.ref
            ).spec_json
            == raw
        )
        assert (
            authority.latest(actor, refs.workspace, first.application_id).ref
            == second.ref
        )
