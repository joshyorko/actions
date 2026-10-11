import asyncio
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
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


# An external immutable acceptance runner may supply subprocess ownership only.
# The hook receives the exact command/cwd/env/timeout and returns CompletedProcess.
# It must not patch Runtime/Core behavior or any expectation in this test.
CANVAS_OWNED_RUNNER: Callable[..., subprocess.CompletedProcess[str]] | None = None
PUBLISHED_CORE_WHEEL_SHA256 = (
    "8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265"
)
PUBLISHED_CORE_MODULE_SHA256 = {
    "actions": "790b5e45f1a570f4d209879a47007ce94b73aab76c522bd6400867168726b0d2",
    "actions.mcp": "c944de3b044a232143e66edd85ebd342b81b49cd100221689e22908d0dd5f365",
    "actions.mcp._metadata": "c5750e654cb3c1e057705d80e65c4f6a935a3d81e46450d6dbf68d37f45cb48c",
}


def _canvas_core_mode() -> str:
    mode = os.environ.get("ACTIONS_CANVAS_CORE_MODE", "candidate")
    assert mode in {"candidate", "published"}, "Unknown Canvas Core mode"
    if mode == "published":
        assert callable(CANVAS_OWNED_RUNNER), "Public mode requires an owned runner"
    return mode


def _canvas_command(
    command: list[str], *, cwd: Path, env: dict[str, str], timeout: float, mode: str
) -> subprocess.CompletedProcess[str]:
    if mode == "published":
        assert callable(CANVAS_OWNED_RUNNER), "Public mode requires an owned runner"
        completed = CANVAS_OWNED_RUNNER(command, cwd=cwd, env=env, timeout=timeout)
    else:
        completed = subprocess.run(
            command, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True
        )
    assert completed.args == command, "Owned runner changed command identity"
    # Preserve both output streams before enforcing the command's success contract.
    if completed.stdout:
        print(completed.stdout)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr)
    completed.check_returncode()
    return completed


def _prepare_canvas_core(
    repository_root: Path, package_root: Path, build_env: dict[str, str], mode: str
) -> dict[str, Any]:
    assert mode in {"candidate", "published"}
    if mode == "published":
        (package_root / "package.yaml").write_text(
            "spec-version: v2\nname: Canvas Runtime bridge acceptance\n"
            "description: Isolated fixture using published Core 1.0.3.\n"
            "version: 0.0.1\ndependencies:\n  conda-forge:\n"
            "    - python=3.12\n    - uv=0.9.26\n  pypi:\n    - actions-core=1.0.3\n",
            encoding="utf-8",
        )
        return {
            "mode": "published",
            "declared_version": "1.0.3",
            "independently_verified_registry_wheel_sha256": PUBLISHED_CORE_WHEEL_SHA256,
            "measured_members": list(PUBLISHED_CORE_MODULE_SHA256),
            "whole_wheel_authenticated": False,
            "cold_registry_acquisition": False,
        }
    candidate_core_wheel_dir = package_root / "candidate-core"
    candidate_core_wheel_dir.mkdir()
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
    candidate_core_wheel_sha256 = hashlib.sha256(
        candidate_core_wheel.read_bytes()
    ).hexdigest()
    if os.name == "nt":
        quoted_wheel_path = subprocess.list2cmdline([str(candidate_core_wheel)])
    else:
        quoted_wheel_path = shlex.quote(str(candidate_core_wheel))
    package_yaml = package_root / "package.yaml"
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
    return {
        "mode": "candidate",
        "path": str(candidate_core_wheel),
        "sha256": candidate_core_wheel_sha256,
    }


PUBLISHED_CORE_PROBE = """from importlib.metadata import distribution
import hashlib
from pathlib import Path
import sys

import actions
import actions.mcp
import actions.mcp._metadata

PUBLISHED_CORE_WHEEL_SHA256 = (
    "8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265"
)
PUBLISHED_CORE_MODULE_SHA256 = {
    "actions": "790b5e45f1a570f4d209879a47007ce94b73aab76c522bd6400867168726b0d2",
    "actions.mcp": "c944de3b044a232143e66edd85ebd342b81b49cd100221689e22908d0dd5f365",
    "actions.mcp._metadata": (
        "c5750e654cb3c1e057705d80e65c4f6a935a3d81e46450d6dbf68d37f45cb48c"
    ),
}


@mcp.tool(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
def canvas_fixture_worker_provenance() -> dict[str, object]:
    core = distribution("actions-core")
    modules = {
        "actions": Path(actions.__file__).resolve(),
        "actions.mcp": Path(actions.mcp.__file__).resolve(),
        "actions.mcp._metadata": Path(actions.mcp._metadata.__file__).resolve(),
    }
    installed_files = {
        Path(core.locate_file(item)).resolve() for item in (core.files or [])
    }
    if any(module not in installed_files for module in modules.values()):
        raise AssertionError("an Actions module is not owned by installed actions-core")
    prefix = Path(sys.prefix).resolve()
    if any(not module.is_relative_to(prefix) for module in modules.values()):
        raise AssertionError("an Actions module is outside the managed environment")
    module_hashes = {
        name: hashlib.sha256(module.read_bytes()).hexdigest()
        for name, module in modules.items()
    }
    if core.version != "1.0.3" or module_hashes != PUBLISHED_CORE_MODULE_SHA256:
        raise AssertionError(
            "installed actions-core differs from the independently verified "
            f"published wheel {PUBLISHED_CORE_WHEEL_SHA256}"
        )
    return {
        "version": core.version,
        "worker_prefix": str(prefix),
        "module_hashes": module_hashes,
        "modules": {name: str(path) for name, path in modules.items()},
    }

"""

CANDIDATE_CORE_PROBE = """@mcp.tool(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
def canvas_fixture_worker_provenance() -> dict[str, str]:
    core_distribution = distribution("actions-core")
    actions_module = Path(__import__("actions").__file__).resolve()
    installed_files = {
        Path(core_distribution.locate_file(file)).resolve()
        for file in (core_distribution.files or [])
    }
    if actions_module not in installed_files:
        raise AssertionError("worker actions module is not owned by actions-core")

    direct_url_value = core_distribution.read_text("direct_url.json")
    if not direct_url_value:
        raise AssertionError("worker actions-core has no direct_url.json")
    direct_url = json.loads(direct_url_value)
    source = urlsplit(direct_url.get("url", ""))
    if source.scheme != "file" or source.netloc not in {"", "localhost"}:
        raise AssertionError("worker actions-core was not installed from a local wheel")
    installed_wheel = Path(url2pathname(source.path)).resolve()
    if installed_wheel != EXPECTED_CORE_WHEEL.resolve():
        raise AssertionError("worker actions-core direct_url differs from the candidate wheel")

    archive = direct_url.get("archive_info", {})
    installed_sha256 = archive.get("hashes", {}).get("sha256")
    if installed_sha256 is None:
        hash_value = archive.get("hash", "")
        if hash_value.startswith("sha256="):
            installed_sha256 = hash_value.removeprefix("sha256=")
    candidate_sha256 = hashlib.sha256(installed_wheel.read_bytes()).hexdigest()
    if installed_sha256 != EXPECTED_CORE_WHEEL_SHA256 or candidate_sha256 != EXPECTED_CORE_WHEEL_SHA256:
        raise AssertionError("worker actions-core wheel SHA-256 differs from the candidate")
    return {
        "worker_prefix": sys.prefix,
        "actions_module": str(actions_module),
        "actions_core_version": core_distribution.version,
        "direct_url_wheel": str(installed_wheel),
        "wheel_sha256": candidate_sha256,
    }
"""


def _canvas_worker_probe(core: dict[str, Any]) -> str:
    if core["mode"] == "published":
        return PUBLISHED_CORE_PROBE
    return (
        "EXPECTED_CORE_WHEEL = Path(" + repr(core["path"]) + ")\n"
        "EXPECTED_CORE_WHEEL_SHA256 = "
        + repr(core["sha256"])
        + "\n"
        + CANDIDATE_CORE_PROBE
    )


def _assert_canvas_playwright_report(report: dict[str, Any]) -> None:
    specs: list[dict[str, Any]] = []

    def collect(suites: list[dict[str, Any]]) -> None:
        for suite in suites:
            specs.extend(suite.get("specs", []))
            collect(suite.get("suites", []))

    collect(report.get("suites", []))
    assert not report.get("errors"), "Playwright reported errors"
    stats = report["stats"]
    assert stats["expected"] == 1
    assert stats["unexpected"] == stats["skipped"] == stats["flaky"] == 0
    assert len(specs) == 1, "Expected exactly one Canvas browser case"
    assert specs[0]["title"] == "official bridge renders a real Runtime Action result"
    tests = specs[0]["tests"]
    assert len(tests) == 1 and len(tests[0]["results"]) == 1
    assert (
        tests[0]["results"][0]["status"] == "passed"
    ), "Browser case did not pass without skips/retries"


def _run_canvas_browser(
    frontend_root: Path, runtime_url: str, mode: str
) -> dict[str, Any]:
    env = os.environ.copy()
    selected = env.get("CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if mode == "published":
        assert selected, "Public mode requires an explicit Chromium executable"
    if not selected:
        selected = shutil.which("chromium")
    browser_path = Path(selected).resolve(strict=True) if selected else None
    if browser_path:
        assert browser_path.is_file() and os.access(browser_path, os.X_OK)
        env["CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = str(browser_path)
    env["CANVAS_RUNTIME_MCP_URL"] = runtime_url
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", 0))
        env["CANVAS_HARNESS_PORT"] = str(port_probe.getsockname()[1])
    if mode == "candidate":
        _canvas_command(
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
            timeout=180,
            mode=mode,
        )
        version = (
            _canvas_command(
                [str(browser_path), "--version"],
                cwd=frontend_root,
                env=env,
                timeout=15,
                mode=mode,
            ).stdout.strip()
            if browser_path
            else "Playwright-pinned Chromium"
        )
        return {
            "executable": str(browser_path) if browser_path else None,
            "version": version,
            "sha256": hashlib.sha256(browser_path.read_bytes()).hexdigest()
            if browser_path
            else "not-recorded",
            "selection": "explicit"
            if selected == os.environ.get("CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
            and selected
            else "system-or-managed",
        }
    assert browser_path is not None
    cli = frontend_root / "node_modules/@playwright/test/cli.js"
    node = shutil.which("node")
    assert node and cli.is_file(), "Use prepared Node/Playwright"
    lock_path = frontend_root / "package-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    version = json.loads((cli.parent / "package.json").read_text(encoding="utf-8"))[
        "version"
    ]
    assert version == lock["packages"]["node_modules/@playwright/test"]["version"]
    browser_sha256 = hashlib.sha256(browser_path.read_bytes()).hexdigest()
    browser_version = _canvas_command(
        [str(browser_path), "--version"],
        cwd=frontend_root,
        env=env,
        timeout=10,
        mode=mode,
    ).stdout.strip()
    assert browser_version
    with tempfile.TemporaryDirectory(
        prefix="cv305-", dir="/tmp" if os.name != "nt" else None
    ) as browser_temp:
        root = Path(browser_temp)
        if os.name != "nt":
            root.chmod(0o700)
        for key in ("TMPDIR", "TMP", "TEMP"):
            env[key] = str(root)
        completed = _canvas_command(
            [
                node,
                str(cli),
                "test",
                "--config",
                str(frontend_root / "playwright.canvas-harness.config.ts"),
                "--grep",
                r"^\s*host-harness\.spec\.ts official bridge renders a real Runtime Action result$",
                "--workers",
                "1",
                "--reporter",
                "json",
            ],
            cwd=frontend_root,
            env=env,
            timeout=180,
            mode=mode,
        )
        _assert_canvas_playwright_report(json.loads(completed.stdout))
    assert not root.exists()
    assert hashlib.sha256(browser_path.read_bytes()).hexdigest() == browser_sha256
    return {
        "status": "passed",
        "selection": "explicit",
        "path": str(browser_path),
        "executable": str(browser_path),
        "sha256": browser_sha256,
        "version": browser_version,
        "playwright_version": version,
        "frontend_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "temporary_root": str(root),
        "temporary_root_removed": True,
    }


@pytest.mark.integration_test
@pytest.mark.skipif(
    os.environ.get("ACTIONS_CANVAS_RUNTIME_ACCEPTANCE") != "1",
    reason="Set ACTIONS_CANVAS_RUNTIME_ACCEPTANCE=1 to run the RCC/browser acceptance.",
)
def test_canvas_view_calls_public_action_through_runtime_bridge(
    action_server_process: ActionServerProcess, tmp_path, tmp_path_factory
) -> None:
    mode = _canvas_core_mode()
    repository_root = Path(__file__).resolve().parents[4]
    frontend_root = repository_root / "action_server" / "frontend"
    # Action Server snapshots tmp_path as the action package below. uv's cache
    # contains directory symlinks, so keep cache and temporary build state in a
    # unique sibling directory rather than inside the synchronized package.
    build_temp_dir = tmp_path_factory.mktemp("canvas-runtime-build")
    build_env = os.environ.copy()
    build_env["UV_CACHE_DIR"] = str(build_temp_dir / "uv-cache")
    build_env["TMPDIR"] = str(build_temp_dir)
    core = _prepare_canvas_core(repository_root, tmp_path, build_env, mode)
    _canvas_command(
        ["npm", "run", "build:canvas"],
        cwd=frontend_root,
        env=build_env,
        timeout=120,
        mode=mode,
    )
    canvas_html = (frontend_root / "dist-canvas" / "index.html").read_text(
        encoding="utf-8"
    )
    (tmp_path / "canvas.html").write_text(canvas_html, encoding="utf-8")
    action_source = """
import hashlib
import json
import sys
from importlib.metadata import distribution
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

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


"""
    action_source += _canvas_worker_probe(core)
    (tmp_path / "canvas_actions.py").write_text(action_source, encoding="utf-8")

    action_server_process.start(
        cwd=tmp_path,
        db_file="server.db",
        actions_sync=True,
        timeout=120,
    )
    runtime_call_observations: list[dict[str, str]] = []
    worker_provenance: dict[str, str] = {}

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
            runtime_call_observations.append(
                {
                    "caller": "python-mcp-client",
                    "tool": "canvas_fixture_search",
                    "result": "passed",
                }
            )

            artifact_status = await session.call_tool(
                "canvas_fixture_artifact_status",
                {"handle": "art_7Wk3qN9pL2xD5mR8sV4cY1"},
            )
            assert artifact_status.structured_content == {"status": "ready"}
            runtime_call_observations.append(
                {
                    "caller": "python-mcp-client",
                    "tool": "canvas_fixture_artifact_status",
                    "result": "passed",
                }
            )

            provenance = await session.call_tool("canvas_fixture_worker_provenance", {})
            assert provenance.structured_content is not None
            worker_provenance.update(provenance.structured_content)
            if mode == "candidate":
                assert worker_provenance["wheel_sha256"] == core["sha256"]
            else:
                assert worker_provenance["version"] == "1.0.3"
                assert (
                    worker_provenance["module_hashes"] == PUBLISHED_CORE_MODULE_SHA256
                )
            assert Path(worker_provenance["worker_prefix"]).is_dir()
            runtime_call_observations.append(
                {
                    "caller": "python-mcp-client",
                    "tool": "canvas_fixture_worker_provenance",
                    "result": "passed",
                }
            )

    assert run_async_in_new_thread(partial(check_runtime_contract)) is None

    browser = _run_canvas_browser(
        frontend_root, f"http://127.0.0.1:{action_server_process.port}/mcp", mode
    )
    runtime_call_observations.extend(
        [
            {
                "caller": "playwright-browser",
                "tool": "canvas_fixture_search",
                "result": "passed",
            },
            {
                "caller": "playwright-browser",
                "tool": "canvas_fixture_artifact_status",
                "result": "passed",
            },
        ]
    )
    action_call_counts = {
        "canvas_fixture_search": 2,
        "canvas_fixture_artifact_status": 2,
        "canvas_fixture_worker_provenance": 1,
    }
    action_names = tuple(action_call_counts)
    placeholders = ", ".join("?" for _ in action_names)
    with sqlite3.connect(action_server_process.datadir / "server.db") as connection:
        run_records = connection.execute(
            f"""
            SELECT run.id, run.status, action.name
            FROM run
            JOIN action ON action.id = run.action_id
            WHERE action.name IN ({placeholders})
            ORDER BY run.numbered_id
            """,
            action_names,
        ).fetchall()
    recorded_counts = {name: 0 for name in action_call_counts}
    for _, status, action_name in run_records:
        assert (
            status == 2
        ), f"Expected successful Runtime Run for {action_name}: {status}"
        recorded_counts[action_name] += 1
    assert recorded_counts == action_call_counts
    persisted_run_records = [
        {
            "run_id": run_id,
            "status": "passed",
            "status_code": status,
            "action_name": action_name,
        }
        for run_id, status, action_name in run_records
    ]
    receipt_path = tmp_path / "canvas-bridge-acceptance-receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "core_mode": mode,
                "package_manifest_sha256": hashlib.sha256(
                    (tmp_path / "package.yaml").read_bytes()
                ).hexdigest(),
                "action_source_sha256": hashlib.sha256(
                    (tmp_path / "canvas_actions.py").read_bytes()
                ).hexdigest(),
                **(
                    {"actions_core_wheel": core}
                    if mode == "candidate"
                    else {"published_core": core}
                ),
                "worker": worker_provenance,
                "canvas_resource": {
                    "uri": CANVAS_RESOURCE_URI,
                    "mime_type": "text/html;profile=mcp-app",
                    "sha256": hashlib.sha256(canvas_html.encode("utf-8")).hexdigest(),
                },
                "browser": browser,
                "limits": [
                    "Fixture artifact status is not real artifact resolution.",
                    "Public Core provenance measures three members, not full-wheel authentication or cold acquisition.",
                    "Native source and owned cleanup are admitted separately by the immutable runner; no production host/ChatGPT proof.",
                ],
                "cache": {
                    "source_root": str(tmp_path.resolve()),
                    "build_root": str(build_temp_dir.resolve()),
                    "uv_cache": build_env["UV_CACHE_DIR"],
                    "outside_synchronized_package": not build_temp_dir.resolve().is_relative_to(
                        tmp_path.resolve()
                    ),
                },
                "runtime_call_observations": runtime_call_observations,
                "persisted_run_records": persisted_run_records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
