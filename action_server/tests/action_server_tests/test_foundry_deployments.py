"""Focused #129 Deployment resolver tests on the existing Runtime Database."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from uuid import uuid4

import pytest

from actions.server._database import Database
from actions.server._models import Action, ActionPackage, Run, create_db
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
from actions.server.run_outputs.models import RunPin
from actions.server.run_outputs.service import RunOutputControlPlane, RunOutputService
from actions.server.run_outputs.types import Actor


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
        if ref != self.refs.package:
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
        if workspace_id not in self.allowed_workspaces:
            raise AccessDenied("Reference unavailable or not authorized")


class _ExecutionPort:
    def action_id_for(self, ref):
        return "test-action-1"


@contextmanager
def _runtime_database(path: Path, workspace_id: WorkspaceId) -> Iterator[Database]:
    """Use the real Runtime schema plus test-only proposed Deployment tables."""
    with create_db(path) as db:
        with db.connect():
            with db.transaction():
                db.execute(
                    "INSERT INTO workspace (id, state, lock_version) "
                    "VALUES (?, 'active', 0)",
                    [str(workspace_id.root)],
                )
                for statement in _TEST_DEPLOYMENT_DDL:
                    db.execute(statement)
        yield db


_TEST_DEPLOYMENT_DDL = (
    "CREATE TABLE deployment (workspace_id TEXT NOT NULL, deployment_id TEXT NOT NULL, "
    "current_revision_id TEXT, state TEXT NOT NULL, PRIMARY KEY(workspace_id, deployment_id))",
    "CREATE TABLE deployment_revision (workspace_id TEXT NOT NULL, deployment_id TEXT NOT NULL, "
    "revision_id TEXT NOT NULL, sequence INTEGER NOT NULL, previous_revision_id TEXT, "
    "rollback_of_revision_id TEXT, change_kind TEXT NOT NULL, specification_json TEXT NOT NULL, "
    "PRIMARY KEY(workspace_id, deployment_id, revision_id), "
    "UNIQUE(workspace_id, deployment_id, sequence))",
    "CREATE TABLE deployment_revision_package (workspace_id TEXT NOT NULL, deployment_id TEXT NOT NULL, "
    "revision_id TEXT NOT NULL, package_id TEXT NOT NULL, package_revision_id TEXT NOT NULL, "
    "PRIMARY KEY(workspace_id, deployment_id, revision_id, package_id))",
    "CREATE TABLE deployment_revision_binding (workspace_id TEXT NOT NULL, deployment_id TEXT NOT NULL, "
    "revision_id TEXT NOT NULL, package_id TEXT NOT NULL, package_revision_id TEXT NOT NULL, "
    "binding_requirement_id TEXT NOT NULL, provider_profile_id TEXT NOT NULL, "
    "provider_profile_revision_id TEXT NOT NULL, PRIMARY KEY(workspace_id, deployment_id, "
    "revision_id, package_id, package_revision_id, binding_requirement_id))",
    "CREATE TABLE deployment_revision_worker_profile_ref (workspace_id TEXT NOT NULL, "
    "deployment_id TEXT NOT NULL, revision_id TEXT NOT NULL, worker_profile_id TEXT NOT NULL, "
    "worker_profile_revision_id TEXT NOT NULL, PRIMARY KEY(workspace_id, deployment_id, revision_id))",
    "CREATE TABLE deployment_revision_policy_ref (workspace_id TEXT NOT NULL, deployment_id TEXT NOT NULL, "
    "revision_id TEXT NOT NULL, policy_id TEXT NOT NULL, policy_revision_id TEXT NOT NULL, "
    "PRIMARY KEY(workspace_id, deployment_id, revision_id))",
    "CREATE TABLE deployment_revision_output_provider_ref (workspace_id TEXT NOT NULL, "
    "deployment_id TEXT NOT NULL, revision_id TEXT NOT NULL, provider_profile_id TEXT NOT NULL, "
    "provider_profile_revision_id TEXT NOT NULL, PRIMARY KEY(workspace_id, deployment_id, revision_id))",
    "CREATE TABLE deployment_revision_request (workspace_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, "
    "deployment_id TEXT NOT NULL, operation_kind TEXT NOT NULL, request_digest TEXT NOT NULL, "
    "parent_revision_id TEXT, result_revision_id TEXT NOT NULL, PRIMARY KEY(workspace_id, idempotency_key))",
)


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


def test_resolution_requires_the_declared_capability_and_binding_ports(tmp_path):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(tmp_path / "runtime.db", refs.workspace) as db:
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


def test_cross_workspace_capability_is_denied_before_execution_resolution(tmp_path):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(tmp_path / "runtime.db", refs.workspace) as db:
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


def test_resolution_returns_only_bindings_for_the_selected_capability(tmp_path):
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
    with _runtime_database(tmp_path / "runtime.db", refs.workspace) as db:
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


def test_compare_and_swap_rejects_a_stale_revision(tmp_path):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(tmp_path / "runtime.db", refs.workspace) as db:
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
            FoundryRepository(db).current(refs.workspace, refs.deployment_id).ref
            == second.ref
        )


def test_changed_input_under_same_idempotency_key_conflicts(tmp_path):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(tmp_path / "runtime.db", refs.workspace) as db:
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


def test_failed_activation_rolls_back_all_rows_and_reopens_cleanly(
    tmp_path, monkeypatch
):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    path = tmp_path / "runtime.db"
    with _runtime_database(path, refs.workspace) as db:
        service, _, _ = _service(db, refs)
        repository = service._repository

        def fail_after_revision_insert(*args, **kwargs):
            raise RuntimeError("injected activation failure")

        monkeypatch.setattr(repository, "_cas_activate", fail_after_revision_insert)
        with pytest.raises(RuntimeError, match="injected activation failure"):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                _spec(refs),
                idempotency_key="transaction-failure",
            )
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM deployment_revision")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT COUNT(*) FROM deployment_revision_request")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT COUNT(*) FROM deployment")
            assert cursor.fetchone()[0] == 0

    restarted = FoundryRepository(Database(path))
    assert restarted.current(refs.workspace, refs.deployment_id) is None


def test_restart_preserves_exact_revision_and_canonical_bindings(tmp_path):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    path = tmp_path / "runtime.db"
    with _runtime_database(path, refs.workspace) as db:
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
    assert reloaded == first
    assert reloaded.specification.bindings[0].provider == refs.provider


def test_active_pointer_to_missing_revision_is_reported_as_corruption(tmp_path):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(tmp_path / "runtime.db", refs.workspace) as db:
        service, _, _ = _service(db, refs)
        service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            _spec(refs),
            idempotency_key="create-1",
        )
        db.execute(
            "UPDATE deployment SET current_revision_id=? "
            "WHERE workspace_id=? AND deployment_id=?",
            [
                _digest("f"),
                str(refs.workspace.root),
                str(refs.deployment_id.root),
            ],
        )
        with pytest.raises(RepositoryCorruption, match="active Deployment revision"):
            FoundryRepository(db).current(refs.workspace, refs.deployment_id)


def test_rollback_publishes_a_new_revision_from_an_exact_retained_target(tmp_path):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(tmp_path / "runtime.db", refs.workspace) as db:
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


def test_caller_selected_plan_has_no_implicit_default_fallback(tmp_path):
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
    with _runtime_database(tmp_path / "runtime.db", refs.workspace) as db:
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


def test_in_flight_run_keeps_its_exact_snapshot_and_binding_revision(tmp_path):
    refs = _refs()
    actor = Actor(principal_id=_uuid())
    with _runtime_database(tmp_path / "runtime.db", refs.workspace) as db:
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
        assert pinned_revision.specification.bindings[0].provider == refs.provider
        assert resolved_current.bindings[0].provider == refs.second_provider
        assert (
            db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).action_id
            == "test-action-1"
        )
