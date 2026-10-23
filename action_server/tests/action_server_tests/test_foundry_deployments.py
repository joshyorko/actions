"""Focused #129 Deployment resolver tests on the existing Runtime Database."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from typing import Iterator
from uuid import uuid4

import pytest

from actions.server._database import Database
from actions.server._models import (
    RUN_ID_COUNTER,
    Action,
    ActionPackage,
    Counter,
    Run,
    get_all_model_classes,
    get_model_db_rules,
)
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    AccessDenied,
    BindingAssignment,
    CapabilityPlanPolicy,
    DeploymentSpecification,
    IdempotencyConflict,
    RepositoryCorruption,
    StaleDeploymentRevision,
)
from actions.server.deployments.ids import (
    BindingRequirementRef,
    CapabilityRef,
    DeploymentId,
    PackageId,
    PackageRevisionId,
    PackageRevisionRef,
    PlanDigest,
    PolicyId,
    PolicyRevisionId,
    ProviderProfileId,
    ProviderProfileRevisionId,
    ProviderProfileRevisionRef,
    RuntimePlanRef,
    WorkerProfileId,
    WorkerProfileRevisionId,
    WorkerProfileRevisionRef,
    WorkspaceId,
    WorkspacePolicyRevisionRef,
)
from actions.server.foundry.models import (
    FoundryAudit,
    FoundryDeploymentHead,
    FoundryDeploymentRevision,
    FoundryPackageRevision,
    FoundryRequest,
)
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration, migrate_db
from actions.server.run_outputs.models import RunPin, Workspace
from actions.server.run_outputs.service import RunOutputControlPlane, RunOutputService
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def _uuid() -> str:
    return str(uuid4())


def _digest(char: str) -> str:
    return "sha256:" + char * 64


def _refs():
    workspace = WorkspaceId(_uuid())
    package = PackageRevisionRef(
        workspace_id=workspace,
        package_id=PackageId(_uuid()),
        revision_id=PackageRevisionId(_digest("1")),
    )
    capability = CapabilityRef(package_revision=package, capability_id="lookup")
    plan = RuntimePlanRef(
        package_revision=package, plan_digest=PlanDigest(_digest("2"))
    )
    requirement = BindingRequirementRef(
        package_revision=package, requirement_id="customer-data"
    )
    provider = ProviderProfileRevisionRef(
        workspace_id=workspace,
        provider_profile_id=ProviderProfileId(_uuid()),
        revision_id=ProviderProfileRevisionId(_digest("3")),
    )
    second_provider = ProviderProfileRevisionRef(
        workspace_id=workspace,
        provider_profile_id=ProviderProfileId(_uuid()),
        revision_id=ProviderProfileRevisionId(_digest("4")),
    )
    output_provider = ProviderProfileRevisionRef(
        workspace_id=workspace,
        provider_profile_id=ProviderProfileId(_uuid()),
        revision_id=ProviderProfileRevisionId(_digest("5")),
    )
    worker = WorkerProfileRevisionRef(
        workspace_id=workspace,
        worker_profile_id=WorkerProfileId(_uuid()),
        revision_id=WorkerProfileRevisionId(_digest("6")),
    )
    policy = WorkspacePolicyRevisionRef(
        workspace_id=workspace,
        policy_id=PolicyId(_uuid()),
        revision_id=PolicyRevisionId(_digest("7")),
    )
    deployment_id = DeploymentId(_uuid())
    return SimpleNamespace(
        workspace=workspace,
        package=package,
        capability=capability,
        plan=plan,
        requirement=requirement,
        provider=provider,
        second_provider=second_provider,
        output_provider=output_provider,
        worker=worker,
        policy=policy,
        deployment_id=deployment_id,
    )


def _spec(refs, *, provider=None) -> DeploymentSpecification:
    return DeploymentSpecification(
        package_revisions=(refs.package,),
        capability_plans=(
            CapabilityPlanPolicy(
                capability=refs.capability,
                mode="locked",
                allowed_plans=(refs.plan,),
                default_plan=refs.plan,
            ),
        ),
        bindings=(
            BindingAssignment(
                requirement=refs.requirement,
                provider=provider or refs.provider,
            ),
        ),
        worker=refs.worker,
        policy=refs.policy,
        output_provider=refs.output_provider,
    )


class _PackagePort:
    """Test adapter double for the compiler-owned Package Revision schema."""

    def __init__(self, refs):
        self.refs = refs
        self.package_refs = {refs.package}
        self.capabilities = {
            refs.capability: SimpleNamespace(
                ref=refs.capability,
                schema_digest=_digest("8"),
                runtime_plans=(refs.plan,),
                binding_requirements=(refs.requirement,),
            )
        }
        self.plans = {
            refs.plan: SimpleNamespace(
                ref=refs.plan,
                runtime_kind="test/no-external-effects",
                capabilities=(refs.capability,),
            )
        }
        self.requirements = {refs.requirement: SimpleNamespace(ref=refs.requirement)}

    def require_revision(self, ref):
        if ref not in self.package_refs:
            raise AccessDenied("Package Revision unavailable")

    def get_capability(self, ref):
        return self.capabilities.get(ref)

    def get_runtime_plan(self, ref):
        return self.plans.get(ref)

    def get_binding_requirement(self, ref):
        return self.requirements.get(ref)


class _AuthorizationPort:
    """Test double proving the service requires explicit typed authorization."""

    def __init__(self, workspace):
        self.allowed_workspaces = {workspace}
        self.revoked_references = set()
        self.calls = []

    def require_workspace(self, actor, workspace_id, permission):
        self.calls.append(("workspace", workspace_id, permission))
        if workspace_id not in self.allowed_workspaces:
            raise AccessDenied("Workspace unavailable or not authorized")

    def require_deployment(self, actor, workspace_id, deployment_id, permission):
        self.calls.append(("deployment", deployment_id, permission))
        if workspace_id not in self.allowed_workspaces:
            raise AccessDenied("Deployment unavailable or not authorized")

    def require_reference(self, actor, ref, permission):
        workspace_id = getattr(ref, "workspace_id", None)
        if workspace_id is None and hasattr(ref, "package_revision"):
            workspace_id = ref.package_revision.workspace_id
        self.calls.append(("reference", ref, permission))
        if ref in self.revoked_references:
            raise AccessDenied("Reference unavailable or not authorized")
        if workspace_id not in self.allowed_workspaces:
            raise AccessDenied("Reference unavailable or not authorized")


class _ExecutionPort:
    def action_id_for(self, ref):
        return "test-action-1"


@contextmanager
def _runtime_database(
    path: Path,
    workspace_id: WorkspaceId,
    package_refs: tuple[PackageRevisionRef, ...],
) -> Iterator[Database]:
    """Upgrade the actual Runtime schema16 fixture through shared migration17."""
    db = Database(path)
    legacy_classes = [
        cls for cls in get_all_model_classes() if not cls.__name__.startswith("Foundry")
    ]
    with db.connect():
        db.initialize(legacy_classes)
        with db.transaction():
            db.create_tables(get_model_db_rules())
            db.insert(Migration(16, MIGRATION_ID_TO_NAME[16]))
            db.insert(Workspace(str(workspace_id.root), "active", 0))
            db.insert(Counter(RUN_ID_COUNTER, 0))

    assert migrate_db(path)
    db = Database(path)
    with db.connect():
        db.initialize(get_all_model_classes())
        with db.transaction():
            for package_ref in package_refs:
                db.insert(
                    FoundryPackageRevision(
                        id=_uuid(),
                        workspace_id=str(package_ref.workspace_id.root),
                        package_id=str(package_ref.package_id.root),
                        revision_id=package_ref.revision_id.root,
                        manifest_json="{}",
                        source_artifact_digest=_digest("f"),
                        source_inventory_json="{}",
                        build_evidence_json="{}",
                    )
                )
        tables = set(db.list_table_names())
        assert "foundry_deployment_revision" in tables
        assert "foundry_deployment_head" in tables
        assert "deployment_revision" not in tables
        yield db


def _service(db, refs, packages=None):
    package_port = packages or _PackagePort(refs)
    authorization = _AuthorizationPort(refs.workspace)
    return (
        FoundryDeploymentService(
            FoundryRepository(db), package_port, authorization, _ExecutionPort()
        ),
        package_port,
        authorization,
    )


def _action_and_grant(db, refs, snapshot, actor):
    with db.transaction():
        db.insert(
            ActionPackage(
                str(refs.package.package_id.root),
                "foundry-test-package",
                "test-source",
                "test-hash",
                "{}",
            )
        )
        db.insert(
            Action(
                "test-action-1",
                str(refs.package.package_id.root),
                refs.capability.capability_id.root,
                "test action",
                "action.py",
                1,
                '{"type":"object"}',
                "{}",
            )
        )
    control = RunOutputControlPlane(db)
    control.register(snapshot)
    control.grant(actor, snapshot.deployment, {"execute", "read", "cancel"})
    return RunOutputService(db, {}), control


def test_resolution_requires_the_declared_capability_and_binding_ports(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, package_port, authorization = _service(db, refs)
        created = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        assert (
            service.resolve(
                actor, refs.workspace, refs.deployment_id, refs.capability
            ).snapshot.deployment
            == created.ref
        )

        package_port.capabilities.clear()
        with pytest.raises(AccessDenied, match="Capability unavailable"):
            service.resolve(actor, refs.workspace, refs.deployment_id, refs.capability)
        assert any(call[0] == "reference" for call in authorization.calls)


def test_cross_workspace_capability_is_denied_before_execution_resolution(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        foreign_workspace = WorkspaceId(_uuid())
        foreign_package = PackageRevisionRef(
            workspace_id=foreign_workspace,
            package_id=PackageId(_uuid()),
            revision_id=PackageRevisionId(_digest("9")),
        )
        foreign_capability = CapabilityRef(
            package_revision=foreign_package, capability_id="lookup"
        )
        with pytest.raises(AccessDenied, match="Capability unavailable"):
            service.resolve(
                actor,
                refs.workspace,
                refs.deployment_id,
                foreign_capability,
            )


def test_every_package_revision_needs_a_shared_store_anchor(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    missing_package = PackageRevisionRef(
        workspace_id=refs.workspace,
        package_id=PackageId(_uuid()),
        revision_id=PackageRevisionId(_digest("9")),
    )
    specification = _spec(refs).model_copy(
        update={"package_revisions": (refs.package, missing_package)}
    )
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        package_port = _PackagePort(refs)
        package_port.package_refs.add(missing_package)
        service, _, _ = _service(db, refs, package_port)
        with pytest.raises(AccessDenied, match="Package Revision unavailable"):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                specification,
                idempotency_key="create-1",
            )
        assert db.all(FoundryDeploymentHead) == []


def test_package_fk_anchor_does_not_choose_execution_or_drop_package_refs(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    anchor_package = PackageRevisionRef(
        workspace_id=refs.workspace,
        package_id=PackageId("00000000-0000-0000-0000-000000000000"),
        revision_id=PackageRevisionId(_digest("9")),
    )
    single_package_spec = _spec(refs)
    specification = DeploymentSpecification(
        package_revisions=(refs.package, anchor_package),
        capability_plans=single_package_spec.capability_plans,
        bindings=single_package_spec.bindings,
        worker=refs.worker,
        policy=refs.policy,
        output_provider=refs.output_provider,
    )
    package_port = _PackagePort(refs)
    package_port.package_refs.add(anchor_package)
    with _runtime_database(
        database_location, refs.workspace, (refs.package, anchor_package)
    ) as db:
        service, _, authorization = _service(db, refs, package_port)
        created = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            specification,
            idempotency_key="multi-package-create",
        )
        anchor = db.first(
            FoundryPackageRevision,
            "SELECT * FROM foundry_package_revision WHERE workspace_id=? "
            "AND package_id=? AND revision_id=?",
            [
                str(refs.workspace.root),
                str(anchor_package.package_id.root),
                anchor_package.revision_id.root,
            ],
        )
        revision_row = db.first(
            FoundryDeploymentRevision,
            "SELECT * FROM foundry_deployment_revision WHERE revision_id=?",
            [created.ref.revision_id.root],
        )
        assert revision_row.foundry_package_revision_id == anchor.id
        selection = json.loads(revision_row.selection_json)
        assert selection["sequence"] == created.sequence
        assert len(selection["specification"]["package_revisions"]) == 2
        assert created.specification.package_revisions == (
            anchor_package,
            refs.package,
        )
        resolved = service.resolve(
            actor, refs.workspace, refs.deployment_id, refs.capability
        )
        assert resolved.snapshot.capability == refs.capability
        assert resolved.revision.specification.package_revisions == (
            anchor_package,
            refs.package,
        )
        authorization.revoked_references.add(anchor_package)
        with pytest.raises(AccessDenied, match="Reference unavailable"):
            service.resolve(actor, refs.workspace, refs.deployment_id, refs.capability)


def test_resolution_returns_only_bindings_for_the_selected_capability(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    second_capability = CapabilityRef(
        package_revision=refs.package, capability_id="admin"
    )
    second_requirement = BindingRequirementRef(
        package_revision=refs.package, requirement_id="admin-data"
    )
    second_plan = RuntimePlanRef(
        package_revision=refs.package, plan_digest=PlanDigest(_digest("a"))
    )
    specification = DeploymentSpecification(
        package_revisions=(refs.package,),
        capability_plans=(
            CapabilityPlanPolicy(
                capability=refs.capability,
                mode="locked",
                allowed_plans=(refs.plan,),
                default_plan=refs.plan,
            ),
            CapabilityPlanPolicy(
                capability=second_capability,
                mode="locked",
                allowed_plans=(second_plan,),
                default_plan=second_plan,
            ),
        ),
        bindings=(
            BindingAssignment(requirement=refs.requirement, provider=refs.provider),
            BindingAssignment(
                requirement=second_requirement, provider=refs.second_provider
            ),
        ),
        worker=refs.worker,
        policy=refs.policy,
        output_provider=refs.output_provider,
    )
    package_port = _PackagePort(refs)
    package_port.capabilities[second_capability] = SimpleNamespace(
        ref=second_capability,
        schema_digest=_digest("b"),
        runtime_plans=(second_plan,),
        binding_requirements=(second_requirement,),
    )
    package_port.plans[second_plan] = SimpleNamespace(
        ref=second_plan,
        runtime_kind="test/no-external-effects",
        capabilities=(second_capability,),
    )
    package_port.requirements[second_requirement] = SimpleNamespace(
        ref=second_requirement
    )
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, authorization = _service(db, refs, package_port)
        service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            specification,
            idempotency_key="create-1",
        )
        authorization.calls.clear()
        resolved = service.resolve(
            actor, refs.workspace, refs.deployment_id, refs.capability
        )
        assert resolved.binding_requirements == (refs.requirement,)
        assert tuple(item.requirement for item in resolved.bindings) == (
            refs.requirement,
        )
        assert not any(
            call[0] == "reference" and call[1] == refs.second_provider
            for call in authorization.calls
        )


def test_compare_and_swap_rejects_a_stale_revision(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        first_head = db.first(
            FoundryDeploymentHead,
            "SELECT * FROM foundry_deployment_head WHERE workspace_id=? AND deployment_id=?",
            [str(refs.workspace.root), str(refs.deployment_id.root)],
        )
        assert first_head.active_revision_id == first.ref.revision_id.root
        assert first_head.lock_version == 1
        second = service.publish(
            actor,
            refs.workspace,
            refs.deployment_id,
            first.ref,
            _spec(refs, provider=refs.second_provider),
            idempotency_key="publish-2",
        )
        second_head = db.first(
            FoundryDeploymentHead,
            "SELECT * FROM foundry_deployment_head WHERE workspace_id=? AND deployment_id=?",
            [str(refs.workspace.root), str(refs.deployment_id.root)],
        )
        assert second_head.active_revision_id == second.ref.revision_id.root
        assert second_head.lock_version == 2
        with pytest.raises(StaleDeploymentRevision):
            service.publish(
                actor,
                refs.workspace,
                refs.deployment_id,
                first.ref,
                _spec(refs),
                idempotency_key="stale-write",
            )
        assert (
            FoundryRepository(db)
            .current(refs.workspace, refs.deployment_id)
            .revision.ref
            == second.ref
        )


def test_changed_input_under_same_idempotency_key_conflicts(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        assert (
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                _spec(refs),
                idempotency_key="create-1",
            ).ref
            == first.ref
        )
        with pytest.raises(IdempotencyConflict):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                _spec(refs, provider=refs.second_provider),
                idempotency_key="create-1",
            )
        second = service.publish(
            actor,
            refs.workspace,
            refs.deployment_id,
            first.ref,
            _spec(refs, provider=refs.second_provider),
            idempotency_key="publish-after-replay",
        )
        assert (
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                _spec(refs),
                idempotency_key="create-1",
            )
            == first
        )
        assert (
            FoundryRepository(db).current(refs.workspace, refs.deployment_id).revision
            == second
        )
        request = db.first(
            FoundryRequest,
            "SELECT * FROM foundry_request WHERE workspace_id=? AND principal_id=? "
            "AND idempotency_key=?",
            [str(refs.workspace.root), str(actor.principal_id), "create-1"],
        )
        result = json.loads(request.result_json)
        assert result["ref"]["revision_id"] == first.ref.revision_id.root
        assert result["sequence"] == first.sequence
        assert (
            result["specification"]["bindings"][0]["provider"]
            == json.loads(first.model_dump_json())["specification"]["bindings"][0][
                "provider"
            ]
        )
        audit = db.first(
            FoundryAudit,
            "SELECT * FROM foundry_audit WHERE deployment_id=?",
            [str(refs.deployment_id.root)],
        )
        assert audit.foundry_request_id == request.id
        assert (
            len(
                db.all(
                    FoundryRequest,
                    where="workspace_id=? AND principal_id=? AND idempotency_key=?",
                    values=[
                        str(refs.workspace.root),
                        str(actor.principal_id),
                        "create-1",
                    ],
                )
            )
            == 1
        )
        other_actor = Actor(principal_id=_uuid())
        other_deployment = DeploymentId(_uuid())
        service.create(
            other_actor,
            refs.workspace,
            other_deployment,
            _spec(refs),
            idempotency_key="create-1",
        )
        assert (
            len(
                db.all(
                    FoundryRequest,
                    where="workspace_id=? AND idempotency_key=?",
                    values=[str(refs.workspace.root), "create-1"],
                )
            )
            == 2
        )


def test_publish_rechecks_revoked_references_after_workspace_lock(
    database_location, monkeypatch
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, authorization = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        repository = service._repository
        lock_workspace = repository._lock_workspace

        def lock_then_revoke(workspace_id):
            lock_workspace(workspace_id)
            authorization.revoked_references.add(refs.second_provider)

        monkeypatch.setattr(repository, "_lock_workspace", lock_then_revoke)
        with pytest.raises(AccessDenied, match="Reference unavailable"):
            service.publish(
                actor,
                refs.workspace,
                refs.deployment_id,
                first.ref,
                _spec(refs, provider=refs.second_provider),
                idempotency_key="publish-revoked-in-transaction",
            )
        assert (
            FoundryRepository(db)
            .current(refs.workspace, refs.deployment_id)
            .revision.ref
            == first.ref
        )
        assert len(db.all(FoundryDeploymentRevision)) == 1
        assert len(db.all(FoundryRequest)) == 1
        assert len(db.all(FoundryAudit)) == 1


def test_idempotent_replay_rechecks_revoked_references_after_workspace_lock(
    database_location, monkeypatch
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, authorization = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        repository = service._repository
        lock_workspace = repository._lock_workspace

        def lock_then_revoke(workspace_id):
            lock_workspace(workspace_id)
            authorization.revoked_references.add(refs.provider)

        monkeypatch.setattr(repository, "_lock_workspace", lock_then_revoke)
        with pytest.raises(AccessDenied, match="Reference unavailable"):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                _spec(refs),
                idempotency_key="create-1",
            )
        assert (
            FoundryRepository(db)
            .current(refs.workspace, refs.deployment_id)
            .revision.ref
            == first.ref
        )
        assert len(db.all(FoundryDeploymentRevision)) == 1
        assert len(db.all(FoundryRequest)) == 1
        assert len(db.all(FoundryAudit)) == 1


def test_publish_revalidates_admitted_packages_after_workspace_lock(
    database_location, monkeypatch
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, package_port, _ = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        repository = service._repository
        lock_workspace = repository._lock_workspace

        def lock_then_remove_admission(workspace_id):
            lock_workspace(workspace_id)
            package_port.package_refs.clear()

        monkeypatch.setattr(repository, "_lock_workspace", lock_then_remove_admission)
        with pytest.raises(AccessDenied, match="Package Revision unavailable"):
            service.publish(
                actor,
                refs.workspace,
                refs.deployment_id,
                first.ref,
                _spec(refs, provider=refs.second_provider),
                idempotency_key="publish-package-revoked-in-transaction",
            )
        assert (
            FoundryRepository(db)
            .current(refs.workspace, refs.deployment_id)
            .revision.ref
            == first.ref
        )
        assert len(db.all(FoundryDeploymentRevision)) == 1
        assert len(db.all(FoundryRequest)) == 1
        assert len(db.all(FoundryAudit)) == 1


def test_failed_activation_rolls_back_all_rows_and_reopens_cleanly(
    database_location, monkeypatch
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    path = database_location
    with _runtime_database(path, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        repository = service._repository

        def fail_after_head_update(*args, **kwargs):
            raise RuntimeError("injected activation failure")

        monkeypatch.setattr(repository, "_append_audit", fail_after_head_update)
        with pytest.raises(RuntimeError, match="injected activation failure"):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                _spec(refs),
                idempotency_key="transaction-failure",
            )
        assert db.all(FoundryDeploymentRevision) == []
        assert db.all(FoundryRequest) == []
        assert db.all(FoundryDeploymentHead) == []
        assert db.all(FoundryAudit) == []

    restarted = FoundryRepository(Database(path))
    assert restarted.current(refs.workspace, refs.deployment_id) is None


def test_restart_preserves_exact_revision_and_canonical_bindings(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    path = database_location
    with _runtime_database(path, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
    restarted = FoundryRepository(Database(path))
    reloaded = restarted.get_revision(first.ref)
    assert reloaded.revision == first
    assert reloaded.revision.specification.bindings[0].provider == refs.provider
    assert reloaded.execution_snapshots


def test_active_pointer_to_missing_revision_is_reported_as_corruption(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        with db.transaction():
            db.execute(
                "UPDATE foundry_deployment_head SET active_revision_id=? "
                "WHERE workspace_id=? AND deployment_id=?",
                [
                    _digest("f"),
                    str(refs.workspace.root),
                    str(refs.deployment_id.root),
                ],
            )
        with pytest.raises(RepositoryCorruption, match="active Deployment revision"):
            FoundryRepository(db).current(refs.workspace, refs.deployment_id)


def test_revoked_binding_reference_is_rechecked_before_run_resolution(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, authorization = _service(db, refs)
        service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        authorization.revoked_references.add(refs.provider)
        with pytest.raises(AccessDenied, match="Reference unavailable"):
            service.resolve(actor, refs.workspace, refs.deployment_id, refs.capability)


def test_runtime_plan_is_revalidated_before_snapshot_admission(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, package_port, _ = _service(db, refs)
        service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        package_port.plans[refs.plan] = SimpleNamespace(
            ref=refs.plan,
            runtime_kind="test/changed-after-activation",
            capabilities=(refs.capability,),
        )
        with pytest.raises(AccessDenied, match="Execution snapshot unavailable"):
            service.resolve(actor, refs.workspace, refs.deployment_id, refs.capability)


def test_empty_persisted_snapshot_map_grants_no_execution_authority(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        created = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        with db.transaction():
            db.execute(
                "UPDATE foundry_deployment_revision SET snapshots_json='{}' "
                "WHERE workspace_id=? AND deployment_id=? AND revision_id=?",
                [
                    str(refs.workspace.root),
                    str(refs.deployment_id.root),
                    created.ref.revision_id.root,
                ],
            )
        with pytest.raises(AccessDenied, match="Execution snapshot unavailable"):
            service.resolve(actor, refs.workspace, refs.deployment_id, refs.capability)


def test_rollback_publishes_a_new_revision_from_an_exact_retained_target(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        second = service.publish(
            actor,
            refs.workspace,
            refs.deployment_id,
            first.ref,
            _spec(refs, provider=refs.second_provider),
            idempotency_key="publish-2",
        )
        rolled_back = service.rollback(
            actor,
            refs.workspace,
            refs.deployment_id,
            second.ref,
            first.ref,
            idempotency_key="rollback-3",
        )
        assert rolled_back.sequence == 3
        assert rolled_back.previous_revision == second.ref
        assert rolled_back.rollback_of == first.ref
        assert rolled_back.specification == first.specification


def test_caller_selected_plan_has_no_implicit_default_fallback(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    specification = _spec(refs).model_copy(
        update={
            "capability_plans": (
                CapabilityPlanPolicy(
                    capability=refs.capability,
                    mode="caller-may-choose",
                    allowed_plans=(refs.plan,),
                    default_plan=None,
                ),
            )
        }
    )
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            specification,
            idempotency_key="create-1",
        )
        with pytest.raises(AccessDenied, match="Runtime Plan unavailable"):
            service.resolve(actor, refs.workspace, refs.deployment_id, refs.capability)


def test_in_flight_run_keeps_its_exact_snapshot_and_binding_revision(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        resolved_first = service.resolve(
            actor, refs.workspace, refs.deployment_id, refs.capability
        )
        run_service, _ = _action_and_grant(db, refs, resolved_first.snapshot, actor)
        run = run_service.admit(actor, resolved_first.snapshot, {}, "run-1")
        pin = db.first(RunPin, "SELECT * FROM run_pin WHERE id=?", [run.id])

        second = service.publish(
            actor,
            refs.workspace,
            refs.deployment_id,
            first.ref,
            _spec(refs, provider=refs.second_provider),
            idempotency_key="publish-2",
        )
        resolved_current = service.resolve(
            actor, refs.workspace, refs.deployment_id, refs.capability
        )
        pinned = run_service._pinned(pin)
        pinned_revision = FoundryRepository(db).get_revision(pinned.deployment)

        assert resolved_current.snapshot.deployment == second.ref
        assert pinned == resolved_first.snapshot
        assert (
            pinned_revision.revision.specification.bindings[0].provider == refs.provider
        )
        assert resolved_current.bindings[0].provider == refs.second_provider
        assert (
            db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).action_id
            == "test-action-1"
        )


def _ui_spec(refs, title="Empty Canvas"):
    from actions.canvas_contract import validate_canvas_spec

    from actions.server.deployments.foundry_values import canvas_revision_digest
    from actions.server.run_outputs.types import CanvasApplicationRef

    spec = validate_canvas_spec(
        {
            "schemaVersion": "actions.canvas-spec/v1",
            "title": title,
            "visibility": ["model", "app"],
            "bindingIds": [],
            "root": {"type": "stack", "id": "main", "children": []},
        }
    )
    return DeploymentSpecification(
        canvas_spec=spec,
        canvas_application=CanvasApplicationRef(
            workspace_id=str(refs.workspace.root),
            app_id=str(refs.deployment_id.root),
            revision_id=canvas_revision_digest(spec, (), ()),
        ),
    )


def test_ui_only_deployment_needs_no_package_and_cannot_resolve_execution(
    database_location,
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, ()) as db:
        service, _, _ = _service(db, refs)
        specification = _ui_spec(refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            specification,
            idempotency_key="explicit-ui-release",
        )
        assert first.specification.package_revisions == ()
        assert first.specification.canvas_spec.title == "Empty Canvas"
        assert db.all(FoundryPackageRevision) == []
        assert db.first(FoundryDeploymentRevision).foundry_package_revision_id is None
        assert (
            FoundryRepository(db)
            .current(refs.workspace, refs.deployment_id)
            .execution_snapshots
            == ()
        )
        with pytest.raises(AccessDenied):
            service.resolve(actor, refs.workspace, refs.deployment_id, refs.capability)
        assert (
            FoundryRepository(Database(database_location))
            .current(refs.workspace, refs.deployment_id)
            .revision
            == first
        )
        assert (
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                specification,
                idempotency_key="explicit-ui-release",
            )
            == first
        )
        assert len(db.all(FoundryAudit)) == 1


def test_ui_only_selection_rejects_missing_view_and_execution_profiles():
    refs = _refs()
    with pytest.raises(ValueError):
        DeploymentSpecification()
    value = _ui_spec(refs).model_dump(mode="json", by_alias=True)
    value["worker"] = refs.worker.model_dump(mode="json")
    with pytest.raises(ValueError):
        DeploymentSpecification.model_validate_json(json.dumps(value))


@pytest.mark.parametrize("same_key", [False, True])
def test_concurrent_publish_is_one_cas_with_audit_continuity(
    database_location, same_key
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create",
        )
        barrier = Barrier(2)

        def publish(index):
            own = Database(database_location)
            with own.connect():
                own.initialize(get_all_model_classes())
                contender, _, _ = _service(own, refs)
                barrier.wait(timeout=20)
                try:
                    return contender.publish(
                        actor,
                        refs.workspace,
                        refs.deployment_id,
                        first.ref,
                        _spec(refs, provider=refs.second_provider),
                        idempotency_key="same-request"
                        if same_key
                        else f"contender-{index}",
                    )
                except StaleDeploymentRevision:
                    return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(publish, range(2)))
        assert sum(result is not None for result in results) == (2 if same_key else 1)
        assert len({result.ref for result in results if result is not None}) == 1
        current = FoundryRepository(db).current(refs.workspace, refs.deployment_id)
        assert current.revision.ref == next(
            result.ref for result in results if result is not None
        )
        assert len(db.all(FoundryDeploymentRevision)) == 2
        assert len(db.all(FoundryRequest)) == 2
        assert len(db.all(FoundryAudit)) == 2
        assert db.first(FoundryDeploymentHead).lock_version == 2


def test_actual_fresh_process_reads_exact_immutable_selection(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, ()) as db:
        service, _, _ = _service(db, refs)
        first = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _ui_spec(refs),
            idempotency_key="create-ui",
        )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["ACTIONS_OWNED_FOUNDRY_DB"] = str(database_location)
    environment["ACTIONS_OWNED_FOUNDRY_REF"] = first.ref.model_dump_json()
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import json, os
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.deployments.ids import DeploymentRevisionRef
from actions.server.deployments.foundry_repository import FoundryRepository
ref = DeploymentRevisionRef.model_validate_json(os.environ['ACTIONS_OWNED_FOUNDRY_REF'])
db = Database(os.environ['ACTIONS_OWNED_FOUNDRY_DB'])
with db.connect():
    db.initialize(get_all_model_classes())
    stored = FoundryRepository(db).current(ref.workspace_id, ref.deployment_id)
    assert stored.revision.ref == ref
    assert stored.execution_snapshots == ()
    print(stored.revision.model_dump_json(by_alias=True))
""",
        ],
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    assert json.loads(result.stdout) == first.model_dump(mode="json", by_alias=True)


def test_backend_snapshot_pins_canvas_source_and_rejects_altered_spec(
    database_location,
):
    from actions.canvas_contract import validate_canvas_spec

    from actions.server.deployments.foundry_values import (
        CanvasCapabilityBinding,
        canvas_revision_digest,
    )
    from actions.server.run_outputs.types import CanvasApplicationRef

    refs = _refs()
    actor = Actor(principal_id=_uuid())
    spec = validate_canvas_spec(
        {
            "schemaVersion": "actions.canvas-spec/v1",
            "title": "Backend view",
            "visibility": ["app"],
            "bindingIds": ["lookup"],
            "root": {"type": "status", "id": "status", "bindingId": "lookup"},
        }
    )
    binding = CanvasCapabilityBinding(binding_id="lookup", capability=refs.capability)
    app = CanvasApplicationRef(
        workspace_id=str(refs.workspace.root),
        app_id=str(refs.deployment_id.root),
        revision_id=canvas_revision_digest(spec, (binding,), (refs.package,)),
    )
    values = _spec(refs).model_dump(mode="json", by_alias=True)
    values.update(
        canvas_spec=spec.model_dump(mode="json", by_alias=True),
        canvas_application=app.model_dump(mode="json"),
        canvas_bindings=[binding.model_dump(mode="json")],
    )
    selection = DeploymentSpecification.model_validate_json(json.dumps(values))
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        revision = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            selection,
            idempotency_key="exact-source",
        )
        resolved = service.resolve(
            actor, refs.workspace, refs.deployment_id, refs.capability
        )
        assert resolved.snapshot.canvas_application == app
        assert resolved.snapshot.deployment == revision.ref
        values["canvas_spec"]["title"] = "Altered after admission"
        with pytest.raises(ValueError, match="differs from immutable source"):
            DeploymentSpecification.model_validate_json(json.dumps(values))
        assert len(db.all(FoundryDeploymentRevision)) == 1


def test_staged_snapshot_is_not_execution_authority(database_location):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _, _ = _service(db, refs)
        repository = FoundryRepository(db)
        staged = repository.stage(
            refs.workspace,
            refs.deployment_id,
            None,
            _spec(refs),
            principal_id=actor.principal_id,
            operation="canvas.create",
            idempotency_key="stage",
            input_digest=_digest("a"),
            preflight=lambda: None,
            snapshot_builder=service._execution_snapshots,
        )
        assert repository.get_revision(staged.ref).execution_snapshots
        assert repository.current(refs.workspace, refs.deployment_id) is None
        with pytest.raises(AccessDenied, match="not been explicitly activated"):
            service.resolve(
                actor,
                refs.workspace,
                refs.deployment_id,
                refs.capability,
                revision=staged.ref,
            )
        activated = repository.activate_existing(
            staged.ref,
            None,
            principal_id=actor.principal_id,
            operation="canvas.release",
            idempotency_key="release",
            input_digest=_digest("b"),
            preflight=lambda revision: service._validate_package_contracts(
                revision.specification
            ),
            snapshot_builder=service._execution_snapshots,
        )
        assert activated.ref == staged.ref
        assert (
            service.resolve(
                actor, refs.workspace, refs.deployment_id, refs.capability
            ).snapshot.deployment
            == staged.ref
        )
