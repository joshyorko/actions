"""Normalized common Run extensions and trusted control-plane records."""

import hashlib
import json

from pydantic.dataclasses import dataclass

from actions.server._models import _db_rules


@dataclass
class Workspace:
    id: str
    state: str
    lock_version: int


@dataclass
class RunAdmission:
    id: str
    workspace_id: str
    deployment_id: str
    snapshot_json: str
    _db_rules.foreign_keys.add("RunAdmission.workspace_id")


@dataclass
class RunAccessGrant:
    id: str
    workspace_id: str
    deployment_id: str
    principal_id: str
    operations_json: str
    _db_rules.foreign_keys.add("RunAccessGrant.workspace_id")


@dataclass
class RunPin:
    id: str
    run_id: str
    workspace_id: str
    run_admission_id: str
    admission_principal_id: str
    request_fingerprint: str
    idempotency_id: str
    idempotency_key: str
    current_attempt_id: str
    epoch: int
    cancel_requested: int
    recovery_epoch: int
    recovery_receipt: str
    state_updated_ms: str
    _db_rules.foreign_keys.update(
        {"RunPin.run_id", "RunPin.workspace_id", "RunPin.run_admission_id"}
    )
    _db_rules.unique_indexes.update({"RunPin.run_id", "RunPin.idempotency_id"})


@dataclass
class RunAttempt:
    id: str
    run_id: str
    workspace_id: str
    owner_id: str
    epoch: int
    lease_deadline_ms: str
    heartbeat_ms: str
    state: str
    _db_rules.foreign_keys.update({"RunAttempt.run_id", "RunAttempt.workspace_id"})
    _db_rules.indexes.add("RunAttempt.run_id")


@dataclass
class RunOutput:
    id: str
    run_id: str
    workspace_id: str
    run_attempt_id: str
    epoch: int
    provider_key: str
    object_ref: str
    digest: str
    size: int
    name: str
    media_type: str
    state: str
    expires_ms: str
    _db_rules.foreign_keys.update(
        {"RunOutput.run_id", "RunOutput.workspace_id", "RunOutput.run_attempt_id"}
    )
    _db_rules.indexes.add("RunOutput.run_id")


@dataclass
class RunExecutionIntent:
    """Immutable dispatch metadata; Run/Attempt remain lifecycle authority."""

    id: str
    workspace_id: str
    actor_id: str
    envelope_json: str
    _db_rules.foreign_keys.add("RunExecutionIntent.workspace_id")


@dataclass(frozen=True)
class RunTaskReceipt:
    """Immutable operation/lifetime association; never Task lifecycle authority."""

    id: str
    run_id: str
    workspace_id: str
    admission_principal_id: str
    receipt_version: str
    original_method: str
    original_tool_name: str
    result_contract_version: str
    invocation_fingerprint: str
    created_ms: str
    ttl_ms: str
    ttl_policy_id: str
    _db_rules.foreign_keys.update(
        {"RunTaskReceipt.workspace_id", "RunTaskReceipt.run_id"}
    )
    _db_rules.unique_indexes.add("RunTaskReceipt.run_id")


def run_child_identity_digest(
    parent_run_id: str, binding_name: str, logical_key_digest: str
) -> str:
    """Return the stable identity key for a delegated child Run.

    Callers hash the Action-supplied logical key before persistence. Attempt
    identity is intentionally excluded; current-fence checks and the RunPin
    request fingerprint validate replay authorization and request consistency.
    """
    identity = json.dumps(
        [parent_run_id, binding_name, logical_key_digest],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(identity).hexdigest()


@dataclass(frozen=True)
class RunChildLineage:
    """Internal child-to-parent identity; this is not an MCP Task receipt.

    ``logical_key_digest`` and ``identity_digest`` are host-computed digests.
    The raw Action-supplied logical key is deliberately not persisted here.
    This record captures identity only; it does not grant execution or read
    authority and does not by itself make child admission atomic.
    """

    id: str
    workspace_id: str
    parent_run_id: str
    child_run_id: str
    binding_name: str
    logical_key_digest: str
    identity_digest: str
    _db_rules.unique_indexes.update(
        {
            "RunChildLineage.id",
            "RunChildLineage.child_run_id",
            "RunChildLineage.identity_digest",
        }
    )
    _db_rules.indexes.update(
        {"RunChildLineage.workspace_id", "RunChildLineage.parent_run_id"}
    )


MODEL_CLASSES = [
    Workspace,
    RunAdmission,
    RunAccessGrant,
    RunPin,
    RunAttempt,
    RunOutput,
    RunExecutionIntent,
    RunTaskReceipt,
    RunChildLineage,
]
