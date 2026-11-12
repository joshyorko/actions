"""Real direct dry-run and retained SQL/provider boundaries; no installed claim."""
import json
import platform
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant, _registry
from action_server_tests.test_robot_package_admission import request_for

from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.deployments.foundry_values import AccessDenied
from actions.server.foundry.models import FoundryAudit, FoundryPackageRevision
from actions.server.foundry.robot_execution import DirectRobotPreparation
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux"
    or platform.machine().lower() != "x86_64"
    or sys.version_info[:2] != (3, 12),
    reason="Pinned Robot Linux x86_64/Python3.12",
)


def prepare(registry, refs, actor, request=None):
    return registry.prepare_trusted_robot(
        request or request_for(),
        logical_package_key="owned-robot",
        trusted_actor=actor,
        workspace_id=refs.workspace,
        application_id=refs.deployment_id,
        preparation=DirectRobotPreparation(Path(sys.executable)),
    )


@pytest.fixture
def host(database_location, foundry_package_store, tmp_path):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        grant = _grant(db, refs, actor)
        registry = _registry(db, foundry_package_store)
        registry = type(registry)(
            db,
            foundry_package_store,
            registry._authorization,
            executor=registry._executor,
            admission=registry._admission,
            robot_validation_root=tmp_path / "validation",
        )
        yield db, refs, actor, registry, foundry_package_store, grant


def test_real_direct_validation_restart_and_replay(host):
    db, refs, actor, registry, provider, _ = host
    ev = prepare(registry, refs, actor)
    ref = registry.admit_robot(actor, refs.workspace, ev)
    retained = registry.robot_validation_evidence(ref)
    assert retained.ready and b"NOT RUN" in retained.output_xml
    assert registry.evidence(ref).ready
    assert registry.admit_robot(actor, refs.workspace, ev) == ref
    reopened = Database(db.db_path)
    with reopened.connect():
        reopened.initialize(get_all_model_classes())
        other = _registry(reopened, provider)
        assert other.robot_validation_evidence(ref) == retained
        assert other.evidence(ref).ready
    assert len(db.all(FoundryAudit)) == 1


def test_fresh_pass_reuses_immutable_diagnostics(host):
    db, refs, actor, registry, _, _ = host
    first = prepare(registry, refs, actor)
    ref = registry.admit_robot(actor, refs.workspace, first)
    old = db.all(FoundryPackageRevision)[0].build_evidence_json
    second = prepare(registry, refs, actor)
    assert (
        registry._robot_pending[id(first)][-2].receipt_json
        != registry._robot_pending[id(second)][-2].receipt_json
    )
    assert registry.admit_robot(actor, refs.workspace, second) == ref
    assert db.all(FoundryPackageRevision)[0].build_evidence_json == old
    assert len(db.all(FoundryAudit)) == 1


def test_source_only_cannot_be_mutably_qualified(host):
    db, refs, actor, registry, _, _ = host
    root = registry._robot_validation_root
    registry._robot_validation_root = None
    ref = registry.admit_robot(actor, refs.workspace, prepare(registry, refs, actor))
    registry._robot_validation_root = root
    ev = prepare(registry, refs, actor)
    with pytest.raises(AccessDenied, match="new source"):
        registry.admit_robot(actor, refs.workspace, ev)
    assert registry.robot_validation_evidence(ref) is None
    assert not registry.evidence(ref).ready


def test_forged_admission_identity_and_changed_issued_result_denied(host):
    db, refs, actor, registry, _, _ = host
    ev = prepare(registry, refs, actor)
    with pytest.raises(AccessDenied, match="exact authorized"):
        registry.admit_robot(actor, refs.workspace, replace(ev))
    result = registry._robot_pending[id(ev)][-2]
    object.__setattr__(result, "stdout", result.stdout + b"forged")
    with pytest.raises(AccessDenied, match="issued Robot validation"):
        registry.admit_robot(actor, refs.workspace, ev)
    assert db.all(FoundryPackageRevision) == []


@pytest.mark.parametrize(
    "mutation", ["extra", "receipt", "seal", "status", "null", "source"]
)
def test_retained_validation_tamper_denied(host, mutation):
    db, refs, actor, registry, _, _ = host
    ref = registry.admit_robot(actor, refs.workspace, prepare(registry, refs, actor))
    row = db.all(FoundryPackageRevision)[0]
    data = json.loads(row.build_evidence_json)
    carrier = data["validation"]
    if mutation == "extra":
        carrier["extra"] = 1
    elif mutation == "receipt":
        carrier["receipt"] = "{}"
    elif mutation == "seal":
        carrier["stdout"]["digest"] = "sha256:" + "0" * 64
    elif mutation == "status":
        carrier["validation"] = "failed"
    elif mutation == "null":
        data["validation"] = None
    else:
        data["source"]["digest"] = "sha256:" + "0" * 64
    from actions.server.foundry.package_registry import _json

    with db.transaction():
        db.execute(
            "UPDATE foundry_package_revision SET build_evidence_json=? WHERE id=?",
            [_json(data), row.id],
        )
    with pytest.raises(AccessDenied):
        registry.robot_validation_evidence(ref)
    with pytest.raises(AccessDenied):
        registry.evidence(ref)
    with pytest.raises(AccessDenied):
        registry.load_verified(ref)


def test_audit_failure_rolls_back_all_sql_and_retry(host, monkeypatch):
    db, refs, actor, registry, _, _ = host
    ev = prepare(registry, refs, actor)
    original = db.insert

    def insert(value):
        if isinstance(value, FoundryAudit):
            raise RuntimeError("audit rejected")
        return original(value)

    with monkeypatch.context() as patch:
        patch.setattr(db, "insert", insert)
        with pytest.raises(RuntimeError, match="audit rejected"):
            registry.admit_robot(actor, refs.workspace, ev)
    assert db.all(FoundryPackageRevision) == [] and db.all(FoundryAudit) == []
    ref = registry.admit_robot(actor, refs.workspace, ev)
    assert registry.robot_validation_evidence(ref).ready


def test_live_post_validation_revocation(host):
    db, refs, actor, registry, _, grant = host
    ev = prepare(registry, refs, actor)
    with db.transaction():
        db.execute("DELETE FROM foundry_access_grant WHERE id=?", [grant.id])
    with pytest.raises(AccessDenied):
        registry.admit_robot(actor, refs.workspace, ev)
    assert db.all(FoundryPackageRevision) == []


def test_concurrent_exact_issued_admission(host):
    db, refs, actor, registry, _, _ = host
    ev = prepare(registry, refs, actor)
    barrier = Barrier(2)

    def admit(_):
        barrier.wait(timeout=15)
        return registry.admit_robot(actor, refs.workspace, ev)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(admit, range(2)))
    assert results[0] == results[1]
    assert registry.robot_validation_evidence(results[0]).ready
    assert len(db.all(FoundryPackageRevision)) == len(db.all(FoundryAudit)) == 1


def test_failed_validation_cannot_replace_passed(host, monkeypatch):
    from actions.server.foundry.robot_validation import RobotValidator, _receipt

    db, refs, actor, registry, _, _ = host
    first = prepare(registry, refs, actor)
    ref = registry.admit_robot(actor, refs.workspace, first)
    original = RobotValidator.validate

    def failed(self, package, **kwargs):
        result = original(self, package, **kwargs)
        result = replace(
            result,
            validation="failed",
            output_xml=result.output_xml.replace(b'status="PASS"', b'status="FAIL"'),
        )
        return replace(result, receipt_json=_receipt(package, result, 1))

    monkeypatch.setattr(RobotValidator, "validate", failed)
    ev = prepare(registry, refs, actor)
    with pytest.raises(AccessDenied, match="new source"):
        registry.admit_robot(actor, refs.workspace, ev)
    assert registry.robot_validation_evidence(ref).ready


def test_failed_validation_retains_unready_then_passed_denied(host, monkeypatch):
    from actions.server.foundry.robot_validation import RobotValidator, _receipt

    db, refs, actor, registry, _, _ = host
    original = RobotValidator.validate

    def failed(self, package, **kwargs):
        result = original(self, package, **kwargs)
        result = replace(
            result,
            validation="failed",
            output_xml=result.output_xml.replace(b'status="PASS"', b'status="FAIL"'),
        )
        return replace(result, receipt_json=_receipt(package, result, 1))

    with monkeypatch.context() as patch:
        patch.setattr(RobotValidator, "validate", failed)
        ev = prepare(registry, refs, actor)
    ref = registry.admit_robot(actor, refs.workspace, ev)
    assert not registry.evidence(ref).ready
    assert registry.admit_robot(actor, refs.workspace, ev) == ref
    with pytest.raises(AccessDenied, match="new source"):
        registry.admit_robot(actor, refs.workspace, prepare(registry, refs, actor))


def test_stage_provider_io_outside_sql_and_live_revocation(host, monkeypatch):
    db, refs, actor, registry, provider, grant = host
    ev = prepare(registry, refs, actor)
    original = provider.stage
    calls = []

    def stage(chunks):
        assert not db.in_transaction()
        item = original(chunks)
        calls.append(item)
        if len(calls) == 2:
            with db.transaction():
                db.execute("DELETE FROM foundry_access_grant WHERE id=?", [grant.id])
        return item

    monkeypatch.setattr(provider, "stage", stage)
    with pytest.raises(AccessDenied):
        registry.admit_robot(actor, refs.workspace, ev)
    assert len(calls) >= 2 and db.all(FoundryPackageRevision) == []


def test_validation_live_post_return_denial_issues_no_ticket(host, monkeypatch):
    from actions.server.foundry.robot_validation import RobotValidator

    db, refs, actor, registry, _, grant = host
    original = RobotValidator.validate

    def validate(self, *args, **kwargs):
        assert not db.in_transaction()
        result = original(self, *args, **kwargs)
        with db.transaction():
            db.execute("DELETE FROM foundry_access_grant WHERE id=?", [grant.id])
        return result

    monkeypatch.setattr(RobotValidator, "validate", validate)
    with pytest.raises(AccessDenied):
        prepare(registry, refs, actor)
    assert registry._robot_pending == {} and db.all(FoundryPackageRevision) == []


def test_independent_validators_concurrent_pass_preserves_one_receipt(host, tmp_path):
    db, refs, actor, registry, provider, _ = host
    barrier = Barrier(2)

    def admit(index):
        separate = Database(db.db_path)
        with separate.connect():
            separate.initialize(get_all_model_classes())
            other = _registry(separate, provider)
            other._robot_validation_root = tmp_path / str(index)
            ev = prepare(other, refs, actor)
            barrier.wait(timeout=15)
            ref = other.admit_robot(actor, refs.workspace, ev)
            return ref, other.robot_validation_evidence(ref)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(admit, range(2)))
    assert results[0] == results[1]
    assert results[0][1].ready
    assert len(db.all(FoundryPackageRevision)) == len(db.all(FoundryAudit)) == 1
