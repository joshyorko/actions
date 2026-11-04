"""Prepare task-owned RCC inputs for the opt-in Action-to-Robot vertical.

This helper is intentionally separate from the acceptance test. It creates a
new output directory, writes the exact supplied manifests, stages the
candidate Core wheel in the fresh Action RCC home's ``wheels`` directory
before publishing, verifies both local artifact acquisitions, and writes
canonical PreparedRccEnvironment receipts. It never edits an existing RCC
home or runs automatically from pytest collection.

Example, after setting ACTIONS_INTERNAL_CHILD_PREPARE_RCC=1::

    python developer/tests/prepare_internal_child_real_vertical_rcc.py \\
      --rcc /path/to/pinned/rcc \\
      --core-wheel /path/to/actions_core-1.1.0a8-py3-none-any.whl \\
      --action-manifest /path/to/action-package.yaml \\
      --robot-manifest /path/to/robot-package.yaml \\
      --output-dir /path/to/new/private/preparation \\
      --minimum-free-bytes 10803773440

The generated receipt paths and hashes are printed as JSON. Existing proxy and
CA settings are inherited without being printed; credentials are not copied.
RCC may use its normal public package sources for dependencies not present in
the task-owned wheel cache.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4


_OPT_IN = "ACTIONS_INTERNAL_CHILD_PREPARE_RCC"
_RCC_VERSION = "v18.19.3"
_RCC_LINUX_SHA256 = "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428"
_MAX_MANIFEST_BYTES = 128 * 1024
_MAX_WHEEL_BYTES = 128 * 1024 * 1024
_MAX_RCC_OUTPUT = 1024 * 1024
_RETAINED_FREE_FLOOR = 10_803_773_440
_TWO_HOME_START_RESERVE = 3_045_752_832


@dataclass(frozen=True)
class _RoleHome:
    directory: Path
    package_yaml: Path
    robocorp_home: Path
    environment: dict[str, str]


def _read_regular(path: Path, *, byte_limit: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError("input file unavailable") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > byte_limit:
            raise ValueError("regular bounded input file required")
        chunks: list[bytes] = []
        total = 0
        while total <= byte_limit:
            chunk = os.read(fd, min(64 * 1024, byte_limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total != info.st_size or total > byte_limit:
            raise ValueError("input file changed or exceeds its bound")
        after = os.fstat(fd)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
        ):
            raise ValueError("input file changed while reading")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _write_new(path: Path, payload: bytes, *, mode: int = 0o600) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def _mkdir_new(path: Path) -> None:
    path.mkdir(mode=0o700)
    info = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
    ):
        raise ValueError("new task-owned private directory required")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _compiler_api():
    root = _repo_root()
    source = str(root / "action_server" / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from actions.server.deployments.package_revision_compiler import (
        PreparedRccEnvironment,
        RccBuildIdentity,
        _extract_json_object,
        _validate_package_inputs,
        load_prepared_rcc_environment,
        snapshot_source_entries,
    )
    from actions.server.deployments.source_manifest import SuppliedSourceEntry

    return (
        PreparedRccEnvironment,
        RccBuildIdentity,
        _extract_json_object,
        _validate_package_inputs,
        load_prepared_rcc_environment,
        snapshot_source_entries,
        SuppliedSourceEntry,
    )


def _supervisor_api():
    path = Path(__file__).with_name("test_rcc_env_exec_fd_real.py")
    spec = importlib.util.spec_from_file_location(
        "_actions340_bounded_rcc_supervisor", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("existing bounded RCC supervisor is unavailable")
    module = importlib.util.module_from_spec(spec)
    # The supervisor test module defines dataclasses, so register it just as
    # Python's normal import machinery would before evaluating its body.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module._require_supervisor_support, module._run_reaped


def _candidate_version(wheel_bytes: bytes) -> str:
    from io import BytesIO

    try:
        with zipfile.ZipFile(BytesIO(wheel_bytes)) as archive:
            metadata_files = [
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            ]
            records = [
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/RECORD")
            ]
            if len(metadata_files) != 1 or len(records) != 1:
                raise ValueError("candidate wheel metadata inventory is ambiguous")
            metadata = archive.read(metadata_files[0]).decode("utf-8", errors="strict")
            if not re.search(r"(?mi)^Name: actions[-_]core\s*$", metadata):
                raise ValueError("candidate wheel is not actions-core")
            versions = re.findall(r"(?mi)^Version: ([^\r\n]+)\s*$", metadata)
            if len(versions) != 1:
                raise ValueError("candidate wheel has no unique version")
            return versions[0]
    except (OSError, KeyError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise ValueError("candidate wheel is not a readable Core wheel") from exc


def _validate_action_manifest(manifest: bytes, core_version: str) -> None:
    (
        _Prepared,
        _Build,
        _extract,
        validate_package_inputs,
        _load,
        snapshot_source_entries,
        SuppliedSourceEntry,
    ) = _compiler_api()
    entries = (
        SuppliedSourceEntry("package.yaml", "file", manifest, 0o644),
        SuppliedSourceEntry("generated_actions.py", "file", b"", 0o644),
        SuppliedSourceEntry(
            "tests/test_preparation.py", "file", b"def test_ok(): pass\n", 0o644
        ),
    )
    snapshot = snapshot_source_entries(entries, protected_input_names=["package.yaml"])
    requirements = validate_package_inputs(snapshot)
    if not any(
        item
        == {
            "kind": "python-package",
            "name": "actions-core",
            "constraint": "==" + core_version,
        }
        for item in requirements
    ):
        raise ValueError("Action package.yaml must exactly pin candidate actions-core")


def _base_environment(role: _RoleHome) -> dict[str, str]:
    task_home = role.directory / "home"
    actions_home = role.directory / "actions-home"
    task_tmp = role.directory / "tmp"
    xdg_config = role.directory / "config"
    xdg_cache = role.directory / "cache"
    for path in (task_home, actions_home, task_tmp, xdg_config, xdg_cache):
        _mkdir_new(path)
    path_value = os.pathsep.join(("/usr/sbin", "/sbin", os.defpath))
    environment = {
        "PATH": path_value,
        "HOME": str(task_home),
        "ROBOCORP_HOME": str(role.robocorp_home),
        "ACTIONS_HOME": str(actions_home),
        "TMPDIR": str(task_tmp),
        "XDG_CONFIG_HOME": str(xdg_config),
        "XDG_CACHE_HOME": str(xdg_cache),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    proxy_names = {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}
    ca_names = {"SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"}
    for name, value in os.environ.items():
        if name.lower() in proxy_names or name in ca_names:
            if name.lower() in proxy_names - {"no_proxy"}:
                parsed = urlsplit(value)
                if parsed.username is not None or parsed.password is not None:
                    raise ValueError(f"proxy credentials are not accepted in {name}")
            environment[name] = value
    return environment


def _make_role(directory: Path, role_name: str, manifest: bytes) -> _RoleHome:
    role_dir = directory / role_name
    _mkdir_new(role_dir)
    robocorp_home = role_dir / "robocorp-home"
    _mkdir_new(robocorp_home)
    package_yaml = role_dir / "package.yaml"
    _write_new(package_yaml, manifest)
    # RCC writes the local trust carrier while publishing/acquiring. Create its
    # private parent before publication; never alter the published artifact.
    _mkdir_new(robocorp_home / "artifacts")
    _mkdir_new(robocorp_home / "artifacts" / "v1")
    _mkdir_new(robocorp_home / "artifacts" / "v1" / "trust")
    role = _RoleHome(role_dir, package_yaml, robocorp_home, {})
    return _RoleHome(
        role_dir,
        package_yaml,
        robocorp_home,
        _base_environment(role),
    )


def _run_supervised(
    run_reaped,
    command: list[str],
    env: dict[str, str],
    phase: str,
    timeout: int,
    minimum_free_bytes: int,
) -> bytes:
    status, stdout, stderr = run_reaped(
        command,
        env=env,
        timeout=timeout,
        disk_paths=(Path(env["ROBOCORP_HOME"]), Path(env["TMPDIR"])),
        minimum_free_bytes=minimum_free_bytes,
    )
    log_root = Path(env["ROBOCORP_HOME"]).parent
    log_name = "rcc-" + phase.replace(" ", "-")
    _write_new(log_root / (log_name + ".stdout.log"), stdout)
    _write_new(log_root / (log_name + ".stderr.log"), stderr)
    if status != 0 or len(stdout) > _MAX_RCC_OUTPUT:
        raise RuntimeError(
            f"bounded RCC {phase} failed or did not settle (status {status})"
        )
    return stdout


def _publish_and_acquire(
    rcc: Path,
    role: _RoleHome,
    run_reaped,
    extract_json_object,
    parse_published_artifact_details,
    minimum_free_bytes,
):
    publish_raw = _run_supervised(
        run_reaped,
        [
            str(rcc),
            "env",
            "publish",
            "--environment",
            str(role.package_yaml),
            "--json",
            "--provider",
            "local",
        ],
        role.environment,
        "publish",
        900,
        minimum_free_bytes,
    )
    payload = extract_json_object(
        publish_raw, required_keys=("specificationDigest", "artifactDigest")
    )
    details = parse_published_artifact_details(payload)
    acquire_raw = _run_supervised(
        run_reaped,
        [
            str(rcc),
            "env",
            "acquire",
            "--artifact",
            details.artifact_digest,
            "--provider",
            "local",
            "--trust-carrier",
            str(role.robocorp_home / "artifacts" / "v1" / "trust"),
            "--trust-carrier-type",
            "filesystem",
            "--permissive-local",
            "--json",
        ],
        role.environment,
        "acquire",
        120,
        minimum_free_bytes,
    )
    try:
        acquired = json.loads(acquire_raw)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("bounded RCC acquire returned invalid JSON") from exc
    verification = acquired.get("verification") if isinstance(acquired, dict) else None
    if (
        not isinstance(acquired, dict)
        or acquired.get("artifactDigest") != details.artifact_digest
        or not isinstance(verification, dict)
        or verification.get("valid") is not True
        or (
            "specificationDigest" in acquired
            and acquired["specificationDigest"] != details.specification_digest
        )
    ):
        raise RuntimeError("RCC acquire identity or verification did not match publish")
    return details


def _prepared_receipt(role: _RoleHome, details, prepared_types):
    (
        PreparedRccEnvironment,
        RccBuildIdentity,
        _extract,
        _validate,
        load,
        _snapshot,
        _entry,
    ) = prepared_types
    manifest = _read_regular(role.package_yaml, byte_limit=_MAX_MANIFEST_BYTES)
    prepared = PreparedRccEnvironment(
        robocorp_home=role.robocorp_home,
        package_yaml_digest="sha256:" + hashlib.sha256(manifest).hexdigest(),
        build_identity=RccBuildIdentity(
            specification_digest=details.specification_digest,
            artifact_digest=details.artifact_digest,
        ),
    )
    return (
        role.directory / "prepared-rcc.json",
        prepared.to_receipt_bytes(),
        prepared,
        load,
    )


def _parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rcc", type=Path, required=True, help="pinned RCC v18.19.3 binary"
    )
    parser.add_argument(
        "--core-wheel", type=Path, required=True, help="candidate actions-core wheel"
    )
    parser.add_argument("--action-manifest", type=Path, required=True)
    parser.add_argument("--robot-manifest", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new private destination; must not exist",
    )
    parser.add_argument(
        "--minimum-free-bytes",
        type=int,
        required=True,
        help="free-space floor retained while RCC runs",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if sys.platform != "linux":
        raise RuntimeError("the bounded subreaper preparation helper is Linux-only")
    args = _parse_args(argv)
    if os.environ.get(_OPT_IN) != "1":
        raise RuntimeError(f"set {_OPT_IN}=1 to authorize task-owned RCC preparation")
    if args.minimum_free_bytes < _RETAINED_FREE_FLOOR:
        raise ValueError("free-space floor must not be lowered")
    if (
        not args.output_dir.is_absolute()
        or args.output_dir.exists()
        or args.output_dir.is_symlink()
    ):
        raise ValueError("absolute new output directory required")
    if not args.output_dir.parent.is_dir() or args.output_dir.parent.is_symlink():
        raise ValueError("existing non-symlink output parent required")

    wheel_bytes = _read_regular(args.core_wheel, byte_limit=_MAX_WHEEL_BYTES)
    if shutil.disk_usage(args.output_dir.parent).free < (
        args.minimum_free_bytes + _TWO_HOME_START_RESERVE + len(wheel_bytes)
    ):
        raise RuntimeError("insufficient free space for two fresh RCC homes")
    core_hash = hashlib.sha256(wheel_bytes).hexdigest()
    core_version = _candidate_version(wheel_bytes)
    action_manifest = _read_regular(
        args.action_manifest, byte_limit=_MAX_MANIFEST_BYTES
    )
    robot_manifest = _read_regular(args.robot_manifest, byte_limit=_MAX_MANIFEST_BYTES)
    _validate_action_manifest(action_manifest, core_version)

    rcc = args.rcc.resolve(strict=True)
    if not rcc.is_file() or not os.access(rcc, os.X_OK):
        raise ValueError("executable pinned RCC binary required")
    if (
        hashlib.sha256(_read_regular(rcc, byte_limit=_MAX_WHEEL_BYTES)).hexdigest()
        != _RCC_LINUX_SHA256
    ):
        raise ValueError("RCC binary does not match pinned Linux SHA-256")

    require_supervisor, run_reaped = _supervisor_api()
    require_supervisor()
    args.output_dir.mkdir(mode=0o700)
    output_info = args.output_dir.stat(follow_symlinks=False)
    if output_info.st_uid != os.getuid() or stat.S_IMODE(output_info.st_mode) & 0o077:
        raise ValueError("new private task-owned output directory required")

    action_role = _make_role(args.output_dir, "action", action_manifest)
    wheels = action_role.robocorp_home / "wheels"
    _mkdir_new(wheels)
    candidate_cache_wheel = wheels / args.core_wheel.name
    _write_new(candidate_cache_wheel, wheel_bytes)
    if (
        hashlib.sha256(
            _read_regular(candidate_cache_wheel, byte_limit=_MAX_WHEEL_BYTES)
        ).hexdigest()
        != core_hash
    ):
        raise RuntimeError("candidate wheel changed while staging")
    robot_role = _make_role(args.output_dir, "robot", robot_manifest)

    prepared_types = _compiler_api()
    from actions.server._rcc_runtime_adapter import parse_published_artifact_details

    # RCC subprocesses receive only the role-specific HOME/config/cache and
    # no inherited account, proxy, index, or workspace credentials.
    version_output = _run_supervised(
        run_reaped,
        [str(rcc), "--version"],
        action_role.environment,
        "version check",
        10,
        args.minimum_free_bytes,
    )
    if version_output.decode("ascii", errors="strict").strip() != _RCC_VERSION:
        raise RuntimeError("RCC binary version does not match v18.19.3")

    action_details = _publish_and_acquire(
        rcc,
        action_role,
        run_reaped,
        prepared_types[2],
        parse_published_artifact_details,
        args.minimum_free_bytes,
    )
    if (
        hashlib.sha256(
            _read_regular(candidate_cache_wheel, byte_limit=_MAX_WHEEL_BYTES)
        ).hexdigest()
        != core_hash
    ):
        raise RuntimeError("RCC changed the staged candidate wheel")
    robot_details = _publish_and_acquire(
        rcc,
        robot_role,
        run_reaped,
        prepared_types[2],
        parse_published_artifact_details,
        args.minimum_free_bytes,
    )
    for role, expected_manifest in (
        (action_role, action_manifest),
        (robot_role, robot_manifest),
    ):
        if (
            _read_regular(role.package_yaml, byte_limit=_MAX_MANIFEST_BYTES)
            != expected_manifest
        ):
            raise RuntimeError("RCC preparation changed an exact package.yaml")
    if (
        hashlib.sha256(
            _read_regular(candidate_cache_wheel, byte_limit=_MAX_WHEEL_BYTES)
        ).hexdigest()
        != core_hash
    ):
        raise RuntimeError("candidate wheel changed after environment publication")

    # Stage and validate both receipts before making either visible. The two
    # renames cannot be one filesystem transaction, so if the second rename
    # fails, remove the first receipt created by this invocation as well.
    receipt_inputs = (
        _prepared_receipt(action_role, action_details, prepared_types),
        _prepared_receipt(robot_role, robot_details, prepared_types),
    )
    staged: list[tuple[Path, Path]] = []
    published: list[Path] = []
    try:
        for destination, payload, expected, load_receipt in receipt_inputs:
            temporary = destination.with_name(
                destination.name + ".pending-" + uuid4().hex
            )
            _write_new(temporary, payload)
            staged.append((temporary, destination))
            if load_receipt(temporary) != expected:
                raise RuntimeError("staged prepared RCC receipt did not round-trip")
        for temporary, destination in staged:
            os.replace(temporary, destination)
            published.append(destination)
    except BaseException:
        for temporary, _destination in staged:
            temporary.unlink(missing_ok=True)
        for destination in published:
            destination.unlink(missing_ok=True)
        raise
    action_receipt = receipt_inputs[0][0]
    robot_receipt = receipt_inputs[1][0]
    report = {
        "schema": "actions340-internal-child-rcc-preparation/v1",
        "rccVersion": _RCC_VERSION,
        "rccBinary": str(rcc),
        "candidateCoreWheelSha256": core_hash,
        "candidateCoreVersion": core_version,
        "action": {
            "receipt": str(action_receipt),
            "robocorpHome": str(action_role.robocorp_home),
            "specificationDigest": action_details.specification_digest,
            "artifactDigest": action_details.artifact_digest,
        },
        "robot": {
            "receipt": str(robot_receipt),
            "robocorpHome": str(robot_role.robocorp_home),
            "specificationDigest": robot_details.specification_digest,
            "artifactDigest": robot_details.artifact_digest,
        },
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
