"""Exercise Work Items browser states through a selected native Runtime."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import stat
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


def packaged_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        metadata = path.lstat()
        digest.update(
            relative + b"\0" + str(stat.S_IMODE(metadata.st_mode)).encode() + b"\0"
        )
        if path.is_symlink():
            digest.update(b"link\0" + os.readlink(path).encode("utf-8") + b"\0")
        elif path.is_dir():
            digest.update(b"directory\0")
        elif path.is_file():
            digest.update(b"file\0" + bytes.fromhex(sha256(path)))
        else:
            raise AssertionError(f"unsupported packaged artifact entry: {relative!r}")
    return digest.hexdigest()


def packaged_files_sha256(
    root: Path, *, exclude_root_files: set[str] | None = None
) -> str:
    excluded = exclude_root_files or set()
    digest = hashlib.sha256()
    entries = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    )
    for path in entries:
        relative = path.relative_to(root).as_posix()
        if "/" not in relative and relative in excluded:
            continue
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def packaged_runtime_identity() -> tuple[Path, str, str, str, str, dict]:
    executable_value = os.environ.get("DAKOTA_WORKITEMS_UI_EXECUTABLE")
    source_sha = os.environ.get("DAKOTA_WORKITEMS_UI_SOURCE_SHA", "")
    runtime_kind = os.environ.get("DAKOTA_WORKITEMS_UI_RUNTIME_KIND", "frozen")
    manifest_value = os.environ.get("DAKOTA_WORKITEMS_UI_BUILD_MANIFEST")
    assert executable_value and manifest_value
    assert re.fullmatch(r"[0-9a-f]{40}", source_sha)
    assert runtime_kind in {"frozen", "go-wrapper"}

    executable = Path(executable_value).resolve()
    manifest = json.loads(Path(manifest_value).read_text(encoding="utf-8"))
    assert manifest.get("source_sha") == source_sha
    assert manifest.get("platform") == platform.system()
    artifact = manifest.get("artifacts", {}).get(runtime_kind, {})
    expected_path = {
        "frozen": "dist/action-server/action-server",
        "go-wrapper": "dist/final/action-server",
    }[runtime_kind]
    assert artifact.get("path") == expected_path
    executable_sha = sha256(executable)
    assert artifact.get("sha256") == executable_sha
    return (
        executable,
        source_sha,
        executable_sha,
        manifest["architecture"],
        runtime_kind,
        artifact,
    )


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


def validate_browser_stage_result(returncode: int, receipt: dict) -> dict:
    if returncode != 0 or receipt.get("status") != "PASS":
        raise AssertionError(
            json.dumps({"returncode": returncode, "receipt": receipt}, sort_keys=True)
        )
    return receipt


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
    return validate_browser_stage_result(result.returncode, receipt)


def test_browser_nonzero_exit_preserves_nested_failure_receipt() -> None:
    receipt = {
        "status": "FAIL",
        "stage": "normal",
        "phase": "keyboard_create_dialog",
        "states": {"trigger": {"aria_haspopup": None}},
    }

    with pytest.raises(AssertionError) as error:
        validate_browser_stage_result(1, receipt)

    assert json.loads(str(error.value)) == {"returncode": 1, "receipt": receipt}


def wrapper_home_environment(runtime_home: Path) -> dict[str, str]:
    if platform.system() == "Windows":
        return {"LOCALAPPDATA": str(runtime_home / "localappdata")}
    return {"HOME": str(runtime_home)}


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
            additional_args=["--address=127.0.0.1", f"--api-key={api_key}"],
            env={
                "ACTIONS_HOME": str(runtime_home),
                "ROBOCORP_HOME": str(runtime_home),
                "ACTIONS_SKIP_UPDATE_CHECK": "1",
                **wrapper_home_environment(runtime_home),
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
    (
        executable,
        source_sha,
        executable_sha,
        architecture,
        runtime_kind,
        artifact,
    ) = packaged_runtime_identity()
    package_root = executable.parent if runtime_kind == "frozen" else None
    package_tree_sha = packaged_tree_sha256(package_root) if package_root else None
    embedded_files_sha = artifact.get("embedded_files_sha256")
    assets_zip_sha = artifact.get("assets_zip_sha256")
    wrapper_source_sha = artifact.get("wrapper_source_sha256")
    embedded_frozen_tree_sha = artifact.get("frozen_package_tree_sha256")
    if runtime_kind == "go-wrapper":
        for digest in (
            embedded_files_sha,
            assets_zip_sha,
            wrapper_source_sha,
            embedded_frozen_tree_sha,
        ):
            assert isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
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
        "package_tree_sha256": package_tree_sha,
        "embedded_files_sha256": embedded_files_sha,
        "assets_zip_sha256": assets_zip_sha,
        "wrapper_source_sha256": wrapper_source_sha,
        "embedded_frozen_tree_sha256": embedded_frozen_tree_sha,
        "runtime_kind": runtime_kind,
        "runtime_version": None,
        "platform": platform.system(),
        "architecture": architecture,
        "action_server_database": "server.db",
        "work_items_database": "datadir/workitems.db",
        "storage_fault_fixture": "test-owned datadir/workitems.db; Action Server DB remains server.db",
        "browser_stages": [],
        "states_not_run": STATES_NOT_RUN,
    }
    process: ActionServerProcess | None = None
    try:
        version_env = os.environ.copy()
        version_env.update(wrapper_home_environment(runtime_home))
        version_env["ACTIONS_SKIP_UPDATE_CHECK"] = "1"
        version = subprocess.run(
            [str(executable), "version"],
            cwd=project,
            env=version_env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert version.returncode == 0
        receipt["runtime_version"] = version.stdout.strip()

        process = start_native_runtime(datadir, project, runtime_home, api_key)
        if runtime_kind == "go-wrapper":
            if platform.system() == "Windows":
                extracted_root = (
                    runtime_home
                    / "localappdata"
                    / "actions"
                    / "bin"
                    / "action-server"
                    / "internal"
                    / receipt["runtime_version"]
                )
            else:
                extracted_root = (
                    runtime_home
                    / ".actions"
                    / "bin"
                    / "action-server"
                    / "internal"
                    / receipt["runtime_version"]
                )
            assert extracted_root.is_dir()
            assert extracted_root.resolve().is_relative_to(runtime_home.resolve())
            assert (extracted_root / "app_hash").read_text().strip() == assets_zip_sha
            extracted_files_sha = packaged_files_sha256(
                extracted_root,
                exclude_root_files={"app_hash", "extract.lock", "lastLaunchTouch"},
            )
            assert extracted_files_sha == embedded_files_sha
            receipt["wrapper_extraction"] = {
                "path_relative_to_runtime_home": extracted_root.relative_to(
                    runtime_home
                ).as_posix(),
                "app_hash_matches_embedded_archive": True,
                "extracted_files_sha256": extracted_files_sha,
            }
        origin = f"http://{process.host}:{process.port}"
        normal = run_browser_stage(
            node,
            "normal",
            tmp_path / "browser-profile-normal",
            api_key,
            origin,
        )
        receipt["browser_stages"].append(normal)
        assert normal.get("status") == "PASS", json.dumps(normal)

        work_items_db = datadir / "workitems.db"
        assert work_items_db.is_file()
        for suffix in ("-wal", "-shm", "-journal"):
            (datadir / f"workitems.db{suffix}").unlink(missing_ok=True)
        work_items_db.write_bytes(b"synthetic corrupt SQLite database")
        storage_error = run_browser_stage(
            node,
            "storage-error",
            tmp_path / "browser-profile-storage-error",
            api_key,
            origin,
        )
        receipt["browser_stages"].append(storage_error)
        assert storage_error.get("status") == "PASS", json.dumps(storage_error)
        if package_root is not None:
            assert packaged_tree_sha256(package_root) == package_tree_sha
        if runtime_kind == "go-wrapper":
            assert (
                packaged_files_sha256(
                    extracted_root,
                    exclude_root_files={"app_hash", "extract.lock", "lastLaunchTouch"},
                )
                == embedded_files_sha
            )
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
