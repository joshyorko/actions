import ast
import json
import sqlite3
from pathlib import Path

import pytest


@pytest.mark.integration_test
def test_binary_preserves_cli_usage_exit_code():
    from actions.server._selftest import actions_server_run

    result = actions_server_run(["devenv", "task"], returncode=2)
    assert "usage: action-server devenv task" in result.stderr
    assert "the following arguments are required: task_names" in result.stderr


def get_internal_version_location(version: str) -> Path:
    import os
    import sys

    if sys.platform == "win32":
        app_data_dir = os.getenv("LOCALAPPDATA")
        if not app_data_dir:
            raise RuntimeError("LOCALAPPDATA environment variable is not set")
        target_path = os.path.join(
            app_data_dir, "actions", "bin", "action-server", "internal"
        )
    else:
        home_dir = os.path.expanduser("~")
        target_path = os.path.join(
            home_dir, ".actions", "bin", "action-server", "internal"
        )

    return Path(target_path) / version


def test_binary_spec_includes_termcolor_hidden_import():
    spec_path = Path(__file__).parents[2] / "action-server.spec"

    assert '"termcolor",' in spec_path.read_text()


def test_binary_spec_collects_postgresql_runtime_modules():
    spec = (Path(__file__).parents[2] / "action-server.spec").read_text()

    assert 'collect_submodules("psycopg")' in spec
    assert 'collect_submodules("psycopg_binary")' in spec
    assert 'collect_dynamic_libs("psycopg_binary")' in spec


def test_binary_spec_collects_sqlite_runtime_modules():
    spec = (Path(__file__).parents[2] / "action-server.spec").read_text()

    assert '"sqlite3",' in spec
    assert '"_sqlite3",' in spec


def test_binary_spec_collects_fastapi_runtime_module():
    spec = (Path(__file__).parents[2] / "action-server.spec").read_text()

    assert '"fastapi",' in spec
    assert 'collect_submodules("fastapi")' in spec
    assert 'collect_submodules("psutil")' in spec
    assert 'collect_submodules("actions")' in spec
    assert 'collect_submodules("starlette")' in spec
    assert 'collect_submodules("mcp")' in spec


def test_binary_spec_collects_runtime_server_module():
    spec = (Path(__file__).parents[2] / "action-server.spec").read_text()

    assert '"uvicorn",' in spec


def test_binary_spec_collects_actions_http_runtime_modules_and_data():
    spec = (Path(__file__).parents[2] / "action-server.spec").read_text()

    assert '"actions_http"' in spec
    assert "collect_all" in spec
    assert "actions_http_hiddenimports" in spec
    assert "actions_http_datas" in spec


def test_binary_spec_bundles_repository_owned_rcc_asset():
    spec = (Path(__file__).parents[2] / "action-server.spec").read_text()

    assert "rcc_datas" in spec
    assert 'startswith("rcc-")' in spec
    assert '"actions/server/bin"' in spec


def test_binary_spec_preserves_work_items_python_sources_for_private_loader():
    """The private loader needs Work Items source files in the extraction tree."""
    spec_path = Path(__file__).parents[2] / "action-server.spec"
    tree = ast.parse(spec_path.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "collect_data_files"
    ]

    work_items_collection = [
        node
        for node in calls
        if node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "actions.work_items"
    ]
    assert len(work_items_collection) == 1
    assert any(
        keyword.arg == "include_py_files"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in work_items_collection[0].keywords
    )

    analysis = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Analysis"
    )
    datas = next(
        keyword.value for keyword in analysis.keywords if keyword.arg == "datas"
    )
    assert any(
        isinstance(node, ast.Name) and node.id == "work_items_datas"
        for node in ast.walk(datas)
    )
    assert '"actions/__init__.py"' not in spec_path.read_text(encoding="utf-8")


def test_work_items_pyinstaller_data_hook_keeps_only_child_package_sources():
    """The hook resolves source under actions/work_items, never the core root."""
    from PyInstaller.utils.hooks import collect_data_files

    data_files = collect_data_files("actions.work_items", include_py_files=True)
    extracted_paths = {
        (Path(destination) / Path(source).name).as_posix()
        for source, destination in data_files
    }

    assert "actions/work_items/__init__.py" in extracted_paths
    assert "actions/work_items/_adapters/_sqlite.py" in extracted_paths
    assert all(path.startswith("actions/work_items/") for path in extracted_paths)
    assert "actions/__init__.py" not in extracted_paths


@pytest.mark.integration_test
def test_binary_build():
    import os
    import shutil
    import sys

    from actions.server._common.run_in_thread import run_in_thread

    CURDIR = Path(__file__).absolute().parent
    action_server_dir = CURDIR.parent.parent
    assert (action_server_dir / "pyproject.toml").exists()

    import subprocess

    env = os.environ.copy()
    env.pop("PYTHONPATH", "")
    env.pop("PYTHONHOME", "")
    env.pop("VIRTUAL_ENV", "")
    env["PYTHONIOENCODING"] = "utf-8"

    dist_dir = action_server_dir / "dist" / "final"
    go_wrapper_name = f"action-server-test-{os.getpid()}"
    target_executable = dist_dir / (
        go_wrapper_name + (".exe" if sys.platform == "win32" else "")
    )

    if target_executable.exists():
        try:
            os.remove(target_executable)
        except Exception:
            raise RuntimeError(f"Failed to remove {target_executable}")

    assets = action_server_dir / "go-wrapper" / "assets"
    for asset_name in ("app_hash", "version.txt", "assets.zip"):
        asset_path = assets / asset_name
        if asset_path.exists():
            asset_path.unlink()

    version = f"test_binary_build-local-{os.getpid()}"
    build_executable_output = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "invoke",
            "build-executable",
            "--go-wrapper",
            "--version",
            version,
            "--go-wrapper-name",
            go_wrapper_name,
        ],
        cwd=action_server_dir,
        env=env,
        stderr=subprocess.STDOUT,
    )

    # Binary should be in the dist directory
    assert target_executable.exists(), f"Binary {target_executable} does not exist. Build output:\n{build_executable_output}"

    env["SEMA4AI_GO_WRAPPER_DEBUG"] = "1"

    # Run the executable
    def run_executable():
        proc = subprocess.Popen(
            [target_executable, "-h"],
            cwd=action_server_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = proc.communicate()
        return proc.returncode, stdout.decode("utf-8", errors="replace")

    extracted_location = get_internal_version_location(version)
    if extracted_location.exists():
        if extracted_location.exists():
            shutil.rmtree(extracted_location)

    try:
        fut1 = run_in_thread(run_executable)
        fut2 = run_in_thread(run_executable)
        fut3 = run_in_thread(run_executable)

        futures = [fut1, fut2, fut3]

        results = [fut.result() for fut in futures]
        outputs = [output for _, output in results]
        assert [returncode for returncode, _ in results] == [0, 0, 0], "\n".join(
            outputs
        )
        skipped = 0
        extracted = 0
        for output in outputs:
            if "Zip hash matches, skipping asset expansion" in output:
                skipped += 1
            if "Expanding assets to: " in output:
                extracted += 1

        full_outputs = "\n".join(outputs)
        assert (
            skipped == 2
        ), f"Expected 2 skipped, got {skipped}. Full outputs:\n{full_outputs}"
        assert (
            extracted == 1
        ), f"Expected 1 extracted, got {extracted}. Full outputs:\n{full_outputs}"

        assert "(ignored) Error touching" not in full_outputs, full_outputs
        assert "(ignored) Error creating" not in full_outputs, full_outputs

        assert extracted_location.exists()

        assert (extracted_location / "app_hash").exists()
        assert (extracted_location / "lastLaunchTouch").exists()
    finally:
        shutil.rmtree(extracted_location)

        if target_executable.exists():
            try:
                os.remove(target_executable)
            except Exception:
                raise RuntimeError(f"Failed to remove {target_executable}")


@pytest.mark.integration_test
def test_work_items_native_executable_api_round_trip(
    action_server_process,
    tmp_path: Path,
) -> None:
    """Exercise the frozen Runtime's own SQLite-backed Work Items API."""
    from actions.work_items import SQLiteAdapter, State

    from actions.server._selftest import ActionServerClient

    project_dir = tmp_path / "action-project"
    project_dir.mkdir()
    (project_dir / "actions.py").write_text(
        "PROJECT_ACTIONS = True\n", encoding="utf-8"
    )
    action_server_process.start(cwd=project_dir, actions_sync=False)
    client = ActionServerClient(action_server_process)

    empty_stats = client.get_json("/api/work-items/stats")
    assert empty_stats == {
        "queue_name": "default",
        "pending": 0,
        "in_progress": 0,
        "done": 0,
        "failed": 0,
        "total": 0,
    }

    created = client.post_get_response(
        "/api/work-items", {"payload": {"native_probe": "#208"}}
    ).json()
    item_id = created["id"]
    assert created["state"] == State.PENDING.value
    assert created["payload"] == {"native_probe": "#208"}

    pending = client.get_json("/api/work-items", params={"state": "PENDING"})
    assert pending["total"] == 1
    assert pending["items"][0]["id"] == item_id
    assert client.get_json(f"/api/work-items/{item_id}")["state"] == State.PENDING.value

    db_path = action_server_process.datadir / "workitems.db"
    assert db_path.is_file()
    assert db_path.parent == action_server_process.datadir

    # The management REST API intentionally has no reserve/release endpoint.
    # Transition the disposable Runtime-owned database through the supported adapter,
    # then verify the native API sees the persisted state.
    adapter = SQLiteAdapter(
        db_path=str(db_path),
        files_dir=str(action_server_process.datadir / "work_item_files"),
    )
    assert adapter.reserve_input() == item_id
    adapter.release_input(item_id, State.DONE)

    done = client.get_json("/api/work-items", params={"state": "DONE"})
    assert done["total"] == 1
    assert done["items"][0]["id"] == item_id
    assert client.get_json(f"/api/work-items/{item_id}")["state"] == State.DONE.value
    final_stats = client.get_json("/api/work-items/stats")
    assert final_stats["done"] == 1
    assert final_stats["total"] == 1

    # Exercise the packaged Runtime error handler with corrupt persisted data.
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE work_items SET payload = ? WHERE id = ?", ("not-json", item_id)
        )

    import actions_http

    def get_error_response(path: str):
        return actions_http.get(
            client.build_full_url(path),
            **client.requests_kwargs(),
        )

    detail_error = get_error_response(f"/api/work-items/{item_id}")
    list_error = get_error_response("/api/work-items")
    for response in (detail_error, list_error):
        assert response.status_code == 503
        body = json.loads(response.text)
        assert body["detail"]["code"] == "work_items_storage_unavailable"
        assert "not found" not in body["detail"]["message"].lower()
        assert str(action_server_process.datadir) not in response.text
