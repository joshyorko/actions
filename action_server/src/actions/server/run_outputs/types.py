"""Strict references; identities describe scope and never grant access."""

from __future__ import annotations

import base64
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from actions.server.deployments.ids import (
    CapabilityRef,
    DeploymentRevisionRef,
    ProviderProfileRevisionRef,
    RuntimePlanRef,
    WorkerProfileRevisionRef,
    WorkspacePolicyRevisionRef,
)


def canonical_uuid(value: str) -> str:
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("canonical UUID required")
    return value


class _Value(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )


class Actor(_Value):
    """Principal supplied by trusted authentication, never package/request JSON."""

    principal_id: str
    _principal = field_validator("principal_id")(canonical_uuid)


class ExecutionSnapshot(_Value):
    """Trusted control-plane registration; this type is not compiler admission."""

    deployment: DeploymentRevisionRef
    capability: CapabilityRef
    runtime_plan: RuntimePlanRef
    worker: WorkerProfileRevisionRef
    policy: WorkspacePolicyRevisionRef
    output_provider: ProviderProfileRevisionRef
    runtime_kind: str = Field(min_length=1, max_length=128)
    capability_schema_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    action_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def consistent_scope(self):
        ws = self.deployment.workspace_id
        if any(
            ref.workspace_id != ws
            for ref in (
                self.capability.package_revision,
                self.runtime_plan.package_revision,
                self.worker,
                self.policy,
                self.output_provider,
            )
        ):
            raise ValueError("snapshot Workspace mismatch")
        if self.capability.package_revision != self.runtime_plan.package_revision:
            raise ValueError("snapshot Package Revision mismatch")
        return self

    @property
    def workspace_id(self) -> str:
        return str(self.deployment.workspace_id.root)

    @property
    def deployment_id(self) -> str:
        return str(self.deployment.deployment_id.root)

    @property
    def provider_key(self) -> str:
        return (
            str(self.output_provider.provider_profile_id.root)
            + ":"
            + self.output_provider.revision_id.root
        )


class AttemptFence(_Value):
    run_id: str
    attempt_id: str
    owner_id: str
    epoch: int = Field(ge=1, le=2_147_483_647)
    _ids = field_validator("run_id", "attempt_id", "owner_id")(canonical_uuid)


class OutputRef(_Value):
    workspace_id: str
    run_id: str
    output_id: str
    _ids = field_validator("workspace_id", "run_id", "output_id")(canonical_uuid)

    @property
    def handle(self) -> str:
        return "art_" + base64.urlsafe_b64encode(UUID(self.output_id).bytes).decode(
            "ascii"
        ).rstrip("=")


def output_id_from_handle(handle: str) -> str:
    if (
        not isinstance(handle, str)
        or re.fullmatch(r"art_[A-Za-z0-9_-]{22}", handle) is None
    ):
        raise ValueError("invalid output handle")
    decoded = base64.urlsafe_b64decode(handle[4:] + "==")
    result = str(UUID(bytes=decoded))
    if OutputRef(workspace_id=result, run_id=result, output_id=result).handle != handle:
        raise ValueError("noncanonical output handle")
    return result


class SealReceipt(_Value):
    """Measured configured-provider receipt, not a caller byte declaration."""

    object_ref: str
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size: int = Field(ge=0, le=64 * 1024 * 1024)
    _object = field_validator("object_ref")(canonical_uuid)
