"""Command/receipt contracts use synthetic subprocess outcomes, not real dry-runs."""
import json
import platform
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from actions.server.deployments.package_revision_compiler import (
    PreparedRccEnvironment,
    RccBuildIdentity,
)
from actions.server.foundry.robot_authoring import parse_robot_backend
from actions.server.foundry.robot_execution import (
    DirectRobotPreparation,
    RccRobotPreparation,
)
from actions.server.foundry.robot_package_admission import (
    assemble_robot_admission,
    digest,
)
from actions.server.foundry.robot_package_builder import build_robot_package
from actions.server.foundry.robot_validation import (
    RobotValidator,
    _ProcessResult,
    _receipt,
    verify_robot_validation,
)


def xml(status="PASS", task="Selected"):
    return f'<robot generator="Robot 7.4.2 (Python 3.12)"><suite name="Tasks"><test name="{task}"><status status="{status}"/></test><status status="{status}"/></suite></robot>'.encode()


@pytest.fixture(params=["direct", "rcc"])
def configured(tmp_path, request):
    files = [
        dict(path="tasks.robot", content="*** Tasks ***\nSelected\n    No Operation\n")
    ]
    prep = DirectRobotPreparation(Path(sys.executable))
    if request.param == "rcc":
        content = "dependencies: {}\n"
        files.append(dict(path="package.yaml", content=content))
        prep = RccRobotPreparation(
            Path(sys.executable),
            PreparedRccEnvironment(
                tmp_path,
                digest(content.encode()),
                RccBuildIdentity("sha256:" + "1" * 64, "sha256:" + "2" * 64),
            ),
        )
    req = parse_robot_backend(
        dict(
            kind="robot",
            logicalName="Robot",
            files=files,
            suitePath="tasks.robot",
            suiteName="Tasks",
            taskName="Selected",
            inputSchema={"type": "object"},
            runtimeKind=request.param,
        )
    )
    package = assemble_robot_admission(
        build_robot_package(req, preparation=prep), "owned-robot"
    )
    root = tmp_path / "validation"
    validator = RobotValidator(root, prep)
    calls = []

    def run(command, source, environment, check, output_xml):
        check()
        calls.append(command)
        if command[-1] == "--version":
            return _ProcessResult(0, b"v18.19.3\n", b"")
        output_xml.write_bytes(xml())
        if request.param == "rcc":
            (source.parent / "rcc-receipt.json").write_text(
                json.dumps(
                    dict(
                        artifactDigest=prep.environment.build_identity.artifact_digest,
                        verification={"valid": True},
                        leaseId="synthetic",
                        exitCode=0,
                        status="completed",
                    )
                )
            )
        return _ProcessResult(0, b"synthetic stdout", b"")

    validator._run = run
    return package, validator, calls


def test_exact_command_and_receipt_contract(configured):
    package, validator, calls = configured
    result = validator.validate(package, check_live=lambda: None)
    assert result.ready and result.execution == "not-qualified"
    assert verify_robot_validation(package, result) == result
    receipt = json.loads(result.receipt_json)
    assert receipt["packageRevisionId"] == package.package_revision_id.root
    assert receipt["sourceDigest"] == package.robot.source_digest
    assert receipt["planDigest"] == package.robot.plan_digest
    assert receipt["validationKind"] == "robot-dryrun"
    command = calls[-1]
    script = command[command.index("-c") + 1]
    assert "dryrun=True" in script and "task.name == task_name" in script
    assert "suite.tests = selected" in script
    assert "log=None, report=None" in script
    compile(script, "robot-dryrun-child", "exec")
    if package.robot.plan.runtime_kind == "direct":
        assert len(calls) == 1 and "--no-build" not in command
        assert result.rcc_receipt is None
    else:
        assert len(calls) == 2 and "--no-build" in command
        assert "--artifact" in command


@pytest.mark.parametrize(
    "mutation", ["receipt", "xml", "stdout", "execution", "other-task"]
)
def test_tamper_rejected(configured, mutation):
    package, validator, _ = configured
    result = validator.validate(package, check_live=lambda: None)
    updates = {
        "receipt": {"receipt_json": b"{}"},
        "xml": {"output_xml": xml("FAIL")},
        "stdout": {"stdout": b"changed"},
        "execution": {"execution": "qualified"},
        "other-task": {"output_xml": xml(task="Other")},
    }[mutation]
    with pytest.raises(ValueError):
        verify_robot_validation(package, replace(result, **updates))


def test_revoked_before_process(configured):
    package, validator, calls = configured

    def denied():
        raise PermissionError("revoked")

    with pytest.raises(PermissionError):
        validator.validate(package, check_live=denied)
    assert calls == []


def test_revoked_after_process(configured):
    package, validator, _ = configured
    original = validator._run
    revoked = False

    def check():
        if revoked:
            raise PermissionError("revoked")

    def run(*args):
        nonlocal revoked
        outcome = original(*args)
        if args[-1] is not None:
            revoked = True
        return outcome

    validator._run = run
    with pytest.raises(PermissionError):
        validator.validate(package, check_live=check)


def test_import_error_cannot_pass(configured):
    package, validator, _ = configured
    result = validator.validate(package, check_live=lambda: None)
    result = replace(
        result,
        output_xml=result.output_xml.replace(
            b"</robot>",
            b'<errors><msg level="ERROR">import failed</msg></errors></robot>',
        ),
    )
    result = replace(result, receipt_json=_receipt(package, result, 0))
    with pytest.raises(ValueError, match="import"):
        verify_robot_validation(package, result)


def test_source_mutation_denies_result(configured):
    package, validator, _ = configured
    original = validator._run

    def run(*args):
        outcome = original(*args)
        if args[-1] is not None:
            (args[1] / "tasks.robot").write_text("changed")
        return outcome

    validator._run = run
    with pytest.raises(ValueError):
        validator.validate(package, check_live=lambda: None)


@pytest.mark.skipif(sys.version_info[:2] != (3, 12), reason="Pinned Robot Python3.12")
def test_real_direct_dryrun_does_not_execute_task(tmp_path):
    prep = DirectRobotPreparation(Path(sys.executable))
    # Fail would fail a genuine execution; dry-run validates its import/arguments.
    req = parse_robot_backend(
        dict(
            kind="robot",
            logicalName="Robot",
            files=[
                dict(
                    path="tasks.robot",
                    content="*** Tasks ***\nSelected\n    Fail    actual execution must not happen\n",
                )
            ],
            suitePath="tasks.robot",
            suiteName="Tasks",
            taskName="Selected",
            inputSchema={"type": "object"},
            runtimeKind="direct",
        )
    )
    package = assemble_robot_admission(
        build_robot_package(req, preparation=prep), "owned-robot"
    )
    checks = []
    result = RobotValidator(tmp_path / "validation", prep).validate(
        package, check_live=lambda: checks.append(True), timeout_seconds=15
    )
    assert result.ready and result.execution == "not-qualified"
    assert len(checks) >= 3
    assert b'generator="Robot 7.4.2 ' in result.output_xml
    assert b'status="NOT RUN"' in result.output_xml
    assert verify_robot_validation(package, result) == result


@pytest.mark.skipif(sys.version_info[:2] != (3, 12), reason="Pinned Robot Python3.12")
def test_real_direct_invalid_keyword_fails_validation(tmp_path):
    prep = DirectRobotPreparation(Path(sys.executable))
    req = parse_robot_backend(
        dict(
            kind="robot",
            logicalName="Robot",
            files=[
                dict(
                    path="tasks.robot",
                    content="*** Tasks ***\nSelected\n    Keyword That Does Not Exist\n",
                )
            ],
            suitePath="tasks.robot",
            suiteName="Tasks",
            taskName="Selected",
            inputSchema={"type": "object"},
            runtimeKind="direct",
        )
    )
    package = assemble_robot_admission(
        build_robot_package(req, preparation=prep), "owned-robot"
    )
    result = RobotValidator(tmp_path / "validation", prep).validate(
        package, check_live=lambda: None, timeout_seconds=15
    )
    assert result.validation == "failed" and not result.ready
    assert result.execution == "not-qualified"


def test_validated_projection_still_does_not_claim_execution(configured):
    from uuid import uuid4

    from actions.server.deployments.ids import PackageRevisionRef
    from actions.server.foundry.robot_authoring import project_robot_evidence
    from actions.server.foundry.robot_package_admission import RobotAdmissionEvidence

    package, validator, _ = configured
    result = validator.validate(package, check_live=lambda: None)
    ref = PackageRevisionRef(
        workspace_id=str(uuid4()),
        package_id=str(uuid4()),
        revision_id=package.package_revision_id,
    )
    evidence = project_robot_evidence(RobotAdmissionEvidence(package), ref, result)
    assert evidence.ready
    assert evidence.execution == "not-qualified"
    assert evidence.public_result()["backendValidationStatus"] == "passed"
    assert not hasattr(evidence, "build_status")


@pytest.mark.skipif(sys.version_info[:2] != (3, 12), reason="Pinned Robot Python3.12")
def test_real_direct_mid_import_revocation_stops_process(tmp_path):
    import time

    prep = DirectRobotPreparation(Path(sys.executable))
    root = tmp_path / "validation"
    req = parse_robot_backend(
        dict(
            kind="robot",
            logicalName="Robot",
            files=[
                dict(
                    path="tasks.robot",
                    content="*** Settings ***\nLibrary    Slow.py\n*** Tasks ***\nSelected\n    No Operation\n",
                ),
                dict(
                    path="Slow.py",
                    content="from pathlib import Path\nimport time\nPath(__file__).with_name('started').write_text('yes')\ntime.sleep(30)\n",
                ),
            ],
            suitePath="tasks.robot",
            suiteName="Tasks",
            taskName="Selected",
            inputSchema={"type": "object"},
            runtimeKind="direct",
        )
    )
    package = assemble_robot_admission(
        build_robot_package(req, preparation=prep), "owned-robot"
    )

    def check():
        if list(root.glob("*/source/started")):
            raise PermissionError("revoked during import")

    start = time.monotonic()
    with pytest.raises(PermissionError, match="during import"):
        RobotValidator(root, prep).validate(
            package, check_live=check, timeout_seconds=10
        )
    assert time.monotonic() - start < 8
    assert list(root.glob("*/stdout.log"))


def test_oversize_diagnostic_cannot_be_retained(configured):
    from actions.server.foundry.robot_validation import LOG_LIMIT

    package, validator, _ = configured
    result = validator.validate(package, check_live=lambda: None)
    with pytest.raises(ValueError, match="bounded"):
        verify_robot_validation(package, replace(result, stdout=b"x" * (LOG_LIMIT + 1)))

pytestmark = pytest.mark.skipif(sys.platform != "linux" or platform.machine().lower() != "x86_64", reason="Pinned Robot Linux x86_64")
