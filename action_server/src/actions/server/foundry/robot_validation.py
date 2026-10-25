"""Bounded host Robot dry-run validation, distinct from genuine task execution.

Library and variable imports can execute trusted developer code. The host must
check live source-execution/deploy grants before and throughout validation. This
module returns evidence to the existing registry; it stores no admission state.
"""
from __future__ import annotations

import json
import os
import selectors
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Literal
from uuid import uuid4
from xml.etree import ElementTree

import psutil

from actions.server._common.process import snapshot_process_descendants
from actions.server._rcc_runtime_adapter import (
    RccRuntimeDescriptor,
    build_exec_command,
    read_receipt,
)
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.foundry.robot_execution import (
    DirectRobotPreparation,
    RccRobotPreparation,
    RobotExecution,
)
from actions.server.foundry.robot_package_admission import (
    AdmittedRobotPackage,
    canonical,
    decode_robot_admission,
    digest,
)
from actions.server.foundry.robot_package_builder import (
    RccRobotPlan,
    verify_robot_package,
)

SCHEMA = "actions.robot-dryrun-validation/v1"
LOG_LIMIT = 256 * 1024
XML_LIMIT = 1024 * 1024

_CHILD = r"""
import platform, sys
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
suite.tests = selected
result = suite.run(dryrun=True, output=output, log=None, report=None,
                   variable=["INPUT_FILE:" + inputs], stdout=sys.stdout, stderr=sys.stderr)
sys.exit(result.return_code)
"""


@dataclass(frozen=True)
class RobotValidationResult:
    """Host-issued bounded diagnostics and canonical receipt for registry retention."""

    receipt_json: bytes
    stdout: bytes
    stderr: bytes
    output_xml: bytes
    rcc_receipt: bytes | None
    validation: Literal["passed", "failed"]
    validation_kind: Literal["robot-dryrun"] = "robot-dryrun"
    execution: Literal["not-qualified"] = "not-qualified"

    @property
    def ready(self) -> bool:
        return (
            self.validation == "passed"
            and self.validation_kind == "robot-dryrun"
            and self.execution == "not-qualified"
        )


@dataclass(frozen=True)
class _ProcessResult:
    exit_code: int
    stdout: bytes
    stderr: bytes


def _receipt(
    package: AdmittedRobotPackage, result: RobotValidationResult, exit_code: int
) -> bytes:
    robot = package.robot
    return canonical(
        {
            "schemaVersion": SCHEMA,
            "packageRevisionId": package.package_revision_id.root,
            "sourceDigest": robot.source_digest,
            "planDigest": robot.plan_digest,
            "runtimeKind": robot.plan.runtime_kind,
            "suitePath": robot.suite_path,
            "suiteName": robot.suite_name,
            "taskName": robot.task_name,
            "robotVersion": robot.plan.robot_version,
            "pythonVersion": list(robot.plan.python_version),
            "platformTag": robot.plan.platform_tag,
            "validationKind": result.validation_kind,
            "validation": result.validation,
            "execution": result.execution,
            "exitCode": exit_code,
            "stdoutDigest": digest(result.stdout),
            "stderrDigest": digest(result.stderr),
            "outputXmlDigest": digest(result.output_xml),
            "rccReceiptDigest": digest(result.rcc_receipt)
            if result.rcc_receipt is not None
            else None,
        }
    )


def verify_robot_validation(
    package: AdmittedRobotPackage, result: RobotValidationResult
) -> RobotValidationResult:
    """Verify retained bytes, not issuance authority; registry must enforce issuance."""
    if (
        type(result) is not RobotValidationResult
        or result.validation_kind != "robot-dryrun"
        or result.execution != "not-qualified"
        or result.validation not in ("passed", "failed")
        or len(result.receipt_json) > 16384
        or len(result.stdout) > LOG_LIMIT
        or len(result.stderr) > LOG_LIMIT
        or len(result.output_xml) > XML_LIMIT
        or (result.rcc_receipt is not None and len(result.rcc_receipt) > XML_LIMIT)
    ):
        raise ValueError("bounded Robot validation result required")
    if (result.rcc_receipt is None) != (package.robot.plan.runtime_kind == "direct"):
        raise ValueError("Robot validation runtime receipt differs")
    xml = result.output_xml.decode("utf-8")
    if "<!DOCTYPE" in xml or "<!ENTITY" in xml:
        raise ValueError("unsupported Robot XML declaration")
    root = ElementTree.fromstring(xml)
    suites, tasks = root.findall("suite"), root.findall(".//test")
    if (
        root.tag != "robot"
        or not root.get("generator", "").startswith("Robot 7.4.2 ")
        or len(suites) != 1
        or suites[0].get("name") != package.robot.suite_name
        or suites[0].findall(".//suite")
        or len(tasks) != 1
        or tasks[0].get("name") != package.robot.task_name
        or tasks[0] not in list(suites[0])
    ):
        raise ValueError("Robot dry-run XML selection differs")
    if result.validation == "passed" and any(
        node.get("level") in ("ERROR", "FAIL") for node in root.findall(".//msg")
    ):
        raise ValueError("Robot dry-run contains import or validation errors")
    if result.rcc_receipt is not None:
        if not isinstance(package.robot.plan, RccRobotPlan):
            raise ValueError("RCC receipt requires RCC Robot plan")
        value = json.loads(result.rcc_receipt)
        if (
            not isinstance(value, dict)
            or value.get("artifactDigest") != package.robot.plan.artifact_digest
            or not isinstance(value.get("verification"), dict)
            or value["verification"].get("valid") is not True
            or not isinstance(value.get("leaseId"), str)
            or not value["leaseId"]
            or (
                not isinstance(value.get("exitCode"), int)
                or isinstance(value.get("exitCode"), bool)
            )
            or value["exitCode"] != (0 if result.validation == "passed" else 1)
            or value.get("status")
            != ("completed" if result.validation == "passed" else "failed")
        ):
            raise ValueError("retained Robot RCC validation receipt differs")
    expected_status = "PASS" if result.validation == "passed" else "FAIL"
    for owner in (suites[0], tasks[0]):
        statuses = owner.findall("status")
        if len(statuses) != 1 or statuses[0].get("status") != expected_status:
            raise ValueError("Robot dry-run XML status differs")
    expected = _receipt(package, result, 0 if result.validation == "passed" else 1)
    if result.receipt_json != expected:
        raise ValueError("Robot validation receipt preimages differ")
    return result


class RobotValidator:
    """Execute one exact selected dry-run in a private host-owned directory."""

    def __init__(
        self, root: Path, preparation: DirectRobotPreparation | RccRobotPreparation
    ):
        # Reuse the execution adapter's platform/private-root checks, not its Run lifecycle.
        checked = RobotExecution(root, preparation)
        self.root, self.preparation = checked.root, checked.preparation

    def validate(
        self,
        package: AdmittedRobotPackage,
        *,
        check_live: Callable[[], None],
        timeout_seconds: int = 60,
    ) -> RobotValidationResult:
        if (
            not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool)
        ) or not 1 <= timeout_seconds <= 600:
            raise ValueError("bounded Robot validation deadline required")
        deadline = time.monotonic() + timeout_seconds

        def check():
            check_live()
            if time.monotonic() >= deadline:
                raise TimeoutError("Robot validation deadline exceeded")

        check()
        if (
            decode_robot_admission(package.manifest_json, package.source_archive)
            != package
        ):
            raise ValueError("Robot validation package differs")
        verify_robot_package(package.robot, preparation=self.preparation)
        directory = self.root / str(uuid4())
        directory.mkdir(mode=0o700)
        source = directory / "source"
        GeneratedRccExecution._extract_snapshot(package.source_archive, source)
        (directory / "input.json").write_bytes(b"{}")
        (directory / "tmp").mkdir(mode=0o700)
        environment = {
            "PATH": "/usr/sbin:/sbin:" + os.defpath,
            "LANG": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
            "TMPDIR": str(directory / "tmp"),
        }
        robot = package.robot
        arguments = [
            "-I",
            "-B",
            "-c",
            _CHILD,
            str(source),
            robot.suite_path,
            robot.suite_name,
            robot.task_name,
            str(directory / "input.json"),
            str(directory / "output.xml"),
        ]
        receipt_path = directory / "rcc-receipt.json"
        if type(self.preparation) is DirectRobotPreparation:
            command = [str(self.preparation.python), *arguments]
        else:
            prep = self.preparation
            if not isinstance(prep, RccRobotPreparation):
                raise ValueError("RCC Robot preparation required")
            environment.update(
                ROBOCORP_HOME=str(prep.environment.robocorp_home), RCC_NO_BUILD="1"
            )
            version = self._run(
                [str(prep.rcc), "--version"], source, environment, check, None
            )
            if version.exit_code != 0 or version.stdout.strip() != b"v18.19.3":
                raise ValueError("unsupported RCC version")
            command = build_exec_command(
                prep.rcc,
                RccRuntimeDescriptor(
                    artifact_digest=prep.environment.build_identity.artifact_digest,
                    provider_reference="local",
                ),
                ["python", *arguments],
                receipt_file=receipt_path,
                local_trust_carrier=prep.environment.robocorp_home
                / "artifacts/v1/trust",
            )
            command.insert(1, "--no-build")
        check()
        outcome = self._run(
            command, source, environment, check, directory / "output.xml"
        )
        check()
        for entry in robot.source.files:
            retained = source.joinpath(*PurePosixPath(entry.path).parts)
            if (
                RobotExecution._read(retained, len(entry.content)) != entry.content
                or stat.S_IMODE(retained.stat().st_mode) != entry.mode
            ):
                raise ValueError("Robot validation source changed")
        xml = RobotExecution._read(directory / "output.xml", XML_LIMIT)
        rcc_receipt = None
        if type(self.preparation) is RccRobotPreparation:
            rcc_receipt = RobotExecution._read(receipt_path, XML_LIMIT)
            value = read_receipt(
                receipt_path,
                self.preparation.environment.build_identity.artifact_digest,
            )
            if (
                (
                    not isinstance(value.get("exitCode"), int)
                    or isinstance(value.get("exitCode"), bool)
                )
                or value["exitCode"] != outcome.exit_code
                or value.get("status")
                != ("completed" if outcome.exit_code == 0 else "failed")
            ):
                raise ValueError("Robot validation RCC receipt differs")
        if outcome.exit_code not in (0, 1):
            raise ValueError("Robot validation exit status invalid")
        from dataclasses import replace

        result = RobotValidationResult(
            b"",
            outcome.stdout,
            outcome.stderr,
            xml,
            rcc_receipt,
            "passed" if outcome.exit_code == 0 else "failed",
        )
        result = replace(
            result, receipt_json=_receipt(package, result, outcome.exit_code)
        )
        verify_robot_validation(package, result)
        check()
        return result

    @staticmethod
    def _run(command, source, environment, check, output_xml):
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
        logs = {"stdout": bytearray(), "stderr": bytearray()}
        error = None
        selector = None
        try:
            selector = selectors.DefaultSelector()
            for name, stream in (
                ("stdout", process.stdout),
                ("stderr", process.stderr),
            ):
                if stream is None:
                    raise ValueError("Robot validation output pipe unavailable")
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                check()
                try:
                    for child in snapshot_process_descendants(process.pid):
                        descendants[(child.pid, child.create_time())] = child
                except psutil.NoSuchProcess:
                    pass
                if (
                    output_xml is not None
                    and output_xml.exists()
                    and output_xml.lstat().st_size > XML_LIMIT
                ):
                    raise ValueError("Robot validation XML exceeds limit")
                for key, _ in selector.select(timeout=0.05):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if len(logs[key.data]) + len(chunk) > LOG_LIMIT:
                        raise ValueError("Robot validation log exceeds limit")
                    logs[key.data].extend(chunk)
        except BaseException as exc:
            error = exc
        finally:
            if selector is not None:
                selector.close()
            cleanup = RobotExecution._cleanup(process, descendants, owns_session=True)
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        for name, content in logs.items():
            RobotExecution._write_log(source.parent / (name + ".log"), content)
        if not cleanup.execution_stopped:
            raise RuntimeError(
                "Robot validation process cleanup unconfirmed"
            ) from error
        if error is not None:
            raise error
        check()
        return _ProcessResult(
            process.returncode, bytes(logs["stdout"]), bytes(logs["stderr"])
        )
