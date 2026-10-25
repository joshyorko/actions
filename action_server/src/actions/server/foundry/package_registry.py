"""Trusted compiler admission into the common immutable Package SQL authority.

This adapter is host-injected. Compiler objects are never admitted from client
JSON, and RCC execution requires the host's explicit trusted-developer policy.
The private output provider stores measured source bytes; SQL owns admission.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Any
from uuid import uuid4, uuid5

from actions.server._database import Database
from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.capability_bundle import (
    CompiledCapabilityBundle,
    decode_bundle,
    select_capability,
    verify_bundle,
)
from actions.server.deployments.capability_bundle_compiler import (
    BundleCompilationOutcome,
    BundleCompilationPolicy,
    compile_generated_python_bundle,
    verify_bundle_compilation_outcome,
)
from actions.server.deployments.foundry_repository import (
    FoundryRepository,
    _transaction,
)
from actions.server.deployments.foundry_values import AccessDenied, WorkItemDeclaration
from actions.server.deployments.ids import (
    BindingRequirementRef,
    CapabilityId,
    CapabilityRef,
    DeploymentId,
    PackageId,
    PackageRevisionRef,
    PlanDigest,
    RuntimePlanRef,
    WorkspaceId,
    WorkspaceScopedRef,
)
from actions.server.deployments.logical_bindings import LogicalBindingRequirement
from actions.server.deployments.package_revision_compiler import (
    CompilationOutcome,
    CompilationReceipt,
    CompiledPackageRevision,
    PackageBuildExecutor,
    PackageCompilationPolicy,
    RuntimePlanHeader,
    TrustedDeveloperExecutionAdmission,
    compile_generated_python_action,
    snapshot_source_entries,
    verify_compilation_outcome,
)
from actions.server.deployments.source_manifest import SuppliedSourceEntry
from actions.server.foundry.authoring_values import (
    AuthoringAccessDenied,
    CompilationEvidence,
    CompilationResult,
    CompiledPackage,
)
from actions.server.foundry.mcp import CanvasCaller
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryPackageRevision,
    FoundryRequest,
)
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.service import AccessDenied as RunAccessDenied
from actions.server.run_outputs.service import OutputProvider
from actions.server.run_outputs.types import (
    Actor,
    AdmittedActionSchema,
    ExecutionSnapshot,
    SealReceipt,
)

if TYPE_CHECKING:
    from actions.server.foundry.robot_execution import (
        DirectRobotPreparation,
        RccRobotPreparation,
    )
    from actions.server.foundry.robot_package_admission import (
        ADMISSION_SCHEMA as _ROBOT_SCHEMA,
    )
    from actions.server.foundry.robot_package_admission import (
        AdmittedRobotPackage,
        RobotAdmissionEvidence,
    )
    from actions.server.foundry.robot_package_builder import RobotPackageRequest

_ROBOT_SCHEMA = "actions.local-robot-package-admission/v1"


_SCHEMA = "actions.local-package-admission/v1"
_BUNDLE_SCHEMA = "actions.local-capability-bundle-admission/v1-draft"


@dataclass(frozen=True)
class RegistryCapabilitySelection:
    package_revision: PackageRevisionRef
    capability: CapabilityRef
    runtime_plan: RuntimePlanRef
    compiled: CompiledPackageRevision


@dataclass(frozen=True)
class RegistryRobotSelection:
    package_revision: PackageRevisionRef
    capability: CapabilityRef
    runtime_plan: RuntimePlanRef
    robot: AdmittedRobotPackage


def _verified_members(
    value: CompiledPackageRevision | CompiledCapabilityBundle,
) -> tuple[CompiledPackageRevision, ...]:
    members = (
        verify_bundle(value)
        if isinstance(value, CompiledCapabilityBundle)
        else (value,)
    )
    seen: set[str] = set()
    for member in members:
        for requirement in json.loads(member.manifest_json)[
            "logicalBindingRequirements"
        ]:
            if requirement["id"] in seen:
                raise AccessDenied(
                    "Logical requirement IDs must be unique across bundle members"
                )
            seen.add(requirement["id"])
    return members


def _json(value: object) -> str:
    return canonicalize_json(json.dumps(value, allow_nan=False).encode()).decode()


def _hash(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class _Pending:
    actor: Actor
    workspace: WorkspaceId
    application: DeploymentId
    outcome: CompilationOutcome | BundleCompilationOutcome
    inventory_json: str


@dataclass(frozen=True)
class PackageCapability:
    ref: CapabilityRef
    schema_digest: str
    runtime_plans: tuple[RuntimePlanRef, ...]
    binding_requirements: tuple[BindingRequirementRef, ...] = ()
    capability_authority: str = "package-revision"
    work_items: WorkItemDeclaration = WorkItemDeclaration()


@dataclass(frozen=True)
class PackagePlan:
    ref: RuntimePlanRef
    runtime_kind: str
    capabilities: tuple[CapabilityRef, ...]


@dataclass(frozen=True)
class PackageBindingRequirement:
    ref: BindingRequirementRef
    contract: LogicalBindingRequirement


class FoundryPackageRegistry:
    """One compiler/Package/Run adapter; no mirrored Action or independent DB.

    ``executor`` is trusted host configuration, never a request parameter.
    The explicit developer admission flag must be supplied by the host before
    generated code runs. Pending object identities only bridge a single local
    compiler call; durable admission is always the existing SQL record.
    """

    def __init__(
        self,
        db: Database,
        source_provider: OutputProvider,
        authorization: SqlFoundryAuthorization,
        *,
        executor: PackageBuildExecutor,
        admission: TrustedDeveloperExecutionAdmission | None = None,
        execution_root: Path | None = None,
    ):
        if db.verbose:
            raise ValueError("Package registry rejects raw SQL bind diagnostics")
        self._db, self._provider, self._authorization = (
            db,
            source_provider,
            authorization,
        )
        self._executor, self._admission, self._execution_root = (
            executor,
            admission,
            execution_root,
        )
        self._pending: OrderedDict[int, _Pending] = OrderedDict()
        self._lock = RLock()
        self._robot_pending: OrderedDict[int, tuple] = OrderedDict()

    def _require(
        self, actor: Actor, workspace: WorkspaceId, application: DeploymentId
    ) -> None:
        try:
            self._authorization.require(
                CanvasCaller(actor, str(workspace.root), "model"),
                "generate_backend",
                application_id=application,
            )
        except AuthoringAccessDenied:
            raise AccessDenied(
                "Package compilation unavailable or not authorized"
            ) from None
        self._authorization.require_workspace(actor, workspace, "deploy")

    def prepare_trusted_robot(
        self,
        request: RobotPackageRequest,
        *,
        logical_package_key: str,
        trusted_actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        preparation: DirectRobotPreparation | RccRobotPreparation,
    ) -> RobotAdmissionEvidence:
        from actions.server.foundry.robot_package_admission import (
            RobotAdmissionEvidence,
            assemble_robot_admission,
            decode_robot_admission,
        )
        from actions.server.foundry.robot_package_builder import build_robot_package

        if self._db.in_transaction():
            raise AccessDenied(
                "Robot preparation requires independent transaction boundary"
            )
        actor = Actor.model_validate(trusted_actor)
        workspace = WorkspaceId.model_validate(workspace_id)
        application = DeploymentId.model_validate(application_id)
        self._require(actor, workspace, application)
        if self._admission is not TrustedDeveloperExecutionAdmission.TRUSTED:
            raise AccessDenied("explicit trusted developer admission required")
        measured = build_robot_package(request, preparation=preparation)
        package = assemble_robot_admission(measured, logical_package_key)
        if (
            decode_robot_admission(package.manifest_json, package.source_archive)
            != package
        ):
            raise AccessDenied("Robot evidence reconstruction differs")
        evidence = RobotAdmissionEvidence(package)
        self._require(actor, workspace, application)
        with self._lock:
            if len(self._robot_pending) >= 32:
                self._robot_pending.popitem(last=False)
            self._robot_pending[id(evidence)] = (
                evidence,
                actor,
                workspace,
                application,
                preparation,
                package.manifest_json,
                _hash(package.source_archive),
            )
        return evidence

    def admit_robot(
        self, actor: Actor, workspace_id: WorkspaceId, evidence: RobotAdmissionEvidence
    ) -> PackageRevisionRef:
        from actions.server.foundry.robot_package_admission import (
            decode_robot_admission,
        )
        from actions.server.foundry.robot_package_builder import verify_robot_package

        if self._db.in_transaction():
            raise AccessDenied("Robot admission requires independent commit authority")
        actor, workspace = (
            Actor.model_validate(actor),
            WorkspaceId.model_validate(workspace_id),
        )
        with self._lock:
            pending = self._robot_pending.get(id(evidence))
        if (
            pending is None
            or pending[0] is not evidence
            or pending[1:3] != (actor, workspace)
        ):
            raise AccessDenied("Robot Package requires exact authorized host outcome")
        _, _, _, application, preparation, manifest, source_digest = pending
        self._require(actor, workspace, application)
        package = evidence.package
        if (
            package.manifest_json != manifest
            or _hash(package.source_archive) != source_digest
            or evidence.verification != "source-and-plan-verified"
            or evidence.execution != "not-qualified"
        ):
            raise AccessDenied("issued Robot evidence changed")
        verify_robot_package(package.robot, preparation=preparation)
        if decode_robot_admission(manifest, package.source_archive) != package:
            raise AccessDenied("Robot evidence reconstruction differs")
        ref = self._ref(workspace, package)
        with self._db.connect():
            existing = self._rows(ref)
        if existing:
            self._authorization.require_reference(actor, ref, "deploy")
            self.load_verified(ref)
            return ref
        staged = self._provider.stage(
            package.source_archive[i : i + 65536]
            for i in range(0, len(package.source_archive), 65536)
        )
        if staged.receipt.digest != source_digest or staged.receipt.size != len(
            package.source_archive
        ):
            raise AccessDenied("Robot source stage differs")
        inserted = False
        with self._db.connect(), _transaction(self._db):
            FoundryRepository(self._db)._lock_workspace(workspace)
            self._require(actor, workspace, application)
            if self._rows(ref):
                self._authorization.require_reference(actor, ref, "deploy")
                self.load_verified(ref)
            else:
                self._db.insert(
                    FoundryPackageRevision(
                        str(uuid5(ref.package_id.root, ref.revision_id.root)),
                        str(workspace.root),
                        str(ref.package_id.root),
                        ref.revision_id.root,
                        manifest.decode(),
                        source_digest,
                        package.robot.source.inventory.canonical_json.decode(),
                        _json(
                            {
                                "schemaVersion": _ROBOT_SCHEMA,
                                "source": staged.receipt.model_dump(mode="json"),
                            }
                        ),
                    )
                )
                request = FoundryRequest(
                    str(uuid4()),
                    str(workspace.root),
                    actor.principal_id,
                    "package.admit",
                    ref.revision_id.root,
                    _hash(manifest),
                    ref.model_dump_json(),
                )
                self._db.insert(request)
                self._db.insert(
                    FoundryAudit(
                        str(uuid4()),
                        str(workspace.root),
                        str(application.root),
                        actor.principal_id,
                        "package.admit",
                        request.id,
                        "",
                        ref.revision_id.root,
                        str(time.time_ns() // 1000000),
                    )
                )
                for reference in (
                    ref,
                    CapabilityRef(
                        package_revision=ref,
                        capability_id=CapabilityId(package.capability_id),
                    ),
                    self._plan_ref(ref, package),
                ):
                    self._db.insert(
                        FoundryAccessGrant(
                            str(uuid4()),
                            str(workspace.root),
                            actor.principal_id,
                            "reference",
                            reference_grant_subject(reference),
                            '["deploy","execute"]',
                        )
                    )
                inserted = True
        if not inserted:
            self._provider.discard(staged)
        return ref

    def _load_robot_row(self, ref, row, data) -> AdmittedRobotPackage:
        from actions.server.foundry.robot_package_admission import (
            MAX_ARCHIVE,
            decode_robot_admission,
        )

        if (
            set(data) != {"schemaVersion", "source"}
            or _json(data) != row.build_evidence_json
        ):
            raise ValueError("closed Robot admission evidence required")
        seal = SealReceipt.model_validate(data["source"])
        if seal.size > MAX_ARCHIVE or seal.digest != row.source_artifact_digest:
            raise ValueError("Robot source bound or identity differs")
        with self._provider.open(seal.object_ref, seal.digest, seal.size) as reader:
            source = reader.read(seal.size + 1)
        if len(source) != seal.size or _hash(source) != seal.digest:
            raise ValueError("Robot source identity differs")
        package = decode_robot_admission(row.manifest_json.encode(), source)
        if (
            self._ref(ref.workspace_id, package) != ref
            or package.robot.source.inventory.canonical_json.decode()
            != row.source_inventory_json
        ):
            raise ValueError("Robot scoped source inventory differs")
        return package

    def robot_admission_evidence(
        self, ref: PackageRevisionRef
    ) -> RobotAdmissionEvidence:
        from actions.server.foundry.robot_package_admission import (
            AdmittedRobotPackage,
            RobotAdmissionEvidence,
        )

        loaded = self.load_verified(ref)
        if not isinstance(loaded, AdmittedRobotPackage):
            raise AccessDenied("Robot admission unavailable")
        return RobotAdmissionEvidence(loaded)

    def compile_trusted_source(
        self,
        entries: Sequence[SuppliedSourceEntry],
        *,
        logical_package_key: str,
        logical_name: str,
        trusted_actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        work_items: WorkItemDeclaration = WorkItemDeclaration(),
        logical_requirements: tuple[LogicalBindingRequirement, ...] = (),
    ) -> CompilationResult:
        trusted_actor = Actor.model_validate(trusted_actor)
        workspace_id, application_id = (
            WorkspaceId.model_validate(workspace_id),
            DeploymentId.model_validate(application_id),
        )
        self._require(trusted_actor, workspace_id, application_id)
        snapshot = snapshot_source_entries(
            entries, protected_input_names=["package.yaml"]
        )
        outcome = compile_generated_python_action(
            entries,
            PackageCompilationPolicy(
                logical_package_key,
                logical_name,
                ">=1.1.0a39,<2.0.0"
                if any(req.invocations is not None for req in logical_requirements)
                else ">=1.1.0a15,<2.0.0",
                ">=1.1.0a4,<2.0.0"
                if any(req.invocations is not None for req in logical_requirements)
                else ">=1.0.2,<2.0.0",
                work_items=work_items,
                logical_requirements=logical_requirements,
            ),
            protected_input_names=["package.yaml"],
            admission=self._admission,
            executor=self._executor,
            execution_root=self._execution_root,
        )
        if outcome.compiled_package is not None:
            compiled = verify_compilation_outcome(outcome)
            if compiled.source_inventory_digest != snapshot.digest:
                raise AccessDenied("Compiled source identity changed")
            self._require(trusted_actor, workspace_id, application_id)
            with self._lock:
                if len(self._pending) >= 32:
                    self._pending.popitem(last=False)
                self._pending[id(compiled)] = _Pending(
                    trusted_actor,
                    workspace_id,
                    application_id,
                    outcome,
                    snapshot.inventory.canonical_json.decode(),
                )
        return CompilationResult(
            outcome.compiled_package, self._evidence(outcome.receipt)
        )

    def compile_trusted_bundle(
        self,
        entries: Sequence[SuppliedSourceEntry],
        *,
        policy: BundleCompilationPolicy,
        trusted_actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
    ) -> CompilationResult:
        actor = Actor.model_validate(trusted_actor)
        workspace = WorkspaceId.model_validate(workspace_id)
        application = DeploymentId.model_validate(application_id)
        self._require(actor, workspace, application)
        seen: set[str] = set()
        for item in policy.capabilities:
            for requirement in item.policy.logical_requirements:
                if requirement.id in seen:
                    raise AccessDenied(
                        "Logical requirement IDs must be unique across bundle members"
                    )
                seen.add(requirement.id)
        snapshot = snapshot_source_entries(
            entries, protected_input_names=["package.yaml"]
        )
        result = compile_generated_python_bundle(
            entries,
            policy,
            protected_input_names=["package.yaml"],
            admission=self._admission,
            executor=self._executor,
            execution_root=self._execution_root,
        )
        if result.bundle is not None:
            bundle = verify_bundle_compilation_outcome(result)
            members = _verified_members(bundle)
            if members[0].source_inventory_digest != snapshot.digest:
                raise AccessDenied("Compiled source identity changed")
            self._require(actor, workspace, application)
            with self._lock:
                if len(self._pending) >= 32:
                    self._pending.popitem(last=False)
                self._pending[id(bundle)] = _Pending(
                    actor,
                    workspace,
                    application,
                    result,
                    snapshot.inventory.canonical_json.decode(),
                )
        return CompilationResult(result.bundle, self._bundle_evidence(result))

    @staticmethod
    def _bundle_evidence(outcome: BundleCompilationOutcome) -> CompilationEvidence:
        if outcome.bundle is not None:
            verify_bundle_compilation_outcome(outcome)
        last = outcome.receipts[-1]
        return CompilationEvidence(
            "succeeded" if outcome.bundle is not None else "failed",
            last.build_status,
            last.import_status,
            last.test_status,
            outcome.failure_code,
            outcome.bundle.package_revision_id if outcome.bundle is not None else None,
            _json(
                {
                    "schemaVersion": _BUNDLE_SCHEMA,
                    "receipts": [asdict(value) for value in outcome.receipts],
                    "failureCode": outcome.failure_code,
                }
            ).encode(),
        )

    @staticmethod
    def _evidence(receipt: CompilationReceipt) -> CompilationEvidence:
        from actions.server.deployments.ids import PackageRevisionId

        return CompilationEvidence(
            receipt.status,
            receipt.build_status,
            receipt.import_status,
            receipt.test_status,
            receipt.failure_code,
            PackageRevisionId(receipt.package_revision_digest)
            if receipt.package_revision_digest
            else None,
            receipt.to_bytes(),
        )

    @staticmethod
    def _ref(
        workspace: WorkspaceId,
        compiled: CompiledPackageRevision
        | CompiledCapabilityBundle
        | AdmittedRobotPackage,
    ) -> PackageRevisionRef:
        from actions.server.foundry.robot_package_admission import AdmittedRobotPackage

        manifest = json.loads(
            compiled.manifest_json
            if isinstance(compiled, AdmittedRobotPackage)
            else _verified_members(compiled)[0].manifest_json
        )
        return PackageRevisionRef(
            workspace_id=workspace,
            package_id=PackageId(
                uuid5(
                    workspace.root,
                    "actions.package/v1:" + manifest["identity"]["packageId"],
                )
            ),
            revision_id=compiled.package_revision_id,
        )

    def _rows(self, ref: PackageRevisionRef) -> list[FoundryPackageRevision]:
        return self._db.select(
            FoundryPackageRevision,
            "SELECT * FROM foundry_package_revision WHERE workspace_id=? AND package_id=? AND revision_id=?",
            [
                str(ref.workspace_id.root),
                str(ref.package_id.root),
                ref.revision_id.root,
            ],
        )

    def admit_compiled(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        compiled: CompiledPackage | CompiledCapabilityBundle,
    ) -> PackageRevisionRef:
        actor, workspace_id = (
            Actor.model_validate(actor),
            WorkspaceId.model_validate(workspace_id),
        )
        with self._lock:
            pending = self._pending.get(id(compiled))
        if (
            pending is None
            or (
                pending.outcome.bundle
                if isinstance(pending.outcome, BundleCompilationOutcome)
                else pending.outcome.compiled_package
            )
            is not compiled
            or pending.actor != actor
            or pending.workspace != workspace_id
        ):
            raise AccessDenied(
                "Package requires this host's exact authorized compiler outcome"
            )
        self._require(actor, workspace_id, pending.application)
        verified = (
            verify_bundle_compilation_outcome(pending.outcome)
            if isinstance(pending.outcome, BundleCompilationOutcome)
            else verify_compilation_outcome(pending.outcome)
        )
        members = _verified_members(verified)
        source_artifact_digest = members[0].source_artifact_digest
        ref = self._ref(workspace_id, verified)
        with self._db.connect():
            existing = self._rows(ref)
        if existing:
            self._authorization.require_reference(actor, ref, "deploy")
            self.load_verified(ref)
            return ref

        staged = self._provider.stage(
            verified.source_archive[offset : offset + 65536]
            for offset in range(0, len(verified.source_archive), 65536)
        )
        # If SQL commit fails or its acknowledgement is lost, retain the sealed
        # object: it may be referenced. Only proven unreferenced duplicate stages
        # are discarded below; recovery/retention must reconcile other orphans.
        evidence: dict[str, Any]
        if isinstance(pending.outcome, BundleCompilationOutcome):
            evidence = {
                "schemaVersion": _BUNDLE_SCHEMA,
                "source": staged.receipt.model_dump(mode="json"),
                "receipts": [asdict(receipt) for receipt in pending.outcome.receipts],
            }
        else:
            assert isinstance(verified, CompiledPackageRevision)
            evidence = {
                "schemaVersion": _SCHEMA,
                "source": staged.receipt.model_dump(mode="json"),
                "receipt": asdict(pending.outcome.receipt),
                "header": {
                    **asdict(verified.runtime_plan_header),
                    "plan_digest": verified.runtime_plan_header.plan_digest.root,
                },
                **{
                    name: getattr(verified, name).decode()
                    for name in (
                        "runtime_plan_payload",
                        "adapter_specification_payload",
                        "input_schema_payload",
                        "output_schema_payload",
                    )
                },
            }
        inserted = False
        with self._db.connect(), _transaction(self._db):
            FoundryRepository(self._db)._lock_workspace(workspace_id)
            self._require(actor, workspace_id, pending.application)
            if self._rows(ref):
                self._authorization.require_reference(actor, ref, "deploy")
                self.load_verified(ref)
            else:
                self._db.insert(
                    FoundryPackageRevision(
                        str(uuid5(ref.package_id.root, ref.revision_id.root)),
                        str(workspace_id.root),
                        str(ref.package_id.root),
                        ref.revision_id.root,
                        verified.manifest_json.decode(),
                        source_artifact_digest,
                        pending.inventory_json,
                        _json(evidence),
                    )
                )
                request = FoundryRequest(
                    str(uuid4()),
                    str(workspace_id.root),
                    actor.principal_id,
                    "package.admit",
                    ref.revision_id.root,
                    _hash(verified.manifest_json),
                    ref.model_dump_json(),
                )
                self._db.insert(request)
                self._db.insert(
                    FoundryAudit(
                        str(uuid4()),
                        str(workspace_id.root),
                        str(pending.application.root),
                        actor.principal_id,
                        "package.admit",
                        request.id,
                        "",
                        ref.revision_id.root,
                        str(time.time_ns() // 1000000),
                    )
                )
                # Explicit trusted compilation plus Workspace deploy policy
                # admits only these newly created immutable source references.
                # Existing revisions never resurrect revoked grants.
                references: tuple[WorkspaceScopedRef, ...] = (
                    ref,
                    *self.capability_refs(ref),
                    *(self._plan_ref(ref, member) for member in members),
                    *(
                        BindingRequirementRef(
                            package_revision=ref, requirement_id=value["id"]
                        )
                        for member in members
                        for value in json.loads(member.manifest_json)[
                            "logicalBindingRequirements"
                        ]
                    ),
                )
                for reference in references:
                    self._db.insert(
                        FoundryAccessGrant(
                            str(uuid4()),
                            str(workspace_id.root),
                            actor.principal_id,
                            "reference",
                            reference_grant_subject(reference),
                            '["deploy","execute"]',
                        )
                    )
                inserted = True
        if not inserted:
            self._provider.discard(staged)
        return ref

    @staticmethod
    def _plan_ref(
        ref: PackageRevisionRef,
        compiled: CompiledPackageRevision | AdmittedRobotPackage,
    ) -> RuntimePlanRef:
        from actions.server.foundry.robot_package_admission import AdmittedRobotPackage

        return RuntimePlanRef(
            package_revision=ref,
            plan_digest=PlanDigest(compiled.robot.plan_digest)
            if isinstance(compiled, AdmittedRobotPackage)
            else compiled.runtime_plan_header.plan_digest,
        )

    def load(self, ref: PackageRevisionRef) -> CompiledPackageRevision:
        ref = PackageRevisionRef.model_validate(ref)
        try:
            with self._db.connect():
                rows = self._rows(ref)
            if len(rows) != 1:
                raise ValueError("missing immutable Package")
            row = rows[0]
            if any(
                len(value) > 512 * 1024
                for value in (
                    row.build_evidence_json,
                    row.manifest_json,
                    row.source_inventory_json,
                )
            ):
                raise ValueError("Package metadata bound exceeded")
            data = json.loads(row.build_evidence_json)
            if data["schemaVersion"] != _SCHEMA:
                raise ValueError("unknown local compiler evidence")
            seal = SealReceipt.model_validate(data["source"])
            if seal.size > 2 * 1024 * 1024 + 65536:
                raise ValueError("source bound exceeded")
            with self._provider.open(seal.object_ref, seal.digest, seal.size) as reader:
                source = reader.read(seal.size + 1)
            if (
                len(source) != seal.size
                or _hash(source) != seal.digest
                or seal.digest != row.source_artifact_digest
            ):
                raise ValueError("source bytes changed")
            receipt = CompilationReceipt(**data["receipt"])
            header = dict(data["header"])
            header["plan_digest"] = PlanDigest(header["plan_digest"])
            header["required_features"] = tuple(header["required_features"])
            compiled = CompiledPackageRevision(
                row.manifest_json.encode(),
                source,
                _hash(row.source_inventory_json.encode()),
                row.source_artifact_digest,
                ref.revision_id,
                RuntimePlanHeader(**header),
                data["runtime_plan_payload"].encode(),
                data["adapter_specification_payload"].encode(),
                data["input_schema_payload"].encode(),
                data["output_schema_payload"].encode(),
                receipt.rcc_specification_digest or "",
                receipt.rcc_artifact_digest or "",
            )
            verify_compilation_outcome(CompilationOutcome(compiled, receipt))
            if self._ref(ref.workspace_id, compiled) != ref:
                raise ValueError("scoped Package identity changed")
            return compiled
        except Exception:
            raise AccessDenied(
                "Package unavailable or integrity verification failed"
            ) from None

    def load_verified(
        self, ref: PackageRevisionRef
    ) -> CompiledPackageRevision | CompiledCapabilityBundle | AdmittedRobotPackage:
        ref = PackageRevisionRef.model_validate(ref)
        try:
            with self._db.connect():
                rows = self._rows(ref)
            if len(rows) != 1:
                raise ValueError("missing Package")
            row = rows[0]
            if any(
                len(value.encode()) > 512 * 1024
                for value in (
                    row.build_evidence_json,
                    row.manifest_json,
                    row.source_inventory_json,
                )
            ):
                raise ValueError("Package metadata bound exceeded")
            data = json.loads(row.build_evidence_json)
            if data.get("schemaVersion") == _ROBOT_SCHEMA:
                return self._load_robot_row(ref, row, data)
            if data.get("schemaVersion") == _SCHEMA:
                return self.load(ref)
            if (
                data.get("schemaVersion") != _BUNDLE_SCHEMA
                or set(data) != {"schemaVersion", "source", "receipts"}
                or _json(data) != row.build_evidence_json
            ):
                raise ValueError("unsupported bundle admission evidence")
            seal = SealReceipt.model_validate(data["source"])
            if seal.size > 2 * 1024 * 1024 + 65536:
                raise ValueError("source bound exceeded")
            with self._provider.open(seal.object_ref, seal.digest, seal.size) as reader:
                source = reader.read(seal.size + 1)
            if (
                len(source) != seal.size
                or _hash(source) != seal.digest
                or seal.digest != row.source_artifact_digest
            ):
                raise ValueError("source identity changed")
            bundle = decode_bundle(row.manifest_json.encode(), source)
            members = _verified_members(bundle)
            if not isinstance(data["receipts"], list) or len(data["receipts"]) != len(
                members
            ):
                raise ValueError("invalid receipts")
            verify_bundle_compilation_outcome(
                BundleCompilationOutcome(
                    bundle,
                    tuple(CompilationReceipt(**value) for value in data["receipts"]),
                    None,
                )
            )
            if (
                members[0].source_inventory_digest
                != _hash(row.source_inventory_json.encode())
                or self._ref(ref.workspace_id, bundle) != ref
            ):
                raise ValueError("scoped source identity changed")
            return bundle
        except Exception:
            raise AccessDenied(
                "Package unavailable or integrity verification failed"
            ) from None

    def selection_for(
        self, capability: CapabilityRef, plan: RuntimePlanRef
    ) -> RegistryCapabilitySelection | RegistryRobotSelection:
        from actions.server.foundry.robot_package_admission import AdmittedRobotPackage

        capability = CapabilityRef.model_validate(capability)
        plan = RuntimePlanRef.model_validate(plan)
        ref = capability.package_revision
        if plan.package_revision != ref:
            raise AccessDenied("Package selection scopes differ")
        loaded = self.load_verified(ref)
        if isinstance(loaded, AdmittedRobotPackage):
            if (
                capability.capability_id.root != loaded.capability_id
                or plan != self._plan_ref(ref, loaded)
            ):
                raise AccessDenied("Undeclared Robot Package selection")
            return RegistryRobotSelection(ref, capability, plan, loaded)
        if isinstance(loaded, CompiledCapabilityBundle):
            try:
                member = select_capability(
                    loaded,
                    ref.revision_id,
                    capability.capability_id.root,
                    plan.plan_digest,
                ).compiled
            except ValueError:
                raise AccessDenied("Undeclared Package selection") from None
        else:
            member = loaded
            if capability not in self.capability_refs(ref) or plan != self._plan_ref(
                ref, member
            ):
                raise AccessDenied("Undeclared Package selection")
        return RegistryCapabilitySelection(ref, capability, plan, member)

    def require_revision(self, ref: PackageRevisionRef) -> None:
        self.load_verified(ref)

    def evidence(self, ref: PackageRevisionRef) -> CompilationEvidence:
        from actions.server.foundry.robot_package_admission import AdmittedRobotPackage

        loaded = self.load_verified(ref)
        if isinstance(loaded, AdmittedRobotPackage):
            raise AccessDenied(
                "Robot measured evidence is not Python compilation readiness"
            )
        with self._db.connect():
            data = json.loads(self._rows(ref)[0].build_evidence_json)
        if isinstance(loaded, CompiledCapabilityBundle):
            return self._bundle_evidence(
                BundleCompilationOutcome(
                    loaded,
                    tuple(CompilationReceipt(**value) for value in data["receipts"]),
                    None,
                )
            )
        return self._evidence(CompilationReceipt(**data["receipt"]))

    def capability_refs(self, ref: PackageRevisionRef) -> tuple[CapabilityRef, ...]:
        from actions.server.foundry.robot_package_admission import AdmittedRobotPackage

        loaded = self.load_verified(ref)
        if isinstance(loaded, AdmittedRobotPackage):
            return (
                CapabilityRef(
                    package_revision=ref,
                    capability_id=CapabilityId(loaded.capability_id),
                ),
            )
        return tuple(
            CapabilityRef(package_revision=ref, capability_id=entry["id"])
            for member in _verified_members(loaded)
            for entry in json.loads(member.manifest_json)["capabilities"]
        )

    def get_capability(self, ref: CapabilityRef) -> PackageCapability | None:
        from actions.server.foundry.robot_package_admission import AdmittedRobotPackage

        ref = CapabilityRef.model_validate(ref)
        loaded = self.load_verified(ref.package_revision)
        if isinstance(loaded, AdmittedRobotPackage):
            if ref.capability_id.root != loaded.capability_id:
                return None
            return PackageCapability(
                ref,
                _hash(loaded.robot.input_schema),
                (self._plan_ref(ref.package_revision, loaded),),
            )
        for member in _verified_members(loaded):
            entry = json.loads(member.manifest_json)["capabilities"][0]
            if entry["id"] != ref.capability_id.root:
                continue
            return PackageCapability(
                ref,
                _hash(member.input_schema_payload),
                (self._plan_ref(ref.package_revision, member),),
                binding_requirements=tuple(
                    BindingRequirementRef(
                        package_revision=ref.package_revision, requirement_id=value
                    )
                    for value in entry["bindingRequirementIds"]
                ),
                work_items=WorkItemDeclaration(
                    mode=entry["mode"], allow_outputs=entry["allowOutputs"]
                ),
            )
        return None

    def get_runtime_plan(self, ref: RuntimePlanRef) -> PackagePlan | None:
        from actions.server.foundry.robot_package_admission import AdmittedRobotPackage

        ref = RuntimePlanRef.model_validate(ref)
        loaded = self.load_verified(ref.package_revision)
        if isinstance(loaded, AdmittedRobotPackage):
            if ref != self._plan_ref(ref.package_revision, loaded):
                return None
            return PackagePlan(
                ref,
                loaded.robot.plan.runtime_kind,
                (
                    CapabilityRef(
                        package_revision=ref.package_revision,
                        capability_id=CapabilityId(loaded.capability_id),
                    ),
                ),
            )
        for member in _verified_members(loaded):
            if ref == self._plan_ref(ref.package_revision, member):
                entry = json.loads(member.manifest_json)["capabilities"][0]
                return PackagePlan(
                    ref,
                    member.runtime_plan_header.runtime_kind,
                    (
                        CapabilityRef(
                            package_revision=ref.package_revision,
                            capability_id=entry["id"],
                        ),
                    ),
                )
        return None

    def get_binding_requirement(
        self, ref: BindingRequirementRef
    ) -> PackageBindingRequirement | None:
        from actions.server.foundry.robot_package_admission import AdmittedRobotPackage

        ref = BindingRequirementRef.model_validate(ref)
        loaded = self.load_verified(ref.package_revision)
        if isinstance(loaded, AdmittedRobotPackage):
            return None
        for member in _verified_members(loaded):
            for value in json.loads(member.manifest_json)["logicalBindingRequirements"]:
                if value["id"] == ref.requirement_id.root:
                    return PackageBindingRequirement(
                        ref,
                        LogicalBindingRequirement.model_validate_json(
                            json.dumps(value)
                        ),
                    )
        return None

    def resolve_capability(
        self, actor: Actor, workspace_id: WorkspaceId, capability: CapabilityRef
    ) -> CapabilityRef:
        capability = CapabilityRef.model_validate(capability)
        if capability.package_revision.workspace_id != workspace_id:
            raise AccessDenied("Capability outside Workspace")
        self._authorization.require_reference(
            actor, capability.package_revision, "deploy"
        )
        self._authorization.require_reference(actor, capability, "deploy")
        if self.get_capability(capability) is None:
            raise AccessDenied("Capability unavailable")
        return capability

    def action_id_for(self, ref: CapabilityRef) -> str:
        if self.get_capability(ref) is None:
            raise AccessDenied("Capability unavailable")
        return str(uuid5(ref.package_revision.package_id.root, ref.model_dump_json()))

    def schema_for(self, snapshot: ExecutionSnapshot) -> AdmittedActionSchema:
        try:
            selected = self.selection_for(snapshot.capability, snapshot.runtime_plan)
            if isinstance(selected, RegistryRobotSelection):
                return AdmittedActionSchema(
                    self.action_id_for(snapshot.capability),
                    snapshot.capability,
                    snapshot.runtime_plan,
                    selected.robot.robot.input_schema.decode(),
                    selected.robot.robot.output_schema.decode(),
                )
            compiled = selected.compiled
            return AdmittedActionSchema(
                self.action_id_for(snapshot.capability),
                snapshot.capability,
                snapshot.runtime_plan,
                compiled.input_schema_payload.decode(),
                compiled.output_schema_payload.decode(),
            )
        except AccessDenied:
            raise RunAccessDenied(
                "Package selection unavailable or not authorized"
            ) from None

    def authorize(
        self, actor: Actor, snapshot: ExecutionSnapshot, operation: str
    ) -> None:
        try:
            workspace = snapshot.deployment.workspace_id
            if operation == "execute":
                self._authorization.require_workspace(actor, workspace, "execute")
                self._authorization.require_deployment(
                    actor, workspace, snapshot.deployment.deployment_id, "execute"
                )
                for ref in (
                    snapshot.deployment,
                    snapshot.capability.package_revision,
                    snapshot.capability,
                    snapshot.runtime_plan,
                    snapshot.worker,
                    snapshot.policy,
                    snapshot.output_provider,
                ):
                    self._authorization.require_reference(actor, ref, "execute")
            else:
                self._authorization.require(
                    CanvasCaller(actor, str(workspace.root), "model"),
                    "read_application" if operation == "read" else "cancel_execution",
                    application_id=snapshot.deployment.deployment_id,
                )
        except (AccessDenied, AuthoringAccessDenied):
            raise RunAccessDenied(
                "Package source unavailable or not authorized"
            ) from None
