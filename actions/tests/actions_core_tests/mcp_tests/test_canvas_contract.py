from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from actions.canvas_contract import (
    CanvasSpec,
    CanvasSpecValidationError,
    validate_canvas_spec,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_DIR = REPOSITORY_ROOT / "docs/contracts/canvas/semantic-v1"
SCHEMA_PATH = REPOSITORY_ROOT / "docs/contracts/canvas/canvas-spec-v1.schema.json"


def _fixture(name: str) -> bytes:
    return (CONTRACT_DIR / name).read_bytes()


def _to_snake_case_document(value: object) -> object:
    aliases = {
        "schemaVersion": "schema_version",
        "bindingIds": "binding_ids",
        "bindingId": "binding_id",
        "submitLabel": "submit_label",
        "rowsKey": "rows_key",
    }
    if isinstance(value, dict):
        return {
            aliases.get(key, key): _to_snake_case_document(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_to_snake_case_document(child) for child in value]
    return value


def test_semantic_fixture_round_trips_as_immutable_canonical_json():
    raw = _fixture("canvas-spec-v1.fixture.json")
    spec = CanvasSpec.from_json(raw)

    expected = json.dumps(
        json.loads(raw),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert spec.to_json() == expected
    assert CanvasSpec.from_json(spec.to_json()).to_json() == expected
    assert spec.schema_version == "actions.canvas-spec/v1"
    assert spec.visibility == ("model", "app")
    with pytest.raises((TypeError, ValueError)):
        spec.title = "changed"
    with pytest.raises(AttributeError):
        spec.binding_ids.append("another")

    python_document = _to_snake_case_document(json.loads(raw))
    constructed = CanvasSpec.from_python(python_document)
    assert constructed.title == "Search records"


@pytest.mark.parametrize(
    ("validator", "takes_json_text"),
    [(CanvasSpec.from_json, True), (validate_canvas_spec, False)],
)
def test_public_validators_accept_camel_case_and_reject_snake_case_json(
    validator, takes_json_text
):
    document = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    valid_input = json.dumps(document) if takes_json_text else document
    assert validator(valid_input).title == "Search records"
    assert CanvasSpec.model_validate(document).title == "Search records"

    snake_case_document = _to_snake_case_document(document)
    invalid_input = (
        json.dumps(snake_case_document) if takes_json_text else snake_case_document
    )
    with pytest.raises(CanvasSpecValidationError):
        validator(invalid_input)

    with pytest.raises(ValidationError):
        CanvasSpec.model_validate(snake_case_document)


def test_empty_visibility_round_trips_without_defaulting_to_any_audience():
    document = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    document["visibility"] = []

    spec = CanvasSpec.from_json(json.dumps(document))
    validated_spec = validate_canvas_spec(document)

    assert spec.visibility == ()
    assert validated_spec.visibility == ()
    assert json.loads(spec.to_json())["visibility"] == []


def test_checked_in_json_schema_declares_v1_semantics_and_bounds():
    schema = json.loads(SCHEMA_PATH.read_text())

    assert schema["$id"] == "urn:actions:canvas-spec:1"
    assert schema["properties"]["schemaVersion"]["const"] == "actions.canvas-spec/v1"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "schemaVersion",
        "title",
        "visibility",
        "bindingIds",
        "root",
    }
    assert schema["properties"]["bindingIds"]["maxItems"] == 32
    assert schema["properties"]["bindingIds"]["uniqueItems"] is True

    node_schemas = schema["$defs"]["CanvasNode"]["oneOf"]
    node_types = {
        node["properties"]["type"]["const"]
        for node in (
            schema["$defs"][ref["$ref"].rsplit("/", 1)[-1]] for ref in node_schemas
        )
    }
    assert node_types == {"stack", "text", "form", "table", "status", "artifact"}
    form = schema["$defs"]["CanvasForm"]
    assert form["properties"]["fields"]["items"]["$ref"].endswith("/CanvasFormField")
    form_field = schema["$defs"]["CanvasFormField"]
    assert set(form_field["required"]) == {"name", "label", "type", "required"}
    assert form_field["properties"]["type"]["enum"] == [
        "text",
        "integer",
        "boolean",
    ]
    table = schema["$defs"]["CanvasTable"]
    assert {"bindingId", "rowsKey", "columns"} <= set(table["required"])
    assert set(schema["$defs"]["CanvasTableColumn"]["required"]) == {
        "key",
        "label",
    }
    artifact = schema["$defs"]["CanvasArtifact"]
    assert {"bindingId", "label"} <= set(artifact["required"])
    for node_schema in schema["$defs"].values():
        if "properties" in node_schema and "type" in node_schema["properties"]:
            assert node_schema["additionalProperties"] is False
    assert "depth 8" in schema["$comment"]
    assert "128 total nodes" in schema["$comment"]


@pytest.mark.parametrize(
    "fixture_name",
    [
        "canvas-spec-v1.invalid-binding.json",
        "canvas-spec-v1.invalid-unknown-field.json",
        "canvas-spec-v1.invalid-version.json",
    ],
)
def test_invalid_cross_language_fixtures_are_rejected(fixture_name: str):
    with pytest.raises(CanvasSpecValidationError):
        CanvasSpec.from_json(_fixture(fixture_name))


def test_rejects_oversized_and_pathologically_deep_documents():
    with pytest.raises(CanvasSpecValidationError, match="64 KiB"):
        CanvasSpec.from_json(b" " * (64 * 1024 + 1))

    large_tree = {
        "schemaVersion": "actions.canvas-spec/v1",
        "title": "Large",
        "visibility": ["app"],
        "bindingIds": [],
        "root": {
            "type": "stack",
            "id": "main",
            "children": [
                {"type": "text", "id": f"text-{index}", "text": "x" * 4096}
                for index in range(16)
            ],
        },
    }
    with pytest.raises(CanvasSpecValidationError, match="64 KiB"):
        validate_canvas_spec(large_tree)

    deeply_nested = {
        "schemaVersion": "actions.canvas-spec/v1",
        "title": "Too deep",
        "visibility": ["app"],
        "bindingIds": [],
        "root": {"type": "stack", "id": "n0", "children": []},
    }
    node = deeply_nested["root"]
    for index in range(8):
        child = {"type": "stack", "id": f"n{index + 1}", "children": []}
        node["children"].append(child)
        node = child

    with pytest.raises(CanvasSpecValidationError, match="depth"):
        validate_canvas_spec(deeply_nested)


def test_rejects_more_than_128_nodes_or_32_logical_binding_ids():
    too_many_nodes = {
        "schemaVersion": "actions.canvas-spec/v1",
        "title": "Too many nodes",
        "visibility": ["app"],
        "bindingIds": [],
        "root": {
            "type": "stack",
            "id": "main",
            "children": [
                {"type": "text", "id": f"text-{index}", "text": "row"}
                for index in range(128)
            ],
        },
    }
    with pytest.raises(CanvasSpecValidationError, match="128"):
        validate_canvas_spec(too_many_nodes)

    too_many_bindings = {
        "schemaVersion": "actions.canvas-spec/v1",
        "title": "Too many bindings",
        "visibility": ["app"],
        "bindingIds": [f"binding-{index}" for index in range(33)],
        "root": {"type": "text", "id": "intro", "text": "Hello"},
    }
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(too_many_bindings)


def test_rejects_duplicate_node_and_binding_ids():
    spec = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    spec["bindingIds"].append("search")
    with pytest.raises(CanvasSpecValidationError, match="unique"):
        validate_canvas_spec(spec)

    spec = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    spec["root"]["children"].append(
        {"type": "text", "id": "intro", "text": "Duplicate ID"}
    )
    with pytest.raises(CanvasSpecValidationError, match="unique"):
        validate_canvas_spec(spec)


def test_json_parser_rejects_duplicate_keys_and_non_json_numbers():
    with pytest.raises(CanvasSpecValidationError, match="duplicate"):
        CanvasSpec.from_json(
            b'{"schemaVersion":"actions.canvas-spec/v1",'
            b'"schemaVersion":"actions.canvas-spec/v1"}'
        )

    with pytest.raises(CanvasSpecValidationError, match="JSON"):
        CanvasSpec.from_json(
            b'{"schemaVersion":"actions.canvas-spec/v1","title":"bad",'
            b'"bindingIds":[],"root":{"type":"text","id":"x",'
            b'"text":NaN}}'
        )


def test_rejects_unsupported_node_types_and_unreferenced_bindings():
    spec = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    spec["root"]["children"][0]["type"] = "html"
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(spec)

    spec = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    spec["bindingIds"].append("unused")
    with pytest.raises(CanvasSpecValidationError, match="referenced"):
        validate_canvas_spec(spec)


def test_form_table_and_artifact_use_the_public_semantic_shapes():
    spec = CanvasSpec.from_json(_fixture("canvas-spec-v1.fixture.json"))
    form = spec.root.children[1]
    assert form.fields[0].name == "query"
    assert form.fields[0].type == "text"
    assert form.fields[1].type == "integer"

    table = spec.root.children[2]
    assert table.rows_key == "items"
    assert [(column.key, column.label) for column in table.columns] == [
        ("name", "Name"),
        ("status", "Status"),
    ]

    artifact = spec.root.children[4]
    assert artifact.label == "Download CSV"


def test_rejects_unknown_form_table_and_artifact_fields():
    spec = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    form = spec["root"]["children"][1]
    form["fields"][0]["onSubmit"] = "run arbitrary code"
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(spec)

    spec = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    spec["root"]["children"][2]["columns"][0]["url"] = "https://example.test"
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(spec)

    spec = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    spec["root"]["children"][4]["fieldId"] = "secret"
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(spec)


def test_form_names_and_table_columns_must_be_unique():
    spec = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    spec["root"]["children"][1]["fields"][1]["name"] = "query"
    with pytest.raises(CanvasSpecValidationError, match="field names"):
        validate_canvas_spec(spec)

    spec = json.loads(_fixture("canvas-spec-v1.fixture.json"))
    spec["root"]["children"][2]["columns"][1]["key"] = "name"
    with pytest.raises(CanvasSpecValidationError, match="column keys"):
        validate_canvas_spec(spec)
