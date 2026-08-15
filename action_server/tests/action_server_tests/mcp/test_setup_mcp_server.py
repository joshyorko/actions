def test_resource_template_matches():
    from actions.server.mcp.setup_mcp_server_from_actions import (
        McpServerSetupHelper,
    )

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
    from actions.server.mcp.setup_mcp_server_from_actions import (
        McpServerSetupHelper,
    )

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
    from actions.server.mcp.setup_mcp_server_from_actions import (
        McpServerSetupHelper,
    )

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
    from actions.server.mcp.setup_mcp_server_from_actions import (
        McpServerSetupHelper,
    )

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
    from actions.server.mcp.setup_mcp_server_from_actions import (
        McpServerSetupHelper,
    )

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
    from actions.server.mcp.setup_mcp_server_from_actions import (
        McpServerSetupHelper,
    )

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
    from actions.server.mcp.setup_mcp_server_from_actions import (
        McpServerSetupHelper,
    )

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
