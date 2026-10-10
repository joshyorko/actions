"""Real watched import failure must keep both packages executable."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from action_server_tests.test_cli_mcp_catalog_rollback import (
    _catalog_rows,
    _catalogs,
    _mcp,
)

from actions.server._selftest import ActionServerProcess


def _write_tool(package: Path, suffix: str, result: str) -> None:
    package.mkdir(exist_ok=True)
    if "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE" in os.environ:
        (package / "package.yaml").write_text(
            "spec-version: v2\n"
            f"name: {package.name}\n"
            "description: Managed frozen watched-reload fixture.\n"
            "version: 0.0.1\n"
            "dependencies:\n"
            "  conda-forge:\n"
            "    - python=3.12\n"
            "    - uv=0.9.26\n"
            "  pypi:\n"
            "    - actions-core=1.0.2\n",
            encoding="utf-8",
        )
    source = package / "watched_actions.py"
    temporary = package / "next-source.tmp"
    temporary.write_text(
        "import hashlib, json, sys\n"
        "from importlib.metadata import version\n"
        "from pathlib import Path\n"
        "import actions\n"
        "from actions import mcp\n\n"
        "@mcp.tool()\n"
        f"def from_package_{suffix}() -> str:\n"
        f'    """Accepted {result} implementation."""\n'
        "    return json.dumps({\n"
        f"        'value': {result!r},\n"
        "        'core_origin': str(Path(actions.__file__).resolve()),\n"
        "        'core_init_sha256': hashlib.sha256(Path(actions.__file__).read_bytes()).hexdigest(),\n"
        "        'core_version': version('actions-core'),\n"
        "        'python_executable': str(Path(sys.executable).resolve()),\n"
        "    })\n",
        encoding="utf-8",
    )
    temporary.replace(source)


def _assert_calls(
    client: httpx.Client, expected_b: str, expected_core: dict[str, str]
) -> None:
    for suffix, expected in (("a", "A1"), ("b", expected_b)):
        response = client.post(
            f"/api/actions/package-{suffix}/from-package-{suffix}/run", json={}
        )
        assert response.status_code == 200, response.text
        assert json.loads(response.json()) == {"value": expected, **expected_core}
        result = _mcp(
            client, "tools/call", {"name": f"from_package_{suffix}", "arguments": {}}
        )
        assert json.loads(result["content"][0]["text"]) == {
            "value": expected,
            **expected_core,
        }


def _managed_worker_identity(client: httpx.Client, suffix: str) -> dict[str, str]:
    response = client.post(
        f"/api/actions/package-{suffix}/from-package-{suffix}/run", json={}
    )
    assert response.status_code == 200, response.text
    identity = json.loads(response.json())
    holotree = (Path(os.environ["ACTIONS_HOME"]) / "holotree").resolve()
    assert Path(identity["python_executable"]).is_relative_to(holotree)
    assert Path(identity["core_origin"]).is_relative_to(holotree)
    assert identity["core_version"] == "1.0.2"
    return {
        key: identity[key]
        for key in (
            "core_origin",
            "core_init_sha256",
            "core_version",
            "python_executable",
        )
    }


def _assert_frozen_parent(process: ActionServerProcess) -> None:
    import psutil

    expected = Path(
        os.environ["SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE"]
    ).resolve()
    actual = Path(psutil.Process(process.process.pid).exe()).resolve()
    assert actual == expected


def _shutdown(client: httpx.Client, process: ActionServerProcess) -> None:
    from actions.server._common.wait_for import wait_for_condition

    response = client.post("/api/shutdown/", json={})
    assert response.status_code == 200, response.text
    wait_for_condition(
        lambda: process.process.returncode is not None,
        msg="Watched Runtime did not exit after controlled shutdown",
        timeout=10,
        sleep=0.05,
    )
    assert process.process.returncode == 1


@pytest.mark.integration_test
def test_failed_watched_reload_keeps_both_packages_and_recovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from actions.server._common.wait_for import wait_for_condition

    native_executable = os.environ.get(
        "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE"
    )
    monkeypatch.setenv("ACTIONS_HOME", str(tmp_path / "actions-home"))
    monkeypatch.setenv("ROBOTS_HOME", str(tmp_path / "robots-home"))
    # Runtime children change cwd; relative PYTHONPATH would select an unrelated
    # editable installation instead of this checkout's production source.
    runtime_src = Path(__file__).resolve().parents[2] / "src"
    monkeypatch.setenv("PYTHONPATH", "" if native_executable else str(runtime_src))
    # Resolve imports with the Runtime child's cwd and environment. The pytest
    # process may intentionally import a different in-tree Core; metadata file
    # locations also need not identify the imported file in an editable install.
    if native_executable:
        assert Path(native_executable).is_file()
        selected_imports = None
        expected_core = None
        runtime_files = None
    else:
        selected_imports = json.loads(
            subprocess.check_output(
                [
                    sys.executable,
                    "-c",
                    "import hashlib, json, sys; from importlib.metadata import version; "
                    "from pathlib import Path; import actions, actions.server; "
                    "print(json.dumps({'runtime_origin': "
                    "str(Path(actions.server.__file__).resolve()), 'core': {"
                    "'core_origin': str(Path(actions.__file__).resolve()), "
                    "'core_init_sha256': hashlib.sha256("
                    "Path(actions.__file__).read_bytes()).hexdigest(), "
                    "'core_version': version('actions-core'), "
                    "'python_executable': str(Path(sys.executable).resolve())}}))",
                ],
                cwd=tmp_path,
                env=os.environ.copy(),
                text=True,
                timeout=10,
            )
        )
        # Keep the source-only control path explicit. The frozen case gets
        # worker provenance from a package action after RCC has admitted it.
        assert selected_imports["runtime_origin"] == str(
            (runtime_src / "actions/server/__init__.py").resolve()
        )
        expected_core = selected_imports["core"]
        print(
            "WORKER_EQUIVALENT_IMPORT_PROBE",
            json.dumps(selected_imports, sort_keys=True),
        )
        runtime_files = {
            name: hashlib.sha256(
                (runtime_src / "actions/server" / name).read_bytes()
            ).hexdigest()
            for name in (
                "_action_package_handler.py",
                "_actions_import.py",
                "_server.py",
                "_watcher.py",
            )
        }
        print(
            "SELECTED_RUNTIME_SOURCE",
            runtime_src,
            json.dumps(runtime_files, sort_keys=True),
        )
        print("EXPECTED_CORE_WORKER", json.dumps(expected_core, sort_keys=True))
    runtime_tmp = tmp_path / "subprocess-tmp"
    runtime_tmp.mkdir()
    monkeypatch.setenv("TMPDIR", str(runtime_tmp))
    package_a, package_b = tmp_path / "package_a", tmp_path / "package_b"
    _write_tool(package_a, "a", "A1")
    _write_tool(package_b, "b", "B1")
    datadir = tmp_path / "runtime-data"
    database = datadir / "catalog.sqlite"
    process = ActionServerProcess(datadir)
    started = time.monotonic()
    try:
        process.start(
            db_file="catalog.sqlite",
            actions_sync=True,
            cwd=tmp_path,
            min_processes=0,
            max_processes=2,
            reuse_processes=False,
            add_shutdown_api=True,
            env={
                "NO_PROXY": "*",
                "no_proxy": "*",
                "PYTHONPATH": "" if native_executable else str(runtime_src),
            },
            additional_args=[
                "--address=127.0.0.1",
                "--auto-reload",
                f"--dir={package_a}",
                f"--dir={package_b}",
            ],
            # The first native managed package environment may be cold on CI.
            # Windows and macOS logs show RCC spending almost 30 seconds in
            # `holotree variables` before the server emits its ready address.
            timeout=90 if native_executable else 30,
        )
        import psutil

        if native_executable:
            _assert_frozen_parent(process)
            assert psutil.Process(process.process.pid).environ()["PYTHONPATH"] == ""
        else:
            assert psutil.Process(process.process.pid).environ()["PYTHONPATH"] == str(
                runtime_src
            )
        print(
            "OBSERVED_WATCHED_RUNTIME_CHILD",
            process.process.pid,
            "PYTHONPATH",
            runtime_src if not native_executable else "frozen executable",
        )
        with httpx.Client(
            base_url=f"http://127.0.0.1:{process.port}", timeout=30, trust_env=False
        ) as client:
            before = _catalogs(client)
            assert {tool["name"] for tool in before["tools/list"]["tools"]} == {
                "from_package_a",
                "from_package_b",
            }
            if native_executable:
                expected_core = _managed_worker_identity(client, "a")
                print(
                    "MANAGED_PACKAGE_WORKER", json.dumps(expected_core, sort_keys=True)
                )
            assert expected_core is not None
            _assert_calls(client, "B1", expected_core)
            before_rows = _catalog_rows(database)
            with sqlite3.connect(database) as connection:
                accepted_sources = [
                    Path(row[0])
                    for row in connection.execute(
                        "SELECT directory FROM action_package"
                    )
                ]
            before_bytes = {
                source / "watched_actions.py": (
                    source / "watched_actions.py"
                ).read_bytes()
                for source in accepted_sources
            }
            source_store = datadir / ".rcc-runtime-sources"
            before_snapshots = set(source_store.iterdir())
            log_offset = len(process.get_stderr())
            malformed = package_b / "next-source.tmp"
            malformed.write_text(
                "from actions import mcp\n@mcp.tool()\ndef broken(:\n",
                encoding="utf-8",
            )
            malformed.replace(package_b / "watched_actions.py")

            def rejected() -> bool:
                output = process.get_stderr()[log_offset:]
                return (
                    "Unable to do auto-reload (actions could not be imported)."
                    in output
                    or "Unable to commit action generation reload." in output
                )

            wait_for_condition(
                rejected,
                msg="Watcher did not reject malformed B",
                timeout=30,
                sleep=0.05,
            )
            assert process.process.returncode is None
            assert _catalog_rows(database) == before_rows
            assert _catalogs(client) == before
            assert set(source_store.iterdir()) == before_snapshots
            for source, expected in before_bytes.items():
                assert source.read_bytes() == expected
            _assert_calls(client, "B1", expected_core)
            print("WATCHED_FAILURE_LAST_GOOD_PASS A=A1 B=B1")

            _write_tool(package_b, "b", "B2")

            def recovered() -> bool:
                # Separate catalog requests can straddle a valid generation
                # transition; poll one response, then compare stable catalogs.
                tools = _mcp(client, "tools/list", {})["tools"]
                return any(
                    tool["name"] == "from_package_b"
                    and "B2" in tool.get("description", "")
                    for tool in tools
                )

            wait_for_condition(
                recovered,
                msg="Watcher did not admit corrected B2",
                timeout=30,
                sleep=0.05,
            )
            after = _catalogs(client)
            assert after != before
            assert (
                after["tools/list"]["_meta"]["actions.catalogRevision"]
                != before["tools/list"]["_meta"]["actions.catalogRevision"]
            )
            assert {tool["name"] for tool in after["tools/list"]["tools"]} == {
                "from_package_a",
                "from_package_b",
            }
            _assert_calls(client, "B2", expected_core)
            accepted_rows = _catalog_rows(database)
            _shutdown(client, process)
            print("WATCHED_RECOVERY_PASS A=A1 B=B2 natural_exit=1")
    finally:
        process.stop()

    restarted = ActionServerProcess(datadir)
    try:
        restarted.start(
            db_file="catalog.sqlite",
            actions_sync=False,
            cwd=tmp_path,
            min_processes=0,
            max_processes=2,
            reuse_processes=False,
            add_shutdown_api=True,
            env={
                "NO_PROXY": "*",
                "no_proxy": "*",
                "PYTHONPATH": "" if native_executable else str(runtime_src),
            },
            additional_args=["--address=127.0.0.1"],
            timeout=30,
        )
        if native_executable:
            _assert_frozen_parent(restarted)
            assert psutil.Process(restarted.process.pid).environ()["PYTHONPATH"] == ""
        else:
            assert psutil.Process(restarted.process.pid).environ()["PYTHONPATH"] == str(
                runtime_src
            )
        print(
            "OBSERVED_RESTARTED_RUNTIME_CHILD",
            restarted.process.pid,
            "PYTHONPATH",
            runtime_src if not native_executable else "frozen executable",
        )
        with httpx.Client(
            base_url=f"http://127.0.0.1:{restarted.port}", timeout=30, trust_env=False
        ) as client:
            assert _catalogs(client) == after
            assert _catalog_rows(database) == accepted_rows
            _assert_calls(client, "B2", expected_core)
            _shutdown(client, restarted)
            print(
                f"WATCHED_RESTART_PASS A=A1 B=B2 natural_exit=1 elapsed={time.monotonic() - started:.2f}s"
            )
    finally:
        restarted.stop()
    if runtime_files is not None:
        assert runtime_files == {
            name: hashlib.sha256(
                (runtime_src / "actions/server" / name).read_bytes()
            ).hexdigest()
            for name in runtime_files
        }
