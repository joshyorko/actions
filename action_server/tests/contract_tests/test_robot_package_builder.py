"""Pure package evidence only, not authorized registry admission."""
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from actions.server.deployments.package_revision_compiler import (
    PreparedRccEnvironment,
    RccBuildIdentity,
)
from actions.server.foundry.robot_execution import (
    DirectRobotPreparation,
    RccRobotPreparation,
)
from actions.server.foundry.robot_package_builder import (
    DirectRobotPlan,
    RobotPackageRequest,
    build_robot_package,
    verify_robot_package,
)


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
    return RobotPackageRequest.model_validate_json(json.dumps(value))


def test_deterministic_measured_direct_package():
    prep = DirectRobotPreparation(Path(sys.executable))
    req = request()
    value = build_robot_package(req, preparation=prep)
    assert value == verify_robot_package(value, preparation=prep)
    assert type(value.plan) is DirectRobotPlan
    assert b"artifact_digest" not in value.plan_payload
    assert b"python" not in value.manifest
    req.input_schema["additionalProperties"] = False
    assert value.input_schema == b'{"type":"object"}'
    validator = Draft202012Validator(json.loads(value.output_schema))
    validator.validate(dict(suite="Tasks", task="Selected", status="PASS"))
    assert not validator.is_valid(
        dict(suite="Tasks", task="Selected", status="PASS", extra=True)
    )
    assert not validator.is_valid(dict(suite="Tasks", task="Other", status="PASS"))
    with pytest.raises(ValueError):
        verify_robot_package(replace(value, task_name="Other"), preparation=prep)
    with pytest.raises(ValueError):
        verify_robot_package(
            replace(value, source_archive=b"changed"), preparation=prep
        )


@pytest.mark.parametrize(
    "field",
    [
        "Actor",
        "workspace",
        "Run",
        "fence",
        "provider",
        "credentials",
        "RobotSelection",
        "preparation",
    ],
)
def test_request_rejects_authority_fields(field):
    with pytest.raises(ValidationError):
        request(**{field: {}})


@pytest.mark.parametrize(
    "path", ["../tasks.robot", "/tasks.robot", "missing.robot", "tasks.py"]
)
def test_invalid_suite_rejected(path):
    with pytest.raises(ValueError):
        build_robot_package(
            request(suitePath=path),
            preparation=DirectRobotPreparation(Path(sys.executable)),
        )


def test_external_schema_rejected():
    with pytest.raises(ValueError):
        build_robot_package(
            request(inputSchema={"$ref": "https://example.org/schema"}),
            preparation=DirectRobotPreparation(Path(sys.executable)),
        )


def test_rcc_requires_exact_retained_package(tmp_path):
    import hashlib

    content = "dependencies:\n  conda-forge: [python=3.12.15]\n"
    digest = "sha256:" + hashlib.sha256(content.encode()).hexdigest()
    prep = RccRobotPreparation(
        Path(sys.executable),
        PreparedRccEnvironment(
            tmp_path,
            digest,
            RccBuildIdentity("sha256:" + "1" * 64, "sha256:" + "2" * 64),
        ),
    )
    req = request(
        runtimeKind="rcc",
        files=[
            dict(
                path="tasks.robot",
                content="*** Tasks ***\nSelected\n    No Operation\n",
            ),
            dict(path="package.yaml", content=content),
        ],
    )
    result = build_robot_package(req, preparation=prep)
    assert (
        result.plan.artifact_digest == prep.environment.build_identity.artifact_digest
    )
    assert verify_robot_package(result, preparation=prep) == result
    with pytest.raises(ValueError):
        build_robot_package(request(runtimeKind="rcc"), preparation=prep)
    with pytest.raises(ValueError):
        build_robot_package(
            req, preparation=DirectRobotPreparation(Path(sys.executable))
        )
    with pytest.raises(ValueError):
        build_robot_package(request(), preparation=prep)
