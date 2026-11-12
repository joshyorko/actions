"""Validate already-published native completion; never execute or finish work."""

from __future__ import annotations

import hashlib
import json
from typing import Protocol

from actions.server._database import Database
from actions.server._models import RunStatus
from actions.server.foundry.activated_execution import ActivatedReviewedExecution
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.service import _one
from actions.server.run_outputs.types import CanvasResultScope, OutputRef

from .api import ManagedError
from .contracts import Complete, ManagedCaller
from .native_runs import NativeRun


class NativeCompletionPort(Protocol):
    db: Database

    def completed(
        self,
        caller: ManagedCaller,
        scope: CanvasResultScope,
        command: Complete,
        native: NativeRun,
    ) -> None:
        ...


class NativeTerminalCompletion:
    """A trusted optional host adapter over the same activated execution authority."""

    def __init__(self, execution: ActivatedReviewedExecution):
        self.execution = execution
        self.db = execution.db

    def completed(
        self,
        caller: ManagedCaller,
        scope: CanvasResultScope,
        command: Complete,
        native: NativeRun,
    ) -> None:
        ticket = native.ticket
        if (
            caller.worker_id != self.execution.worker_id
            or caller.worker_id != ticket.claim.owner_id
            or command.claim.owner_id != ticket.claim.owner_id
            or command.claim.item_id != ticket.claim.item_id
            or command.claim.epoch != ticket.claim.epoch
        ):
            raise ManagedError("stale_claim")
        if command.outcome != "done" or command.output_payloads or command.run_ids:
            raise ManagedError("unsupported_operation")
        if native.run.status != RunStatus.PASSED:
            raise ManagedError("blocked_uncertain_effect")
        if scope != ticket.proposal.binding.scope:
            raise ManagedError("forbidden")
        # Reauthorize immutable admitted selection and the original reviewer;
        # source artifact expiry does not reopen or replace retained Run inputs.
        self.execution.resume(caller.actor, ticket)
        try:
            self.execution.read_execution(caller.actor, scope, ticket.proposal)
        except ValueError:
            raise ManagedError("storage_unavailable") from None
        self._verify_outputs(caller, scope, native)

    def _verify_outputs(
        self, caller: ManagedCaller, scope: CanvasResultScope, native: NativeRun
    ) -> None:
        try:
            envelope = json.loads(native.run.result or "null")
            published = tuple(OutputRef.model_validate(v) for v in envelope["outputs"])
            records = envelope["result"]["outputs"]
            expected = {
                "generated-action-result.json": "application/json",
                "rcc-receipt.json": "application/json",
                "rcc-stdout.log": "application/octet-stream",
                "rcc-stderr.log": "application/octet-stream",
            }
            if len(published) != 4 or len(set(published)) != 4 or len(records) != 4:
                raise ValueError("exact native output inventory required")
            seen: set[str] = set()
            total = 0
            for record in records:
                if set(record) != {"name", "ref", "digest", "size"}:
                    raise ValueError("closed native output receipt required")
                name = record["name"]
                if name in seen or name not in expected:
                    raise ValueError("duplicate or unknown native output")
                seen.add(name)
                ref = OutputRef.model_validate(record["ref"])
                row = _one(self.db, RunOutput, ref.output_id)
                if (
                    ref not in published
                    or ref.run_id != native.run.id
                    or ref.workspace_id != scope.application.workspace_id
                    or row.name != name
                    or row.media_type != expected[name]
                    or row.run_attempt_id != native.ticket.fence.attempt_id
                    or row.epoch != native.ticket.fence.epoch
                    or row.digest != record["digest"]
                    or row.size != record["size"]
                ):
                    raise ValueError("native output lineage or seal differs")
                total += row.size
                if total > 64 * 1024 * 1024:
                    raise ValueError("native output inventory exceeds byte bound")
                with self.execution.outputs.resolve(
                    caller.actor,
                    scope.application.workspace_id,
                    ref.handle,
                    canvas_scope=scope,
                ) as resolved:
                    digest, size = hashlib.sha256(), 0
                    while chunk := resolved.read(64 * 1024):
                        size += len(chunk)
                        if size > row.size:
                            raise ValueError("native output exceeds seal")
                        digest.update(chunk)
                    if size != row.size or "sha256:" + digest.hexdigest() != row.digest:
                        raise ValueError("native output bytes differ from seal")
        except ManagedError:
            raise
        except (KeyError, TypeError, ValueError):
            raise ManagedError("storage_unavailable") from None
