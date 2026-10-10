from __future__ import annotations

import pytest


def _capture_options(monkeypatch):
    from actions import _hooks

    found = []
    monkeypatch.setattr(
        _hooks, "on_action_func_found", lambda func, options: found.append(options)
    )
    return found


def test_tool_and_ui_resource_copy_public_metadata_as_json(monkeypatch):
    from actions import mcp

    found = _capture_options(monkeypatch)
    tool_meta = {
        "ui": {
            "resourceUri": "ui://fixture/view",
            "visibility": ["model", "app"],
        },
        "com.example.extension": {"enabled": True},
    }
    resource_meta = {
        "ui": {
            "csp": {
                "connectDomains": ["https://api.example.test"],
                "resourceDomains": ["https://static.example.test"],
            }
        }
    }

    def action():
        return "ok"

    mcp.tool(meta=tool_meta)(action)
    mcp.resource(
        "ui://fixture/view",
        mime_type="text/html;profile=mcp-app",
        meta=resource_meta,
    )(action)

    tool_meta["ui"]["visibility"].clear()
    tool_meta["com.example.extension"]["enabled"] = False
    resource_meta["ui"]["csp"]["connectDomains"].append("https://mutated.test")

    assert found[0]["_meta"] == {
        "ui": {
            "resourceUri": "ui://fixture/view",
            "visibility": ["model", "app"],
        },
        "com.example.extension": {"enabled": True},
    }
    assert found[1]["_meta"] == {
        "ui": {
            "csp": {
                "connectDomains": ["https://api.example.test"],
                "resourceDomains": ["https://static.example.test"],
            }
        }
    }


@pytest.mark.parametrize(
    "meta",
    [
        [],
        {1: "non-string key"},
        {"value": object()},
        {"value": float("nan")},
        {"value": "\ud800"},
        {"value": "💩" * 17000},
        {"ui": {"resourceUri": "https://example.test/view"}},
        {"ui": {"resourceUri": "ui:///view"}},
        {
            "ui": {
                "resourceUri": "ui://fixture/view",
                "visibility": ["app", "unknown"],
            }
        },
        {
            "ui": {
                "resourceUri": "ui://fixture/view",
                "visibility": ["app", "app"],
            }
        },
        {"ui": {"csp": {"unknownDomains": ["https://example.test"]}}},
        {"ui": {"csp": {"connectDomains": [1]}}},
    ],
)
def test_tool_rejects_invalid_public_mcp_metadata(meta):
    from actions import mcp

    def action():
        return "ok"

    with pytest.raises(ValueError):
        mcp.tool(meta=meta)(action)


def test_tool_rejects_cycles_and_bounded_metadata_overflow():
    from actions import mcp

    cyclic = {}
    cyclic["cycle"] = cyclic
    deep = value = {}
    for _ in range(18):
        value["next"] = {}
        value = value["next"]
    too_large = {"value": "x" * (64 * 1024)}

    def action():
        return "ok"

    for meta in (cyclic, deep, too_large):
        with pytest.raises(ValueError):
            mcp.tool(meta=meta)(action)


def test_ui_resource_uri_allows_query_and_fragment_identity():
    from actions import mcp

    uri = "UI://fixture/view?revision=4#main"

    def action():
        return "ok"

    mcp.tool(meta={"ui": {"resourceUri": uri}})(action)
    mcp.resource(uri, mime_type="text/html;profile=mcp-app")(action)


def test_mcp_metadata_accepts_bounded_unicode_strings():
    from actions import mcp

    def action():
        return "ok"

    mcp.tool(meta={"value": "💩" * 1000})(action)


@pytest.mark.parametrize("value", [1.25, float("inf")])
def test_tool_rejects_float_subclasses_as_non_json_scalars(value):
    from actions.mcp._metadata import normalize_mcp_meta

    class FloatSubclass(float):
        pass

    with pytest.raises(ValueError):
        normalize_mcp_meta({"value": FloatSubclass(value)}, subject="tool")


@pytest.mark.parametrize(
    ("uri", "mime_type", "meta"),
    [
        ("ui://fixture/view", "text/html", None),
        ("ui:///view", "text/html;profile=mcp-app", None),
        (
            "https://fixture.example/view",
            "text/html;profile=mcp-app",
            {"ui": {"csp": {"connectDomains": ["https://api.example.test"]}}},
        ),
    ],
)
def test_resource_rejects_invalid_ui_resource_declarations(uri, mime_type, meta):
    from actions import mcp

    def resource_fn():
        return "<html></html>"

    with pytest.raises(ValueError):
        mcp.resource(uri, mime_type=mime_type, meta=meta)(resource_fn)
