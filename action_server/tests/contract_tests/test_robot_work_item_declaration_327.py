"""Immutable Robot Work Item declarations; no worker/queue execution authority."""
# Imported fixtures are injected by pytest.
# ruff: noqa: F811
import json
import sys
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from action_server_tests.foundry_fixtures import foundry_package_store
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant, _registry

from actions.server.deployments.foundry_values import WorkItemDeclaration
from actions.server.foundry import robot_package_builder as builder
from actions.server.foundry.robot_execution import DirectRobotPreparation
from actions.server.foundry.robot_package_admission import (
    SCHEMA,
    assemble_robot_admission,
    canonical,
    decode_robot_admission,
    digest,
)
from actions.server.run_outputs.types import Actor

ISOLATED = Path(__file__).resolve().parents[2] / "src"
assert (
    Path(builder.__file__).resolve().is_relative_to(ISOLATED)
), "isolated Runtime origin required"


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    # Pure metadata/SQLite tests neither launch nor configure RCC.
    yield


def request(**updates):
    value = dict(
        kind="robot",
        logicalName="Declaration Robot",
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
    return builder.RobotPackageRequest.model_validate_json(json.dumps(value))


def build(**updates):
    return builder.build_robot_package(
        request(**updates), preparation=DirectRobotPreparation(Path(sys.executable))
    )


def test_default_none_preserves_exact_legacy_manifest_and_revision():
    package = build()
    explicit = build(workItems={"mode": "none", "allow_outputs": False})
    assert package == explicit
    assert package.work_items == WorkItemDeclaration()
    legacy = {
        "kind": "robot",
        "logicalName": package.logical_name,
        "sourceInventoryDigest": package.source.digest,
        "sourceDigest": package.source_digest,
        "suitePath": package.suite_path,
        "suiteName": package.suite_name,
        "taskName": package.task_name,
        "inputSchemaDigest": digest(package.input_schema),
        "outputSchemaDigest": digest(package.output_schema),
        "planDigest": package.plan_digest,
        "discriminator": package.plan.discriminator,
    }
    assert package.manifest == builder._json(legacy)
    assert "workItems" not in json.loads(package.manifest)
    admitted = assemble_robot_admission(package, "declaration-robot")
    unsigned = dict(
        schemaVersion=SCHEMA,
        identity=dict(packageId="declaration-robot", logicalName=package.logical_name),
        capabilityId="robot.task",
        robotManifest=package.manifest.decode(),
        inputSchema=package.input_schema.decode(),
        outputSchema=package.output_schema.decode(),
        plan=package.plan_payload.decode(),
    )
    expected_revision = digest(canonical([SCHEMA, unsigned]))
    assert admitted.package_revision_id.root == expected_revision
    assert admitted.manifest_json == canonical(
        dict(unsigned, revisionDigest=expected_revision)
    )


@pytest.mark.parametrize("mode", ["optional", "required-input", "consumer"])
def test_supported_input_modes_are_measured_and_round_trip(mode):
    package = build(workItems={"mode": mode, "allow_outputs": False})
    assert package.work_items == WorkItemDeclaration(mode=mode)
    assert json.loads(package.manifest)["workItems"] == {
        "mode": mode,
        "allow_outputs": False,
    }
    assert package.package_digest != build().package_digest
    assert (
        builder.verify_robot_package(
            package, preparation=DirectRobotPreparation(Path(sys.executable))
        )
        == package
    )
    admitted = assemble_robot_admission(package, "declaration-robot")
    decoded = decode_robot_admission(admitted.manifest_json, package.source_archive)
    assert decoded == admitted
    assert decoded.robot.work_items == package.work_items


@pytest.mark.parametrize(
    "declaration",
    [
        {"mode": "producer", "allow_outputs": True},
        {"mode": "producer", "allow_outputs": False},
        {"mode": "optional", "allow_outputs": True},
        {"mode": "required-input", "allow_outputs": True},
        {"mode": "consumer", "allow_outputs": True},
        {"mode": "none", "allow_outputs": True},
        {"mode": "unknown", "allow_outputs": False},
        {"mode": "consumer", "allow_outputs": "false"},
        {"mode": "consumer", "allow_outputs": False, "queue": "untrusted"},
    ],
)
def test_outputs_unknown_modes_and_untrusted_fields_rejected(declaration):
    with pytest.raises(ValueError):
        build(workItems=declaration)


def test_forged_verified_declaration_cannot_override_measured_manifest():
    package = build(workItems={"mode": "consumer", "allow_outputs": False})
    forged = replace(package, work_items=WorkItemDeclaration(mode="optional"))
    with pytest.raises(ValueError):
        builder.verify_robot_package(
            forged, preparation=DirectRobotPreparation(Path(sys.executable))
        )


@pytest.mark.parametrize(
    "replacement",
    [
        None,
        {"mode": "optional", "allow_outputs": False},
        {"mode": "consumer", "allow_outputs": True},
    ],
)
def test_declaration_tamper_without_revision_change_rejected(replacement):
    package = build(workItems={"mode": "consumer", "allow_outputs": False})
    admitted = assemble_robot_admission(package, "declaration-robot")
    outer = json.loads(admitted.manifest_json)
    inner = json.loads(outer["robotManifest"])
    if replacement is None:
        del inner["workItems"]
    else:
        inner["workItems"] = replacement
    outer["robotManifest"] = builder._json(inner).decode()
    with pytest.raises(ValueError):
        decode_robot_admission(canonical(outer), package.source_archive)


@pytest.mark.parametrize("mode", ["none", "optional", "required-input", "consumer"])
def test_sqlite_registry_projection_preserves_declaration(
    tmp_path, foundry_package_store, mode
):
    # Explicit SQLite path: never use the parametrized PostgreSQL fixture.
    assert Path(builder.__file__).resolve().is_relative_to(ISOLATED)
    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    with _runtime_database(tmp_path / "declaration.db", refs.workspace, ()) as db:
        _grant(db, refs, actor)
        registry = _registry(db, foundry_package_store)
        evidence = registry.prepare_trusted_robot(
            request(workItems={"mode": mode, "allow_outputs": False}),
            logical_package_key="declaration-robot",
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
            preparation=DirectRobotPreparation(Path(sys.executable)),
        )
        ref = registry.admit_robot(actor, refs.workspace, evidence)
        capability = registry.capability_refs(ref)[0]
        declaration = registry.get_capability(capability)
        assert declaration.work_items == WorkItemDeclaration(mode=mode)
        assert registry.load_verified(ref).robot.work_items == declaration.work_items
