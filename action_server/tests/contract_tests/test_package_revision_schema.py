"""Draft schema tests for the portable Package Revision fixture boundary."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

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
    "ef95aa3a88433917fd6aa73d519a4e86d6c9b59201d1d50976188b80a69bc5f4"
)


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


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
    del missing_workspace["packageRevisionRef"]["workspaceId"]
    assert not validator.is_valid(missing_workspace)

    missing_package_owner = copy.deepcopy(fixture)
    del missing_package_owner["runtimePlanRef"]["packageRevisionRef"]
    assert not validator.is_valid(missing_package_owner)


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
