"""Managed Work Items over the existing Runtime SQL authority.

This adapter exposes the persisted invoice-review queue only. It does not open
the legacy Work Items database, create a queue/scheduler, or infer a grant from
an identifier. Mutation receipts use the existing shared FoundryRequest rows;
all queue, review, Run, Attempt and output mutations delegate to their existing
Runtime services.

Generic producer admission, client-supplied retry evidence and Run logs do not
have canonical Runtime primitives yet. Those operations remain unadvertised.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Callable
from uuid import uuid4

from actions.work_items import EmptyQueue, State
from actions.work_items._adapters._sql_review import FORMAT, SQLReviewQueue
from actions.work_items._fencing import (
    ClaimRejected,
    WorkItemClaim,
    payload_fingerprint,
)
from pydantic import TypeAdapter

from actions.server._database import Database
from actions.server._models import RUN_ID_COUNTER, Run, RunStatus
from actions.server.data_queries.invoice_worker import (
    InvoiceWorkerService,
    WorkerInput,
    WorkerTicket,
)
from actions.server.data_queries.review import (
    InvoiceReviewService,
    ReviewBinding,
    ReviewConflict,
    ReviewProposal,
)
from actions.server.data_queries.review_models import FencedWorkItem, InvoiceReview
from actions.server.deployments.ids import WorkspaceId
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import (
    OPERATION_PERMISSION,
    Capabilities,
    Claim,
    ClaimRef,
    ClaimResult,
    Command,
    Complete,
    Decide,
    Inspect,
    Intervention,
    ItemPage,
    ItemResult,
    ItemView,
    ManagedCaller,
    ManagedWorkItemsPort,
    Operation,
    Permission,
    QueuePage,
    QueueRef,
    QueueView,
    Queues,
    Renew,
    ReviewPage,
    ReviewResult,
    ReviewView,
    RunResult,
    RunView,
    AttemptView,
    ArtifactRef,
    ArtifactChunk,
)
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _canonical,
    _key,
    _lock_workspace,
    _now,
    _returning,
    _transaction,
    _one,
)
from actions.server.run_outputs.types import (
    Actor,
    CanvasResultScope,
    ExecutionSnapshot,
    OutputRef,
    output_id_from_handle,
)
from actions.server.managed_work_items.contracts import QueueAuthorizationPort


MAX_DISCOVERED_REVIEWS = 512
MAX_ATTEMPTS = 100
ARTIFACT_CHUNK_BYTES = 64 * 1024
_COMMAND_ADAPTER: TypeAdapter[Command] = TypeAdapter(Command)
_CURSOR_ID = re.compile(r"^[0-9a-f-]{36}$")
_ARTIFACT_CURSOR = re.compile(r"^(?:0|[1-9][0-9]{0,7})$")
_UNIMPLEMENTED = {Operation.ENQUEUE, Operation.RETRY, Operation.LOGS}


class SQLManagedWorkItemsService(ManagedWorkItemsPort):
    """Read and operate the existing review-backed Runtime SQL Work Items.

    Args:
        reviews: The canonical Runtime invoice review service, which owns the
            shared Database and the one SQLReviewQueue implementation.
        authorization: A trusted, live workspace/queue policy adapter supplied
            by the host. Missing authorization is always unavailable.
        worker_for: Optional trusted lookup for the existing invoice worker
            composition. It is required only for evidence-bound completion.

    Queue discovery is intentionally limited to Workspace/Deployment scopes
    already represented by canonical InvoiceReview rows. A general queue
    catalog is an explicit integration dependency, not inferred from client
    input or arbitrary SQL rows.
    """

    def __init__(
        self,
        reviews: InvoiceReviewService | None,
        authorization: QueueAuthorizationPort | None,
        *,
        worker_for: Callable[[CanvasResultScope], InvoiceWorkerService | None]
        | None = None,
    ) -> None:
        if reviews is None or authorization is None:
            raise ManagedError("unconfigured")
        if not isinstance(reviews, InvoiceReviewService):
            raise ManagedError("unconfigured")
        if not isinstance(reviews.db, Database):
            raise ManagedError("unconfigured")
        self.reviews = reviews
        self.db = reviews.db
        self.authorization = authorization
        self.worker_for = worker_for

    def capabilities(
        self, caller: ManagedCaller, workspace_id: WorkspaceId
    ) -> Capabilities:
        try:
            caller = ManagedCaller.model_validate(caller)
            workspace_id = WorkspaceId.model_validate(workspace_id)
            permissions = self._workspace_permissions(caller, workspace_id)
            scopes = self._known_scopes(workspace_id)
            worker_available = self._worker_available(scopes)
            operations = self._operations(
                permissions, worker_available, caller.worker_id is not None
            )
            from actions.server import __version__ as runtime_version

            from actions.work_items import __version__ as sdk_version

            return Capabilities(
                runtime_version=runtime_version,
                sdk_version=sdk_version,
                workspace_id=workspace_id,
                operations=operations,
                permissions=tuple(
                    permission for permission in Permission if permission in permissions
                ),
                backend=self._backend(),
                modes=("reviewed",),
            )
        except ManagedError:
            raise
        except AccessDenied:
            raise ManagedError("forbidden") from None
        except (TypeError, ValueError):
            raise ManagedError("unconfigured") from None
        except Exception:
            raise ManagedError("storage_unavailable") from None

    def call(self, caller: ManagedCaller, command: Command) -> dict[str, Any]:
        try:
            caller = ManagedCaller.model_validate(caller)
            command = _COMMAND_ADAPTER.validate_python(command)
            operation = Operation(command.operation)
            workspace_id = self._workspace_for(command)
            permission = OPERATION_PERMISSION[operation]
            self._require_workspace(caller, workspace_id, permission)
            if isinstance(command, Queues):
                return self._queues_page(caller, command).model_dump(mode="json")

            queue = command.queue
            self._require_queue(caller, queue, permission)
            if operation in _UNIMPLEMENTED:
                raise ManagedError("unsupported_operation")
            if operation == Operation.ARTIFACT:
                self._require_workspace(caller, workspace_id, Permission.READ)
                self._require_queue(caller, queue, Permission.READ)
            if operation in {
                Operation.LIST,
                Operation.GET,
                Operation.CLAIM,
                Operation.RENEW,
                Operation.COMPLETE,
                Operation.CANCEL,
                Operation.REVIEWS,
                Operation.DECIDE,
                Operation.RUN,
                Operation.ARTIFACT,
            }:
                self._require_workspace(caller, workspace_id, Permission.READ)
                self._require_queue(caller, queue, Permission.READ)

            if (
                isinstance(command, (Claim, Renew, Complete))
                and caller.worker_id is None
            ):
                raise ManagedError("forbidden")

            scope = self._scope_for_queue(queue)
            operation_set = self._operations(
                self._workspace_permissions(caller, workspace_id),
                self._worker_available(self._known_scopes(workspace_id)),
                caller.worker_id is not None,
            )
            if operation not in operation_set:
                raise ManagedError("unsupported_operation")

            if self._is_mutation(command):
                return self._mutate(caller, command, scope).model_dump(mode="json")
            return self._read(caller, command, scope).model_dump(mode="json")
        except ManagedError:
            raise
        except AccessDenied:
            raise ManagedError("forbidden") from None
        except (ClaimRejected, FenceRejected):
            raise ManagedError("stale_claim") from None
        except ReviewConflict:
            raise ManagedError("changed_input") from None
        except ValueError:
            raise
        except Exception:
            raise ManagedError("storage_unavailable") from None

    @staticmethod
    def _workspace_for(command: Command) -> WorkspaceId:
        if isinstance(command, Queues):
            return command.workspace_id
        return command.queue.workspace_id

    @staticmethod
    def _is_mutation(command: Command) -> bool:
        return isinstance(command, (Claim, Renew, Complete, Intervention, Decide))

    def _backend(self) -> str:
        if self.db.backend_name not in ("sqlite", "postgresql"):
            raise ManagedError("unconfigured")
        return self.db.backend_name

    def _workspace_permissions(
        self, caller: ManagedCaller, workspace_id: WorkspaceId
    ) -> set[Permission]:
        permissions: set[Permission] = set()
        for permission in Permission:
            try:
                self.authorization.require_workspace(caller, workspace_id, permission)
            except AccessDenied:
                continue
            except ManagedError as error:
                if error.code == "forbidden":
                    continue
                raise
            permissions.add(permission)
        return permissions

    def _operations(
        self,
        permissions: set[Permission],
        worker_available: bool,
        worker_identity_available: bool,
    ) -> tuple[Operation, ...]:
        operations: list[Operation] = []
        if Permission.READ in permissions:
            operations.extend(
                (
                    Operation.QUEUES,
                    Operation.LIST,
                    Operation.GET,
                    Operation.RUN,
                )
            )
        if Permission.READ in permissions and Permission.REVIEW in permissions:
            operations.extend((Operation.REVIEWS, Operation.DECIDE))
        if (
            Permission.READ in permissions
            and Permission.CLAIM in permissions
            and worker_identity_available
        ):
            operations.extend((Operation.CLAIM, Operation.RENEW))
        if Permission.READ in permissions and Permission.CANCEL in permissions:
            operations.append(Operation.CANCEL)
        if (
            Permission.READ in permissions
            and Permission.COMPLETE in permissions
            and worker_available
            and worker_identity_available
        ):
            operations.append(Operation.COMPLETE)
        if Permission.READ in permissions and Permission.ARTIFACT_READ in permissions:
            operations.append(Operation.ARTIFACT)
        return tuple(dict.fromkeys(operations))

    def _worker_available(self, scopes: dict[QueueRef, CanvasResultScope]) -> bool:
        if self.worker_for is None:
            return False
        return any(self.worker_for(scope) is not None for scope in scopes.values())

    def _require_workspace(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, permission: Permission
    ) -> None:
        try:
            self.authorization.require_workspace(caller, workspace_id, permission)
        except AccessDenied:
            raise ManagedError("forbidden") from None

    def _require_queue(
        self, caller: ManagedCaller, queue: QueueRef, permission: Permission
    ) -> None:
        try:
            self.authorization.require_queue(caller, queue, permission)
        except AccessDenied:
            raise ManagedError("forbidden") from None

    def _known_scopes(
        self, workspace_id: WorkspaceId
    ) -> dict[QueueRef, CanvasResultScope]:
        workspace = str(workspace_id.root)
        rows = self.db.select(
            InvoiceReview,
            "SELECT * FROM invoice_review WHERE workspace_id=? ORDER BY id LIMIT ?",
            [workspace, MAX_DISCOVERED_REVIEWS + 1],
        )
        if len(rows) > MAX_DISCOVERED_REVIEWS:
            raise ManagedError("storage_unavailable")
        scopes: dict[QueueRef, CanvasResultScope] = {}
        by_queue_id: dict[str, CanvasResultScope] = {}
        for row in rows:
            scope = self._binding(row).scope
            if (
                row.workspace_id != workspace
                or scope.application.workspace_id != workspace
                or str(scope.deployment.workspace_id.root) != workspace
            ):
                raise ManagedError("storage_unavailable")
            queue = self._queue_ref(scope)
            prior = by_queue_id.get(queue.queue_id)
            if prior is not None and prior != scope:
                raise ManagedError("storage_unavailable")
            by_queue_id[queue.queue_id] = scope
            scopes[queue] = scope
        return scopes

    def _queue_ref(self, scope: CanvasResultScope) -> QueueRef:
        return QueueRef(
            workspace_id=WorkspaceId.model_validate(scope.application.workspace_id),
            deployment=scope.deployment,
            queue_id=self.reviews.queue(scope).queue_name,
        )

    def _scope_for_queue(self, queue: QueueRef) -> CanvasResultScope:
        known = self._known_scopes(queue.workspace_id)
        scope = known.get(queue)
        if scope is None:
            raise ManagedError("not_found")
        return scope

    @staticmethod
    def _binding(row: InvoiceReview) -> ReviewBinding:
        try:
            binding = ReviewBinding.model_validate_json(row.binding_json)
            if _canonical(binding.model_dump(mode="json"), 65536) != row.binding_json:
                raise ValueError("noncanonical review binding")
            return binding
        except Exception:
            raise ManagedError("storage_unavailable") from None

    @staticmethod
    def _proposal(row: InvoiceReview) -> ReviewProposal:
        return ReviewProposal(
            review_id=row.id, binding=SQLManagedWorkItemsService._binding(row)
        )

    def _queue(self, scope: CanvasResultScope) -> SQLReviewQueue:
        return self.reviews.queue(scope)

    def _queues_page(self, caller: ManagedCaller, command: Queues) -> QueuePage:
        if command.cursor is not None and not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}", command.cursor
        ):
            raise ValueError("invalid queue cursor")
        known = self._known_scopes(command.workspace_id)
        entries = []
        for queue, scope in known.items():
            if (
                command.deployment_id is not None
                and queue.deployment.deployment_id != command.deployment_id
            ):
                continue
            if command.cursor is not None and queue.queue_id <= command.cursor:
                continue
            if not self._queue_permission(caller, queue, Permission.READ):
                continue
            entries.append((queue, scope))
        entries.sort(key=lambda item: item[0].queue_id)
        visible, more = entries[: command.limit], len(entries) > command.limit
        views = tuple(
            self._queue_view(caller, queue, scope) for queue, scope in visible
        )
        return QueuePage(
            queues=views,
            next_cursor=visible[-1][0].queue_id if more and visible else None,
            server_time_ms=str(_now(self.db)),
        )

    def _queue_permission(
        self, caller: ManagedCaller, queue: QueueRef, permission: Permission
    ) -> bool:
        try:
            self.authorization.require_workspace(caller, queue.workspace_id, permission)
            self.authorization.require_queue(caller, queue, permission)
            return True
        except AccessDenied:
            return False
        except ManagedError as error:
            if error.code == "forbidden":
                return False
            raise

    def _queue_view(
        self, caller: ManagedCaller, queue_ref: QueueRef, scope: CanvasResultScope
    ) -> QueueView:
        queue = self._queue(scope)
        # The canonical queue rejects unknown persisted row formats before the
        # projection counts them.
        queue.list_items()
        counts = {state.value: 0 for state in State}
        with self.db.cursor() as cursor:
            self.db.execute_query(
                cursor,
                "SELECT state,COUNT(*) FROM fenced_work_item WHERE workspace_id=? AND queue_name=? GROUP BY state",
                [str(queue_ref.workspace_id.root), queue_ref.queue_id],
            )
            for state, count in cursor.fetchall():
                if state not in counts:
                    raise ManagedError("storage_unavailable")
                counts[state] = int(count)
        permissions = tuple(
            permission
            for permission in Permission
            if self._queue_permission(caller, queue_ref, permission)
        )
        return QueueView(
            queue=queue_ref,
            label="Invoice review",
            mode="reviewed",
            counts=counts,
            permissions=permissions,
        )

    def _read(self, caller: ManagedCaller, command: Command, scope: CanvasResultScope):
        if isinstance(command, Inspect):
            operation = Operation(command.operation)
            if operation == Operation.LIST:
                return self._items_page(caller, command, scope)
            if operation == Operation.GET:
                row = self._item_row(command.queue, command.item_id or "")
                return ItemResult(
                    item=self._item_view(caller, command.queue, scope, row),
                    server_time_ms=str(_now(self.db)),
                )
            if operation == Operation.REVIEWS:
                return self._reviews_page(caller, command, scope)
            if operation == Operation.RUN:
                return RunResult(
                    run=self._run_view(
                        caller, command.queue, scope, command.run_id or ""
                    ),
                    server_time_ms=str(_now(self.db)),
                )
            if operation == Operation.ARTIFACT:
                return self._artifact_chunk(
                    caller,
                    command.queue,
                    scope,
                    command.artifact_handle or "",
                    command.cursor,
                )
            if operation == Operation.LOGS:
                raise ManagedError("unsupported_operation")
        raise ManagedError("unsupported_operation")

    def _items_page(
        self, caller: ManagedCaller, command: Inspect, scope: CanvasResultScope
    ) -> ItemPage:
        if command.cursor is not None and _CURSOR_ID.fullmatch(command.cursor) is None:
            raise ValueError("invalid Work Item cursor")
        queue = self._queue(scope)
        queue.list_items()  # includes the SDK's fail-closed format check
        rows = self.db.select(
            FencedWorkItem,
            "SELECT * FROM fenced_work_item WHERE workspace_id=? AND queue_name=? AND id>? ORDER BY id LIMIT ?",
            [
                str(command.queue.workspace_id.root),
                command.queue.queue_id,
                command.cursor or "",
                command.limit + 1,
            ],
        )
        if any(row.format != FORMAT for row in rows):
            raise ManagedError("storage_unavailable")
        more = len(rows) > command.limit
        page = rows[: command.limit]
        return ItemPage(
            items=tuple(
                self._item_view(caller, command.queue, scope, row) for row in page
            ),
            next_cursor=page[-1].id if more and page else None,
            server_time_ms=str(_now(self.db)),
        )

    def _reviews_page(
        self, caller: ManagedCaller, command: Inspect, scope: CanvasResultScope
    ) -> ReviewPage:
        if command.cursor is not None and _CURSOR_ID.fullmatch(command.cursor) is None:
            raise ValueError("invalid review cursor")
        workspace = str(command.queue.workspace_id.root)
        rows = self.db.select(
            InvoiceReview,
            "SELECT * FROM invoice_review WHERE workspace_id=? ORDER BY id LIMIT ?",
            [workspace, MAX_DISCOVERED_REVIEWS + 1],
        )
        if len(rows) > MAX_DISCOVERED_REVIEWS:
            raise ManagedError("storage_unavailable")
        selected: list[InvoiceReview] = []
        for row in rows:
            proposal = self._proposal(row)
            if proposal.binding.scope != scope:
                continue
            if command.cursor is not None and row.id <= command.cursor:
                continue
            selected.append(row)
        visible, more = selected[: command.limit], len(selected) > command.limit
        views = []
        for row in visible:
            proposal = self._proposal(row)
            receipt = self.reviews.status(caller.actor, scope, proposal)
            views.append(
                ReviewView(
                    proposal=proposal,
                    state=receipt.state,
                    work_item_id=receipt.work_item_id,
                )
            )
        return ReviewPage(
            reviews=tuple(views),
            next_cursor=visible[-1].id if more and visible else None,
            server_time_ms=str(_now(self.db)),
        )

    def _item_row(self, queue: QueueRef, item_id: str) -> FencedWorkItem:
        rows = self.db.select(
            FencedWorkItem,
            "SELECT * FROM fenced_work_item WHERE id=? AND workspace_id=? AND queue_name=? LIMIT 2",
            [item_id, str(queue.workspace_id.root), queue.queue_id],
        )
        if not rows:
            raise ManagedError("not_found")
        if len(rows) != 1 or rows[0].format != FORMAT:
            raise ManagedError("storage_unavailable")
        return rows[0]

    def _review_for_item(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        row: FencedWorkItem,
    ) -> tuple[InvoiceReview, ReviewProposal, dict[str, Any]]:
        try:
            payload = self._queue(scope).load_payload(row.id)
            if (
                not isinstance(payload, dict)
                or set(payload) != {"schema", "review_id", "binding"}
                or payload.get("schema") != "actions.invoice-review/v1"
                or not isinstance(payload.get("review_id"), str)
                or not isinstance(payload.get("binding"), dict)
            ):
                raise ValueError("unknown reviewed queue payload")
            rows = self.db.select(
                InvoiceReview,
                "SELECT * FROM invoice_review WHERE id=? AND workspace_id=? AND work_item_id=? LIMIT 2",
                [payload["review_id"], str(queue.workspace_id.root), row.id],
            )
            if len(rows) != 1:
                raise ValueError("Work Item has no unique review owner")
            review = rows[0]
            proposal = self._proposal(review)
            if proposal.binding.scope != scope or proposal.model_dump(mode="json") != {
                "review_id": payload["review_id"],
                "binding": payload["binding"],
            }:
                raise ValueError("Work Item review binding differs")
            receipt = self.reviews.status(caller.actor, scope, proposal)
            if receipt.work_item_id != row.id or receipt.state not in (
                "approved",
                "cancelled",
            ):
                raise ValueError("review has not admitted this Work Item")
            return review, proposal, payload
        except ManagedError:
            raise
        except AccessDenied:
            raise
        except Exception:
            raise ManagedError("storage_unavailable") from None

    def _source_snapshot(
        self, caller: ManagedCaller, queue: QueueRef, proposal: ReviewProposal
    ) -> ExecutionSnapshot:
        try:
            pin = _one(self.db, RunPin, proposal.binding.run_id)
            snapshot = self.reviews.outputs._pinned(pin)
            if (
                snapshot.deployment != queue.deployment
                or snapshot.workspace_id != str(queue.workspace_id.root)
                or snapshot.canvas_application != proposal.binding.scope.application
            ):
                raise AccessDenied("Run/output unavailable or access denied")
            self.reviews.outputs._authorize(caller.actor, snapshot, "read")
            return snapshot
        except AccessDenied:
            raise
        except Exception:
            raise ManagedError("storage_unavailable") from None

    def _worker_run(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        proposal: ReviewProposal,
        item_id: str,
    ) -> tuple[RunPin, Run, ExecutionSnapshot, WorkerInput] | None:
        from actions.server.data_queries.invoice_worker import work_item_run_key

        key = work_item_run_key(item_id)
        idempotency_id = _key(
            "actions.workspace-run-idempotency/v1", str(queue.workspace_id.root), key
        )
        pins = self.db.select(
            RunPin,
            "SELECT * FROM run_pin WHERE idempotency_id=? LIMIT 2",
            [idempotency_id],
        )
        if not pins:
            return None
        if len(pins) != 1 or pins[0].idempotency_key != key:
            raise ManagedError("storage_unavailable")
        pin = pins[0]
        run = _one(self.db, Run, pin.run_id)
        snapshot = self.reviews.outputs._pinned(pin)
        try:
            worker_input = WorkerInput.model_validate_json(run.inputs)
            if (
                worker_input.proposal != proposal
                or worker_input.initial_claim.item_id != item_id
                or snapshot.deployment != queue.deployment
                or snapshot.workspace_id != str(queue.workspace_id.root)
                or snapshot.canvas_application != proposal.binding.scope.application
            ):
                raise ValueError("worker Run differs from reviewed Work Item")
            self.reviews.outputs._authorize(caller.actor, snapshot, "read")
        except AccessDenied:
            raise
        except Exception:
            raise ManagedError("storage_unavailable") from None
        return pin, run, snapshot, worker_input

    def _item_view(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        row: FencedWorkItem,
    ) -> ItemView:
        review, proposal, payload = self._review_for_item(caller, queue, scope, row)
        snapshot = self._source_snapshot(caller, queue, proposal)
        execution = self.reviews.execution(caller.actor, scope, proposal)
        run_ids: tuple[str, ...] = ()
        associated = self._worker_run(caller, queue, proposal, row.id)
        if associated is not None:
            run_ids = (associated[1].id,)
        try:
            digest = payload_fingerprint(payload)
        except Exception:
            raise ManagedError("storage_unavailable") from None
        claim = None
        deadline = None
        if (
            row.state == State.IN_PROGRESS.value
            and row.claim_owner
            and not row.cancel_requested
        ):
            claim = ClaimRef(
                queue=queue,
                item_id=row.id,
                owner_id=row.claim_owner,
                epoch=row.claim_epoch,
            )
            deadline = str(row.claim_deadline_ms)
        children = self.db.select(
            FencedWorkItem,
            "SELECT * FROM fenced_work_item WHERE workspace_id=? AND parent_id=? ORDER BY id LIMIT ?",
            [str(queue.workspace_id.root), row.id, 101],
        )
        if len(children) > 100:
            raise ManagedError("storage_unavailable")
        return ItemView(
            queue=queue,
            id=row.id,
            parent_id=row.parent_id or None,
            queue_state=row.state,
            business_state=self._business_state(row, review, execution),
            payload=payload,
            protected_input_digest=digest,
            snapshot=snapshot,
            delivery_count=row.claim_epoch,
            claim=claim,
            lease_deadline_ms=deadline,
            available_after_ms=str(row.created_ms),
            created_ms=str(row.created_ms),
            run_ids=run_ids,
            child_ids=tuple(child.id for child in children),
            review_id=review.id,
        )

    @staticmethod
    def _business_state(
        row: FencedWorkItem, review: InvoiceReview, execution: Any
    ) -> str:
        if review.state == "pending":
            return "needs_review"
        if review.state == "rejected":
            return "business_failed"
        if review.state == "cancelled":
            return "cancelled"
        phase = getattr(execution, "phase", "unknown")
        if row.state == State.PENDING.value:
            return "ready"
        if row.state == State.IN_PROGRESS.value:
            if phase == "blocked":
                return "blocked"
            return "running"
        if row.state == State.DONE.value and phase == "completed":
            return "completed"
        if row.state == State.FAILED.value:
            if phase == "dead_letter":
                return "dead_letter"
            if phase == "cancelled" or row.cancel_requested:
                return "cancelled"
            return "application_failed"
        return "unknown"

    def _review_view(
        self, caller: ManagedCaller, scope: CanvasResultScope, row: InvoiceReview
    ) -> ReviewView:
        proposal = self._proposal(row)
        receipt = self.reviews.status(caller.actor, scope, proposal)
        return ReviewView(
            proposal=proposal,
            state=receipt.state,
            work_item_id=receipt.work_item_id,
        )

    def _run_view(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        run_id: str,
    ) -> RunView:
        if not self._run_belongs_to_scope(caller, queue, scope, run_id):
            raise ManagedError("not_found")
        pin = _one(self.db, RunPin, run_id)
        snapshot = self.reviews.outputs._pinned(pin)
        self.reviews.outputs._authorize(caller.actor, snapshot, "read")
        run = _one(self.db, Run, run_id)
        state = {
            RunStatus.NOT_RUN: "pending",
            RunStatus.RUNNING: "running",
            RunStatus.PASSED: "succeeded",
            RunStatus.FAILED: "failed",
            RunStatus.CANCELLED: "cancelled",
        }.get(run.status)
        if state is None:
            raise ManagedError("storage_unavailable")
        result_value = None
        envelope = None
        if run.result:
            try:
                candidate = json.loads(run.result)
                if isinstance(candidate, dict):
                    envelope = candidate
                    if candidate.get("version") == 1:
                        result_value = candidate.get("result")
                    elif (
                        run.status == RunStatus.RUNNING
                        and candidate.get("effect", {}).get("state") == "blocked"
                    ):
                        state = "blocked"
            except (ValueError, TypeError):
                raise ManagedError("storage_unavailable") from None
        attempts = self.db.select(
            RunAttempt,
            "SELECT * FROM run_attempt WHERE run_id=? ORDER BY epoch LIMIT ?",
            [run_id, MAX_ATTEMPTS + 1],
        )
        if len(attempts) > MAX_ATTEMPTS:
            raise ManagedError("storage_unavailable")
        attempt_views = tuple(
            AttemptView(
                id=attempt.id,
                owner_id=attempt.owner_id,
                epoch=attempt.epoch,
                state=attempt.state,
                lease_deadline_ms=str(attempt.lease_deadline_ms),
            )
            for attempt in attempts
        )
        artifacts = self._run_artifacts(caller, queue, scope, run, envelope)
        return RunView(
            id=run.id,
            snapshot=snapshot,
            state=state,
            attempts=attempt_views,
            artifacts=artifacts,
            result=result_value,
        )

    def _run_belongs_to_scope(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        run_id: str,
    ) -> bool:
        if run_id not in self._scope_run_ids(caller, scope):
            return False
        try:
            pin = _one(self.db, RunPin, run_id)
            snapshot = self.reviews.outputs._pinned(pin)
            if (
                snapshot.deployment != queue.deployment
                or snapshot.workspace_id != str(queue.workspace_id.root)
                or snapshot.canvas_application != scope.application
            ):
                return False
            self.reviews.outputs._authorize(caller.actor, snapshot, "read")
            return True
        except AccessDenied:
            raise
        except Exception:
            return False

    def _scope_run_ids(
        self, caller: ManagedCaller, scope: CanvasResultScope
    ) -> set[str]:
        workspace = scope.application.workspace_id
        rows = self.db.select(
            InvoiceReview,
            "SELECT * FROM invoice_review WHERE workspace_id=? ORDER BY id LIMIT ?",
            [workspace, MAX_DISCOVERED_REVIEWS + 1],
        )
        if len(rows) > MAX_DISCOVERED_REVIEWS:
            raise ManagedError("storage_unavailable")
        run_ids: set[str] = set()
        for row in rows:
            proposal = self._proposal(row)
            if proposal.binding.scope != scope:
                continue
            receipt = self.reviews.status(caller.actor, scope, proposal)
            run_ids.add(row.run_id)
            if receipt.work_item_id:
                associated = self._worker_run(
                    caller,
                    self._queue_ref(scope),
                    proposal,
                    receipt.work_item_id,
                )
                if associated is not None:
                    run_ids.add(associated[1].id)
        return run_ids

    def _run_artifacts(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        run: Run,
        envelope: dict[str, Any] | None,
    ) -> tuple[ArtifactRef, ...]:
        if not (
            self._queue_permission(caller, queue, Permission.READ)
            and self._queue_permission(caller, queue, Permission.ARTIFACT_READ)
        ):
            return ()
        if not isinstance(envelope, dict) or envelope.get("version") != 1:
            return ()
        outputs = envelope.get("outputs")
        if not isinstance(outputs, list) or len(outputs) > 64:
            raise ManagedError("storage_unavailable")
        result = []
        for raw in outputs:
            try:
                ref = OutputRef.model_validate(raw)
                if ref.run_id != run.id or ref.workspace_id != str(
                    queue.workspace_id.root
                ):
                    raise ValueError("output scope mismatch")
                row = _one(self.db, RunOutput, ref.output_id)
                if (
                    row.run_id != run.id
                    or row.workspace_id != str(queue.workspace_id.root)
                    or row.state != "final"
                ):
                    raise ValueError("output is not final on this Run")
                if run.status not in (RunStatus.PASSED, RunStatus.FAILED) or int(
                    row.expires_ms
                ) <= _now(self.db):
                    continue
                result.append(
                    ArtifactRef(
                        handle=ref.handle,
                        run_id=run.id,
                        digest=row.digest,
                        size=row.size,
                    )
                )
            except Exception:
                raise ManagedError("storage_unavailable") from None
        return tuple(result)

    def _artifact_chunk(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        handle: str,
        cursor: str | None,
    ) -> ArtifactChunk:
        if cursor is not None and _ARTIFACT_CURSOR.fullmatch(cursor) is None:
            raise ValueError("invalid artifact cursor")
        output_id_from_handle(handle)
        offset = int(cursor or "0")
        with self.reviews.outputs.resolve(
            caller.actor,
            str(queue.workspace_id.root),
            handle,
            canvas_scope=scope,
        ) as output:
            if output.run_id not in self._scope_run_ids(caller, scope):
                raise ManagedError("not_found")
            if offset > output.size:
                raise ValueError("artifact cursor exceeds its size")
            skipped = 0
            while skipped < offset:
                chunk = output.read(min(ARTIFACT_CHUNK_BYTES, offset - skipped))
                if not chunk:
                    raise ManagedError("storage_unavailable")
                skipped += len(chunk)
            data = output.read(ARTIFACT_CHUNK_BYTES)
            next_offset = offset + len(data)
            eof = next_offset >= output.size
            ref = ArtifactRef(
                handle=handle,
                run_id=output.run_id,
                digest=output.digest,
                size=output.size,
            )
            return ArtifactChunk(
                artifact=ref,
                offset=offset,
                data_base64=base64.b64encode(data).decode("ascii"),
                eof=eof,
                next_cursor=None if eof else str(next_offset),
            )

    def _mutate(
        self,
        caller: ManagedCaller,
        command: Command,
        scope: CanvasResultScope,
    ):
        workspace = self._workspace_for(command)
        operation = Operation(command.operation)
        with _transaction(self.db):
            self._lock_workspace_for_mutation(workspace)
            permission = OPERATION_PERMISSION[operation]
            self._require_workspace(caller, workspace, permission)
            self._require_queue(caller, command.queue, permission)
            self._preflight_mutation(caller, command, scope)
            fingerprint = self._request_fingerprint(caller, command)
            prior = self._prior_request(caller, command)
            if prior is not None:
                if prior.request_fingerprint != fingerprint:
                    raise ManagedError("changed_input")
                self._validate_request_audit(caller, command, prior)
                try:
                    receipt = json.loads(prior.result_json)
                    if (
                        not isinstance(receipt, dict)
                        or receipt.get("schema")
                        != "actions.managed-work-items/request/v1"
                        or not isinstance(receipt.get("result"), dict)
                    ):
                        raise ValueError("invalid managed request receipt")
                    result = dict(receipt["result"])
                    if "replay" in result:
                        result["replay"] = True
                    replayed = self._result_model(operation).model_validate_json(
                        json.dumps(result, ensure_ascii=False, allow_nan=False)
                    )
                    if isinstance(command, Claim):
                        self._validate_claim_replay(caller, command, replayed, scope)
                    elif isinstance(command, Renew):
                        self._validate_renew_replay(caller, command, replayed, scope)
                    return replayed
                except ManagedError:
                    raise
                except Exception:
                    raise ManagedError("storage_unavailable") from None
            result = self._apply_mutation(caller, command, scope)
            receipt = _canonical(
                {
                    "schema": "actions.managed-work-items/request/v1",
                    "command": command.model_dump(mode="json"),
                    "result": result.model_dump(mode="json"),
                },
                512 * 1024,
            )
            request = FoundryRequest(
                id=str(uuid4()),
                workspace_id=str(workspace.root),
                principal_id=caller.actor.principal_id,
                operation="managed-work-items/v1/" + operation.value,
                idempotency_key=command.idempotency_key,
                request_fingerprint=fingerprint,
                result_json=receipt,
            )
            self.db.insert(request)
            deployment_revision = command.queue.deployment.revision_id.root
            self.db.insert(
                FoundryAudit(
                    id=str(uuid4()),
                    workspace_id=str(workspace.root),
                    deployment_id=str(command.queue.deployment.deployment_id.root),
                    principal_id=caller.actor.principal_id,
                    operation=request.operation,
                    foundry_request_id=request.id,
                    from_revision_id=deployment_revision,
                    to_revision_id=deployment_revision,
                    created_ms=str(_now(self.db)),
                )
            )
            return result

    def _validate_request_audit(
        self, caller: ManagedCaller, command: Command, request: FoundryRequest
    ) -> None:
        rows = self.db.select(
            FoundryAudit,
            "SELECT * FROM foundry_audit WHERE foundry_request_id=? LIMIT 2",
            [request.id],
        )
        revision_id = command.queue.deployment.revision_id.root
        if len(rows) != 1:
            raise ManagedError("storage_unavailable")
        audit = rows[0]
        if (
            audit.workspace_id != str(command.queue.workspace_id.root)
            or audit.deployment_id != str(command.queue.deployment.deployment_id.root)
            or audit.principal_id != caller.actor.principal_id
            or audit.operation != request.operation
            or audit.from_revision_id != revision_id
            or audit.to_revision_id != revision_id
        ):
            raise ManagedError("storage_unavailable")

    def _validate_claim_replay(
        self,
        caller: ManagedCaller,
        command: Claim,
        result: ClaimResult,
        scope: CanvasResultScope,
    ) -> None:
        claim = result.claim
        if claim is None:
            return
        if (
            claim.queue != command.queue
            or result.item is None
            or result.item.queue != command.queue
        ):
            raise ManagedError("storage_unavailable")
        self._require_worker(claim.owner_id, caller.worker_id)
        self._require_current_claim(command.queue, claim)
        row = self._item_row(command.queue, claim.item_id)
        self._review_for_item(caller, command.queue, scope, row)

    def _validate_renew_replay(
        self,
        caller: ManagedCaller,
        command: Renew,
        result: ClaimResult,
        scope: CanvasResultScope,
    ) -> None:
        if (
            result.claim != command.claim
            or result.item is None
            or result.item.queue != command.queue
        ):
            raise ManagedError("storage_unavailable")
        self._require_worker(command.claim.owner_id, caller.worker_id)
        self._require_current_claim(command.queue, command.claim)
        row = self._item_row(command.queue, command.claim.item_id)
        self._review_for_item(caller, command.queue, scope, row)

    def _preflight_mutation(
        self,
        caller: ManagedCaller,
        command: Command,
        scope: CanvasResultScope,
    ) -> None:
        if isinstance(command, Decide):
            self._authorize_review(caller.actor, scope, command.proposal, "review")
            return
        if (
            isinstance(command, Intervention)
            and command.operation == Operation.CANCEL.value
        ):
            row = self._item_row(command.queue, command.item_id)
            review, proposal, _ = self._review_for_item(
                caller, command.queue, scope, row
            )
            del review
            self._authorize_review(caller.actor, scope, proposal, "cancel")
            return
        if isinstance(command, (Claim, Renew)):
            if caller.worker_id is None:
                raise ManagedError("forbidden")
            if isinstance(command, Renew):
                self._require_worker(command.claim.owner_id, caller.worker_id)
                row = self._item_row(command.queue, command.claim.item_id)
                self._review_for_item(caller, command.queue, scope, row)
            return
        if isinstance(command, Complete):
            self._require_worker(command.claim.owner_id, caller.worker_id)
            row = self._item_row(command.queue, command.claim.item_id)
            _, proposal, _ = self._review_for_item(caller, command.queue, scope, row)
            self._authorize_review(caller.actor, scope, proposal, "review")
            worker = self._worker(scope)
            if worker is None:
                raise ManagedError("unsupported_operation")
            self.reviews.outputs._authorize(
                caller.actor, worker.plan.snapshot, "execute"
            )
            return

    @staticmethod
    def _require_worker(owner_id: str, worker_id: str | None) -> None:
        if worker_id is None or owner_id != worker_id:
            raise ManagedError("forbidden")

    def _lock_workspace_for_mutation(self, workspace_id: WorkspaceId) -> None:
        if not _returning(
            self.db,
            "UPDATE counter SET value=value WHERE id=? RETURNING id",
            [RUN_ID_COUNTER],
        ):
            raise ManagedError("storage_unavailable")
        _lock_workspace(self.db, str(workspace_id.root))

    def _request_fingerprint(self, caller: ManagedCaller, command: Command) -> str:
        return _key(
            "actions.managed-work-items-request/v1",
            caller.actor.principal_id,
            caller.worker_id or "",
            _canonical(command.model_dump(mode="json"), 512 * 1024),
        )

    def _prior_request(
        self, caller: ManagedCaller, command: Command
    ) -> FoundryRequest | None:
        rows = self.db.select(
            FoundryRequest,
            "SELECT * FROM foundry_request WHERE workspace_id=? AND principal_id=? AND operation=? AND idempotency_key=? LIMIT 2",
            [
                str(self._workspace_for(command).root),
                caller.actor.principal_id,
                "managed-work-items/v1/" + str(command.operation),
                command.idempotency_key,
            ],
        )
        if len(rows) > 1:
            raise ManagedError("storage_unavailable")
        return rows[0] if rows else None

    @staticmethod
    def _result_model(operation: Operation) -> type:
        from actions.server.managed_work_items.contracts import RESULT_MODELS

        return RESULT_MODELS[operation]

    def _apply_mutation(
        self,
        caller: ManagedCaller,
        command: Command,
        scope: CanvasResultScope,
    ):
        if isinstance(command, Decide):
            receipt = self.reviews.decide(
                caller.actor, scope, command.proposal, command.decision
            )
            return ReviewResult(
                review=ReviewView(
                    proposal=command.proposal,
                    state=receipt.state,
                    work_item_id=receipt.work_item_id,
                ),
                server_time_ms=str(_now(self.db)),
            )
        if isinstance(command, Claim):
            if caller.worker_id is None:
                raise ManagedError("forbidden")
            queue = self._queue(scope)
            try:
                claim = queue.reserve_fenced(
                    caller.worker_id, lease_seconds=command.lease_seconds
                )
            except EmptyQueue:
                return ClaimResult(
                    item=None,
                    claim=None,
                    lease_deadline_ms=None,
                    server_time_ms=str(_now(self.db)),
                )
            item_row = self._item_row(command.queue, claim.item_id)
            item = self._item_view(caller, command.queue, scope, item_row)
            if item.claim is None or item.claim.owner_id != caller.worker_id:
                raise ManagedError("storage_unavailable")
            return ClaimResult(
                item=item,
                claim=item.claim,
                lease_deadline_ms=item.lease_deadline_ms,
                server_time_ms=str(_now(self.db)),
            )
        if isinstance(command, Renew):
            self._require_worker(command.claim.owner_id, caller.worker_id)
            self._require_current_claim(command.queue, command.claim)
            self._queue(scope).renew_fenced(
                WorkItemClaim(
                    command.claim.item_id,
                    command.claim.owner_id,
                    command.claim.epoch,
                ),
                lease_seconds=command.lease_seconds,
            )
            row = self._item_row(command.queue, command.claim.item_id)
            item = self._item_view(caller, command.queue, scope, row)
            return ClaimResult(
                item=item,
                claim=item.claim,
                lease_deadline_ms=item.lease_deadline_ms,
                server_time_ms=str(_now(self.db)),
            )
        if (
            isinstance(command, Intervention)
            and command.operation == Operation.CANCEL.value
        ):
            row = self._item_row(command.queue, command.item_id)
            if row.claim_epoch != command.expected_epoch:
                raise ManagedError("stale_claim")
            review, proposal, _ = self._review_for_item(
                caller, command.queue, scope, row
            )
            del review
            self.reviews.cancel(caller.actor, scope, proposal)
            updated = self._item_row(command.queue, command.item_id)
            return ItemResult(
                item=self._item_view(caller, command.queue, scope, updated),
                server_time_ms=str(_now(self.db)),
            )
        if isinstance(command, Complete):
            if command.outcome != "done" or command.output_payloads or command.run_ids:
                raise ManagedError("unsupported_operation")
            self._require_worker(command.claim.owner_id, caller.worker_id)
            self._require_current_claim(command.queue, command.claim)
            row = self._item_row(command.queue, command.claim.item_id)
            _, proposal, _ = self._review_for_item(caller, command.queue, scope, row)
            associated = self._worker_run(caller, command.queue, proposal, row.id)
            worker = self._worker(scope)
            if associated is None or worker is None:
                raise ManagedError("approval_required")
            pin, run, _, _ = associated
            if run.status == RunStatus.FAILED:
                raise ManagedError("unsupported_operation")
            claim = WorkItemClaim(
                command.claim.item_id,
                command.claim.owner_id,
                command.claim.epoch,
            )
            ticket = worker._ticket(proposal, claim, pin)
            receipt = worker.complete(caller.actor, WorkerTicket.model_validate(ticket))
            if receipt.work_item_id != command.claim.item_id:
                raise ManagedError("storage_unavailable")
            updated = self._item_row(command.queue, command.claim.item_id)
            return ItemResult(
                item=self._item_view(caller, command.queue, scope, updated),
                server_time_ms=str(_now(self.db)),
            )
        if (
            isinstance(command, Intervention)
            and command.operation == Operation.RETRY.value
        ):
            raise ManagedError("unsupported_operation")
        raise ManagedError("unsupported_operation")

    def _require_current_claim(self, queue: QueueRef, claim: ClaimRef) -> None:
        row = self._item_row(queue, claim.item_id)
        try:
            lease_expired = int(row.claim_deadline_ms) <= _now(self.db)
        except Exception:
            raise ManagedError("storage_unavailable") from None
        if (
            row.state != State.IN_PROGRESS.value
            or row.claim_owner != claim.owner_id
            or row.claim_epoch != claim.epoch
            or row.cancel_requested
            or lease_expired
        ):
            raise ManagedError("stale_claim")

    def _worker(self, scope: CanvasResultScope) -> InvoiceWorkerService | None:
        if self.worker_for is None:
            return None
        try:
            worker = self.worker_for(scope)
        except AccessDenied:
            return None
        if worker is not None and not isinstance(worker, InvoiceWorkerService):
            raise ManagedError("unconfigured")
        return worker

    def _authorize_review(
        self,
        actor: Actor,
        scope: CanvasResultScope,
        proposal: ReviewProposal,
        operation: str,
    ) -> None:
        proposal = ReviewProposal.model_validate(proposal)
        if proposal.binding.scope != scope:
            raise ManagedError("not_found")
        # status() rechecks the exact retained Review binding and Run read grant.
        self.reviews.status(actor, scope, proposal)
        pin = _one(self.db, RunPin, proposal.binding.run_id)
        snapshot = self.reviews.outputs._pinned(pin)
        self.reviews.outputs._authorize(actor, snapshot, operation)
