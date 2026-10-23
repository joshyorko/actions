"""Authorized Deployment activation and exact immutable execution resolution."""

from __future__ import annotations

import re
from typing import Any

from actions.server.deployments.ids import (
    BindingRequirementRef,
    CapabilityRef,
    DeploymentId,
    DeploymentRevisionRef,
    PackageRevisionRef,
    RuntimePlanRef,
    WorkspaceId,
    WorkspaceScopedRef,
    require_package_scope,
    require_workspace_scope,
)
from actions.server.run_outputs.types import Actor, ExecutionSnapshot

from .foundry_repository import FoundryRepository, request_digest
from .foundry_values import (
    AccessDenied,
    CapabilityExecutionPort,
    CapabilityPlanPolicy,
    DeploymentExecutionSnapshot,
    DeploymentRevision,
    DeploymentSpecification,
    OperationKind,
    PackageContractError,
    PackageRevisionPort,
    Permission,
    ResolvedDeploymentExecution,
    WorkspaceAuthorizationPort,
)

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class FoundryDeploymentService:
    """Use injected Runtime authority ports; fail closed when a port is absent."""

    def __init__(
        self,
        repository: FoundryRepository,
        packages: PackageRevisionPort,
        authorization: WorkspaceAuthorizationPort,
        execution: CapabilityExecutionPort,
    ):
        if (
            repository is None
            or packages is None
            or authorization is None
            or execution is None
        ):
            raise TypeError("all Deployment authority ports are required")
        self._repository = repository
        self._packages = packages
        self._authorization = authorization
        self._execution = execution

    def create(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        specification: DeploymentSpecification,
        *,
        idempotency_key: str,
    ) -> DeploymentRevision:
        return self._activate(
            actor,
            workspace_id,
            deployment_id,
            specification,
            expected_revision=None,
            idempotency_key=idempotency_key,
            operation_kind="create",
        )

    def publish(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        expected_revision: DeploymentRevisionRef,
        specification: DeploymentSpecification,
        *,
        idempotency_key: str,
    ) -> DeploymentRevision:
        return self._activate(
            actor,
            workspace_id,
            deployment_id,
            specification,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            operation_kind="publish",
        )

    def rollback(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        expected_revision: DeploymentRevisionRef,
        target_revision: DeploymentRevisionRef,
        *,
        idempotency_key: str,
    ) -> DeploymentRevision:
        actor, workspace_id, deployment_id = self._owner(
            actor, workspace_id, deployment_id
        )
        self._require_workspace(actor, workspace_id, "deploy")
        self._authorization.require_deployment(
            actor, workspace_id, deployment_id, "deploy"
        )
        self._require_owner_ref(workspace_id, deployment_id, expected_revision)
        self._require_owner_ref(workspace_id, deployment_id, target_revision)
        self._authorization.require_reference(actor, expected_revision, "deploy")
        self._authorization.require_reference(actor, target_revision, "deploy")
        target = self._repository.get_revision(target_revision)
        if target is None:
            raise AccessDenied("Deployment unavailable or not authorized")
        self._authorize_specification(
            actor, workspace_id, target.revision.specification, "deploy"
        )
        self._validate_package_contracts(target.revision.specification)
        return self._activate(
            actor,
            workspace_id,
            deployment_id,
            target.revision.specification,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            operation_kind="rollback",
            rollback_of=target_revision,
        )

    def resolve(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        capability: CapabilityRef,
        *,
        revision: DeploymentRevisionRef | None = None,
        runtime_plan: RuntimePlanRef | None = None,
    ) -> ResolvedDeploymentExecution:
        actor, workspace_id, deployment_id = self._owner(
            actor, workspace_id, deployment_id
        )
        self._require_workspace(actor, workspace_id, "execute")
        self._authorization.require_deployment(
            actor, workspace_id, deployment_id, "execute"
        )
        capability = CapabilityRef.model_validate(capability)
        if runtime_plan is not None:
            runtime_plan = RuntimePlanRef.model_validate(runtime_plan)
        if revision is None:
            stored = self._repository.current(workspace_id, deployment_id)
        else:
            revision = DeploymentRevisionRef.model_validate(revision)
            self._require_owner_ref(workspace_id, deployment_id, revision)
            self._authorization.require_reference(actor, revision, "execute")
            stored = self._repository.get_revision(revision)
        if stored is None:
            raise AccessDenied("Deployment unavailable or not authorized")
        revision_record = stored.revision
        self._authorization.require_reference(actor, revision_record.ref, "execute")
        specification = revision_record.specification
        try:
            require_workspace_scope(capability, workspace_id)
            if capability.package_revision not in specification.package_revisions:
                raise AccessDenied("Capability unavailable or not authorized")
            self._authorization.require_reference(
                actor, capability.package_revision, "execute"
            )
            self._authorization.require_reference(actor, capability, "execute")
            for package_ref in specification.package_revisions:
                self._authorization.require_reference(actor, package_ref, "execute")
                self._packages.require_revision(package_ref)
            declaration = self._capability(capability)
            plan_policy = self._plan_policy(specification, capability)
            selected_ref = plan_policy.select(runtime_plan)
            declared_plans = self._validated_package_refs(
                declaration.runtime_plans, capability.package_revision
            )
            if selected_ref not in declared_plans:
                raise AccessDenied("Runtime Plan unavailable or not authorized")
            self._authorization.require_reference(actor, selected_ref, "execute")
            plan = self._plan(selected_ref)
            self._validate_runtime_plan(plan, selected_ref, capability)
            persisted_snapshot = next(
                (
                    entry.snapshot
                    for entry in stored.execution_snapshots
                    if entry.capability == capability
                    and entry.runtime_plan == selected_ref
                ),
                None,
            )
            if persisted_snapshot is None:
                raise AccessDenied("Execution snapshot unavailable or not authorized")
            current_snapshot = self._execution_snapshot(
                revision_record, capability, selected_ref, declaration, plan
            )
            if current_snapshot != persisted_snapshot:
                raise AccessDenied("Execution snapshot unavailable or not authorized")
            binding_requirements = self._validated_package_refs(
                declaration.binding_requirements,
                capability.package_revision,
                binding=True,
            )
            for requirement_ref in binding_requirements:
                requirement = self._packages.get_binding_requirement(requirement_ref)
                if requirement is None or requirement.ref != requirement_ref:
                    raise AccessDenied(
                        "Binding requirement unavailable or not authorized"
                    )
                self._authorization.require_reference(actor, requirement_ref, "execute")
            selected_requirement_set = set(binding_requirements)
            assignment_by_requirement = {
                binding.requirement: binding
                for binding in specification.bindings
                if binding.requirement in selected_requirement_set
            }
            if set(assignment_by_requirement) != selected_requirement_set:
                raise AccessDenied("Deployment bindings unavailable or incomplete")
            bindings = tuple(
                assignment_by_requirement[ref] for ref in binding_requirements
            )
            for binding in bindings:
                self._authorization.require_reference(
                    actor, binding.provider, "execute"
                )
            for ref in (
                specification.worker,
                specification.policy,
                specification.output_provider,
            ):
                if ref is None:
                    raise AccessDenied(
                        "Execution profile unavailable or not authorized"
                    )
                self._authorization.require_reference(actor, ref, "execute")
            return ResolvedDeploymentExecution(
                revision=revision_record,
                snapshot=persisted_snapshot,
                binding_requirements=binding_requirements,
                bindings=bindings,
            )
        except AccessDenied:
            raise
        except (TypeError, ValueError) as exc:
            raise AccessDenied("Capability unavailable or not authorized") from exc

    def _activate(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        specification: DeploymentSpecification,
        *,
        expected_revision: DeploymentRevisionRef | None,
        idempotency_key: str,
        operation_kind: OperationKind,
        rollback_of: DeploymentRevisionRef | None = None,
    ) -> DeploymentRevision:
        actor, workspace_id, deployment_id = self._owner(
            actor, workspace_id, deployment_id
        )
        self._require_workspace(actor, workspace_id, "deploy")
        if not isinstance(specification, DeploymentSpecification):
            raise TypeError("specification must be DeploymentSpecification")
        specification = DeploymentSpecification.model_validate(specification)
        if specification.workspace_id != workspace_id:
            raise AccessDenied("Deployment unavailable or not authorized")
        if (
            specification.canvas_application is not None
            and specification.canvas_application.app_id != str(deployment_id.root)
        ):
            raise AccessDenied("Canvas application unavailable or not authorized")
        self._authorization.require_deployment(
            actor, workspace_id, deployment_id, "deploy"
        )
        if expected_revision is not None:
            expected_revision = DeploymentRevisionRef.model_validate(expected_revision)
            self._require_owner_ref(workspace_id, deployment_id, expected_revision)
            self._authorization.require_reference(actor, expected_revision, "deploy")
        if rollback_of is not None:
            rollback_of = DeploymentRevisionRef.model_validate(rollback_of)
            self._require_owner_ref(workspace_id, deployment_id, rollback_of)
            self._authorization.require_reference(actor, rollback_of, "deploy")
        _validate_idempotency_key(idempotency_key)
        self._authorize_specification(actor, workspace_id, specification, "deploy")
        self._validate_package_contracts(specification)

        def preflight() -> None:
            """Recheck authorization and package contracts under the Workspace lock."""
            self._require_workspace(actor, workspace_id, "deploy")
            self._authorization.require_deployment(
                actor, workspace_id, deployment_id, "deploy"
            )
            if expected_revision is not None:
                self._authorization.require_reference(
                    actor, expected_revision, "deploy"
                )
            if rollback_of is not None:
                self._authorization.require_reference(actor, rollback_of, "deploy")
            self._authorize_specification(actor, workspace_id, specification, "deploy")
            self._validate_package_contracts(specification)

        digest = request_digest(
            workspace_id,
            deployment_id,
            expected_revision,
            specification,
            operation_kind,
            rollback_of,
        )
        return self._repository.activate(
            workspace_id,
            deployment_id,
            expected_revision,
            specification,
            idempotency_key=idempotency_key,
            input_digest=digest,
            operation_kind=operation_kind,
            principal_id=str(actor.principal_id),
            preflight=preflight,
            snapshot_builder=self._execution_snapshots,
            rollback_of=rollback_of,
        )

    def _execution_snapshots(
        self, revision: DeploymentRevision
    ) -> tuple[DeploymentExecutionSnapshot, ...]:
        """Snapshot each explicitly allowed Capability/Plan pair at activation."""
        self._validate_package_contracts(revision.specification)
        snapshots: list[DeploymentExecutionSnapshot] = []
        for policy in revision.specification.capability_plans:
            declaration = self._capability(policy.capability)
            for plan_ref in policy.allowed_plans:
                plan = self._plan(plan_ref)
                self._validate_runtime_plan(plan, plan_ref, policy.capability)
                snapshots.append(
                    DeploymentExecutionSnapshot(
                        capability=policy.capability,
                        runtime_plan=plan_ref,
                        snapshot=self._execution_snapshot(
                            revision,
                            policy.capability,
                            plan_ref,
                            declaration,
                            plan,
                        ),
                    )
                )
        return tuple(snapshots)

    def _execution_snapshot(
        self,
        revision: DeploymentRevision,
        capability: CapabilityRef,
        runtime_plan: RuntimePlanRef,
        capability_declaration: Any,
        plan_declaration: Any,
    ) -> ExecutionSnapshot:
        action_id = self._execution.action_id_for(capability)
        if not isinstance(action_id, str) or not action_id or len(action_id) > 128:
            raise PackageContractError("Runtime capability identity is invalid")
        specification = revision.specification
        if (
            specification.worker is None
            or specification.policy is None
            or specification.output_provider is None
        ):
            raise PackageContractError("UI-only revisions cannot admit execution")
        return ExecutionSnapshot(
            deployment=revision.ref,
            capability=capability,
            runtime_plan=runtime_plan,
            worker=specification.worker,
            policy=specification.policy,
            output_provider=specification.output_provider,
            canvas_application=specification.canvas_application,
            runtime_kind=_valid_runtime_kind(plan_declaration.runtime_kind),
            capability_schema_digest=_valid_digest(
                capability_declaration.schema_digest
            ),
            action_id=action_id,
        )

    def _authorize_specification(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        specification: DeploymentSpecification,
        permission: Permission,
    ) -> None:
        if specification.workspace_id != workspace_id:
            raise AccessDenied("Deployment unavailable or not authorized")
        refs: list[WorkspaceScopedRef] = list(specification.package_revisions)
        refs.extend(policy.capability for policy in specification.capability_plans)
        for plan_policy in specification.capability_plans:
            refs.extend(plan_policy.allowed_plans)
        refs.extend(binding.requirement for binding in specification.bindings)
        refs.extend(binding.provider for binding in specification.bindings)
        refs.extend(
            ref
            for ref in (
                specification.worker,
                specification.policy,
                specification.output_provider,
            )
            if ref is not None
        )
        for ref in refs:
            try:
                require_workspace_scope(ref, workspace_id)
            except (TypeError, ValueError) as exc:
                raise AccessDenied("Deployment unavailable or not authorized") from exc
            self._authorization.require_reference(actor, ref, permission)

    def _validate_package_contracts(
        self, specification: DeploymentSpecification
    ) -> None:
        for package_ref in specification.package_revisions:
            self._packages.require_revision(package_ref)

        declared_requirements: set[BindingRequirementRef] = set()
        declared_capabilities = {
            policy.capability: self._capability(policy.capability)
            for policy in specification.capability_plans
        }
        for policy in specification.capability_plans:
            declaration = declared_capabilities[policy.capability]
            _valid_digest(declaration.schema_digest)
            declared_plans = self._validated_package_refs(
                declaration.runtime_plans, policy.capability.package_revision
            )
            if not set(policy.allowed_plans).issubset(set(declared_plans)):
                raise PackageContractError(
                    "Deployment selected an undeclared Package Runtime Plan"
                )
            for plan_ref in policy.allowed_plans:
                self._validate_runtime_plan(
                    self._plan(plan_ref), plan_ref, policy.capability
                )
            for requirement_ref in self._validated_package_refs(
                declaration.binding_requirements,
                policy.capability.package_revision,
                binding=True,
            ):
                requirement = self._packages.get_binding_requirement(requirement_ref)
                if requirement is None or requirement.ref != requirement_ref:
                    raise AccessDenied(
                        "Binding requirement unavailable or not authorized"
                    )
                declared_requirements.add(requirement_ref)

        assigned = {binding.requirement for binding in specification.bindings}
        if assigned != declared_requirements:
            raise AccessDenied("Deployment bindings unavailable or incomplete")

    def _capability(self, ref: CapabilityRef) -> Any:
        declaration = self._packages.get_capability(ref)
        if declaration is None or declaration.ref != ref:
            raise AccessDenied("Capability unavailable or not authorized")
        return declaration

    def _plan(self, ref: RuntimePlanRef) -> Any:
        declaration = self._packages.get_runtime_plan(ref)
        if declaration is None or declaration.ref != ref:
            raise AccessDenied("Runtime Plan unavailable or not authorized")
        return declaration

    @staticmethod
    def _validate_runtime_plan(
        plan: Any, ref: RuntimePlanRef, capability: CapabilityRef
    ) -> None:
        try:
            require_package_scope(ref, capability.package_revision)
            plan_ref = RuntimePlanRef.model_validate(plan.ref)
            supported = tuple(
                CapabilityRef.model_validate(item) for item in plan.capabilities
            )
            if plan_ref != ref or capability not in supported:
                raise ValueError("Runtime Plan capability scope mismatch")
            _valid_runtime_kind(plan.runtime_kind)
        except (AttributeError, TypeError, ValueError) as exc:
            raise PackageContractError(
                "Package Runtime Plan declaration is invalid"
            ) from exc

    @staticmethod
    def _validated_package_refs(
        refs: Any,
        package_ref: PackageRevisionRef,
        *,
        binding: bool = False,
    ) -> tuple[Any, ...]:
        model = BindingRequirementRef if binding else RuntimePlanRef
        try:
            validated = tuple(model.model_validate(item) for item in refs)
            for ref in validated:
                require_package_scope(ref, package_ref)
            if len(set(validated)) != len(validated):
                raise ValueError("Package declaration contains duplicate references")
            return validated
        except (AttributeError, TypeError, ValueError) as exc:
            raise PackageContractError(
                "Package declaration references are invalid"
            ) from exc

    @staticmethod
    def _plan_policy(
        specification: DeploymentSpecification, capability: CapabilityRef
    ) -> CapabilityPlanPolicy:
        matches = [
            policy
            for policy in specification.capability_plans
            if policy.capability == capability
        ]
        if len(matches) != 1:
            raise AccessDenied("Capability unavailable or not authorized")
        return matches[0]

    def _require_workspace(
        self, actor: Actor, workspace_id: WorkspaceId, permission: Permission
    ) -> None:
        self._authorization.require_workspace(actor, workspace_id, permission)

    @staticmethod
    def _owner(
        actor: Actor, workspace_id: WorkspaceId, deployment_id: DeploymentId
    ) -> tuple[Actor, WorkspaceId, DeploymentId]:
        if not isinstance(actor, Actor):
            raise TypeError("actor must come from trusted authentication")
        actor = Actor.model_validate(actor)
        workspace_id = WorkspaceId.model_validate(workspace_id)
        deployment_id = DeploymentId.model_validate(deployment_id)
        return actor, workspace_id, deployment_id

    @staticmethod
    def _require_owner_ref(
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        ref: DeploymentRevisionRef,
    ) -> None:
        try:
            ref = DeploymentRevisionRef.model_validate(ref)
            if ref.workspace_id != workspace_id or ref.deployment_id != deployment_id:
                raise ValueError("Deployment revision is outside its owner")
        except (TypeError, ValueError) as exc:
            raise AccessDenied("Deployment unavailable or not authorized") from exc


def _valid_digest(value: str) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise PackageContractError("Package capability schema digest is invalid")
    return value


def _valid_runtime_kind(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise PackageContractError("Package Runtime Plan kind is invalid")
    return value


def _validate_idempotency_key(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("bounded idempotency key required")
    try:
        size = len(value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise ValueError("idempotency key must contain valid Unicode") from exc
    if not 1 <= size <= 256 or any(ord(character) < 0x20 for character in value):
        raise ValueError("idempotency key must be 1..256 UTF-8 bytes")
