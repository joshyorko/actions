"""Strict immutable identifiers and explicit scope comparisons."""

from __future__ import annotations

import re
import unicodedata
import uuid
from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, RootModel, TypeAdapter, field_validator

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _uuid(value: Any) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    if not isinstance(value, str):
        raise ValueError("identifier must be a canonical UUID string")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("identifier must be a canonical UUID string") from exc
    if str(parsed) != value:
        raise ValueError("identifier must be a canonical lowercase UUID string")
    return parsed


class _UUIDId(RootModel[uuid.UUID]):
    model_config = ConfigDict(frozen=True, strict=True, revalidate_instances="always")

    @field_validator("root", mode="before")
    @classmethod
    def validate_uuid(cls, value: Any) -> uuid.UUID:
        return _uuid(value)


class WorkspaceId(_UUIDId):
    pass


class PackageId(_UUIDId):
    pass


class DeploymentId(_UUIDId):
    pass


class ProviderProfileId(_UUIDId):
    pass


class WorkerProfileId(_UUIDId):
    pass


class PolicyId(_UUIDId):
    pass


class _Digest(RootModel[str]):
    model_config = ConfigDict(frozen=True, strict=True, revalidate_instances="always")

    @field_validator("root")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError(
                "digest must use sha256 and 64 lowercase hexadecimal characters"
            )
        return value


class PolicyRevisionId(_Digest):
    pass


class PackageRevisionId(_Digest):
    pass


class DeploymentRevisionId(_Digest):
    pass


class ProviderProfileRevisionId(_Digest):
    pass


class WorkerProfileRevisionId(_Digest):
    pass


class PlanDigest(_Digest):
    pass


class _PackageLocalId(RootModel[str]):
    model_config = ConfigDict(frozen=True, strict=True, revalidate_instances="always")

    @field_validator("root")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if not value or value != unicodedata.normalize("NFC", value):
            raise ValueError("package-local identifier must be non-empty NFC text")
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("package-local identifier must be valid Unicode")
        return value


class CapabilityId(_PackageLocalId):
    pass


class BindingRequirementId(_PackageLocalId):
    pass


class _Ref(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )


class WorkspacePolicyRevisionRef(_Ref):
    workspace_id: WorkspaceId
    policy_id: PolicyId
    revision_id: PolicyRevisionId


class PackageRevisionRef(_Ref):
    workspace_id: WorkspaceId
    package_id: PackageId
    revision_id: PackageRevisionId


class DeploymentRevisionRef(_Ref):
    workspace_id: WorkspaceId
    deployment_id: DeploymentId
    revision_id: DeploymentRevisionId


class ProviderProfileRevisionRef(_Ref):
    workspace_id: WorkspaceId
    provider_profile_id: ProviderProfileId
    revision_id: ProviderProfileRevisionId


class WorkerProfileRevisionRef(_Ref):
    workspace_id: WorkspaceId
    worker_profile_id: WorkerProfileId
    revision_id: WorkerProfileRevisionId


class CapabilityRef(_Ref):
    package_revision: PackageRevisionRef
    capability_id: CapabilityId


class RuntimePlanRef(_Ref):
    package_revision: PackageRevisionRef
    plan_digest: PlanDigest


class BindingRequirementRef(_Ref):
    package_revision: PackageRevisionRef
    requirement_id: BindingRequirementId


WorkspaceScopedRef: TypeAlias = (
    WorkspacePolicyRevisionRef
    | PackageRevisionRef
    | DeploymentRevisionRef
    | ProviderProfileRevisionRef
    | WorkerProfileRevisionRef
    | CapabilityRef
    | RuntimePlanRef
    | BindingRequirementRef
)
PackageScopedRef: TypeAlias = CapabilityRef | RuntimePlanRef | BindingRequirementRef
_WORKSPACE_REF_ADAPTER: TypeAdapter[WorkspaceScopedRef] = TypeAdapter(
    WorkspaceScopedRef
)
_PACKAGE_REF_ADAPTER: TypeAdapter[PackageScopedRef] = TypeAdapter(PackageScopedRef)


def require_workspace_scope(
    ref: WorkspaceScopedRef, expected_workspace_id: WorkspaceId
) -> WorkspaceScopedRef:
    """Require an explicit workspace match; this does not check existence or access."""
    if not isinstance(ref, WorkspaceScopedRef):
        raise TypeError("ref must be a typed workspace-scoped reference")
    if not isinstance(expected_workspace_id, WorkspaceId):
        raise TypeError("expected_workspace_id must be WorkspaceId")
    expected_workspace_id = WorkspaceId.model_validate(expected_workspace_id)
    ref = _WORKSPACE_REF_ADAPTER.validate_python(ref)
    owner = getattr(ref, "workspace_id", None)
    package_revision = getattr(ref, "package_revision", None)
    if owner is None and isinstance(package_revision, PackageRevisionRef):
        owner = package_revision.workspace_id
    if owner != expected_workspace_id:
        raise ValueError("reference is outside the expected workspace scope")
    return ref


def require_package_scope(
    ref: PackageScopedRef, expected_package_revision: PackageRevisionRef
) -> PackageScopedRef:
    """Require an explicit package-revision match, including its workspace."""
    if not isinstance(ref, PackageScopedRef):
        raise TypeError("ref must be a typed package-scoped reference")
    if not isinstance(expected_package_revision, PackageRevisionRef):
        raise TypeError("expected_package_revision must be PackageRevisionRef")
    expected_package_revision = PackageRevisionRef.model_validate(
        expected_package_revision
    )
    ref = _PACKAGE_REF_ADAPTER.validate_python(ref)
    if ref.package_revision != expected_package_revision:
        raise ValueError("reference is outside the expected package revision scope")
    return ref
