"""Tests for the bounded deployment identity values and canonical JSON contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from actions.server.deployments.canonical import (
    CanonicalJSONError,
    canonicalize_json,
    parse_canonical_json,
)
from actions.server.deployments.ids import (
    BindingRequirementRef,
    CapabilityId,
    CapabilityRef,
    DeploymentRevisionRef,
    PackageRevisionRef,
    PlanDigest,
    RuntimePlanRef,
    WorkspaceId,
    require_package_scope,
    require_workspace_scope,
)


FIXTURES = Path(__file__).parent / "fixtures" / "deployments"


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        (b'{"z":1,"a":"e\\u0301"}', '{"a":"\u00e9","z":1}'),
        (b'{"items":[3,2,1],"ok":true}', '{"items":[3,2,1],"ok":true}'),
        (
            b"[333333333.33333329,4.50,2e-3,1e-27]",
            "[333333333.3333333,4.5,0.002,1e-27]",
        ),
        (b"-0", "0"),
        (b"9007199254740991", "9007199254740991"),
        (b"-9007199254740991", "-9007199254740991"),
    ],
)
def test_canonical_json_exact_bytes(raw: bytes, canonical: str) -> None:
    expected = canonical.encode("utf-8")
    assert canonicalize_json(raw) == expected
    assert canonicalize_json(raw) == canonicalize_json(raw)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":1,"x":2}',
        '{"é":1,"e\u0301":2}'.encode(),
        b"\xff",
        b'"\\ud800"',
        b"NaN",
        b"Infinity",
        b"-Infinity",
        b"1e309",
        b"1e-4000",
        b"9007199254740992",
        b"1e30",
        b"1e21",
        b"9007199254740993.0",
        b"900719925474099300e-2",
        b"-9007199254740992e0",
    ],
)
def test_rejects_values_outside_canonical_domain_without_echo(raw: bytes) -> None:
    with pytest.raises(CanonicalJSONError) as error:
        canonicalize_json(raw)
    assert raw.decode("utf-8", errors="replace") not in str(error.value)


def test_rfc8785_direct_vector_is_separate_from_restricted_input_domain() -> None:
    import rfc8785

    value = [333333333.3333333, 1e30, 4.5, 0.002, 1e-27]
    assert rfc8785.dumps(value) == b"[333333333.3333333,1e+30,4.5,0.002,1e-27]"


def test_rfc8785_sorts_object_keys_by_utf16_code_units() -> None:
    raw = '{"\uE000":1,"\U00010000":2}'.encode("utf-8")
    assert canonicalize_json(raw) == '{"𐀀":2,"":1}'.encode("utf-8")


def test_parse_returns_normalized_value_and_golden_vector_file_is_fixed() -> None:
    vector = json.loads((FIXTURES / "canonical-json-v1.json").read_text())
    for item in vector["vectors"]:
        raw = item["input"].encode("utf-8")
        actual = canonicalize_json(raw)
        assert actual.decode("utf-8") == item["canonical"]
        assert parse_canonical_json(raw) == json.loads(item["canonical"])


def test_canonical_bytes_are_stable_in_a_fresh_process(tmp_path: Path) -> None:
    raw = b'{"nested":{"z":0,"a":"e\\u0301"},"array":[2,1]}'
    expected = canonicalize_json(raw)
    env = os.environ.copy()
    source = str(Path(__file__).parents[2] / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (source, env.get("PYTHONPATH", "")) if part
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from actions.server.deployments.canonical import canonicalize_json; import sys; sys.stdout.buffer.write(canonicalize_json(sys.stdin.buffer.read()))",
        ],
        input=raw,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
        env=env,
        check=True,
    )
    assert result.stdout == expected


def test_strict_reference_types_and_scope_checks() -> None:
    workspace = "123e4567-e89b-12d3-a456-426614174000"
    package = "123e4567-e89b-12d3-a456-426614174001"
    deployment = "123e4567-e89b-12d3-a456-426614174002"
    revision = "sha256:" + "a" * 64
    package_ref = PackageRevisionRef(
        workspace_id=workspace, package_id=package, revision_id=revision
    )
    plan = RuntimePlanRef(package_revision=package_ref, plan_digest=revision)
    assert require_package_scope(plan, package_ref) == plan
    assert require_workspace_scope(plan, WorkspaceId(workspace)) == plan
    assert type(plan.plan_digest) is PlanDigest
    assert type(package_ref.revision_id) is not PlanDigest

    malformed_workspace = WorkspaceId.model_copy(
        WorkspaceId(workspace), update={"root": "not-a-uuid"}
    )
    with pytest.raises(ValidationError):
        WorkspaceId.model_validate(malformed_workspace)
    malformed_package = PackageRevisionRef.model_copy(
        package_ref,
        update={"revision_id": PlanDigest(revision)},
    )
    with pytest.raises(ValidationError):
        PackageRevisionRef.model_validate(malformed_package)
    with pytest.raises(ValidationError):
        RuntimePlanRef(package_revision=malformed_package, plan_digest=revision)
    malformed_digest = PlanDigest.model_copy(
        PlanDigest(revision), update={"root": "sha256:not-a-digest"}
    )
    malformed_plan = RuntimePlanRef.model_copy(
        plan, update={"plan_digest": malformed_digest}
    )
    with pytest.raises(ValidationError):
        RuntimePlanRef.model_validate(malformed_plan)
    with pytest.raises(ValidationError):
        require_package_scope(malformed_plan, package_ref)
    with pytest.raises(ValidationError):
        require_workspace_scope(malformed_plan, WorkspaceId(workspace))
    malformed_context = PackageRevisionRef.model_copy(
        package_ref,
        update={"revision_id": PlanDigest(revision)},
    )
    with pytest.raises(ValidationError):
        require_package_scope(plan, malformed_context)
    malformed_workspace_context = WorkspaceId.model_copy(
        WorkspaceId(workspace), update={"root": "not-a-uuid"}
    )
    with pytest.raises(ValidationError):
        require_workspace_scope(plan, malformed_workspace_context)
    with pytest.raises(ValidationError):
        RuntimePlanRef.model_validate({**plan.model_dump(), "extra": True})
    with pytest.raises(ValidationError):
        RuntimePlanRef(
            package_revision=package_ref, plan_digest=package_ref.revision_id
        )
    with pytest.raises(ValidationError):
        package_ref.workspace_id = WorkspaceId(deployment)  # type: ignore[misc]
    with pytest.raises(ValidationError):
        PackageRevisionRef(
            workspace_id=workspace.upper(), package_id=package, revision_id=revision
        )
    with pytest.raises(ValidationError):
        PackageRevisionRef(workspace_id=7, package_id=package, revision_id=revision)
    with pytest.raises(ValidationError):
        PackageRevisionRef(
            workspace_id=workspace,
            package_id=package,
            revision_id="SHA256:" + "a" * 64,
        )
    with pytest.raises(ValidationError):
        RuntimePlanRef.model_validate(
            {
                **plan.model_dump(),
                "workspace_id": workspace,
                "package_id": package,
            }
        )
    other_package = PackageRevisionRef(
        workspace_id=workspace,
        package_id=deployment,
        revision_id=revision,
    )
    with pytest.raises(ValueError):
        require_package_scope(plan, other_package)
    with pytest.raises(ValueError):
        require_workspace_scope(plan, WorkspaceId(deployment))
    capability = CapabilityRef(package_revision=package_ref, capability_id="read")
    assert require_workspace_scope(capability, WorkspaceId(workspace)) == capability
    assert require_package_scope(capability, package_ref) == capability
    requirement = BindingRequirementRef(
        package_revision=package_ref, requirement_id="provider.main"
    )
    assert require_package_scope(requirement, package_ref) == requirement
    with pytest.raises(ValidationError):
        CapabilityRef(package_revision=package_ref, capability_id="e\u0301")
    with pytest.raises(ValidationError):
        CapabilityId("")
    with pytest.raises(TypeError):
        require_package_scope(plan, package)
    with pytest.raises(TypeError):
        require_package_scope(plan.model_dump(), package_ref)  # type: ignore[arg-type]


def test_deployment_reference_has_only_explicit_typed_fields() -> None:
    ref = DeploymentRevisionRef(
        workspace_id="123e4567-e89b-12d3-a456-426614174000",
        deployment_id="123e4567-e89b-12d3-a456-426614174002",
        revision_id="sha256:" + "b" * 64,
    )
    assert set(ref.model_dump()) == {"workspace_id", "deployment_id", "revision_id"}
    with pytest.raises(ValidationError):
        DeploymentRevisionRef.model_validate(
            {**ref.model_dump(), "workspace_id": "not-a-uuid"}
        )
