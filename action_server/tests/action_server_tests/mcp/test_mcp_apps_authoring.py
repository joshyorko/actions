import asyncio
import importlib.util
import json
from functools import partial
from types import SimpleNamespace

import pytest
from action_server_tests.fixtures import run_async_in_new_thread
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import ReadResourceResult, TextResourceContents

from actions.server._selftest import ActionServerProcess


def test_public_mcp_apps_metadata_through_runtime_streamable_route(
    monkeypatch, tmp_path
) -> None:
    async def check() -> None:
        await _check_public_metadata(monkeypatch, tmp_path)

    run_async_in_new_thread(partial(check))


async def _check_public_metadata(monkeypatch, tmp_path) -> None:
    from actions import _hooks
    from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

    captured = {}
    monkeypatch.setattr(
        _hooks,
        "on_action_func_found",
        lambda func, options: captured.__setitem__(func.__name__, (func, options)),
    )
    package_file = tmp_path / "mcp_apps.py"
    package_file.write_text(
        """from actions import mcp

UI_URI = "ui://fixture/view"

@mcp.resource(
    UI_URI,
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"csp": {"connectDomains": ["https://api.example.test"]}}},
)
def app_view() -> str:
    return "<html>fixture</html>"

@mcp.tool(meta={"ui": {"resourceUri": UI_URI, "visibility": ["model", "app"]}, "com.example.extra": {"v": 1}})
def text_result() -> str:
    return "ready"

@mcp.tool(meta={"ui": {"resourceUri": UI_URI, "visibility": ["app"]}})
def object_result() -> dict[str, str]:
    return {"status": "ready"}
""",
        encoding="utf-8",
    )
    module_spec = importlib.util.spec_from_file_location("mcp_apps", package_file)
    assert module_spec and module_spec.loader
    package_module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(package_module)

    replacement = McpServerSetupHelper()
    for name, (decorated_func, options) in captured.items():
        output_schema = (
            '{"type":"object","properties":{"status":{"type":"string"}}}'
            if name == "object_result"
            else '{"type":"string"}'
        )
        action = SimpleNamespace(
            name=name,
            options=json.dumps(options),
            input_schema='{"type":"object","properties":{}}',
            output_schema=output_schema,
        )

        async def invoke(
            *, response_handler, inputs, headers, cookies, fn=decorated_func
        ):
            result = fn(**inputs)
            if asyncio.iscoroutine(result):
                return await result
            return result

        replacement.register_action(invoke, None, action, name, "")

    persistent = McpServerSetupHelper()
    persistent.replace_catalog(replacement)
    app = persistent.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=persistent.transport_security,
    )

    import httpx2

    async with app.router.lifespan_context(app):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            base_url="http://127.0.0.1:8000",
        ) as http_client:
            async with streamable_http_client(
                "http://127.0.0.1:8000/mcp", http_client=http_client
            ) as connection:
                async with ClientSession(connection[0], connection[1]) as session:
                    await session.discover()
                    listed = await session.list_tools()
                    tools = {tool.name: tool for tool in listed.tools}
                    assert tools["text_result"].meta == {
                        "ui": {
                            "resourceUri": "ui://fixture/view",
                            "visibility": ["model", "app"],
                        },
                        "com.example.extra": {"v": 1},
                    }

                    resource = await session.read_resource("ui://fixture/view")
                    assert isinstance(resource, ReadResourceResult)
                    content = resource.contents[0]
                    assert isinstance(content, TextResourceContents)
                    assert content.mime_type == "text/html;profile=mcp-app"
                    assert content.text == "<html>fixture</html>"
                    assert resource.meta["ui"] == {
                        "csp": {"connectDomains": ["https://api.example.test"]}
                    }

                    text = await session.call_tool("text_result", {})
                    assert [item.text for item in text.content] == ["ready"]
                    assert text.meta["ui"] == tools["text_result"].meta["ui"]
                    assert text.meta["com.example.extra"] == {"v": 1}

                    structured = await session.call_tool("object_result", {})
                    assert structured.content == []
                    assert structured.structured_content == {"status": "ready"}
                    assert structured.meta["ui"] == {
                        "resourceUri": "ui://fixture/view",
                        "visibility": ["app"],
                    }


@pytest.mark.integration_test
def test_public_mcp_apps_metadata_through_action_server_process(
    action_server_process: ActionServerProcess, tmp_path
) -> None:
    package_file = tmp_path / "mcp_apps.py"
    package_file.write_text(
        """from actions import mcp

UI_URI = "ui://fixture/view?revision=1"

@mcp.resource(
    UI_URI,
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"csp": {"connectDomains": ["https://api.example.test"]}}},
)
def app_view() -> str:
    return "<html>fixture</html>"

@mcp.tool(meta={"ui": {"resourceUri": UI_URI, "visibility": ["model", "app"]}, "com.example.extra": {"v": 1}})
def text_result() -> str:
    return "ready"

@mcp.tool(meta={"ui": {"resourceUri": UI_URI, "visibility": ["app"]}})
def object_result() -> dict[str, str]:
    return {"status": "ready"}
""",
        encoding="utf-8",
    )
    action_server_process.start(
        cwd=tmp_path,
        db_file="server.db",
        actions_sync=True,
        timeout=120,
    )

    async def check_routes() -> None:
        async with action_server_process.mcp_client() as session:
            listed = await session.list_tools()
            tools = {tool.name: tool for tool in listed.tools}
            expected_meta = {
                "ui": {
                    "resourceUri": "ui://fixture/view?revision=1",
                    "visibility": ["model", "app"],
                },
                "com.example.extra": {"v": 1},
            }
            assert tools["text_result"].meta == expected_meta

            resource = await session.read_resource("ui://fixture/view?revision=1")
            assert resource.contents[0].mime_type == "text/html;profile=mcp-app"
            assert resource.contents[0].text == "<html>fixture</html>"
            assert resource.meta["ui"] == {
                "csp": {"connectDomains": ["https://api.example.test"]}
            }

            text = await session.call_tool("text_result", {})
            assert [item.text for item in text.content] == ["ready"]
            assert text.meta["com.example.extra"] == {"v": 1}

            structured = await session.call_tool("object_result", {})
            assert structured.content == []
            assert structured.structured_content == {"status": "ready"}
            assert structured.meta["ui"]["visibility"] == ["app"]

    assert run_async_in_new_thread(partial(check_routes)) is None
