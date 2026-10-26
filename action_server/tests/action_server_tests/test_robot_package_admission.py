"""Canonical SQL/source admission; synthetic preparation is not Robot execution."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant, _registry

from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.deployments.foundry_values import AccessDenied
from actions.server.deployments.ids import CapabilityRef, PlanDigest, RuntimePlanRef
from actions.server.deployments.package_revision_compiler import (
    PreparedRccEnvironment,
    RccBuildIdentity,
)
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryPackageRevision,
)
from actions.server.foundry.robot_execution import (
    DirectRobotPreparation,
    RccRobotPreparation,
)
from actions.server.foundry.robot_package_admission import decode_robot_admission
from actions.server.foundry.robot_package_builder import RobotPackageRequest
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def request_for(kind="direct"):
    files = [
        {"path": "task.robot", "content": "*** Tasks ***\nOwned\n    No Operation\n"}
    ]
    if kind == "rcc":
        files.append({"path": "package.yaml", "content": "dependencies: {}\n"})
    return RobotPackageRequest.model_validate_json(
        json.dumps(
            {
                "kind": "robot",
                "logicalName": "Owned Robot",
                "suitePath": "task.robot",
                "suiteName": "Task",
                "taskName": "Owned",
                "inputSchema": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                    "additionalProperties": False,
                },
                "runtimeKind": kind,
                "files": files,
            }
        )
    )


@pytest.fixture
def admitted(database_location, foundry_package_store):
    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        registry = _registry(db, foundry_package_store)
        evidence = registry.prepare_trusted_robot(
            request_for(),
            logical_package_key="owned-robot",
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
            preparation=DirectRobotPreparation(Path(sys.executable)),
        )
        yield db, refs, actor, registry, evidence, foundry_package_store


def test_admission_reload_exact_refs_and_no_compilation_claim(admitted):
    db, refs, actor, registry, evidence, provider = admitted
    assert evidence.execution == "not-qualified" and not hasattr(evidence, "ready")
    ref = registry.admit_robot(actor, refs.workspace, evidence)
    assert registry.admit_robot(actor, refs.workspace, evidence) == ref
    assert len(db.all(FoundryPackageRevision)) == len(db.all(FoundryAudit)) == 1
    cap = registry.capability_refs(ref)[0]
    plan = registry.get_capability(cap).runtime_plans[0]
    selected = registry.selection_for(cap, plan)
    assert selected.robot == evidence.package
    assert registry.get_runtime_plan(plan).runtime_kind == "direct"
    assert "artifact_digest" not in json.loads(selected.robot.robot.plan_payload)
    projected = registry.evidence(ref)
    assert projected.admission_ready and not projected.ready
    assert projected.execution == "not-qualified"
    assert not hasattr(projected, "build_status")
    with pytest.raises(AccessDenied):
        registry.admit_robot(actor, refs.workspace, replace(evidence))
    reopened = Database(db.db_path)
    with reopened.connect():
        reopened.initialize(get_all_model_classes())
        other = _registry(reopened, provider)
        assert other.load_verified(ref) == evidence.package
        assert other.robot_admission_evidence(ref) == evidence
    with db.transaction():
        db.execute(
            "DELETE FROM foundry_access_grant WHERE subject_id=?",
            [reference_grant_subject(ref)],
        )
    with pytest.raises(AccessDenied):
        registry.admit_robot(actor, refs.workspace, evidence)
    assert not [
        g
        for g in db.all(FoundryAccessGrant)
        if g.subject_id == reference_grant_subject(ref)
    ]


@pytest.mark.parametrize(
    "part", ["manifest", "inventory", "source", "plan", "capability", "owner"]
)
def test_tamper_and_scope_denial(admitted, part):
    db, refs, actor, registry, evidence, provider = admitted
    ref = registry.admit_robot(actor, refs.workspace, evidence)
    cap = registry.capability_refs(ref)[0]
    plan = registry.get_capability(cap).runtime_plans[0]
    if part == "plan":
        with pytest.raises(AccessDenied):
            registry.selection_for(
                cap,
                RuntimePlanRef(
                    package_revision=ref, plan_digest=PlanDigest("sha256:" + "f" * 64)
                ),
            )
    elif part == "capability":
        with pytest.raises(AccessDenied):
            registry.selection_for(
                CapabilityRef(package_revision=ref, capability_id="robot.other"), plan
            )
    elif part == "owner":
        with pytest.raises(AccessDenied):
            registry.admit_robot(
                Actor(principal_id=str(uuid4())), refs.workspace, evidence
            )
    else:
        column = {
            "manifest": "manifest_json",
            "inventory": "source_inventory_json",
            "source": "source_artifact_digest",
        }[part]
        with db.transaction():
            db.execute(
                f"UPDATE foundry_package_revision SET {column}=? WHERE revision_id=?",
                [
                    "{}" if part != "source" else "sha256:" + "f" * 64,
                    ref.revision_id.root,
                ],
            )
        with pytest.raises(AccessDenied):
            registry.load_verified(ref)


def test_issued_evidence_cannot_change_before_admission(admitted):
    db, refs, actor, registry, evidence, provider = admitted
    object.__setattr__(
        evidence, "package", replace(evidence.package, manifest_json=b"{}")
    )
    with pytest.raises(AccessDenied):
        registry.admit_robot(actor, refs.workspace, evidence)
    assert db.all(FoundryPackageRevision) == []


def test_rcc_retains_exact_host_measurements(admitted, tmp_path):
    import hashlib

    db, refs, actor, registry, _, provider = admitted
    request = request_for("rcc")
    yaml = request.files[1].content.encode()
    env = PreparedRccEnvironment(
        robocorp_home=tmp_path,
        package_yaml_digest="sha256:" + hashlib.sha256(yaml).hexdigest(),
        build_identity=RccBuildIdentity("sha256:" + "a" * 64, "sha256:" + "b" * 64),
        rcc_version="v18.19.3",
    )
    # Synthetic typed host measurements exercise identity propagation only.
    prep = RccRobotPreparation(Path(sys.executable), env)
    ev = registry.prepare_trusted_robot(
        request,
        logical_package_key="rcc-robot",
        trusted_actor=actor,
        workspace_id=refs.workspace,
        application_id=refs.deployment_id,
        preparation=prep,
    )
    ref = registry.admit_robot(actor, refs.workspace, ev)
    loaded = registry.load_verified(ref)
    assert loaded.robot.plan.artifact_digest == env.build_identity.artifact_digest
    assert (
        loaded.robot.plan.specification_digest
        == env.build_identity.specification_digest
    )
    assert loaded.robot.plan.package_yaml_digest == env.package_yaml_digest
    with pytest.raises(ValueError):
        registry.prepare_trusted_robot(
            request,
            logical_package_key="wrong",
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
            preparation=DirectRobotPreparation(Path(sys.executable)),
        )


def test_outer_transaction_cannot_acknowledge_admission(admitted):
    db, refs, actor, registry, evidence, provider = admitted
    with db.transaction():
        with pytest.raises(AccessDenied):
            registry.admit_robot(actor, refs.workspace, evidence)
    assert db.all(FoundryPackageRevision) == []
    assert registry.admit_robot(actor, refs.workspace, evidence)


def test_audit_failure_rolls_back_admission_and_replay_is_safe(admitted, monkeypatch):
    db, refs, actor, registry, evidence, provider = admitted
    original = db.insert

    def fail_audit(value):
        if isinstance(value, FoundryAudit):
            raise RuntimeError("synthetic audit failure")
        return original(value)

    with monkeypatch.context() as patch:
        patch.setattr(db, "insert", fail_audit)
        with pytest.raises(RuntimeError, match="synthetic"):
            registry.admit_robot(actor, refs.workspace, evidence)
    assert db.all(FoundryPackageRevision) == []
    assert db.all(FoundryAudit) == []
    ref = registry.admit_robot(actor, refs.workspace, evidence)
    assert registry.load_verified(ref) == evidence.package
    assert len(db.all(FoundryAudit)) == 1


def test_independent_connections_concurrent_admission_is_idempotent(admitted):
    db, refs, actor, registry, evidence, provider = admitted
    barrier = Barrier(2)

    def admit_one(_):
        other_db = Database(db.db_path)
        with other_db.connect():
            other_db.initialize(get_all_model_classes())
            other = _registry(other_db, provider)
            ev = other.prepare_trusted_robot(
                request_for(),
                logical_package_key="owned-robot",
                trusted_actor=actor,
                workspace_id=refs.workspace,
                application_id=refs.deployment_id,
                preparation=DirectRobotPreparation(Path(sys.executable)),
            )
            barrier.wait(timeout=15)
            return other.admit_robot(actor, refs.workspace, ev)

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(admit_one, range(2)))
    assert result[0] == result[1]
    assert len(db.all(FoundryPackageRevision)) == len(db.all(FoundryAudit)) == 1
    assert registry.load_verified(result[0]) == evidence.package


@pytest.mark.parametrize("plan", [None, [], {"runtime_kind": "unknown"}])
def test_closed_retained_plan_rejects_invalid_carrier(admitted, plan):
    db, refs, actor, registry, evidence, provider = admitted
    from actions.server.foundry.robot_package_admission import canonical

    value = json.loads(evidence.package.manifest_json)
    value["plan"] = json.dumps(plan)
    with pytest.raises(ValueError):
        decode_robot_admission(canonical(value), evidence.package.source_archive)
