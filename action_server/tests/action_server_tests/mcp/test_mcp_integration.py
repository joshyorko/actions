from typing import Literal

import pytest
from action_server_tests.fixtures import run_async_in_new_thread
from mcp import ClientSession

from actions.server._selftest import ActionServerProcess


async def check_mcp_server(
    port: int,
    headers: dict[str, str] | None = None,
    use_actions_mcp: bool = True,
):
    """
    This method is meant to check that the `resources/no_conda/mcp` implementation
    is working.
    """
    from mcp.client.streamable_http import streamable_http_client
    from mcp.types import (
        CallToolResult,
        GetPromptResult,
        Prompt,
        ReadResourceResult,
        TextContent,
        TextResourceContents,
    )
    from pydantic.networks import AnyUrl

    import httpx2

    async with httpx2.AsyncClient(headers=headers or {}) as http_client:
        async with (
            streamable_http_client(
                f"http://localhost:{port}/mcp", http_client=http_client
            ) as connection_info,
            ClientSession(connection_info[0], connection_info[1]) as session,
        ):
            await session.discover()
            tools_list = await session.list_tools()
            tools = tools_list.tools

            assert len(tools) > 0

            tool_names = [tool.name for tool in tools]
            assert "greet_mcp" in tool_names, (
                f"greet_mcp tool not found. Available tools: {tool_names}"
            )

            greet_tool = next(tool for tool in tools if tool.name == "greet_mcp")
            assert greet_tool is not None, (
                f"'greet_mcp' tool not found. Available tools: {tool_names}"
            )

            input_schema = greet_tool.input_schema
            expected_action_server = {
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the person to greet.",
                        "title": "Name",
                    },
                    "title": {
                        "type": "string",
                        "description": "The title for the persor (Mr., Mrs., ...).",
                        "title": "Title",
                        "default": "Mr.",
                    },
                },
                "type": "object",
                "required": ["name"],
            }

            expected_mcp = {
                "properties": {
                    "name": {"title": "Name", "type": "string"},
                    "title": {"default": "Mr.", "title": "title", "type": "string"},
                },
                "required": ["name"],
                "title": "greet_mcpArguments",
                "type": "object",
            }

            assert input_schema in (expected_action_server, expected_mcp), (
                "Found: %s\nExpected: %s or %s",
                input_schema,
                expected_action_server,
                expected_mcp,
            )

            # -- Test tool call.

            tool_result = await session.call_tool(
                greet_tool.name, {"name": "John", "title": "Mr."}
            )

            assert isinstance(tool_result, CallToolResult)
            tool_content = tool_result.content[0]
            assert isinstance(tool_content, TextContent)
            assert tool_content.text == "Hello Mr. John.", (
                f"Expected: Hello Mr. John., got: {tool_content.text}"
            )

            # -- Test prompts.

            prompts_list = await session.list_prompts()
            prompts = prompts_list.prompts
            found = {prompt.name for prompt in prompts}
            assert found == {
                "my_prompt",
                "my_prompt_with_optional_arg",
            }, f"Found: {found}. Expected: {'my_prompt', 'my_prompt_with_optional_arg'}"

            # Check the schema of the prompt with optional argument.
            prompt_with_optional_arg: Prompt = next(
                prompt
                for prompt in prompts
                if prompt.name == "my_prompt_with_optional_arg"
            )
            as_dict = prompt_with_optional_arg.model_dump(exclude_none=True)
            assert as_dict["name"] == "my_prompt_with_optional_arg"
            expected_arguments = [
                {
                    "name": "name",
                    "description": (
                        "The name of the person to greet." if use_actions_mcp else None
                    ),
                    "required": False,
                }
            ]
            assert as_dict["arguments"] == expected_arguments, (
                f"Found: {as_dict['arguments']}. Expected: {expected_arguments}"
            )

            # Check the schema of the prompt without optional argument.
            prompt_without_optional_arg: Prompt = next(
                prompt for prompt in prompts if prompt.name == "my_prompt"
            )
            as_dict = prompt_without_optional_arg.model_dump(exclude_none=True)
            assert as_dict["name"] == "my_prompt"
            expected_arguments = [
                {
                    "name": "name",
                    "description": (
                        "The name of the person to greet." if use_actions_mcp else None
                    ),
                    "required": True,
                }
            ]
            assert as_dict["arguments"] == expected_arguments, (
                f"Found: {as_dict['arguments']}. Expected: {expected_arguments}"
            )

            # Get the prompt.
            prompt_result = await session.get_prompt(
                "my_prompt_with_optional_arg", {"name": "John"}
            )
            assert isinstance(prompt_result, GetPromptResult)

            # The format differs between sema4ai MCP and standard MCP
            if use_actions_mcp:
                # sema4ai MCP now includes the prompt's description from docstring (first line)
                expected_prompt_result = {
                    "meta": None,
                    "description": "Prompt with an optional argument.",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": "This is the built in prompt for John.",
                                "annotations": None,
                                "meta": None,
                            },
                        }
                    ],
                }
            else:
                # Standard MCP now includes the prompt's description from docstring
                expected_prompt_result = {
                    "meta": None,
                    "description": "\n        Prompt with an optional argument.\n\n        Args:\n            name: The name of the person to greet.\n        ",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": "This is the built in prompt for John.",
                                "annotations": None,
                                "meta": None,
                            },
                        }
                    ],
                }

            found_prompt_result = prompt_result.model_dump()
            assert (
                found_prompt_result["description"]
                == expected_prompt_result["description"]
            )
            assert found_prompt_result["messages"] == expected_prompt_result["messages"]
            assert found_prompt_result["result_type"] == "complete"
            assert (
                found_prompt_result["meta"]["io.modelcontextprotocol/serverInfo"][
                    "name"
                ]
                == "Action Server"
            )

            # -- Test resources (simple).

            resources_list = await session.list_resources()
            resources = resources_list.resources
            uris = [str(resource.uri) for resource in resources]
            assert ["custom://my/resource/simple"] == uris

            # Read (simple) resource.
            resource = await session.read_resource(resources[0].uri)
            assert isinstance(resource, ReadResourceResult)
            resource_content = resource.contents[0]
            assert isinstance(resource_content, TextResourceContents)
            assert (
                resource_content.text == "This is a simple resource without a template."
            )

            # -- Test resources (template).

            resource_templates_list = await session.list_resource_templates()
            resource_templates = resource_templates_list.resource_templates
            uris = [
                str(resource_template.uri_template)
                for resource_template in resource_templates
            ]
            assert ["custom://my/resource/{name}"] == uris

            # Read (template) resource.
            uri_template: str = resource_templates[0].uri_template
            uri: AnyUrl = AnyUrl(uri_template.replace("{name}", "John"))
            resource = await session.read_resource(str(uri))
            assert isinstance(resource, ReadResourceResult)
            resource_content = resource.contents[0]
            assert isinstance(resource_content, TextResourceContents)
            assert resource_content.text == "This is the built in resource for John."

            return "ok"


async def check_mcp_server_with_actions(
    port: int,
    headers: dict[str, str] | None = None,
):
    """
    This method is meant to check that the `resources/no_conda/greeter` actions
    work as mcp tools.
    """

    from mcp.client.streamable_http import streamable_http_client
    from mcp.types import CallToolResult, TextContent

    import httpx2

    async with httpx2.AsyncClient(headers=headers or {}) as http_client:
        async with (
            streamable_http_client(
                f"http://localhost:{port}/mcp", http_client=http_client
            ) as connection_info,
            ClientSession(connection_info[0], connection_info[1]) as session,
        ):
            await session.discover()
            tools_list = await session.list_tools()
            tools = tools_list.tools

            assert len(tools) > 0

            tool_names = [tool.name for tool in tools]
            assert "greet" in tool_names, (
                f"greet tool not found. Available tools: {tool_names}"
            )

            greet_tool = next(tool for tool in tools if tool.name == "greet")
            assert greet_tool is not None, (
                f"'greet' tool not found. Available tools: {tool_names}"
            )

            input_schema = greet_tool.input_schema
            expected_action_server = {
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the person to greet.",
                        "title": "Name",
                    },
                    "title": {
                        "type": "string",
                        "description": "The title for the persor (Mr., Mrs., ...).",
                        "title": "Title",
                        "default": "Mr.",
                    },
                },
                "type": "object",
                "required": ["name"],
            }

            expected_mcp = {
                "properties": {
                    "name": {"title": "Name", "type": "string"},
                    "title": {"default": "Mr.", "title": "title", "type": "string"},
                },
                "required": ["name"],
                "title": "greetArguments",
                "type": "object",
            }

            assert input_schema in (expected_action_server, expected_mcp), (
                "Found: %s\nExpected: %s or %s",
                input_schema,
                expected_action_server,
                expected_mcp,
            )

            # -- Test tool call.

            tool_result = await session.call_tool(
                greet_tool.name, {"name": "John", "title": "Mr."}
            )

            assert isinstance(tool_result, CallToolResult)
            tool_content = tool_result.content[0]
            assert isinstance(tool_content, TextContent)
            assert tool_content.text == "Hello Mr. John.", (
                f"Expected: Hello Mr. John., got: {tool_content.text}"
            )

            return "ok"


@pytest.mark.integration_test
def test_modern_mcp_lists_tools_without_initialization(
    action_server_process: ActionServerProcess,
) -> None:
    """The v2 request envelope lists tools directly on the stateless /mcp route."""
    from action_server_tests.fixtures import get_in_resources

    root_dir = get_in_resources("no_conda", "greeter")
    action_server_process.start(
        db_file="server.db",
        cwd=str(root_dir),
        actions_sync=True,
        timeout=60 * 10,
    )

    async def request_tools() -> None:
        import httpx

        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientCapabilities": {},
                }
            },
        }
        async with httpx.AsyncClient() as client:
            sse_response = await client.get(
                f"http://localhost:{action_server_process.port}/sse"
            )
            assert sse_response.status_code == 404, sse_response.text

            initialize_response = await client.post(
                f"http://localhost:{action_server_process.port}/mcp",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Mcp-Protocol-Version": "2026-07-28",
                    "Mcp-Method": "initialize",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2026-07-28",
                        "capabilities": {},
                        "clientInfo": {"name": "legacy-test", "version": "1.0"},
                    },
                },
            )
            initialize_payload = initialize_response.json()
            assert (
                initialize_response.status_code != 200 or "error" in initialize_payload
            )
            assert "result" not in initialize_payload

            response = await client.post(
                f"http://localhost:{action_server_process.port}/mcp",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Mcp-Protocol-Version": "2026-07-28",
                    "Mcp-Method": "tools/list",
                },
                json=body,
            )

        assert response.status_code == 200, response.text
        assert "Mcp-Session-Id" not in response.headers
        payload = response.json()
        assert payload["result"]["tools"]
        assert any(tool["name"] == "greet" for tool in payload["result"]["tools"])

    run_async_in_new_thread(request_tools)


@pytest.mark.integration_test
def test_mcp_integration_with_actions_in_no_conda_greeter(
    action_server_process: ActionServerProcess,
) -> None:
    """
    Tests that run the mcp server based on `actions.mcp` bundled in the
    action server.
    """
    from functools import partial

    from action_server_tests.fixtures import get_in_resources

    root_dir = get_in_resources("no_conda", "greeter")

    action_server_process.start(
        db_file="server.db",
        cwd=str(root_dir),
        actions_sync=True,
        timeout=60 * 10,
    )
    assert (
        run_async_in_new_thread(
            partial(
                check_mcp_server_with_actions,
                action_server_process.port,
            )
        )
        == "ok"
    )


@pytest.mark.integration_test
def test_mcp_integration_with_actions_in_no_conda_mcp(
    action_server_process: ActionServerProcess,
) -> None:
    from functools import partial

    from action_server_tests.fixtures import get_in_resources

    root_dir = get_in_resources("no_conda", "mcp")

    action_server_process.start(
        db_file="server.db",
        cwd=str(root_dir),
        actions_sync=True,
        timeout=60 * 10,
        additional_args=["--api-key=Foo"],
    )
    assert (
        run_async_in_new_thread(
            partial(
                check_mcp_server,
                action_server_process.port,
                headers={"Authorization": "Bearer Foo"},
            )
        )
        == "ok"
    )

    with pytest.raises(
        Exception
    ):  # If we don't pass the headers we should get an exception
        run_async_in_new_thread(
            partial(
                check_mcp_server,
                action_server_process.port,
            )
        )

    with pytest.raises(
        Exception
    ):  # If we pass the wrong headers we should get an exception
        run_async_in_new_thread(
            partial(
                check_mcp_server,
                action_server_process.port,
                headers={"Authorization": "Bearer Bar"},
            )
        )


@pytest.mark.integration_test
def test_mcp_integration_with_structured_output(
    action_server_process: ActionServerProcess, data_regression
) -> None:
    from functools import partial

    from action_server_tests.fixtures import get_in_resources

    root_dir = get_in_resources("no_conda", "mcp")

    action_server_process.start(
        db_file="server.db",
        cwd=str(root_dir),
        actions_sync=True,
        timeout=60 * 10,
    )

    async def check_with_structured_output():
        import httpx2
        from mcp.client.streamable_http import streamable_http_client
        from mcp.types import CallToolResult

        async with httpx2.AsyncClient() as http_client:
            async with streamable_http_client(
                f"http://localhost:{action_server_process.port}/mcp",
                http_client=http_client,
            ) as connection_info:
                read_stream, write_stream = connection_info[:2]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.discover()
                    tools_list = await session.list_tools()
                    tools = tools_list.tools

                    # Find the structured data tool
                    tool_names = [tool.name for tool in tools]
                    assert "get_structured_data" in tool_names, (
                        f"get_structured_data tool not found. Available tools: {tool_names}"
                    )

                    structured_tool = next(
                        tool for tool in tools if tool.name == "get_structured_data"
                    )
                    assert structured_tool is not None

                    # Call the tool with structured output
                    tool_result = await session.call_tool(structured_tool.name, {})

                    assert isinstance(tool_result, CallToolResult)
                    assert not tool_result.content

                    structured_output = tool_result.structured_content
                    data_regression.check(structured_output)

        return "ok"

    assert run_async_in_new_thread(partial(check_with_structured_output)) == "ok"


@pytest.mark.integration_test
@pytest.mark.parametrize("scenario", ["env_var", "request_header"])
def test_mcp_integration_secrets(
    action_server_process: ActionServerProcess,
    scenario: Literal["env_var", "request_header"],
) -> None:
    from functools import partial

    from action_server_tests.fixtures import get_in_resources

    root_dir = get_in_resources("no_conda", "mcp")

    action_server_process.start(
        db_file="server.db",
        cwd=str(root_dir),
        actions_sync=True,
        timeout=60 * 10,
        env={
            "MY_SECRET": "FooSecret",
        }
        if scenario == "env_var"
        else None,
    )

    async def check_with_secrets():
        import httpx2
        from mcp.client.streamable_http import streamable_http_client

        port = action_server_process.port
        headers = {"x-my-secret": "FooSecret"} if scenario == "request_header" else None
        async with httpx2.AsyncClient(headers=headers) as http_client:
            async with streamable_http_client(
                f"http://localhost:{port}/mcp", http_client=http_client
            ) as (
                read_stream,
                write_stream,
                *_,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.discover()
                    tools_list = await session.list_tools()
                    tool_names = [tool.name for tool in tools_list.tools]
                    assert "check_secrets" in tool_names, (
                        f"'check_secrets' tool not found. Available tools: {tool_names}"
                    )
                    result = await session.call_tool("check_secrets", {})
                    assert result.content[0].text == "FooSecret", (
                        f"Expected 'FooSecret', got: {result.content[0].text}"
                    )
        return "ok"

    assert run_async_in_new_thread(partial(check_with_secrets)) == "ok"


_MODERN_PROTOCOL_VERSION = "2026-07-28"


def _modern_request(
    method: str, request_id: int, params: dict | None = None
) -> tuple[dict, dict]:
    use_params = dict(params or {})
    use_params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": _MODERN_PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Mcp-Protocol-Version": _MODERN_PROTOCOL_VERSION,
        "Mcp-Method": method,
    }
    if method == "tools/call":
        headers["Mcp-Name"] = use_params["name"]
    return headers, {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": use_params,
    }


async def _post_modern_mcp(
    url: str, method: str, request_id: int, params: dict | None = None
):
    import httpx

    headers, body = _modern_request(method, request_id, params)
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert "Mcp-Session-Id" not in response.headers
    payload = response.json()
    assert "error" not in payload, payload
    return payload["result"]


@pytest.mark.integration_test
def test_modern_mcp_requests_can_move_between_independent_replicas(tmpdir) -> None:
    """A 2026-07-28 request can move between independent stateless replicas."""
    from pathlib import Path

    from action_server_tests.fixtures import get_in_resources, run_async_in_new_thread
    from actions.server._selftest import ActionServerProcess

    root_dir = get_in_resources("no_conda", "greeter")
    first = ActionServerProcess(Path(tmpdir) / "first-runtime")
    second = ActionServerProcess(Path(tmpdir) / "second-runtime")
    try:
        first.start(
            db_file="server.db", cwd=root_dir, actions_sync=True, timeout=60 * 10
        )
        second.start(
            db_file="server.db", cwd=root_dir, actions_sync=True, timeout=60 * 10
        )

        async def call_each_replica() -> list[str]:
            results = []
            for port, name in ((first.port, "First"), (second.port, "Second")):
                result = await _post_modern_mcp(
                    f"http://localhost:{port}/mcp",
                    "tools/call",
                    request_id=1,
                    params={"name": "greet", "arguments": {"name": name}},
                )
                results.append(result["content"][0]["text"])
            return results

        assert run_async_in_new_thread(call_each_replica) == [
            "Hello Mr. First.",
            "Hello Mr. Second.",
        ]
    finally:
        second.stop()
        first.stop()


@pytest.mark.integration_test
def test_mcp_v2_routes_accept_discover_and_subscription_methods(
    action_server_process: ActionServerProcess,
) -> None:
    """The live MCP v2 SDK routes are not blocked by gateway method inspection."""
    from action_server_tests.fixtures import get_in_resources, run_async_in_new_thread

    root_dir = get_in_resources("no_conda", "greeter")
    action_server_process.start(
        db_file="server.db", cwd=root_dir, actions_sync=True, timeout=60 * 10
    )

    async def check_routes() -> None:
        import httpx2

        requests = (
            ("server/discover", 1, None),
            (
                "subscriptions/listen",
                2,
                {"notifications": {"toolsListChanged": True}},
            ),
        )
        async with httpx2.AsyncClient() as client:
            for method, request_id, params in requests:
                headers, body = _modern_request(method, request_id, params)
                response = await client.post(
                    f"http://localhost:{action_server_process.port}/mcp",
                    headers=headers,
                    json=body,
                )
                expected_status = 406 if method == "subscriptions/listen" else 200
                assert response.status_code == expected_status, response.text
                if method == "server/discover":
                    payload = response.json()
                    assert "result" in payload, payload

    run_async_in_new_thread(check_routes)


@pytest.mark.integration_test
def test_mcp_test_gateway_observes_tool_routing_metadata(
    action_server_process: ActionServerProcess,
) -> None:
    """A real forwarding gateway observes the route metadata sent over HTTP."""
    from contextlib import asynccontextmanager

    from action_server_tests.fixtures import get_in_resources, run_async_in_new_thread

    root_dir = get_in_resources("no_conda", "greeter")
    action_server_process.start(
        db_file="server.db", cwd=root_dir, actions_sync=True, timeout=60 * 10
    )

    @asynccontextmanager
    async def test_gateway(target_url: str):
        from aiohttp import ClientSession, web

        observed: list[dict[str, str]] = []

        async def forward(request: web.Request) -> web.Response:
            body = await request.read()
            observed.append(
                {key.lower(): value for key, value in request.headers.items()}
            )
            async with ClientSession() as upstream_client:
                async with upstream_client.request(
                    request.method,
                    target_url + request.rel_url.path_qs,
                    data=body,
                    headers=dict(request.headers),
                ) as upstream_response:
                    response_headers = {
                        key: value
                        for key, value in upstream_response.headers.items()
                        if key.lower()
                        not in {"connection", "content-length", "transfer-encoding"}
                    }
                    return web.Response(
                        status=upstream_response.status,
                        headers=response_headers,
                        body=await upstream_response.read(),
                    )

        app = web.Application()
        app.router.add_route("*", "/{path:.*}", forward)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        try:
            yield f"http://127.0.0.1:{port}", observed
        finally:
            await runner.cleanup()

    async def call_through_gateway() -> list[dict[str, str]]:
        import httpx2
        from mcp.client.streamable_http import streamable_http_client

        target_url = f"http://localhost:{action_server_process.port}"
        async with test_gateway(target_url) as (gateway_url, observed):
            async with httpx2.AsyncClient() as http_client:
                async with streamable_http_client(
                    f"{gateway_url}/mcp", http_client=http_client
                ) as connection_info:
                    async with ClientSession(
                        connection_info[0], connection_info[1]
                    ) as session:
                        await session.discover()
                        result = await session.call_tool("greet", {"name": "Gateway"})
                        assert result.content[0].text == "Hello Mr. Gateway."
            return observed

    observed = run_async_in_new_thread(call_through_gateway)
    tool_call = next(
        headers for headers in observed if headers.get("mcp-method") == "tools/call"
    )
    assert tool_call["mcp-name"] == "greet"


@pytest.mark.integration_test
def test_mcp_forwards_headers_and_cookies_to_actions(
    action_server_process: ActionServerProcess,
) -> None:
    from functools import partial

    from action_server_tests.fixtures import get_in_resources

    root_dir = get_in_resources("no_conda", "check_headers")
    action_server_process.start(
        db_file="server.db", cwd=root_dir, actions_sync=True, timeout=60 * 10
    )

    async def call_action():
        import json

        async with action_server_process.mcp_client(
            headers={
                "X-Mcp-Acceptance": "forwarded",
                "Cookie": "mcp_acceptance_cookie=present",
            }
        ) as session:
            result = await session.call_tool("check_headers", {"name": "Header"})
        return json.loads(result.content[0].text)

    observed = run_async_in_new_thread(partial(call_action))
    observed_headers = {
        key.lower(): value for key, value in observed["headers"].items()
    }
    observed_cookies = {
        key.lower(): value for key, value in observed["cookies"].items()
    }
    assert observed_headers["x-mcp-acceptance"] == "forwarded", observed
    assert observed_cookies["mcp_acceptance_cookie"] == "present", observed


@pytest.mark.integration_test
def test_mcp_catalogs_are_fresh_after_action_reload(
    action_server_process: ActionServerProcess, tmpdir
) -> None:
    from pathlib import Path

    from action_server_tests.fixtures import run_async_in_new_thread
    from devutils.fixtures import wait_for_non_error_condition

    actions_file = Path(tmpdir) / "catalog" / "catalog_actions.py"
    actions_file.parent.mkdir(parents=True)

    def write_catalog(suffix: str) -> None:
        actions_file.write_text(
            f"""\
from actions import mcp

@mcp.tool()
def tool_{suffix}() -> str:
    return "tool {suffix}"

@mcp.resource("catalog://{suffix}")
def resource_{suffix}() -> str:
    return "resource {suffix}"

@mcp.prompt()
def prompt_{suffix}() -> str:
    return "prompt {suffix}"
"""
        )

    write_catalog("before")
    action_server_process.start(
        db_file="server.db",
        cwd=actions_file.parent,
        actions_sync=True,
        timeout=60 * 10,
        additional_args=["--auto-reload"],
    )

    async def catalog_names() -> dict[str, list[str]]:
        base_url = f"http://localhost:{action_server_process.port}/mcp"
        tools = await _post_modern_mcp(base_url, "tools/list", 1)
        resources = await _post_modern_mcp(base_url, "resources/list", 2)
        prompts = await _post_modern_mcp(base_url, "prompts/list", 3)
        for result in (tools, resources, prompts):
            assert result["ttlMs"] == 0
            assert result["cacheScope"] == "private"
        return {
            "tools": [tool["name"] for tool in tools["tools"]],
            "resources": [resource["uri"] for resource in resources["resources"]],
            "prompts": [prompt["name"] for prompt in prompts["prompts"]],
        }

    assert run_async_in_new_thread(catalog_names) == {
        "tools": ["tool_before"],
        "resources": ["catalog://before"],
        "prompts": ["prompt_before"],
    }
    write_catalog("after")

    def assert_fresh_catalogs() -> None:
        assert run_async_in_new_thread(catalog_names) == {
            "tools": ["tool_after"],
            "resources": ["catalog://after"],
            "prompts": ["prompt_after"],
        }

    wait_for_non_error_condition(assert_fresh_catalogs)
