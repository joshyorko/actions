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
                snapshot, _ = self.outputs.execution_context(actor, fence)
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
                for binding in resolved.bindings:
                    projected = self.registry.get_binding_requirement(
                        binding.requirement
                    )
                    if (
                        projected is None
                        or projected.ref != binding.requirement
                        or projected.contract.kind != "data"
                    ):
                        raise LogicalReadRejected(
                            "supported artifact-verified data requirement required"
                        )
                    entry = self.configured.entry(binding.provider)
                    for operation in projected.contract.operations:
                        matched, _ = scan_contract(
                            entry.descriptor, entry.source, operation.name
                        )
                        if matched != operation:
                            raise LogicalReadRejected(
                                "provider operation contract differs"
                            )
                        selections.append((binding, projected.contract.id, operation))
                selections.sort(key=lambda item: (item[1], item[2].name))
                keys = [(name, operation.name) for _, name, operation in selections]
                if len(keys) != len(set(keys)) or len(keys) > MAX_OPERATIONS:
                    raise LogicalReadRejected(
                        "bounded unambiguous logical operations required"
                    )
                lookups = [
                    dict(requirementId=name, operation=operation.name, rows=[])
                    for _, name, operation in selections
                ]
                declared = len(_bytes(dict(version=VERSION, lookups=lookups))) + sum(
                    max(0, op.max_bytes - 2) for _, _, op in selections
                )
                if declared > MAX_BYTES:
                    raise LogicalReadRejected(
                        "declared aggregate logical context exceeds bound"
                    )
                receipts, pins = [], []
                for index, (binding, name, operation) in enumerate(selections):
                    self._check(event)
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
                    lookups[index]["rows"] = rows
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
                context = _bytes(dict(version=VERSION, lookups=lookups))
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
                    self.configured.recheck_sql(actor, reference, pins)
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
