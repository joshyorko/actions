"""Selected immutable generic policy adapter; no inferred queue or grants.

Enqueue retains the domain's sole request/audit owner. Claim and renew use a
separate receipt namespace and the existing canonical queue. No automatic
reclaim, execution launch, output-child admission or retry is exposed.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Literal, cast
from uuid import uuid4

from actions.work_items import State
from actions.work_items._fencing import ClaimRejected, WorkItemClaim
from pydantic import BaseModel, TypeAdapter

from actions.server._models import RunStatus
from actions.server.data_queries.invoice_worker import work_item_run_key
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.deployments.ids import WorkspaceId
from actions.server.foundry.generic_work_item_execution import (
    GenericInput,
    GenericWorkItemExecution,
)
from actions.server.foundry.logical_receipts import (
    validate_bound_record,
    versions_for_selection,
)
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import (
    ArtifactChunk,
    ArtifactRef,
    AttemptView,
    Capabilities,
    Claim,
    ClaimRef,
    ClaimResult,
    Command,
    Complete,
    Enqueue,
    Inspect,
    ItemPage,
    ItemResult,
    ItemView,
    LogLine,
    LogPage,
    ManagedCaller,
    Operation,
    Permission,
    QueuePage,
    Queues,
    QueueView,
    Renew,
    RunResult,
    RunView,
)
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _canonical,
    _key,
    _now,
)
from actions.server.run_outputs.types import OutputRef, output_id_from_handle

_COMMAND: TypeAdapter[Command] = TypeAdapter(Command)


class GenericManagedWorkItemsService:
    """One trusted selected input policy; host owns catalog and authentication."""

    def __init__(self, execution: GenericWorkItemExecution):
        if not isinstance(execution, GenericWorkItemExecution):
            raise TypeError("typed generic domain authority required")
        if execution.policy.input_queue is None:
            raise ValueError("managed input service requires an explicit input queue")
        self.execution = execution
        self.db = execution.db
        self.queue_ref = execution.queue_ref(execution.policy.input_queue)
        self.queue = execution.queue(execution.policy.input_queue)

    def _authorize(self, caller, permission=Permission.READ):
        self.execution.authorize(caller, Permission.READ)
        if permission != Permission.READ:
            self.execution.authorize(caller, permission)

    def _permissions(self, caller):
        self._authorize(caller)
        result = [Permission.READ]
        for permission in (
            Permission.ENQUEUE,
            Permission.CLAIM,
            Permission.COMPLETE,
            Permission.ARTIFACT_READ,
        ):
            try:
                self._authorize(caller, permission)
            except AccessDenied:
                continue
            result.append(permission)
        return tuple(result)

    def capabilities(
        self, caller: ManagedCaller, workspace_id: WorkspaceId
    ) -> Capabilities:
        try:
            with self.db.connect():
                caller = ManagedCaller.model_validate(caller)
                if workspace_id != self.queue_ref.workspace_id:
                    raise AccessDenied("wrong workspace")
                permissions = self._permissions(caller)
                operations = [
                    Operation.QUEUES,
                    Operation.LIST,
                    Operation.GET,
                    Operation.RUN,
                ]
                if Permission.ENQUEUE in permissions:
                    operations.append(Operation.ENQUEUE)
                if Permission.CLAIM in permissions and caller.worker_id:
                    operations.extend((Operation.CLAIM, Operation.RENEW))
                if (
                    Permission.COMPLETE in permissions
                    and Permission.CLAIM in permissions
                    and caller.worker_id
                ):
                    operations.append(Operation.COMPLETE)
                if Permission.ARTIFACT_READ in permissions:
                    operations.extend((Operation.ARTIFACT, Operation.LOGS))
                from actions.work_items import __version__ as sdk_version

                from actions.server import __version__ as runtime_version

                mode = self.execution.policy.input_mode
                return Capabilities(
                    runtime_version=runtime_version,
                    sdk_version=sdk_version,
                    workspace_id=workspace_id,
                    permissions=permissions,
                    operations=tuple(operations),
                    backend=cast(Literal["sqlite", "postgresql"], self.db.backend_name),
                    modes=(
                        cast(
                            Literal["optional", "required-input", "consumer"],
                            {
                                "optional": "optional",
                                "required": "required-input",
                                "claim": "consumer",
                            }[mode],
                        ),
                    ),
                )
        except AccessDenied:
            raise ManagedError("forbidden") from None

    def _rows(self, caller):
        # A shared logical name is not a Deployment identity. Inspect bounded
        # metadata and admit only exact envelopes before projection or mutation.
        result = []
        for row in self._physical_rows():
            raw = json.loads(row.payload)
            if (
                not isinstance(raw, dict)
                or raw.get("schema") != "actions.generic-work-item/v1"
            ):
                continue
            envelope = GenericInput.model_validate(raw)
            if (
                envelope.snapshot != self.execution.snapshot
                or envelope.policy != self.execution.policy
            ):
                continue
            self.execution.read_input(caller, row.id)
            result.append(row)
        return result

    def _physical_rows(self):
        cursor, count, total = "", 0, 0
        while True:
            batch = self.db.select(
                FencedWorkItem,
                "SELECT * FROM fenced_work_item WHERE workspace_id=? AND queue_name=? AND id>? ORDER BY id LIMIT 64",
                [
                    str(self.queue_ref.workspace_id.root),
                    self.queue_ref.queue_id,
                    cursor,
                ],
            )
            if not batch:
                return
            for row in batch:
                count += 1
                total += len(row.payload.encode("utf-8"))
                if count > 10000 or total > 16 * 1024 * 1024:
                    raise ManagedError("storage_unavailable")
                yield row
            cursor = batch[-1].id

    def _row(self, caller, item_id):
        rows = [row for row in self._rows(caller) if row.id == item_id]
        if len(rows) != 1:
            raise ManagedError("not_found")
        return rows[0]

    def _item(self, caller, row):
        envelope = self.execution.read_input(caller, row.id)
        claim = None
        deadline = None
        if (
            row.state == State.IN_PROGRESS.value
            and row.claim_owner
            and not row.cancel_requested
        ):
            claim = ClaimRef(
                queue=self.queue_ref,
                item_id=row.id,
                owner_id=row.claim_owner,
                epoch=row.claim_epoch,
            )
            deadline = str(row.claim_deadline_ms)
        state = "DONE" if row.state == State.DONE.value else row.state
        retained = self._execution(caller, row.id)
        return ItemView(
            queue=self.queue_ref,
            id=row.id,
            parent_id=row.parent_id or None,
            queue_state=state,
            business_state="cancelled"
            if row.cancel_requested
            else {
                "PENDING": "ready",
                "IN_PROGRESS": "running",
                "DONE": "completed",
                "FAILED": "application_failed",
            }[state],
            payload=envelope.inputs,
            protected_input_digest=envelope.input_digest,
            snapshot=envelope.snapshot,
            delivery_count=row.claim_epoch,
            claim=claim,
            lease_deadline_ms=deadline,
            available_after_ms=str(row.created_ms),
            created_ms=str(row.created_ms),
            run_ids=(retained[0].id,) if retained else (),
        )

    def call(self, caller: ManagedCaller, command: Command) -> dict[str, Any]:
        try:
            with self.db.connect():
                caller = ManagedCaller.model_validate(caller)
                command = _COMMAND.validate_python(command)
                self._authorize(caller)
                result: BaseModel
                if isinstance(command, Queues):
                    if command.workspace_id != self.queue_ref.workspace_id:
                        raise AccessDenied("wrong workspace")
                    if command.cursor is not None:
                        raise ManagedError("changed_input")
                    pages: tuple[QueueView, ...] = ()
                    if command.deployment_id in (
                        None,
                        self.queue_ref.deployment.deployment_id,
                    ):
                        counts: dict[str, int] = {}
                        for row in self._rows(caller):
                            state = (
                                "DONE" if row.state == State.DONE.value else row.state
                            )
                            counts[state] = counts.get(state, 0) + 1
                        pages = (
                            QueueView(
                                queue=self.queue_ref,
                                label=self.queue_ref.queue_id,
                                mode=cast(
                                    Literal["optional", "required-input", "consumer"],
                                    {
                                        "optional": "optional",
                                        "required": "required-input",
                                        "claim": "consumer",
                                    }[self.execution.policy.input_mode],
                                ),
                                counts=counts,
                                permissions=self._permissions(caller),
                            ),
                        )
                    result = QueuePage(queues=pages, server_time_ms=str(_now(self.db)))
                else:
                    if command.queue != self.queue_ref:
                        raise AccessDenied("wrong selected queue")
                    if isinstance(command, Enqueue):
                        if (
                            command.snapshot != self.execution.snapshot
                            or command.review is not None
                        ):
                            raise ManagedError("changed_input")
                        admitted = self.execution._enqueue_result(
                            caller, command.payload, command.idempotency_key
                        )
                        result = ItemResult(
                            item=self._item(caller, self._row(caller, admitted.item_id)),
                            replay=admitted.replay,
                            server_time_ms=str(_now(self.db)),
                        )
                    elif isinstance(command, (Claim, Renew, Complete)):
                        result = self._mutate(caller, command)
                    elif (
                        isinstance(command, Inspect) and command.operation == "runs.get"
                    ):
                        retained = self._find_run(caller, command.run_id)
                        result = RunResult(
                            run=self._run_view(caller, retained),
                            server_time_ms=str(_now(self.db)),
                        )
                    elif (
                        isinstance(command, Inspect)
                        and command.operation == "runs.logs"
                    ):
                        result = self._logs(caller, command)
                    elif (
                        isinstance(command, Inspect)
                        and command.operation == "artifacts.read"
                    ):
                        result = self._artifact(caller, command)
                    elif (
                        isinstance(command, Inspect)
                        and command.operation == "items.get"
                    ):
                        result = ItemResult(
                            item=self._item(caller, self._row(caller, command.item_id)),
                            server_time_ms=str(_now(self.db)),
                        )
                    elif (
                        isinstance(command, Inspect)
                        and command.operation == "items.list"
                    ):
                        rows = self._rows(caller)
                        if command.cursor is not None:
                            from actions.server.run_outputs.types import canonical_uuid

                            canonical_uuid(command.cursor)
                            rows = [r for r in rows if r.id > command.cursor]
                        page = rows[: command.limit]
                        result = ItemPage(
                            items=tuple(self._item(caller, r) for r in page),
                            next_cursor=page[-1].id
                            if len(rows) > command.limit
                            else None,
                            server_time_ms=str(_now(self.db)),
                        )
                    else:
                        raise ManagedError("unsupported_operation")
                return result.model_dump(mode="json")
        except ManagedError:
            raise
        except AccessDenied:
            raise ManagedError("forbidden") from None
        except (ClaimRejected, FenceRejected):
            raise ManagedError("stale_claim") from None
        except Exception:
            raise ManagedError("storage_unavailable") from None

    def _claim_result(self, caller, ref):
        if ref is None:
            return ClaimResult(
                item=None,
                claim=None,
                lease_deadline_ms=None,
                server_time_ms=str(_now(self.db)),
            )
        if ref.queue != self.queue_ref or ref.owner_id != caller.worker_id:
            raise AccessDenied("claim owner differs")
        self.queue._require(WorkItemClaim(ref.item_id, ref.owner_id, ref.epoch))
        item = self._item(caller, self._row(caller, ref.item_id))
        return ClaimResult(
            item=item,
            claim=item.claim,
            lease_deadline_ms=item.lease_deadline_ms,
            server_time_ms=str(_now(self.db)),
        )

    def _mutate(self, caller, command):
        with self.execution._transaction():
            self._authorize(caller, Permission.CLAIM)
            if isinstance(command, Complete):
                self._authorize(caller, Permission.COMPLETE)
            if caller.worker_id is None:
                raise AccessDenied("server-held worker required")
            fingerprint = hashlib.sha256(
                _canonical(
                    {
                        "command": command.model_dump(mode="json"),
                        "worker": caller.worker_id,
                    },
                    524288,
                ).encode()
            ).hexdigest()
            key = _key(
                "actions.generic-managed/v1",
                str(self.queue_ref.workspace_id.root),
                caller.actor.principal_id,
                command.idempotency_key,
            )
            prior = self.db.all(FoundryRequest, where="id=?", values=[key])
            operation = "generic-managed/" + command.operation
            if prior:
                row = prior[0]
                if (
                    row.request_fingerprint != fingerprint
                    or row.operation != operation
                    or row.principal_id != caller.actor.principal_id
                    or row.workspace_id != str(self.queue_ref.workspace_id.root)
                    or row.idempotency_key != command.idempotency_key
                ):
                    raise ManagedError("changed_input")
                audit = self.db.all(
                    FoundryAudit, where="foundry_request_id=?", values=[key]
                )
                if len(audit) != 1 or any(
                    (
                        audit[0].operation != operation,
                        audit[0].principal_id != caller.actor.principal_id,
                        audit[0].workspace_id != row.workspace_id,
                        audit[0].deployment_id
                        != str(self.queue_ref.deployment.deployment_id.root),
                        audit[0].from_revision_id
                        != self.queue_ref.deployment.revision_id.root,
                        audit[0].to_revision_id
                        != self.queue_ref.deployment.revision_id.root,
                    )
                ):
                    raise ManagedError("storage_unavailable")
                if isinstance(command, Complete):
                    saved_item = ItemResult.model_validate_json(row.result_json).item
                    if (
                        saved_item.id != command.claim.item_id
                        or saved_item.queue != self.queue_ref
                    ):
                        raise ManagedError("storage_unavailable")
                    self._completed(caller, command)
                    return ItemResult(
                        item=self._item(
                            caller, self._row(caller, command.claim.item_id)
                        ),
                        replay=True,
                        server_time_ms=str(_now(self.db)),
                    )
                saved = ClaimResult.model_validate_json(row.result_json)
                return self._claim_result(caller, saved.claim)
            if isinstance(command, Complete):
                self._completed(caller, command)
                result = ItemResult(
                    item=self._item(caller, self._row(caller, command.claim.item_id)),
                    server_time_ms=str(_now(self.db)),
                )
            elif isinstance(command, Claim):
                rows = [
                    r
                    for r in self._rows(caller)
                    if r.state == State.PENDING.value
                    and r.claim_epoch == 0
                    and not r.cancel_requested
                ]
                rows.sort(key=lambda r: (int(r.created_ms), r.id))
                ref = None
                if rows:
                    claim = self.queue.reserve_item_fenced(
                        rows[0].id,
                        caller.worker_id,
                        lease_seconds=command.lease_seconds,
                    )
                    ref = ClaimRef(
                        queue=self.queue_ref,
                        item_id=claim.item_id,
                        owner_id=claim.owner_id,
                        epoch=claim.epoch,
                    )
                result = self._claim_result(caller, ref)
            else:
                self._claim_result(caller, command.claim)
                claim = WorkItemClaim(
                    command.claim.item_id, command.claim.owner_id, command.claim.epoch
                )
                if self._execution(caller, command.claim.item_id):
                    ticket = self.execution.retained_ticket(caller, claim)
                    self.execution.outputs(caller, ticket).heartbeat(
                        ticket.fence, lease_seconds=command.lease_seconds
                    )
                else:
                    self.queue.renew_fenced(claim, lease_seconds=command.lease_seconds)
                result = self._claim_result(caller, command.claim)
            self.db.insert(
                FoundryRequest(
                    id=key,
                    workspace_id=str(self.queue_ref.workspace_id.root),
                    principal_id=caller.actor.principal_id,
                    operation=operation,
                    idempotency_key=command.idempotency_key,
                    request_fingerprint=fingerprint,
                    result_json=result.model_dump_json(),
                )
            )
            self.db.insert(
                FoundryAudit(
                    id=str(uuid4()),
                    workspace_id=str(self.queue_ref.workspace_id.root),
                    deployment_id=str(self.queue_ref.deployment.deployment_id.root),
                    principal_id=caller.actor.principal_id,
                    operation=operation,
                    foundry_request_id=key,
                    from_revision_id=self.queue_ref.deployment.revision_id.root,
                    to_revision_id=self.queue_ref.deployment.revision_id.root,
                    created_ms=str(_now(self.db)),
                )
            )
            return result

    def _execution(self, caller, item_id):
        pins = self.db.all(
            RunPin,
            where="workspace_id=? AND idempotency_key=?",
            values=[str(self.queue_ref.workspace_id.root), work_item_run_key(item_id)],
        )
        if not pins:
            return None
        return self.execution.read_execution(caller, item_id)

    def _find_run(self, caller, run_id):
        for row in self._rows(caller):
            retained = self._execution(caller, row.id)
            if retained and retained[0].id == run_id:
                return retained
        raise ManagedError("not_found")

    def _artifacts(self, caller, retained):
        run, attempt, ticket = retained
        if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
            return ()
        envelope = json.loads(run.result or "null")
        if (
            not isinstance(envelope, dict)
            or isinstance(envelope.get("version"), bool)
            or not isinstance(envelope.get("version"), int)
            or envelope["version"] != 1
            or not isinstance(envelope.get("result"), dict)
            or envelope["result"].get("version")
            != versions_for_selection(self.execution.registry, self.execution.snapshot)[
                1
            ]
        ):
            raise ManagedError("storage_unavailable")
        validate_bound_record(
            self.db,
            self.execution.registry,
            self.execution.snapshot,
            run,
            ticket.fence,
            envelope["result"],
            claim=ticket.claim.model_dump() if ticket.claim else None,
            terminal=True,
            outputs=envelope["outputs"],
        )
        refs = tuple(OutputRef.model_validate(raw) for raw in envelope["outputs"])
        if len(refs) > 64 or len({r.output_id for r in refs}) != len(refs):
            raise ManagedError("storage_unavailable")
        result = []
        for ref in refs:
            rows = self.db.all(RunOutput, where="id=?", values=[ref.output_id])
            if len(rows) != 1:
                raise ManagedError("storage_unavailable")
            row = rows[0]
            if (
                ref.run_id != run.id
                or ref.workspace_id != str(self.queue_ref.workspace_id.root)
                or row.run_id != run.id
                or row.workspace_id != ref.workspace_id
                or row.state != "final"
                or row.run_attempt_id != attempt.id
                or row.epoch != ticket.fence.epoch
            ):
                raise ManagedError("storage_unavailable")
            if int(row.expires_ms) <= _now(self.db):
                raise ManagedError("storage_unavailable")
            result.append(
                ArtifactRef(
                    handle=ref.handle, run_id=run.id, digest=row.digest, size=row.size
                )
            )
        return tuple(result)

    def _run_view(self, caller, retained):
        run, attempt, _ = retained
        artifacts = ()
        try:
            self._authorize(caller, Permission.ARTIFACT_READ)
        except AccessDenied:
            pass
        else:
            artifacts = self._artifacts(caller, retained)
        attempts = self.db.select(
            RunAttempt,
            "SELECT * FROM run_attempt WHERE run_id=? AND workspace_id=? ORDER BY epoch LIMIT 101",
            [run.id, str(self.queue_ref.workspace_id.root)],
        )
        if len(attempts) > 100 or not any(row.id == attempt.id for row in attempts):
            raise ManagedError("storage_unavailable")
        result_value = None
        if run.status in (RunStatus.PASSED, RunStatus.FAILED):
            result_value = json.loads(run.result or "null")["result"]
        return RunView(
            id=run.id,
            snapshot=self.execution.snapshot,
            state={
                RunStatus.PASSED: "succeeded",
                RunStatus.FAILED: "failed",
                RunStatus.NOT_RUN: "pending",
                RunStatus.RUNNING: "running",
                RunStatus.CANCELLED: "cancelled",
            }[run.status],
            attempts=tuple(
                AttemptView(
                    id=row.id,
                    owner_id=row.owner_id,
                    epoch=row.epoch,
                    state=row.state,
                    lease_deadline_ms=str(row.lease_deadline_ms),
                )
                for row in attempts
            ),
            artifacts=artifacts,
            result=result_value,
        )

    def _artifact(self, caller, command):
        self._authorize(caller, Permission.ARTIFACT_READ)
        from actions.server.run_outputs.types import output_id_from_handle

        rows = self.db.all(
            RunOutput,
            where="id=?",
            values=[output_id_from_handle(command.artifact_handle)],
        )
        if len(rows) != 1:
            raise ManagedError("not_found")
        retained = self._find_run(caller, rows[0].run_id)
        refs = [
            r
            for r in self._artifacts(caller, retained)
            if r.handle == command.artifact_handle
        ]
        if len(refs) != 1:
            raise ManagedError("not_found")
        cursor = command.cursor or "0"
        if not cursor.isascii() or not cursor.isdecimal() or len(cursor) > 10:
            raise ManagedError("changed_input")
        offset = int(cursor)
        if offset > refs[0].size:
            raise ManagedError("changed_input")
        with self.execution.base.resolve(
            caller.actor, str(self.queue_ref.workspace_id.root), command.artifact_handle
        ) as output:
            remaining = offset
            while remaining:
                data = output.read(min(remaining, 65536))
                if not data:
                    raise ManagedError("storage_unavailable")
                remaining -= len(data)
            data = output.read(65536)
        end = offset + len(data)
        return ArtifactChunk(
            artifact=refs[0],
            offset=offset,
            data_base64=base64.b64encode(data).decode("ascii"),
            eof=end == refs[0].size,
            next_cursor=None if end == refs[0].size else str(end),
        )

    def _completed(self, caller, command):
        if command.outcome != "done" or command.output_payloads or command.run_ids:
            raise ManagedError("unsupported_operation")
        ref = command.claim
        if ref.owner_id != caller.worker_id:
            raise AccessDenied("different completion owner")
        ticket = self.execution.retained_ticket(
            caller, WorkItemClaim(ref.item_id, ref.owner_id, ref.epoch)
        )
        retained = self.execution.read_execution(caller, ref.item_id)
        run, attempt, actual = retained
        row = self._row(caller, ref.item_id)
        if (
            ticket != actual
            or run.status != RunStatus.PASSED
            or attempt.state != "succeeded"
            or row.state != State.DONE.value
            or row.cancel_requested
        ):
            raise ManagedError("blocked_uncertain_effect")
        refs = self._artifacts(caller, retained)
        records = json.loads(run.result)["result"]["outputs"]
        expected = {
            "generated-action-result.json": "application/json",
            "rcc-receipt.json": "application/json",
            "rcc-stdout.log": "application/octet-stream",
            "rcc-stderr.log": "application/octet-stream",
        }
        from actions.server.foundry.logical_receipts import generated_output_names

        for name in generated_output_names(json.loads(run.result)["result"]):
            expected.setdefault(name, "application/json")
        if (
            len(refs) != len(expected)
            or len(records) != len(expected)
            or {r["name"] for r in records} != set(expected)
        ):
            raise ManagedError("storage_unavailable")
        total = 0
        for record in records:
            if set(record) != {"name", "ref", "digest", "size"}:
                raise ManagedError("storage_unavailable")
            output_ref = OutputRef.model_validate(record["ref"])
            if output_ref.run_id != run.id or output_ref.workspace_id != str(
                self.queue_ref.workspace_id.root
            ):
                raise ManagedError("storage_unavailable")
            matches = [r for r in refs if r.handle == output_ref.handle]
            row = self.db.all(RunOutput, where="id=?", values=[output_ref.output_id])[0]
            if (
                len(matches) != 1
                or record["digest"] != row.digest
                or record["size"] != row.size
                or row.name != record["name"]
                or row.media_type != expected[row.name]
            ):
                raise ManagedError("storage_unavailable")
            total += row.size
        if total > 64 * 1024 * 1024:
            raise ManagedError("storage_unavailable")
        for ref in refs:
            with self.execution.base.resolve(
                caller.actor, str(self.queue_ref.workspace_id.root), ref.handle
            ) as output:
                digest, size = hashlib.sha256(), 0
                while chunk := output.read(65536):
                    digest.update(chunk)
                    size += len(chunk)
                    if size > ref.size:
                        raise ManagedError("storage_unavailable")
                if size != ref.size or "sha256:" + digest.hexdigest() != ref.digest:
                    raise ManagedError("storage_unavailable")

    def _logs(self, caller, command):
        self._authorize(caller, Permission.ARTIFACT_READ)
        retained = self._find_run(caller, command.run_id)
        refs = self._artifacts(caller, retained)
        cursor = command.cursor or "0"
        if not cursor.isascii() or not cursor.isdecimal() or len(cursor) > 10:
            raise ManagedError("changed_input")
        records = []
        for name in ("rcc-stdout.log", "rcc-stderr.log"):
            selected = []
            for ref in refs:
                output_ref = self.db.all(
                    RunOutput,
                    where="run_id=? AND name=? AND state=?",
                    values=[command.run_id, name, "final"],
                )
                if len(output_ref) > 1:
                    raise ManagedError("storage_unavailable")
                if output_ref and output_ref[0].id == output_id_from_handle(ref.handle):
                    selected.append(ref)
            for ref in selected:
                if ref.size > 4 * 1024 * 1024:
                    raise ManagedError("storage_unavailable")
                with self.execution.base.resolve(
                    caller.actor, str(self.queue_ref.workspace_id.root), ref.handle
                ) as output:
                    raw = output.read(ref.size + 1)
                if (
                    len(raw) != ref.size
                    or "sha256:" + hashlib.sha256(raw).hexdigest() != ref.digest
                ):
                    raise ManagedError("storage_unavailable")
                for text in raw.decode("utf-8").splitlines():
                    if len(text) > 8192:
                        raise ManagedError("storage_unavailable")
                    records.append(text)
        start = int(cursor)
        page = records[start : start + command.limit]
        end = start + len(page)
        return LogPage(
            run_id=command.run_id,
            lines=tuple(
                LogLine(offset=start + i, text=text) for i, text in enumerate(page)
            ),
            next_cursor=str(end) if end < len(records) else None,
            server_time_ms=str(_now(self.db)),
        )
