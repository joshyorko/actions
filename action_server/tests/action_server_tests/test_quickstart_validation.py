"""Smoke-test the public community quickstart."""

import pytest

from action_server_tests.fixtures import actions_server_run, run_async_in_new_thread

pytestmark = pytest.mark.integration_test


def test_public_quickstart_creates_project_and_serves_mcp(
    tmp_path, action_server_process
) -> None:
    """The documented install, new, start, and MCP path works end to end."""
    project_path = tmp_path / "my-project"
    actions_server_run(
        ["new", "--name", project_path.name, "--template", "minimal"],
        returncode=0,
        cwd=tmp_path,
    )
    assert (project_path / "package.yaml").is_file()

    action_server_process.start(
        db_file="server.db",
        cwd=project_path,
        actions_sync=True,
        timeout=60 * 10,
    )

    async def request_tools() -> None:
        import httpx2

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
        async with httpx2.AsyncClient() as client:
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
        payload = response.json()
        assert any(tool["name"] == "greet" for tool in payload["result"]["tools"])

    run_async_in_new_thread(request_tools)
