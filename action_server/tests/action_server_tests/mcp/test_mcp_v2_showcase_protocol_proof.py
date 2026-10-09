"""Exercise the public stateless MCP contract through a mounted Runtime."""

import uuid
from pathlib import Path

import pytest
from action_server_tests.fixtures import run_async_in_new_thread
from actions.server._selftest import ActionServerProcess


@pytest.mark.integration_test
def test_mcp_v2_showcase_protocol_proof(
    action_server_process: ActionServerProcess, tmp_path: Path
) -> None:
    """One local action catalog exposes every current core MCP surface."""
    (tmp_path / "package.yaml").write_text(
        """\
spec-version: v2
name: MCP v2 protocol proof
description: Ephemeral integration fixture for the mounted Runtime protocol.
version: 0.0.1
dependencies:
  conda-forge:
    - python=3.12.12
    - uv=0.8.17
  pypi:
    - actions-core=1.0.2
""",
        encoding="utf-8",
    )
    (tmp_path / "showcase_actions.py").write_text(
        '''\
from actions import Response, Table, mcp


@mcp.tool(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
def lookup_item(item_id: str) -> Response[Table]:
    """Look up a static demo item by its identifier."""
    if item_id != "alpha":
        return Response(error="No demo item matches this ID.")
    return Response(
        result=Table(
            columns=["item_id", "title"],
            rows=[[item_id, "Alpha item"]],
            name="demo_item",
        )
    )


@mcp.resource("showcase://catalog/overview")
def catalog_overview() -> str:
    """Describe the static showcase catalog."""
    return "Demo catalog with one item: alpha."


@mcp.resource("showcase://items/{item_id}")
def item_resource(item_id: str) -> str:
    """Return the static item description."""
    return "Alpha item" if item_id == "alpha" else "Unknown demo item."


@mcp.prompt()
def explain_item(item_id: str) -> str:
    """Explain one item from the demo catalog."""
    return f"Explain demo item {item_id}."
''',
        encoding="utf-8",
    )
    action_server_process.start(
        db_file="server.db",
        cwd=tmp_path,
        actions_sync=True,
        timeout=60 * 10,
    )

    async def exercise_protocol() -> None:
        import httpx2

        protocol_version = "2026-07-28"
        base_url = f"http://localhost:{action_server_process.port}/mcp"
        async with httpx2.AsyncClient(trust_env=False) as client:
            next_request_id = 0

            async def post(method: str, params: dict | None = None):
                nonlocal next_request_id
                next_request_id += 1
                request_id = str(uuid.uuid4())
                request_params = dict(params or {})
                request_params["_meta"] = {
                    "io.modelcontextprotocol/protocolVersion": protocol_version,
                    "io.modelcontextprotocol/clientCapabilities": {},
                }
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Mcp-Protocol-Version": protocol_version,
                    "Mcp-Method": method,
                    "X-Request-ID": request_id,
                }
                if method in ("tools/call", "prompts/get"):
                    headers["Mcp-Name"] = request_params["name"]
                elif method == "resources/read":
                    headers["Mcp-Name"] = request_params["uri"]
                response = await client.post(
                    base_url,
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": next_request_id,
                        "method": method,
                        "params": request_params,
                    },
                )
                assert response.status_code == 200, response.text
                assert "Mcp-Session-Id" not in response.headers
                assert response.headers["X-Request-ID"] == request_id
                payload = response.json()
                assert "error" not in payload, payload
                return payload["result"]

            discovered = await post("server/discover")
            assert discovered

            catalogs = {
                method: await post(method)
                for method in (
                    "tools/list",
                    "resources/list",
                    "resources/templates/list",
                    "prompts/list",
                )
            }
            revisions = {
                result["_meta"]["actions.catalogRevision"]
                for result in catalogs.values()
            }
            assert len(revisions) == 1
            revision = revisions.pop()
            assert len(revision) == 64
            assert all(character in "0123456789abcdef" for character in revision)
            for result in catalogs.values():
                assert result["ttlMs"] == 0
                assert result["cacheScope"] == "private"

            tool = catalogs["tools/list"]["tools"][0]
            assert tool["name"] == "lookup_item"
            assert tool["inputSchema"]["properties"]["item_id"]["type"] == "string"
            assert "item_id" in tool["inputSchema"]["required"]
            assert catalogs["resources/list"]["resources"][0]["uri"] == (
                "showcase://catalog/overview"
            )
            assert (
                catalogs["resources/templates/list"]["resourceTemplates"][0][
                    "uriTemplate"
                ]
                == "showcase://items/{item_id}"
            )
            assert catalogs["prompts/list"]["prompts"][0]["name"] == "explain_item"

            called = await post(
                "tools/call",
                {"name": "lookup_item", "arguments": {"item_id": "alpha"}},
            )
            assert called["structuredContent"] == {
                "result": {
                    "columns": ["item_id", "title"],
                    "rows": [["alpha", "Alpha item"]],
                    "name": "demo_item",
                    "description": None,
                },
                "error": None,
            }
            safe_error = await post(
                "tools/call",
                {"name": "lookup_item", "arguments": {"item_id": "missing"}},
            )
            assert safe_error["structuredContent"] == {
                "result": None,
                "error": "No demo item matches this ID.",
            }

            direct = await post(
                "resources/read", {"uri": "showcase://catalog/overview"}
            )
            assert direct["contents"][0]["text"] == (
                "Demo catalog with one item: alpha."
            )
            templated = await post("resources/read", {"uri": "showcase://items/alpha"})
            assert templated["contents"][0]["text"] == "Alpha item"
            prompt = await post(
                "prompts/get",
                {"name": "explain_item", "arguments": {"item_id": "alpha"}},
            )
            assert prompt["messages"][0]["content"]["text"] == (
                "Explain demo item alpha."
            )

    run_async_in_new_thread(exercise_protocol)
