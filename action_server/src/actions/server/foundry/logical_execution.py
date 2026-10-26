"""Host-owned eager retained scans, separate from Run admission/publication.

Only issued PreparedLogicalReads objects can authorize a SQL-only recheck.
The child context contains logical lookups, not provider/configuration identity.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from actions.server.foundry.logical_receipts import KnowledgeOperationEvidence
    from actions.server.foundry.generated_knowledge import KnowledgePreparation

from actions.server.data_queries.sealed_duckdb import scan_contract
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    BindingAssignment,
    StoredDeploymentRevision,
)
from actions.server.deployments.ids import ProviderProfileRevisionRef
from actions.server.foundry.models import FoundryAccessGrant, FoundryPackageRevision
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.provider_execution import (
    ConfiguredProviderExecution,
    SQLRecordPin,
)
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.service import RunOutputService, _transaction
from actions.server.run_outputs.types import Actor, AttemptFence, ExecutionSnapshot

VERSION = "actions.logical-read-context/v1"
MAX_BYTES = 256 * 1024
MAX_OPERATIONS = 32


def _bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


class LogicalReadRejected(ValueError):
    pass


class _TotalCancellation(threading.Event):
    def __init__(self, parent: threading.Event, deadline: float):
        super().__init__()
        self.parent, self.deadline = parent, deadline

    def is_set(self):
        return self.parent.is_set() or time.monotonic() >= self.deadline


@dataclass(frozen=True)
class LogicalReadReceipt:
    requirement_id: str
    operation: str
    provider: ProviderProfileRevisionRef
    source_revision: str
    config_digest: str
    catalog_digest: str
    contract_digest: str
    result_digest: str
    row_count: int
    kind: str = "data"
    parameters_digest: str | None = None
    knowledge: KnowledgeOperationEvidence | None = None


@dataclass(frozen=True, eq=False)
class PreparedLogicalReads:
    actor: Actor
    fence: AttemptFence
    snapshot: ExecutionSnapshot
    context: bytes
    context_digest: str
    receipts: tuple[LogicalReadReceipt, ...]
    # Host-only retained authority. These fields never enter child context.
    bindings: tuple[BindingAssignment, ...]
    deployment: StoredDeploymentRevision
    package_pins: tuple[SQLRecordPin, ...]
    provider_pins: tuple[
        tuple[ProviderProfileRevisionRef, tuple[SQLRecordPin, ...]], ...
    ]

    knowledge: tuple[KnowledgePreparation, ...] = ()


class LogicalExecution:
    def __init__(
        self,
        deployments: FoundryDeploymentService,
        registry: FoundryPackageRegistry,
        outputs: RunOutputService,
        configured: ConfiguredProviderExecution,
    ):
        if (
            type(outputs) is not RunOutputService
            or not isinstance(registry, FoundryPackageRegistry)
            or outputs.capabilities is not registry
            or outputs.db is not configured.db
        ):
            raise TypeError("canonical common Run/Package/provider services required")
        self.deployments, self.registry, self.outputs, self.configured = (
            deployments,
            registry,
            outputs,
            configured,
        )
        self.db = outputs.db
        self.authorization = SqlFoundryAuthorization(self.db)
        self.repository = FoundryRepository(self.db)
        self._issued: dict[int, PreparedLogicalReads] = {}
        from actions.server.foundry.logical_preparation import (
            LogicalPreparationSupervisor,
        )

        self._preparations = LogicalPreparationSupervisor(self)

    def require_selected_adapters(self, snapshot: ExecutionSnapshot) -> None:
        """Read immutable selection and import its adapters before admission.

        This is dependency readiness, not a grant or a connection/source probe.
        Existing callers retain responsibility for live execution authorization.
        """
        snapshot = ExecutionSnapshot.model_validate(snapshot)
        declaration = self.registry.get_capability(snapshot.capability)
        stored = self.repository.get_revision(snapshot.deployment)
        if declaration is None or stored is None:
            raise LogicalReadRejected("selected logical metadata unavailable")
        for reference in declaration.binding_requirements:
            bindings = [
                binding
                for binding in stored.revision.specification.bindings
                if binding.requirement == reference
            ]
            requirement = self.registry.get_binding_requirement(reference)
            if (
                len(bindings) != 1
                or requirement is None
                or requirement.contract.kind not in ("data", "knowledge")
            ):
                raise LogicalReadRejected("exact selected data binding required")
            if requirement.contract.kind == "knowledge":
                from actions.server.data_queries.knowledge_operations import (
                    knowledge_contract,
                )

                if requirement.contract.invocations is None:
                    raise LogicalReadRejected("explicit Knowledge mappings required")
                for operation in requirement.contract.operations:
                    knowledge_contract(operation)
            self.configured.require_adapter_available(
                bindings[0].provider,
                tuple(operation.name for operation in requirement.contract.operations),
            )

    def _check(self, event):
        if event.is_set():
            raise LogicalReadRejected("logical read cancelled or deadline exceeded")

    def prepare(
        self,
        actor: Actor,
        fence: AttemptFence,
        *,
        cancelled: threading.Event,
        deadline: float,
    ) -> PreparedLogicalReads:
        actor, fence = Actor.model_validate(actor), AttemptFence.model_validate(fence)
        if (
            isinstance(deadline, bool)
            or not isinstance(deadline, (float, int))
            or not math.isfinite(deadline)
        ):
            raise LogicalReadRejected("absolute monotonic deadline required")
        event = _TotalCancellation(cancelled, deadline)
        self._check(event)
        try:
            with self.db.connect():
                snapshot, inputs = self.outputs.execution_context(actor, fence)
                resolved = self.deployments.resolve(
                    actor,
                    snapshot.deployment.workspace_id,
                    snapshot.deployment.deployment_id,
                    snapshot.capability,
                    revision=snapshot.deployment,
                    runtime_plan=snapshot.runtime_plan,
                )
                if resolved.snapshot != snapshot:
                    raise LogicalReadRejected("resolved Run selection differs")
                stored = self.repository.get_revision(snapshot.deployment)
                if stored is None:
                    raise LogicalReadRejected("retained Deployment unavailable")
                self.configured.check_current()
                selections = []
                input_schema = json.loads(
                    self.registry.schema_for(snapshot).input_schema
                )
                for binding in resolved.bindings:
                    projected = self.registry.get_binding_requirement(
                        binding.requirement
                    )
                    if (
                        projected is None
                        or projected.ref != binding.requirement
                        or projected.contract.kind not in ("data", "knowledge")
                    ):
                        raise LogicalReadRejected(
                            "supported artifact-verified data requirement required"
                        )
                    entry = self.configured.entry(binding.provider)
                    for operation in projected.contract.operations:
                        if projected.contract.kind == "knowledge":
                            from actions.server.data_queries.knowledge_operations import (
                                knowledge_contract,
                            )

                            knowledge_contract(operation)
                            matches = [
                                op
                                for op in entry.descriptor.operations
                                if op.name == operation.name
                            ]
                            matched = matches[0] if len(matches) == 1 else None
                        else:
                            matched, _ = scan_contract(
                                entry.descriptor, entry.source, operation.name
                            )
                        if matched != operation:
                            raise LogicalReadRejected(
                                "provider operation contract differs"
                            )
                        selections.append((binding, projected.contract, operation))
                selections.sort(key=lambda item: (item[1].id, item[2].name))
                keys = [
                    (requirement.id, operation.name)
                    for _, requirement, operation in selections
                ]
                if len(keys) != len(set(keys)) or len(keys) > MAX_OPERATIONS:
                    raise LogicalReadRejected(
                        "bounded unambiguous logical operations required"
                    )
                from actions.server.deployments.logical_bindings import (
                    mapped_parameters,
                )

                version2 = any(
                    requirement.kind == "knowledge" for _, requirement, _ in selections
                )
                parameters = [
                    mapped_parameters(requirement, operation.name, input_schema, inputs)
                    if requirement.kind == "knowledge"
                    else {}
                    for _, requirement, operation in selections
                ]
                version = "actions.logical-context/v2" if version2 else VERSION
                lookups: list[dict[str, Any]] = [
                    dict(
                        requirementId=requirement.id,
                        operation=operation.name,
                        kind=requirement.kind,
                        parameters=parameters[index],
                        result=[] if requirement.kind == "data" else {},
                    )
                    if version2
                    else dict(
                        requirementId=requirement.id, operation=operation.name, rows=[]
                    )
                    for index, (_, requirement, operation) in enumerate(selections)
                ]
                declared = len(_bytes(dict(version=version, lookups=lookups))) + sum(
                    max(0, op.max_bytes - 2) for _, _, op in selections
                )
                if declared > MAX_BYTES:
                    raise LogicalReadRejected(
                        "declared aggregate logical context exceeds bound"
                    )
                receipts, pins, knowledge = [], [], []
                for index, (binding, requirement, operation) in enumerate(selections):
                    name = requirement.id
                    self._check(event)
                    if requirement.kind == "knowledge":
                        from actions.server.foundry.generated_knowledge import (
                            prepare_knowledge,
                        )

                        prepared_knowledge = prepare_knowledge(
                            self,
                            actor,
                            fence,
                            snapshot,
                            binding,
                            requirement,
                            operation,
                            parameters[index],
                            event,
                        )
                        knowledge.append(prepared_knowledge)
                        result_value = json.loads(prepared_knowledge.result)
                        lookups[index]["result"] = result_value
                        inner = json.loads(result_value["result_json"])
                        row_count = len(inner["hits"]) if "hits" in inner else 1
                        receipts.append(
                            LogicalReadReceipt(
                                name,
                                operation.name,
                                binding.provider,
                                self.configured.entry(
                                    binding.provider
                                ).source.revision_id,
                                self.configured.entry(binding.provider).config_digest,
                                self.configured.pointer.digest,
                                operation.contract_digest,
                                _digest(prepared_knowledge.result),
                                row_count,
                                "knowledge",
                                _digest(prepared_knowledge.parameters),
                                prepared_knowledge.evidence,
                            )
                        )
                        pins.append(
                            (
                                binding.provider,
                                self.configured.pin_sql(
                                    actor,
                                    binding.provider,
                                    manage=prepared_knowledge.ingestion is not None,
                                ),
                            )
                        )
                        continue
                    with self.configured.open_provider(
                        actor, binding.provider
                    ) as engine:
                        result = engine.execute(actor, operation.name, {}, event)
                    self._check(event)
                    if (
                        result.operation != operation.name
                        or result.contract_digest != operation.contract_digest
                        or result.source_revision
                        != self.configured.entry(binding.provider).source.revision_id
                    ):
                        raise LogicalReadRejected(
                            "logical scan receipt identity differs"
                        )
                    rows = json.loads(result.payload)
                    if (
                        not isinstance(rows, list)
                        or len(rows) != result.row_count
                        or len(rows) > operation.max_rows
                        or len(result.payload) > operation.max_bytes
                        or _bytes(rows) != result.payload
                    ):
                        raise LogicalReadRejected(
                            "logical result bounds or canonical bytes differ"
                        )
                    lookups[index]["result" if version2 else "rows"] = rows
                    receipts.append(
                        LogicalReadReceipt(
                            name,
                            operation.name,
                            binding.provider,
                            result.source_revision,
                            self.configured.entry(binding.provider).config_digest,
                            self.configured.pointer.digest,
                            result.contract_digest,
                            _digest(result.payload),
                            result.row_count,
                        )
                    )
                    pins.append(
                        (
                            binding.provider,
                            self.configured.pin_sql(actor, binding.provider),
                        )
                    )
                context = _bytes(dict(version=version, lookups=lookups))
                if len(context) > MAX_BYTES:
                    raise LogicalReadRejected("actual logical context exceeds bound")
                self.configured.check_current()
                self._check(event)
                prepared = PreparedLogicalReads(
                    actor,
                    fence,
                    snapshot,
                    context,
                    _digest(context),
                    tuple(receipts),
                    resolved.bindings,
                    stored,
                    tuple(
                        SQLRecordPin.capture(
                            self.db,
                            FoundryPackageRevision,
                            "workspace_id=? AND package_id=? AND revision_id=?",
                            (
                                str(ref.workspace_id.root),
                                str(ref.package_id.root),
                                ref.revision_id.root,
                            ),
                        )
                        for ref in stored.revision.specification.package_revisions
                    ),
                    tuple(pins),
                    tuple(knowledge),
                )
                self._issued[id(prepared)] = prepared
                try:
                    self.recheck(actor, fence, prepared)
                except BaseException:
                    self.release(prepared)
                    raise
                return prepared
        except LogicalReadRejected:
            raise
        except Exception:
            raise LogicalReadRejected("logical execution unavailable") from None

    def recheck(
        self, actor: Actor, fence: AttemptFence, prepared: PreparedLogicalReads
    ) -> None:
        """SQL-only; call within the existing fenced publication transaction.

        Private catalog race exclusion depends on ordinary Runtime mutex lifetime.
        No engine, artifact projection, provider._read or secret operation here.
        """
        if (
            self._issued.get(id(prepared)) is not prepared
            or prepared.actor != actor
            or prepared.fence != fence
            or _digest(prepared.context) != prepared.context_digest
        ):
            raise LogicalReadRejected("unissued or mismatched logical preparation")
        try:
            with _transaction(self.db):
                self.outputs._fence(fence)
                if self.db.backend_name == "postgresql":
                    self.db.select(
                        FoundryAccessGrant,
                        "SELECT * FROM foundry_access_grant WHERE workspace_id=? AND principal_id=? ORDER BY id LIMIT 129 FOR SHARE",
                        [prepared.snapshot.workspace_id, actor.principal_id],
                    )
                snapshot, _ = self.outputs.execution_context(actor, fence)
                if (
                    snapshot != prepared.snapshot
                    or self.repository.get_revision(snapshot.deployment)
                    != prepared.deployment
                    or not self.repository.was_activated(snapshot.deployment)
                ):
                    raise LogicalReadRejected("retained logical Deployment changed")
                for (
                    package
                ) in prepared.deployment.revision.specification.package_revisions:
                    self.authorization.require_reference(actor, package, "execute")
                for binding in prepared.bindings:
                    self.authorization.require_reference(
                        actor, binding.requirement, "execute"
                    )
                    self.authorization.require_reference(
                        actor, binding.provider, "execute"
                    )
                for package_pin in prepared.package_pins:
                    package_pin.recheck(self.db)
                for reference, pins in prepared.provider_pins:
                    manage = any(
                        item.ingestion is not None
                        and item.ingestion.binding.source_provider == reference
                        for item in prepared.knowledge
                    )
                    self.configured.recheck_sql(actor, reference, pins, manage=manage)
                for item in prepared.knowledge:
                    item.recheck(actor, fence)
        except LogicalReadRejected:
            raise
        except Exception:
            raise LogicalReadRejected(
                "logical publication authority unavailable"
            ) from None

    def release(self, prepared: PreparedLogicalReads) -> None:
        """Host lifecycle owner must release after completion/abort; no SQL mutation."""
        if self._issued.get(id(prepared)) is prepared:
            del self._issued[id(prepared)]

    def begin_preparation(self, actor, fence, *, cancelled, deadline):
        return self._preparations.begin(
            actor, fence, cancelled=cancelled, deadline=deadline
        )

    def release_preparation(self, owner, prepared):
        self._preparations.release(owner, prepared)

    def close(self, timeout_seconds=15):
        """Stop/settle owned preparation; false forbids provider teardown."""
        return self._preparations.close(timeout_seconds) and not self._issued
