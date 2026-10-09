"""Black-box RCC source-only reload and in-flight generation acceptance."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import psutil
import pytest

RCC_SHA256 = "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428"
RCC_VERSION = "v18.19.3"
ASYNC_TIMEOUT_HEADER = "x-actions-async-timeout"
REQUEST_ID_HEADER = "x-actions-request-id"
RUN_ID_HEADER = "x-action-server-run-id"


def _wait_for(label: str, read: Callable[[], Any], timeout: float = 60.0) -> Any:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            value = read()
        except (OSError, sqlite3.Error) as exc:
            last_error = exc
            value = None
        if value:
            return value
        time.sleep(0.05)
    detail = f"; last read error: {last_error}" if last_error else ""
    raise AssertionError(f"timed out waiting for {label}{detail}")


def _read_package_runtime(db_path: Path, package_name: str) -> dict[str, Any] | None:
    with sqlite3.connect(db_path, timeout=3) as connection:
        row = connection.execute(
            "SELECT id, env_json FROM action_package WHERE name = ?",
            (package_name,),
        ).fetchone()
    if row is None:
        return None
    env = json.loads(row[1])
    runtime = env.get("runtime")
    if not isinstance(runtime, dict):
        raise AssertionError("ActionPackage env_json has no runtime descriptor")
    return {"package_id": row[0], **runtime}


def _read_package_directory(db_path: Path, package_name: str) -> Path | None:
    with sqlite3.connect(db_path, timeout=3) as connection:
        row = connection.execute(
            "SELECT directory FROM action_package WHERE name = ?", (package_name,)
        ).fetchone()
    return Path(row[0]) if row else None


def _read_run(db_path: Path, run_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(db_path, timeout=3) as connection:
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


def _rcc_trace(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _exec_record_since(
    trace: list[dict[str, Any]], start: int
) -> dict[str, Any] | None:
    for record in reversed(trace[start:]):
        args = record["args"]
        if args[:2] == ["env", "exec"] and "--receipt-file" in args:
            return record
    return None


def _environment_operations(trace: list[dict[str, Any]]) -> list[list[str]]:
    phases = {"publish", "acquire", "build"}
    return [
        record["args"]
        for record in trace
        if len(record["args"]) > 1
        and record["args"][0] == "env"
        and record["args"][1] in phases
    ]


def _process_tree(pid: int) -> list[dict[str, Any]]:
    root = psutil.Process(pid)
    processes = [root, *root.children(recursive=True)]
    return [
        {"pid": process.pid, "create_time": process.create_time()}
        for process in processes
    ]


def _process_identity_exists(identity: dict[str, Any]) -> bool:
    try:
        process = psutil.Process(identity["pid"])
        return abs(process.create_time() - identity["create_time"]) < 0.01
    except psutil.NoSuchProcess:
        return False


def _old_process_tree_reaped(tree: list[dict[str, Any]]) -> bool:
    return not any(_process_identity_exists(item) for item in tree)


def _action_source(start_path: Path, release_path: Path, result: str) -> str:
    return f'''from pathlib import Path
import time
from actions import action

@action
def generation_probe() -> str:
    Path({str(start_path)!r}).write_text("entered", encoding="utf-8")
    deadline = time.monotonic() + 60
    while not Path({str(release_path)!r}).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("test release barrier was not opened")
        time.sleep(0.02)
    return {result!r}
'''


def _runtime_test_environment(
    tmp_path: Path, source_root: Path
) -> tuple[dict[str, str], str, str, Path, str, Path, dict[str, Path]]:
    real_rcc = Path(os.environ["ACTIONS_RUNTIME_REAL_RCC_BINARY"]).resolve()
    real_rcc_sha = hashlib.sha256(real_rcc.read_bytes()).hexdigest()
    assert real_rcc_sha == RCC_SHA256
    version = subprocess.run(
        [str(real_rcc), "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert version == RCC_VERSION

    trace_path = tmp_path / "rcc-calls.jsonl"
    wrapper = tmp_path / "rcc-instrumented"
    assert not trace_path.exists()
    assert not wrapper.exists()
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "with open(os.environ['ACTIONS_RUNTIME_RCC_TRACE'], 'a', encoding='utf-8') as stream:\n"
        "    stream.write(json.dumps({'pid': os.getpid(), 'args': sys.argv[1:]}) + '\\n')\n"
        "real = os.environ['ACTIONS_RUNTIME_RCC_REAL_BINARY']\n"
        "os.execv(real, [real, *sys.argv[1:]])\n"
    )
    wrapper.chmod(0o700)

    rcc_home = Path(
        os.environ.get("ACTIONS_RUNTIME_LOCAL_RCC_HOME", str(tmp_path / "rcc-home"))
    ).resolve()
    rcc_home.mkdir(parents=True, exist_ok=True)
    trust_carrier_dir = Path(
        os.environ.get(
            "ACTIONS_RUNTIME_LOCAL_TRUST_CARRIER",
            str(tmp_path / "rcc-trust-carrier"),
        )
    ).resolve()
    if not trust_carrier_dir.exists():
        trust_carrier_dir.mkdir(mode=0o700, parents=True)
    info = trust_carrier_dir.lstat()
    assert not stat.S_ISLNK(info.st_mode)
    assert stat.S_ISDIR(info.st_mode)
    assert info.st_uid == os.geteuid()
    assert stat.S_IMODE(info.st_mode) & 0o022 == 0
    trust_carrier_identity = "sha256:" + hashlib.sha256(
        b"actions-rcc-trust-carrier-v1\0"
        + os.fsencode(str(trust_carrier_dir.resolve(strict=True)))
    ).hexdigest()

    runtime_env = os.environ.copy()
    source_pythonpath = str(source_root / "src")
    other_pythonpath = runtime_env.get("PYTHONPATH", "")
    runtime_env.update(
        {
            "ACTIONS_RUNTIME_SOURCE_ROOT": str(source_root),
            "ACTIONS_RUNTIME_RCC_BINARY": str(wrapper),
            "ACTIONS_RUNTIME_RCC_REAL_BINARY": str(real_rcc),
            "ACTIONS_RUNTIME_RCC_TRACE": str(trace_path),
            "ACTIONS_RUNTIME_RCC_PROVIDER": "local",
            "ACTIONS_RUNTIME_RCC_TRUST_CARRIER": str(trust_carrier_dir),
            "ACTIONS_REAL_RCC_ARTIFACT_TEST": "1",
            "ACTIONS_RUNTIME_RCC_TIMEOUT": "120",
            "PYTHONPATH": os.pathsep.join(
                [source_pythonpath, other_pythonpath]
                if other_pythonpath
                else [source_pythonpath]
            ),
            "ROBOCORP_HOME": str(rcc_home),
            "S4_ACTION_SERVER_RCC_CONFIG_LOCATION": str(
                tmp_path / "rcc-config" / "rcc.yaml"
            ),
        }
    )
    source_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib, json; modules = ("
            "'actions.server._actions_import', "
            "'actions.server._action_package_handler', "
            "'actions.server._rcc_runtime_adapter', "
            "'actions.server._server'); "
            "print(json.dumps({name: importlib.import_module(name).__file__ "
            "for name in modules}))",
        ],
        env=runtime_env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    module_origins = {
        name: Path(path).resolve() for name, path in json.loads(source_probe).items()
    }
    for name, origin in module_origins.items():
        assert source_root in origin.parents, f"{name} imported from {origin}"
    source_module = module_origins["actions.server._rcc_runtime_adapter"]
    return (
        runtime_env,
        real_rcc_sha,
        version,
        trace_path,
        trust_carrier_identity,
        source_module,
        module_origins,
    )


@pytest.mark.integration_test
@pytest.mark.real_rcc
def test_real_rcc_source_only_reload_drains_pinned_generation(
    action_server_process, client, tmp_path
):
    """Prove old/new Actions against one Artifact without preparation on reload."""
    import platform

    required = (
        "ACTIONS_RUNTIME_SOURCE_ROOT",
        "ACTIONS_RUNTIME_SOURCE_SHA",
        "ACTIONS_RUNTIME_SOURCE_ARCHIVE",
        "ACTIONS_RUNTIME_SOURCE_ARCHIVE_SHA256",
        "ACTIONS_RUNTIME_SOURCE_IDENTITY_FILE",
        "ACTIONS_RUNTIME_REAL_RCC_BINARY",
        "ACTIONS_RUNTIME_LIFECYCLE_RECEIPT",
    )
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, f"source-bound lifecycle proof missing inputs: {missing}"

    source_root = Path(os.environ["ACTIONS_RUNTIME_SOURCE_ROOT"]).resolve()
    source_sha = os.environ["ACTIONS_RUNTIME_SOURCE_SHA"]
    archive = Path(os.environ["ACTIONS_RUNTIME_SOURCE_ARCHIVE"]).resolve()
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    identity = json.loads(Path(os.environ["ACTIONS_RUNTIME_SOURCE_IDENTITY_FILE"]).read_text())
    assert identity["commit"] == source_sha
    assert identity["archive_sha256"] == archive_sha
    assert identity["archive_sha256"] == os.environ[
        "ACTIONS_RUNTIME_SOURCE_ARCHIVE_SHA256"
    ]
    assert len(source_sha) == 40 and all(char in "0123456789abcdef" for char in source_sha)
    assert (source_root / "src/actions/server/_rcc_runtime_adapter.py").is_file()

    (
        runtime_env,
        real_rcc_sha,
        version,
        trace_path,
        trust_carrier_identity,
        source_module,
        source_module_origins,
    ) = _runtime_test_environment(tmp_path, source_root)

    package_dir = tmp_path / "package" / "rcc-lifecycle"
    package_dir.mkdir(parents=True)
    (package_dir / "package.yaml").write_text(
        "version: 0.1\nspec-version: v2\ndependencies:\n"
        "  conda-forge:\n    - python=3.11.11\n"
        "  pypi:\n    - actions-core=1.0.2\n",
        encoding="utf-8",
    )
    action_file = package_dir / "action.py"
    started_path = tmp_path / "old-action-entered"
    release_path = tmp_path / "release-old-action"
    action_file.write_text(
        _action_source(started_path, release_path, "old-generation"),
        encoding="utf-8",
    )

    db_path = action_server_process.datadir / "server.db"
    receipt_path = Path(os.environ["ACTIONS_RUNTIME_LIFECYCLE_RECEIPT"])
    assert not receipt_path.exists(), f"receipt already exists: {receipt_path}"
    evidence: dict[str, Any] = {
        "schema": "rcc-runtime-generation-lifecycle-v1",
        "status": "NOT_RUN",
        "source_commit": source_sha,
        "source_archive_sha256": archive_sha,
        "source_module": str(source_module),
        "source_module_origins": {
            name: str(path) for name, path in source_module_origins.items()
        },
        "rcc_version": version,
        "rcc_sha256": real_rcc_sha,
        "provider": "local",
        "trust_carrier_identity": trust_carrier_identity,
        "trust_carrier_mode": "separate-filesystem",
        "host_platform": platform.platform(),
    }
    old_tree: list[dict[str, Any]] = []
    old_run_id: str | None = None
    try:
        action_server_process.start(
            timeout=120,
            actions_sync=True,
            cwd=package_dir,
            db_file="server.db",
            min_processes=0,
            max_processes=2,
            reuse_processes=False,
            additional_args=["--auto-reload"],
            env=runtime_env,
        )
        package_name = package_dir.name

        def read_package():
            return _read_package_runtime(db_path, package_name)

        initial_runtime = _wait_for("initial ActionPackage runtime descriptor", read_package)
        assert initial_runtime["kind"] == "rcc"
        assert initial_runtime["rcc_version"] == RCC_VERSION
        assert initial_runtime["trust_carrier_identity"] == trust_carrier_identity
        artifact_digest = initial_runtime["artifact_digest"]
        environment_fingerprint = initial_runtime["environment_fingerprint"]
        initial_generation = initial_runtime["source_generation"]
        source_store = action_server_process.datadir / ".rcc-runtime-sources"
        package_store = source_store / hashlib.sha256(package_name.encode("utf-8")).hexdigest()
        initial_source = _read_package_directory(db_path, package_name)
        assert initial_source is not None and initial_source.is_absolute()
        assert initial_source.is_relative_to(package_store)
        assert "old-generation" in (initial_source / "action.py").read_text(
            encoding="utf-8"
        )
        evidence["package_id"] = initial_runtime["package_id"]
        evidence["source_snapshot_before"] = str(initial_source)
        evidence["artifact_digest"] = artifact_digest
        evidence["environment_fingerprint"] = environment_fingerprint
        evidence["source_generation_before"] = initial_generation

        old_request_trace_start = len(_rcc_trace(trace_path))
        old_response = client.post_get_response(
            f"api/actions/{package_name}/generation-probe/run",
            {},
            {
                ASYNC_TIMEOUT_HEADER: "0",
                REQUEST_ID_HEADER: f"lifecycle-old-{uuid.uuid4().hex}",
            },
        )
        old_run_id = old_response.headers.get(RUN_ID_HEADER)
        assert old_run_id, old_response.headers
        evidence["old_run_id"] = old_run_id
        _wait_for("old Action entered", started_path.is_file)
        old_run = _wait_for(
            "old Run running",
            lambda: (row if (row := _read_run(db_path, old_run_id)) and row["status"] == 1 else None),
        )
        evidence["old_run_running"] = old_run

        trace_before = _rcc_trace(trace_path)
        old_exec = _exec_record_since(trace_before, old_request_trace_start)
        assert old_exec, "no real RCC env exec receipt was logged for the old Action"
        old_exec_args = old_exec["args"]
        assert "--permissive-local" in old_exec_args
        provider_index = old_exec_args.index("--provider")
        assert old_exec_args[provider_index + 1] == "local"
        receipt_index = old_exec_args.index("--receipt-file")
        old_receipt_path = Path(old_exec_args[receipt_index + 1])
        old_wrapper_pid = old_exec["pid"]
        old_tree = _process_tree(old_wrapper_pid)
        assert len(old_tree) > 1, "no live RCC wrapper descendants were observed"
        evidence["old_wrapper_pid"] = old_wrapper_pid
        evidence["old_wrapper_receipt"] = str(old_receipt_path)
        evidence["old_wrapper_tree_before_drain"] = old_tree
        provider_ops_before_reload = _environment_operations(trace_before)
        assert provider_ops_before_reload, "no explicit local RCC preparation was observed"
        evidence["provider_ops_before_reload"] = provider_ops_before_reload

        replacement = tmp_path / "action.py.new"
        replacement.write_text(
            "from actions import action\n\n"
            "@action\n"
            "def generation_probe() -> str:\n"
            "    return 'new-generation'\n",
            encoding="utf-8",
        )
        replacement.replace(action_file)

        def read_new_generation():
            current = _read_package_runtime(db_path, package_name)
            if current and current.get("source_generation") != initial_generation:
                return current
            return None

        next_runtime = _wait_for("source-only Runtime generation", read_new_generation)
        next_source = _read_package_directory(db_path, package_name)
        assert next_source is not None and next_source.is_relative_to(package_store)
        assert next_source != initial_source
        assert "new-generation" in (next_source / "action.py").read_text(
            encoding="utf-8"
        )
        assert next_runtime["artifact_digest"] == artifact_digest
        assert next_runtime["environment_fingerprint"] == environment_fingerprint
        assert next_runtime["trust_carrier_identity"] == trust_carrier_identity
        assert next_runtime["source_generation"] != initial_generation
        evidence["source_generation_after"] = next_runtime["source_generation"]
        evidence["source_snapshot_after"] = str(next_source)
        evidence["artifact_digest_after"] = next_runtime["artifact_digest"]

        new_start = len(_rcc_trace(trace_path))
        new_response = client.post_get_response(
            f"api/actions/{package_name}/generation-probe/run",
            {},
            {
                ASYNC_TIMEOUT_HEADER: "0",
                REQUEST_ID_HEADER: f"lifecycle-new-{uuid.uuid4().hex}",
            },
        )
        new_run_id = new_response.headers.get(RUN_ID_HEADER)
        assert new_run_id, new_response.headers
        evidence["new_run_id"] = new_run_id
        new_run = _wait_for(
            "new generation Run passed",
            lambda: (row if (row := _read_run(db_path, new_run_id)) and row["status"] == 2 else None),
        )
        assert new_run["result"] == "new-generation"
        evidence["new_run_result"] = new_run

        still_old = _read_run(db_path, old_run_id)
        assert still_old and still_old["status"] == 1, still_old
        assert _process_identity_exists(old_tree[0]), "old wrapper exited before drain"
        evidence["old_run_still_running_after_new_pass"] = still_old

        trace_after_new = _rcc_trace(trace_path)
        provider_ops_after_reload = _environment_operations(trace_after_new)
        assert provider_ops_after_reload == evidence["provider_ops_before_reload"], (
            "source-only reload added RCC publish/acquire/build calls"
        )
        evidence["provider_ops_after_reload"] = provider_ops_after_reload
        new_exec = _exec_record_since(trace_after_new, new_start)
        assert new_exec, "new generation Action did not create an RCC env exec wrapper"
        new_receipt_index = new_exec["args"].index("--receipt-file")
        new_receipt_path = Path(new_exec["args"][new_receipt_index + 1])
        evidence["new_wrapper_pid"] = new_exec["pid"]
        evidence["new_wrapper_receipt"] = str(new_receipt_path)

        release_path.touch()
        old_passed = _wait_for(
            "old generation Run passed",
            lambda: (row if (row := _read_run(db_path, old_run_id)) and row["status"] == 2 else None),
        )
        assert old_passed["result"] == "old-generation"
        evidence["old_run_result"] = old_passed

        _wait_for(
            "old wrapper and observed descendants reaped",
            lambda: True if _old_process_tree_reaped(old_tree) else None,
            timeout=20,
        )
        evidence["old_wrapper_tree_reaped"] = old_tree

        def valid_receipt(path: Path):
            if not path.is_file():
                return None
            receipt = json.loads(path.read_text(encoding="utf-8"))
            if (
                receipt.get("artifactDigest") == artifact_digest
                and receipt.get("verification", {}).get("valid") is True
                and receipt.get("leaseId")
                and receipt.get("status") == "completed"
                and receipt.get("exitCode") == 0
            ):
                return receipt
            return None

        old_receipt = _wait_for(
            "old RCC completion receipt", lambda: valid_receipt(old_receipt_path)
        )
        new_receipt = _wait_for(
            "new RCC completion receipt", lambda: valid_receipt(new_receipt_path)
        )
        evidence["old_rcc_receipt"] = old_receipt
        evidence["new_rcc_receipt"] = new_receipt
        evidence["status"] = "PASS"
    except Exception as exc:
        evidence["status"] = "FAIL"
        evidence["failure_type"] = type(exc).__name__
        evidence["failure"] = str(exc)[:1000]
        raise
    finally:
        if not release_path.exists():
            release_path.touch()
        if old_run_id:
            try:
                evidence["old_run_after_release"] = _wait_for(
                    "old Run cleanup after opening release barrier",
                    lambda: (row if (row := _read_run(db_path, old_run_id)) and row["status"] != 1 else None),
                    timeout=15,
                )
            except AssertionError as cleanup_error:
                evidence["old_run_cleanup"] = "NOT_OBSERVED"
                evidence["old_run_cleanup_error"] = str(cleanup_error)
        evidence["rcc_trace"] = _rcc_trace(trace_path)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


@pytest.mark.integration_test
@pytest.mark.real_rcc
def test_real_rcc_import_failure_keeps_last_good_generation(
    action_server_process, client, tmp_path
):
    """A malformed source update must not replace the live Action generation."""
    import platform

    import requests

    required = (
        "ACTIONS_RUNTIME_SOURCE_ROOT",
        "ACTIONS_RUNTIME_SOURCE_SHA",
        "ACTIONS_RUNTIME_SOURCE_ARCHIVE",
        "ACTIONS_RUNTIME_SOURCE_ARCHIVE_SHA256",
        "ACTIONS_RUNTIME_SOURCE_IDENTITY_FILE",
        "ACTIONS_RUNTIME_REAL_RCC_BINARY",
        "ACTIONS_RUNTIME_LIFECYCLE_RECEIPT",
    )
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, f"source-bound lifecycle proof missing inputs: {missing}"

    source_root = Path(os.environ["ACTIONS_RUNTIME_SOURCE_ROOT"]).resolve()
    source_sha = os.environ["ACTIONS_RUNTIME_SOURCE_SHA"]
    archive = Path(os.environ["ACTIONS_RUNTIME_SOURCE_ARCHIVE"]).resolve()
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    identity = json.loads(
        Path(os.environ["ACTIONS_RUNTIME_SOURCE_IDENTITY_FILE"]).read_text()
    )
    assert identity["commit"] == source_sha
    assert identity["archive_sha256"] == archive_sha
    assert archive_sha == os.environ["ACTIONS_RUNTIME_SOURCE_ARCHIVE_SHA256"]
    assert (source_root / "src/actions/server/_rcc_runtime_adapter.py").is_file()

    (
        runtime_env,
        real_rcc_sha,
        version,
        trace_path,
        trust_carrier_identity,
        source_module,
        source_module_origins,
    ) = _runtime_test_environment(tmp_path, source_root)
    receipt_path = Path(os.environ["ACTIONS_RUNTIME_LIFECYCLE_RECEIPT"])
    assert not receipt_path.exists(), f"receipt already exists: {receipt_path}"

    package_root = tmp_path / "packages"
    package_dir = package_root / "last-good"
    package_dir.mkdir(parents=True)
    (package_dir / "package.yaml").write_text(
        "version: 0.1\nspec-version: v2\ndependencies:\n"
        "  conda-forge:\n    - python=3.11.11\n"
        "  pypi:\n    - actions-core=1.0.2\n",
        encoding="utf-8",
    )
    action_file = package_dir / "action.py"
    started_path = tmp_path / "last-good-action-entered"
    release_path = tmp_path / "release-last-good-action"
    action_file.write_text(
        _action_source(started_path, release_path, "last-good"), encoding="utf-8"
    )

    db_path = action_server_process.datadir / "server.db"
    evidence: dict[str, Any] = {
        "schema": "rcc-runtime-import-rollback-v1",
        "status": "NOT_RUN",
        "source_commit": source_sha,
        "source_archive_sha256": archive_sha,
        "source_module": str(source_module),
        "source_module_origins": {
            name: str(path) for name, path in source_module_origins.items()
        },
        "rcc_version": version,
        "rcc_sha256": real_rcc_sha,
        "provider": "local",
        "trust_carrier_identity": trust_carrier_identity,
        "host_platform": platform.platform(),
    }
    run_ids: list[str] = []
    evidence["run_ids"] = run_ids
    worker_tree: list[dict[str, Any]] = []
    server_started = False
    shutdown_status: int | None = None

    def submit_generation_probe(label: str) -> tuple[str, dict[str, Any]]:
        response = client.post_get_response(
            "api/actions/last-good/generation-probe/run",
            {},
            {
                ASYNC_TIMEOUT_HEADER: "0",
                REQUEST_ID_HEADER: f"rollback-{label}-{uuid.uuid4().hex}",
            },
        )
        run_id = response.headers.get(RUN_ID_HEADER)
        assert run_id, response.headers
        run_ids.append(run_id)
        record = _wait_for(
            f"{label} Run reached a terminal state",
            lambda: (
                row
                if (row := _read_run(db_path, run_id)) and row["status"] in (2, 3)
                else None
            ),
        )
        return run_id, record

    try:
        action_server_process.start(
            timeout=120,
            actions_sync=True,
            cwd=package_dir,
            db_file="server.db",
            add_shutdown_api=True,
            min_processes=0,
            max_processes=1,
            reuse_processes=True,
            additional_args=["--auto-reload"],
            env=runtime_env,
        )
        server_started = True
        package_name = package_dir.name
        initial_runtime = _wait_for(
            "initial ActionPackage runtime descriptor",
            lambda: _read_package_runtime(db_path, package_name),
        )
        assert initial_runtime["kind"] == "rcc"
        assert initial_runtime["rcc_version"] == RCC_VERSION
        assert initial_runtime["trust_carrier_identity"] == trust_carrier_identity
        artifact_digest = initial_runtime["artifact_digest"]
        environment_fingerprint = initial_runtime["environment_fingerprint"]
        source_generation = initial_runtime["source_generation"]
        source_store = action_server_process.datadir / ".rcc-runtime-sources"
        package_store = source_store / hashlib.sha256(package_name.encode("utf-8")).hexdigest()
        initial_source = _read_package_directory(db_path, package_name)
        assert initial_source is not None and initial_source.is_absolute()
        assert initial_source.is_relative_to(package_store)
        assert "last-good" in (initial_source / "action.py").read_text(
            encoding="utf-8"
        )
        evidence["package_id"] = initial_runtime["package_id"]
        evidence["artifact_digest"] = artifact_digest
        evidence["environment_fingerprint"] = environment_fingerprint
        evidence["source_generation"] = source_generation
        evidence["source_snapshot_before"] = str(initial_source)

        trace_before_first = len(_rcc_trace(trace_path))
        first_response = client.post_get_response(
            "api/actions/last-good/generation-probe/run",
            {},
            {
                ASYNC_TIMEOUT_HEADER: "0",
                REQUEST_ID_HEADER: f"rollback-before-{uuid.uuid4().hex}",
            },
        )
        first_run_id = first_response.headers.get(RUN_ID_HEADER)
        assert first_run_id, first_response.headers
        run_ids.append(first_run_id)
        _wait_for("last-good Action entered", started_path.is_file)
        first_run_running = _wait_for(
            "last-good Run running",
            lambda: (
                row
                if (row := _read_run(db_path, first_run_id))
                and row["status"] == 1
                else None
            ),
        )
        evidence["first_run_running"] = first_run_running
        first_exec = _exec_record_since(_rcc_trace(trace_path), trace_before_first)
        assert first_exec, "no RCC env exec wrapper was observed for the first Run"
        wrapper_args = first_exec["args"]
        assert "--permissive-local" in wrapper_args
        provider_index = wrapper_args.index("--provider")
        assert wrapper_args[provider_index + 1] == "local"
        receipt_index = wrapper_args.index("--receipt-file")
        worker_receipt_path = Path(wrapper_args[receipt_index + 1])
        worker_pid = first_exec["pid"]
        worker_tree = _process_tree(worker_pid)
        assert len(worker_tree) > 1, "no live RCC worker descendants were observed"
        evidence["worker_pid"] = worker_pid
        evidence["worker_tree_before_failure"] = worker_tree
        evidence["worker_receipt_path"] = str(worker_receipt_path)

        initial_descriptor = _read_package_runtime(db_path, package_name)
        assert initial_descriptor == initial_runtime
        provider_ops_before = _environment_operations(_rcc_trace(trace_path))

        invalid_source = tmp_path / "action.py.invalid"
        invalid_source.write_text(
            "from actions import action\n\n"
            "@action\n"
            "def generation_probe(:\n"
            "    return 'broken'\n",
            encoding="utf-8",
        )
        invalid_source.replace(action_file)
        evidence["invalid_source_sha256"] = hashlib.sha256(
            action_file.read_bytes()
        ).hexdigest()

        server_log_path = action_server_process.datadir / "server_log.txt"

        def import_failure_observed():
            combined = action_server_process.get_stdout() + action_server_process.get_stderr()
            if server_log_path.is_file():
                combined += server_log_path.read_text(encoding="utf-8", errors="replace")
            return (
                "It was not possible to list the actions." in combined
                and "Unable to do auto-reload (actions could not be imported)." in combined
            )

        _wait_for("auto-reload import failure diagnostic", import_failure_observed)
        after_failure_descriptor = _read_package_runtime(db_path, package_name)
        assert after_failure_descriptor == initial_runtime
        assert _read_package_directory(db_path, package_name) == initial_source
        assert [path for path in package_store.iterdir() if path.is_dir()] == [
            initial_source
        ]
        evidence["descriptor_preserved"] = True
        evidence["source_snapshot_preserved"] = str(initial_source)
        evidence["snapshot_directories_after_failure"] = [
            str(path) for path in package_store.iterdir() if path.is_dir()
        ]
        assert _process_identity_exists(worker_tree[0]), (
            "in-flight last-good worker was replaced after import failure"
        )
        evidence["same_last_good_worker_during_failure"] = _process_identity_exists(
            worker_tree[0]
        )

        release_path.write_text("release", encoding="utf-8")
        first_run = _wait_for(
            "last-good Run passed after import failure",
            lambda: (
                row
                if (row := _read_run(db_path, first_run_id)) and row["status"] == 2
                else None
            ),
        )
        assert first_run["result"] == "last-good"
        assert first_run["status"] == 2
        evidence["first_run"] = first_run
        second_run_id, second_run = submit_generation_probe("after-import-failure")
        assert second_run_id != first_run_id
        evidence["second_run"] = second_run
        descriptor_after_second_run = _read_package_runtime(db_path, package_name)
        evidence["descriptor_preserved_after_second_run"] = (
            descriptor_after_second_run == initial_runtime
        )
        same_worker_after_failure = _process_identity_exists(worker_tree[0])
        evidence["same_last_good_worker_after_failure"] = same_worker_after_failure
        provider_ops_after = _environment_operations(_rcc_trace(trace_path))
        evidence["provider_ops_before_failure"] = provider_ops_before
        evidence["provider_ops_after_failure"] = provider_ops_after
        assert second_run["status"] == 2 and second_run["result"] == "last-good"
        assert descriptor_after_second_run == initial_runtime
        assert provider_ops_after == provider_ops_before

        recovered_source = tmp_path / "action.py.recovered"
        recovered_source.write_text(
            "from actions import action\n\n"
            "@action\n"
            "def generation_probe() -> str:\n"
            "    return 'recovered-generation'\n",
            encoding="utf-8",
        )
        recovered_source.replace(action_file)

        def read_recovered_generation():
            runtime = _read_package_runtime(db_path, package_name)
            source = _read_package_directory(db_path, package_name)
            if (
                runtime
                and runtime["source_generation"] != source_generation
                and source
                and source != initial_source
                and source.is_relative_to(package_store)
                and (source / "action.py").is_file()
                and "recovered-generation"
                in (source / "action.py").read_text(encoding="utf-8")
            ):
                return runtime, source
            return None

        recovered_runtime, recovered_snapshot = _wait_for(
            "valid source recovery snapshot", read_recovered_generation
        )
        assert recovered_runtime["artifact_digest"] == artifact_digest
        assert recovered_runtime["environment_fingerprint"] == environment_fingerprint
        evidence["recovered_source_generation"] = recovered_runtime["source_generation"]
        evidence["recovered_source_snapshot"] = str(recovered_snapshot)

        trace_before_recovery_run = len(_rcc_trace(trace_path))
        recovered_run_id, recovered_run = submit_generation_probe("after-recovery")
        evidence["recovered_run"] = recovered_run
        recovery_exec = _wait_for(
            "recovered-generation RCC worker",
            lambda: _exec_record_since(_rcc_trace(trace_path), trace_before_recovery_run),
        )
        recovery_tree = _process_tree(recovery_exec["pid"])
        assert recovered_run["status"] == 2
        assert recovered_run["result"] == "recovered-generation"
        evidence["recovered_wrapper_pid"] = recovery_exec["pid"]
        evidence["recovered_wrapper_tree_before_shutdown"] = recovery_tree
        provider_ops_after_recovery = _environment_operations(_rcc_trace(trace_path))
        evidence["provider_ops_after_recovery"] = provider_ops_after_recovery
        assert provider_ops_after_recovery == provider_ops_before

        exec_records = [
            item
            for item in _rcc_trace(trace_path)
            if item["args"][:2] == ["env", "exec"]
            and "--receipt-file" in item["args"]
        ]
        evidence["env_exec_wrapper_pids_before_shutdown"] = [
            item["pid"] for item in exec_records
        ]

        shutdown_response = requests.post(
            client.build_full_url("api/shutdown/"),
            params={"timeout": 5},
            timeout=10,
        )
        shutdown_status = shutdown_response.status_code
        evidence["shutdown_http_status"] = shutdown_status
        _wait_for(
            "Runtime process shutdown",
            lambda: action_server_process.process.returncode is not None,
            timeout=15,
        )
        evidence["runtime_process_exit_code"] = action_server_process.process.returncode
        _wait_for(
            "last-good RCC worker tree reaped",
            lambda: True if _old_process_tree_reaped(worker_tree) else None,
            timeout=20,
        )
        _wait_for(
            "recovered RCC worker tree reaped",
            lambda: True if _old_process_tree_reaped(recovery_tree) else None,
            timeout=20,
        )
        evidence["worker_trees_observed_absent"] = {
            "last_good": worker_tree,
            "recovered": recovery_tree,
        }

        exec_records = [
            item
            for item in _rcc_trace(trace_path)
            if item["args"][:2] == ["env", "exec"]
            and "--receipt-file" in item["args"]
        ]
        receipt_paths = [
            Path(item["args"][item["args"].index("--receipt-file") + 1])
            for item in exec_records
        ]
        _wait_for(
            "all RCC worker receipts",
            lambda: True if receipt_paths and all(path.is_file() for path in receipt_paths) else None,
        )
        terminal_receipts = [
            json.loads(path.read_text(encoding="utf-8")) for path in receipt_paths
        ]
        evidence["worker_receipt_paths"] = [str(path) for path in receipt_paths]
        evidence["rcc_receipts"] = terminal_receipts
        evidence["status"] = "PASS" if (
            second_run["status"] == 2
            and second_run["result"] == "last-good"
            and descriptor_after_second_run == initial_runtime
            and recovered_run["status"] == 2
            and recovered_run["result"] == "recovered-generation"
            and recovered_runtime["source_generation"] != source_generation
            and recovered_runtime["artifact_digest"] == artifact_digest
            and provider_ops_after == provider_ops_before
            and provider_ops_after_recovery == provider_ops_before
            and worker_pid in [item["pid"] for item in exec_records]
            and all(
                receipt.get("artifactDigest") == artifact_digest
                and receipt.get("verification", {}).get("valid") is True
                and receipt.get("leaseId")
                and receipt.get("status") == "completed"
                and receipt.get("exitCode") == 0
                for receipt in terminal_receipts
            )
        ) else "FAIL"
        assert evidence["status"] == "PASS", (
            "last-good Action did not remain usable after import failure; "
            f"persisted Run={second_run}, Runtime exit="
            f"{action_server_process.process.returncode}"
        )
    except Exception as exc:
        evidence["status"] = "FAIL"
        evidence["failure_type"] = type(exc).__name__
        evidence["failure"] = str(exc)[:1000]
        raise
    finally:
        if server_started and action_server_process.process.returncode is None:
            try:
                requests.post(
                    client.build_full_url("api/shutdown/"),
                    params={"timeout": 5},
                    timeout=10,
                )
            except requests.RequestException:
                evidence["cleanup_shutdown_request"] = "NOT_CONFIRMED"
        evidence["rcc_trace"] = _rcc_trace(trace_path)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
