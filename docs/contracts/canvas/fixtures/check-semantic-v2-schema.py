"""Reproduce the approved v2 schema delta without rewriting v1 or v2."""
import json
from pathlib import Path

import jsonschema

r = Path(__file__).resolve().parents[4]
p = r / "docs/contracts/canvas/canvas-spec-v1.schema.json"
v = json.loads(p.read_text())
v["$id"] = "urn:actions:canvas-spec:2"
v["description"] = "Declarative CanvasSpec v2. Logical binding IDs carry no authority."
v["properties"]["schemaVersion"]["const"] = "actions.canvas-spec/v2"
v[
    "$comment"
] += " Inspector field keys are unique; cards participate in node depth/count and binding traversal."


def obj(kind, props):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["type", "id", *props],
        "properties": {
            "type": {"const": kind},
            "id": {"$ref": "#/$defs/Identifier"},
            **props,
        },
    }


idref = {"$ref": "#/$defs/Identifier"}
title = {"type": "string", "minLength": 1, "maxLength": 256}
for name, kind, props in [
    (
        "CanvasCard",
        "card",
        {
            "title": title,
            "children": {
                "type": "array",
                "maxItems": 128,
                "items": {"$ref": "#/$defs/CanvasNode"},
            },
        },
    ),
    (
        "CanvasChart",
        "chart",
        {
            "title": title,
            "bindingId": idref,
            "rowsKey": idref,
            "chartType": {"enum": ["bar", "line"]},
            "labelKey": idref,
            "valueKey": idref,
        },
    ),
    (
        "CanvasLog",
        "log",
        {"title": title, "bindingId": idref, "rowsKey": idref, "messageKey": idref},
    ),
    (
        "CanvasInspector",
        "inspector",
        {
            "title": title,
            "bindingId": idref,
            "valueKey": idref,
            "fields": {
                "type": "array",
                "minItems": 1,
                "maxItems": 16,
                "items": {"$ref": "#/$defs/CanvasTableColumn"},
            },
        },
    ),
]:
    v["$defs"][name] = obj(kind, props)
    v["$defs"]["CanvasNode"]["oneOf"].append({"$ref": "#/$defs/" + name})
assert (
    json.loads((r / "docs/contracts/canvas/canvas-spec-v2.schema.json").read_text())
    == v
)

jsonschema.Draft202012Validator.check_schema(v)
jsonschema.validate(
    json.loads(
        (r / "docs/contracts/canvas/fixtures/semantic-v2.fixture.json").read_text()
    ),
    v,
)
print("v2 schema derivation and four-node fixture PASS")
