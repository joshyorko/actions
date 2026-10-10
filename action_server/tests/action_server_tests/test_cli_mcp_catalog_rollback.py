"""Complete CLI admission must reject ambiguous MCP keys without losing source."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import httpx
import pytest

from actions.server._selftest import ActionServerProcess, actions_server_run


def _write_retained_package(package: Path, generation: str) -> None:
    package.mkdir(exist_ok=True)
    (package / "catalog_actions.py").write_text(
        f'''from actions import mcp

@mcp.tool()
def retained_tool() -> str:
    """{generation} tool."""
    return "{generation}-tool"

@mcp.resource("catalog://retained")
def retained_resource() -> str:
    """{generation} resource."""
    return "{generation}-resource"

@mcp.resource("catalog://retained/{{item}}")
def retained_template(item: str) -> str:
    """{generation} template."""
    return f"{generation}-template-{{item}}"

@mcp.prompt()
def retained_prompt(subject: str) -> str:
    """{generation} prompt."""
    return f"{generation}-prompt-{{subject}}"
''',
        encoding="utf-8",
    )


def _mcp(client: httpx.Client, method: str, params: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": method,
    }
    if "name" in params:
        headers["Mcp-Name"] = params["name"]
    elif "uri" in params:
        headers["Mcp-Name"] = params["uri"]
    response = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {
                **params,
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientCapabilities": {},
                },
            },
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "error" not in payload, payload
    return payload["result"]


def _catalogs(client: httpx.Client) -> dict[str, Any]:
    catalogs = {
        method: _mcp(client, method, {})
        for method in (
            "tools/list",
            "resources/list",
            "resources/templates/list",
            "prompts/list",
        )
    }
    assert (
        len(
            {
                catalog["_meta"]["actions.catalogRevision"]
                for catalog in catalogs.values()
            }
        )
        == 1
    )
    for catalog in catalogs.values():
        assert catalog["ttlMs"] == 0
        assert catalog["cacheScope"] == "private"
    return catalogs


def _assert_retained_callbacks(client: httpx.Client) -> None:
    for name, expected in (
        ("retained_tool", "last-good-tool"),
        ("sibling_tool", "last-good-sibling"),
    ):
        result = _mcp(client, "tools/call", {"name": name, "arguments": {}})
        assert result["content"][0]["text"] == expected
    for uri, expected in (
        ("catalog://retained", "last-good-resource"),
        ("catalog://retained/alpha", "last-good-template-alpha"),
    ):
        result = _mcp(client, "resources/read", {"uri": uri})
        assert result["contents"][0]["text"] == expected
    result = _mcp(
        client,
        "prompts/get",
        {"name": "retained_prompt", "arguments": {"subject": "alpha"}},
    )
    assert result["messages"][0]["content"]["text"] == "last-good-prompt-alpha"
    response = client.post(
        "/api/actions/package-a/retained-prompt/run", json={"subject": "alpha"}
    )
    assert response.status_code == 200, response.text
    assert response.json() == "last-good-prompt-alpha"


@contextmanager
def _runtime(
    datadir: Path, cwd: Path, directories: tuple[Path, ...] = ()
) -> Iterator[httpx.Client]:
    from actions.server._common.wait_for import wait_for_condition

    process = ActionServerProcess(datadir)
    try:
        process.start(
            db_file="catalog.sqlite",
            actions_sync=bool(directories),
            cwd=cwd,
            min_processes=0,
            max_processes=2,
            reuse_processes=True,
            add_shutdown_api=True,
            env={"NO_PROXY": "*", "no_proxy": "*"},
            additional_args=["--address=127.0.0.1"]
            + [f"--dir={directory}" for directory in directories],
            timeout=30,
        )
        with httpx.Client(
            base_url=f"http://127.0.0.1:{process.port}", timeout=30, trust_env=False
        ) as client:
            try:
                yield client
            finally:
                response = client.post("/api/shutdown/", json={})
                assert response.status_code == 200, response.text
                wait_for_condition(
                    lambda: process.process.returncode is not None,
                    msg="Runtime did not exit after controlled shutdown",
                    timeout=10,
                    sleep=0.05,
                )
                assert process.process.returncode == 1
    finally:
        process.stop()


def _catalog_rows(database: Path) -> dict[str, list[tuple[Any, ...]]]:
    with sqlite3.connect(database) as connection:
        return {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
            for table in ("action_package", "action")
        }


@pytest.mark.integration_test
@pytest.mark.parametrize(
    ("collision", "declaration", "diagnostic"),
    [
        (
            "resource",
            '@mcp.resource("catalog://retained")\n'
            'def conflicting_resource() -> str:\n    return "candidate-resource"\n',
            "duplicate resource URI",
        ),
        (
            "template",
            '@mcp.resource("catalog://retained/{item}")\n'
            "def conflicting_template(item: str) -> str:\n    return item\n",
            "duplicate resource template URI",
        ),
        (
            "prompt",
            "@mcp.prompt()\n"
            "def retained_prompt(subject: str) -> str:\n    return subject\n",
            "duplicate prompt name",
        ),
    ],
    ids=("resource", "template", "prompt"),
)
def test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    collision: str,
    declaration: str,
    diagnostic: str,
) -> None:
    if "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE" in os.environ:
        pytest.skip(
            "Unmanaged source-subprocess proof; native managed packages are separate"
        )
    monkeypatch.setenv("ACTIONS_HOME", str(tmp_path / "actions-home"))
    monkeypatch.setenv("ROBOTS_HOME", str(tmp_path / "robots-home"))
    package_a = tmp_path / "package_a"
    package_b = tmp_path / "package_b"
    package_c = tmp_path / "package_c"
    datadir = tmp_path / "runtime-data"
    _write_retained_package(package_a, "last-good")
    package_b.mkdir()
    (package_b / "catalog_actions.py").write_text(
        "from actions import mcp\n@mcp.tool()\n"
        'def sibling_tool() -> str:\n    return "last-good-sibling"\n',
        encoding="utf-8",
    )
    with _runtime(datadir, tmp_path, (package_a, package_b)) as client:
        before_catalogs = _catalogs(client)
        _assert_retained_callbacks(client)

    database = datadir / "catalog.sqlite"
    before_rows = _catalog_rows(database)
    with sqlite3.connect(database) as connection:
        old_sources = [
            Path(row[0])
            for row in connection.execute("SELECT directory FROM action_package")
        ]
    old_source_bytes = {
        source / "catalog_actions.py": (source / "catalog_actions.py").read_bytes()
        for source in old_sources
    }
    source_store = datadir / ".rcc-runtime-sources"
    before_snapshots = set(source_store.iterdir())

    _write_retained_package(package_a, "candidate")
    package_c.mkdir()
    (package_c / "catalog_actions.py").write_text(
        "from actions import mcp\n" + declaration, encoding="utf-8"
    )
    # A is collected and B is genuinely omitted before C creates the collision.
    # The whole admission must roll back A's replacement and B's disable.
    result = actions_server_run(
        [
            "start",
            "--actions-sync=true",
            f"--dir={package_a}",
            f"--dir={package_c}",
            "--db-file=catalog.sqlite",
            f"--datadir={datadir}",
            "--address=127.0.0.1",
            "--port=0",
            "--min-processes=0",
            "--skip-lint",
        ],
        returncode=1,
        cwd=tmp_path,
        timeout=30,
        additional_env={"NO_PROXY": "*", "no_proxy": "*"},
    )
    assert diagnostic in result.stdout + result.stderr
    assert _catalog_rows(database) == before_rows
    assert set(source_store.iterdir()) == before_snapshots
    for source, expected in old_source_bytes.items():
        assert source.read_bytes() == expected

    with _runtime(datadir, tmp_path) as client:
        assert _catalogs(client) == before_catalogs
        _assert_retained_callbacks(client)
    assert _catalog_rows(database) == before_rows
    print(f"COMPLETE_CLI_MCP_ROLLBACK_PASS collision={collision}")
