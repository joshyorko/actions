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
from uuid import uuid4, uuid5

from actions.server._database import Database
from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.foundry_repository import (
    FoundryRepository,
    _transaction,
)
from actions.server.deployments.foundry_values import AccessDenied
from actions.server.deployments.ids import (
    BindingRequirementRef,
    CapabilityRef,
    DeploymentId,
    PackageId,
    PackageRevisionRef,
    PlanDigest,
    RuntimePlanRef,
    WorkspaceId,
    WorkspaceScopedRef,
)
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

_SCHEMA = "actions.local-package-admission/v1"


def _json(value: object) -> str:
    return canonicalize_json(json.dumps(value, allow_nan=False).encode()).decode()


def _hash(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class _Pending:
    actor: Actor
    workspace: WorkspaceId
    application: DeploymentId
    outcome: CompilationOutcome
    inventory_json: str


@dataclass(frozen=True)
class PackageCapability:
    ref: CapabilityRef
    schema_digest: str
    runtime_plans: tuple[RuntimePlanRef, ...]
    binding_requirements: tuple[BindingRequirementRef, ...] = ()
    capability_authority: str = "package-revision"


@dataclass(frozen=True)
class PackagePlan:
    ref: RuntimePlanRef
    runtime_kind: str
    capabilities: tuple[CapabilityRef, ...]


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

    def compile_trusted_source(
        self,
        entries: Sequence[SuppliedSourceEntry],
        *,
        logical_package_key: str,
        logical_name: str,
        trusted_actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
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
                ">=1.1.0a15,<2.0.0",
                ">=1.0.2,<2.0.0",
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
        workspace: WorkspaceId, compiled: CompiledPackageRevision
    ) -> PackageRevisionRef:
        manifest = json.loads(compiled.manifest_json)
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
        self, actor: Actor, workspace_id: WorkspaceId, compiled: CompiledPackage
    ) -> PackageRevisionRef:
        actor, workspace_id = (
            Actor.model_validate(actor),
            WorkspaceId.model_validate(workspace_id),
        )
        with self._lock:
            pending = self._pending.get(id(compiled))
        if (
            pending is None
            or pending.outcome.compiled_package is not compiled
            or pending.actor != actor
            or pending.workspace != workspace_id
        ):
            raise AccessDenied(
                "Package requires this host's exact authorized compiler outcome"
            )
        self._require(actor, workspace_id, pending.application)
        verified = verify_compilation_outcome(pending.outcome)
        ref = self._ref(workspace_id, verified)
        with self._db.connect():
            existing = self._rows(ref)
        if existing:
            self._authorization.require_reference(actor, ref, "deploy")
            self.load(ref)
            return ref

        staged = self._provider.stage(
            verified.source_archive[offset : offset + 65536]
            for offset in range(0, len(verified.source_archive), 65536)
        )
        # If SQL commit fails or its acknowledgement is lost, retain the sealed
        # object: it may be referenced. Only proven unreferenced duplicate stages
        # are discarded below; recovery/retention must reconcile other orphans.
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
                self.load(ref)
            else:
                self._db.insert(
                    FoundryPackageRevision(
                        str(uuid5(ref.package_id.root, ref.revision_id.root)),
                        str(workspace_id.root),
                        str(ref.package_id.root),
                        ref.revision_id.root,
                        verified.manifest_json.decode(),
                        verified.source_artifact_digest,
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
                    self._plan_ref(ref, verified),
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
        ref: PackageRevisionRef, compiled: CompiledPackageRevision
    ) -> RuntimePlanRef:
        return RuntimePlanRef(
            package_revision=ref, plan_digest=compiled.runtime_plan_header.plan_digest
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

    def require_revision(self, ref: PackageRevisionRef) -> None:
        self.load(ref)

    def evidence(self, ref: PackageRevisionRef) -> CompilationEvidence:
        self.load(ref)
        with self._db.connect():
            data = json.loads(self._rows(ref)[0].build_evidence_json)
        return self._evidence(CompilationReceipt(**data["receipt"]))

    def capability_refs(self, ref: PackageRevisionRef) -> tuple[CapabilityRef, ...]:
        compiled = self.load(ref)
        return tuple(
            CapabilityRef(package_revision=ref, capability_id=entry["id"])
            for entry in json.loads(compiled.manifest_json)["capabilities"]
        )

    def get_capability(self, ref: CapabilityRef) -> PackageCapability | None:
        ref = CapabilityRef.model_validate(ref)
        compiled = self.load(ref.package_revision)
        if ref not in self.capability_refs(ref.package_revision):
            return None
        return PackageCapability(
            ref,
            _hash(compiled.input_schema_payload),
            (self._plan_ref(ref.package_revision, compiled),),
        )

    def get_runtime_plan(self, ref: RuntimePlanRef) -> PackagePlan | None:
        ref = RuntimePlanRef.model_validate(ref)
        compiled = self.load(ref.package_revision)
        if ref != self._plan_ref(ref.package_revision, compiled):
            return None
        return PackagePlan(
            ref,
            compiled.runtime_plan_header.runtime_kind,
            self.capability_refs(ref.package_revision),
        )

    def get_binding_requirement(self, ref: BindingRequirementRef) -> None:
        self.load(ref.package_revision)
        return None  # This compiler declares no logical requirements.

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
            compiled = self.load(snapshot.capability.package_revision)
            if (
                self.get_capability(snapshot.capability) is None
                or self.get_runtime_plan(snapshot.runtime_plan) is None
            ):
                raise AccessDenied("Undeclared Package selection")
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
