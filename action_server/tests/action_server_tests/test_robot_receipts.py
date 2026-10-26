# Imported pytest fixtures are resolved through their original dependencies.
# ruff: noqa: F811
"""Synthetic Robot adapter, real SQL/provider seals; no Robot process launch."""
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from action_server_tests.test_robot_package_admission import admitted as admitted
from action_server_tests.test_robot_package_admission import (
    disable_feedback as disable_feedback,
)
from action_server_tests.test_robot_runtime_runner import case as case

from actions.server._models import Run
from actions.server.foundry.models import FoundryPackageRevision
from actions.server.foundry.robot_receipts import (
    robot_output_names,
    validate_robot_record,
)
from actions.server.foundry.robot_retained_projection import (
    retained_robot_projection,
    robot_projection_if_present,
)
from actions.server.run_outputs.models import (
    RunAdmission,
    RunAttempt,
    RunOutput,
    RunPin,
)
from actions.server.run_outputs.service import FenceRejected, _one

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def completed(case):
    c = case
    c.run = c.runner.execute(c.caller, c.ticket, c.service)
    c.outer = json.loads(c.run.result)
    return c


def validate(c, *, terminal=True, allow_expired=False):
    run = _one(c.db, Run, c.ticket.fence.run_id)
    outer = json.loads(run.result)
    return validate_robot_record(
        c.db,
        c.registry,
        c.service.snapshot,
        run,
        c.ticket.fence,
        outer["result"] if terminal else outer,
        claim=None,
        terminal=terminal,
        outputs=outer.get("outputs") if terminal else None,
        _allow_expired_terminal=allow_expired,
    )


def change_record(c, change, *, terminal=True):
    run = _one(c.db, Run, c.ticket.fence.run_id)
    outer = json.loads(run.result)
    change(outer["result"] if terminal else outer)
    with c.db.transaction():
        c.db.update_by_id(Run, run.id, {"result": json.dumps(outer)})


def trap(*args, **kwargs):
    raise AssertionError("provider/registry read inside metadata validation")


def test_terminal_and_projection_use_sql_only(completed, monkeypatch):
    c = completed
    monkeypatch.setattr(c.registry, "selection_for", trap)
    monkeypatch.setattr(c.registry, "get_capability", trap)
    monkeypatch.setattr(c.provider, "open", trap)
    with c.db.transaction():
        validate(c)
        projected = retained_robot_projection(c.db, c.service.snapshot)
        assert projected.source_digest == c.outer["result"]["sourceArtifactDigest"]
        assert projected.snapshot == c.service.snapshot
        assert robot_projection_if_present(c.db, c.service.snapshot) == projected
    assert robot_output_names(c.outer["result"]) == {
        "robot-stdout.log",
        "robot-stderr.log",
        "robot-output.xml",
    }


def test_seeded_dispatch_checks_metadata_without_provider(case, monkeypatch):
    c = case
    monkeypatch.setattr(c.registry, "selection_for", trap)
    monkeypatch.setattr(c.provider, "open", trap)
    with c.db.transaction():
        validate(c, terminal=False)


@pytest.mark.parametrize(
    "key,value", [("version", True), ("version", 1.0), ("version", 2), ("extra", None)]
)
def test_outer_envelope_rejected(completed, key, value):
    c = completed
    outer = dict(c.outer)
    outer[key] = value
    # Preserve float spellings to prove scalar type checks before normalization.
    with c.db.transaction():
        c.db.update_by_id(Run, c.run.id, {"result": json.dumps(outer)})
    with pytest.raises(FenceRejected):
        validate(c)


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r["publicationFence"].update(epoch=True),
        lambda r: r["launch"]["fence"].update(epoch=True),
        lambda r: r["launch"]["selection"].update(python_version=[3.0, 12]),
        lambda r: r["launch"].update(launch_id=str(uuid4()).upper()),
        lambda r: r["launch"].update(discriminator="other"),
        lambda r: r["launch"].update(selection_encoding="other"),
        lambda r: r["launch"]["selection"].update(inputs='{"value":"changed"}'),
        lambda r: r["launch"]["selection"].update(input_schema="{}"),
        lambda r: r["launch"]["selection"].update(task_name="Other"),
        lambda r: r["launch"]["selection"].update(source_digest="sha256:" + "f" * 64),
        lambda r: r["launch"]["selection"].update(
            rcc_artifact_digest="sha256:" + "f" * 64
        ),
        lambda r: r.update(returnCode=False),
        lambda r: r.update(status="FAIL"),
        lambda r: r["actionResult"].update(extra=True),
        lambda r: r["cleanup"].update(wrapper_reaped=1),
        lambda r: r["cleanup"].update(descendant_snapshot_complete=False),
        lambda r: r["cleanup"].update(zombie_descendant_pids=[True]),
        lambda r: r["cleanup"].update(zombie_descendant_pids=[10, 10]),
        lambda r: r["cleanup"].update(live_descendant_pids=[10]),
        lambda r: r["outputs"][0].update(size=True),
        lambda r: r["outputs"][0].update(observedBytes=True),
        lambda r: r["outputs"][0].update(truncated=0),
        lambda r: r["outputs"][0].update(name="other"),
        lambda r: r["outputs"][0].update(ref=r["outputs"][1]["ref"]),
        lambda r: r["outputs"][0]["ref"].update(workspace_id=str(uuid4())),
        lambda r: r["outputs"][0].update(digest="sha256:" + "f" * 64),
    ],
)
def test_receipt_mutations_rejected(completed, change):
    change_record(completed, change)
    with pytest.raises(FenceRejected):
        validate(completed)


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider_key", "other"),
        ("workspace_id", None),
        ("run_attempt_id", None),
        ("epoch", 99),
        ("media_type", "text/plain"),
        ("name", "other"),
        ("state", "provisional"),
        ("expires_ms", "0"),
        ("expires_ms", "01"),
        ("object_ref", "bad"),
        ("digest", "sha256:" + "f" * 64),
        ("size", 999),
    ],
)
def test_output_sql_scope_mutation_rejected(completed, field, value):
    c = completed
    row = c.db.all(RunOutput)[0]
    if value is None:
        # Valid existing identities avoid turning the test into only an FK error.
        value = str(uuid4()) if field == "workspace_id" else row.run_attempt_id
        if field == "workspace_id":
            from actions.server.run_outputs.models import Workspace

            with c.db.transaction():
                c.db.insert(Workspace(value, "active", 0))
        else:
            old = _one(c.db, RunAttempt, row.run_attempt_id)
            other = replace(old, id=str(uuid4()))
            with c.db.transaction():
                c.db.insert(other)
            value = other.id
    with c.db.transaction():
        c.db.update_by_id(RunOutput, row.id, {field: value})
    with pytest.raises(FenceRejected):
        validate(c)


def test_expired_output_only_allows_explicit_metadata_ack(completed):
    c = completed
    row = c.db.all(RunOutput)[0]
    with c.db.transaction():
        c.db.update_by_id(RunOutput, row.id, {"expires_ms": "1"})
    with pytest.raises(FenceRejected):
        validate(c)
    validate(c, allow_expired=True)
    with pytest.raises(FenceRejected):
        validate(c, allow_expired=1)


@pytest.mark.parametrize(
    "change",
    [
        "pin_epoch",
        "attempt_owner",
        "attempt_state",
        "admission",
        "inputs",
        "extra_final",
    ],
)
def test_current_authority_rows_are_rechecked(completed, change):
    c = completed
    with c.db.transaction():
        if change == "pin_epoch":
            c.db.update_by_id(RunPin, c.run.id, {"epoch": 99})
        elif change == "attempt_owner":
            c.db.update_by_id(
                RunAttempt, c.ticket.fence.attempt_id, {"owner_id": str(uuid4())}
            )
        elif change == "attempt_state":
            c.db.update_by_id(
                RunAttempt, c.ticket.fence.attempt_id, {"state": "running"}
            )
        elif change == "admission":
            pin = _one(c.db, RunPin, c.run.id)
            c.db.update_by_id(
                RunAdmission, pin.run_admission_id, {"snapshot_json": "{}"}
            )
        elif change == "inputs":
            c.db.update_by_id(Run, c.run.id, {"inputs": "{}"})
        else:
            c.db.insert(replace(c.db.all(RunOutput)[0], id=str(uuid4()), name="extra"))
    with pytest.raises(FenceRejected):
        validate(c)


@pytest.mark.parametrize(
    "field",
    [
        "manifest_json",
        "source_inventory_json",
        "build_evidence_json",
        "source_artifact_digest",
    ],
)
def test_package_metadata_mutation_rejected(completed, field):
    c = completed
    row = c.db.all(FoundryPackageRevision)[0]
    value = "sha256:" + "f" * 64 if field == "source_artifact_digest" else "{}"
    with c.db.transaction():
        c.db.update_by_id(FoundryPackageRevision, row.id, {field: value})
    with pytest.raises(FenceRejected):
        validate(c)


def test_duplicate_scoped_package_rejected(completed):
    c = completed
    row = c.db.all(FoundryPackageRevision)[0]
    with c.db.transaction():
        c.db.insert(replace(row, id=str(uuid4())))
    with pytest.raises(FenceRejected):
        validate(c)


def test_record_duplicate_keys_rejected(completed):
    c = completed
    raw = c.run.result.replace('"version":1', '"version":1,"version":1')
    assert raw != c.run.result
    with c.db.transaction():
        c.db.update_by_id(Run, c.run.id, {"result": raw})
    with pytest.raises(FenceRejected):
        validate(c)


def test_retained_rcc_projection_never_reads_source(admitted, tmp_path, monkeypatch):
    import sys
    from pathlib import Path

    from action_server_tests.test_robot_package_admission import request_for

    from actions.server.deployments.package_revision_compiler import (
        PreparedRccEnvironment,
        RccBuildIdentity,
    )
    from actions.server.foundry.robot_execution import RccRobotPreparation
    from actions.server.foundry.robot_package_admission import digest
    from actions.server.foundry.robot_package_builder import RccRobotPlan
    from actions.server.run_outputs.types import ExecutionSnapshot

    db, refs, actor, registry, _, provider = admitted
    preparation = RccRobotPreparation(
        Path(sys.executable),
        PreparedRccEnvironment(
            tmp_path,
            digest(b"dependencies: {}\n"),
            RccBuildIdentity("sha256:" + "1" * 64, "sha256:" + "2" * 64),
        ),
    )
    evidence = registry.prepare_trusted_robot(
        request_for("rcc"),
        logical_package_key="rcc-projection",
        trusted_actor=actor,
        workspace_id=refs.workspace,
        application_id=refs.deployment_id,
        preparation=preparation,
    )
    package = registry.admit_robot(actor, refs.workspace, evidence)
    cap = registry.capability_refs(package)[0]
    plan = registry.get_capability(cap).runtime_plans[0]
    from actions.server.deployments.ids import DeploymentRevisionRef

    snapshot = ExecutionSnapshot(
        deployment=DeploymentRevisionRef(
            workspace_id=refs.workspace,
            deployment_id=refs.deployment_id,
            revision_id="sha256:" + "3" * 64,
        ),
        capability=cap,
        runtime_plan=plan,
        worker=refs.worker,
        policy=refs.policy,
        output_provider=refs.output_provider,
        runtime_kind="rcc",
        capability_schema_digest=digest(evidence.package.robot.input_schema),
        action_id=registry.action_id_for(cap),
        capability_authority="package-revision",
    )
    monkeypatch.setattr(registry, "selection_for", trap)
    monkeypatch.setattr(provider, "open", trap)
    with db.transaction():
        projection = retained_robot_projection(db, snapshot)
        assert isinstance(projection.plan, RccRobotPlan)
        assert projection.plan.artifact_digest == "sha256:" + "2" * 64
        row = db.all(FoundryPackageRevision)[0]
        original = row.build_evidence_json
        bad = json.loads(original)
        bad["source"]["size"] = True
        db.update_by_id(
            FoundryPackageRevision, row.id, {"build_evidence_json": json.dumps(bad)}
        )
        with pytest.raises(FenceRejected):
            retained_robot_projection(db, snapshot)


def test_stale_run_argument_rejected(completed):
    c = completed
    with c.db.transaction():
        c.db.update_by_id(Run, c.run.id, {"result": "{}"})
    with pytest.raises(FenceRejected):
        validate_robot_record(
            c.db,
            c.registry,
            c.service.snapshot,
            c.run,
            c.ticket.fence,
            c.outer["result"],
            claim=None,
            terminal=True,
            outputs=c.outer["outputs"],
        )
