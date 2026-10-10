"""Acceptance checks for the packaged Canvas Query template."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import zipfile
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest
from action_server_tests.fixtures import actions_server_run
from actions.server._selftest import ActionServerProcess

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
EMBEDDED_TEMPLATES = REPOSITORY_ROOT / "action_server/src/actions/server/templates"


def test_canvas_query_template_is_in_the_deterministic_offline_bundle() -> None:
    metadata = json.loads(
        (EMBEDDED_TEMPLATES / "action-templates.yaml").read_text(encoding="utf-8")
    )
    bundle_bytes = (EMBEDDED_TEMPLATES / "action-templates.zip").read_bytes()
    assert hashlib.sha256(bundle_bytes).hexdigest() == metadata["hash"]
    assert metadata["templates"]["canvas-query"].startswith("Canvas Query -")

    with zipfile.ZipFile(EMBEDDED_TEMPLATES / "action-templates.zip") as bundle:
        embedded_template = bundle.read("canvas-query.zip")
    assert (
        embedded_template == (EMBEDDED_TEMPLATES / "zips/canvas-query.zip").read_bytes()
    )
    with zipfile.ZipFile(io.BytesIO(embedded_template)) as template:
        names = set(template.namelist())
        assert {
            "package.yaml",
            "LICENSE",
            "README.md",
            "canvas_query.py",
            "canvas.html",
            "canvas-resource.json",
            "acceptance-gates.json",
        } <= names
        packaged_action = template.read("canvas_query.py").decode("utf-8")
        package_yaml = template.read("package.yaml").decode("utf-8")
        resource_bytes = template.read("canvas.html")
    assert "from actions.mcp import resource, tool" in packaged_action
    assert "actions.server" not in packaged_action
    assert "actions-core=1.0.3" in package_yaml
    resource_info_path = REPOSITORY_ROOT / "templates/canvas-query/canvas-resource.json"
    resource_info = json.loads(resource_info_path.read_text(encoding="utf-8"))
    assert hashlib.sha256(resource_bytes).hexdigest() == resource_info["sha256"]


def test_canvas_query_examples_match_shared_schema_limits_and_partial_result() -> None:
    fixture_dir = REPOSITORY_ROOT / "docs/contracts/canvas/fixtures"
    schema = json.loads(
        (fixture_dir / "query-results-v0.1.schema.json").read_text(encoding="utf-8")
    )
    fixture = json.loads(
        (fixture_dir / "query-results-v0.1.fixture.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(fixture)

    candidate = deepcopy(fixture)
    candidate["input"]["query"] = "😀" * 64
    validator.validate(candidate)

    for query in ("", "   ", "😀" * 65):
        candidate = deepcopy(fixture)
        candidate["input"]["query"] = query
        errors = list(validator.iter_errors(candidate))
        assert any(list(error.absolute_path) == ["input", "query"] for error in errors)

    partial_result = deepcopy(fixture)
    partial_result["success"]["artifact"] = None
    errors = list(validator.iter_errors(partial_result))
    assert any(list(error.absolute_path) == ["success", "artifact"] for error in errors)


def _create_project(tmp_path: Path, name: str) -> Path:
    project = tmp_path / name
    actions_server_run(
        ["new", "--name", name, "--template", "canvas-query"],
        returncode=0,
        cwd=tmp_path,
    )
    return project


def test_new_canvas_project_extracts_the_embedded_template(tmp_path: Path) -> None:
    project = _create_project(tmp_path, "canvas-query")
    expected_files = {
        "package.yaml",
        "LICENSE",
        "README.md",
        "canvas_query.py",
        "canvas.html",
        "canvas-resource.json",
        "acceptance-gates.json",
        "tests/test_canvas_query.py",
    }
    assert expected_files <= {
        path.relative_to(project).as_posix()
        for path in project.rglob("*")
        if path.is_file()
    }
    resource_bytes = (project / "canvas.html").read_bytes()
    resource_info = json.loads(
        (project / "canvas-resource.json").read_text(encoding="utf-8")
    )
    assert hashlib.sha256(resource_bytes).hexdigest() == resource_info["sha256"]
    package = (project / "package.yaml").read_text(encoding="utf-8")
    assert "actions-core=1.0.3" in package
    assert "robocorp" not in package.casefold()


@pytest.mark.integration_test
@pytest.mark.skipif(
    os.environ.get("ACTIONS_CANVAS_TEMPLATE_ACCEPTANCE") != "1",
    reason="Set ACTIONS_CANVAS_TEMPLATE_ACCEPTANCE=1 for the Runtime/browser gate.",
)
def test_canvas_template_runs_through_runtime_and_real_browser(
    action_server_process: ActionServerProcess, tmp_path: Path
) -> None:
    project = _create_project(tmp_path, "canvas-query-runtime")
    action_server_process.start(
        cwd=project,
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
                "resourceUri": "ui://action-canvas/v1/canvas.html?query-fixture=0.1",
                "visibility": ["model", "app"],
            }

            resource = await session.read_resource(
                "ui://action-canvas/v1/canvas.html?query-fixture=0.1"
            )
            content = resource.contents[0]
            assert content.mime_type == "text/html;profile=mcp-app"
            assert content.text == (project / "canvas.html").read_text(encoding="utf-8")

            match = await session.call_tool("canvas_fixture_search", {"query": "alpha"})
            assert match.structured_content == {
                "rows": [
                    {"id": "record-001", "title": "Alpha guide", "category": "Guide"},
                    {
                        "id": "record-002",
                        "title": "Alpha checklist",
                        "category": "Checklist",
                    },
                ],
                "artifact": None,
                "error": None,
            }
            miss = await session.call_tool(
                "canvas_fixture_search", {"query": "unmatched-query"}
            )
            assert miss.structured_content == {
                "rows": [],
                "artifact": None,
                "error": {
                    "code": "no_matches",
                    "message": "No records matched that query.",
                },
            }

    from action_server_tests.fixtures import run_async_in_new_thread

    assert run_async_in_new_thread(check_runtime_contract) is None

    repository_root = Path(__file__).resolve().parents[4]
    frontend_root = repository_root / "action_server" / "frontend"
    playwright_cli = frontend_root / "node_modules" / "@playwright" / "test" / "cli.js"
    node = shutil.which("node")
    assert (
        node is not None
    ), "Node must be available in the prepared frontend toolchain."
    assert (
        playwright_cli.is_file()
    ), "Install frontend dependencies through the configured toolchain."

    env = os.environ.copy()
    env["CANVAS_RUNTIME_MCP_URL"] = f"http://127.0.0.1:{action_server_process.port}/mcp"
    env["CANVAS_TEMPLATE_RESOURCE_PATH"] = str(project / "canvas.html")
    env["CANVAS_TEMPLATE_TEST_OUTPUT"] = str(tmp_path / "playwright-output")
    browser = shutil.which("chromium")
    if browser:
        env["CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = browser
    subprocess.run(
        [
            node,
            str(playwright_cli),
            "test",
            "--config",
            str(frontend_root / "playwright.canvas-template.config.ts"),
        ],
        cwd=frontend_root,
        env=env,
        check=True,
        timeout=180,
    )
