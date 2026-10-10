"""Acceptance checks for the packaged Canvas Query template."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
import zipfile
from copy import deepcopy
from pathlib import Path

import jsonschema
import psutil
import pytest
from action_server_tests.fixtures import actions_server_run
from mcp.types import TextResourceContents

from actions.server._selftest import ActionServerProcess

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
EMBEDDED_TEMPLATES = REPOSITORY_ROOT / "action_server/src/actions/server/templates"


def _run_owned_process_tree(
    command: list[str], *, cwd: Path, env: dict[str, str], timeout: float
) -> subprocess.CompletedProcess[str]:
    """Run a command and terminate only its captured descendants on timeout."""
    from actions.server._common.process import (
        force_kill_process_tree_until,
        snapshot_process_descendants,
    )

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=(
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        ),
        start_new_session=os.name != "nt",
    )
    descendants: list[psutil.Process] = []
    descendant_identities: set[tuple[int, float]] = set()
    snapshot_complete = True

    def capture_descendants() -> None:
        nonlocal snapshot_complete
        try:
            captured = snapshot_process_descendants(process.pid)
        except Exception:
            snapshot_complete = False
            return
        snapshot_complete = True
        for child in captured:
            identity = (child.pid, child.create_time())
            if identity not in descendant_identities:
                descendant_identities.add(identity)
                descendants.append(child)

    try:
        capture_descendants()
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                stdout, stderr = process.communicate(timeout=min(0.05, remaining))
                break
            except subprocess.TimeoutExpired as error:
                capture_descendants()
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(
                        command, timeout, output=error.output, stderr=error.stderr
                    ) from None
        completed = subprocess.CompletedProcess(
            command, process.returncode, stdout, stderr
        )
        if completed.returncode:
            raise subprocess.CalledProcessError(
                completed.returncode, command, completed.stdout, completed.stderr
            )
        return completed
    finally:
        if os.name != "nt":
            # Once the leader has exited, its numeric process-group ID could
            # be reused. Signal the group only while its leader is still ours,
            # or while a captured, identity-checked descendant proves that the
            # original session still exists.
            # Do not poll first: Popen.returncode stays None until this owner
            # reaps its leader, which keeps its private group ID authoritative
            # for an immediate-owner-exit timeout.
            owns_live_group = process.returncode is None
            if not owns_live_group:
                for child in descendants:
                    try:
                        current = psutil.Process(child.pid)
                        if (
                            current.create_time() == child.create_time()
                            and os.getpgid(child.pid) == process.pid
                        ):
                            owns_live_group = True
                            break
                    except (ProcessLookupError, psutil.NoSuchProcess):
                        continue
            if owns_live_group:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if process.poll() is None:
            capture_descendants()
        if process.poll() is None or descendants:
            cleanup = force_kill_process_tree_until(
                process,
                descendants,
                time.monotonic() + 5,
                snapshot_complete_before_call=snapshot_complete,
            )
            if not cleanup.wrapper_reaped or cleanup.live_descendant_pids:
                raise RuntimeError(f"Could not stop owned command tree: {cleanup!r}")
            process.communicate(timeout=1)


@pytest.mark.skipif(os.name == "nt", reason="POSIX session cleanup is Linux-gated")
def test_owned_process_timeout_stops_its_descendant(tmp_path: Path) -> None:
    child_pid_file = tmp_path / "child.pid"
    script = (
        "import os, subprocess, sys, time; time.sleep(0.1); "
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
        "open(os.environ['CHILD_PID_FILE'], 'w').write(str(child.pid))"
    )
    env = os.environ.copy()
    env["CHILD_PID_FILE"] = str(child_pid_file)
    with pytest.raises(subprocess.TimeoutExpired):
        _run_owned_process_tree(
            [sys.executable, "-c", script], cwd=tmp_path, env=env, timeout=0.5
        )

    child_pid = int(child_pid_file.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 1
    while True:
        try:
            child = psutil.Process(child_pid)
            if child.status() == psutil.STATUS_ZOMBIE:
                break
        except psutil.NoSuchProcess:
            break
        if time.monotonic() >= deadline:
            pytest.fail(
                "The owned child remained live after its parent was cleaned up."
            )
        time.sleep(0.01)


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
    os.environ.get("ACTIONS_CANVAS_TEMPLATE_CANDIDATE_ACCEPTANCE") != "1",
    reason=(
        "Set ACTIONS_CANVAS_TEMPLATE_CANDIDATE_ACCEPTANCE=1 for the "
        "candidate-source Runtime/browser gate."
    ),
)
def test_canvas_template_candidate_source_runs_through_runtime_and_real_browser(
    action_server_process: ActionServerProcess, tmp_path: Path
) -> None:
    """Exercise the template against an exact source wheel without changing its bundle."""
    if os.name == "nt":
        pytest.skip("The candidate-source browser gate is hosted on POSIX Linux.")
    repository_root = Path(__file__).resolve().parents[4]
    frontend_root = repository_root / "action_server" / "frontend"
    source_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    source_tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    source_blobs = {
        path: subprocess.run(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        for path in (
            "actions/pyproject.toml",
            "actions/src/actions/mcp/__init__.py",
            "actions/src/actions/mcp/_metadata.py",
        )
    }
    source_status = subprocess.run(
        ["git", "status", "--porcelain", "--", "actions"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert (
        not source_status
    ), "The Core package source must match the recorded checkout before wheel build."

    candidate_wheel_dir = tmp_path / "candidate-core-wheel"
    candidate_wheel_dir.mkdir()
    build_env = os.environ.copy()
    build_env["UV_CACHE_DIR"] = str(tmp_path / "uv-cache")
    build_env["TMPDIR"] = str(tmp_path)
    subprocess.run(
        [
            shutil.which("uv") or "uv",
            "build",
            "--wheel",
            "--out-dir",
            str(candidate_wheel_dir),
            str(repository_root / "actions"),
        ],
        cwd=repository_root,
        env=build_env,
        check=True,
        timeout=120,
    )
    candidate_wheel = next(candidate_wheel_dir.glob("actions_core-*.whl"))
    candidate_wheel_sha256 = hashlib.sha256(candidate_wheel.read_bytes()).hexdigest()
    with zipfile.ZipFile(candidate_wheel) as wheel:
        metadata_name = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata_lines = wheel.read(metadata_name).decode("utf-8").splitlines()
        wheel_api_sources: dict[str, dict[str, str]] = {}
        for source_path in (
            "actions/src/actions/mcp/__init__.py",
            "actions/src/actions/mcp/_metadata.py",
        ):
            wheel_path = source_path.removeprefix("actions/src/")
            source_bytes = wheel.read(wheel_path)
            git_blob = hashlib.sha1(
                f"blob {len(source_bytes)}\0".encode("ascii") + source_bytes
            ).hexdigest()
            assert git_blob == source_blobs[source_path]
            wheel_api_sources[wheel_path] = {
                "sha256": hashlib.sha256(source_bytes).hexdigest(),
                "git_blob": git_blob,
            }
    candidate_version = next(
        line.partition(": ")[2]
        for line in metadata_lines
        if line.startswith("Version: ")
    )

    project = _create_project(tmp_path, "canvas-query-candidate-runtime")
    original_package = (project / "package.yaml").read_text(encoding="utf-8")
    with zipfile.ZipFile(EMBEDDED_TEMPLATES / "zips/canvas-query.zip") as bundle:
        bundled_package = bundle.read("package.yaml").decode("utf-8")
    assert original_package == bundled_package
    assert original_package.count("actions-core=1.0.3") == 1
    if os.name == "nt":
        quoted_wheel_path = subprocess.list2cmdline([str(candidate_wheel)])
    else:
        quoted_wheel_path = shlex.quote(str(candidate_wheel))
    candidate_package = original_package.replace(
        "actions-core=1.0.3", "actions-core=1.0.2"
    )
    candidate_package += (
        "\npost-install:\n"
        "  - python -m pip install --no-deps --force-reinstall "
        f"{quoted_wheel_path}\n"
    )
    (project / "package.yaml").write_text(candidate_package, encoding="utf-8")

    action_source = """
import hashlib
import json
import sys
from importlib.metadata import distribution
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

from actions.mcp import tool

EXPECTED_WHEEL = Path(__EXPECTED_WHEEL__)
EXPECTED_SHA256 = __EXPECTED_SHA256__
EXPECTED_VERSION = __EXPECTED_VERSION__
SOURCE_REVISION = __SOURCE_REVISION__
SOURCE_TREE = __SOURCE_TREE__
SOURCE_BLOBS = __SOURCE_BLOBS__
EXPECTED_API_SOURCES = __EXPECTED_API_SOURCES__

@tool
def canvas_candidate_core_provenance() -> dict[str, object]:
    import actions.mcp as mcp_module
    import actions.mcp._metadata as metadata_module

    core = distribution("actions-core")
    actions_module = Path(__import__("actions").__file__).resolve()
    installed_files = {
        Path(core.locate_file(item)).resolve() for item in (core.files or [])
    }
    if actions_module not in installed_files:
        raise AssertionError("worker actions module is not owned by actions-core")
    raw_direct_url = core.read_text("direct_url.json")
    if not raw_direct_url:
        raise AssertionError("worker actions-core has no direct_url.json")
    direct_url = json.loads(raw_direct_url)
    source = urlsplit(direct_url.get("url", ""))
    if source.scheme != "file" or source.netloc not in {"", "localhost"}:
        raise AssertionError("worker actions-core was not installed from a local wheel")
    installed_wheel = Path(url2pathname(source.path)).resolve()
    archive = direct_url.get("archive_info", {})
    installed_sha256 = archive.get("hashes", {}).get("sha256")
    if installed_sha256 is None:
        hash_value = archive.get("hash", "")
        if hash_value.startswith("sha256="):
            installed_sha256 = hash_value.removeprefix("sha256=")
    installed_wheel_sha256 = hashlib.sha256(installed_wheel.read_bytes()).hexdigest()
    if installed_wheel != EXPECTED_WHEEL.resolve():
        raise AssertionError("worker direct_url differs from the candidate wheel")
    if installed_sha256 != EXPECTED_SHA256 or installed_wheel_sha256 != EXPECTED_SHA256:
        raise AssertionError("worker wheel SHA-256 differs from the candidate")
    if core.version != EXPECTED_VERSION:
        raise AssertionError("worker Core metadata differs from candidate metadata")
    api_modules = {
        "actions.mcp": mcp_module,
        "actions.mcp._metadata": metadata_module,
    }
    measured_api_sources = {}
    for module_name, module in api_modules.items():
        module_path = Path(module.__file__).resolve()
        wheel_relative_path = {
            "actions.mcp": "actions/mcp/__init__.py",
            "actions.mcp._metadata": "actions/mcp/_metadata.py",
        }[module_name]
        expected_source = EXPECTED_API_SOURCES[wheel_relative_path]
        distribution_path = Path(core.locate_file(wheel_relative_path)).resolve()
        if module_path != distribution_path:
            raise AssertionError(f"{module_name} did not load from actions-core")
        actual_bytes = module_path.read_bytes()
        module_sha256 = hashlib.sha256(actual_bytes).hexdigest()
        if module_sha256 != expected_source["sha256"]:
            raise AssertionError(f"{module_name} bytes differ from the candidate wheel")
        measured_api_sources[module_name] = {
            "path": str(module_path),
            "sha256": module_sha256,
            "git_blob": expected_source["git_blob"],
        }
    return {
        "worker_prefix": sys.prefix,
        "actions_module": str(actions_module),
        "actions_core_version": core.version,
        "direct_url_wheel": str(installed_wheel),
        "wheel_sha256": installed_wheel_sha256,
        "source_revision": SOURCE_REVISION,
        "source_tree": SOURCE_TREE,
        "source_blobs": SOURCE_BLOBS,
        "api_modules": measured_api_sources,
    }
"""
    substitutions = {
        "__EXPECTED_WHEEL__": repr(str(candidate_wheel)),
        "__EXPECTED_SHA256__": repr(candidate_wheel_sha256),
        "__EXPECTED_VERSION__": repr(candidate_version),
        "__SOURCE_REVISION__": repr(source_revision),
        "__SOURCE_TREE__": repr(source_tree),
        "__SOURCE_BLOBS__": repr(source_blobs),
        "__EXPECTED_API_SOURCES__": repr(wheel_api_sources),
    }
    for placeholder, value in substitutions.items():
        action_source = action_source.replace(placeholder, value)
    (project / "canvas_candidate_core.py").write_text(action_source, encoding="utf-8")

    assert "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE" not in os.environ, (
        "This source acceptance requires ActionServerProcess to launch the "
        "checkout's Python Runtime module."
    )
    runtime_env = os.environ.copy()
    runtime_env["PYTHONPATH"] = str(repository_root / "action_server/src")
    runtime_env.pop("PYTHONHOME", None)
    runtime_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import actions.server; print(actions.server.__file__)",
        ],
        cwd=project,
        env=runtime_env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    expected_runtime_origin = (
        repository_root / "action_server/src/actions/server/__init__.py"
    ).resolve()
    assert Path(runtime_probe).resolve() == expected_runtime_origin

    action_server_process.start(
        cwd=project,
        db_file="server.db",
        actions_sync=True,
        timeout=120,
        env=runtime_env,
    )
    worker_provenance: dict[str, object] = {}

    async def check_runtime_contract() -> None:
        async with action_server_process.mcp_client() as session:
            listed = await session.list_tools()
            search = next(
                tool for tool in listed.tools if tool.name == "canvas_fixture_search"
            )
            assert search.meta is not None
            assert search.meta["ui"] == {
                "resourceUri": "ui://action-canvas/v1/canvas.html?query-fixture=0.1",
                "visibility": ["model", "app"],
            }
            resource = await session.read_resource(
                "ui://action-canvas/v1/canvas.html?query-fixture=0.1"
            )
            content = resource.contents[0]
            assert isinstance(content, TextResourceContents)
            assert content.mime_type == "text/html;profile=mcp-app"
            assert content.text == (project / "canvas.html").read_text(encoding="utf-8")
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
                "artifact": None,
                "error": None,
            }
            provenance = await session.call_tool("canvas_candidate_core_provenance", {})
            assert provenance.structured_content is not None
            worker_provenance.update(provenance.structured_content)

    from action_server_tests.fixtures import run_async_in_new_thread

    assert run_async_in_new_thread(check_runtime_contract) is None
    assert worker_provenance["wheel_sha256"] == candidate_wheel_sha256
    assert worker_provenance["source_revision"] == source_revision
    assert worker_provenance["source_tree"] == source_tree
    assert worker_provenance["source_blobs"] == source_blobs
    measured_api_modules = worker_provenance.get("api_modules")
    assert isinstance(measured_api_modules, dict)
    for module_name, wheel_path in (
        ("actions.mcp", "actions/mcp/__init__.py"),
        ("actions.mcp._metadata", "actions/mcp/_metadata.py"),
    ):
        measured = measured_api_modules.get(module_name)
        assert isinstance(measured, dict)
        assert measured["sha256"] == wheel_api_sources[wheel_path]["sha256"]
        assert measured["git_blob"] == wheel_api_sources[wheel_path]["git_blob"]
        module_path = Path(str(measured["path"]))
        assert module_path.is_absolute()
        assert module_path.as_posix().endswith(wheel_path)

    server_args = action_server_process.process._args
    assert server_args[:3] == [sys.executable, "-m", "actions.server"]
    runtime_module_sha256 = hashlib.sha256(
        expected_runtime_origin.read_bytes()
    ).hexdigest()

    node = shutil.which("node")
    playwright_cli = frontend_root / "node_modules" / "@playwright" / "test" / "cli.js"
    assert (
        node is not None
    ), "Node must be available in the prepared frontend toolchain."
    assert (
        playwright_cli.is_file()
    ), "The configured frontend toolchain must provide Playwright."
    browser = shutil.which("chromium")
    assert (
        browser is not None
    ), "Set up a real browser executable in the hosted acceptance job."
    browser_path = Path(browser).resolve()
    browser_version = subprocess.run(
        [str(browser_path), "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    browser_sha256 = hashlib.sha256(browser_path.read_bytes()).hexdigest()
    env = os.environ.copy()
    env["CANVAS_RUNTIME_MCP_URL"] = f"http://127.0.0.1:{action_server_process.port}/mcp"
    env["CANVAS_TEMPLATE_RESOURCE_PATH"] = str(project / "canvas.html")
    env["CANVAS_TEMPLATE_TEST_OUTPUT"] = str(tmp_path / "candidate-playwright-output")
    env["CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = str(browser_path)
    _run_owned_process_tree(
        [
            node,
            str(playwright_cli),
            "test",
            "--config",
            str(frontend_root / "playwright.canvas-template.config.ts"),
        ],
        cwd=frontend_root,
        env=env,
        timeout=180,
    )

    template_zip = EMBEDDED_TEMPLATES / "zips/canvas-query.zip"
    receipt = {
        "scope": "candidate-source Runtime/browser acceptance only",
        "template_zip_sha256": hashlib.sha256(template_zip.read_bytes()).hexdigest(),
        "built_resource_sha256": hashlib.sha256(
            (project / "canvas.html").read_bytes()
        ).hexdigest(),
        "production_package_manifest_sha256": hashlib.sha256(
            original_package.encode("utf-8")
        ).hexdigest(),
        "candidate_acceptance_manifest_sha256": hashlib.sha256(
            candidate_package.encode("utf-8")
        ).hexdigest(),
        "candidate_registry_base": "actions-core=1.0.2",
        "candidate_core": {
            "runtime_module_origin": str(expected_runtime_origin),
            "runtime_module_sha256": runtime_module_sha256,
            "runtime_process_args": server_args,
            "source_revision": source_revision,
            "source_tree": source_tree,
            "source_blobs": source_blobs,
            "wheel_api_sources": wheel_api_sources,
            "wheel_path": str(candidate_wheel),
            "version": candidate_version,
            "sha256": candidate_wheel_sha256,
            "worker": worker_provenance,
        },
        "runtime_calls": [
            "canvas_fixture_search",
            "canvas_candidate_core_provenance",
        ],
        "browser": {
            "status": "passed",
            "path": str(browser_path),
            "version": browser_version,
            "sha256": browser_sha256,
        },
        "limits": [
            "The production template's published actions-core=1.0.3 gate is separate and not run here.",
            "artifact:null is a partial result and does not prove authorized artifact retrieval.",
            "This local Runtime/browser gate does not claim ChatGPT rendering.",
        ],
    }
    (tmp_path / "canvas-template-candidate-source-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


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
            assert isinstance(content, TextResourceContents)
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
