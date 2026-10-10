"""Private, source-bound inspection of one explicitly declared v2 fixture.

This observes RCC metadata for a harness-owned fixture. It does not establish
authorization, arbitrary-package completeness, admission, publication, or a
security sandbox.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import selectors
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from actions.server._common.process import ProcessTreeCleanupResult
from actions.server._rcc_runtime_adapter import (
    RccProcessHandle,
    build_exec_command,
    compute_source_generation,
    prepare_runtime_for_inspection,
    verify_rcc_version,
)
from actions.server.deployments import package_compiler, source_manifest, source_staging
from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.ids import CapabilityId, PackageId

_OUTPUT_LIMIT = 1024 * 1024
_RECEIPT_LIMIT = 64 * 1024
_CLEANUP_SECONDS = 3.0


@dataclass(frozen=True)
class InspectionObservation:
    status: str
    rcc_version: str
    specification_digest: str
    artifact_digest: str
    provider_reference: str | None
    core_version: str
    core_module_origin: str
    core_distribution_root: str
    core_distribution_record_sha256: str
    core_sys_prefix: str
    managed_python: str
    managed_prefix: str
    materialization_path: str
    materialization_id: str
    materialization_cwd: str
    exit_code: int
    receipt_path: str
    cleanup: ProcessTreeCleanupResult
    source_inventory_sha256: str
    metadata_sha256: str
    receipt_sha256: str
    operation_cleanup_complete: bool


@dataclass(frozen=True)
class ControlledFixtureInspection:
    compilation: package_compiler.ProposedControlledCompilation
    observation: InspectionObservation


def _private_environment(operation_root: Path) -> dict[str, str]:
    private_dirs = {
        "HOME": operation_root / "home",
        "TMPDIR": operation_root / "tmp",
        "XDG_CACHE_HOME": operation_root / "xdg-cache",
        "XDG_CONFIG_HOME": operation_root / "xdg-config",
        "ROBOCORP_HOME": operation_root / "rcc-home",
    }
    for path in private_dirs.values():
        path.mkdir(mode=0o700)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        **{name: str(path) for name, path in private_dirs.items()},
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }
    for name in ("LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR", "SYSTEMROOT", "WINDIR"):
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def _run_bounded_rcc_process(
    command: list[str], *, cwd: Path, env: dict[str, str], output_limit: int,
    deadline: float, receipt: Path,
    ) -> tuple[int, bytes, bytes, ProcessTreeCleanupResult]:
    """Run an RCC command with nonblocking drains and owned-tree cleanup."""
    process = subprocess.Popen(
        command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        raise RuntimeError("RCC output pipes were not created")
    handle = RccProcessHandle(process, receipt)
    selector = selectors.DefaultSelector()
    streams = (process.stdout, process.stderr)
    buffers = (bytearray(), bytearray())
    total_output = 0
    over_limit = False
    owned: dict[tuple[int, float], Any] = {}
    error: BaseException | None = None
    timed_out = False
    cleanup: ProcessTreeCleanupResult | None = None
    code: int | None = None

    def drain_ready(timeout: float) -> None:
        nonlocal total_output, over_limit
        for key, _ in selector.select(timeout):
            try:
                chunk = os.read(key.fd, 64 * 1024)
            except BlockingIOError:
                continue
            except OSError as exc:
                raise RuntimeError("RCC output pipe read failed") from exc
            if not chunk:
                selector.unregister(key.fd)
                continue
            available = max(0, output_limit - total_output)
            if available:
                buffers[key.data].extend(chunk[:available])
            total_output += len(chunk)
            over_limit = over_limit or total_output > output_limit

    try:
        for index, stream in enumerate(streams):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, index)
        while process.poll() is None:
            snapshot_complete = True
            for child in handle.capture_owned_processes():
                try:
                    owned[(child.pid, child.create_time())] = child
                except Exception:
                    snapshot_complete = False
            handle._owned_processes = list(owned.values())
            handle._owned_snapshot_complete = snapshot_complete
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            drain_ready(min(0.025, remaining))
        code = process.poll()
    except BaseException as exc:
        error = exc
    finally:
        cleanup_deadline = time.monotonic() + _CLEANUP_SECONDS
        try:
            cleanup = handle.force_kill_until(cleanup_deadline)
        except BaseException as exc:
            error = error or exc
        while selector.get_map() and time.monotonic() < cleanup_deadline:
            try:
                drain_ready(min(0.025, cleanup_deadline - time.monotonic()))
            except BaseException as exc:
                error = error or exc
                break
        pipes_drained = not selector.get_map()
        selector.close()
        for stream in streams:
            try:
                stream.close()
            except OSError as exc:
                error = error or exc
    if cleanup is None:
        raise RuntimeError("RCC process cleanup result is missing") from error
    if not cleanup.descendant_reap_complete or not pipes_drained:
        raise RuntimeError(
            f"RCC process cleanup incomplete: tree={cleanup.descendant_reap_complete}; "
            f"pipes_drained={pipes_drained}; live={cleanup.live_descendant_pids}; "
            f"zombies={cleanup.zombie_descendant_pids}; errors={cleanup.errors}"
        ) from error
    if timed_out:
        raise TimeoutError(
            "RCC command exceeded its execution deadline; cleanup_complete=True"
        ) from None
    if error is not None:
        raise error
    if code is None:
        code = process.returncode
    if code is None:
        raise RuntimeError("RCC process returned no status")
    if over_limit:
        raise ValueError("RCC process output exceeds its byte bound")
    return code, bytes(buffers[0]), bytes(buffers[1]), cleanup


def _limited_runner(
    *, cwd: Path, env: dict[str, str], deadline: float, receipt: Path
):
    def run(*args: str) -> tuple[int, str, str]:
        code, stdout, stderr, _ = _run_bounded_rcc_process(
            list(args), cwd=cwd, env=env, output_limit=_OUTPUT_LIMIT,
            deadline=deadline, receipt=receipt,
        )
        return code, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")

    return run


def _core_metadata_script(metadata_path: Path) -> str:
    return (
        "import contextlib, hashlib, importlib.metadata, io, json, pathlib, sys\n"
        "import actions, actions.cli\n"
        "class LimitedCapture(io.StringIO):\n"
        "    size = 0\n"
        "    def write(self, value):\n"
        "        self.size += len(value.encode('utf-8'))\n"
        "        if self.size > 1048576: raise ValueError('metadata output exceeds the byte bound')\n"
        "        return super().write(value)\n"
        "capture = LimitedCapture()\n"
        "with contextlib.redirect_stdout(capture): result = actions.cli.main(['metadata', sys.argv[1]], exit=False)\n"
        "if not isinstance(result, int) or isinstance(result, bool) or result != 0: raise RuntimeError('Core metadata command failed')\n"
        "metadata = json.loads(capture.getvalue())\n"
        "distribution = importlib.metadata.distribution('actions-core')\n"
        "record = distribution.read_text('RECORD')\n"
        "origin = pathlib.Path(actions.__file__).resolve()\n"
        "recorded = any(str(item).replace('\\\\', '/') == 'actions/__init__.py' and pathlib.Path(distribution.locate_file(item)).resolve() == origin for item in (distribution.files or ()))\n"
        "metadata['_inspection_core'] = {'version': distribution.version, 'origin': str(origin), 'distribution_root': str(pathlib.Path(distribution.locate_file('')).resolve()), 'record_sha256': hashlib.sha256((record or '').encode()).hexdigest(), 'recorded_origin': recorded, 'sys_prefix': sys.prefix, 'python': str(pathlib.Path(sys.executable)), 'cwd': str(pathlib.Path.cwd().resolve())}\n"
        "encoded = json.dumps(metadata).encode('utf-8')\n"
        "if len(encoded) > 1048576: raise ValueError('metadata output exceeds the byte bound')\n"
        f"pathlib.Path({str(metadata_path)!r}).write_bytes(encoded)\n"
    )


def _load_metadata(
    raw: bytes, package_dir: Path, materialization_path: Path
) -> tuple[dict[str, Any], str, str, str, str, str, str, str, bytes]:
    if len(raw) > _OUTPUT_LIMIT:
        raise ValueError("inspection metadata exceeds its bound")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("actions"), list):
        raise ValueError("inspection metadata has invalid shape")
    core = value.pop("_inspection_core", None)
    if (
        not isinstance(core, dict)
        or not isinstance(core.get("version"), str)
        or not isinstance(core.get("origin"), str)
        or not isinstance(core.get("distribution_root"), str)
        or not isinstance(core.get("record_sha256"), str)
        or not isinstance(core.get("recorded_origin"), bool)
        or not isinstance(core.get("sys_prefix"), str)
        or not isinstance(core.get("python"), str)
        or not isinstance(core.get("cwd"), str)
    ):
        raise ValueError("installed Core provenance is missing")
    origin = Path(core["origin"]).resolve()
    distribution_root = Path(core["distribution_root"]).resolve()
    try:
        origin.relative_to(package_dir.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("installed Core import origin is inside inspected source")
    if core["version"] != "1.0.2":
        raise ValueError("inspected fixture requires actions-core 1.0.2")
    prefix = Path(core["sys_prefix"]).resolve()
    python = Path(core["python"]).resolve()
    materialization_cwd = Path(core["cwd"]).resolve()
    for evidence_path in (origin, distribution_root, python):
        try:
            evidence_path.relative_to(prefix)
        except ValueError:
            raise ValueError(
                "installed Core provenance is outside its interpreter prefix"
            ) from None
    if prefix != materialization_path.resolve(strict=True):
        raise ValueError("managed Python prefix differs from RCC receipt materialization")
    for evidence_path in (origin, distribution_root, python):
        try:
            evidence_path.relative_to(materialization_path.resolve(strict=True))
        except ValueError:
            raise ValueError(
                "installed Core provenance is outside RCC receipt materialization"
            ) from None
    if materialization_cwd != materialization_path.resolve(strict=True):
        raise ValueError("RCC child working directory differs from receipt materialization")
    if Path(core["python"]).name != "python":
        raise ValueError("RCC inspection did not use the managed python command")
    if not core["recorded_origin"] or len(core["record_sha256"]) != 64:
        raise ValueError(
            "installed Core distribution RECORD does not identify imported module"
        )
    try:
        int(core["record_sha256"], 16)
    except ValueError:
        raise ValueError(
            "installed Core distribution RECORD digest is invalid"
        ) from None
    return (
        value,
        core["version"],
        str(origin),
        str(distribution_root),
        core["record_sha256"],
        str(prefix),
        str(python),
        str(materialization_cwd),
        raw,
    )


def _supplied_actions(
    metadata: dict[str, Any],
    declared_actions: tuple[package_compiler.DeclaredAction, ...],
    staged: Path,
):
    expected = {
        (
            str(CapabilityId.model_validate(item.capability_id).root),
            item.source_path,
            item.python_name,
        ): item
        for item in declared_actions
    }
    rows = metadata["actions"]
    if len(rows) != len(expected):
        raise ValueError("RCC metadata action count differs from fixture declaration")
    supplied = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("RCC metadata action row is invalid")
        file_path = Path(row.get("file", "")).resolve()
        try:
            source_path = file_path.relative_to(staged.resolve()).as_posix()
        except ValueError:
            raise ValueError(
                "RCC metadata action path escapes staged fixture"
            ) from None
        match = next(
            (key for key in expected if key[1:] == (source_path, row.get("name"))), None
        )
        if match is None or match in seen:
            raise ValueError("RCC metadata actions do not map exactly to declaration")
        seen.add(match)
        supplied.append(
            package_compiler.SuppliedActionMetadata(
                capability_id=CapabilityId.model_validate(match[0]),
                source_path=source_path,
                python_name=row["name"],
                docs=row.get("docs", ""),
                input_schema_json=canonicalize_json(
                    json.dumps(row.get("input_schema", {})).encode()
                ),
                output_schema_json=canonicalize_json(
                    json.dumps(row.get("output_schema", {})).encode()
                ),
                managed_params_schema_json=canonicalize_json(
                    json.dumps(row.get("managed_params_schema", {})).encode()
                ),
                options_json=canonicalize_json(
                    json.dumps(row.get("options", {})).encode()
                ),
            )
        )
    return tuple(supplied)


def _verify_complete_fixture_tree(root: Path, declared_paths: tuple[str, ...]) -> None:
    """Require the harness fixture tree to contain exactly declared files."""
    expected_files = set(declared_paths)
    expected_directories = {
        "/".join(parts[:index])
        for path in declared_paths
        for parts in (source_manifest._validated_parts(path),)
        for index in range(1, len(parts))
    }
    observed_files: set[str] = set()
    observed_directories: set[str] = set()
    pending = [(root, "")]
    while pending:
        directory, prefix = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                relative = f"{prefix}/{entry.name}" if prefix else entry.name
                source_manifest._validated_parts(relative)
                facts = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(facts.st_mode):
                    observed_directories.add(relative)
                    pending.append((Path(entry.path), relative))
                elif stat.S_ISREG(facts.st_mode):
                    observed_files.add(relative)
                else:
                    raise ValueError("controlled fixture contains a non-regular entry")
                if (
                    len(observed_files) + len(observed_directories)
                    > source_manifest.MAX_ENTRIES
                ):
                    raise ValueError("controlled fixture tree exceeds the entry bound")
    if observed_files != expected_files or observed_directories != expected_directories:
        raise ValueError("controlled fixture tree differs from complete declaration")


def _read_owned_regular_file(path: Path, limit: int) -> bytes:
    """Read bounded output through a no-follow descriptor and verify identity."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or before.st_nlink != 1
            or before.st_size > limit
        ):
            raise ValueError("inspection output is not a bounded owned regular file")
        chunks = bytearray()
        while len(chunks) <= limit:
            chunk = os.read(descriptor, min(65536, limit + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
        after = os.fstat(descriptor)
        if (
            len(chunks) > limit
            or (before.st_dev, before.st_ino, before.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
            or len(chunks) != after.st_size
        ):
            raise ValueError("inspection output changed or exceeds its bound")
        return bytes(chunks)
    finally:
        os.close(descriptor)


def inspect_controlled_fixture(
    *,
    source_root: Path,
    operation_parent: Path,
    output_directory: Path,
    rcc_location: Path,
    package_id: PackageId,
    declared_paths: tuple[str, ...],
    protected_paths: tuple[str, ...],
    source_entries: tuple[source_manifest.SuppliedSourceEntry, ...],
    declared_actions: tuple[package_compiler.DeclaredAction, ...],
    provider: str | None,
    timeout_seconds: float = 120.0,
) -> ControlledFixtureInspection:
    """Inspect one explicit fixture with bounded RCC execution and source remeasurement."""
    if sys.platform != "linux":
        raise RuntimeError("controlled RCC inspection currently requires Linux")
    if not 0 < timeout_seconds <= 300:
        raise ValueError("inspection timeout must be within the supported bound")
    if provider is None:
        raise ValueError("controlled inspection requires an explicit provider context")
    source_root = Path(source_root).resolve()
    output_directory = Path(output_directory).resolve()
    operation_parent = Path(operation_parent).resolve()
    output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    operation_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    for directory in (output_directory, operation_parent):
        facts = directory.stat()
        if (
            not stat.S_ISDIR(facts.st_mode)
            or facts.st_uid != os.geteuid()
            or stat.S_IMODE(facts.st_mode) & 0o077
            or stat.S_IMODE(facts.st_mode) & 0o700 != 0o700
        ):
            raise ValueError("inspection directories must be owner-private")
        try:
            directory.relative_to(source_root)
        except ValueError:
            pass
        else:
            raise ValueError("inspection output and operations must be outside source")
    supplied_inventory = source_manifest.validate_proposed_inventory(
        source_entries, protected_input_names=protected_paths
    )
    expected = tuple(sorted(declared_paths, key=lambda x: x.encode("utf-8")))
    if tuple(entry.path for entry in supplied_inventory.entries) != expected:
        raise ValueError("fixture source entries differ from complete path declaration")
    _verify_complete_fixture_tree(source_root, expected)
    deadline = time.monotonic() + timeout_seconds
    nonce = os.urandom(16).hex()
    metadata_file = output_directory / f"metadata-{nonce}.json"
    receipt_file = output_directory / f"receipt-{nonce}.json"
    if metadata_file.exists() or receipt_file.exists():
        raise FileExistsError("inspection output name collision")
    result: ControlledFixtureInspection | None = None
    operation_root: Path | None = None
    with tempfile.TemporaryDirectory(
        prefix="rcc-inspect-", dir=operation_parent
    ) as operation:
        root = Path(operation)
        operation_root = root
        env = _private_environment(root)
        staged = root / "package"
        staged.mkdir(mode=0o700)
        with contextlib.ExitStack() as stack:
            source_fd = os.open(source_root, os.O_RDONLY | os.O_DIRECTORY)
            stack.callback(os.close, source_fd)
            stage_fd = os.open(staged, os.O_RDONLY | os.O_DIRECTORY)
            stack.callback(os.close, stage_fd)
            staged_proposal = source_staging.stage_selected_files(
                source_fd, stage_fd, expected, protected_input_names=protected_paths
            )
        measured = staged_proposal.source
        staged_entries = tuple(source_entries)
        if measured.inventory != supplied_inventory:
            raise ValueError("measured source differs from supplied fixture bytes")
        package_yaml = staged / "package.yaml"
        if "package.yaml" not in expected:
            raise ValueError("controlled RCC fixture must declare package.yaml")
        generation = compute_source_generation(staged)
        runner = _limited_runner(cwd=root, env=env, deadline=deadline, receipt=receipt_file)
        version = verify_rcc_version(rcc_location, runner=runner)
        prepared = prepare_runtime_for_inspection(
            package_yaml,
            rcc_location,
            source_generation=generation,
            provider=provider,
            runner=runner,
        )
        if prepared.runtime_descriptor.provider_reference != provider:
            raise ValueError("prepared RCC provider context differs from request")
        if (
            prepared.published_artifact_details.artifact_digest
            != prepared.runtime_descriptor.artifact_digest
        ):
            raise ValueError("published artifact pair differs from prepared runtime")
        command = build_exec_command(
            rcc_location,
            prepared.runtime_descriptor,
            ["python", "-c", _core_metadata_script(metadata_file), str(staged)],
            receipt_file=receipt_file,
        )
        code, stdout, stderr, cleanup = _run_bounded_rcc_process(
            command,
            cwd=root,
            env=env,
            output_limit=_OUTPUT_LIMIT,
            deadline=deadline,
            receipt=receipt_file,
        )
        if code != 0:
            raise RuntimeError(f"RCC inspection command failed ({code})")
        if len(stdout) + len(stderr) > _OUTPUT_LIMIT:
            raise ValueError("inspection process output exceeds its bound")
        receipt_bytes = _read_owned_regular_file(receipt_file, _RECEIPT_LIMIT)
        receipt = json.loads(receipt_bytes.decode("utf-8"))
        if (
            not isinstance(receipt, dict)
            or receipt.get("artifactDigest")
            != prepared.runtime_descriptor.artifact_digest
            or not isinstance(receipt.get("verification"), dict)
            or receipt["verification"].get("valid") is not True
            or not isinstance(receipt.get("leaseId"), str)
            or not receipt["leaseId"]
            or receipt.get("status") != "completed"
            or not isinstance(receipt.get("exitCode"), int)
            or isinstance(receipt.get("exitCode"), bool)
            or receipt["exitCode"] != code
            or receipt["exitCode"] != 0
        ):
            raise ValueError("RCC receipt does not confirm this completed invocation")
        materialization_id = receipt.get("materializationId")
        materialization_value = receipt.get("path")
        if not isinstance(materialization_id, str) or not materialization_id:
            raise ValueError("RCC receipt materialization identity is missing")
        if not isinstance(materialization_value, str) or not materialization_value:
            raise ValueError("RCC receipt materialization path is missing")
        rcc_home = Path(env["ROBOCORP_HOME"]).resolve(strict=True)
        materialization_path = Path(materialization_value).resolve(strict=True)
        try:
            materialization_path.relative_to(rcc_home)
        except ValueError:
            raise ValueError(
                "RCC receipt materialization path escapes the private RCC home"
            ) from None
        materialization_facts = materialization_path.stat()
        if (
            materialization_path == rcc_home
            or not stat.S_ISDIR(materialization_facts.st_mode)
            or materialization_facts.st_uid != os.geteuid()
        ):
            raise ValueError("RCC receipt materialization is not an owned directory")
        (
            metadata,
            core_version,
            core_origin,
            core_distribution_root,
            core_record_sha256,
            core_sys_prefix,
            managed_python,
            materialization_cwd,
            metadata_bytes,
        ) = _load_metadata(
            _read_owned_regular_file(metadata_file, _OUTPUT_LIMIT),
            staged,
            materialization_path,
        )
        supplied_actions = _supplied_actions(metadata, declared_actions, staged)
        compilation = package_compiler.compile_controlled_fixture(
            package_id=package_id,
            measured=measured,
            declared_paths=expected,
            protected_paths=protected_paths,
            source_entries=staged_entries,
            declared_actions=declared_actions,
            supplied_actions=supplied_actions,
            rcc=package_compiler.SuppliedRccIdentity(
                prepared.published_artifact_details.specification_digest,
                receipt["artifactDigest"],
            ),
        )
        # A second descriptor-based measure must still match initial source.
        source_fd = os.open(source_root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            from actions.server.deployments import source_read

            after = source_read.read_selected_files(
                source_fd, expected, protected_input_names=protected_paths
            )
        finally:
            os.close(source_fd)
        if after.inventory != measured.inventory:
            raise ValueError("source changed during RCC inspection")
        _verify_complete_fixture_tree(source_root, expected)
        staged_fd = os.open(staged, os.O_RDONLY | os.O_DIRECTORY)
        try:
            staged_after = source_read.read_selected_files(
                staged_fd, expected, protected_input_names=protected_paths
            )
        finally:
            os.close(staged_fd)
        if staged_after.inventory != measured.inventory:
            raise ValueError("staged source changed during RCC inspection")
        _verify_complete_fixture_tree(staged, expected)
        observation = InspectionObservation(
            status="PASS",
            rcc_version=version,
            specification_digest=prepared.published_artifact_details.specification_digest,
            artifact_digest=prepared.published_artifact_details.artifact_digest,
            provider_reference=prepared.runtime_descriptor.provider_reference,
            core_version=core_version,
            core_module_origin=core_origin,
            core_distribution_root=core_distribution_root,
            core_distribution_record_sha256=core_record_sha256,
            core_sys_prefix=core_sys_prefix,
            managed_python=managed_python,
            managed_prefix=str(materialization_path),
            materialization_path=str(materialization_path),
            materialization_id=materialization_id,
            materialization_cwd=materialization_cwd,
            exit_code=code,
            receipt_path=str(receipt_file),
            cleanup=cleanup,
            source_inventory_sha256=hashlib.sha256(
                measured.inventory.canonical_json
            ).hexdigest(),
            metadata_sha256=hashlib.sha256(metadata_bytes).hexdigest(),
            receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
            operation_cleanup_complete=False,
        )
        result = ControlledFixtureInspection(compilation, observation)
    if result is None:
        raise RuntimeError("inspection completed without an observation")
    cleanup_complete = operation_root is not None and not operation_root.exists()
    if not cleanup_complete:
        raise RuntimeError("inspection operation directory cleanup was incomplete")
    from dataclasses import replace

    return ControlledFixtureInspection(
        result.compilation,
        replace(result.observation, operation_cleanup_complete=True),
    )
