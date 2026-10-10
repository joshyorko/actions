"""A successful watched source switch must let an old Run drain on its snapshot."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import psutil
import pytest

from actions.server._selftest import ActionServerProcess


def _wait_for(label: str, read, timeout: float = 45.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = read()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {label}")


def _run_row(database: Path, run_id: str):
    with sqlite3.connect(database, timeout=3) as connection:
        row = connection.execute(
            "SELECT id, status, result, error_message FROM run WHERE id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "status": row[1],
        "result": json.loads(row[2]) if row[2] else None,
        "error_message": row[3],
    }


def _package_directory(database: Path, package_name: str) -> Path | None:
    with sqlite3.connect(database, timeout=3) as connection:
        row = connection.execute(
            "SELECT directory FROM action_package WHERE name = ?", (package_name,)
        ).fetchone()
    return Path(row[0]) if row else None


def _process_is_alive(pid: int, created: float) -> bool:
    try:
        return psutil.Process(pid).create_time() == created
    except psutil.NoSuchProcess:
        return False


def _write_generation(package: Path, *, generation: str, block: bool) -> None:
    source = package / "generation_action.py"
    temporary = package / "generation_action.py.next"
    temporary.write_text(
        "import hashlib, importlib.metadata, json, time\n"
        "from pathlib import Path\n"
        "import actions\n"
        "from actions import action\n\n"
        "@action\n"
        "def generation_probe() -> str:\n"
        f"    generation = {generation!r}\n"
        + (
            "    Path("
            + repr(str(package.parent / "v1-started"))
            + ").write_text('started', encoding='utf-8')\n"
            "    deadline = time.monotonic() + 60\n"
            "    release = Path(" + repr(str(package.parent / "release-v1")) + ")\n"
            "    while not release.exists():\n"
            "        if time.monotonic() >= deadline:\n"
            "            raise TimeoutError('v1 Run release barrier timed out')\n"
            "        time.sleep(0.02)\n"
            if block
            else ""
        )
        + "    payload = Path(__file__).with_name('generation.txt').read_text(encoding='utf-8')\n"
        + "    return json.dumps({'generation': generation, 'payload': payload, 'source': str(Path(__file__).resolve()), 'core_origin': str(Path(actions.__file__).resolve()), 'core_init_sha256': hashlib.sha256(Path(actions.__file__).read_bytes()).hexdigest(), 'core_version': importlib.metadata.version('actions-core')})\n",
        encoding="utf-8",
    )
    (package / "generation.txt").write_text(generation, encoding="utf-8")
    temporary.replace(source)


@pytest.mark.integration_test
def test_successful_generation_switch_drains_old_run_on_its_source_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run real source-mode workers across a valid watcher generation switch."""
    if "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE" in os.environ:
        pytest.skip("This proves unmanaged source workers, not a frozen executable")

    monkeypatch.setenv("ACTIONS_HOME", str(tmp_path / "actions-home"))
    monkeypatch.setenv("ROBOTS_HOME", str(tmp_path / "robots-home"))
    runtime_src = Path(__file__).resolve().parents[2] / "src"
    monkeypatch.setenv("PYTHONPATH", str(runtime_src))
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir()
    monkeypatch.setenv("TMPDIR", str(runtime_tmp))

    worker_import = json.loads(
        subprocess.check_output(
            [
                sys.executable,
                "-c",
                "import hashlib, importlib.metadata, json; from pathlib import Path; "
                "import actions, actions.server; "
                "print(json.dumps({'runtime': str(Path(actions.server.__file__).resolve()), "
                "'core_origin': str(Path(actions.__file__).resolve()), "
                "'core_init_sha256': hashlib.sha256(Path(actions.__file__).read_bytes()).hexdigest(), "
                "'core_version': importlib.metadata.version('actions-core')}))",
            ],
            cwd=tmp_path,
            env=os.environ.copy(),
            text=True,
            timeout=10,
        )
    )
    assert worker_import["runtime"] == str(
        (runtime_src / "actions/server/__init__.py").resolve()
    )
    print("WORKER_EQUIVALENT_RUNTIME_IMPORT", json.dumps(worker_import, sort_keys=True))
    runtime_sources = (
        "_actions_import.py",
        "_action_package_handler.py",
        "_actions_process_pool.py",
        "_preload_actions/preload_actions_server_main.py",
    )
    runtime_source_hashes = {
        name: hashlib.sha256(
            (runtime_src / "actions/server" / name).read_bytes()
        ).hexdigest()
        for name in runtime_sources
    }
    print(
        "SELECTED_RUNTIME_SOURCE_SHA256",
        json.dumps(runtime_source_hashes, sort_keys=True),
    )

    package = tmp_path / "generation-package"
    package.mkdir()
    _write_generation(package, generation="v1", block=True)
    datadir = tmp_path / "runtime-data"
    database = datadir / "server.db"
    process = ActionServerProcess(datadir)
    shutdown_status: int | None = None
    natural_returncode: int | None = None
    release = tmp_path / "release-v1"
    try:
        process.start(
            db_file="server.db",
            actions_sync=True,
            cwd=tmp_path,
            min_processes=0,
            max_processes=2,
            reuse_processes=False,
            add_shutdown_api=True,
            env={"NO_PROXY": "*", "no_proxy": "*"},
            additional_args=[
                "--address=127.0.0.1",
                "--auto-reload",
                f"--dir={package}",
            ],
            timeout=30,
        )
        server_pid = process.process.pid
        with httpx.Client(
            base_url=f"http://127.0.0.1:{process.port}", timeout=30, trust_env=False
        ) as client:
            _wait_for(
                "initial package registration",
                lambda: _package_directory(database, package.name),
            )
            initial_directory = _package_directory(database, package.name)
            assert initial_directory is not None

            def submit(label: str) -> str:
                response = client.post(
                    "/api/actions/generation-package/generation-probe/run",
                    json={},
                    headers={
                        "x-actions-async-timeout": "0",
                        "x-actions-request-id": f"generation-drain-{label}-{uuid.uuid4().hex}",
                    },
                )
                assert response.status_code == 200, response.text
                run_id = response.headers.get("x-action-server-run-id")
                assert run_id, response.headers
                return run_id

            old_run_id = submit("old")
            _wait_for("v1 worker to enter", lambda: (tmp_path / "v1-started").is_file())
            server_process = psutil.Process(server_pid)
            owned_workers = [
                (child.pid, child.create_time())
                for child in server_process.children(recursive=True)
            ]
            assert (
                owned_workers
            ), "the blocked action should have an owned worker process"
            _wait_for(
                "old Run running",
                lambda: (
                    row
                    if (row := _run_row(database, old_run_id)) and row["status"] == 1
                    else None
                ),
            )
            old_snapshot = _package_directory(database, package.name)
            assert old_snapshot is not None
            old_action = old_snapshot / "generation_action.py"
            old_payload = old_snapshot / "generation.txt"
            old_bytes = old_payload.read_text(encoding="utf-8")
            assert old_bytes == "v1"

            _write_generation(package, generation="v2", block=False)
            new_snapshot = _wait_for(
                "successful v2 package admission",
                lambda: (
                    current
                    if (current := _package_directory(database, package.name))
                    and current != initial_directory
                    and current != old_snapshot
                    and (current / "generation.txt").is_file()
                    and (current / "generation.txt").read_text(encoding="utf-8") == "v2"
                    else None
                ),
            )
            assert old_payload.read_text(encoding="utf-8") == old_bytes
            assert old_action.is_file()

            new_run_id = submit("new")
            new_run = _wait_for(
                "new Run completed while v1 remained in flight",
                lambda: (
                    row
                    if (row := _run_row(database, new_run_id))
                    and row["status"] in (2, 3)
                    else None
                ),
            )
            assert _run_row(database, old_run_id)["status"] == 1
            assert new_run["status"] == 2, new_run
            new_result = json.loads(new_run["result"])
            assert new_result == {
                "generation": "v2",
                "payload": "v2",
                "source": str((new_snapshot / "generation_action.py").resolve()),
                "core_origin": worker_import["core_origin"],
                "core_init_sha256": worker_import["core_init_sha256"],
                "core_version": worker_import["core_version"],
            }

            release.write_text("release", encoding="utf-8")
            old_run = _wait_for(
                "old Run to drain successfully",
                lambda: (
                    row
                    if (row := _run_row(database, old_run_id))
                    and row["status"] in (2, 3)
                    else None
                ),
            )
            assert old_run["status"] == 2, old_run
            old_result = json.loads(old_run["result"])
            assert old_result == {
                "generation": "v1",
                "payload": "v1",
                "source": str((old_snapshot / "generation_action.py").resolve()),
                "core_origin": worker_import["core_origin"],
                "core_init_sha256": worker_import["core_init_sha256"],
                "core_version": worker_import["core_version"],
            }
            assert old_payload.read_text(encoding="utf-8") == "v1"
            assert _package_directory(database, package.name) == new_snapshot
            assert runtime_source_hashes == {
                name: hashlib.sha256(
                    (runtime_src / "actions/server" / name).read_bytes()
                ).hexdigest()
                for name in runtime_sources
            }
            owned_workers = sorted(
                set(owned_workers)
                | {
                    (child.pid, child.create_time())
                    for child in server_process.children(recursive=True)
                }
            )
            print(
                "SUCCESSFUL_GENERATION_DRAIN_PASS",
                json.dumps(
                    {
                        "old_run_id": old_run_id,
                        "new_run_id": new_run_id,
                        "old_source": old_result["source"],
                        "new_source": new_result["source"],
                        "old_result": old_result,
                        "new_result": new_result,
                        "old_snapshot_retained_until_drain": True,
                    },
                    sort_keys=True,
                ),
            )

            response = client.post("/api/shutdown/", json={})
            shutdown_status = response.status_code
            assert response.status_code == 200, response.text
        _wait_for(
            "natural Action Server exit",
            lambda: process.process.returncode is not None,
            timeout=15,
        )
        natural_returncode = process.process.returncode
        assert natural_returncode == 1
        assert process.process.pid == server_pid
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not any(
                _process_is_alive(pid, created) for pid, created in owned_workers
            ):
                break
            time.sleep(0.05)
        assert all(
            not _process_is_alive(pid, created) for pid, created in owned_workers
        ), f"owned worker processes survived natural shutdown: {owned_workers}"
    finally:
        if process.process.returncode is None:
            release.write_text("cleanup-release", encoding="utf-8")
            process.stop()
        else:
            process.stop()
    assert shutdown_status == 200
    assert natural_returncode == 1
