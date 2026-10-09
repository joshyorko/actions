"""Exercise Work Items browser states through a selected native Runtime."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from actions.server._selftest import ActionServerProcess

PACKAGE = Path(__file__).resolve().parents[2]
FRONTEND = PACKAGE / "frontend"
BROWSER_SCRIPT = FRONTEND / "scripts" / "native-workitems-ui-acceptance.mjs"
STATES_NOT_RUN = {
    "authorization_denial_ui": "separate #153 authentication ownership",
    "missing_runtime_support": "cannot be induced without mutating the package",
    "generic_http_500": "no supported native backend fault fixture",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def packaged_runtime_identity() -> tuple[Path, str, str, str]:
    executable_value = os.environ.get("DAKOTA_WORKITEMS_UI_EXECUTABLE")
    source_sha = os.environ.get("DAKOTA_WORKITEMS_UI_SOURCE_SHA", "")
    manifest_value = os.environ.get("DAKOTA_WORKITEMS_UI_BUILD_MANIFEST")
    assert executable_value and manifest_value
    assert re.fullmatch(r"[0-9a-f]{40}", source_sha)

    executable = Path(executable_value).resolve()
    manifest = json.loads(Path(manifest_value).read_text(encoding="utf-8"))
    assert manifest.get("source_sha") == source_sha
    assert manifest.get("platform") == platform.system()
    wrapper = manifest.get("artifacts", {}).get("go-wrapper", {})
    assert wrapper.get("path") == "dist/final/action-server"
    executable_sha = sha256(executable)
    assert wrapper.get("sha256") == executable_sha
    return executable, source_sha, executable_sha, manifest["architecture"]


def write_receipt(receipt: dict) -> None:
    destination_value = os.environ.get("DAKOTA_WORKITEMS_UI_RECEIPT")
    if not destination_value:
        return
    destination = Path(destination_value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, delete=False
        ) as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
            temporary = Path(stream.name)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run_browser_stage(
    node: str,
    stage: str,
    profile: Path,
    api_key: str,
    origin: str,
) -> dict:
    result = subprocess.run(
        [node, str(BROWSER_SCRIPT)],
        cwd=FRONTEND,
        input=json.dumps(
            {
                "origin": origin,
                "api_key": api_key,
                "profile": str(profile),
                "stage": stage,
            }
        ),
        text=True,
        capture_output=True,
        timeout=150,
        check=False,
    )
    if len(result.stdout) > 65536:
        raise AssertionError("browser receipt exceeded its size limit")
    try:
        receipt = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise AssertionError("browser acceptance returned an invalid receipt") from None
    assert result.returncode == 0, receipt
    assert receipt.get("status") == "PASS", receipt
    return receipt


def start_native_runtime(
    datadir: Path, project: Path, runtime_home: Path, api_key: str
) -> ActionServerProcess:
    process = ActionServerProcess(datadir)
    try:
        process.start(
            db_file="server.db",
            cwd=project,
            timeout=90,
            min_processes=0,
            max_processes=1,
            port=0,
            additional_args=[f"--api-key={api_key}"],
            env={
                "ACTIONS_HOME": str(runtime_home),
                "ROBOCORP_HOME": str(runtime_home),
                "ACTIONS_SKIP_UPDATE_CHECK": "1",
            },
        )
    except Exception as error:
        raise AssertionError(
            f"packaged Runtime startup failed ({type(error).__name__})"
        ) from None
    return process


@pytest.mark.integration_test
def test_packaged_work_items_ui_create_keyboard_narrow_and_storage_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable, source_sha, executable_sha, architecture = packaged_runtime_identity()
    node = os.environ.get("DAKOTA_WORKITEMS_UI_NODE") or shutil.which("node")
    assert node is not None
    monkeypatch.setenv(
        "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE", str(executable)
    )

    project = tmp_path / "project"
    datadir = tmp_path / "datadir"
    runtime_home = tmp_path / "runtime-home"
    for directory in (project, datadir, runtime_home):
        directory.mkdir()

    api_key = secrets.token_urlsafe(32)
    receipt = {
        "schema_version": 1,
        "status": "IN_PROGRESS",
        "source_sha": source_sha,
        "executable_sha256": executable_sha,
        "runtime_version": None,
        "platform": platform.system(),
        "architecture": architecture,
        "action_server_database": "server.db",
        "work_items_database": "datadir/workitems.db",
        "browser_stages": [],
        "states_not_run": STATES_NOT_RUN,
    }
    process: ActionServerProcess | None = None
    try:
        version = subprocess.run(
            [str(executable), "version"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert version.returncode == 0
        receipt["runtime_version"] = version.stdout.strip()

        process = start_native_runtime(datadir, project, runtime_home, api_key)
        normal = run_browser_stage(
            node,
            "normal",
            tmp_path / "browser-profile-normal",
            api_key,
            f"http://{process.host}:{process.port}",
        )
        receipt["browser_stages"].append(normal)
        process.stop()
        process = None

        work_items_db = datadir / "workitems.db"
        assert work_items_db.is_file()
        for suffix in ("-wal", "-shm", "-journal"):
            (datadir / f"workitems.db{suffix}").unlink(missing_ok=True)
        work_items_db.write_bytes(b"synthetic corrupt SQLite database")

        process = start_native_runtime(datadir, project, runtime_home, api_key)
        storage_error = run_browser_stage(
            node,
            "storage-error",
            tmp_path / "browser-profile-storage-error",
            api_key,
            f"http://{process.host}:{process.port}",
        )
        receipt["browser_stages"].append(storage_error)
        receipt["status"] = "PASS_BOUNDED"
        write_receipt(receipt)
    except Exception as error:
        receipt["status"] = "FAIL"
        receipt["failure_type"] = type(error).__name__
        write_receipt(receipt)
        raise
    finally:
        if process is not None:
            process.stop()
