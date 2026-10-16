import pytest


@pytest.mark.parametrize("selection", ["all", "whitelist", "disabled"])
def test_package_scoped_http_actions_have_distinct_mcp_tools(monkeypatch, selection):
    from fastapi.testclient import TestClient

    from actions.server import _actions_run, _app
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._models import ActionPackage, create_db

    app = _app._CustomFastAPI()
    monkeypatch.setattr(_app, "get_app", lambda: app)

    def generate(action_package, action, display_name, **_kwargs):
        async def http_action():
            return action.id

        async def internal_action(**_kwargs):
            return action.id

        return http_action, internal_action, {}

    monkeypatch.setattr(_actions_run, "generate_func_from_action", generate)
    routes = _ActionRoutes(
        whitelist="package1/do_it" if selection == "whitelist" else None,
        endpoint_dependencies=[],
    )
    with create_db(":memory:") as db:
        with db.transaction():
            for name in ("package1", "package2"):
                package = ActionPackage(name, name, name, "hash", "{}")
                db.insert(package)
                action = _catalog_action(
                    action_id=f"{name}-action",
                    name="do_it",
                    options={"_meta": {"package": name}},
                    docs="Run this action",
                )
                action.action_package_id = name
                action.enabled = selection != "disabled" or name == "package1"
                db.insert(action)
        routes.register_actions()
        routes.setup_mcp_server(None)

        with TestClient(app, base_url="http://localhost:8080") as client:
            packages = ("package1", "package2") if selection == "all" else ("package1",)
            for name in packages:
                response = client.post(f"/api/actions/{name}/do-it/run")
                assert response.status_code == 200
                assert response.json() == f"{name}-action"

            def mcp_request(method, params):
                params = {
                    **params,
                    "_meta": {
                        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                        "io.modelcontextprotocol/clientCapabilities": {},
                    },
                }
                response = client.post(
                    "/mcp",
                    headers={
                        "Accept": "application/json, text/event-stream",
                        "MCP-Protocol-Version": "2026-07-28",
                        "Mcp-Method": method,
                        **({"Mcp-Name": params["name"]} if "name" in params else {}),
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": method,
                        "params": params,
                    },
                )
                assert response.status_code == 200, response.text
                return response.json()["result"]

            tools = mcp_request("tools/list", {})["tools"]
            expected_names = (
                ["package1__do_it", "package2__do_it"]
                if selection == "all"
                else ["do_it"]
            )
            assert [tool["name"] for tool in tools] == expected_names
            for package_name, tool in zip(packages, tools):
                assert tool["_meta"] == {"package": package_name}
                assert tool["annotations"]["title"] == "Do It"
                result = mcp_request("tools/call", {"name": tool["name"]})
                assert result["content"][0]["text"] == f"{package_name}-action"
                assert result["_meta"]["package"] == package_name


def test_collision_names_reserve_bare_names_and_are_order_independent():
    import re
    from types import SimpleNamespace

    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    pairs = []
    for index, (package_name, action_name) in enumerate(
        [
            ("package1", "do_it"),
            ("package2", "do_it"),
            ("other", "package1__do_it"),
            ("a b", "repeat"),
            ("a?b", "repeat"),
            ("x" * 90 + "a", "repeat"),
            ("x" * 90 + "b", "repeat"),
            ("unicode", "工具" * 40),
            ("a__b", "c"),
            ("a", "b__c"),
            ("other-c", "c"),
            ("other-b", "b__c"),
        ]
    ):
        action = _catalog_action(
            action_id=str(index), name=action_name, options={}, docs=""
        )
        pairs.append((SimpleNamespace(name=package_name), action))

    names = McpServerSetupHelper.resolve_tool_names(pairs)
    assert names == McpServerSetupHelper.resolve_tool_names(list(reversed(pairs)))
    assert len(set(names.values())) == len(pairs)
    assert names["2"] == "package1__do_it"
    assert names["0"].startswith("package1__do_it_")
    assert names["1"] == "package2__do_it"
    assert names["7"] == "工具" * 40
    for action_id, name in names.items():
        if action_id not in ("2", "7"):
            assert re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", name)

    revisions = []
    for order in (pairs, pairs[::-1]):
        helper = McpServerSetupHelper()
        for package, action in order:
            helper.register_action(
                lambda **kwargs: "result",
                package,
                action,
                action.name,
                action.docs,
                tool_name=names[action.id],
            )
            assert helper._tool_name_to_action_info[names[action.id]].action is action
        assert [tool.name for tool in helper._tools] == sorted(names.values())
        revisions.append(helper.catalog_revision)
    assert revisions[0] == revisions[1]

    # Forced digest collisions still retain every action deterministically.
    from unittest.mock import patch

    with patch("actions.server.mcp.setup_mcp_server_v2.sha256") as digest:
        digest.return_value.hexdigest.return_value = "0" * 64
        forced_names = McpServerSetupHelper.resolve_tool_names(pairs)
        assert len(set(forced_names.values())) == len(pairs)
        assert forced_names == McpServerSetupHelper.resolve_tool_names(pairs[::-1])


def test_tool_names_exclude_resources_and_prompts_and_reject_duplicate_identity():
    from types import SimpleNamespace

    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    package = SimpleNamespace(name="package")
    pairs = [
        (
            package,
            _catalog_action(
                action_id=kind, name="repeat", options={"kind": kind}, docs=""
            ),
        )
        for kind in ("tool", "resource", "prompt")
    ]
    assert McpServerSetupHelper.resolve_tool_names(pairs) == {"tool": "repeat"}
    with pytest.raises(ValueError, match="duplicate tool identity"):
        McpServerSetupHelper.resolve_tool_names([pairs[0], pairs[0]])


def test_call_tool_uses_admitted_catalog_during_concurrent_reload(monkeypatch):
    import asyncio
    import threading
    from types import SimpleNamespace

    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    def action(name):
        return SimpleNamespace(
            name=name,
            options="{}",
            input_schema="{}",
            output_schema='{"type": "string"}',
        )

    helper = McpServerSetupHelper()
    observed = []
    old_started = threading.Event()
    release_old = threading.Event()

    async def old_action(**_kwargs):
        observed.append("old")
        return "old-result"

    async def new_action(**_kwargs):
        observed.append("new")
        return "new-result"

    helper.register_action(old_action, None, action("tool"), "Tool", "old")
    replacement = McpServerSetupHelper()
    replacement.register_action(new_action, None, action("tool"), "Tool", "new")

    def request_values(_ctx):
        old_started.set()
        release_old.wait(timeout=5)
        return {}, {}

    monkeypatch.setattr(helper, "_request_values", request_values)
    call_result = {}

    def invoke():
        async def call():
            return await helper._call_tool(
                SimpleNamespace(request=None),
                SimpleNamespace(name="tool", arguments={}),
            )

        try:
            call_result["value"] = asyncio.run(call())
        except BaseException as exc:  # pragma: no cover - surfaced below
            call_result["error"] = exc

    thread = threading.Thread(target=invoke)
    thread.start()
    assert old_started.wait(timeout=5)
    helper.replace_catalog(replacement)
    release_old.set()
    thread.join(timeout=5)

    assert "error" not in call_result
    assert call_result["value"].content[0].text == "old-result"
    assert observed == ["old"]


@pytest.mark.parametrize("resource_mime", [None, "text/html"])
def test_invalid_ui_resource_reference_does_not_replace_catalog(resource_mime):
    import json
    from types import SimpleNamespace

    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    def action(name, options="{}"):
        return SimpleNamespace(
            name=name,
            options=options,
            input_schema="{}",
            output_schema='{"type":"string"}',
        )

    async def old_func(**_kwargs):
        return "old"

    async def new_func(**_kwargs):
        return "new"

    helper = McpServerSetupHelper()
    old_catalog = McpServerSetupHelper()
    old_catalog.register_action(old_func, None, action("old_tool"), "Old", "")
    helper.replace_catalog(old_catalog)
    published = helper._catalog

    replacement = McpServerSetupHelper()
    metadata = {
        "kind": "action",
        "_meta": {"ui": {"resourceUri": "ui://fixture/view"}},
    }
    replacement.register_action(
        new_func,
        None,
        action("new_tool", json.dumps(metadata)),
        "New",
        "",
    )
    if resource_mime is not None:
        resource_options = {
            "kind": "resource",
            "uri": "ui://fixture/view",
            "mime_type": resource_mime,
        }
        replacement.register_action(
            new_func,
            None,
            action("view", json.dumps(resource_options)),
            "View",
            "",
        )

    with pytest.raises(ValueError, match="MCP"):
        helper.replace_catalog(replacement)

    assert helper._catalog is published
    assert [tool.name for tool in helper._tools] == ["old_tool"]


@pytest.mark.parametrize(
    ("uri", "mime_type"),
    [
        ("ui://fixture/view", "text/html"),
        ("ui:///view", "text/html;profile=mcp-app"),
    ],
)
def test_unreferenced_ui_resource_requires_valid_uri_and_apps_mime_before_publish(
    uri, mime_type
):
    import json
    from types import SimpleNamespace

    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    action = SimpleNamespace(
        name="view",
        options=json.dumps(
            {
                "kind": "resource",
                "uri": uri,
                "mime_type": mime_type,
            }
        ),
        input_schema="{}",
        output_schema='{"type":"string"}',
    )

    async def resource_func(**_kwargs):
        return "<html />"

    helper = McpServerSetupHelper()
    replacement = McpServerSetupHelper()
    replacement.register_action(resource_func, None, action, "View", "")

    with pytest.raises(ValueError, match="MCP Apps resource"):
        helper.replace_catalog(replacement)

    assert helper._tools == []


def test_resource_template_matches():
    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    setup = McpServerSetupHelper()
    assert setup._resource_template_matches(
        "https://example.com/resource/{id}", "https://example.com/resource/123"
    ) == {"id": "123"}

    assert setup._resource_template_matches(
        "https://example.com/resource/{id}", "https://example.com/resource/123"
    ) == {"id": "123"}

    assert (
        setup._resource_template_matches(
            "https://example.com/resource/{id}", "https://example.com/resource/123/foo"
        )
        is None
    )

    assert setup._resource_template_matches("https://{k}:{v}", "https://key:value") == {
        "k": "key",
        "v": "value",
    }


def test_collect_and_call_resource():
    import json

    from action_server_tests.fixtures import run_async_in_new_thread

    from actions.server._models import Action
    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    action = Action(
        id="123",
        action_package_id="456",
        name="test",
        docs="test",
        file="test.py",
        lineno=1,
        input_schema=json.dumps({}),
        output_schema=json.dumps({}),
        enabled=True,
        is_consequential=None,
        managed_params_schema=None,
        options=json.dumps(
            {
                "kind": "resource",
                "uri": "https://example.com/resource/{a}",
            }
        ),
    )

    setup = McpServerSetupHelper()

    received_inputs = {}

    async def run(*, inputs: dict, **kwargs):
        received_inputs.update(inputs)
        return "run result"

    setup.register_action(
        func=run,
        action_package=None,
        action=action,
        display_name=None,
        doc_desc=None,
    )

    assert len(setup._resource_templates) == 1

    async def call():
        from types import SimpleNamespace

        from mcp.types import ReadResourceRequestParams

        result = await setup._read_resource(
            SimpleNamespace(request=None),
            ReadResourceRequestParams(uri="https://example.com/resource/123"),
        )
        return result

    result = run_async_in_new_thread(call)
    assert received_inputs == {"a": "123"}
    assert "run result" in str(result)
    assert "text/plain" in str(result)


def test_collect_and_call_prompt():
    import json

    from action_server_tests.fixtures import run_async_in_new_thread

    from actions.server._models import Action
    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    action = Action(
        id="123",
        action_package_id="456",
        name="test_prompt",
        docs="test prompt",
        file="test.py",
        lineno=1,
        input_schema=json.dumps({"properties": {"text": {"type": "string"}}}),
        output_schema=json.dumps({}),
        enabled=True,
        is_consequential=None,
        managed_params_schema=None,
        options=json.dumps(
            {
                "kind": "prompt",
            }
        ),
    )

    setup = McpServerSetupHelper()

    received_inputs = {}

    async def run(*, inputs: dict, **kwargs):
        received_inputs.update(inputs)
        return "prompt result"

    setup.register_action(
        func=run,
        action_package=None,
        action=action,
        display_name=None,
        doc_desc=None,
    )

    async def call():
        from types import SimpleNamespace

        from mcp.types import GetPromptRequestParams

        result = await setup._get_prompt(
            SimpleNamespace(request=None),
            GetPromptRequestParams(
                name="test_prompt", arguments={"text": "test input"}
            ),
        )
        return result

    result = run_async_in_new_thread(call)
    assert received_inputs == {"text": "test input"}
    assert "prompt result" in str(result)


def test_preserves_declared_mcp_meta_on_tool_and_result():
    import json

    from action_server_tests.fixtures import run_async_in_new_thread

    from actions.server._models import Action
    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    declared_meta = {"ui": {"resourceUri": "ui://action-canvas/v1/canvas.html"}}
    action = Action(
        id="123",
        action_package_id="456",
        name="canvas_preview",
        docs="preview",
        file="test.py",
        lineno=1,
        input_schema=json.dumps({"type": "object", "properties": {}}),
        output_schema=json.dumps({"type": "string"}),
        enabled=True,
        is_consequential=None,
        managed_params_schema=None,
        options=json.dumps({"kind": "tool", "_meta": declared_meta}),
    )
    setup = McpServerSetupHelper()

    async def run(**kwargs):
        return "preview ready"

    setup.register_action(
        func=run,
        action_package=None,
        action=action,
        display_name="Canvas preview",
        doc_desc="preview",
    )

    assert setup._tools[0].meta == declared_meta

    async def call():
        from types import SimpleNamespace

        from mcp.types import CallToolRequestParams

        return await setup._call_tool(
            SimpleNamespace(request=None),
            CallToolRequestParams(name="canvas_preview", arguments={}),
        )

    result = run_async_in_new_thread(call)
    assert result.meta == declared_meta


def test_preserves_declared_mcp_meta_on_resources_and_prompts():
    import json

    from action_server_tests.fixtures import run_async_in_new_thread

    from actions.server._models import Action
    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    declared_meta = {"ui": {"resourceUri": "ui://action-canvas/v1/canvas.html"}}
    setup = McpServerSetupHelper()

    async def run(**kwargs):
        return "result"

    for name, options in (
        ("resource", {"kind": "resource", "uri": "https://canvas.example/direct"}),
        (
            "template",
            {"kind": "resource", "uri": "https://canvas.example/{id}"},
        ),
        ("prompt", {"kind": "prompt"}),
    ):
        setup.register_action(
            func=run,
            action_package=None,
            action=Action(
                id=name,
                action_package_id="456",
                name=name,
                docs=name,
                file="test.py",
                lineno=1,
                input_schema=json.dumps({"type": "object", "properties": {}}),
                output_schema=json.dumps({"type": "string"}),
                enabled=True,
                is_consequential=None,
                managed_params_schema=None,
                options=json.dumps({**options, "_meta": declared_meta}),
            ),
            display_name=name,
            doc_desc=name,
        )

    assert setup._resources["https://canvas.example/direct"].meta == declared_meta
    assert setup._resource_templates[0].meta == declared_meta
    assert setup._prompts[0].meta == declared_meta

    async def call():
        from types import SimpleNamespace

        from mcp.types import GetPromptRequestParams, ReadResourceRequestParams

        ctx = SimpleNamespace(request=None)
        return (
            await setup._read_resource(
                ctx, ReadResourceRequestParams(uri="https://canvas.example/direct")
            ),
            await setup._read_resource(
                ctx, ReadResourceRequestParams(uri="https://canvas.example/123")
            ),
            await setup._get_prompt(ctx, GetPromptRequestParams(name="prompt")),
        )

    direct_result, template_result, prompt_result = run_async_in_new_thread(call)
    assert direct_result.meta == declared_meta
    assert template_result.meta == declared_meta
    assert prompt_result.meta == declared_meta


def test_catalogs_are_sorted_and_revisioned_independently_of_registration_order():
    import asyncio
    import json

    from actions.server._models import Action
    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    first = McpServerSetupHelper()
    second = McpServerSetupHelper()
    # The helper must derive the catalog from registered MCP definitions, not
    # from the order in which the Action rows happened to be loaded.
    for helper, names in (
        (first, ["zulu", "alpha"]),
        (second, ["alpha", "zulu"]),
    ):
        for name in names:
            action = Action(
                id=name,
                action_package_id="package",
                name=name,
                docs=name,
                file="actions.py",
                lineno=1,
                input_schema=json.dumps({"type": "object", "properties": {}}),
                output_schema=json.dumps({"type": "string"}),
                enabled=True,
                is_consequential=None,
                managed_params_schema=None,
                options=json.dumps({"kind": "tool"}),
            )
            helper.register_action(
                func=lambda **kwargs: "result",
                action=action,
                action_package=None,
                display_name=name,
                doc_desc=name,
            )

    assert [tool.name for tool in first._tools] == ["alpha", "zulu"]
    assert [tool.name for tool in second._tools] == ["alpha", "zulu"]
    assert first.catalog_revision == second.catalog_revision

    result = asyncio.run(first._list_tools(None, None))
    assert result.meta["actions.catalogRevision"] == first.catalog_revision


def test_catalog_revision_changes_when_surface_changes_and_reload_clears_cache():
    import json

    from actions.server._models import Action
    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    helper = McpServerSetupHelper()
    action = Action(
        id="one",
        action_package_id="package",
        name="one",
        docs="one",
        file="actions.py",
        lineno=1,
        input_schema=json.dumps({"type": "object", "properties": {}}),
        output_schema=json.dumps({"type": "string"}),
        enabled=True,
        is_consequential=None,
        managed_params_schema=None,
        options=json.dumps({"kind": "tool"}),
    )
    helper.register_action(
        func=lambda **kwargs: "result",
        action=action,
        action_package=None,
        display_name="one",
        doc_desc="one",
    )
    before = helper.catalog_revision
    helper.unregister_actions()
    assert helper.catalog_revision != before
    assert helper._tools == []


def _catalog_action(
    *,
    action_id: str,
    name: str,
    options: dict,
    docs: str,
    input_schema: dict | None = None,
):
    import json

    from actions.server._models import Action

    return Action(
        id=action_id,
        action_package_id="package",
        name=name,
        docs=docs,
        file="actions.py",
        lineno=1,
        input_schema=json.dumps(input_schema or {"type": "object", "properties": {}}),
        output_schema=json.dumps({"type": "string"}),
        enabled=True,
        is_consequential=None,
        managed_params_schema=None,
        options=json.dumps(options),
    )


def _register_catalog_action(helper, action):
    helper.register_action(
        func=lambda **kwargs: "result",
        action=action,
        action_package=None,
        display_name=action.name,
        doc_desc=action.docs,
    )


@pytest.mark.parametrize(
    ("options", "names", "duplicate_key"),
    [
        ({"kind": "tool"}, ("duplicate", "duplicate"), "tool name"),
        (
            {"kind": "resource", "uri": "catalog://direct"},
            ("first", "second"),
            "resource URI",
        ),
        (
            {"kind": "resource", "uri": "catalog://{item}"},
            ("first", "second"),
            "resource template URI",
        ),
        ({"kind": "prompt"}, ("duplicate", "duplicate"), "prompt name"),
    ],
)
def test_duplicate_catalog_keys_are_rejected_in_opposite_registration_orders(
    options, names, duplicate_key
):
    actions = [
        _catalog_action(
            action_id=f"{name}-{index}",
            name=name,
            options=options,
            docs=f"definition {index}",
        )
        for index, name in enumerate(names)
    ]

    for registration_order in (actions, list(reversed(actions))):
        from actions.server.mcp.setup_mcp_server_from_actions import (
            McpServerSetupHelper,
        )

        helper = McpServerSetupHelper()
        _register_catalog_action(helper, registration_order[0])
        with pytest.raises(ValueError, match=f"duplicate {duplicate_key}"):
            _register_catalog_action(helper, registration_order[1])


def test_catalog_revision_changes_for_schema_and_meta_changes():
    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    def revision_for(input_schema, mcp_meta):
        helper = McpServerSetupHelper()
        _register_catalog_action(
            helper,
            _catalog_action(
                action_id="tool",
                name="tool",
                options={"kind": "tool", "_meta": mcp_meta},
                docs="tool",
                input_schema=input_schema,
            ),
        )
        return helper.catalog_revision

    base_schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
    }
    changed_schema = {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
    }
    base_meta = {"ui": {"resourceUri": "ui://base"}}
    changed_meta = {"ui": {"resourceUri": "ui://changed"}}

    base_revision = revision_for(base_schema, base_meta)
    assert revision_for(changed_schema, base_meta) != base_revision
    assert revision_for(base_schema, changed_meta) != base_revision


def test_large_catalog_revision_is_bounded():
    import time

    from actions.server.mcp.setup_mcp_server_from_actions import McpServerSetupHelper

    helper = McpServerSetupHelper()
    for index in range(1000):
        _register_catalog_action(
            helper,
            _catalog_action(
                action_id=f"tool-{index}",
                name=f"tool_{index:04d}",
                options={"kind": "tool"},
                docs=f"tool {index}",
            ),
        )

    started = time.perf_counter()
    revision = helper.catalog_revision
    elapsed = time.perf_counter() - started

    assert len(revision) == 64
    assert elapsed < 2.0, f"large catalog revision took {elapsed:.3f}s"
