"""Draft schema tests for the portable Package Revision fixture boundary."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DESIGN_DIR = REPOSITORY_ROOT / "docs" / "design"
FIXTURE_DIR = DESIGN_DIR / "fixtures" / "package-revision-v1"
PACKAGE_SCHEMA = DESIGN_DIR / "package-revision-v1.schema.json"
REFERENCE_SCHEMA = DESIGN_DIR / "package-revision-references-v1.schema.json"
PORTABLE_FIXTURE = FIXTURE_DIR / "portable-rcc.json"
REFERENCE_FIXTURE = FIXTURE_DIR / "consumer-refs.json"
PORTABLE_FIXTURE_SHA256 = (
    "5c972f561d46999dcc2bd9cce46e3adf27ae9aa949a943320a1eab7d104865e4"
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_portable_package_revision_schema_accepts_fixture() -> None:
    schema = _read_json(PACKAGE_SCHEMA)
    fixture = _read_json(PORTABLE_FIXTURE)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(fixture)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["identity"].update(workspaceId="ws-production"),
        lambda value: value["identity"].update(deploymentId="deployment-prod"),
        lambda value: value["logicalBindingRequirements"][0].update(
            value="secret-value"
        ),
        lambda value: value["sourceArtifact"].update(localPath="/srv/actions/package"),
        lambda value: value.update(
            defaultRuntimePlanDigest="sha256:5555555555555555555555555555555555555555555555555555555555555555"
        ),
        lambda value: value["runtimePlans"][0]["requiredFeatures"].append("task.exec"),
    ],
    ids=(
        "workspace-reference",
        "deployment-reference",
        "binding-value",
        "host-path",
        "deployment-selection",
        "duplicate-plan-feature",
    ),
)
def test_portable_package_revision_schema_rejects_installation_state(mutation) -> None:
    schema = _read_json(PACKAGE_SCHEMA)
    fixture = copy.deepcopy(_read_json(PORTABLE_FIXTURE))
    mutation(fixture)

    assert not Draft202012Validator(schema).is_valid(fixture)


def test_reference_schema_requires_workspace_and_full_package_plan_identity() -> None:
    schema = _read_json(REFERENCE_SCHEMA)
    fixture = _read_json(REFERENCE_FIXTURE)

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(fixture)

    missing_workspace = copy.deepcopy(fixture)
    del missing_workspace["runtimePlanRef"]["packageRevisionRef"]["workspaceId"]
    assert not validator.is_valid(missing_workspace)

    missing_package_owner = copy.deepcopy(fixture)
    del missing_package_owner["runtimePlanRef"]["packageRevisionRef"]
    assert not validator.is_valid(missing_package_owner)


def test_reference_schema_has_one_authoritative_package_owner() -> None:
    schema = _read_json(REFERENCE_SCHEMA)
    fixture = _read_json(REFERENCE_FIXTURE)

    assert set(fixture) == {"runtimePlanRef"}
    Draft202012Validator(schema).validate(fixture)


@pytest.mark.parametrize(
    ("field", "other_identity"),
    [
        ("workspaceId", "workspace-other"),
        ("packageId", "other-package"),
        ("revisionDigest", "sha256:" + "9" * 64),
    ],
)
def test_reference_schema_rejects_contradictory_outer_package_owner(
    field, other_identity
) -> None:
    fixture = _read_json(REFERENCE_FIXTURE)
    owner = fixture["runtimePlanRef"]["packageRevisionRef"]
    fixture["packageRevisionRef"] = {**owner, field: other_identity}

    assert not Draft202012Validator(_read_json(REFERENCE_SCHEMA)).is_valid(fixture)


def test_reference_schema_rejects_even_a_matching_outer_package_owner() -> None:
    fixture = _read_json(REFERENCE_FIXTURE)
    fixture["packageRevisionRef"] = copy.deepcopy(
        fixture["runtimePlanRef"]["packageRevisionRef"]
    )

    assert not Draft202012Validator(_read_json(REFERENCE_SCHEMA)).is_valid(fixture)


@pytest.mark.parametrize("schema_path", [PACKAGE_SCHEMA, REFERENCE_SCHEMA])
@pytest.mark.parametrize("version", [1, 2])
def test_plan_schema_version_accepts_positive_integers(schema_path, version) -> None:
    fixture_path = (
        PORTABLE_FIXTURE if schema_path == PACKAGE_SCHEMA else REFERENCE_FIXTURE
    )
    fixture = _read_json(fixture_path)
    plan = (
        fixture["runtimePlans"][0]
        if schema_path == PACKAGE_SCHEMA
        else fixture["runtimePlanRef"]
    )
    field = "schemaVersion" if schema_path == PACKAGE_SCHEMA else "planSchemaVersion"
    plan[field] = version

    Draft202012Validator(_read_json(schema_path)).validate(fixture)


@pytest.mark.parametrize("schema_path", [PACKAGE_SCHEMA, REFERENCE_SCHEMA])
@pytest.mark.parametrize(
    "version", ["actions.runtime-plan/v1-draft", "1", 0, -1, True, 1.5, None]
)
def test_plan_schema_version_rejects_non_positive_integer_values(
    schema_path, version
) -> None:
    fixture_path = (
        PORTABLE_FIXTURE if schema_path == PACKAGE_SCHEMA else REFERENCE_FIXTURE
    )
    fixture = _read_json(fixture_path)
    plan = (
        fixture["runtimePlans"][0]
        if schema_path == PACKAGE_SCHEMA
        else fixture["runtimePlanRef"]
    )
    field = "schemaVersion" if schema_path == PACKAGE_SCHEMA else "planSchemaVersion"
    plan[field] = version

    assert not Draft202012Validator(_read_json(schema_path)).is_valid(fixture)


def test_portable_fixture_is_stably_serialized() -> None:
    raw = PORTABLE_FIXTURE.read_bytes()
    fixture = json.loads(raw)
    canonical = (
        json.dumps(fixture, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    assert raw == canonical
    assert hashlib.sha256(raw).hexdigest() == PORTABLE_FIXTURE_SHA256


def test_consumer_reference_fixture_is_stably_serialized() -> None:
    raw = REFERENCE_FIXTURE.read_bytes()
    fixture = json.loads(raw)
    canonical = (
        json.dumps(fixture, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    assert raw == canonical
