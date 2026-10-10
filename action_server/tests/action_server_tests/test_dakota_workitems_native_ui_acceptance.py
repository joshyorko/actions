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
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, TypedDict, TypeGuard

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


class PackageTreeEntry(TypedDict):
    path: str
    kind: str
    mode: int
    link_target: str | None
    content_sha256: str | None


class PackageTreeChange(TypedDict):
    path: str
    fields: list[str]
    baseline: PackageTreeEntry
    observed: PackageTreeEntry


class PackageTreeDifference(TypedDict):
    added: list[PackageTreeEntry]
    removed: list[PackageTreeEntry]
    changed: list[PackageTreeChange]


class RuntimeTreeDelta(PackageTreeDifference):
    valid: bool
    failure_reason: str | None
    runtime_generated_state: list[PackageTreeEntry]
    rcc_version: str
    expected_rcc_path: str


class CleanupObservation(TypedDict, total=False):
    wrapper_started: bool
    wrapper_reaped: bool
    live_descendant_count: int
    zombie_descendant_count: int
    descendant_snapshot_complete: bool
    control_error_count: int
    control_failure_type: str
    snapshot_failure_type: str | None
    stop_failure_type: str | None


def is_string_keyed_object(value: object) -> TypeGuard[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


def receipt_section(receipt: Mapping[str, object], key: str) -> dict[str, object]:
    value = receipt.get(key)
    if not is_string_keyed_object(value):
        raise AssertionError(f"acceptance receipt field {key} is not an object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def packaged_tree_sha256(
    root: Path, *, exclude_root_files: set[str] | None = None
) -> str:
    excluded = exclude_root_files or set()
    digest = hashlib.sha256()
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        if b"/" not in relative and relative.decode("utf-8") in excluded:
            if path.is_file():
                continue
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


def packaged_tree_inventory(
    root: Path, *, exclude_root_files: set[str] | None = None
) -> list[PackageTreeEntry]:
    excluded = exclude_root_files or set()
    inventory: list[PackageTreeEntry] = []
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix()
        if "/" not in relative and relative in excluded and path.is_file():
            continue
        metadata = path.lstat()
        if path.is_symlink():
            kind = "symlink"
            link_target = os.readlink(path)
        elif path.is_dir():
            kind = "directory"
            link_target = None
        elif path.is_file():
            kind = "file"
            link_target = None
        else:
            raise AssertionError("unsupported packaged artifact entry")
        inventory.append(
            {
                "path": relative,
                "kind": kind,
                "mode": stat.S_IMODE(metadata.st_mode),
                "link_target": link_target,
                "content_sha256": sha256(path) if path.is_file() else None,
            }
        )
    return inventory


def copy_frozen_package_tree(source: Path, destination: Path) -> Path:
    return shutil.copytree(
        source, destination, symlinks=True, copy_function=shutil.copy2
    )


def write_tree_inventory_snapshot(
    receipt_value: str | None,
    *,
    stage: str,
    source_sha: str,
    runtime_kind: str,
    executable_sha: str,
    manifest_path: Path,
    package_root: Path,
    exclude_root_files: set[str] | None = None,
) -> None:
    if not receipt_value:
        return
    receipt_path = Path(receipt_value)
    inventory_path = receipt_path.with_name(
        f"{receipt_path.stem}-{stage}-tree-inventory.json"
    )
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha": source_sha,
                "runtime_kind": runtime_kind,
                "stage": stage,
                "platform": platform.system(),
                "executable_sha256": executable_sha,
                "manifest_sha256": sha256(manifest_path),
                "package_tree_sha256": packaged_tree_sha256(
                    package_root, exclude_root_files=exclude_root_files
                ),
                "entries": packaged_tree_inventory(
                    package_root, exclude_root_files=exclude_root_files
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def compare_package_tree_inventories(
    baseline: list[PackageTreeEntry], observed: list[PackageTreeEntry]
) -> PackageTreeDifference:
    before = {entry["path"]: entry for entry in baseline}
    after = {entry["path"]: entry for entry in observed}
    added = [after[path] for path in sorted(after.keys() - before.keys())]
    removed = [before[path] for path in sorted(before.keys() - after.keys())]
    changed: list[PackageTreeChange] = []
    for path in sorted(before.keys() & after.keys()):
        fields = [
            field
            for field in ("kind", "mode", "link_target", "content_sha256")
            if before[path].get(field) != after[path].get(field)
        ]
        if fields:
            changed.append(
                {
                    "path": path,
                    "fields": fields,
                    "baseline": before[path],
                    "observed": after[path],
                }
            )
    return {"added": added, "removed": removed, "changed": changed}


def classify_runtime_tree_delta(
    baseline: list[PackageTreeEntry],
    observed: list[PackageTreeEntry],
    *,
    platform_name: str,
) -> RuntimeTreeDelta:
    from actions.server._download_rcc import RCC_VERSION

    difference = compare_package_tree_inventories(baseline, observed)
    bin_path = "_internal/actions/server/bin"
    executable_path = f"{bin_path}/rcc-{RCC_VERSION}"
    if platform_name == "Windows":
        executable_path += ".exe"
    allowed_paths = {bin_path, executable_path}
    added_by_path = {entry["path"]: entry for entry in difference["added"]}
    reason = None
    if difference["removed"] or difference["changed"]:
        reason = "immutable_entry_changed"
    elif set(added_by_path) - allowed_paths:
        reason = "unrecognized_runtime_generated_entry"
    elif bin_path in added_by_path and executable_path not in added_by_path:
        reason = "runtime_rcc_directory_without_binary"
    elif executable_path in added_by_path:
        binary = added_by_path[executable_path]
        if (
            binary.get("kind") != "file"
            or re.fullmatch(r"[0-9a-f]{64}", str(binary.get("content_sha256", "")))
            is None
        ):
            reason = "runtime_rcc_binary_identity_missing"
        elif bin_path not in added_by_path and bin_path not in {
            entry["path"] for entry in baseline
        }:
            reason = "runtime_rcc_parent_directory_missing"
    return {
        "valid": reason is None,
        "failure_reason": reason,
        "runtime_generated_state": (difference["added"] if reason is None else []),
        "rcc_version": RCC_VERSION,
        "expected_rcc_path": executable_path,
        **difference,
    }


def record_postruntime_tree_observation(
    receipt: dict[str, object],
    *,
    package_root: Path,
    baseline_entries: list[PackageTreeEntry],
    baseline_tree_sha256: str,
    baseline_kind: str,
    stage: str,
    exclude_root_files: set[str] | None,
    immutable_package_root: Path,
    immutable_package_tree_sha256: str,
    receipt_value: str | None,
    source_sha: str,
    runtime_kind: str,
    executable_sha: str,
    manifest_path: Path,
) -> None:
    observed_sha = packaged_tree_sha256(
        package_root, exclude_root_files=exclude_root_files
    )
    observed_entries = packaged_tree_inventory(
        package_root, exclude_root_files=exclude_root_files
    )
    write_tree_inventory_snapshot(
        receipt_value,
        stage=stage,
        source_sha=source_sha,
        runtime_kind=runtime_kind,
        executable_sha=executable_sha,
        manifest_path=manifest_path,
        package_root=package_root,
        exclude_root_files=exclude_root_files,
    )
    delta = classify_runtime_tree_delta(
        baseline_entries, observed_entries, platform_name=platform.system()
    )
    immutable_tree_sha = packaged_tree_sha256(immutable_package_root)
    immutable_tree_unchanged = immutable_tree_sha == immutable_package_tree_sha256
    failure_reason = delta["failure_reason"]
    if failure_reason is None and not immutable_tree_unchanged:
        failure_reason = "immutable_build_artifact_changed"
    validation_passed = delta["valid"] and immutable_tree_unchanged
    report_path = None
    if receipt_value:
        receipt_path = Path(receipt_value)
        report = receipt_path.with_name(f"{receipt_path.stem}-{stage}-tree-diff.json")
        report.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_sha": source_sha,
                    "runtime_kind": runtime_kind,
                    "runtime_tree_kind": baseline_kind,
                    "platform": platform.system(),
                    "executable_sha256": executable_sha,
                    "manifest_sha256": sha256(manifest_path),
                    "expected_runtime_tree_sha256": baseline_tree_sha256,
                    "observed_package_tree_sha256": observed_sha,
                    "expected_immutable_build_tree_sha256": immutable_package_tree_sha256,
                    "observed_immutable_build_tree_sha256": immutable_tree_sha,
                    "immutable_build_tree_unchanged": immutable_tree_unchanged,
                    "runtime_delta_valid": validation_passed,
                    "runtime_delta_failure_reason": failure_reason,
                    "runtime_generated_contract": {
                        "rcc_version": delta["rcc_version"],
                        "rcc_path": delta["expected_rcc_path"],
                    },
                    "runtime_generated_state": delta["runtime_generated_state"],
                    "added": delta["added"],
                    "removed": delta["removed"],
                    "changed": delta["changed"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        report_path = report.name
    receipt[f"{stage}_tree_sha256"] = observed_sha
    receipt["immutable_build_tree_sha256_after_runtime"] = immutable_tree_sha
    receipt["post_runtime_tree_diff"] = {
        "added_count": len(delta["added"]),
        "removed_count": len(delta["removed"]),
        "changed_count": len(delta["changed"]),
        "report_path": report_path,
    }
    receipt["post_runtime_tree_validation"] = {
        "valid": validation_passed,
        "failure_reason": failure_reason,
        "immutable_build_tree_unchanged": immutable_tree_unchanged,
        "rcc_version": delta["rcc_version"],
        "runtime_generated_state": delta["runtime_generated_state"],
    }


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


def wrapper_source_sha256(root: Path, relative_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative in relative_paths:
        path = root / relative
        assert path.is_file(), f"wrapper source input is missing: {relative}"
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def require_sha256(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise AssertionError(f"manifest field {field} is missing or invalid")
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise AssertionError(f"manifest field {field} is missing or invalid")
    return value


def require_measured_digest(
    artifact: Mapping[str, object], field: str, measured: str
) -> None:
    recorded = artifact.get(field)
    recorded = require_sha256(recorded, field)
    assert recorded == measured, f"manifest field {field} does not match build input"


class NativeRuntimeStartupError(AssertionError):
    def __init__(
        self,
        primary_error: Exception,
        cleanup_error: Exception | None = None,
        cleanup_observation: CleanupObservation | None = None,
    ):
        self.primary_error = primary_error
        self.cleanup_error = cleanup_error
        self.cleanup_observation = cleanup_observation
        message = f"packaged Runtime startup failed ({type(primary_error).__name__})"
        if cleanup_error is not None:
            message += f"; cleanup failed ({type(cleanup_error).__name__})"
        super().__init__(message)


class NativeRuntimeCleanupError(AssertionError):
    def __init__(
        self,
        observation: CleanupObservation,
        stop_error: BaseException | None = None,
    ):
        self.observation = observation
        self.stop_error = stop_error
        detail = (
            f"wrapper_reaped={observation['wrapper_reaped']}, "
            f"live_descendants={observation['live_descendant_count']}, "
            f"snapshot_complete={observation['descendant_snapshot_complete']}, "
            f"control_errors={observation['control_error_count']}"
        )
        if stop_error is not None:
            detail += f", stop_error={type(stop_error).__name__}"
        super().__init__(f"native Runtime cleanup was not observed complete ({detail})")


def packaged_artifact_relative_path(runtime_kind: str, platform_name: str) -> str:
    executable = {
        "frozen": "dist/action-server/action-server",
        "go-wrapper": "dist/final/action-server",
    }[runtime_kind]
    return executable + (".exe" if platform_name == "Windows" else "")


@pytest.mark.parametrize(
    ("runtime_kind", "platform_name", "expected_path"),
    [
        ("frozen", "Linux", "dist/action-server/action-server"),
        ("go-wrapper", "Linux", "dist/final/action-server"),
        ("frozen", "Windows", "dist/action-server/action-server.exe"),
        ("go-wrapper", "Windows", "dist/final/action-server.exe"),
    ],
)
def test_native_manifest_executable_paths_match_platform(
    runtime_kind: str, platform_name: str, expected_path: str
) -> None:
    assert packaged_artifact_relative_path(runtime_kind, platform_name) == expected_path


@pytest.mark.parametrize(
    ("platform_name", "expected"),
    [
        (
            "Windows",
            Path("localappdata/actions/bin/action-server/internal/1.2.3"),
        ),
        ("Linux", Path(".actions/bin/action-server/internal/1.2.3")),
        ("Darwin", Path(".actions/bin/action-server/internal/1.2.3")),
    ],
)
def test_wrapper_extraction_root_is_beneath_the_test_runtime_home(
    tmp_path: Path, platform_name: str, expected: Path
) -> None:
    root = wrapper_extraction_root(tmp_path, "1.2.3", platform_name)
    assert root == tmp_path / expected
    assert root.is_relative_to(tmp_path)


def packaged_runtime_identity() -> (
    tuple[Path, str, str, str, Literal["frozen", "go-wrapper"], dict[str, object]]
):
    executable_value = os.environ.get("DAKOTA_WORKITEMS_UI_EXECUTABLE")
    source_sha = os.environ.get("DAKOTA_WORKITEMS_UI_SOURCE_SHA", "")
    runtime_kind_value = os.environ.get("DAKOTA_WORKITEMS_UI_RUNTIME_KIND", "frozen")
    manifest_value = os.environ.get("DAKOTA_WORKITEMS_UI_BUILD_MANIFEST")
    assert executable_value and manifest_value
    assert re.fullmatch(r"[0-9a-f]{40}", source_sha)
    if runtime_kind_value == "frozen":
        runtime_kind: Literal["frozen", "go-wrapper"] = "frozen"
    elif runtime_kind_value == "go-wrapper":
        runtime_kind = "go-wrapper"
    else:
        raise AssertionError("native Runtime kind must be frozen or go-wrapper")

    executable = Path(executable_value).resolve()
    manifest_value_data: object = json.loads(
        Path(manifest_value).read_text(encoding="utf-8")
    )
    assert is_string_keyed_object(
        manifest_value_data
    ), "native manifest must be an object"
    manifest = manifest_value_data
    assert manifest.get("source_sha") == source_sha
    assert manifest.get("platform") == platform.system()
    artifacts_value = manifest.get("artifacts")
    assert is_string_keyed_object(artifacts_value), "native artifacts must be an object"
    artifact_value = artifacts_value.get(runtime_kind)
    assert is_string_keyed_object(artifact_value), "selected artifact must be an object"
    artifact = artifact_value
    expected_path = packaged_artifact_relative_path(runtime_kind, platform.system())
    assert artifact.get("path") == expected_path
    executable_sha = sha256(executable)
    assert artifact.get("sha256") == executable_sha
    frozen_package = (
        executable.parent
        if runtime_kind == "frozen"
        else executable.parents[1] / "action-server"
    )
    write_tree_inventory_snapshot(
        os.environ.get("DAKOTA_WORKITEMS_UI_RECEIPT"),
        stage="pretest",
        source_sha=source_sha,
        runtime_kind=runtime_kind,
        executable_sha=executable_sha,
        manifest_path=Path(manifest_value),
        package_root=frozen_package,
    )
    require_measured_digest(
        artifact,
        "frozen_package_tree_sha256",
        packaged_tree_sha256(frozen_package),
    )
    require_measured_digest(
        artifact, "embedded_files_sha256", packaged_files_sha256(frozen_package)
    )
    source_paths = (
        "go-wrapper/main.go",
        "go-wrapper/go.mod",
        "go-wrapper/go.sum",
    )
    assert artifact.get("wrapper_source_files") == list(source_paths)
    require_measured_digest(
        artifact,
        "wrapper_source_sha256",
        wrapper_source_sha256(PACKAGE, source_paths),
    )
    assert artifact.get("assets_zip_path") == "go-wrapper/assets/assets.zip"
    require_measured_digest(
        artifact,
        "assets_zip_sha256",
        sha256(PACKAGE / "go-wrapper/assets/assets.zip"),
    )
    architecture = manifest.get("architecture")
    assert isinstance(
        architecture, str
    ), "native manifest architecture must be a string"
    return (
        executable,
        source_sha,
        executable_sha,
        architecture,
        runtime_kind,
        artifact,
    )


def write_receipt(receipt: dict[str, object]) -> None:
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


def validate_browser_stage_result(
    returncode: int, receipt: Mapping[str, object]
) -> Mapping[str, object]:
    if returncode != 0 or receipt.get("status") != "PASS":
        raise AssertionError(
            json.dumps({"returncode": returncode, "receipt": receipt}, sort_keys=True)
        )
    return receipt


def record_browser_stage(
    acceptance_receipt: dict[str, object], browser_stage: dict[str, object]
) -> None:
    stages = acceptance_receipt.get("browser_stages")
    if not isinstance(stages, list):
        raise AssertionError("acceptance receipt browser_stages is not a list")
    stages.append(browser_stage)
    script_exit_code = browser_stage.get("script_exit_code")
    if not isinstance(script_exit_code, int):
        raise AssertionError("browser receipt script_exit_code is not an integer")
    validate_browser_stage_result(script_exit_code, browser_stage)


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
        receipt_value: object = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise AssertionError("browser acceptance returned an invalid receipt") from None
    if not is_string_keyed_object(receipt_value):
        raise AssertionError("browser acceptance returned a non-object receipt")
    receipt = receipt_value
    receipt["script_exit_code"] = result.returncode
    return receipt


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


def test_browser_stage_is_recorded_before_failure_is_raised() -> None:
    acceptance_receipt: dict[str, object] = {"browser_stages": []}
    browser_stage = {
        "status": "FAIL",
        "stage": "normal",
        "phase": "keyboard_create_dialog",
        "script_exit_code": 1,
        "states": {"trigger": {"aria_haspopup": None}},
    }

    with pytest.raises(AssertionError):
        record_browser_stage(acceptance_receipt, browser_stage)

    assert acceptance_receipt["browser_stages"] == [browser_stage]


def wrapper_home_environment(runtime_home: Path) -> dict[str, str]:
    if platform.system() == "Windows":
        return {"LOCALAPPDATA": str(runtime_home / "localappdata")}
    return {"HOME": str(runtime_home)}


def wrapper_extraction_root(
    runtime_home: Path, runtime_version: str, platform_name: str
) -> Path:
    if platform_name == "Windows":
        return (
            runtime_home
            / "localappdata"
            / "actions"
            / "bin"
            / "action-server"
            / "internal"
            / runtime_version
        )
    return (
        runtime_home
        / ".actions"
        / "bin"
        / "action-server"
        / "internal"
        / runtime_version
    )


def native_runtime_environment(runtime_home: Path) -> dict[str, str]:
    return {
        "ACTIONS_HOME": str(runtime_home),
        "ROBOCORP_HOME": str(runtime_home),
        "ACTIONS_SKIP_UPDATE_CHECK": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        **wrapper_home_environment(runtime_home),
    }


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
            env=native_runtime_environment(runtime_home),
        )
    except Exception as error:
        cleanup_receipt: dict[str, object] = {}
        cleanup_observation: CleanupObservation | None
        try:
            cleanup_observation = stop_runtime_for_acceptance(process, cleanup_receipt)
        except Exception as cleanup_error:
            cleanup_observation = (
                cleanup_error.observation
                if isinstance(cleanup_error, NativeRuntimeCleanupError)
                else None
            )
            raise NativeRuntimeStartupError(
                error, cleanup_error, cleanup_observation
            ) from None
        raise NativeRuntimeStartupError(
            error, cleanup_observation=cleanup_observation
        ) from None
    return process


def stop_runtime_for_acceptance(
    process: ActionServerProcess, receipt: dict[str, object]
) -> CleanupObservation:
    from actions.server._common.process import (
        ProcessTreeCleanupResult,
        force_kill_process_tree_until,
        snapshot_process_descendants,
    )

    runtime_process = process.process
    child = runtime_process._proc
    descendants = None
    snapshot_complete = child is None
    snapshot_failure_type = None
    if child is not None:
        try:
            descendants = snapshot_process_descendants(child.pid)
            snapshot_complete = True
        except BaseException as error:
            snapshot_failure_type = type(error).__name__

    stop_error = None
    try:
        process.stop()
    except BaseException as error:
        stop_error = error

    if child is None:
        result = ProcessTreeCleanupResult(True, (), (), ())
    else:
        try:
            result = force_kill_process_tree_until(
                child,
                descendants,
                time.monotonic() + 15,
                snapshot_complete_before_call=snapshot_complete,
            )
        except BaseException as error:
            cleanup_failure_observation: CleanupObservation = {
                "wrapper_started": True,
                "wrapper_reaped": False,
                "live_descendant_count": 0,
                "zombie_descendant_count": 0,
                "descendant_snapshot_complete": snapshot_complete,
                "control_error_count": 1,
                "control_failure_type": type(error).__name__,
                "snapshot_failure_type": snapshot_failure_type,
                "stop_failure_type": type(stop_error).__name__ if stop_error else None,
            }
            receipt["cleanup_observation"] = cleanup_failure_observation
            receipt["cleanup_failure_type"] = type(error).__name__
            receipt["status"] = "FAIL"
            raise NativeRuntimeCleanupError(
                cleanup_failure_observation, stop_error
            ) from None

    observation: CleanupObservation = {
        "wrapper_started": child is not None,
        "wrapper_reaped": result.wrapper_reaped,
        "live_descendant_count": len(result.live_descendant_pids),
        "zombie_descendant_count": len(result.zombie_descendant_pids),
        "descendant_snapshot_complete": result.descendant_snapshot_complete,
        "control_error_count": len(result.errors),
        "snapshot_failure_type": snapshot_failure_type,
        "stop_failure_type": type(stop_error).__name__ if stop_error else None,
    }
    receipt["cleanup_observation"] = observation
    if not result.execution_stopped or stop_error is not None:
        cleanup_type = (
            type(stop_error).__name__
            if stop_error is not None
            else "ProcessTreeCleanupIncomplete"
        )
        receipt["cleanup_failure_type"] = cleanup_type
        receipt["status"] = "FAIL"
        raise NativeRuntimeCleanupError(observation, stop_error) from None
    return observation


class NoOpStopActionServerProcess(ActionServerProcess):
    def stop(self) -> None:
        return None


def cleanup_test_runtime(
    datadir: Path, child: subprocess.Popen | None = None
) -> NoOpStopActionServerProcess:
    from actions.server._robo_utils.process import Process

    process = NoOpStopActionServerProcess(datadir)
    process._process = Process(["test-runtime"], cwd=datadir)
    process.process._proc = child
    return process


def test_native_runtime_startup_failure_stops_created_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class StartupProcess:
        def __init__(self, _datadir):
            self.stop_calls = 0
            self.process = type("Wrapped", (), {"_proc": None})()

        def start(self, **_kwargs):
            raise TimeoutError("startup timeout")

        def stop(self):
            self.stop_calls += 1

    created: list[StartupProcess] = []

    def create_process(datadir):
        process = StartupProcess(datadir)
        created.append(process)
        return process

    monkeypatch.setattr(sys.modules[__name__], "ActionServerProcess", create_process)
    with pytest.raises(AssertionError, match="TimeoutError"):
        start_native_runtime(tmp_path, tmp_path, tmp_path, "test-key")
    assert len(created) == 1
    assert created[0].stop_calls == 1


def test_native_runtime_disables_bytecode_writes_for_tree_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class StartupProcess:
        def __init__(self, _datadir):
            self.start_options = None

        def start(self, **kwargs):
            self.start_options = kwargs

        def stop(self):
            pass

    created: list[StartupProcess] = []

    def create_process(datadir):
        process = StartupProcess(datadir)
        created.append(process)
        return process

    monkeypatch.setattr(sys.modules[__name__], "ActionServerProcess", create_process)
    start_native_runtime(tmp_path, tmp_path, tmp_path / "runtime-home", "test-key")
    assert created[0].start_options["env"]["PYTHONDONTWRITEBYTECODE"] == "1"


def test_native_runtime_startup_preserves_cleanup_failure_type(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class StartupProcess:
        def __init__(self, _datadir):
            self.process = type("Wrapped", (), {"_proc": None})()

        def start(self, **_kwargs):
            raise TimeoutError("startup timeout")

        def stop(self):
            raise RuntimeError("cleanup detail is not emitted")

    monkeypatch.setattr(sys.modules[__name__], "ActionServerProcess", StartupProcess)
    with pytest.raises(NativeRuntimeStartupError) as error:
        start_native_runtime(tmp_path, tmp_path, tmp_path, "test-key")
    assert "TimeoutError" in str(error.value)
    assert isinstance(error.value.primary_error, TimeoutError)
    cleanup_error = error.value.cleanup_error
    assert isinstance(cleanup_error, NativeRuntimeCleanupError)
    assert isinstance(cleanup_error.stop_error, RuntimeError)


def test_missing_and_mismatched_manifest_digests_fail_closed() -> None:
    fields = (
        "embedded_files_sha256",
        "assets_zip_sha256",
        "wrapper_source_sha256",
        "frozen_package_tree_sha256",
    )
    for field in fields:
        with pytest.raises(AssertionError, match=field):
            require_measured_digest({}, field, "a" * 64)
        with pytest.raises(AssertionError, match=field):
            require_measured_digest({field: "b" * 64}, field, "a" * 64)


def test_pretest_inventory_records_relative_entry_identity(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "nested").mkdir()
    (package / "nested/module.py").write_bytes(b"measured content")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    receipt_path = tmp_path / "dakota-workitems-ui-frozen-test.json"

    write_tree_inventory_snapshot(
        str(receipt_path),
        stage="pretest",
        source_sha="a" * 40,
        runtime_kind="frozen",
        executable_sha="b" * 64,
        manifest_path=manifest_path,
        package_root=package,
    )

    inventory_path = (
        tmp_path / "dakota-workitems-ui-frozen-test-pretest-tree-inventory.json"
    )
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert inventory["source_sha"] == "a" * 40
    assert inventory["stage"] == "pretest"
    assert inventory["manifest_sha256"] == sha256(manifest_path)
    assert inventory["entries"] == packaged_tree_inventory(package)
    assert (
        inventory["entries"][-1]["content_sha256"]
        == hashlib.sha256(b"measured content").hexdigest()
    )


def test_frozen_runtime_copy_preserves_measured_package_tree(tmp_path: Path) -> None:
    source = tmp_path / "build-tree"
    source.mkdir()
    (source / "action-server.exe").write_bytes(b"native executable")
    (source / "_internal").mkdir()
    (source / "_internal/runtime.pyd").write_bytes(b"runtime module")
    copy = copy_frozen_package_tree(source, tmp_path / "runtime-copy")

    assert packaged_tree_sha256(copy) == packaged_tree_sha256(source)
    assert sha256(copy / "action-server.exe") == sha256(source / "action-server.exe")


def test_tree_inventory_diff_preserves_added_removed_and_changed_entries() -> None:
    baseline: list[PackageTreeEntry] = [
        {
            "path": "changed.py",
            "kind": "file",
            "mode": 420,
            "link_target": None,
            "content_sha256": "a" * 64,
        },
        {
            "path": "removed.py",
            "kind": "file",
            "mode": 420,
            "link_target": None,
            "content_sha256": "b" * 64,
        },
    ]

    observed: list[PackageTreeEntry] = [
        {
            "path": "changed.py",
            "kind": "file",
            "mode": 420,
            "link_target": None,
            "content_sha256": "c" * 64,
        },
        {
            "path": "added.py",
            "kind": "file",
            "mode": 420,
            "link_target": None,
            "content_sha256": "d" * 64,
        },
    ]

    difference = compare_package_tree_inventories(baseline, observed)
    assert [entry["path"] for entry in difference["added"]] == ["added.py"]
    assert [entry["path"] for entry in difference["removed"]] == ["removed.py"]
    assert difference["changed"] == [
        {
            "path": "changed.py",
            "fields": ["content_sha256"],
            "baseline": baseline[0],
            "observed": observed[0],
        }
    ]


@pytest.mark.parametrize(
    ("platform_name", "suffix"), [("Linux", ""), ("Windows", ".exe")]
)
def test_runtime_rcc_download_is_measured_separately_from_immutable_tree(
    platform_name: str, suffix: str
) -> None:
    from actions.server._download_rcc import RCC_VERSION

    executable_path = f"_internal/actions/server/bin/rcc-{RCC_VERSION}{suffix}"
    observed: list[PackageTreeEntry] = [
        {
            "path": "_internal/actions/server/bin",
            "kind": "directory",
            "mode": 511,
            "link_target": None,
            "content_sha256": None,
        },
        {
            "path": executable_path,
            "kind": "file",
            "mode": 511,
            "link_target": None,
            "content_sha256": "c" * 64,
        },
    ]

    result = classify_runtime_tree_delta([], observed, platform_name=platform_name)
    assert result["valid"] is True
    assert result["rcc_version"] == "18.19.3"
    assert result["expected_rcc_path"] == executable_path
    assert result["runtime_generated_state"] == observed


def test_runtime_tree_delta_rejects_mutation_of_an_immutable_build_entry() -> None:
    baseline: list[PackageTreeEntry] = [
        {
            "path": "module.py",
            "kind": "file",
            "mode": 420,
            "link_target": None,
            "content_sha256": "a" * 64,
        }
    ]
    observed: list[PackageTreeEntry] = [{**baseline[0], "content_sha256": "b" * 64}]

    result = classify_runtime_tree_delta(baseline, observed, platform_name="Windows")
    assert result["valid"] is False
    assert result["failure_reason"] == "immutable_entry_changed"
    assert result["runtime_generated_state"] == []


def test_runtime_tree_delta_rejects_unexplained_additions() -> None:
    observed: list[PackageTreeEntry] = [
        {
            "path": "_internal/actions/server/__pycache__",
            "kind": "directory",
            "mode": 493,
            "link_target": None,
            "content_sha256": None,
        }
    ]

    result = classify_runtime_tree_delta([], observed, platform_name="Windows")
    assert result["valid"] is False
    assert result["failure_reason"] == "unrecognized_runtime_generated_entry"
    assert result["runtime_generated_state"] == []


def test_postruntime_tree_mismatch_retains_exact_inventory_diff(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "module.py").write_bytes(b"packaged source")
    baseline = packaged_tree_inventory(package)
    baseline_sha = packaged_tree_sha256(package)
    inventory_path = tmp_path / "native-artifact-tree-inventory.json"
    inventory_path.write_text(json.dumps(baseline), encoding="utf-8")
    manifest_path = tmp_path / "native-artifact-manifest.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    receipt_path = tmp_path / "dakota-workitems-ui-frozen-test.json"
    receipt: dict[str, object] = {"package_tree_sha256": packaged_tree_sha256(package)}

    runtime_package = copy_frozen_package_tree(package, tmp_path / "runtime-copy")
    generated = runtime_package / "__pycache__"
    generated.mkdir()
    (generated / "module.pyc").write_bytes(b"runtime-generated bytecode")
    record_postruntime_tree_observation(
        receipt,
        package_root=runtime_package,
        baseline_entries=baseline,
        baseline_tree_sha256=baseline_sha,
        baseline_kind="task_owned_frozen_copy",
        stage="frozen-copy-post-runtime",
        exclude_root_files=None,
        immutable_package_root=package,
        immutable_package_tree_sha256=baseline_sha,
        receipt_value=str(receipt_path),
        source_sha="a" * 40,
        runtime_kind="frozen",
        executable_sha="b" * 64,
        manifest_path=manifest_path,
    )

    report_path = (
        tmp_path
        / "dakota-workitems-ui-frozen-test-frozen-copy-post-runtime-tree-diff.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["runtime_delta_valid"] is False
    assert (
        report["runtime_delta_failure_reason"] == "unrecognized_runtime_generated_entry"
    )
    assert report["expected_runtime_tree_sha256"] == baseline_sha
    assert (
        report["observed_package_tree_sha256"]
        == receipt["frozen-copy-post-runtime_tree_sha256"]
    )
    assert report["immutable_build_tree_unchanged"] is True
    assert [entry["path"] for entry in report["added"]] == [
        "__pycache__",
        "__pycache__/module.pyc",
    ]
    assert report["removed"] == []
    assert report["changed"] == []
    assert receipt_section(receipt, "post_runtime_tree_diff")["added_count"] == 2
    assert (
        tmp_path
        / "dakota-workitems-ui-frozen-test-frozen-copy-post-runtime-tree-inventory.json"
    ).is_file()


def test_cleanup_failure_prevents_bounded_pass_receipt(tmp_path: Path) -> None:
    class FailingCleanup(NoOpStopActionServerProcess):
        def stop(self) -> None:
            raise OSError("cleanup details stay private")

    process = FailingCleanup(tmp_path)
    from actions.server._robo_utils.process import Process

    process._process = Process(["test-runtime"], cwd=tmp_path)
    receipt: dict[str, object] = {"status": "IN_PROGRESS"}
    with pytest.raises(NativeRuntimeCleanupError):
        stop_runtime_for_acceptance(process, receipt)
    assert receipt["status"] == "FAIL"
    assert receipt["cleanup_failure_type"] == "OSError"
    assert (
        receipt_section(receipt, "cleanup_observation")["stop_failure_type"]
        == "OSError"
    )


def test_normal_stop_return_with_observed_live_descendant_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server._common.process import ProcessTreeCleanupResult

    child_process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    class Child:
        pid = 321

        def create_time(self):
            return 123.5

    process = cleanup_test_runtime(tmp_path, child_process)

    monkeypatch.setattr(
        "actions.server._common.process.snapshot_process_descendants",
        lambda pid: [Child()] if pid == child_process.pid else [],
    )
    monkeypatch.setattr(
        "actions.server._common.process.force_kill_process_tree_until",
        lambda *_args, **_kwargs: ProcessTreeCleanupResult(
            True, (321,), (), (), descendant_snapshot_complete=True
        ),
    )
    receipt: dict[str, object] = {"status": "IN_PROGRESS"}
    try:
        with pytest.raises(NativeRuntimeCleanupError):
            stop_runtime_for_acceptance(process, receipt)
        assert receipt["status"] == "FAIL"
        observation = receipt_section(receipt, "cleanup_observation")
        assert observation["wrapper_reaped"] is True
        assert observation["live_descendant_count"] == 1
    finally:
        if child_process.poll() is None:
            child_process.kill()
            child_process.wait(timeout=2)


def test_bounded_observation_reaps_only_the_owned_runtime_process() -> None:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    process = cleanup_test_runtime(Path.cwd(), child)

    receipt: dict[str, object] = {"status": "IN_PROGRESS"}
    try:
        stop_runtime_for_acceptance(process, receipt)
        assert child.poll() is not None
        observation = receipt_section(receipt, "cleanup_observation")
        assert observation["wrapper_reaped"] is True
        assert observation["live_descendant_count"] == 0
        assert "zombie_descendant_count" in observation
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=2)


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
    package_root = (
        executable.parent
        if runtime_kind == "frozen"
        else executable.parents[1] / "action-server"
    )
    package_tree_sha = (
        packaged_tree_sha256(package_root) if runtime_kind == "frozen" else None
    )
    embedded_files_sha = artifact.get("embedded_files_sha256")
    assets_zip_sha = artifact.get("assets_zip_sha256")
    wrapper_source_sha = artifact.get("wrapper_source_sha256")
    embedded_frozen_tree_sha = artifact.get("frozen_package_tree_sha256")
    if runtime_kind == "go-wrapper":
        embedded_files_sha = require_sha256(embedded_files_sha, "embedded_files_sha256")
        assets_zip_sha = require_sha256(assets_zip_sha, "assets_zip_sha256")
        wrapper_source_sha = require_sha256(wrapper_source_sha, "wrapper_source_sha256")
        embedded_frozen_tree_sha = require_sha256(
            embedded_frozen_tree_sha, "frozen_package_tree_sha256"
        )
    if runtime_kind == "frozen":
        assert package_tree_sha is not None
        immutable_build_tree_sha = package_tree_sha
    else:
        immutable_build_tree_sha = require_sha256(
            artifact.get("frozen_package_tree_sha256"),
            "frozen_package_tree_sha256",
        )
    node = os.environ.get("DAKOTA_WORKITEMS_UI_NODE") or shutil.which("node")
    assert node is not None
    project = tmp_path / "project"
    datadir = tmp_path / "datadir"
    runtime_home = tmp_path / "runtime-home"
    for directory in (project, datadir, runtime_home):
        directory.mkdir()

    api_key = secrets.token_urlsafe(32)
    receipt: dict[str, object] = {
        "schema_version": 1,
        "status": "IN_PROGRESS",
        "source_sha": source_sha,
        "executable_sha256": executable_sha,
        "package_tree_sha256": package_tree_sha,
        "immutable_build_tree_sha256": immutable_build_tree_sha,
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
    runtime_package_root: Path | None = None
    runtime_baseline_entries: list[PackageTreeEntry] | None = None
    runtime_baseline_tree_sha: str | None = None
    runtime_baseline_kind: str | None = None
    runtime_exclude_root_files: set[str] | None = None
    runtime_executable = executable
    extracted_root: Path | None = None
    try:
        if runtime_kind == "frozen":
            runtime_package_root = copy_frozen_package_tree(
                package_root, tmp_path / "frozen-runtime-package"
            )
            runtime_executable = runtime_package_root / executable.relative_to(
                package_root
            )
            runtime_baseline_tree_sha = packaged_tree_sha256(runtime_package_root)
            if (
                runtime_baseline_tree_sha != package_tree_sha
                or sha256(runtime_executable) != executable_sha
            ):
                raise AssertionError(
                    "task-owned frozen package copy changed artifact bytes"
                )
            runtime_baseline_entries = packaged_tree_inventory(runtime_package_root)
            runtime_baseline_kind = "task_owned_frozen_copy"
            receipt["runtime_artifact_isolation"] = runtime_baseline_kind
            write_tree_inventory_snapshot(
                os.environ.get("DAKOTA_WORKITEMS_UI_RECEIPT"),
                stage="frozen-copy-pretest",
                source_sha=source_sha,
                runtime_kind=runtime_kind,
                executable_sha=executable_sha,
                manifest_path=Path(os.environ["DAKOTA_WORKITEMS_UI_BUILD_MANIFEST"]),
                package_root=runtime_package_root,
            )

        monkeypatch.setenv(
            "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE",
            str(runtime_executable),
        )
        version_env = os.environ.copy()
        version_env.update(native_runtime_environment(runtime_home))
        version = subprocess.run(
            [str(runtime_executable), "version"],
            cwd=project,
            env=version_env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert version.returncode == 0
        runtime_version = version.stdout.strip()
        receipt["runtime_version"] = runtime_version

        if runtime_kind == "go-wrapper":
            extracted_root = wrapper_extraction_root(
                runtime_home, runtime_version, platform.system()
            )
            assert extracted_root.is_dir()
            assert extracted_root.resolve().is_relative_to(runtime_home.resolve())
            assert (extracted_root / "app_hash").read_text().strip() == assets_zip_sha
            extracted_files_sha = packaged_files_sha256(
                extracted_root,
                exclude_root_files={"app_hash", "extract.lock", "lastLaunchTouch"},
            )
            assert extracted_files_sha == embedded_files_sha
            runtime_package_root = extracted_root
            runtime_exclude_root_files = {
                "app_hash",
                "extract.lock",
                "lastLaunchTouch",
            }
            runtime_baseline_entries = packaged_tree_inventory(
                runtime_package_root,
                exclude_root_files=runtime_exclude_root_files,
            )
            runtime_baseline_tree_sha = packaged_tree_sha256(
                runtime_package_root,
                exclude_root_files=runtime_exclude_root_files,
            )
            runtime_baseline_kind = "go_wrapper_extraction"
            receipt["runtime_artifact_isolation"] = runtime_baseline_kind
            write_tree_inventory_snapshot(
                os.environ.get("DAKOTA_WORKITEMS_UI_RECEIPT"),
                stage="go-wrapper-pretest",
                source_sha=source_sha,
                runtime_kind=runtime_kind,
                executable_sha=executable_sha,
                manifest_path=Path(os.environ["DAKOTA_WORKITEMS_UI_BUILD_MANIFEST"]),
                package_root=runtime_package_root,
                exclude_root_files=runtime_exclude_root_files,
            )
            receipt["wrapper_extraction"] = {
                "path_relative_to_runtime_home": extracted_root.relative_to(
                    runtime_home
                ).as_posix(),
                "app_hash_matches_embedded_archive": True,
                "extracted_files_sha256": extracted_files_sha,
                "pre_runtime_tree_sha256": runtime_baseline_tree_sha,
            }
        process = start_native_runtime(datadir, project, runtime_home, api_key)
        origin = f"http://{process.host}:{process.port}"
        normal = run_browser_stage(
            node,
            "normal",
            tmp_path / "browser-profile-normal",
            api_key,
            origin,
        )
        record_browser_stage(receipt, normal)

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
        record_browser_stage(receipt, storage_error)
    except BaseException as error:
        receipt["status"] = "FAIL"
        if isinstance(error, NativeRuntimeStartupError):
            receipt["failure_type"] = type(error.primary_error).__name__
            if error.cleanup_error is not None:
                receipt["cleanup_failure_type"] = type(error.cleanup_error).__name__
            if error.cleanup_observation is not None:
                receipt["cleanup_observation"] = error.cleanup_observation
        else:
            receipt["failure_type"] = type(error).__name__
        if process is not None:
            try:
                stop_runtime_for_acceptance(process, receipt)
            except BaseException:
                pass
        if (
            runtime_package_root is not None
            and runtime_baseline_entries is not None
            and runtime_baseline_tree_sha is not None
            and runtime_baseline_kind is not None
        ):
            try:
                record_postruntime_tree_observation(
                    receipt,
                    package_root=runtime_package_root,
                    baseline_entries=runtime_baseline_entries,
                    baseline_tree_sha256=runtime_baseline_tree_sha,
                    baseline_kind=runtime_baseline_kind,
                    stage=f"{runtime_kind}-post-runtime",
                    exclude_root_files=runtime_exclude_root_files,
                    immutable_package_root=package_root,
                    immutable_package_tree_sha256=immutable_build_tree_sha,
                    receipt_value=os.environ.get("DAKOTA_WORKITEMS_UI_RECEIPT"),
                    source_sha=source_sha,
                    runtime_kind=runtime_kind,
                    executable_sha=executable_sha,
                    manifest_path=Path(
                        os.environ["DAKOTA_WORKITEMS_UI_BUILD_MANIFEST"]
                    ),
                )
            except BaseException as inventory_error:
                receipt["post_runtime_inventory_failure_type"] = type(
                    inventory_error
                ).__name__
        write_receipt(receipt)
        raise
    else:
        if process is not None:
            try:
                stop_runtime_for_acceptance(process, receipt)
            except BaseException:
                write_receipt(receipt)
                raise
        if (
            runtime_package_root is not None
            and runtime_baseline_entries is not None
            and runtime_baseline_tree_sha is not None
            and runtime_baseline_kind is not None
        ):
            try:
                record_postruntime_tree_observation(
                    receipt,
                    package_root=runtime_package_root,
                    baseline_entries=runtime_baseline_entries,
                    baseline_tree_sha256=runtime_baseline_tree_sha,
                    baseline_kind=runtime_baseline_kind,
                    stage=f"{runtime_kind}-post-runtime",
                    exclude_root_files=runtime_exclude_root_files,
                    immutable_package_root=package_root,
                    immutable_package_tree_sha256=immutable_build_tree_sha,
                    receipt_value=os.environ.get("DAKOTA_WORKITEMS_UI_RECEIPT"),
                    source_sha=source_sha,
                    runtime_kind=runtime_kind,
                    executable_sha=executable_sha,
                    manifest_path=Path(
                        os.environ["DAKOTA_WORKITEMS_UI_BUILD_MANIFEST"]
                    ),
                )
            except BaseException as error:
                receipt["status"] = "FAIL"
                receipt["failure_type"] = type(error).__name__
                receipt["failure_phase"] = "post_runtime_tree_inventory"
                write_receipt(receipt)
                raise
            validation = receipt_section(receipt, "post_runtime_tree_validation")
            if validation.get("valid") is not True:
                receipt["status"] = "FAIL"
                receipt["failure_type"] = "AssertionError"
                receipt["failure_phase"] = "post_runtime_package_tree_delta"
                write_receipt(receipt)
                raise AssertionError(
                    "task-owned package tree changed outside the runtime RCC download contract"
                )
        receipt["status"] = "PASS_BOUNDED"
        write_receipt(receipt)
