"""Private, source-bound inspection of one explicitly declared v2 fixture.

This observes RCC metadata for a harness-owned fixture. It does not establish
authorization, arbitrary-package completeness, admission, publication, or a
security sandbox.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import time
import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from actions.server._common.process import ProcessTreeCleanupResult
from actions.server._rcc_runtime_adapter import (
    RccProcessHandle,
    build_exec_command,
    compute_source_generation,
    prepare_runtime_for_inspection,
    read_receipt,
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
    exit_code: int
    cleanup: ProcessTreeCleanupResult
    source_inventory_sha256: str
    metadata_sha256: str
    receipt_sha256: str
    operation_cleanup_complete: bool


@dataclass(frozen=True)
class ControlledFixtureInspection:
    compilation: package_compiler.ProposedControlledCompilation
    observation: InspectionObservation


def _limited_runner(deadline: float):
    def run(*args: str) -> tuple[int, str, str]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("RCC inspection deadline expired")
        proc = subprocess.Popen(
            list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        if proc.stdout is None or proc.stderr is None:
            raise RuntimeError("RCC preparation output pipes were not created")
        handle = RccProcessHandle(proc, Path(os.devnull))
        buffers = [bytearray(), bytearray()]
        over_limit = threading.Event()

        def drain(stream, buffer):
            while True:
                chunk = stream.read(16 * 1024)
                if not chunk:
                    return
                room = _OUTPUT_LIMIT + 1 - len(buffer)
                if room > 0:
                    buffer.extend(chunk[:room])
                if len(buffer) > _OUTPUT_LIMIT:
                    over_limit.set()

        threads = [
            threading.Thread(target=drain, args=(proc.stdout, buffers[0]), daemon=True),
            threading.Thread(target=drain, args=(proc.stderr, buffers[1]), daemon=True),
        ]
        error: BaseException | None = None
        timed_out = False
        for thread in threads:
            thread.start()
        try:
            _wait_capturing_descendants(handle, deadline)
        except subprocess.TimeoutExpired:
            timed_out = True
        except BaseException as exc:
            error = exc
        finally:
            cleanup = _cleanup_tree(handle)
            proc.stdout.close()
            proc.stderr.close()
            close_deadline = time.monotonic() + _CLEANUP_SECONDS
            for thread in threads:
                thread.join(timeout=max(0, close_deadline - time.monotonic()))
        if not cleanup.descendant_reap_complete or any(
            thread.is_alive() for thread in threads
        ):
            raise RuntimeError(
                "RCC preparation process cleanup was incomplete"
            ) from error
        if timed_out:
            raise TimeoutError("RCC preparation command timed out") from None
        if error is not None:
            raise error
        if over_limit.is_set():
            raise ValueError("RCC preparation output exceeds its bound")
        return (
            proc.returncode,
            buffers[0].decode("utf-8", "replace"),
            buffers[1].decode("utf-8", "replace"),
        )

    return run


def _cleanup_tree(handle: RccProcessHandle) -> ProcessTreeCleanupResult:
    if handle._owned_processes is None:
        try:
            handle.capture_owned_processes()
        except Exception:
            pass
    return handle.force_kill_until(time.monotonic() + _CLEANUP_SECONDS)


def _wait_capturing_descendants(handle: RccProcessHandle, deadline: float) -> int:
    """Wait while retaining snapshots of children that appear after spawn."""
    owned: dict[tuple[int, float], Any] = {}
    process = handle.process
    while process.poll() is None:
        try:
            children = handle.capture_owned_processes()
        except Exception:
            if process.poll() is not None:
                break
            raise
        for child in children:
            try:
                owned[(child.pid, child.create_time())] = child
            except Exception:
                continue
        handle._owned_processes = list(owned.values())
        handle._owned_snapshot_complete = True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(process.args, 0)
        try:
            return handle.wait(timeout=min(0.02, remaining))
        except subprocess.TimeoutExpired:
            continue
    return process.returncode


def _run_exec(
    command: list[str], *, cwd: Path, output_limit: int, deadline: float, receipt: Path
):
    env = dict(os.environ)
    for name in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(name, None)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    if process.stdout is None or process.stderr is None:
        raise RuntimeError("RCC inspection output pipes were not created")
    handle = RccProcessHandle(process, receipt)
    buffers = [bytearray(), bytearray()]
    over_limit = threading.Event()

    def drain(stream, buffer):
        while True:
            chunk = stream.read(16 * 1024)
            if not chunk:
                return
            room = output_limit + 1 - len(buffer)
            if room > 0:
                buffer.extend(chunk[:room])
            if len(buffer) > output_limit:
                over_limit.set()

    threads = [
        threading.Thread(target=drain, args=(process.stdout, buffers[0]), daemon=True),
        threading.Thread(target=drain, args=(process.stderr, buffers[1]), daemon=True),
    ]
    for thread in threads:
        thread.start()
    error: BaseException | None = None
    timed_out = False
    code: int | None = None
    try:
        code = _wait_capturing_descendants(handle, deadline)
    except (subprocess.TimeoutExpired, TimeoutError) as exc:
        timed_out = True
        error = exc
    except BaseException as exc:
        error = exc
    finally:
        cleanup = _cleanup_tree(handle)
        process.stdout.close()
        process.stderr.close()
        close_deadline = time.monotonic() + _CLEANUP_SECONDS
        for thread in threads:
            thread.join(timeout=max(0, close_deadline - time.monotonic()))
    if not cleanup.descendant_reap_complete or any(
        thread.is_alive() for thread in threads
    ):
        raise RuntimeError(
            f"RCC inspection process cleanup was incomplete; cleanup_complete={cleanup.descendant_reap_complete}; "
            f"snapshot={cleanup.descendant_snapshot_complete}; live={cleanup.live_descendant_pids}; "
            f"zombies={cleanup.zombie_descendant_pids}; errors={cleanup.errors}"
        ) from error
    if timed_out:
        raise TimeoutError(
            f"RCC inspection timed out; cleanup_complete={cleanup.descendant_reap_complete}"
        ) from None
    if error is not None:
        raise error
    if code is None:
        raise RuntimeError("RCC inspection process returned no status")
    if not cleanup.descendant_reap_complete:
        raise RuntimeError("RCC inspection process cleanup was incomplete")
    if over_limit.is_set():
        raise ValueError("RCC inspection output exceeds its bound")
    return code, bytes(buffers[0]), bytes(buffers[1]), cleanup


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
        "with contextlib.redirect_stdout(capture): actions.cli.main(['metadata', sys.argv[1]])\n"
        "metadata = json.loads(capture.getvalue())\n"
        "distribution = importlib.metadata.distribution('actions-core')\n"
        "record = distribution.read_text('RECORD')\n"
        "origin = pathlib.Path(actions.__file__).resolve()\n"
        "recorded = any(str(item).replace('\\\\', '/') == 'actions/__init__.py' and pathlib.Path(distribution.locate_file(item)).resolve() == origin for item in (distribution.files or ()))\n"
        "metadata['_inspection_core'] = {'version': distribution.version, 'origin': str(origin), 'distribution_root': str(pathlib.Path(distribution.locate_file('')).resolve()), 'record_sha256': hashlib.sha256((record or '').encode()).hexdigest(), 'recorded_origin': recorded, 'sys_prefix': sys.prefix}\n"
        "encoded = json.dumps(metadata).encode('utf-8')\n"
        "if len(encoded) > 1048576: raise ValueError('metadata output exceeds the byte bound')\n"
        f"pathlib.Path({str(metadata_path)!r}).write_bytes(encoded)\n"
    )


def _load_metadata(
    path: Path, package_dir: Path
) -> tuple[dict[str, Any], str, str, str, str, str, bytes]:
    if not path.is_file() or path.stat().st_size > _OUTPUT_LIMIT:
        raise ValueError("inspection metadata is missing or exceeds its bound")
    raw = path.read_bytes()
    value = json.loads(raw)
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
    for evidence_path in (origin, distribution_root):
        try:
            evidence_path.relative_to(prefix)
        except ValueError:
            raise ValueError(
                "installed Core provenance is outside its interpreter prefix"
            ) from None
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
        core["sys_prefix"],
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
    metadata_file = output_directory / f"metadata-{os.urandom(8).hex()}.json"
    receipt_file = output_directory / f"receipt-{os.urandom(8).hex()}.json"
    result: ControlledFixtureInspection | None = None
    with tempfile.TemporaryDirectory(
        prefix="rcc-inspect-", dir=operation_parent
    ) as operation:
        root = Path(operation)
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
        runner = _limited_runner(deadline)
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
            [sys.executable, "-c", _core_metadata_script(metadata_file), str(staged)],
            receipt_file=receipt_file,
        )
        code, stdout, stderr, cleanup = _run_exec(
            command,
            cwd=staged,
            output_limit=_OUTPUT_LIMIT,
            deadline=deadline,
            receipt=receipt_file,
        )
        if code != 0:
            raise RuntimeError(f"RCC inspection command failed ({code})")
        if len(stdout) + len(stderr) > _OUTPUT_LIMIT:
            raise ValueError("inspection process output exceeds its bound")
        if not receipt_file.is_file() or receipt_file.stat().st_size > _RECEIPT_LIMIT:
            raise ValueError("RCC receipt is missing or exceeds its bound")
        receipt_bytes = receipt_file.read_bytes()
        receipt = read_receipt(
            receipt_file, prepared.runtime_descriptor.artifact_digest
        )
        (
            metadata,
            core_version,
            core_origin,
            core_distribution_root,
            core_record_sha256,
            core_sys_prefix,
            metadata_bytes,
        ) = _load_metadata(metadata_file, staged)
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
            exit_code=code,
            cleanup=cleanup,
            source_inventory_sha256=hashlib.sha256(
                repr(measured.inventory).encode()
            ).hexdigest(),
            metadata_sha256=hashlib.sha256(metadata_bytes).hexdigest(),
            receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
            operation_cleanup_complete=False,
        )
        result = ControlledFixtureInspection(compilation, observation)
    if result is None:
        raise RuntimeError("inspection completed without an observation")
    cleanup_complete = not any(
        path.name.startswith("rcc-inspect-") for path in operation_parent.iterdir()
    )
    if not cleanup_complete:
        raise RuntimeError("inspection operation directory cleanup was incomplete")
    from dataclasses import replace

    return ControlledFixtureInspection(
        result.compilation,
        replace(result.observation, operation_cleanup_complete=True),
    )
