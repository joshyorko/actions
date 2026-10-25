"""Closed logical receipt values, not complete generated-envelope authority.

Full-summary comparison is for a trusted publication expectation. Identity-only
comparison is for retained readers: it cannot authenticate result/context hashes
or counts. Callers still own issuance, launch equality, fences, grants and seals.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

if TYPE_CHECKING:
    from actions.server.foundry.logical_execution import PreparedLogicalReads

DISPATCH_V1 = "actions.generated-rcc-dispatch/v1"
DISPATCH_V2 = "actions.generated-rcc-dispatch/v2"
EXECUTION_V1 = "actions.generated-rcc-execution/v1"
EXECUTION_V2 = "actions.generated-rcc-execution/v2"
MAX_OPERATIONS = 32
MAX_SUMMARY_BYTES = 64 * 1024
_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}")
_OPERATION = re.compile(r"[a-z][a-z0-9_-]{0,58}\.scan/v1")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def _matches(value, pattern):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError("canonical logical receipt identity required")
    return value


class _Value(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        revalidate_instances="always",
        serialize_by_alias=True,
    )

    @model_validator(mode="before")
    @classmethod
    def closed_alias_keys(cls, value, info: ValidationInfo):
        # Enforce the wire key set before Pydantic JSON alias resolution; a
        # field-name/alias collision must not disappear as an ignored key.
        if isinstance(value, dict) and set(value) != {
            field.alias or name for name, field in cls.model_fields.items()
        }:
            raise ValueError("closed canonical logical receipt fields required")
        if (
            info.mode == "json"
            and isinstance(value, dict)
            and isinstance(value.get("operations"), list)
        ):
            # A before-validator exposes Python containers. Restore only the
            # declared JSON-array -> immutable tuple conversion, without scalar
            # coercion or accepting Python-list constructor values.
            value = {**value, "operations": tuple(value["operations"])}
        return value


class LogicalOperationIdentity(_Value):
    requirement_id: str = Field(alias="requirementId")
    operation: str
    source_revision: str = Field(alias="sourceRevision")
    contract_digest: str = Field(alias="contractDigest")

    @field_validator("requirement_id")
    @classmethod
    def identifier(cls, value):
        return _matches(value, _ID)

    @field_validator("operation")
    @classmethod
    def exact_scan(cls, value):
        return _matches(value, _OPERATION)

    @field_validator("source_revision", "contract_digest")
    @classmethod
    def digest(cls, value):
        return _matches(value, _DIGEST)


class LogicalOperationReceipt(LogicalOperationIdentity):
    result_digest: str = Field(alias="resultDigest")
    row_count: int = Field(alias="rowCount", ge=0, le=100000)

    @field_validator("result_digest")
    @classmethod
    def result_hash(cls, value):
        return _matches(value, _DIGEST)


class LogicalReadSummary(_Value):
    version: Literal["actions.logical-read-receipt/v1"]
    context_digest: str = Field(alias="contextDigest")
    operations: tuple[LogicalOperationReceipt, ...] = Field(
        min_length=1, max_length=MAX_OPERATIONS
    )

    @field_validator("context_digest")
    @classmethod
    def context_hash(cls, value):
        return _matches(value, _DIGEST)

    @model_validator(mode="after")
    def unique_ordered(self):
        keys = [(entry.requirement_id, entry.operation) for entry in self.operations]
        if len(set(keys)) != len(keys) or keys != sorted(keys):
            raise ValueError("unique canonical logical operation order required")
        return self


def _canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate receipt key")
        result[key] = value
    return result


def _no_constant(value):
    raise ValueError("nonfinite receipt value")


def _bounded(value, depth=0):
    if depth > 5:
        raise ValueError("receipt nesting unsupported")
    if isinstance(value, str):
        if len(value) > 256:
            raise ValueError("receipt string exceeds bound")
    elif isinstance(value, dict):
        if len(value) > 16:
            raise ValueError("receipt fields exceed bound")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("receipt keys must be strings")
            _bounded(key, depth + 1)
            _bounded(item, depth + 1)
    elif isinstance(value, (list, tuple)):
        if len(value) > MAX_OPERATIONS:
            raise ValueError("receipt operations exceed bound")
        for item in value:
            _bounded(item, depth + 1)
    elif value is not None and type(value) not in (int, float, bool):
        raise ValueError("receipt value unsupported")


def _parse(value) -> LogicalReadSummary:
    if isinstance(value, bytes):
        if not 1 <= len(value) <= MAX_SUMMARY_BYTES:
            raise ValueError("receipt exceeds bound")
        decoded = json.loads(
            value.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_no_constant
        )
        _bounded(decoded)
        if _canonical(decoded) != value:
            raise ValueError("canonical receipt bytes required")
        raw = value
    elif isinstance(value, dict):
        _bounded(value)
        raw = _canonical(value)
    else:
        raise ValueError("receipt object or canonical bytes required")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise ValueError("receipt exceeds bound")
    return LogicalReadSummary.model_validate_json(raw)


def _requirements(requirement_ids: tuple[str, ...]) -> tuple[str, ...]:
    if type(requirement_ids) is not tuple or len(requirement_ids) > MAX_OPERATIONS:
        raise ValueError("bounded immutable requirement identity tuple required")
    for value in requirement_ids:
        _matches(value, _ID)
    if len(set(requirement_ids)) != len(requirement_ids):
        raise ValueError("duplicate requirement identity")
    return requirement_ids


def versions_for(requirement_ids: tuple[str, ...]) -> tuple[str, str]:
    """Select only from trusted artifact-verified capability requirement IDs."""
    return (
        (DISPATCH_V2, EXECUTION_V2)
        if _requirements(requirement_ids)
        else (DISPATCH_V1, EXECUTION_V1)
    )


def validate_generated_version(
    record: dict, *, requirement_ids: tuple[str, ...], terminal: bool
) -> None:
    """Partial check ONLY: does not validate any envelope fields or authorize it."""
    if not isinstance(terminal, bool) or not isinstance(record, dict):
        raise ValueError("generated receipt version unavailable")
    expected = versions_for(requirement_ids)[int(terminal)]
    if record.get("version") != expected:
        raise ValueError(
            "generated receipt version differs from capability requirements"
        )


def derive_summary(prepared: PreparedLogicalReads) -> LogicalReadSummary:
    """Project actual prepared values; issuance belongs to LogicalExecution.recheck."""
    from actions.server.foundry.logical_execution import (
        LogicalReadReceipt,
        PreparedLogicalReads,
    )

    try:
        if (
            type(prepared) is not PreparedLogicalReads
            or type(prepared.context) is not bytes  # noqa: E721 -- built-in immutable bytes only
            or not 1 <= len(prepared.context) <= 256 * 1024
            or "sha256:" + hashlib.sha256(prepared.context).hexdigest()
            != prepared.context_digest
            or type(prepared.receipts) is not tuple
            or any(type(row) is not LogicalReadReceipt for row in prepared.receipts)
        ):
            raise ValueError("prepared logical value required")
        return _parse(
            {
                "version": "actions.logical-read-receipt/v1",
                "contextDigest": prepared.context_digest,
                "operations": [
                    {
                        "requirementId": row.requirement_id,
                        "operation": row.operation,
                        "sourceRevision": row.source_revision,
                        "contractDigest": row.contract_digest,
                        "resultDigest": row.result_digest,
                        "rowCount": row.row_count,
                    }
                    for row in prepared.receipts
                ],
            }
        )
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ValueError("prepared logical summary unavailable") from None


def validate_summary(value, *, expected: LogicalReadSummary) -> LogicalReadSummary:
    """Exact publication comparison; expected must come from trusted preparation."""
    try:
        if type(expected) is not LogicalReadSummary:
            raise ValueError("trusted expected summary required")
        # Re-parse even a model_copy-created object: frozen DTOs are not authority.
        trusted = _parse(expected.model_dump(mode="json"))
        parsed = _parse(value)
        if parsed != trusted:
            raise ValueError("logical summary differs")
        return parsed
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ValueError("logical summary unavailable or differs") from None


def validate_summary_identities(
    value,
    *,
    expected_operations: tuple[LogicalOperationIdentity, ...],
    requirement_ids: tuple[str, ...],
) -> LogicalReadSummary:
    """Retained-read identity coverage only; result/context evidence stays unproven.

    Expected identities and requirement IDs must come from verified immutable
    Package/Deployment/provider metadata, never from the claimed summary.
    Callers must enforce each declared operation max_rows (the global 100000
    bound is structural only), launch/terminal equality, complete envelope/fence/
    output-inventory validation and live authorization.
    """
    try:
        requirements = _requirements(requirement_ids)
        if (
            type(expected_operations) is not tuple
            or not 1 <= len(expected_operations) <= MAX_OPERATIONS
            or any(
                type(op) is not LogicalOperationIdentity for op in expected_operations
            )
        ):
            raise ValueError("trusted operation identity tuple required")
        expected = tuple(
            LogicalOperationIdentity.model_validate_json(
                _canonical(op.model_dump(mode="json"))
            )
            for op in expected_operations
        )
        keys = [(op.requirement_id, op.operation) for op in expected]
        if len(set(keys)) != len(keys) or {op.requirement_id for op in expected} != set(
            requirements
        ):
            raise ValueError("expected operation coverage differs")
        parsed = _parse(value)
        actual = tuple(
            LogicalOperationIdentity(
                requirementId=op.requirement_id,
                operation=op.operation,
                sourceRevision=op.source_revision,
                contractDigest=op.contract_digest,
            )
            for op in parsed.operations
        )
        if actual != tuple(
            sorted(expected, key=lambda op: (op.requirement_id, op.operation))
        ):
            raise ValueError("logical operation identity differs")
        return parsed
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ValueError("logical identity summary unavailable or differs") from None


def requirement_ids(registry, snapshot) -> tuple[str, ...]:
    """Read the artifact-verified capability, never a claimed journal version."""
    declaration = registry.get_capability(snapshot.capability)
    if declaration is None:
        raise ValueError("immutable capability unavailable")
    return tuple(ref.requirement_id.root for ref in declaration.binding_requirements)


def _retained_projection(db, registry, snapshot):
    """Validate public summary against immutable SQL metadata; no source reads.

    This deliberately does not call SqlProviderRegistry._read, which verifies
    source bytes. Ordinary Run read authorization remains the caller's duty.
    """
    from actions.server.data_queries.sealed_duckdb import scan_contract
    from actions.server.deployments.foundry_repository import FoundryRepository
    from actions.server.deployments.provider_registry import (
        ProviderDescriptor,
        SourceManifest,
        canonical,
    )
    from actions.server.foundry.provider_models import (
        FoundryProviderRevision,
        FoundrySourceRevision,
    )
    from actions.server.foundry.provider_registry import _id, _ref_id
    from actions.server.run_outputs.service import _one

    declaration = registry.get_capability(snapshot.capability)
    stored = FoundryRepository(db).get_revision(snapshot.deployment)
    if declaration is None or stored is None:
        raise ValueError("immutable logical selection unavailable")
    expected, limits = [], {}
    for ref in declaration.binding_requirements:
        bindings = [
            b for b in stored.revision.specification.bindings if b.requirement == ref
        ]
        if len(bindings) != 1:
            raise ValueError("exact logical binding required")
        binding = bindings[0]
        projected = registry.get_binding_requirement(ref)
        if projected is None or projected.contract.kind != "data":
            raise ValueError("artifact-verified data requirement required")
        row = _one(db, FoundryProviderRevision, _ref_id(binding.provider))
        if len(row.descriptor_json) > 128 * 1024:
            raise ValueError("provider descriptor exceeds bound")
        descriptor = ProviderDescriptor.model_validate_json(row.descriptor_json)
        source_row = _one(db, FoundrySourceRevision, row.foundry_source_revision_id)
        if len(source_row.manifest_json) > 128 * 1024:
            raise ValueError("source metadata exceeds bound")
        source = SourceManifest.model_validate_json(source_row.manifest_json)
        workspace = str(snapshot.deployment.workspace_id.root)
        if (
            descriptor.reference != binding.provider
            or row.workspace_id != workspace
            or canonical(descriptor) != row.descriptor_json
            or source_row.workspace_id != workspace
            or source_row.revision_id != source.revision_id
            or source.revision_id != descriptor.source_revision
            or source.kind != descriptor.kind
            or source.schema_version != "actions.logical-source/v2"
            or canonical(source) != source_row.manifest_json
            or source_row.id != _id(workspace + source.revision_id)
        ):
            raise ValueError("retained provider/source identity differs")
        for operation in projected.contract.operations:
            supported, _ = scan_contract(descriptor, source, operation.name)
            if supported != operation:
                raise ValueError("retained operation contract differs")
            identity = LogicalOperationIdentity(
                requirementId=ref.requirement_id.root,
                operation=operation.name,
                sourceRevision=source.revision_id,
                contractDigest=operation.contract_digest,
            )
            expected.append(identity)
            limits[(identity.requirement_id, identity.operation)] = operation.max_rows
    from actions.server.foundry.execution_selection import compiled_for_snapshot

    compiled = compiled_for_snapshot(registry, snapshot)
    fixed = dict(
        sourceArtifactDigest=compiled.source_artifact_digest,
        packageRevision=snapshot.capability.package_revision.revision_id.root,
        runtimePlanDigest=snapshot.runtime_plan.plan_digest.root,
        rccSpecificationDigest=compiled.rcc_specification_digest,
        rccArtifactDigest=compiled.rcc_artifact_digest,
    )
    return _RetainedProjection(
        snapshot,
        tuple(expected),
        tuple(limits.items()),
        tuple(fixed.items()),
        tuple(ref.requirement_id.root for ref in declaration.binding_requirements),
    )


@dataclass(frozen=True)
class _RetainedProjection:
    snapshot: object
    operations: tuple
    limits: tuple
    fixed: tuple
    requirement_ids: tuple[str, ...]


def _projected_summary(projection, value):
    summary = validate_summary_identities(
        value,
        expected_operations=projection.operations,
        requirement_ids=projection.requirement_ids,
    )
    limits = dict(projection.limits)
    if any(
        op.row_count > limits[(op.requirement_id, op.operation)]
        for op in summary.operations
    ):
        raise ValueError("declared logical row limit exceeded")
    return summary


def retained_summary(db, registry, snapshot, value) -> LogicalReadSummary:
    """Metadata-only retained read: never engines, source seals or secrets."""
    return _projected_summary(_retained_projection(db, registry, snapshot), value)


def validate_bound_record(
    db,
    registry,
    snapshot,
    run,
    fence,
    record,
    *,
    claim,
    terminal,
    outputs=None,
    _projection=None,
    _allow_expired_terminal=False,
):
    """Strict bound v2 journal/terminal validation; reads metadata only.

    Existing caller authorization/fence checks and sealed-byte resolution remain
    required. Output SQL seals, exact lineage and logical equality are checked here.
    """
    from actions.server._models import RunStatus
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import _canonical, _now, _one
    from actions.server.run_outputs.types import OutputRef, canonical_uuid

    ids = (
        _projection.requirement_ids
        if _projection is not None
        else requirement_ids(registry, snapshot)
    )
    validate_generated_version(record, requirement_ids=ids, terminal=terminal)
    if not ids:
        return
    if not isinstance(_allow_expired_terminal, bool) or (
        _allow_expired_terminal
        and (not terminal or run.status not in (RunStatus.PASSED, RunStatus.FAILED))
    ):
        raise ValueError("expired output metadata is terminal acknowledgement only")
    # Decode the persisted carrier independently so duplicate keys cannot be
    # discarded by a caller's earlier json.loads before closed validation.
    raw = run.result
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("bounded retained carrier required")
    carrier = json.loads(
        raw,
        object_pairs_hook=_pairs,
        parse_constant=_no_constant,
    )
    if _canonical(carrier, 2 * 1024 * 1024) != raw:
        raise ValueError("canonical retained carrier required")
    if run.status in (RunStatus.PASSED, RunStatus.FAILED):
        if (
            not isinstance(carrier, dict)
            or set(carrier) != {"version", "result", "outputs"}
            or isinstance(carrier["version"], bool)
            or carrier["version"] != 1
            or _canonical(carrier["result"], 2 * 1024 * 1024)
            != _canonical(record, 2 * 1024 * 1024)
        ):
            raise ValueError("closed retained output carrier required")
    elif not terminal and _canonical(carrier, 2 * 1024 * 1024) != _canonical(
        record, 2 * 1024 * 1024
    ):
        raise ValueError("retained journal differs")
    seed = {"version", "mode", "claim", "fence", "launch"}
    fixed_keys = {
        "sourceArtifactDigest",
        "packageRevision",
        "runtimePlanDigest",
        "rccSpecificationDigest",
        "rccArtifactDigest",
    }
    terminal_keys = {
        "version",
        "mode",
        "claim",
        "lineage",
        "launch",
        "publicationFence",
        "execution",
        "outputs",
        "actionResult",
        "logicalReads",
    } | fixed_keys
    if (
        set(record) != terminal_keys
        if terminal
        else not seed <= set(record) or bool(set(record) - (seed | {"execution"}))
    ):
        raise ValueError("closed bound execution fields required")
    if (
        _canonical(record.get("claim"), 4096) != _canonical(claim, 4096)
        or record.get("mode") != ("work-items" if claim else "standalone")
        or _canonical(record.get("publicationFence" if terminal else "fence"), 4096)
        != _canonical(fence.model_dump(), 4096)
    ):
        raise ValueError("bound execution fence differs")
    launch = record["launch"]
    if launch is None:
        if terminal or record.get("execution") is not None:
            raise ValueError("bound execution requires launch")
        return
    projection = (
        _projection
        if _projection is not None
        else _retained_projection(db, registry, snapshot)
    )
    if projection.snapshot != snapshot:
        raise ValueError("retained projection selection differs")
    fixed = dict(projection.fixed)
    lineage = dict(
        packageRevision=snapshot.capability.package_revision.model_dump(mode="json"),
        runtimePlan=snapshot.runtime_plan.model_dump(mode="json"),
        workItemClaim=claim,
        runId=fence.run_id,
        attemptFence=fence.model_dump(),
    )
    if (
        not isinstance(launch, dict)
        or set(launch)
        != {"id", "workItemClaim", "lineage", "inputDigest", "logicalReads"}
        | fixed_keys
    ):
        raise ValueError("closed logical launch required")
    canonical_uuid(launch["id"])
    if (
        _canonical(launch["lineage"], 16384) != _canonical(lineage, 16384)
        or _canonical(launch["workItemClaim"], 4096) != _canonical(claim, 4096)
        or launch["inputDigest"]
        != "sha256:"
        + hashlib.sha256(
            _canonical(json.loads(run.inputs), 262144).encode()
        ).hexdigest()
        or any(launch[k] != v for k, v in fixed.items())
    ):
        raise ValueError("logical launch lineage differs")
    summary = _projected_summary(projection, launch["logicalReads"])
    if record.get("execution") is not None:
        _execution_shape(record["execution"], fixed["rccArtifactDigest"])
    if not terminal:
        return
    validate_summary(record["logicalReads"], expected=summary)
    if _canonical(record["lineage"], 16384) != _canonical(lineage, 16384) or any(
        record[k] != v for k, v in fixed.items()
    ):
        raise ValueError("logical terminal lineage differs")
    if (
        not isinstance(outputs, (list, tuple))
        or len(outputs) != 4
        or not isinstance(record["outputs"], list)
        or len(record["outputs"]) != 4
    ):
        raise ValueError("complete bound output inventory required")
    inventory = {}
    for raw, evidence in zip(outputs, record["outputs"]):
        ref = raw if isinstance(raw, OutputRef) else OutputRef.model_validate(raw)
        if not isinstance(evidence, dict) or set(evidence) != {
            "name",
            "ref",
            "digest",
            "size",
        }:
            raise ValueError("closed output evidence required")
        row = _one(db, RunOutput, ref.output_id)
        expires_ms = int(row.expires_ms)
        if expires_ms < 0 or str(expires_ms) != row.expires_ms:
            raise ValueError("canonical output retention timestamp required")
        if (
            ref.run_id != run.id
            or ref.workspace_id != snapshot.workspace_id
            or evidence["ref"] != ref.model_dump(mode="json")
            or row.run_id != run.id
            or row.run_attempt_id != fence.attempt_id
            or row.epoch != fence.epoch
            or row.workspace_id != snapshot.workspace_id
            or row.state
            != (
                "final"
                if run.status in (RunStatus.PASSED, RunStatus.FAILED)
                else "provisional"
            )
            or row.provider_key != snapshot.provider_key
            or (not _allow_expired_terminal and expires_ms <= _now(db))
            or (
                not isinstance(evidence["size"], int)
                or isinstance(evidence["size"], bool)
            )
            or evidence["size"] < 0
            or (evidence["name"], evidence["digest"], evidence["size"])
            != (row.name, row.digest, row.size)
            or row.name in inventory
        ):
            raise ValueError("bound output seal differs")
        inventory[row.name] = evidence
    names = {
        "generated-action-result.json",
        "rcc-receipt.json",
        "rcc-stdout.log",
        "rcc-stderr.log",
    }
    execution = record["execution"]
    if (
        set(inventory) != names
        or not isinstance(execution, dict)
        or set(execution)
        != {
            "status",
            "resultDigest",
            "receiptDigest",
            "artifactDigest",
            "stdout",
            "stderr",
        }
    ):
        raise ValueError("closed measured execution required")
    if (
        execution["status"] != "completed"
        or execution["artifactDigest"] != fixed["rccArtifactDigest"]
        or execution["resultDigest"]
        != inventory["generated-action-result.json"]["digest"]
        or execution["resultDigest"]
        != "sha256:"
        + hashlib.sha256(
            _canonical(record["actionResult"], 524288).encode()
        ).hexdigest()
        or execution["receiptDigest"] != inventory["rcc-receipt.json"]["digest"]
    ):
        raise ValueError("measured result differs")
    for stream in ("stdout", "stderr"):
        measured = execution[stream]
        if not isinstance(measured, dict) or set(measured) != {
            "observedBytes",
            "retainedBytes",
            "discardedObservedBytes",
            "streamComplete",
            "truncated",
            "digest",
        }:
            raise ValueError("closed stream measurement required")
        if (
            any(
                (not isinstance(measured[k], int) or isinstance(measured[k], bool))
                or measured[k] < 0
                for k in ("observedBytes", "retainedBytes", "discardedObservedBytes")
            )
            or any(
                not isinstance(measured[k], bool)
                for k in ("streamComplete", "truncated")
            )
            or measured["observedBytes"]
            != measured["retainedBytes"] + measured["discardedObservedBytes"]
            or measured["truncated"]
            != (
                measured["discardedObservedBytes"] > 0 or not measured["streamComplete"]
            )
            or (measured["digest"], measured["retainedBytes"])
            != (
                inventory[f"rcc-{stream}.log"]["digest"],
                inventory[f"rcc-{stream}.log"]["size"],
            )
        ):
            raise ValueError("stream measurement differs")


def _execution_shape(execution, artifact_digest):
    if (
        not isinstance(execution, dict)
        or set(execution)
        != {
            "status",
            "resultDigest",
            "receiptDigest",
            "artifactDigest",
            "stdout",
            "stderr",
        }
        or execution["status"] != "completed"
        or execution["artifactDigest"] != artifact_digest
    ):
        raise ValueError("closed completed execution required")
    for name in ("resultDigest", "receiptDigest", "artifactDigest"):
        _matches(execution[name], _DIGEST)
    for stream in ("stdout", "stderr"):
        measured = execution[stream]
        if not isinstance(measured, dict) or set(measured) != {
            "observedBytes",
            "retainedBytes",
            "discardedObservedBytes",
            "streamComplete",
            "truncated",
            "digest",
        }:
            raise ValueError("closed stream measurement required")
        _matches(measured["digest"], _DIGEST)
        if (
            any(
                not isinstance(measured[k], int)
                or isinstance(measured[k], bool)
                or not 0 <= measured[k] <= 2**53 - 1
                for k in ("observedBytes", "retainedBytes", "discardedObservedBytes")
            )
            or any(
                not isinstance(measured[k], bool)
                for k in ("streamComplete", "truncated")
            )
            or measured["observedBytes"]
            != measured["retainedBytes"] + measured["discardedObservedBytes"]
            or measured["truncated"]
            != (
                measured["discardedObservedBytes"] > 0 or not measured["streamComplete"]
            )
        ):
            raise ValueError("stream measurement differs")


class LogicalPublicationGuard:
    """Mixin for trusted domain output wrappers; no persistent invocation state."""

    def bind_logical_execution(self, execution, prepared, *, publication_check=None):
        from contextlib import contextmanager

        from actions.server.foundry.logical_execution import (
            LogicalExecution,
            PreparedLogicalReads,
        )

        @contextmanager
        def bind():
            if (
                getattr(self, "_logical_binding", None) is not None
                or type(execution) is not LogicalExecution
                or type(prepared) is not PreparedLogicalReads
                or (publication_check is not None and not callable(publication_check))
                or execution.db is not self.db
                or execution.outputs is not self.owner.base
                or self.db.in_transaction()
                or execution.registry is not self.owner.registry
                or prepared.actor != self.caller.actor
                or prepared.fence != self.ticket.fence
                or prepared.snapshot != self.owner.snapshot
            ):
                raise ValueError("exact invocation logical binding required")
            projection = _retained_projection(
                self.db, self.owner.registry, self.owner.snapshot
            )
            self._logical_binding = (
                execution,
                prepared,
                derive_summary(prepared),
                projection,
                publication_check,
            )
            try:
                yield
            finally:
                self._logical_binding = None

        return bind()

    def _logical_projection(self):
        binding = getattr(self, "_logical_binding", None)
        return binding[3] if binding is not None else None

    def _logical_publication(self, actor, fence, outputs, result, run):
        ids = self._logical_requirements
        if not ids:
            return
        binding = getattr(self, "_logical_binding", None)
        if binding is None:
            raise ValueError("issued logical publication binding required")
        execution, prepared, expected, projection, _check = binding
        execution.recheck(actor, fence, prepared)
        validate_summary(result.get("logicalReads"), expected=expected)
        validate_summary(
            result.get("launch", {}).get("logicalReads"), expected=expected
        )
        validate_bound_record(
            self.db,
            self.owner.registry,
            self.owner.snapshot,
            run,
            fence,
            result,
            claim=self.ticket.claim.model_dump() if self.ticket.claim else None,
            terminal=True,
            outputs=outputs,
            _projection=projection,
        )

    def publish(self, actor, fence, outputs, result, **kwargs):
        """Final pure budget gate, immediately before canonical base publication.

        Host callbacks may inspect monotonic time and in-memory cancellation only;
        they return None or raise. Durable cancellation remains the base fence's
        responsibility. Never pass a callback that queries SQL or performs I/O.
        """
        if self._logical_requirements:
            binding = getattr(self, "_logical_binding", None)
            if binding is None or not self.db.in_transaction():
                raise ValueError("bound publication transaction required")
            check = binding[4]
            if check is not None and check() is not None:
                raise ValueError("publication check must return None or raise")
        return super().publish(actor, fence, outputs, result, **kwargs)
