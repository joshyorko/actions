"""Private JSON review queue on a host-owned SQL transaction and schema.

The host owns migration/admission and supplies one serialized Workspace writer.
No connection, schema, worker process, attachment or external effect is created.
This bounded bridge preserves WorkItemClaim semantics; it is not a legacy adapter.
"""

import json
from contextlib import AbstractContextManager
from typing import Any, Protocol
from uuid import uuid4

from .._exceptions import EmptyQueue
from .._fencing import ClaimRejected, WorkItemClaim, validate_lease, validate_owner
from .._types import JSONType, State

FORMAT = "actions.review-work-item/v1"
FIELDS = "id,workspace_id,queue_name,parent_id,state,payload,created_ms,claim_owner,claim_epoch,claim_deadline_ms,cancel_requested,error_message,format"


class SQLReviewStore(Protocol):
    backend_name: str

    def transaction(self) -> AbstractContextManager[None]: ...

    def execute(self, sql: str, values: list[Any]) -> list[tuple[Any, ...]]: ...


class SQLReviewQueue:
    def __init__(self, store: SQLReviewStore, workspace_id: str, queue_name: str):
        validate_owner(workspace_id)
        if not isinstance(queue_name, str) or not 1 <= len(queue_name) <= 256:
            raise ValueError("bounded queue identity required")
        self.store, self.workspace_id, self.queue_name = store, workspace_id, queue_name
        if store.backend_name == "sqlite":
            self.clock = "CAST((julianday('now')-2440587.5)*86400000 AS BIGINT)"
        elif store.backend_name == "postgresql":
            self.clock = "CAST(EXTRACT(EPOCH FROM clock_timestamp())*1000 AS BIGINT)"
        else:
            raise ValueError("unsupported SQL review backend")

    def _check_format(self) -> None:
        rows = self.store.execute(
            "SELECT DISTINCT format FROM fenced_work_item WHERE workspace_id=? AND queue_name=?",
            [self.workspace_id, self.queue_name],
        )
        if any(row[0] != FORMAT for row in rows):
            raise ValueError("unknown review Work Item format")

    @staticmethod
    def _payload(payload: JSONType) -> str:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
        if len(data.encode()) > 256 * 1024:
            raise ValueError("Work Item payload exceeds limit")
        return data

    def _seed(self, payload: str, item_id: str, queue: str, parent: str = "") -> None:
        self.store.execute(
            "INSERT INTO fenced_work_item ("
            + FIELDS
            + ") VALUES (?,?,?,?,?,?,"
            + self.clock
            + ",?,0,0,0,?,?) RETURNING id",
            [
                item_id,
                self.workspace_id,
                queue,
                parent,
                State.PENDING.value,
                payload,
                "",
                "",
                FORMAT,
            ],
        )

    def seed_input(self, payload: JSONType, *, item_id: str) -> str:
        validate_owner(item_id)
        data = self._payload(payload)
        with self.store.transaction():
            self._check_format()
            self._seed(data, item_id, self.queue_name)
        return item_id

    def reserve_fenced(self, owner_id: str, *, lease_seconds: int) -> WorkItemClaim:
        validate_owner(owner_id)
        validate_lease(lease_seconds)
        with self.store.transaction():
            self._check_format()
            rows = self.store.execute(
                "SELECT id FROM fenced_work_item WHERE workspace_id=? AND queue_name=? AND cancel_requested=0 AND (state=? OR (state=? AND CAST(claim_deadline_ms AS BIGINT)<="
                + self.clock
                + ")) ORDER BY CAST(created_ms AS BIGINT),id LIMIT 1",
                [self.workspace_id, self.queue_name, State.PENDING.value, State.IN_PROGRESS.value],
            )
            if not rows:
                raise EmptyQueue("No claimable review Work Item")
            changed = self.store.execute(
                "UPDATE fenced_work_item SET state=?,claim_owner=?,claim_epoch=claim_epoch+1,claim_deadline_ms="
                + self.clock
                + "+? WHERE id=? AND cancel_requested=0 RETURNING id,claim_epoch",
                [State.IN_PROGRESS.value, owner_id, lease_seconds * 1000, rows[0][0]],
            )
            return WorkItemClaim(changed[0][0], owner_id, changed[0][1])

    def _require(self, claim: WorkItemClaim) -> None:
        if not isinstance(claim, WorkItemClaim):
            raise ClaimRejected("typed Work Item claim required")
        rows = self.store.execute(
            "SELECT id FROM fenced_work_item WHERE id=? AND workspace_id=? AND queue_name=? AND state=? AND claim_owner=? AND claim_epoch=? AND cancel_requested=0 AND format=? AND CAST(claim_deadline_ms AS BIGINT)>"
            + self.clock,
            [
                claim.item_id,
                self.workspace_id,
                self.queue_name,
                State.IN_PROGRESS.value,
                claim.owner_id,
                claim.epoch,
                FORMAT,
            ],
        )
        if not rows:
            raise ClaimRejected("Work Item claim is not current")

    def renew_fenced(self, claim: WorkItemClaim, *, lease_seconds: int) -> None:
        validate_lease(lease_seconds)
        with self.store.transaction():
            self._check_format()
            self._require(claim)
            changed = self.store.execute(
                "UPDATE fenced_work_item SET claim_deadline_ms="
                + self.clock
                + "+? WHERE id=? AND workspace_id=? AND queue_name=? AND state=? AND claim_owner=? AND claim_epoch=? AND cancel_requested=0 AND format=? AND CAST(claim_deadline_ms AS BIGINT)>"
                + self.clock
                + " RETURNING id",
                [
                    lease_seconds * 1000,
                    claim.item_id,
                    self.workspace_id,
                    self.queue_name,
                    State.IN_PROGRESS.value,
                    claim.owner_id,
                    claim.epoch,
                    FORMAT,
                ],
            )
            if not changed:
                raise ClaimRejected("Work Item claim expired during renewal")

    def finish_fenced(
        self,
        claim: WorkItemClaim,
        state: State,
        *,
        outputs: tuple[JSONType, ...] = (),
        message: str | None = None,
    ) -> list[str]:
        if state not in (State.DONE, State.FAILED) or (state == State.FAILED and not message):
            raise ValueError("terminal state and failure message required")
        data = [self._payload(payload) for payload in outputs]
        if len(data) > 64 or sum(len(value.encode()) for value in data) > 256 * 1024:
            raise ValueError("output limit exceeded")
        ids = [str(uuid4()) for _ in data]
        with self.store.transaction():
            self._check_format()
            self._require(claim)
            for item, payload in zip(ids, data, strict=False):
                self._seed(payload, item, self.queue_name + "_output", claim.item_id)
            changed = self.store.execute(
                "UPDATE fenced_work_item SET state=?,error_message=?,claim_owner='',claim_deadline_ms=0 WHERE id=? AND workspace_id=? AND queue_name=? AND state=? AND claim_owner=? AND claim_epoch=? AND cancel_requested=0 AND format=? AND CAST(claim_deadline_ms AS BIGINT)>"
                + self.clock
                + " RETURNING id",
                [
                    state.value,
                    message or "",
                    claim.item_id,
                    self.workspace_id,
                    self.queue_name,
                    State.IN_PROGRESS.value,
                    claim.owner_id,
                    claim.epoch,
                    FORMAT,
                ],
            )
            if not changed:
                raise ClaimRejected("Work Item claim expired before publication")
        return ids

    def cancel(self, item_id: str) -> bool:
        with self.store.transaction():
            self._check_format()
            return bool(
                self.store.execute(
                    "UPDATE fenced_work_item SET state=?,cancel_requested=1,claim_owner='',claim_deadline_ms=0,error_message='cancelled' WHERE id=? AND workspace_id=? AND queue_name=? AND state IN (?,?) RETURNING id",
                    [
                        State.FAILED.value,
                        item_id,
                        self.workspace_id,
                        self.queue_name,
                        State.PENDING.value,
                        State.IN_PROGRESS.value,
                    ],
                )
            )

    def list_items(self) -> list[dict[str, Any]]:
        with self.store.transaction():
            self._check_format()
            rows = self.store.execute(
                "SELECT "
                + FIELDS
                + " FROM fenced_work_item WHERE workspace_id=? AND queue_name=? ORDER BY CAST(created_ms AS BIGINT),id LIMIT 100",
                [self.workspace_id, self.queue_name],
            )
            return [dict(zip(FIELDS.split(","), row, strict=False)) for row in rows]

    def load_payload(self, item_id: str) -> JSONType:
        with self.store.transaction():
            self._check_format()
            rows = self.store.execute(
                "SELECT payload FROM fenced_work_item WHERE id=? AND workspace_id=? AND queue_name=?",
                [item_id, self.workspace_id, self.queue_name],
            )
            if not rows:
                raise ValueError("Work Item unavailable")
            return json.loads(rows[0][0])
