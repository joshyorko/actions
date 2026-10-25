import json
import sys
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from actions.server.deployments.ids import DeploymentId, PackageRevisionRef, WorkspaceId
from actions.server.foundry.authoring_values import (
    AuthoringAccessDenied,
    AuthoringError,
    AuthoringValidationError,
)
from actions.server.foundry.mcp import CanvasCaller
from actions.server.foundry.robot_authoring import (
    RobotAuthoringAdapter,
    parse_robot_backend,
    project_robot_evidence,
    robot_backend_schema,
)
from actions.server.foundry.robot_execution import DirectRobotPreparation
from actions.server.foundry.robot_package_admission import (
    RobotAdmissionEvidence,
    assemble_robot_admission,
)
from actions.server.foundry.robot_package_builder import build_robot_package
from actions.server.run_outputs.types import Actor
from jsonschema import Draft202012Validator


def request(**updates):
    value = dict(
        kind="robot",
        logicalName="Robot",
        files=[
            dict(
                path="tasks.robot",
                content="*** Tasks ***\nSelected\n    No Operation\n",
            )
        ],
        suitePath="tasks.robot",
        suiteName="Tasks",
        taskName="Selected",
        inputSchema={"type": "object"},
        runtimeKind="direct",
    )
    value.update(updates)
    return value


class Authorization:
    def __init__(self, deny=None):
        self.operations = []
        self.deny = deny

    def require(self, caller, operation, **kwargs):
        self.operations.append(operation)
        if operation == self.deny:
            raise AuthoringAccessDenied("denied")


class Registry:
    def __init__(self):
        self.calls = []

    def prepare_trusted_robot(self, request, **kwargs):
        self.calls.append("prepare")
        self.kwargs = kwargs
        self.evidence = RobotAdmissionEvidence(
            assemble_robot_admission(
                build_robot_package(request, preparation=kwargs["preparation"]),
                kwargs["logical_package_key"],
            )
        )
        return self.evidence

    def admit_robot(self, actor, workspace, evidence):
        self.calls.append("admit")
        assert evidence is self.evidence
        return PackageRevisionRef(
            workspace_id=workspace,
            package_id=str(uuid4()),
            revision_id=evidence.package.package_revision_id,
        )

    def robot_validation_evidence(self, ref):
        return None

    def robot_admission_evidence(self, ref):
        self.calls.append("reload")
        return self.evidence


@pytest.fixture
def configured():
    registry, auth = Registry(), Authorization()
    caller = CanvasCaller(Actor(principal_id=str(uuid4())), str(uuid4()), "model")
    app = DeploymentId.model_validate(str(uuid4()))
    prep = DirectRobotPreparation(Path(sys.executable))
    adapter = RobotAuthoringAdapter(registry, auth, direct=prep)
    return registry, auth, caller, app, adapter


def test_admit_retains_honest_path_free_evidence(configured):
    registry, auth, caller, app, adapter = configured
    result = adapter.prepare_and_admit(
        parse_robot_backend(request()), caller=caller, application_id=app
    )
    assert registry.calls == ["prepare", "admit", "reload"]
    assert auth.operations == ["apply_revision", "execute_generated_source"]
    assert registry.kwargs["logical_package_key"] == "canvas-" + str(app.root)
    assert result.evidence.package_revision_id == result.package_revision.revision_id
    assert result.evidence.admission_ready and not result.evidence.ready
    assert result.evidence.public_result() == dict(
        backendKind="robot",
        runtimeKind="direct",
        admissionVerification="source-and-plan-verified",
        executionQualification="not-qualified",
        validationKind=None,
        backendValidationStatus="not-run",
    )
    assert not hasattr(result.evidence, "build_status")
    assert b"artifact_digest" not in registry.evidence.package.robot.plan_payload


@pytest.mark.parametrize("denied", ["apply_revision", "execute_generated_source"])
def test_authorization_precedes_registry_io(configured, denied):
    registry, auth, caller, app, adapter = configured
    auth.deny = denied
    with pytest.raises(AuthoringAccessDenied):
        adapter.prepare_and_admit(
            parse_robot_backend(request()), caller=caller, application_id=app
        )
    assert registry.calls == []


def test_unconfigured_rcc_never_falls_back(configured):
    registry, auth, caller, app, adapter = configured
    with pytest.raises(AuthoringAccessDenied, match="not configured"):
        adapter.prepare_and_admit(
            parse_robot_backend(request(runtimeKind="rcc")),
            caller=caller,
            application_id=app,
        )
    assert registry.calls == []


@pytest.mark.parametrize(
    "extra",
    [
        "python",
        "rcc",
        "preparation",
        "artifact_digest",
        "actor",
        "workspace",
        "execution",
        "buildStatus",
    ],
)
def test_request_rejects_authority_fields(extra):
    with pytest.raises(AuthoringValidationError):
        parse_robot_backend(request(**{extra: "untrusted"}))


def test_schema_is_closed_and_nesting_safe():
    schema = robot_backend_schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(
        {"type": "object", "properties": {"backend": schema}}
    )
    validator.validate({"backend": request()})
    assert not validator.is_valid({"backend": request(preparation={})})
    assert "#/$defs/" not in json.dumps(schema)


def test_tampered_retained_evidence_rejected(configured):
    registry, auth, caller, app, adapter = configured
    original = registry.robot_admission_evidence
    registry.robot_admission_evidence = lambda ref: replace(
        original(ref), execution="passed"
    )
    with pytest.raises(AuthoringError, match="Retained"):
        adapter.prepare_and_admit(
            parse_robot_backend(request()), caller=caller, application_id=app
        )


def test_wrong_revision_rejected(configured):
    registry, auth, caller, app, adapter = configured
    result = adapter.prepare_and_admit(
        parse_robot_backend(request()), caller=caller, application_id=app
    )
    other = result.package_revision.model_copy(
        update={
            "revision_id": type(result.package_revision.revision_id).model_validate(
                "sha256:" + "f" * 64
            )
        }
    )
    with pytest.raises(AuthoringError):
        project_robot_evidence(registry.evidence, other)


def test_app_audience_rejected_before_registry(configured):
    registry, auth, caller, app, adapter = configured
    caller = replace(caller, audience="app")
    with pytest.raises(AuthoringAccessDenied, match="model audience"):
        adapter.prepare_and_admit(
            parse_robot_backend(request()), caller=caller, application_id=app
        )
    assert registry.calls == []
    assert auth.operations == []


def test_wrong_workspace_rejected(configured):
    registry, auth, caller, app, adapter = configured
    original = registry.admit_robot
    registry.admit_robot = lambda actor, workspace, evidence: original(
        actor, WorkspaceId.model_validate(str(uuid4())), evidence
    )
    with pytest.raises(AuthoringError, match="Workspace"):
        adapter.prepare_and_admit(
            parse_robot_backend(request()), caller=caller, application_id=app
        )
    assert registry.calls == ["prepare", "admit"]
