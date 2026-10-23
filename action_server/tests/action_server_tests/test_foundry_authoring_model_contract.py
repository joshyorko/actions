"""Model-facing Canvas contract over the real Runtime SQL authoring adapter."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import (
    _ExecutionPort,
    _PackagePort,
    _refs,
    _runtime_database,
)
from action_server_tests.test_foundry_sql_authoring import _grant
from actions.canvas_contract import CanvasSpec
from jsonschema import Draft202012Validator, ValidationError

from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.foundry.authoring import FoundryAuthoring
from actions.server.foundry.mcp import MODEL_TOOLS, CanvasCaller, CanvasMcp
from actions.server.foundry.sql_authoring import SqlAuthoringAuthority
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


class _BackendUnavailable:
    def __getattr__(self, name):
        raise AssertionError(f"UI-only authoring unexpectedly used {name}")


def test_model_tool_schema_resolves_nested_canvas_references():
    from actions.server.foundry.authoring import SCHEMAS

    spec = {
        "schemaVersion": "actions.canvas-spec/v1",
        "title": "Owned nested spec",
        "visibility": ["app"],
        "bindingIds": [],
        "root": {
            "type": "stack",
            "id": "main",
            "children": [{"type": "text", "id": "hello", "text": "World"}],
        },
    }
    for name in ("canvas_apply", "canvas_preview"):
        validator = Draft202012Validator(SCHEMAS[name])
        arguments = {"spec": spec}
        if name == "canvas_apply":
            arguments.update(
                appId=str(uuid4()),
                expectedBase=None,
                bindings=[],
                idempotencyKey="schema",
            )
        validator.validate(arguments)
        with pytest.raises(ValidationError):
            validator.validate(dict(arguments, spec=dict(spec, root={"type": "shell"})))


def _canvas(db, refs):
    repository = FoundryRepository(db)
    authorization = SqlFoundryAuthorization(db)
    deployments = FoundryDeploymentService(
        repository, _PackagePort(refs), authorization, _ExecutionPort()
    )
    authority = SqlAuthoringAuthority(repository, deployments, authorization)
    unavailable = _BackendUnavailable()
    port = FoundryAuthoring(
        authority,
        authorization,
        unavailable,
        unavailable,
        unavailable,
    )

    async def authenticate(context):
        return context if isinstance(context, CanvasCaller) else None

    return CanvasMcp(port, authenticate, "<html>model contract</html>")


def test_real_adapter_exposes_typed_spec_and_round_trips_authored_structure(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    model = CanvasCaller(actor, str(refs.workspace.root), "model")
    app = CanvasCaller(actor, str(refs.workspace.root), "app")

    async def exercise(canvas):
        tools = {tool.name: tool for tool in await canvas.tools(model)}
        assert set(tools) == MODEL_TOOLS
        apply_schema = tools["canvas_apply"].input_schema
        spec_schema = apply_schema["properties"]["spec"]
        canonical = CanvasSpec.model_json_schema(
            by_alias=True,
            mode="validation",
            ref_template="#/properties/spec/$defs/{model}",
        )
        canonical["description"] = spec_schema["description"]
        assert spec_schema == canonical
        assert "complete new CanvasSpec revision" in apply_schema["description"]
        assert tools["canvas_apply"].description == apply_schema["description"]
        assert (
            "private binding targets" in tools["canvas_get"].input_schema["description"]
        )

        created = await canvas.call(
            model, "canvas_create", {"idempotencyKey": "model-create"}
        )
        assert not created.is_error
        created_model = created.structured_content
        assert created_model is not None
        assert set(created_model["spec"]) == {
            "schemaVersion",
            "title",
            "visibility",
            "bindingIds",
            "root",
        }
        assert created_model["spec"]["title"] == "New Canvas"
        CanvasSpec.from_json(json.dumps(created_model["spec"]))
        assert "bindings" not in created_model
        assert "backend" not in created_model
        assert "source" not in created_model

        app_id = created_model["applicationId"]
        base = created_model["revisionId"]
        spec = dict(created_model["spec"])
        spec["title"] = "Model-authored records"
        spec["root"] = {
            "type": "stack",
            "id": "main",
            "children": [
                {"type": "text", "id": "heading", "text": "Recent records"},
                {"type": "text", "id": "help", "text": "Choose a record to continue."},
            ],
        }
        applied = await canvas.call(
            model,
            "canvas_apply",
            {
                "appId": app_id,
                "expectedBase": base,
                "spec": spec,
                "bindings": [],
                "idempotencyKey": "model-apply",
            },
        )
        assert not applied.is_error
        applied_model = applied.structured_content
        assert applied_model is not None
        assert applied_model["spec"]["title"] == "Model-authored records"
        assert applied_model["spec"]["root"] == spec["root"]
        assert "bindings" not in applied_model

        reopened = await canvas.call(model, "canvas_get", {"appId": app_id})
        assert not reopened.is_error
        assert reopened.structured_content["spec"] == applied_model["spec"]

        inspected = await canvas.call(model, "canvas_inspect", {"appId": app_id})
        assert not inspected.is_error
        revisions = inspected.structured_content["revisions"]
        assert [revision["spec"]["title"] for revision in revisions] == [
            "New Canvas",
            "Model-authored records",
        ]
        assert all("bindings" not in revision for revision in revisions)

        denied_mutation = await canvas.call(
            app,
            "canvas_apply",
            {
                "appId": app_id,
                "expectedBase": applied_model["revisionId"],
                "spec": spec,
                "bindings": [],
                "idempotencyKey": "app-must-not-author",
            },
        )
        assert denied_mutation.is_error
        denied_tool = await canvas.call(app, "canvas_dispatch", {})
        assert denied_tool.is_error

    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        asyncio.run(exercise(_canvas(db, refs)))


def test_real_adapter_hides_other_workspace_authored_spec(database_location):
    refs = _refs()
    other_workspace = type(refs.workspace).model_validate(str(uuid4()))
    actor = Actor(principal_id=str(uuid4()))
    authorized = CanvasCaller(actor, str(refs.workspace.root), "model")
    cross_workspace = CanvasCaller(actor, str(other_workspace.root), "model")

    async def exercise(canvas):
        created = await canvas.call(
            authorized, "canvas_create", {"idempotencyKey": "private-create"}
        )
        assert not created.is_error
        app_id = created.structured_content["applicationId"]

        denied = await canvas.call(cross_workspace, "canvas_get", {"appId": app_id})
        assert denied.is_error
        assert denied.structured_content is None
        assert "New Canvas" not in str(denied.content)

    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        asyncio.run(exercise(_canvas(db, refs)))
