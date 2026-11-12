"""Common Runtime SQL records; these rows do not grant compiler admission.

The service validates scoped identities, canonical bytes and authorization.
Registration and migrations belong to the common Database, never a side store.
"""

from typing import Optional

from pydantic.dataclasses import dataclass

from actions.server._models import _db_rules


@dataclass
class FoundryPackageRevision:
    id: str
    workspace_id: str
    package_id: str
    revision_id: str
    manifest_json: str
    source_artifact_digest: str
    source_inventory_json: str
    build_evidence_json: str
    _db_rules.foreign_keys.add("FoundryPackageRevision.workspace_id")
    _db_rules.indexes.add("FoundryPackageRevision.workspace_id")


@dataclass
class FoundryDeploymentRevision:
    id: str
    workspace_id: str
    deployment_id: str
    revision_id: str
    foundry_package_revision_id: Optional[str]
    selection_json: str
    snapshots_json: str
    _db_rules.foreign_keys.update(
        {
            "FoundryDeploymentRevision.workspace_id",
            "FoundryDeploymentRevision.foundry_package_revision_id",
        }
    )
    _db_rules.indexes.add("FoundryDeploymentRevision.workspace_id")


@dataclass
class FoundryDeploymentHead:
    id: str
    workspace_id: str
    deployment_id: str
    active_revision_id: str
    lock_version: int
    _db_rules.foreign_keys.add("FoundryDeploymentHead.workspace_id")
    _db_rules.indexes.add("FoundryDeploymentHead.workspace_id")


@dataclass
class FoundryRequest:
    id: str
    workspace_id: str
    principal_id: str
    operation: str
    idempotency_key: str
    request_fingerprint: str
    result_json: str
    _db_rules.foreign_keys.add("FoundryRequest.workspace_id")
    _db_rules.indexes.add("FoundryRequest.workspace_id")


@dataclass
class FoundryAudit:
    id: str
    workspace_id: str
    deployment_id: str
    principal_id: str
    operation: str
    foundry_request_id: str
    from_revision_id: str
    to_revision_id: str
    created_ms: str
    _db_rules.foreign_keys.update(
        {"FoundryAudit.workspace_id", "FoundryAudit.foundry_request_id"}
    )
    _db_rules.indexes.add("FoundryAudit.workspace_id")


@dataclass
class FoundryAccessGrant:
    id: str
    workspace_id: str
    principal_id: str
    subject_kind: str
    subject_id: str
    operations_json: str
    _db_rules.foreign_keys.add("FoundryAccessGrant.workspace_id")
    _db_rules.indexes.update(
        {"FoundryAccessGrant.workspace_id", "FoundryAccessGrant.principal_id"}
    )


MODEL_CLASSES = [
    FoundryPackageRevision,
    FoundryDeploymentRevision,
    FoundryDeploymentHead,
    FoundryRequest,
    FoundryAudit,
    FoundryAccessGrant,
]
