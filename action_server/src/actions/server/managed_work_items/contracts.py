"""Closed client contract for #132; identifiers and DTOs confer no authority.

Legacy /api/work-items on published Runtime1.0.4 is local CRUD, not this
managed protocol. A client must negotiate authenticated capabilities and must
not infer distributed support from version, an import or FileAdapter presence.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated, Literal, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from actions.server.data_queries.review import ReviewProposal
from actions.server.deployments.ids import (
    DeploymentId,
    DeploymentRevisionRef,
    WorkspaceId,
)
from actions.server.run_outputs.types import Actor, ExecutionSnapshot, canonical_uuid

CONTRACT_VERSION = "actions.managed-work-items/v1"
API_PREFIX = "/api/managed-work-items/v1"
MINIMUM_RUNTIME = "1.1.0a13"
MINIMUM_SDK = "0.5.0a1"


class Permission(StrEnum):
    READ = "work_items.read"
    ENQUEUE = "work_items.enqueue"
    CLAIM = "work_items.claim"
    COMPLETE = "work_items.complete"
    RETRY = "work_items.retry"
    CANCEL = "work_items.cancel"
    REVIEW = "work_items.review"
    ARTIFACT_READ = "work_items.artifact.read"


class Operation(StrEnum):
    QUEUES = "queues.list"
    LIST = "items.list"
    GET = "items.get"
    ENQUEUE = "items.enqueue"
    CLAIM = "items.claim"
    RENEW = "items.renew"
    COMPLETE = "items.complete"
    RETRY = "items.retry"
    CANCEL = "items.cancel"
    REVIEWS = "reviews.list"
    DECIDE = "reviews.decide"
    RUN = "runs.get"
    LOGS = "runs.logs"
    ARTIFACT = "artifacts.read"


OPERATION_PERMISSION = {
    Operation.QUEUES: Permission.READ,
    Operation.LIST: Permission.READ,
    Operation.GET: Permission.READ,
    Operation.ENQUEUE: Permission.ENQUEUE,
    Operation.CLAIM: Permission.CLAIM,
    Operation.RENEW: Permission.CLAIM,
    Operation.COMPLETE: Permission.COMPLETE,
    Operation.RETRY: Permission.RETRY,
    Operation.CANCEL: Permission.CANCEL,
    Operation.REVIEWS: Permission.REVIEW,
    Operation.DECIDE: Permission.REVIEW,
    Operation.RUN: Permission.READ,
    Operation.LOGS: Permission.READ,
    Operation.ARTIFACT: Permission.ARTIFACT_READ,
}


class _Value(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )


class ManagedCaller(_Value):
    """Supplied by trusted Runtime authentication, never request JSON."""

    actor: Actor
    worker_id: str | None = None

    @model_validator(mode="after")
    def canonical_worker(self):
        if self.worker_id is not None:
            canonical_uuid(self.worker_id)
        return self


class QueueRef(_Value):
    workspace_id: WorkspaceId
    deployment: DeploymentRevisionRef
    queue_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")

    @model_validator(mode="after")
    def matching_workspace(self):
        if self.deployment.workspace_id != self.workspace_id:
            raise ValueError("queue Deployment belongs to another Workspace")
        return self


class ClaimRef(_Value):
    queue: QueueRef
    item_id: str
    owner_id: str
    epoch: int = Field(ge=1, le=2_147_483_647)

    @model_validator(mode="after")
    def canonical_claim(self):
        canonical_uuid(self.item_id)
        canonical_uuid(self.owner_id)
        return self


class Capabilities(_Value):
    schema_version: Literal[
        "actions.managed-work-items/v1"
    ] = "actions.managed-work-items/v1"
    runtime_version: str
    sdk_version: str
    workspace_id: WorkspaceId
    operations: tuple[Operation, ...]
    permissions: tuple[Permission, ...]
    backend: Literal["sqlite", "postgresql"]
    time_authority: Literal["database"] = "database"
    # Private invoice/review support is not silently advertised as a complete
    # general Work Items policy. Implementations declare the actual modes.
    modes: tuple[
        Literal[
            "reviewed", "producer", "consumer", "optional", "required-input", "none"
        ],
        ...,
    ]

    @model_validator(mode="after")
    def operations_are_authorized(self):
        if len(set(self.operations)) != len(self.operations) or len(
            set(self.permissions)
        ) != len(self.permissions):
            raise ValueError("duplicate managed capability")
        if any(
            OPERATION_PERMISSION[operation] not in self.permissions
            for operation in self.operations
        ):
            raise ValueError("advertised operation lacks its explicit permission")
        from actions.server._common.package_deps.pip_impl.pip_packaging_version import (
            Version,
        )

        if Version(self.runtime_version) < Version(MINIMUM_RUNTIME) or Version(
            self.sdk_version
        ) < Version(MINIMUM_SDK):
            raise ValueError(
                "managed capabilities require the declared candidate floor"
            )
        return self


Key = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]


class Queues(_Value):
    schema_version: Literal[
        "actions.managed-work-items/v1"
    ] = "actions.managed-work-items/v1"
    operation: Literal["queues.list"]
    workspace_id: WorkspaceId
    deployment_id: DeploymentId | None = None
    cursor: str | None = Field(default=None, max_length=4096)
    limit: int = Field(default=50, ge=1, le=100)


class _Command(_Value):
    schema_version: Literal[
        "actions.managed-work-items/v1"
    ] = "actions.managed-work-items/v1"
    queue: QueueRef

    @model_validator(mode="after")
    def bounded_finite_command(self):
        raw = json.dumps(
            self.model_dump(mode="json"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
        if len(raw) > 512 * 1024:
            raise ValueError("managed Work Item command exceeds the byte bound")
        return self


class Inspect(_Command):
    operation: Literal[
        "items.list",
        "items.get",
        "reviews.list",
        "runs.get",
        "runs.logs",
        "artifacts.read",
    ]
    item_id: str | None = None
    run_id: str | None = None
    artifact_handle: str | None = None
    cursor: str | None = Field(default=None, max_length=4096)
    limit: int = Field(default=50, ge=1, le=100)

    @model_validator(mode="after")
    def exact_target(self):
        expected = {
            "items.get": "item_id",
            "runs.get": "run_id",
            "runs.logs": "run_id",
            "artifacts.read": "artifact_handle",
        }.get(self.operation)
        for name in ("item_id", "run_id", "artifact_handle"):
            value = getattr(self, name)
            if name == expected:
                if not value:
                    raise ValueError("operation target is required")
                if name != "artifact_handle":
                    canonical_uuid(value)
                else:
                    from actions.server.run_outputs.types import output_id_from_handle

                    output_id_from_handle(value)
            elif value is not None:
                raise ValueError("unexpected target for managed inspection")
        return self


class Enqueue(_Command):
    operation: Literal["items.enqueue"]
    idempotency_key: Key
    snapshot: ExecutionSnapshot
    payload: JsonValue
    review: ReviewProposal | None = None

    @model_validator(mode="after")
    def exact_deployment(self):
        if self.snapshot.deployment != self.queue.deployment:
            raise ValueError("enqueue snapshot differs from the queue Deployment")
        return self


class Claim(_Command):
    operation: Literal["items.claim"]
    idempotency_key: Key
    lease_seconds: int = Field(ge=1, le=3600)
    # owner_id is deliberately absent: use authenticated ManagedCaller.worker_id.


class Renew(_Command):
    operation: Literal["items.renew"]
    idempotency_key: Key
    claim: ClaimRef
    lease_seconds: int = Field(ge=1, le=3600)

    @model_validator(mode="after")
    def exact_queue(self):
        if self.claim.queue != self.queue:
            raise ValueError("claim belongs to another queue")
        return self


class Complete(_Command):
    operation: Literal["items.complete"]
    idempotency_key: Key
    claim: ClaimRef
    outcome: Literal["done", "business_failed", "application_failed"]
    output_payloads: tuple[JsonValue, ...] = Field(default=(), max_length=100)
    run_ids: tuple[str, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def exact_queue(self):
        if self.claim.queue != self.queue:
            raise ValueError("claim belongs to another queue")
        return self


class Intervention(_Command):
    operation: Literal["items.retry", "items.cancel"]
    idempotency_key: Key
    item_id: str
    expected_epoch: int = Field(ge=0, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=1024)
    reconciliation_receipt: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def canonical_item(self):
        canonical_uuid(self.item_id)
        return self


class Decide(_Command):
    operation: Literal["reviews.decide"]
    idempotency_key: Key
    proposal: ReviewProposal
    decision: Literal["approve", "reject"]

    @model_validator(mode="after")
    def exact_review_scope(self):
        if self.proposal.binding.scope.deployment != self.queue.deployment:
            raise ValueError("review belongs to another Deployment revision")
        return self


Command: TypeAlias = Annotated[
    Queues | Inspect | Enqueue | Claim | Renew | Complete | Intervention | Decide,
    Field(discriminator="operation"),
]


class ManagedWorkItemsPort(Protocol):
    """A transport adapter must inject the one real Runtime domain service."""

    def capabilities(
        self, caller: ManagedCaller, workspace_id: WorkspaceId
    ) -> Capabilities:
        ...

    def call(self, caller: ManagedCaller, command: Command) -> dict[str, JsonValue]:
        ...


Milliseconds = Annotated[str, Field(pattern=r"^[0-9]{1,20}$")]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
BusinessState: TypeAlias = Literal[
    "ready",
    "running",
    "blocked",
    "needs_review",
    "completed",
    "business_failed",
    "application_failed",
    "cancelled",
    "dead_letter",
    "unknown",
]


class ArtifactRef(_Value):
    handle: str
    run_id: str
    digest: Digest
    size: int = Field(ge=0, le=64 * 1024 * 1024)

    @model_validator(mode="after")
    def valid_identity(self):
        from actions.server.run_outputs.types import output_id_from_handle

        output_id_from_handle(self.handle)
        canonical_uuid(self.run_id)
        return self


class AttemptView(_Value):
    id: str
    owner_id: str
    epoch: int = Field(ge=1, le=2_147_483_647)
    state: Literal["running", "lost", "aborted", "succeeded", "failed", "cancelled"]
    lease_deadline_ms: Milliseconds

    @model_validator(mode="after")
    def valid_identity(self):
        canonical_uuid(self.id)
        canonical_uuid(self.owner_id)
        return self


class RunView(_Value):
    id: str
    snapshot: ExecutionSnapshot
    state: Literal["pending", "running", "succeeded", "failed", "cancelled", "blocked"]
    attempts: tuple[AttemptView, ...] = Field(default=(), max_length=100)
    artifacts: tuple[ArtifactRef, ...] = Field(default=(), max_length=100)
    result: JsonValue = None

    @model_validator(mode="after")
    def valid_identity(self):
        canonical_uuid(self.id)
        if any(artifact.run_id != self.id for artifact in self.artifacts):
            raise ValueError("artifact belongs to another Run")
        return self


class ItemView(_Value):
    queue: QueueRef
    id: str
    parent_id: str | None = None
    queue_state: Literal["PENDING", "IN_PROGRESS", "DONE", "FAILED"]
    business_state: BusinessState
    payload: JsonValue
    protected_input_digest: Digest
    snapshot: ExecutionSnapshot
    delivery_count: int = Field(ge=0, le=2_147_483_647)
    claim: ClaimRef | None = None
    lease_deadline_ms: Milliseconds | None = None
    available_after_ms: Milliseconds
    created_ms: Milliseconds
    run_ids: tuple[str, ...] = Field(default=(), max_length=100)
    child_ids: tuple[str, ...] = Field(default=(), max_length=100)
    review_id: str | None = None

    @model_validator(mode="after")
    def valid_identity(self):
        canonical_uuid(self.id)
        for value in (self.parent_id, self.review_id, *self.run_ids, *self.child_ids):
            if value is not None:
                canonical_uuid(value)
        if self.snapshot.deployment != self.queue.deployment:
            raise ValueError("Work Item admission differs from its queue")
        if self.claim is not None and (
            self.claim.queue != self.queue or self.claim.item_id != self.id
        ):
            raise ValueError("Work Item claim differs from the projected item")
        if (self.claim is None) != (self.lease_deadline_ms is None):
            raise ValueError("claim and lease deadline must appear together")
        return self


class QueueView(_Value):
    queue: QueueRef
    label: str = Field(min_length=1, max_length=256)
    mode: Literal["reviewed", "producer", "consumer", "optional", "required-input"]
    counts: dict[str, Annotated[int, Field(ge=0)]]
    permissions: tuple[Permission, ...]


class QueuePage(_Value):
    queues: tuple[QueueView, ...] = Field(max_length=100)
    next_cursor: str | None = None
    server_time_ms: Milliseconds


class ItemPage(_Value):
    items: tuple[ItemView, ...] = Field(max_length=100)
    next_cursor: str | None = None
    server_time_ms: Milliseconds


class ItemResult(_Value):
    item: ItemView
    replay: bool = False
    server_time_ms: Milliseconds


class ClaimResult(_Value):
    item: ItemView | None
    claim: ClaimRef | None
    lease_deadline_ms: Milliseconds | None
    server_time_ms: Milliseconds

    @model_validator(mode="after")
    def matching_item(self):
        if self.item is None:
            if self.claim is not None or self.lease_deadline_ms is not None:
                raise ValueError("empty queue result cannot contain a claim")
        elif (
            self.item.claim != self.claim
            or self.item.lease_deadline_ms != self.lease_deadline_ms
        ):
            raise ValueError("claim result differs from its Work Item")
        return self


class ReviewView(_Value):
    proposal: ReviewProposal
    state: Literal["pending", "approved", "rejected", "cancelled"]
    work_item_id: str | None = None

    @model_validator(mode="after")
    def valid_identity(self):
        if self.work_item_id is not None:
            canonical_uuid(self.work_item_id)
        if self.state in {"pending", "rejected"} and self.work_item_id is not None:
            raise ValueError("unapproved proposal must not manufacture a Work Item")
        return self


class ReviewPage(_Value):
    reviews: tuple[ReviewView, ...] = Field(max_length=100)
    next_cursor: str | None = None
    server_time_ms: Milliseconds


class ReviewResult(_Value):
    review: ReviewView
    replay: bool = False
    server_time_ms: Milliseconds


class RunResult(_Value):
    run: RunView
    server_time_ms: Milliseconds


class LogLine(_Value):
    offset: int = Field(ge=0)
    text: str = Field(max_length=8192)


class LogPage(_Value):
    run_id: str
    lines: tuple[LogLine, ...] = Field(max_length=100)
    next_cursor: str | None = None
    server_time_ms: Milliseconds


class ArtifactChunk(_Value):
    artifact: ArtifactRef
    offset: int = Field(ge=0)
    data_base64: str = Field(max_length=90_000)
    eof: bool
    next_cursor: str | None = None


RESULT_MODELS: dict[Operation, type[BaseModel]] = {
    Operation.QUEUES: QueuePage,
    Operation.LIST: ItemPage,
    Operation.GET: ItemResult,
    Operation.ENQUEUE: ItemResult,
    Operation.CLAIM: ClaimResult,
    Operation.RENEW: ClaimResult,
    Operation.COMPLETE: ItemResult,
    Operation.RETRY: ItemResult,
    Operation.CANCEL: ItemResult,
    Operation.REVIEWS: ReviewPage,
    Operation.DECIDE: ReviewResult,
    Operation.RUN: RunResult,
    Operation.LOGS: LogPage,
    Operation.ARTIFACT: ArtifactChunk,
}


def public_contract_schema() -> dict[str, JsonValue]:
    """Each named schema is a standalone JSON Schema document with local $defs."""
    from pydantic import TypeAdapter

    return {
        "contract_version": CONTRACT_VERSION,
        "api_prefix": API_PREFIX,
        "minimum_runtime": MINIMUM_RUNTIME,
        "minimum_sdk": MINIMUM_SDK,
        "commands": TypeAdapter(Command).json_schema(),
        "results": {
            operation.value: model.model_json_schema()
            for operation, model in RESULT_MODELS.items()
        },
    }


class QueueAuthorizationPort(Protocol):
    """Integration-owned live policy, distinct from Run/review/output grants."""

    def require_workspace(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, permission: Permission
    ) -> None:
        ...

    def require_queue(
        self, caller: ManagedCaller, queue: QueueRef, permission: Permission
    ) -> None:
        ...
