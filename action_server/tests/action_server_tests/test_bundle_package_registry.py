"""Real registry SQL/source seals; synthetic compiler is not execution proof."""
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant
from contract_tests.test_capability_bundle import Executor, entries, policy

from actions.server.deployments.foundry_values import AccessDenied
from actions.server.deployments.ids import CapabilityRef, RuntimePlanRef
from actions.server.deployments.package_revision_compiler import (
    TrustedDeveloperExecutionAdmission,
)
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryPackageRevision,
    FoundryRequest,
)
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def registry(db, provider):
    return FoundryPackageRegistry(
        db,
        provider,
        SqlFoundryAuthorization(db),
        executor=Executor(),
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
    )


def compile_(r, refs, actor, p=None):
    result = r.compile_trusted_bundle(
        entries(),
        policy=p or policy(),
        trusted_actor=actor,
        workspace_id=refs.workspace,
        application_id=refs.deployment_id,
    )
    assert result.evidence.ready
    assert result.compiled_package is not None
    return result.compiled_package


def test_bundle_admission_exact_projection_reload_and_outer_identity(
    database_location, foundry_package_store
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        b = compile_(r, refs, actor)
        ref = r.admit_compiled(actor, refs.workspace, b)
        assert ref.revision_id == b.package_revision_id
        assert r.admit_compiled(actor, refs.workspace, b) == ref
        fresh = registry(db, foundry_package_store)
        assert fresh.load_verified(ref) == b
        with pytest.raises(AccessDenied):
            fresh.load(ref)
        a, beta = fresh.capability_refs(ref)
        da, dbeta = fresh.get_capability(a), fresh.get_capability(beta)
        assert da.work_items.mode == "none" and dbeta.work_items.mode == "producer"
        assert fresh.get_runtime_plan(da.runtime_plans[0]).capabilities == (a,)
        selected = fresh.selection_for(beta, dbeta.runtime_plans[0])
        assert selected.package_revision == ref
        assert selected.compiled.package_revision_id != ref.revision_id
        assert json.loads(selected.compiled.output_schema_payload)["type"] == "integer"
        with pytest.raises(AccessDenied):
            fresh.selection_for(a, dbeta.runtime_plans[0])
        missing = CapabilityRef(package_revision=ref, capability_id="action.unknown")
        assert fresh.get_capability(missing) is None
        with pytest.raises(AccessDenied):
            fresh.selection_for(missing, da.runtime_plans[0])
        assert fresh.evidence(ref).ready
        assert len(db.all(FoundryPackageRevision)) == 1
        assert (
            len([x for x in db.all(FoundryRequest) if x.operation == "package.admit"])
            == 1
        )


def test_bundle_unissued_copy_and_other_actor_denied(
    database_location, foundry_package_store
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        b = compile_(r, refs, actor)
        for candidate, who in (
            (replace(b), actor),
            (b, Actor(principal_id=str(uuid4()))),
        ):
            with pytest.raises(AccessDenied):
                r.admit_compiled(who, refs.workspace, candidate)
        assert db.all(FoundryPackageRevision) == []


def test_bundle_requires_live_compile_authority_and_replay_no_grant_resurrection(
    database_location, foundry_package_store
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        r = registry(db, foundry_package_store)
        with pytest.raises(AccessDenied):
            compile_(r, refs, actor)
        _grant(db, refs, actor)
        b = compile_(r, refs, actor)
        r.admit_compiled(actor, refs.workspace, b)
        with db.transaction():
            db.execute(
                "DELETE FROM foundry_access_grant WHERE subject_kind=?", ["reference"]
            )
        with pytest.raises(AccessDenied):
            r.admit_compiled(actor, refs.workspace, b)
        assert all(x.subject_kind != "reference" for x in db.all(FoundryAccessGrant))


def test_schema_for_rejects_cross_member_plan(database_location, foundry_package_store):
    from action_server_tests.run_outputs.test_service import snapshot

    from actions.server.run_outputs.service import AccessDenied as RunDenied
    from actions.server.run_outputs.types import ExecutionSnapshot

    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        ref = r.admit_compiled(actor, refs.workspace, compile_(r, refs, actor))
        a, b = r.capability_refs(ref)
        da, dbeta = r.get_capability(a), r.get_capability(b)
        raw = snapshot(str(refs.workspace.root)).model_dump(mode="json")
        raw.update(
            capability_authority="package-revision",
            capability=a.model_dump(mode="json"),
            runtime_plan=da.runtime_plans[0].model_dump(mode="json"),
            action_id=r.action_id_for(a),
            capability_schema_digest=da.schema_digest,
        )
        selected = r.schema_for(ExecutionSnapshot.model_validate(raw))
        assert json.loads(selected.output_schema)["type"] == "string"
        raw["runtime_plan"] = dbeta.runtime_plans[0].model_dump(mode="json")
        with pytest.raises(RunDenied):
            r.schema_for(ExecutionSnapshot.model_validate(raw))


@pytest.mark.parametrize("conflict", [False, True])
def test_duplicate_logical_requirement_ids_never_issued(
    database_location, foundry_package_store, conflict
):
    from actions.server.deployments.logical_bindings import (
        BindingField,
        BindingOperation,
        LogicalBindingRequirement,
    )

    requirement = LogicalBindingRequirement(
        id="records",
        kind="data",
        operations=(
            BindingOperation(
                name="records.read/v1",
                effect="read",
                parameters=(),
                result=(BindingField(name="count", kind="integer"),),
                max_rows=1,
                max_bytes=100,
                timeout_ms=100,
            ),
        ),
    )
    second = (
        requirement.model_copy(update={"kind": "knowledge"})
        if conflict
        else requirement
    )
    p = policy()
    p = replace(
        p,
        capabilities=tuple(
            replace(c, policy=replace(c.policy, logical_requirements=(req,)))
            for c, req in zip(p.capabilities, (requirement, second))
        ),
    )
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        with pytest.raises(AccessDenied, match="unique"):
            compile_(r, refs, actor, p)
        assert not r._pending
        assert not db.all(FoundryPackageRevision)


@pytest.mark.parametrize("field", ["receipts", "tag", "manifest", "inventory"])
def test_reload_rejects_corrupt_evidence(
    database_location, foundry_package_store, field
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        ref = r.admit_compiled(actor, refs.workspace, compile_(r, refs, actor))
        row = db.all(FoundryPackageRevision)[0]
        evidence = json.loads(row.build_evidence_json)
        if field == "receipts":
            evidence["receipts"].reverse()
            column = "build_evidence_json"
            value = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
        elif field == "tag":
            evidence["schemaVersion"] = "other"
            column = "build_evidence_json"
            value = json.dumps(evidence)
        elif field == "manifest":
            column = "manifest_json"
            value = "{}"
        else:
            column = "source_inventory_json"
            value = "[]"
        with db.transaction():
            db.execute(
                f"UPDATE foundry_package_revision SET {column}=? WHERE id=?",
                [value, row.id],
            )
        with pytest.raises(AccessDenied):
            registry(db, foundry_package_store).load_verified(ref)


def test_admission_sql_failure_rolls_back_rows_grants_and_audit(
    database_location, foundry_package_store, monkeypatch
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        b = compile_(r, refs, actor)
        original = db.insert

        def fail(value):
            if isinstance(value, FoundryAudit):
                raise RuntimeError("injected audit failure")
            return original(value)

        with monkeypatch.context() as m:
            m.setattr(db, "insert", fail)
            with pytest.raises(RuntimeError, match="injected"):
                r.admit_compiled(actor, refs.workspace, b)
        assert not db.all(FoundryPackageRevision)
        assert not db.all(FoundryRequest)
        assert all(x.subject_kind == "workspace" for x in db.all(FoundryAccessGrant))
        assert (
            r.admit_compiled(actor, refs.workspace, b).revision_id
            == b.package_revision_id
        )


def test_execute_grant_alone_cannot_compile_and_revocation_blocks_admission(
    database_location, foundry_package_store
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        grant = _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        b = compile_(r, refs, actor)
        with db.transaction():
            db.execute(
                "UPDATE foundry_access_grant SET operations_json=? WHERE id=?",
                ['["execute"]', grant.id],
            )
        with pytest.raises(AccessDenied):
            r.admit_compiled(actor, refs.workspace, b)
        with pytest.raises(AccessDenied):
            compile_(r, refs, actor)
        assert not db.all(FoundryPackageRevision)


def test_concurrent_identical_admission_has_one_outer_authority(
    database_location, foundry_package_store
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        bundles = [compile_(r, refs, actor), compile_(r, refs, actor)]
        barrier = Barrier(2)

        def admit(b):
            barrier.wait(timeout=10)
            return r.admit_compiled(actor, refs.workspace, b)

        with ThreadPoolExecutor(max_workers=2) as executor:
            values = list(executor.map(admit, bundles))
        assert values[0] == values[1]
        assert len(db.all(FoundryPackageRevision)) == 1
        assert len(db.all(FoundryRequest)) == 1
        assert len(db.all(FoundryAudit)) == 1


def test_scoped_selection_cannot_cross_package_and_workspace(
    database_location, foundry_package_store
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        ref = r.admit_compiled(actor, refs.workspace, compile_(r, refs, actor))
        a = r.capability_refs(ref)[0]
        plan = r.get_capability(a).runtime_plans[0]
        from actions.server.deployments.ids import WorkspaceId

        other = ref.model_copy(update={"workspace_id": WorkspaceId(uuid4())})
        with pytest.raises(AccessDenied):
            r.selection_for(
                a, RuntimePlanRef(package_revision=other, plan_digest=plan.plan_digest)
            )
        with pytest.raises(AccessDenied):
            r.load_verified(other)


@pytest.mark.parametrize("phase", ["build", "import", "test"])
def test_failed_bundle_compilation_has_no_ready_ack_or_pending(
    database_location, foundry_package_store, phase
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = FoundryPackageRegistry(
            db,
            foundry_package_store,
            SqlFoundryAuthorization(db),
            executor=Executor(fail=phase),
            admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        )
        result = r.compile_trusted_bundle(
            entries(),
            policy=policy(),
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
        )
        assert result.compiled_package is None and not result.evidence.ready
        assert result.evidence.status == "failed"
        assert not r._pending and not db.all(FoundryPackageRevision)


def test_bundle_evidence_roundtrip_and_exact_grant_set(
    database_location, foundry_package_store
):
    from actions.server.foundry.sql_authorization import reference_grant_subject

    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        result = r.compile_trusted_bundle(
            entries(),
            policy=policy(),
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
        )
        ref = r.admit_compiled(actor, refs.workspace, result.compiled_package)
        assert registry(db, foundry_package_store).evidence(ref) == result.evidence
        caps = r.capability_refs(ref)
        expected = {
            reference_grant_subject(v)
            for v in (ref, *caps, *(r.get_capability(c).runtime_plans[0] for c in caps))
        }
        grants = [
            g for g in db.all(FoundryAccessGrant) if g.subject_kind == "reference"
        ]
        assert {g.subject_id for g in grants} == expected
        assert len(grants) == 5
        assert all(
            json.loads(g.operations_json) == ["deploy", "execute"] for g in grants
        )


def test_selected_logical_requirement_and_unknown_requirement_are_exact(
    database_location, foundry_package_store
):
    from actions.server.deployments.ids import BindingRequirementRef
    from actions.server.deployments.logical_bindings import (
        BindingField,
        BindingOperation,
        LogicalBindingRequirement,
    )

    requirement = LogicalBindingRequirement(
        id="records",
        kind="data",
        operations=(
            BindingOperation(
                name="records.read/v1",
                effect="read",
                parameters=(),
                result=(BindingField(name="count", kind="integer"),),
                max_rows=1,
                max_bytes=100,
                timeout_ms=100,
            ),
        ),
    )
    p = policy()
    p = replace(
        p,
        capabilities=(
            p.capabilities[0],
            replace(
                p.capabilities[1],
                policy=replace(
                    p.capabilities[1].policy, logical_requirements=(requirement,)
                ),
            ),
        ),
    )
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        r = registry(db, foundry_package_store)
        ref = r.admit_compiled(actor, refs.workspace, compile_(r, refs, actor, p))
        a, b = r.capability_refs(ref)
        assert r.get_capability(a).binding_requirements == ()
        bound = r.get_capability(b).binding_requirements
        assert len(bound) == 1 and bound[0].package_revision == ref
        assert r.get_binding_requirement(bound[0]).contract == requirement
        assert (
            r.get_binding_requirement(
                BindingRequirementRef(package_revision=ref, requirement_id="missing")
            )
            is None
        )
