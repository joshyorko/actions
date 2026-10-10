"""Normalized common Run extensions and trusted control-plane records."""

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


MODEL_CLASSES = [Workspace, RunAdmission, RunAccessGrant, RunPin, RunAttempt, RunOutput]
