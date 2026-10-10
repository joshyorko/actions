"""Create the embedded MCP showcase and exercise its real stateless endpoint."""

import importlib.util
from pathlib import Path

import pytest
from action_server_tests.fixtures import actions_server_run

from actions.server._selftest import ActionServerProcess


def _load_example(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.integration_test
def test_embedded_mcp_v2_showcase_template_end_to_end(
    action_server_process: ActionServerProcess, tmp_path: Path
) -> None:
    project = tmp_path / "mcp-showcase"
    actions_server_run(
        [
            "new",
            "--name",
            project.name,
            "--template",
            "mcp-v2-showcase",
        ],
        returncode=0,
        cwd=tmp_path,
    )
    assert (project / "package.yaml").is_file()
    assert (project / "showcase_actions.py").is_file()
    assert (project / "examples" / "mcp_client.py").is_file()

    action_server_process.start(
        db_file="server.db",
        cwd=project,
        actions_sync=True,
        timeout=60 * 10,
    )
    base_url = f"http://localhost:{action_server_process.port}/mcp"
    client = _load_example(
        project / "examples" / "mcp_client.py", "mcp_showcase_client"
    )
    sse = _load_example(project / "examples" / "open_close_sse.py", "mcp_showcase_sse")

    observed = client.exercise(base_url)
    assert observed["discovered"]
    catalogs = observed["catalogs"]
    tools = {tool["name"]: tool for tool in catalogs["tools/list"]["tools"]}
    assert set(tools) == {
        "lookup_demo_item",
        "search_demo_catalog",
    }
    search_inputs = tools["search_demo_catalog"]["inputSchema"]["properties"]
    assert search_inputs["query"]["type"] == "string"
    assert search_inputs["limit"]["type"] == "integer"
    assert search_inputs["limit"]["default"] == 2
    assert "query" in tools["search_demo_catalog"]["inputSchema"]["required"]
    assert "item_id" in tools["lookup_demo_item"]["inputSchema"]["required"]
    assert tools["search_demo_catalog"]["outputSchema"]["type"] == "object"
    assert [
        resource["uri"] for resource in catalogs["resources/list"]["resources"]
    ] == ["showcase://catalog/overview"]
    assert [
        resource["uriTemplate"]
        for resource in catalogs["resources/templates/list"]["resourceTemplates"]
    ] == ["showcase://items/{item_id}"]
    assert [prompt["name"] for prompt in catalogs["prompts/list"]["prompts"]] == [
        "explain_demo_item"
    ]

    results = observed["operations"]
    assert results[0]["structuredContent"]["result"]["rows"][0][0] == "alpha"
    assert results[1]["structuredContent"]["result"]["item_id"] == "alpha"
    assert results[2]["contents"][0]["text"].startswith("Static demo catalog:")
    assert results[3]["contents"][0]["text"].startswith("Alpha field guide:")
    assert "Alpha field guide" in results[4]["messages"][0]["content"]["text"]
    assert results[5]["structuredContent"] == {
        "result": None,
        "error": "No demo item matches this ID.",
    }

    sse.open_channel(base_url)
