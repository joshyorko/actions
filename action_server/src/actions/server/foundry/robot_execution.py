"""Trusted-host Robot execution only; canonical admission/publication stay upstream.

The lifecycle port must bind the entire selection to its admitted snapshot and
atomically reject an existing launch intent. This module owns no SQL, queue,
retry, terminal state, or registry. Source libraries are trusted developer code,
not an OS sandbox. Initial process supervision is Linux-only and fails closed
elsewhere. Execution directories remain host-owned reconciliation evidence.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Literal, Protocol
from uuid import uuid4
from xml.etree import ElementTree

import psutil
from jsonschema import Draft202012Validator

from actions.server._common.process import (
    ProcessTreeCleanupResult,
    force_kill_process_tree_until,
    snapshot_process_descendants,
)
from actions.server._rcc_runtime_adapter import (
    RccRuntimeDescriptor,
    build_exec_command,
    read_receipt,
)
from actions.server.deployments.package_revision_compiler import PreparedRccEnvironment
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    ExecutionSnapshot,
    OutputRef,
)

DISCRIMINATOR = "actions.robot-dispatch/v1"
ADAPTER_VERSION = "1"
ROBOT_VERSION = "7.4.2"
ROBOT_INPUT_LIMIT = 65536
_LOG_LIMIT = 256 * 1024
_XML_LIMIT = 1024 * 1024
_HEARTBEAT_SECONDS = 1.0
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _posix_flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError("POSIX operation requires " + name)
    return value


def _digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _json(content: bytes, limit: int):
    if not isinstance(content, bytes) or len(content) > limit:
        raise ValueError("bounded immutable JSON bytes required")
    value = json.loads(content)
    if (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        != content
    ):
        raise ValueError("canonical JSON bytes required")
    return value


def encode_robot_inputs(inputs: object) -> bytes:
    """Use the execution carrier's exact canonical encoding and byte budget."""
    content = json.dumps(
        inputs, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    _json(content, ROBOT_INPUT_LIMIT)
    return content


def _schema(content: bytes):
    schema = _json(content, 32768)
    if not isinstance(schema, dict):
        raise ValueError("object schema required")
    pending = [schema]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"$ref", "$dynamicRef"} and (
                    not isinstance(child, str) or not child.startswith("#/")
                ):
                    raise ValueError("external schema references unsupported")
                pending.append(child)
        elif isinstance(value, list):
            pending.extend(value)
    Draft202012Validator.check_schema(schema)
    return schema


def _executable(path: Path):
    if (
        not isinstance(path, Path)
        or not path.is_absolute()
        or not path.is_file()
        or not os.access(path, os.X_OK)
    ):
        raise ValueError("absolute trusted host executable required")


@dataclass(frozen=True)
class DirectRobotPreparation:
    python: Path

    def __post_init__(self):
        _executable(self.python)


@dataclass(frozen=True)
class RccRobotPreparation:
    rcc: Path
    environment: PreparedRccEnvironment

    def __post_init__(self):
        _executable(self.rcc)
        if type(self.environment) is not PreparedRccEnvironment:
            raise ValueError("retained RCC preparation required")


@dataclass(frozen=True)
class RobotSelection:
    """Host-verified plan/selection, never accepted directly from a request.

    Inputs reach Robot as an owned JSON file via the INPUT_FILE variable. The
    output schema describes {suite, task, status}, not a fabricated Action result.
    Host check_live must verify schema/plan provenance as well as the live fence.
    """

    snapshot: ExecutionSnapshot
    plan_kind: Literal["direct", "rcc"]
    suite_path: str
    suite_name: str
    task_name: str
    source_digest: str
    input_schema: bytes
    output_schema: bytes
    inputs: bytes
    adapter_version: str = ADAPTER_VERSION
    robot_version: str = ROBOT_VERSION
    python_version: tuple[int, int] = (3, 12)
    platform_tag: str = "linux-x86_64"
    rcc_specification_digest: str | None = None
    rcc_artifact_digest: str | None = None
    package_yaml_digest: str | None = None
    discriminator: str = DISCRIMINATOR

    def __post_init__(self):
        if not isinstance(self.snapshot, ExecutionSnapshot):
            raise ValueError("typed ExecutionSnapshot required")
        ExecutionSnapshot.model_validate(self.snapshot)
        if (
            self.discriminator != DISCRIMINATOR
            or self.adapter_version != ADAPTER_VERSION
            or self.robot_version != ROBOT_VERSION
        ):
            raise ValueError("unsupported Robot adapter/version")
        if self.python_version != (3, 12) or self.platform_tag != "linux-x86_64":
            raise ValueError("unsupported Robot platform/Python contract")
        if not isinstance(self.source_digest, str) or not _DIGEST.fullmatch(
            self.source_digest
        ):
            raise ValueError("source digest required")
        path = PurePosixPath(self.suite_path)
        if (
            not self.suite_path
            or path.is_absolute()
            or path.as_posix() != self.suite_path
            or "\\" in self.suite_path
            or any(p in {".", ".."} for p in path.parts)
            or path.suffix != ".robot"
        ):
            raise ValueError("exact relative Robot suite path required")
        for name in (self.suite_name, self.task_name):
            if (
                not isinstance(name, str)
                or not name
                or len(name) > 256
                or any(ord(c) < 32 for c in name)
            ):
                raise ValueError("exact bounded Robot name required")
        rcc_fields = (
            self.rcc_specification_digest,
            self.rcc_artifact_digest,
            self.package_yaml_digest,
        )
        if self.plan_kind == "direct":
            if any(value is not None for value in rcc_fields):
                raise ValueError("direct plan contains RCC fields")
        elif self.plan_kind == "rcc":
            if any(
                not isinstance(value, str) or not _DIGEST.fullmatch(value)
                for value in rcc_fields
            ):
                raise ValueError("RCC plan requires retained identities")
        else:
            raise ValueError("unsupported Robot plan")
        inputs = _json(self.inputs, ROBOT_INPUT_LIMIT)
        if not isinstance(inputs, dict):
            raise ValueError("Robot inputs must be an object")
        Draft202012Validator(_schema(self.input_schema)).validate(inputs)
        _schema(self.output_schema)


@dataclass(frozen=True)
class RobotLaunchIntent:
    selection: RobotSelection
    fence: AttemptFence
    launch_id: str
    discriminator: str = DISCRIMINATOR


@dataclass(frozen=True)
class RobotStagedOutput:
    ref: OutputRef
    name: str
    media_type: str
    digest: str
    byte_length: int
    observed_bytes: int
    truncated: bool


@dataclass(frozen=True)
class RobotExecutionResult:
    launch: RobotLaunchIntent
    status: Literal["PASS", "FAIL"]
    return_code: int
    outputs: tuple[RobotStagedOutput, ...]
    cleanup: ProcessTreeCleanupResult
    discriminator: str = DISCRIMINATOR


class RobotLifecycle(Protocol):
    def check_live(
        self, actor: Actor, fence: AttemptFence, selection: RobotSelection
    ) -> ExecutionSnapshot:
        ...

    def heartbeat(
        self, actor: Actor, fence: AttemptFence, selection: RobotSelection
    ) -> None:
        ...

    def launch_intent(
        self, actor: Actor, fence: AttemptFence
    ) -> RobotLaunchIntent | None:
        ...

    def record_launch_intent(
        self, actor: Actor, fence: AttemptFence, intent: RobotLaunchIntent
    ) -> RobotLaunchIntent:
        """Atomic absent->intent CAS with live authority; existing intent refuses."""
        ...

    def stage_output(
        self,
        actor: Actor,
        fence: AttemptFence,
        *,
        name: str,
        media_type: str,
        content: bytes,
    ) -> OutputRef:
        """Recheck live authority and stage bounded bytes; never publish."""
        ...


class RobotExecutionError(RuntimeError):
    def __init__(self, message: str, *, directory: Path | None = None):
        super().__init__(message)
        self.directory = directory


class RobotCleanupIncomplete(RobotExecutionError):
    """Keep resources and launch intent: observed process shutdown unconfirmed."""


class RobotCancellationStopped(RobotExecutionError):
    """Adapter cleanup evidence, not durable cancellation or mutation authority.

    The owner must independently verify persisted user cancellation: the adapter
    cancellation callback can also represent a host shutdown request.
    """

    def __init__(
        self,
        launch: RobotLaunchIntent,
        cleanup: ProcessTreeCleanupResult,
        *,
        directory: Path,
    ):
        if not cleanup.execution_stopped:
            raise ValueError("confirmed Robot execution shutdown required")
        super().__init__("Robot execution cancelled", directory=directory)
        self.launch = launch
        self.cleanup = cleanup


_CHILD = r"""
import json, platform, sys
from pathlib import Path
import robot
from robot.api import TestSuiteBuilder
source, suite_path, suite_name, task_name, inputs, output = sys.argv[1:]
if robot.__version__ != "7.4.2" or sys.version_info[:2] != (3, 12):
    raise RuntimeError("Robot/Python preparation differs from pinned plan")
if sys.platform + "-" + platform.machine().lower() != "linux-x86_64":
    raise RuntimeError("Robot platform differs from pinned plan")
sys.path.insert(0, source)
suite = TestSuiteBuilder().build(str(Path(source) / suite_path))
if suite.name != suite_name or suite.suites:
    raise RuntimeError("exact leaf suite required")
selected = [task for task in suite.tests if task.name == task_name]
if len(selected) != 1:
    raise RuntimeError("exact unique task required")
# Select actual model objects, not Robot CLI wildcard/normalized name matching.
suite.tests = selected
result = suite.run(output=output, variable=["INPUT_FILE:" + inputs],
                   stdout=sys.stdout, stderr=sys.stderr)
sys.exit(result.return_code)
"""


class RobotExecution:
    root: Path
    preparation: DirectRobotPreparation | RccRobotPreparation

    def __init__(
        self,
        execution_root: Path,
        preparation: DirectRobotPreparation | RccRobotPreparation,
    ):
        if sys.platform != "linux" or platform.machine().lower() != "x86_64":
            raise ValueError("unsupported host supervision platform")
        if not isinstance(execution_root, Path) or not execution_root.is_absolute():
            raise ValueError("absolute owned execution root required")
        if any(
            parent.is_symlink() for parent in (execution_root, *execution_root.parents)
        ):
            raise ValueError("execution root aliases unsupported")
        execution_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not execution_root.is_dir() or execution_root.stat().st_mode & 0o077:
            raise ValueError("private execution root required")
        if type(preparation) not in (DirectRobotPreparation, RccRobotPreparation):
            raise ValueError("trusted typed Robot preparation required")
        self.root = execution_root
        self.preparation = preparation

    def execute(
        self,
        actor: Actor,
        fence: AttemptFence,
        *,
        selection: RobotSelection,
        source_archive: bytes,
        lifecycle: RobotLifecycle,
        cancelled: Callable[[], bool],
        timeout_seconds: int,
    ) -> RobotExecutionResult:
        actor, fence = Actor.model_validate(actor), AttemptFence.model_validate(fence)
        if type(selection) is not RobotSelection:
            raise ValueError("typed immutable Robot selection required")
        # Recheck values even if a caller bypassed dataclass construction.
        selection.__post_init__()
        if (
            sys.platform != "linux"
            or sys.platform + "-" + platform.machine().lower() != selection.platform_tag
        ):
            raise ValueError("unsupported host supervision platform")
        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or not 1 <= timeout_seconds <= 600
            or not callable(cancelled)
        ):
            raise ValueError("bounded deadline and cancellation predicate required")
        if (
            not isinstance(source_archive, bytes)
            or len(source_archive) > 16 * 1024 * 1024
            or _digest(source_archive) != selection.source_digest
        ):
            raise ValueError("retained source digest/size differs")
        direct = isinstance(self.preparation, DirectRobotPreparation)
        if direct != (selection.plan_kind == "direct"):
            raise ValueError("plan/preparation mismatch; no fallback")
        deadline = time.monotonic() + timeout_seconds
        cancellation_error = RobotExecutionError("Robot execution cancelled")
        stopped_cleanup: ProcessTreeCleanupResult | None = None

        from actions.work_items._fencing import ClaimRejected

        from actions.server.run_outputs.service import FenceRejected

        def confirm_stopped_cancellation(error):
            if stopped_cleanup is None:
                return
            confirmed = error is cancellation_error
            if type(error) in (FenceRejected, ClaimRejected):
                try:
                    confirmed = cancelled() is True
                except BaseException as recheck_error:
                    raise recheck_error from error
            if confirmed:
                raise RobotCancellationStopped(
                    intent, stopped_cleanup, directory=directory
                ) from error

        def check():
            if cancelled():
                if stopped_cleanup is not None:
                    raise RobotCancellationStopped(
                        intent, stopped_cleanup, directory=directory
                    )
                raise cancellation_error
            if time.monotonic() >= deadline:
                raise RobotExecutionError("Robot execution deadline exceeded")
            try:
                current = lifecycle.check_live(actor, fence, selection)
            except (FenceRejected, ClaimRejected) as exc:
                confirm_stopped_cancellation(exc)
                raise
            if current != selection.snapshot:
                raise RobotExecutionError("live execution snapshot differs")

        check()
        if lifecycle.launch_intent(actor, fence) is not None:
            raise RobotExecutionError("prior launch requires reconciliation")
        directory = self.root / str(uuid4())
        directory.mkdir(mode=0o700)
        source = directory / "source"
        GeneratedRccExecution._extract_snapshot(source_archive, source)
        suite = source.joinpath(*PurePosixPath(selection.suite_path).parts)
        self._read(suite, 1024 * 1024)
        (directory / "input.json").write_bytes(selection.inputs)
        (directory / "tmp").mkdir(mode=0o700)
        environment = {
            "PATH": "/usr/sbin:/sbin:" + os.defpath,
            "LANG": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
            "TMPDIR": str(directory / "tmp"),
        }
        arguments = [
            "-I",
            "-B",
            "-c",
            _CHILD,
            str(source),
            selection.suite_path,
            selection.suite_name,
            selection.task_name,
            str(directory / "input.json"),
            str(directory / "output.xml"),
        ]
        rcc_receipt = directory / "rcc-receipt.json"
        prep = self.preparation
        if isinstance(prep, DirectRobotPreparation):
            command = [str(prep.python), *arguments]
        else:
            retained = prep.environment
            if (
                retained.build_identity.specification_digest
                != selection.rcc_specification_digest
                or retained.build_identity.artifact_digest
                != selection.rcc_artifact_digest
                or retained.package_yaml_digest != selection.package_yaml_digest
                or _digest(self._read(source / "package.yaml", 32768))
                != selection.package_yaml_digest
            ):
                raise ValueError("retained RCC preparation differs from plan/source")
            environment.update(
                ROBOCORP_HOME=str(retained.robocorp_home), RCC_NO_BUILD="1"
            )
            version = subprocess.run(
                [str(prep.rcc), "--version"],
                env=environment,
                capture_output=True,
                timeout=min(15, timeout_seconds),
                check=True,
            )
            if version.stdout.strip() != b"v18.19.3":
                raise ValueError("unsupported RCC version")
            command = build_exec_command(
                prep.rcc,
                RccRuntimeDescriptor(
                    artifact_digest=retained.build_identity.artifact_digest,
                    provider_reference="local",
                ),
                ["python", *arguments],
                receipt_file=rcc_receipt,
                local_trust_carrier=retained.robocorp_home / "artifacts/v1/trust",
            )
            command.insert(1, "--no-build")
        check()
        intent = RobotLaunchIntent(selection, fence, directory.name)
        confirmed = lifecycle.record_launch_intent(actor, fence, intent)
        if confirmed != intent or lifecycle.launch_intent(actor, fence) != intent:
            raise RobotExecutionError(
                "launch intent uncertain; reconciliation required", directory=directory
            )
        lifecycle.heartbeat(actor, fence, selection)
        check()
        process = subprocess.Popen(
            command,
            cwd=source,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        descendants = {}
        observed = {"stdout": 0, "stderr": 0}
        retained_logs = {"stdout": bytearray(), "stderr": bytearray()}
        selector = None
        heartbeat = time.monotonic()
        error = None
        try:
            selector = selectors.DefaultSelector()
            for name, stream in (
                ("stdout", process.stdout),
                ("stderr", process.stderr),
            ):
                if stream is None:
                    raise RobotExecutionError("Robot output pipe unavailable")
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                check()
                if process.poll() is None:
                    try:
                        for child in snapshot_process_descendants(process.pid):
                            descendants[(child.pid, child.create_time())] = child
                    except psutil.NoSuchProcess:
                        # Normal wrapper/child exit can race the snapshot. The
                        # final group sweep still verifies observed shutdown.
                        pass
                if time.monotonic() >= heartbeat:
                    lifecycle.heartbeat(actor, fence, selection)
                    heartbeat = time.monotonic() + _HEARTBEAT_SECONDS
                if (directory / "output.xml").exists() and (
                    directory / "output.xml"
                ).lstat().st_size > _XML_LIMIT:
                    raise RobotExecutionError("Robot XML exceeds limit")
                for key, _ in selector.select(timeout=0.05):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    name = key.data
                    observed[name] += len(chunk)
                    retained_logs[name].extend(
                        chunk[: max(0, _LOG_LIMIT - len(retained_logs[name]))]
                    )
                    self._write_log(directory / (name + ".log"), retained_logs[name])
        except BaseException as exc:
            error = exc
        finally:
            try:
                if selector is not None:
                    selector.close()
            except BaseException as exc:
                error = error or exc
            cleanup = self._cleanup(process, descendants, owns_session=True)
            for stream in (process.stdout, process.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except BaseException as exc:
                    error = error or exc
            for name in retained_logs:
                try:
                    self._write_log(directory / (name + ".log"), retained_logs[name])
                except BaseException as exc:
                    error = error or exc
        if not cleanup.execution_stopped:
            raise RobotCleanupIncomplete(
                "Robot process cleanup unconfirmed; retain resources",
                directory=directory,
            ) from error
        stopped_cleanup = cleanup
        if error is not None:
            # Cancellation can commit between the callback and a lifecycle
            # fence/claim check. Recheck only those exact authority failures;
            # unrelated errors must never become cancellation evidence.
            confirm_stopped_cancellation(error)
            if isinstance(error, RobotExecutionError):
                error.directory = directory
            raise error
        check()
        # Re-read only the bounded admitted inventory, never arbitrary workload
        # output files. Changed retained code cannot receive staged evidence.
        try:
            with zipfile.ZipFile(io.BytesIO(source_archive)) as archive:
                for info in archive.infolist():
                    path = source.joinpath(*PurePosixPath(info.filename).parts)
                    if self._read(path, info.file_size) != archive.read(
                        info
                    ) or stat.S_IMODE(path.stat().st_mode) != stat.S_IMODE(
                        info.external_attr >> 16
                    ):
                        raise ValueError("changed source")
        except (OSError, ValueError):
            raise RobotExecutionError(
                "retained source changed during execution", directory=directory
            ) from None
        xml = self._read(directory / "output.xml", _XML_LIMIT)
        if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
            raise RobotExecutionError(
                "unsupported Robot XML declaration", directory=directory
            )
        document = ElementTree.fromstring(xml)
        suites, tasks = document.findall("suite"), document.findall(".//test")
        if (
            not document.get("generator", "").startswith("Robot " + ROBOT_VERSION + " ")
            or len(suites) != 1
            or suites[0].get("name") != selection.suite_name
            or len(tasks) != 1
            or tasks[0].get("name") != selection.task_name
            or tasks[0] not in list(suites[0])
        ):
            raise RobotExecutionError(
                "Robot XML task/suite identity differs", directory=directory
            )
        status_node = tasks[0].find("status")
        status = status_node.get("status") if status_node is not None else None
        if status not in {"PASS", "FAIL"} or process.returncode != (
            0 if status == "PASS" else 1
        ):
            raise RobotExecutionError("Robot status/exit mismatch", directory=directory)
        Draft202012Validator(_schema(selection.output_schema)).validate(
            {
                "suite": selection.suite_name,
                "task": selection.task_name,
                "status": status,
            }
        )
        payloads = [
            (
                "robot-stdout.log",
                "application/octet-stream",
                bytes(retained_logs["stdout"]),
                observed["stdout"],
            ),
            (
                "robot-stderr.log",
                "application/octet-stream",
                bytes(retained_logs["stderr"]),
                observed["stderr"],
            ),
            ("robot-output.xml", "application/xml", xml, len(xml)),
        ]
        if not direct:
            if selection.rcc_artifact_digest is None:
                raise RobotExecutionError("RCC artifact identity unavailable")
            receipt = self._read(rcc_receipt, _XML_LIMIT)
            execution_receipt = read_receipt(rcc_receipt, selection.rcc_artifact_digest)
            exit_code = execution_receipt.get("exitCode")
            if (
                not isinstance(exit_code, int)
                or isinstance(exit_code, bool)
                or exit_code != process.returncode
                or execution_receipt.get("status")
                != ("completed" if status == "PASS" else "failed")
            ):
                raise RobotExecutionError(
                    "RCC receipt/status differs", directory=directory
                )
            payloads.append(
                ("rcc-receipt.json", "application/json", receipt, len(receipt))
            )
        outputs = []
        for name, media, content, seen in payloads:
            check()
            try:
                ref = lifecycle.stage_output(
                    actor, fence, name=name, media_type=media, content=content
                )
            except (FenceRejected, ClaimRejected) as exc:
                confirm_stopped_cancellation(exc)
                raise
            ref = OutputRef.model_validate(ref)
            if ref.run_id != fence.run_id or ref.workspace_id != str(
                selection.snapshot.deployment.workspace_id.root
            ):
                raise RobotExecutionError(
                    "staged output scope differs", directory=directory
                )
            outputs.append(
                RobotStagedOutput(
                    ref,
                    name,
                    media,
                    _digest(content),
                    len(content),
                    seen,
                    seen > len(content),
                )
            )
        check()
        status_value: Literal["PASS", "FAIL"] = "PASS" if status == "PASS" else "FAIL"
        return RobotExecutionResult(
            intent, status_value, process.returncode, tuple(outputs), cleanup
        )

    @staticmethod
    def _cleanup(process, descendants, *, owns_session=False):
        # A process may orphan a child between descendant samples. All ordinary
        # descendants inherit our new session's process group; inspect it even
        # after the wrapper exits. Deliberate session escape is outside this
        # trusted-code adapter (not an OS sandbox).
        deadline = time.monotonic() + 5
        try:
            if owns_session is not True or os.name != "posix":
                raise ValueError("owned POSIX session required")
            try:
                if os.getpgid(process.pid) != process.pid:
                    raise ValueError("wrapper does not own its process group")
            except ProcessLookupError:
                # A reaped wrapper can leave members of its trusted owned group.
                pass
            while True:
                # Popen above created this owned session. Stop its kernel-owned
                # group before sampling: a sampled member could otherwise fork
                # and exit before status inspection, hiding a live descendant.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                for candidate in psutil.process_iter():
                    try:
                        if (
                            candidate.pid != process.pid
                            and os.getpgid(candidate.pid) == process.pid
                        ):
                            descendants[
                                (candidate.pid, candidate.create_time())
                            ] = candidate
                    except (ProcessLookupError, psutil.NoSuchProcess):
                        continue
                alive = []
                for candidate in descendants.values():
                    try:
                        if candidate.is_running():
                            alive.append(candidate)
                    except psutil.NoSuchProcess:
                        pass
                result = force_kill_process_tree_until(
                    process, alive, deadline, snapshot_complete_before_call=True
                )
                # Verify the group after termination; late-spawned live members
                # must be included in another bounded cleanup pass.
                remaining = []
                for candidate in psutil.process_iter():
                    try:
                        if (
                            candidate.pid != process.pid
                            and os.getpgid(candidate.pid) == process.pid
                            and candidate.status() != psutil.STATUS_ZOMBIE
                        ):
                            remaining.append(candidate)
                    except (ProcessLookupError, psutil.NoSuchProcess):
                        continue
                if not remaining:
                    return result
                if time.monotonic() >= deadline:
                    return ProcessTreeCleanupResult(
                        result.wrapper_reaped,
                        tuple(p.pid for p in remaining),
                        result.zombie_descendant_pids,
                        ("Robot process group cleanup exceeded deadline",),
                        False,
                    )
        except Exception:
            return ProcessTreeCleanupResult(
                process.poll() is not None,
                (),
                (),
                ("Robot process cleanup inspection failed",),
                False,
            )

    @staticmethod
    def _write_log(path: Path, content: bytes | bytearray):
        fd = os.open(
            path,
            os.O_WRONLY
            | os.O_CREAT
            | _posix_flag("O_NOFOLLOW")
            | _posix_flag("O_NONBLOCK"),
            0o600,
        )
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("regular single-link Robot diagnostic required")
            os.ftruncate(fd, 0)
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(content)
        finally:
            os.close(fd)

    @staticmethod
    def _read(path: Path, limit: int) -> bytes:
        # O_NONBLOCK is required before fstat: opening a FIFO read-only can hang
        # forever after the workload exits, outside the execution deadline.
        if any(parent.is_symlink() for parent in path.parents):
            raise ValueError("Robot evidence parent alias refused")
        fd = os.open(
            path, os.O_RDONLY | _posix_flag("O_NOFOLLOW") | _posix_flag("O_NONBLOCK")
        )
        try:
            before = os.fstat(fd)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size > limit
            ):
                raise ValueError("bounded single-link regular Robot evidence required")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                content = stream.read(limit + 1)
            after = os.fstat(fd)
            if (
                len(content) > limit
                or len(content) != before.st_size
                or (
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                    before.st_ctime_ns,
                    before.st_mode,
                    before.st_nlink,
                )
                != (
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                    after.st_ctime_ns,
                    after.st_mode,
                    after.st_nlink,
                )
            ):
                raise ValueError("Robot evidence changed or exceeds limit")
            return content
        finally:
            os.close(fd)
