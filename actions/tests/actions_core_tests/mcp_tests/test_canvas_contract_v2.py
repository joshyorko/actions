"""Versioned syntax foundation; renderer result bounds are a separate gate."""
import hashlib
import json
from pathlib import Path

import pytest

from actions.canvas_contract import (
    CanvasSpec,
    CanvasSpecV2,
    CanvasSpecValidationError,
    parse_canvas_spec,
    validate_canvas_spec,
)

ROOT = Path(__file__).resolve().parents[4]


def fixture():
    return json.loads(
        (ROOT / "docs/contracts/canvas/fixtures/semantic-v2.fixture.json").read_bytes()
    )


def test_versioned_roundtrip_and_old_reader_refusal():
    value = fixture()
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    spec = parse_canvas_spec(raw)
    assert type(spec) is CanvasSpecV2
    assert spec.to_json() == raw
    assert CanvasSpecV2.from_json(raw).to_json() == raw
    with pytest.raises(CanvasSpecValidationError):
        CanvasSpec.from_json(raw)
    old = (
        ROOT / "docs/contracts/canvas/semantic-v1/canvas-spec-v1.fixture.json"
    ).read_bytes()
    expected = CanvasSpec.from_json(old).to_json()
    assert type(parse_canvas_spec(old)) is CanvasSpec
    assert parse_canvas_spec(old).to_json() == expected
    assert (
        hashlib.sha256(parse_canvas_spec(old).to_json().encode()).digest()
        == hashlib.sha256(expected.encode()).digest()
    )
    with pytest.raises(CanvasSpecValidationError):
        CanvasSpecV2.from_json(old)


@pytest.mark.parametrize(
    "version", ["actions.canvas-spec/v0", "actions.canvas-spec/v3", None, 1]
)
def test_unknown_versions(version):
    value = fixture()
    value["schemaVersion"] = version
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(value)


@pytest.mark.parametrize(
    "mutation",
    [
        "v1-nodes",
        "unknown-node",
        "extra",
        "duplicate-id",
        "duplicate-field",
        "unknown-binding",
        "unused-binding",
        "title-long",
        "empty-fields",
        "many-fields",
        "path",
        "binding-count",
        "byte-bound",
        "surrogate",
    ],
)
def test_closed_v2_boundaries(mutation):
    value = fixture()
    root = value["root"]
    chart, log, inspector = root["children"]
    if mutation == "v1-nodes":
        value["schemaVersion"] = "actions.canvas-spec/v1"
    elif mutation == "unknown-node":
        chart["type"] = "iframe"
    elif mutation == "extra":
        chart["url"] = "https://example.invalid"
    elif mutation == "duplicate-id":
        log["id"] = chart["id"]
    elif mutation == "duplicate-field":
        inspector["fields"] *= 2
    elif mutation == "unknown-binding":
        chart["bindingId"] = "missing"
    elif mutation == "unused-binding":
        value["bindingIds"].append("unused")
    elif mutation == "title-long":
        root["title"] = "x" * 257
    elif mutation == "empty-fields":
        inspector["fields"] = []
    elif mutation == "many-fields":
        inspector["fields"] = [{"key": f"f{i}", "label": "Field"} for i in range(17)]
    elif mutation == "path":
        chart["valueKey"] = "a.b"
    elif mutation == "binding-count":
        value["bindingIds"] = [f"b{i}" for i in range(33)]
    elif mutation == "byte-bound":
        root["children"] = [
            {"type": "text", "id": f"t{i}", "text": "é" * 4096} for i in range(9)
        ]
        value["bindingIds"] = []
    else:
        root["title"] = "\ud800"
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(value)


def test_exact_node_depth_count_and_field_limits():
    value = fixture()
    value["root"]["title"] = "😀" * 256
    value["root"]["children"][2]["fields"] = [
        {"key": f"f{i}", "label": "x" * 256} for i in range(16)
    ]
    validate_canvas_spec(value)
    value["bindingIds"] = []
    value["root"] = {
        "type": "card",
        "id": "root",
        "title": "Root",
        "children": [{"type": "text", "id": f"t{i}", "text": "x"} for i in range(127)],
    }
    validate_canvas_spec(value)
    value["root"]["children"].append({"type": "text", "id": "overflow", "text": "x"})
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(value)
    value["root"] = {"type": "text", "id": "leaf", "text": "x"}
    for i in range(7):
        value["root"] = {
            "type": "card",
            "id": f"c{i}",
            "title": "Card",
            "children": [value["root"]],
        }
    validate_canvas_spec(value)
    value["root"] = {"type": "stack", "id": "too_deep", "children": [value["root"]]}
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(value)


def test_v2_schema_fixture_and_duplicate_json():
    schema = json.loads(
        (ROOT / "docs/contracts/canvas/canvas-spec-v2.schema.json").read_bytes()
    )
    assert schema["properties"]["schemaVersion"]["const"] == fixture()["schemaVersion"]
    with pytest.raises(CanvasSpecValidationError):
        parse_canvas_spec(
            '{"schemaVersion":"actions.canvas-spec/v2","schemaVersion":"actions.canvas-spec/v1"}'
        )


def test_canonical_size_exactly_65536_then_one_more_byte():
    value = fixture()
    value["bindingIds"] = []
    value["root"] = {
        "type": "card",
        "id": "root",
        "title": "Card",
        "children": [
            {"type": "text", "id": f"t{i}", "text": "x" * 4096} for i in range(15)
        ]
        + [{"type": "text", "id": "tail", "text": "x"}],
    }

    def size():
        return len(
            json.dumps(
                value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode()
        )

    value["root"]["children"][-1]["text"] = "x" * (65536 - size() + 1)
    assert size() == 65536
    assert len(validate_canvas_spec(value).to_json().encode()) == 65536
    value["root"]["children"][-1]["text"] += "x"
    with pytest.raises(CanvasSpecValidationError):
        validate_canvas_spec(value)
