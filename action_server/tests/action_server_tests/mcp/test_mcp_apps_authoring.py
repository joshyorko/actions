import asyncio
import importlib.util
import json
import os
import shlex
import shutil
import socket
import subprocess
from collections.abc import Callable
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from action_server_tests.fixtures import run_async_in_new_thread
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import ReadResourceResult, TextContent, TextResourceContents

from actions.server._selftest import ActionServerProcess


CANVAS_RESOURCE_URI = "ui://action-canvas/v1/canvas.html?query-fixture=0.1"


def test_public_mcp_apps_metadata_through_runtime_streamable_route(
    monkeypatch, tmp_path
) -> None:
    async def check() -> None:
        await _check_public_metadata(monkeypatch, tmp_path)

    run_async_in_new_thread(partial(check))


async def _check_public_metadata(monkeypatch, tmp_path) -> None:
    from actions import _hooks
    from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

    captured: dict[str, tuple[Callable[..., Any], dict[str, Any]]] = {}
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
                    assert content.meta is not None
                    assert content.meta["ui"] == {
                        "csp": {"connectDomains": ["https://api.example.test"]}
                    }
                    assert resource.meta is not None
                    assert resource.meta["ui"] == {
                        "csp": {"connectDomains": ["https://api.example.test"]}
                    }

                    text = await session.call_tool("text_result", {})
                    assert len(text.content) == 1
                    assert isinstance(text.content[0], TextContent)
                    assert text.content[0].text == "ready"
                    assert text.meta is not None
                    assert tools["text_result"].meta is not None
                    assert text.meta["ui"] == tools["text_result"].meta["ui"]
                    assert text.meta["com.example.extra"] == {"v": 1}

                    structured = await session.call_tool("object_result", {})
                    assert structured.content == []
                    assert structured.structured_content == {"status": "ready"}
                    assert structured.meta is not None
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
            content = resource.contents[0]
            assert isinstance(content, TextResourceContents)
            assert content.mime_type == "text/html;profile=mcp-app"
            assert content.text == "<html>fixture</html>"
            assert content.meta is not None
            assert content.meta["ui"] == {
                "csp": {"connectDomains": ["https://api.example.test"]}
            }
            assert resource.meta is not None
            assert resource.meta["ui"] == {
                "csp": {"connectDomains": ["https://api.example.test"]}
            }

            text = await session.call_tool("text_result", {})
            assert len(text.content) == 1
            assert isinstance(text.content[0], TextContent)
            assert text.content[0].text == "ready"
            assert text.meta is not None
            assert text.meta["com.example.extra"] == {"v": 1}

            structured = await session.call_tool("object_result", {})
            assert structured.content == []
            assert structured.structured_content == {"status": "ready"}
            assert structured.meta is not None
            assert structured.meta["ui"]["visibility"] == ["app"]

    assert run_async_in_new_thread(partial(check_routes)) is None


@pytest.mark.integration_test
@pytest.mark.skipif(
    os.environ.get("ACTIONS_CANVAS_RUNTIME_ACCEPTANCE") != "1",
    reason="Set ACTIONS_CANVAS_RUNTIME_ACCEPTANCE=1 to run the RCC/browser acceptance.",
)
def test_canvas_view_calls_public_action_through_runtime_bridge(
    action_server_process: ActionServerProcess, tmp_path
) -> None:
    repository_root = Path(__file__).resolve().parents[4]
    frontend_root = repository_root / "action_server" / "frontend"
    candidate_core_wheel_dir = tmp_path / "candidate-core"
    candidate_core_wheel_dir.mkdir()
    build_env = os.environ.copy()
    build_env["UV_CACHE_DIR"] = str(tmp_path / "uv-cache")
    build_env["TMPDIR"] = str(tmp_path)
    subprocess.run(
        [
            shutil.which("uv") or "uv",
            "build",
            "--wheel",
            "--out-dir",
            str(candidate_core_wheel_dir),
            str(repository_root / "actions"),
        ],
        env=build_env,
        check=True,
        timeout=120,
    )
    candidate_core_wheel = next(candidate_core_wheel_dir.glob("actions_core-*.whl"))
    if os.name == "nt":
        quoted_wheel_path = subprocess.list2cmdline([str(candidate_core_wheel)])
    else:
        quoted_wheel_path = shlex.quote(str(candidate_core_wheel))
    package_yaml = tmp_path / "package.yaml"
    package_yaml.write_text(
        "spec-version: v2\n"
        "name: Canvas Runtime bridge acceptance\n"
        "description: Isolated fixture using the exact candidate Core wheel.\n"
        "version: 0.0.1\n"
        "dependencies:\n"
        "  conda-forge:\n"
        "    - python=3.12\n"
        "    - uv=0.9.26\n"
        "  pypi:\n"
        "    - actions-core=1.0.2\n"
        "post-install:\n"
        "  - python -m pip install --no-deps --force-reinstall "
        f"{quoted_wheel_path}\n",
        encoding="utf-8",
    )
    subprocess.run(["npm", "run", "build:canvas"], cwd=frontend_root, check=True)
    canvas_html = (frontend_root / "dist-canvas" / "index.html").read_text(
        encoding="utf-8"
    )
    (tmp_path / "canvas.html").write_text(canvas_html, encoding="utf-8")
    (tmp_path / "canvas_actions.py").write_text(
        '''
from pathlib import Path

from actions import mcp

UI_URI = "ui://action-canvas/v1/canvas.html?query-fixture=0.1"

@mcp.resource(
    UI_URI,
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"csp": {}}},
)
def canvas_view() -> str:
    return Path(__file__).with_name("canvas.html").read_text(encoding="utf-8")

@mcp.tool(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
    meta={"ui": {"resourceUri": UI_URI, "visibility": ["model", "app"]}},
)
def canvas_fixture_search(query: str) -> dict[str, object]:
    if query.casefold() == "alpha":
        return {
            "rows": [
                {"id": "record-001", "title": "Alpha guide", "category": "Guide"},
                {"id": "record-002", "title": "Alpha checklist", "category": "Checklist"},
            ],
            "artifact": {"handle": "art_7Wk3qN9pL2xD5mR8sV4cY1"},
            "error": None,
        }
    return {
        "rows": [],
        "artifact": None,
        "error": {
            "code": "no_matches",
            "message": "No records matched that query.",
        },
    }

@mcp.tool(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
    meta={"ui": {"resourceUri": UI_URI, "visibility": ["app"]}},
)
def canvas_fixture_artifact_status(handle: str) -> dict[str, str]:
    if handle != "art_7Wk3qN9pL2xD5mR8sV4cY1":
        raise ValueError("Unknown fixture artifact handle.")
    return {"status": "ready"}
''',
        encoding="utf-8",
    )

    action_server_process.start(
        cwd=tmp_path,
        db_file="server.db",
        actions_sync=True,
        timeout=120,
    )

    async def check_runtime_contract() -> None:
        async with action_server_process.mcp_client() as session:
            listed = await session.list_tools()
            search_tool = next(
                tool for tool in listed.tools if tool.name == "canvas_fixture_search"
            )
            assert search_tool.meta is not None
            assert search_tool.meta["ui"] == {
                "resourceUri": CANVAS_RESOURCE_URI,
                "visibility": ["model", "app"],
            }

            resource = await session.read_resource(CANVAS_RESOURCE_URI)
            resource_content = resource.contents[0]
            assert isinstance(resource_content, TextResourceContents)
            assert resource_content.mime_type == "text/html;profile=mcp-app"
            assert resource_content.text == canvas_html

            result = await session.call_tool(
                "canvas_fixture_search", {"query": "alpha"}
            )
            assert result.structured_content == {
                "rows": [
                    {"id": "record-001", "title": "Alpha guide", "category": "Guide"},
                    {
                        "id": "record-002",
                        "title": "Alpha checklist",
                        "category": "Checklist",
                    },
                ],
                "artifact": {"handle": "art_7Wk3qN9pL2xD5mR8sV4cY1"},
                "error": None,
            }

    assert run_async_in_new_thread(partial(check_runtime_contract)) is None

    playwright_executable = shutil.which("chromium")
    if playwright_executable:
        env = os.environ.copy()
        env["CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = playwright_executable
    else:
        env = os.environ.copy()
    env["CANVAS_RUNTIME_MCP_URL"] = (
        f"http://127.0.0.1:{action_server_process.port}/mcp"
    )
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", 0))
        env["CANVAS_HARNESS_PORT"] = str(port_probe.getsockname()[1])
    subprocess.run(
        [
            "npm",
            "run",
            "test:canvas-harness",
            "--",
            "--grep",
            "real Runtime Action result",
        ],
        cwd=frontend_root,
        env=env,
        check=True,
        timeout=180,
    )
