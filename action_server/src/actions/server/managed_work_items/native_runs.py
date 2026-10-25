"""Read-only projection of reviewed native Runs into managed Work Items.

This module reads only Runs admitted by the existing Work Item Run key and
published through the common Run/Attempt/output authority. It does not admit,
resume, mutate, or manufacture Run or log data.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from actions.work_items import State
from pydantic import ValidationError

from actions.server._models import Run, RunStatus
from actions.server.data_queries.invoice_worker import (
    ClaimValue,
    WorkerInput,
    work_item_run_key,
)
from actions.server.data_queries.review import InvoiceReviewService, ReviewProposal
from actions.server.data_queries.review_models import FencedWorkItem, InvoiceReview
from actions.server.foundry.work_item_execution import (
    GeneratedWorkItemTicket,
    require_reviewed_run_inputs,
)
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import (
    LogLine,
    LogPage,
    ManagedCaller,
    Permission,
    QueueAuthorizationPort,
    QueueRef,
)
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _key,
    _now,
    _one,
)
from actions.server.run_outputs.types import (
    AttemptFence,
    CanvasResultScope,
    ExecutionSnapshot,
    OutputRef,
)

MAX_NATIVE_LOG_BYTES = 256 * 1024
_LOG_LINE_CHARS = 8192
_LOG_CURSOR = re.compile(r"^(?:0|[1-9][0-9]{0,5})$")
_LOG_OUTPUTS = (("rcc-stdout.log", "stdout"), ("rcc-stderr.log", "stderr"))

ItemReviewResolver = Callable[
    [ManagedCaller, QueueRef, CanvasResultScope, FencedWorkItem],
    tuple[InvoiceReview, ReviewProposal, dict[str, Any]],
]


@dataclass(frozen=True)
class NativeRun:
    """A current, live-authorized native Run tied to one exact Work Item."""

    pin: RunPin
    run: Run
    snapshot: ExecutionSnapshot
    proposal: ReviewProposal
    ticket: GeneratedWorkItemTicket

    @property
    def phase(self) -> str:
        return {
            RunStatus.RUNNING: "running",
            RunStatus.PASSED: "completed",
            RunStatus.FAILED: "failed",
        }.get(self.run.status, "unknown")


class NativeRunProjection:
    """Resolve and project exact native Runs from the shared SQL authority."""

    def __init__(
        self,
        reviews: InvoiceReviewService,
        authorization: QueueAuthorizationPort,
        review_for_item: ItemReviewResolver,
    ) -> None:
        self.reviews = reviews
        self.db = reviews.db
        self.authorization = authorization
        self.review_for_item = review_for_item

    def _authorize_scope(
        self, caller: ManagedCaller, queue: QueueRef, scope: CanvasResultScope
    ) -> None:
        if (
            queue.deployment != scope.deployment
            or queue.workspace_id != scope.deployment.workspace_id
            or scope.application.workspace_id != str(queue.workspace_id.root)
        ):
            raise AccessDenied("Run/output unavailable or access denied")
        self.authorization.require_workspace(
            caller, queue.workspace_id, Permission.READ
        )
        self.authorization.require_queue(caller, queue, Permission.READ)

    def for_item(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        row: FencedWorkItem,
    ) -> NativeRun | None:
        """Find the native Run for an item after rechecking its live authority."""
        self._authorize_scope(caller, queue, scope)
        if (
            row.workspace_id != str(queue.workspace_id.root)
            or row.queue_name != queue.queue_id
        ):
            return None
        _, proposal, _ = self.review_for_item(caller, queue, scope, row)
        return self._for_item_authorized(caller, queue, scope, row, proposal)

    def for_run(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        run_id: str,
    ) -> NativeRun | None:
        """Resolve a caller-selected Run only if it maps to this live Work Item."""
        self._authorize_scope(caller, queue, scope)
        try:
            run = _one(self.db, Run, run_id)
            pin = _one(self.db, RunPin, run_id)
            snapshot = self.reviews.outputs._pinned(pin)
        except AccessDenied:
            return None
        if not self._same_scope(snapshot, queue, scope):
            return None
        self.reviews.outputs._authorize(caller.actor, snapshot, "read")
        if self._is_legacy_worker(run):
            return None
        parsed = self._ticket_data(run)
        if parsed is None:
            return None
        claim, _ = parsed
        key = work_item_run_key(claim.item_id)
        if pin.idempotency_key != key or pin.idempotency_id != _key(
            "actions.workspace-run-idempotency/v1",
            str(queue.workspace_id.root),
            key,
        ):
            return None
        rows = self.db.select(
            FencedWorkItem,
            "SELECT * FROM fenced_work_item WHERE id=? AND workspace_id=? AND queue_name=? LIMIT 2",
            [claim.item_id, str(queue.workspace_id.root), queue.queue_id],
        )
        if len(rows) != 1:
            return None
        _, proposal, _ = self.review_for_item(caller, queue, scope, rows[0])
        return self._validate_authorized(
            caller, queue, scope, rows[0], proposal, pin, run, snapshot
        )

    def _for_item_authorized(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        row: FencedWorkItem,
        proposal: ReviewProposal,
    ) -> NativeRun | None:
        key = work_item_run_key(row.id)
        idempotency_id = _key(
            "actions.workspace-run-idempotency/v1",
            str(queue.workspace_id.root),
            key,
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
        if snapshot.capability_authority != "package-revision":
            # Source/action-backed worker Runs use the separate existing worker
            # projection, which validates their own snapshot and live grants.
            return None
        if not self._same_scope(snapshot, queue, scope):
            raise ManagedError("storage_unavailable")
        self.reviews.outputs._authorize(caller.actor, snapshot, "read")
        if self._is_legacy_worker(run):
            return None
        return self._validate_authorized(
            caller, queue, scope, row, proposal, pin, run, snapshot
        )

    def _validate_authorized(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        row: FencedWorkItem,
        proposal: ReviewProposal,
        pin: RunPin,
        run: Run,
        snapshot: ExecutionSnapshot,
    ) -> NativeRun:
        parsed = self._ticket_data(run)
        if parsed is None:
            raise ManagedError("storage_unavailable")
        claim, fence = parsed
        try:
            ticket = GeneratedWorkItemTicket(
                proposal=proposal,
                claim=claim,
                fence=fence,
            )
            attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
            expected_fence = AttemptFence(
                run_id=run.id,
                attempt_id=attempt.id,
                owner_id=attempt.owner_id,
                epoch=attempt.epoch,
            )
        except (TypeError, ValueError):
            raise ManagedError("storage_unavailable") from None
        # Work Item claims and Run Attempts advance independently. Compare
        # each retained epoch with its own canonical row, never with the other
        # counter: an expired pre-admission claim can precede Attempt 1.
        if (
            ticket.proposal != proposal
            or ticket.claim.item_id != row.id
            or ticket.claim.epoch != row.claim_epoch
            or ticket.fence != expected_fence
            or pin.run_id != run.id
            or pin.workspace_id != str(queue.workspace_id.root)
            or pin.epoch != ticket.fence.epoch
            or ticket.fence.owner_id != ticket.claim.owner_id
            or expected_fence.run_id != ticket.fence.run_id
            or attempt.run_id != run.id
            or not self._same_scope(snapshot, queue, scope)
        ):
            raise FenceRejected("native Run no longer matches its Work Item fence")

        if run.status == RunStatus.RUNNING:
            now = _now(self.db)
            if (
                row.state != "IN_PROGRESS"
                or row.claim_owner != ticket.claim.owner_id
                or row.cancel_requested
                or int(row.claim_deadline_ms) <= now
                or attempt.state != "running"
                or int(attempt.lease_deadline_ms) <= now
                or pin.cancel_requested
            ):
                raise FenceRejected("native Run or Work Item lease is no longer live")
        elif run.status == RunStatus.PASSED:
            if (
                row.state != State.DONE.value
                or row.claim_owner
                or row.cancel_requested
                or attempt.state != "succeeded"
            ):
                raise FenceRejected("successful native Run differs from its Work Item")
        elif run.status == RunStatus.FAILED:
            if (
                row.state != State.FAILED.value
                or row.claim_owner
                or row.cancel_requested
                or attempt.state != "failed"
            ):
                raise FenceRejected("failed native Run differs from its Work Item")
        else:
            raise FenceRejected("native Run is not in a supported fenced state")

        # Scope, queue, current review, and the common Run read grant have all
        # been rechecked above. This validates retained inputs without reopening
        # an expired source artifact or granting new execution authority.
        try:
            require_reviewed_run_inputs(run, proposal)
        except FenceRejected:
            raise
        except Exception:
            raise ManagedError("storage_unavailable") from None
        return NativeRun(pin, run, snapshot, proposal, ticket)

    @staticmethod
    def _same_scope(
        snapshot: ExecutionSnapshot, queue: QueueRef, scope: CanvasResultScope
    ) -> bool:
        return (
            snapshot.capability_authority == "package-revision"
            and snapshot.deployment == queue.deployment == scope.deployment
            and snapshot.workspace_id == str(queue.workspace_id.root)
            and snapshot.canvas_application == scope.application
        )

    @staticmethod
    def _is_legacy_worker(run: Run) -> bool:
        try:
            WorkerInput.model_validate_json(run.inputs)
            return True
        except (TypeError, ValueError, ValidationError):
            return False

    @staticmethod
    def _ticket_data(run: Run) -> tuple[ClaimValue, AttemptFence] | None:
        try:
            record = json.loads(run.result or "null")
        except (TypeError, ValueError):
            raise ManagedError("storage_unavailable") from None
        if not isinstance(record, dict):
            return None
        if run.status in (RunStatus.PASSED, RunStatus.FAILED):
            if record.get("version") != 1:
                return None
            result = record.get("result")
            if (
                not isinstance(result, dict)
                or result.get("version") != "actions.generated-rcc-execution/v1"
                or result.get("mode") != "work-items"
            ):
                return None
            claim_data = result.get("claim")
            fence_data = result.get("publicationFence")
        else:
            if (
                record.get("version") != "actions.generated-rcc-dispatch/v1"
                or record.get("mode") != "work-items"
            ):
                return None
            claim_data = record.get("claim")
            fence_data = record.get("fence")
        try:
            return (
                ClaimValue.model_validate(claim_data),
                AttemptFence.model_validate(fence_data),
            )
        except (TypeError, ValueError):
            raise ManagedError("storage_unavailable") from None

    def logs(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        native: NativeRun,
        *,
        cursor: str | None,
        limit: int,
    ) -> LogPage:
        """Page the persisted RCC stdout/stderr objects in stable stream order."""
        self._authorize_scope(caller, queue, scope)
        if cursor is not None and _LOG_CURSOR.fullmatch(cursor) is None:
            raise ValueError("invalid native Run log cursor")
        self.reviews.outputs._authorize(caller.actor, native.snapshot, "read")
        start = int(cursor or "0")
        records = self._log_records(caller, queue, scope, native)
        lines: list[LogLine] = []
        offset = 0
        has_more = False
        for text in records:
            if offset >= start:
                if len(lines) == limit:
                    has_more = True
                    break
                lines.append(LogLine(offset=offset, text=text))
            offset += 1
        next_cursor = str(lines[-1].offset + 1) if has_more and lines else None
        return LogPage(
            run_id=native.run.id,
            lines=tuple(lines),
            next_cursor=next_cursor,
            server_time_ms=str(_now(self.db)),
        )

    def _log_records(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        scope: CanvasResultScope,
        native: NativeRun,
    ):
        if native.run.status not in (RunStatus.PASSED, RunStatus.FAILED):
            return
        try:
            envelope = json.loads(native.run.result or "null")
            refs = envelope.get("outputs", [])
            if not isinstance(refs, list) or len(refs) > 64:
                raise ValueError("bounded final Run output list required")
        except (TypeError, ValueError, AttributeError):
            raise ManagedError("storage_unavailable") from None
        by_name: dict[str, tuple[OutputRef, RunOutput]] = {}
        now = _now(self.db)
        for raw in refs:
            try:
                ref = OutputRef.model_validate(raw)
                if ref.run_id != native.run.id or ref.workspace_id != str(
                    queue.workspace_id.root
                ):
                    raise ValueError("output belongs to another Run or Workspace")
                output = _one(self.db, RunOutput, ref.output_id)
                if (
                    output.run_id != native.run.id
                    or output.workspace_id != str(queue.workspace_id.root)
                    or output.run_attempt_id != native.pin.current_attempt_id
                    or output.epoch != native.pin.epoch
                    or output.state != "final"
                ):
                    raise ValueError("output is not final on the current Run fence")
                label = dict(_LOG_OUTPUTS).get(output.name)
                if label is None or int(output.expires_ms) <= now:
                    continue
                if output.media_type != "application/octet-stream":
                    raise ValueError("captured Run logs must remain binary outputs")
                if output.size > MAX_NATIVE_LOG_BYTES:
                    raise ValueError("captured Run log exceeds its retained bound")
                if label in by_name:
                    raise ValueError("duplicate captured Run log stream")
                by_name[label] = (ref, output)
            except (TypeError, ValueError):
                raise ManagedError("storage_unavailable") from None

        for name, label in _LOG_OUTPUTS:
            selected = by_name.get(label)
            if selected is None:
                continue
            ref, row = selected
            with self.reviews.outputs.resolve(
                caller.actor,
                str(queue.workspace_id.root),
                ref.handle,
                canvas_scope=scope,
            ) as resolved_output:
                chunks = []
                total = 0
                while total <= MAX_NATIVE_LOG_BYTES:
                    chunk = resolved_output.read(
                        min(64 * 1024, MAX_NATIVE_LOG_BYTES + 1 - total)
                    )
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                if total != row.size or total > MAX_NATIVE_LOG_BYTES:
                    raise ManagedError("storage_unavailable")
            stream = b"".join(chunks).decode("utf-8", errors="replace")
            prefix = f"[{label}] "
            chunk_chars = _LOG_LINE_CHARS - len(prefix)
            for raw_line in stream.splitlines():
                if not raw_line:
                    yield prefix.rstrip()
                    continue
                for offset in range(0, len(raw_line), chunk_chars):
                    yield prefix + raw_line[offset : offset + chunk_chars]
