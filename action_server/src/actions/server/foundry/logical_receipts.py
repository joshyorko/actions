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

from actions.server.data_queries.knowledge_values import KnowledgeRevisionRef
from actions.server.run_outputs.types import AttemptFence

if TYPE_CHECKING:
    from actions.server.foundry.logical_execution import PreparedLogicalReads

DISPATCH_V1 = "actions.generated-rcc-dispatch/v1"
DISPATCH_V2 = "actions.generated-rcc-dispatch/v2"
EXECUTION_V1 = "actions.generated-rcc-execution/v1"
EXECUTION_V2 = "actions.generated-rcc-execution/v2"
DISPATCH_V3 = "actions.generated-rcc-dispatch/v3"
EXECUTION_V3 = "actions.generated-rcc-execution/v3"
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


class LogicalOperationV2Identity(LogicalOperationIdentity):
    kind: Literal["data", "knowledge"]

    @field_validator("operation")
    @classmethod
    def exact_scan(cls, value):
        return _matches(
            value, re.compile(r"[a-z][a-z0-9_-]{0,58}\.(scan|ingest|search)/v1")
        )

    @model_validator(mode="after")
    def operation_kind(self):
        if self.operation.endswith(".scan/v1") != (self.kind == "data"):
            raise ValueError("logical operation kind differs")
        return self


class KnowledgeOperationEvidence(_Value):
    # The retained definition is host-selected; no credentials/config bytes.
    revision: "KnowledgeRevisionRef"
    corpus_handle: str = Field(alias="corpusHandle", pattern=r"^art_[A-Za-z0-9_-]{22}$")
    corpus_digest: str = Field(alias="corpusDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    corpus_output: str = Field(
        alias="corpusOutput", pattern=r"^knowledge-[0-9a-f]{64}\.json$"
    )
    source_fence: "AttemptFence" = Field(alias="sourceFence")


class LogicalOperationV2Receipt(LogicalOperationV2Identity):
    result_digest: str = Field(alias="resultDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    row_count: int = Field(alias="rowCount", ge=0, le=100000)
    parameters_digest: str = Field(
        alias="parametersDigest", pattern=r"^sha256:[0-9a-f]{64}$"
    )
    knowledge: KnowledgeOperationEvidence | None

    @model_validator(mode="after")
    def evidence_kind(self):
        if (self.knowledge is not None) != (self.kind == "knowledge"):
            raise ValueError("exact Knowledge operation evidence required")
        return self


class LogicalSummaryV2(LogicalReadSummary):
    version: Literal["actions.logical-receipt/v2"]  # type: ignore[assignment]
    operations: tuple[LogicalOperationV2Receipt, ...] = Field(  # type: ignore[assignment]
        min_length=1, max_length=MAX_OPERATIONS
    )


KnowledgeOperationEvidence.model_rebuild()


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
    if depth > 8:
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


def _parse(value) -> LogicalReadSummary | LogicalSummaryV2:
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
    model = (
        LogicalSummaryV2
        if json.loads(raw).get("version") == "actions.logical-receipt/v2"
        else LogicalReadSummary
    )
    return model.model_validate_json(raw)


def _requirements(requirement_ids: tuple[str, ...]) -> tuple[str, ...]:
    if type(requirement_ids) is not tuple or len(requirement_ids) > MAX_OPERATIONS:
        raise ValueError("bounded immutable requirement identity tuple required")
    for value in requirement_ids:
        _matches(value, _ID)
    if len(set(requirement_ids)) != len(requirement_ids):
        raise ValueError("duplicate requirement identity")
    return requirement_ids


def versions_for(
    requirement_ids: tuple[str, ...], *, knowledge: bool = False
) -> tuple[str, str]:
    """Select only from trusted artifact-verified capability requirement IDs."""
    ids = _requirements(requirement_ids)
    if not isinstance(knowledge, bool) or (knowledge and not ids):
        raise ValueError("verified Knowledge selection requires bindings")
    if knowledge:
        return DISPATCH_V3, EXECUTION_V3
    return (DISPATCH_V2, EXECUTION_V2) if ids else (DISPATCH_V1, EXECUTION_V1)


def validate_generated_version(
    record: dict,
    *,
    requirement_ids: tuple[str, ...],
    terminal: bool,
    knowledge: bool = False,
) -> None:
    """Partial check ONLY: does not validate any envelope fields or authorize it."""
    if not isinstance(terminal, bool) or not isinstance(record, dict):
        raise ValueError("generated receipt version unavailable")
    expected = versions_for(requirement_ids, knowledge=knowledge)[int(terminal)]
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
        version2 = (
            json.loads(prepared.context).get("version") == "actions.logical-context/v2"
        )
        return _parse(
            {
                "version": "actions.logical-receipt/v2"
                if version2
                else "actions.logical-read-receipt/v1",
                "contextDigest": prepared.context_digest,
                "operations": [
                    {
                        "requirementId": row.requirement_id,
                        "operation": row.operation,
                        "sourceRevision": row.source_revision,
                        "contractDigest": row.contract_digest,
                        "resultDigest": row.result_digest,
                        "rowCount": row.row_count,
                        **(
                            {
                                "kind": row.kind,
                                "parametersDigest": row.parameters_digest
                                or "sha256:" + hashlib.sha256(b"{}").hexdigest(),
                                "knowledge": row.knowledge.model_dump(mode="json")
                                if row.knowledge is not None
                                else None,
                            }
                            if version2
                            else {}
                        ),
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
        if type(expected) not in (LogicalReadSummary, LogicalSummaryV2):
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
                type(op) not in (LogicalOperationIdentity, LogicalOperationV2Identity)
                for op in expected_operations
            )
        ):
            raise ValueError("trusted operation identity tuple required")
        expected = tuple(
            type(op).model_validate_json(_canonical(op.model_dump(mode="json")))
            for op in expected_operations
        )
        keys = [(op.requirement_id, op.operation) for op in expected]
        if len(set(keys)) != len(keys) or {op.requirement_id for op in expected} != set(
            requirements
        ):
            raise ValueError("expected operation coverage differs")
        parsed = _parse(value)
        identity_type = (
            LogicalOperationV2Identity
            if type(parsed) is LogicalSummaryV2
            else LogicalOperationIdentity
        )
        if any(type(op) is not identity_type for op in expected):
            raise ValueError("logical summary version differs from verified operations")
        actual = tuple(
            identity_type(
                requirementId=op.requirement_id,
                operation=op.operation,
                sourceRevision=op.source_revision,
                contractDigest=op.contract_digest,
                **(
                    {"kind": op.kind}
                    if isinstance(op, LogicalOperationV2Receipt)
                    else {}
                ),
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


def has_knowledge(registry, snapshot) -> bool:
    """Determine the new protocol from immutable verified declarations only."""
    declaration = registry.get_capability(snapshot.capability)
    if declaration is None:
        raise ValueError("immutable capability unavailable")
    found = False
    for reference in declaration.binding_requirements:
        projected = registry.get_binding_requirement(reference)
        if projected is None or projected.ref != reference:
            raise ValueError("immutable logical requirement unavailable")
        if projected.contract.kind == "knowledge":
            if projected.contract.invocations is None:
                raise ValueError("explicit Knowledge invocation mapping required")
            found = True
        elif projected.contract.kind != "data":
            raise ValueError("supported logical requirement required")
    return found


def versions_for_selection(registry, snapshot, *, projection=None) -> tuple[str, str]:
    # Retained package kind selects the protocol, never an untrusted journal tag.
    # This path reads only SQL metadata; artifact verification remains with execution.
    db = getattr(registry, "_db", None)
    if db is not None:
        from actions.server.foundry.robot_retained_projection import (
            robot_projection_if_present,
        )

        if robot_projection_if_present(db, snapshot) is not None:
            from actions.server.foundry.robot_execution import DISCRIMINATOR
            from actions.server.foundry.robot_runtime_runner import TERMINAL_VERSION

            return DISCRIMINATOR, TERMINAL_VERSION
    if projection is not None:
        if projection.snapshot != snapshot:
            raise ValueError("retained version selection differs")
        return versions_for(projection.requirement_ids, knowledge=projection.knowledge)
    return versions_for(
        requirement_ids(registry, snapshot), knowledge=has_knowledge(registry, snapshot)
    )


def _retained_projection(
    db, registry, snapshot, *, run=None, _visited=(), _budget=None
):
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
    from actions.server.foundry.models import FoundryPackageRevision
    from actions.server.foundry.provider_execution import SQLRecordPin
    from actions.server.foundry.provider_models import (
        FoundryProviderRevision,
        FoundrySourceRevision,
    )
    from actions.server.foundry.provider_registry import _id, _ref_id
    from actions.server.run_outputs.service import _one

    if _budget is None:
        _budget = [64]
    _budget[0] -= 1
    if _budget[0] < 0 or len(_visited) > 8 or (run is not None and run.id in _visited):
        raise ValueError("bounded acyclic Knowledge source history required")
    declaration = registry.get_capability(snapshot.capability)
    stored = FoundryRepository(db).get_revision(snapshot.deployment)
    if declaration is None or stored is None:
        raise ValueError("immutable logical selection unavailable")
    knowledge = has_knowledge(registry, snapshot)
    expected, limits, requirements, providers, metadata_pins = [], {}, [], [], []
    for ref in declaration.binding_requirements:
        bindings = [
            b for b in stored.revision.specification.bindings if b.requirement == ref
        ]
        if len(bindings) != 1:
            raise ValueError("exact logical binding required")
        binding = bindings[0]
        projected = registry.get_binding_requirement(ref)
        if projected is None or projected.contract.kind not in ("data", "knowledge"):
            raise ValueError("artifact-verified data requirement required")
        requirements.append(projected.contract)
        providers.append((projected.contract.id, binding.provider))
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
            or descriptor.kind != projected.contract.kind
            or source.schema_version
            != (
                "actions.logical-source/v1"
                if descriptor.kind == "knowledge"
                else "actions.logical-source/v2"
            )
            or canonical(source) != source_row.manifest_json
            or source_row.id != _id(workspace + source.revision_id)
        ):
            raise ValueError("retained provider/source identity differs")
        metadata_pins.extend(
            (
                SQLRecordPin.capture(db, FoundryProviderRevision, "id=?", (row.id,)),
                SQLRecordPin.capture(
                    db, FoundrySourceRevision, "id=?", (source_row.id,)
                ),
            )
        )
        for operation in projected.contract.operations:
            if projected.contract.kind == "knowledge":
                from actions.server.data_queries.knowledge_operations import (
                    knowledge_contract,
                )

                knowledge_contract(operation)
                matches = [
                    op for op in descriptor.operations if op.name == operation.name
                ]
                supported = matches[0] if len(matches) == 1 else None
            else:
                supported, _ = scan_contract(descriptor, source, operation.name)
            if supported != operation:
                raise ValueError("retained operation contract differs")
            identity_type = (
                LogicalOperationV2Identity if knowledge else LogicalOperationIdentity
            )
            identity = identity_type(
                requirementId=ref.requirement_id.root,
                operation=operation.name,
                sourceRevision=source.revision_id,
                contractDigest=operation.contract_digest,
                **({"kind": projected.contract.kind} if knowledge else {}),
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
    for package in stored.revision.specification.package_revisions:
        metadata_pins.append(
            SQLRecordPin.capture(
                db,
                FoundryPackageRevision,
                "workspace_id=? AND package_id=? AND revision_id=?",
                (
                    str(package.workspace_id.root),
                    str(package.package_id.root),
                    package.revision_id.root,
                ),
            )
        )
    schema = registry.schema_for(snapshot)
    search_projections = []
    if knowledge and run is not None:
        from actions.server._models import Run
        from actions.server.deployments.logical_bindings import mapped_parameters
        from actions.server.run_outputs.models import RunOutput, RunPin
        from actions.server.run_outputs.service import RunOutputService
        from actions.server.run_outputs.types import output_id_from_handle

        seen_handles = set()
        for requirement in requirements:
            if requirement.kind != "knowledge":
                continue
            for operation in requirement.operations:
                if not operation.name.endswith(".search/v1"):
                    continue
                parameters = mapped_parameters(
                    requirement,
                    operation.name,
                    json.loads(schema.input_schema),
                    json.loads(run.inputs),
                )
                handle = parameters["ingestion_handle"]
                if handle in seen_handles:
                    continue
                seen_handles.add(handle)
                output = _one(db, RunOutput, output_id_from_handle(handle))
                source_run = _one(db, Run, output.run_id)
                source_pin = _one(db, RunPin, source_run.id)
                source_snapshot = RunOutputService(
                    db, {}, capabilities=registry
                )._pinned(source_pin)
                if source_snapshot.workspace_id != snapshot.workspace_id:
                    raise ValueError("Knowledge source Workspace differs")
                search_projections.append(
                    (
                        handle,
                        _retained_projection(
                            db,
                            registry,
                            source_snapshot,
                            run=source_run,
                            _visited=(*_visited, run.id),
                            _budget=_budget,
                        ),
                    )
                )
    return _RetainedProjection(
        snapshot,
        tuple(expected),
        tuple(limits.items()),
        tuple(fixed.items()),
        tuple(ref.requirement_id.root for ref in declaration.binding_requirements),
        knowledge,
        tuple(requirements),
        tuple(providers),
        schema.input_schema,
        declaration,
        stored,
        schema.output_schema,
        tuple(metadata_pins),
        tuple(search_projections),
    )


@dataclass(frozen=True)
class _RetainedProjection:
    snapshot: object
    operations: tuple
    limits: tuple
    fixed: tuple
    requirement_ids: tuple[str, ...]
    knowledge: bool = False
    requirements: tuple = ()
    providers: tuple = ()
    input_schema: str = ""
    declaration: object = None
    deployment: object = None
    output_schema: str = ""
    metadata_pins: tuple = ()
    search_projections: tuple = ()


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
    from actions.server.foundry.robot_retained_projection import (
        robot_projection_if_present,
    )
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import _canonical, _now, _one
    from actions.server.run_outputs.types import OutputRef, canonical_uuid

    if robot_projection_if_present(db, snapshot) is not None:
        from actions.server.foundry.robot_receipts import validate_robot_record

        return validate_robot_record(
            db,
            registry,
            snapshot,
            run,
            fence,
            record,
            claim=claim,
            terminal=terminal,
            outputs=outputs,
            _allow_expired_terminal=_allow_expired_terminal,
        )
    if terminal and isinstance(record, dict) and record.get("version") == FAILURE_V1:
        return validate_failed_record(
            db,
            registry,
            snapshot,
            run,
            fence,
            record,
            claim=claim,
            outputs=outputs,
            _projection=_projection,
            _allow_expired_terminal=_allow_expired_terminal,
        )
    ids = (
        _projection.requirement_ids
        if _projection is not None
        else requirement_ids(registry, snapshot)
    )
    expected_version = versions_for_selection(
        registry, snapshot, projection=_projection
    )[int(terminal)]
    if not isinstance(record, dict) or record.get("version") != expected_version:
        raise ValueError(
            "generated receipt version differs from capability requirements"
        )
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
        else _retained_projection(db, registry, snapshot, run=run)
    )
    if projection.snapshot != snapshot:
        raise ValueError("retained projection selection differs")
    for metadata_pin in projection.metadata_pins:
        metadata_pin.recheck(db)
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
    corpus_inventory = (
        _knowledge_inventory(
            db,
            registry,
            projection,
            summary,
            run,
            fence,
            allow_expired=_allow_expired_terminal,
        )
        if projection.knowledge
        else {}
    )
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
        or len(outputs) != 4 + len(corpus_inventory)
        or not isinstance(record["outputs"], list)
        or len(record["outputs"]) != 4 + len(corpus_inventory)
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
        if row.name in corpus_inventory and (
            row.media_type != "application/json" or not 1 <= row.size <= 8 * 1024 * 1024
        ):
            raise ValueError("Knowledge corpus output type or bounds differ")
        inventory[row.name] = evidence
    names = {
        "generated-action-result.json",
        "rcc-receipt.json",
        "rcc-stdout.log",
        "rcc-stderr.log",
    }
    names.update(corpus_inventory)
    for name, evidence in corpus_inventory.items():
        if (
            name not in inventory
            or inventory[name]["digest"] != evidence.corpus_digest
            or OutputRef.model_validate(inventory[name]["ref"]).handle
            != evidence.corpus_handle
        ):
            raise ValueError("Knowledge corpus inventory differs")
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


def _knowledge_inventory(
    db, registry, projection, summary, run, fence, *, allow_expired=False
):
    """Reconstruct mapped parameters and definition identities from immutable SQL."""
    from actions.server.data_queries.knowledge_values import canonical
    from actions.server.deployments.logical_bindings import mapped_parameters
    from actions.server.foundry.knowledge_authority import (
        KnowledgeRevisionAuthority,
        _id,
    )
    from actions.server.foundry.knowledge_models import KnowledgeCollectionRevision
    from actions.server.foundry.provider_registry import SqlProviderRegistry
    from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
    from actions.server.run_outputs.service import _one

    requirements = {item.id: item for item in projection.requirements}
    providers = dict(projection.providers)
    schema, inputs = json.loads(projection.input_schema), json.loads(run.inputs)
    inventory = {}
    for operation in summary.operations:
        requirement = requirements[operation.requirement_id]
        parameters = (
            mapped_parameters(requirement, operation.operation, schema, inputs)
            if operation.kind == "knowledge"
            else {}
        )
        if (
            operation.parameters_digest
            != "sha256:" + hashlib.sha256(_canonical(parameters)).hexdigest()
        ):
            raise ValueError("logical mapped parameters differ")
        if operation.kind != "knowledge":
            continue
        evidence = operation.knowledge
        # _load validates canonical retained definition, provider/source and registration audit SQL.
        provider_registry = SqlProviderRegistry(db, SqlFoundryAuthorization(db), None)
        authority = KnowledgeRevisionAuthority(db, provider_registry)
        spec = authority._load(evidence.revision)
        definition = _one(
            db, KnowledgeCollectionRevision, _id(canonical(evidence.revision))
        )
        if (
            spec.source_revision != operation.source_revision
            or definition.source_provider_json
            != providers[operation.requirement_id].model_dump_json()
            or str(evidence.revision.workspace_id.root)
            != projection.snapshot.workspace_id
        ):
            raise ValueError("Knowledge definition selection differs")
        if operation.operation.endswith(".ingest/v1"):
            from actions.server.foundry.generated_knowledge import operation_key

            name = (
                "knowledge-"
                + operation_key(
                    fence.run_id, operation.requirement_id, operation.operation
                )
                + ".json"
            )
            if (
                evidence.source_fence != fence
                or evidence.corpus_output != name
                or name in inventory
            ):
                raise ValueError("Knowledge ingestion fence or identity differs")
            inventory[name] = evidence
        else:
            if evidence.corpus_handle != parameters["ingestion_handle"]:
                raise ValueError("Knowledge search source differs from admitted input")
            source_projection = dict(projection.search_projections).get(
                evidence.corpus_handle
            )
            if source_projection is None:
                raise ValueError("verified Knowledge source projection required")
            _validate_search_source(
                db, registry, source_projection, evidence, allow_expired=allow_expired
            )
    return inventory


def _validate_search_source(db, registry, projection, evidence, *, allow_expired):
    from actions.server._models import Run, RunStatus
    from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
    from actions.server.run_outputs.service import _now, _one
    from actions.server.run_outputs.types import output_id_from_handle

    output = _one(db, RunOutput, output_id_from_handle(evidence.corpus_handle))
    source_run = _one(db, Run, output.run_id)
    pin = _one(db, RunPin, source_run.id)
    attempt = _one(db, RunAttempt, pin.current_attempt_id)
    actual_fence = AttemptFence(
        run_id=source_run.id,
        attempt_id=attempt.id,
        owner_id=attempt.owner_id,
        epoch=pin.epoch,
    )
    if (
        source_run.status != RunStatus.PASSED
        or attempt.state != "succeeded"
        or attempt.run_id != source_run.id
        or attempt.epoch != pin.epoch
        or actual_fence != evidence.source_fence
        or (not allow_expired and int(output.expires_ms) <= _now(db))
        or attempt.workspace_id != projection.snapshot.workspace_id
        or (output.name, output.digest)
        != (evidence.corpus_output, evidence.corpus_digest)
    ):
        raise ValueError("Knowledge source publication fence or corpus differs")
    outer = json.loads(source_run.result)
    if (
        not isinstance(outer, dict)
        or set(outer) != {"version", "result", "outputs"}
        or not isinstance(outer.get("result"), dict)
        or not isinstance(outer.get("outputs"), list)
    ):
        raise ValueError("closed Knowledge source publication required")
    record = outer["result"]
    validate_bound_record(
        db,
        registry,
        projection.snapshot,
        source_run,
        actual_fence,
        record,
        claim=record.get("claim"),
        terminal=True,
        outputs=outer["outputs"],
        _projection=projection,
        _allow_expired_terminal=True,
    )
    source_summary = _parse(record["logicalReads"])
    matches = [
        op
        for op in source_summary.operations
        if isinstance(op, LogicalOperationV2Receipt)
        and op.kind == "knowledge"
        and op.operation.endswith(".ingest/v1")
        and op.knowledge == evidence
    ]
    if len(matches) != 1:
        raise ValueError("exact successful generated Knowledge ingestion required")


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

        from actions.server._models import Run
        from actions.server.foundry.logical_execution import (
            LogicalExecution,
            PreparedLogicalReads,
        )
        from actions.server.run_outputs.service import _one

        @contextmanager
        def bind():
            if (
                getattr(self, "_logical_binding", None) is not None
                or getattr(self, "_robot_authority", None) is not None
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
                self.db,
                self.owner.registry,
                self.owner.snapshot,
                run=_one(execution.db, Run, prepared.fence.run_id),
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
        failed = getattr(self, "_failed_binding", None)
        return (
            binding[3]
            if binding is not None
            else (failed[0] if failed is not None else None)
        )

    def bind_generated_failure(self, record):
        """Cache immutable selection outside SQL; only trusted host supplies receipt."""
        from contextlib import contextmanager

        from actions.server._models import Run
        from actions.server.run_outputs.service import _canonical, _one

        @contextmanager
        def bind():
            if (
                self.db.in_transaction()
                or getattr(self, "_failed_binding", None) is not None
                or getattr(self, "_robot_authority", None) is not None
            ):
                raise ValueError("owned failure binding outside transaction required")
            projection = self._logical_projection() or _retained_projection(
                self.db,
                self.owner.registry,
                self.owner.snapshot,
                run=_one(self.db, Run, self.ticket.fence.run_id),
            )
            self._failed_binding = (projection, _canonical(record, 2 * 1024 * 1024))
            try:
                yield
            finally:
                self._failed_binding = None

        return bind()

    def _failed_publication(self, actor, fence, outputs, result, run):
        from actions.server.run_outputs.service import FenceRejected, _canonical

        binding = getattr(self, "_failed_binding", None)
        if binding is None or _canonical(result, 2 * 1024 * 1024) != binding[1]:
            raise FenceRejected(
                "issued failed execution binding required; reconciliation pending"
            )
        logical = getattr(self, "_logical_binding", None)
        if logical is not None:
            execution, prepared, expected, _projection, _check = logical
            execution.recheck(actor, fence, prepared)
            validate_summary(result["launch"]["logicalReads"], expected=expected)
        validate_failed_record(
            self.db,
            self.owner.registry,
            self.owner.snapshot,
            run,
            fence,
            result,
            claim=self.ticket.claim.model_dump() if self.ticket.claim else None,
            outputs=outputs,
            _projection=binding[0],
        )

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


def generated_output_names(record):
    """Output names after validate_bound_record; this helper grants no authority."""
    from actions.server.foundry.robot_runtime_runner import TERMINAL_VERSION

    if record.get("version") == TERMINAL_VERSION:
        from actions.server.foundry.robot_receipts import robot_output_names

        return robot_output_names(record)
    if record.get("version") == FAILURE_V1:
        return {"rcc-receipt.json", "rcc-stdout.log", "rcc-stderr.log"}
    names = {
        "generated-action-result.json",
        "rcc-receipt.json",
        "rcc-stdout.log",
        "rcc-stderr.log",
    }
    if record.get("version") == EXECUTION_V3:
        summary = _parse(record["logicalReads"])
        if type(summary) is not LogicalSummaryV2:
            raise ValueError("Knowledge summary required")
        names.update(
            op.knowledge.corpus_output
            for op in summary.operations
            if op.kind == "knowledge" and op.operation.endswith(".ingest/v1")
        )
    return names


FAILURE_V1 = "actions.generated-rcc-failure/v1"


def validate_failed_record(
    db,
    registry,
    snapshot,
    run,
    fence,
    record,
    *,
    claim,
    outputs,
    _projection=None,
    _allow_expired_terminal=False,
):
    """Closed failed-child receipt; SQL seals only, never a result or domain commit."""
    from actions.server._models import RunStatus
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import _canonical, _now, _one
    from actions.server.run_outputs.types import OutputRef, canonical_uuid

    projection = _projection or _retained_projection(db, registry, snapshot, run=run)
    if projection.snapshot != snapshot:
        raise ValueError("failed selection differs")
    for pin in projection.metadata_pins:
        pin.recheck(db)
    fixed = dict(projection.fixed)
    keys = {
        "version",
        "mode",
        "claim",
        "lineage",
        "launch",
        "publicationFence",
        "execution",
        "outputs",
    } | set(fixed)
    if (
        not isinstance(record, dict)
        or set(record) != keys
        or record["version"] != FAILURE_V1
    ):
        raise ValueError("closed generated failure required")
    if (
        run.id != fence.run_id
        or run.status == RunStatus.PASSED
        or not isinstance(_allow_expired_terminal, bool)
        or (_allow_expired_terminal and run.status != RunStatus.FAILED)
    ):
        raise ValueError("failed terminal state differs")
    from actions.server.run_outputs.models import RunAttempt, RunPin

    attempt = _one(db, RunAttempt, fence.attempt_id)
    pin = _one(db, RunPin, run.id)
    if (
        attempt.run_id != run.id
        or attempt.workspace_id != snapshot.workspace_id
        or attempt.owner_id != fence.owner_id
        or attempt.epoch != fence.epoch
        or pin.current_attempt_id != fence.attempt_id
        or pin.epoch != fence.epoch
        or attempt.state != ("failed" if run.status == RunStatus.FAILED else "running")
    ):
        raise ValueError("failed current Attempt differs")
    lineage = dict(
        packageRevision=snapshot.capability.package_revision.model_dump(mode="json"),
        runtimePlan=snapshot.runtime_plan.model_dump(mode="json"),
        workItemClaim=claim,
        runId=fence.run_id,
        attemptFence=fence.model_dump(),
    )
    launch = record["launch"]
    launch_keys = {"id", "workItemClaim", "lineage", "inputDigest"} | set(fixed)
    if projection.requirement_ids:
        launch_keys.add("logicalReads")
    if not isinstance(launch, dict) or set(launch) != launch_keys:
        raise ValueError("closed failed launch required")
    canonical_uuid(launch["id"])
    if (
        record["mode"] != ("work-items" if claim else "standalone")
        or _canonical(record["claim"], 4096) != _canonical(claim, 4096)
        or _canonical(launch["workItemClaim"], 4096) != _canonical(claim, 4096)
        or _canonical(record["publicationFence"], 4096)
        != _canonical(fence.model_dump(), 4096)
        or _canonical(record["lineage"], 16384) != _canonical(lineage, 16384)
        or _canonical(launch["lineage"], 16384) != _canonical(lineage, 16384)
        or launch["inputDigest"]
        != "sha256:"
        + hashlib.sha256(
            _canonical(json.loads(run.inputs), 262144).encode()
        ).hexdigest()
        or any(record[k] != v or launch[k] != v for k, v in fixed.items())
    ):
        raise ValueError("failed immutable lineage differs")
    if projection.requirement_ids:
        _projected_summary(projection, launch["logicalReads"])
    carrier = json.loads(
        run.result, object_pairs_hook=_pairs, parse_constant=_no_constant
    )
    if _canonical(carrier, 2 * 1024 * 1024) != run.result:
        raise ValueError("canonical failure carrier required")
    if run.status == RunStatus.FAILED:
        if (
            not isinstance(carrier, dict)
            or set(carrier) != {"version", "result", "outputs"}
            or (
                not isinstance(carrier["version"], int)
                or isinstance(carrier["version"], bool)
            )
            or carrier["version"] != 1
            or _canonical(carrier["result"], 2 * 1024 * 1024)
            != _canonical(record, 2 * 1024 * 1024)
        ):
            raise ValueError("failed terminal carrier differs")
    elif (
        not isinstance(carrier, dict)
        or set(carrier)
        not in (
            {"version", "mode", "claim", "fence", "launch"},
            {"version", "mode", "claim", "fence", "launch", "execution"},
        )
        or carrier.get("version")
        != versions_for_selection(registry, snapshot, projection=projection)[0]
        or carrier.get("execution") is not None
        or carrier.get("mode") != record["mode"]
        or carrier.get("launch") != launch
        or carrier.get("claim") != claim
        or carrier.get("fence") != fence.model_dump()
    ):
        raise ValueError("failed publication launch changed")
    execution = record["execution"]
    if (
        not isinstance(execution, dict)
        or set(execution)
        != {
            "status",
            "exitCode",
            "receiptDigest",
            "artifactDigest",
            "cleanup",
            "stdout",
            "stderr",
        }
        or execution["status"] != "failed"
        or (
            not isinstance(execution["exitCode"], int)
            or isinstance(execution["exitCode"], bool)
        )
        or execution["exitCode"] == 0
        or not -2147483648 <= execution["exitCode"] <= 2147483647
        or execution["artifactDigest"] != fixed["rccArtifactDigest"]
        or execution["cleanup"]
        != {
            "wrapperReaped": True,
            "descendantSnapshotComplete": True,
            "executionStopped": True,
        }
        or any(not isinstance(v, bool) for v in execution["cleanup"].values())
    ):
        raise ValueError("proven child failure and complete cleanup required")
    _matches(execution["receiptDigest"], _DIGEST)
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
            raise ValueError("closed failed stream measurement required")
        _matches(measured["digest"], _DIGEST)
        if (
            any(
                (not isinstance(measured[k], int) or isinstance(measured[k], bool))
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
            raise ValueError("failed stream measurement differs")
    if (
        not isinstance(outputs, (list, tuple))
        or len(outputs) != 3
        or not isinstance(record["outputs"], list)
        or len(record["outputs"]) != 3
    ):
        raise ValueError("exact failure diagnostic inventory required")
    inventory = {}
    for raw, evidence in zip(outputs, record["outputs"]):
        ref = raw if isinstance(raw, OutputRef) else OutputRef.model_validate(raw)
        row = _one(db, RunOutput, ref.output_id)
        if (
            not isinstance(evidence, dict)
            or set(evidence) != {"name", "ref", "digest", "size"}
            or ref.run_id != run.id
            or ref.workspace_id != snapshot.workspace_id
            or evidence["ref"] != ref.model_dump(mode="json")
            or row.run_id != run.id
            or row.workspace_id != snapshot.workspace_id
            or row.run_attempt_id != fence.attempt_id
            or row.epoch != fence.epoch
            or row.provider_key != snapshot.provider_key
            or row.state
            != ("final" if run.status == RunStatus.FAILED else "provisional")
            or (not _allow_expired_terminal and int(row.expires_ms) <= _now(db))
            or (
                not isinstance(evidence["size"], int)
                or isinstance(evidence["size"], bool)
            )
            or evidence["size"] < 0
            or (evidence["name"], evidence["digest"], evidence["size"])
            != (row.name, row.digest, row.size)
            or row.name in inventory
        ):
            raise ValueError("failed diagnostic seal differs")
        limit = 1024 * 1024 if row.name == "rcc-receipt.json" else 256 * 1024
        media = (
            "application/json"
            if row.name == "rcc-receipt.json"
            else "application/octet-stream"
        )
        if row.size > limit or row.media_type != media:
            raise ValueError("bounded typed diagnostic required")
        inventory[row.name] = evidence
    if (
        set(inventory) != {"rcc-receipt.json", "rcc-stdout.log", "rcc-stderr.log"}
        or execution["receiptDigest"] != inventory["rcc-receipt.json"]["digest"]
    ):
        raise ValueError("failed diagnostic inventory differs")
    for stream in ("stdout", "stderr"):
        if (execution[stream]["digest"], execution[stream]["retainedBytes"]) != (
            inventory[f"rcc-{stream}.log"]["digest"],
            inventory[f"rcc-{stream}.log"]["size"],
        ):
            raise ValueError("failed stream measurement differs")
