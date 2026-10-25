"""Execution pins the outer Package and exact selected adapter preimage."""
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_logical_binding_checkpoint import compile_fixture

from actions.server.deployments.ids import (
    CapabilityRef,
    PackageRevisionRef,
    RuntimePlanRef,
)
from actions.server.foundry.execution_selection import compiled_for_snapshot
from actions.server.run_outputs.service import AccessDenied


def fixture():
    compiled = compile_fixture().compiled_package
    import json

    package = PackageRevisionRef(
        workspace_id=uuid4(), package_id=uuid4(), revision_id="sha256:" + "a" * 64
    )
    capability = CapabilityRef(
        package_revision=package,
        capability_id=json.loads(compiled.manifest_json)["capabilities"][0]["id"],
    )
    plan = RuntimePlanRef(
        package_revision=package, plan_digest=compiled.runtime_plan_header.plan_digest
    )
    snapshot = SimpleNamespace(capability=capability, runtime_plan=plan)
    selected = SimpleNamespace(
        package_revision=package,
        capability=capability,
        runtime_plan=plan,
        compiled=compiled,
    )
    registry = SimpleNamespace(selection_for=lambda c, p: selected)
    return snapshot, selected, registry


def test_outer_revision_is_not_replaced_by_inner_integrity_preimage():
    snapshot, selected, registry = fixture()
    assert (
        selected.compiled.package_revision_id
        != snapshot.capability.package_revision.revision_id
    )
    assert compiled_for_snapshot(registry, snapshot) is selected.compiled


@pytest.mark.parametrize("field", ["package_revision", "capability", "runtime_plan"])
def test_mismatched_selection_is_refused(field):
    snapshot, selected, registry = fixture()
    setattr(selected, field, object())
    with pytest.raises(AccessDenied):
        compiled_for_snapshot(registry, snapshot)


def test_cross_package_plan_is_refused():
    snapshot, selected, registry = fixture()
    snapshot.runtime_plan = snapshot.runtime_plan.model_copy(
        update={
            "package_revision": snapshot.capability.package_revision.model_copy(
                update={"package_id": uuid4()}
            )
        }
    )
    selected.runtime_plan = snapshot.runtime_plan
    with pytest.raises(AccessDenied):
        compiled_for_snapshot(registry, snapshot)


def test_corrupted_member_is_refused():
    snapshot, selected, registry = fixture()
    selected.compiled = replace(selected.compiled, source_archive=b"corrupt")
    with pytest.raises(AccessDenied):
        compiled_for_snapshot(registry, snapshot)


def test_other_member_plan_is_refused():
    snapshot, selected, registry = fixture()
    snapshot.runtime_plan = snapshot.runtime_plan.model_copy(
        update={
            "plan_digest": type(snapshot.runtime_plan.plan_digest)("sha256:" + "b" * 64)
        }
    )
    selected.runtime_plan = snapshot.runtime_plan
    with pytest.raises(AccessDenied):
        compiled_for_snapshot(registry, snapshot)


def test_real_registry_denial_uses_run_execution_boundary():
    from actions.server.deployments.foundry_values import AccessDenied as RegistryDenied

    snapshot, _, registry = fixture()

    def deny(*args):
        raise RegistryDenied("Undeclared Package selection")

    registry.selection_for = deny
    with pytest.raises(AccessDenied, match="Package execution selection unavailable"):
        compiled_for_snapshot(registry, snapshot)
