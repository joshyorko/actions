# Imported pytest fixtures are intentionally injected by parameter name.
# ruff: noqa: F811
"""Bound selection authority with actual Run/Attempt SQL and provider IO traps."""
from dataclasses import replace
from uuid import uuid4

import pytest
from action_server_tests.run_outputs.test_service import snapshot
from action_server_tests.test_robot_package_admission import (  # noqa: F401
    admitted,
    disable_feedback,
)

from actions.server.foundry.execution_selection import compiled_for_snapshot
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.robot_execution_selection import prepare_robot_selection
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.types import ExecutionSnapshot

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def admitted_run(case):
    db, refs, actor, registry, evidence, provider = case
    ref = registry.admit_robot(actor, refs.workspace, evidence)
    cap = registry.capability_refs(ref)[0]
    declaration = registry.get_capability(cap)
    raw = snapshot(str(ref.workspace_id.root)).model_dump(mode="json")
    raw.update(
        capability_authority="package-revision",
        capability=cap.model_dump(mode="json"),
        runtime_plan=declaration.runtime_plans[0].model_dump(mode="json"),
        action_id=registry.action_id_for(cap),
        capability_schema_digest=declaration.schema_digest,
        runtime_kind="direct",
    )
    selected = ExecutionSnapshot.model_validate(raw)
    with db.transaction():
        for reference in (
            selected.deployment,
            selected.worker,
            selected.policy,
            selected.output_provider,
        ):
            db.insert(
                FoundryAccessGrant(
                    str(uuid4()),
                    str(ref.workspace_id.root),
                    actor.principal_id,
                    "reference",
                    reference_grant_subject(reference),
                    '["execute"]',
                )
            )
    control = RunOutputControlPlane(db, capabilities=registry)
    control.register(selected)
    control.grant(actor, selected.deployment, {"execute", "read", "cancel"})
    outputs = RunOutputService(db, {}, capabilities=registry)
    run = outputs.admit(actor, selected, {"value": "owned"}, "robot")
    fence = outputs.claim(run.id, str(uuid4()), lease_seconds=60)
    return outputs, fence, selected, control


def test_prebound_callback_is_sql_only_and_python_path_refuses_robot(
    admitted, monkeypatch
):
    db, refs, actor, registry, evidence, provider = admitted
    outputs, fence, snapshot, control = admitted_run(admitted)
    with pytest.raises(AccessDenied):
        compiled_for_snapshot(registry, snapshot)
    checks = []

    def current(a, f, s):
        checks.append((a, f, s))

    prepared = prepare_robot_selection(
        outputs, registry, actor, fence, require_current=current
    )
    assert prepared.source_archive == evidence.package.source_archive

    def denied(*a, **k):
        raise AssertionError("provider/projection IO in bound callback")

    monkeypatch.setattr(provider, "open", denied)
    monkeypatch.setattr(registry, "load_verified", denied)
    monkeypatch.setattr(registry, "schema_for", denied)
    with db.transaction():
        assert (
            prepared(actor, fence, snapshot, {"value": "owned"}) == prepared.selection
        )
    assert len(checks) >= 3
    with pytest.raises(FenceRejected):
        replace(prepared)(actor, fence, snapshot, {"value": "owned"})


@pytest.mark.parametrize("change", ["source", "grant", "cancel", "epoch", "callback"])
def test_live_changes_deny_bound_selection(admitted, change):
    db, refs, actor, registry, evidence, provider = admitted
    outputs, fence, snapshot, control = admitted_run(admitted)
    allowed = [True]

    def current(a, f, s):
        if not allowed[0]:
            raise FenceRejected("current deployment or independent claim changed")

    prepared = prepare_robot_selection(
        outputs, registry, actor, fence, require_current=current
    )
    if change == "source":
        with db.transaction():
            db.execute(
                "UPDATE foundry_package_revision SET build_evidence_json=? WHERE revision_id=?",
                ["{}", snapshot.capability.package_revision.revision_id.root],
            )
    elif change == "grant":
        control.grant(actor, snapshot.deployment, {"read"})
    elif change == "cancel":
        with db.transaction():
            db.insert(
                FoundryAccessGrant(
                    str(uuid4()),
                    str(refs.workspace.root),
                    actor.principal_id,
                    "application",
                    str(snapshot.deployment.deployment_id.root),
                    '["cancel_execution"]',
                )
            )
        outputs.cancel(actor, fence.run_id)
    elif change == "epoch":
        fence = fence.model_copy(update={"epoch": fence.epoch + 1})
    else:
        allowed[0] = False
    with pytest.raises((ValueError, FenceRejected, AccessDenied)):
        prepared(actor, fence, snapshot, {"value": "owned"})


def test_preparation_refuses_outer_transaction(admitted):
    db, refs, actor, registry, evidence, provider = admitted
    outputs, fence, snapshot, control = admitted_run(admitted)
    with db.transaction(), pytest.raises(FenceRejected):
        prepare_robot_selection(
            outputs, registry, actor, fence, require_current=lambda *args: None
        )
