"""Bounded generated data from authorized sealed results, never UI metadata."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from actions.server._models import Run, RunStatus
from actions.server.deployments.canonical import canonicalize_json
from actions.server.foundry.logical_receipts import (
    EXECUTION_V1,
    EXECUTION_V2,
    EXECUTION_V3,
)
from actions.server.run_outputs.models import (
    RunAttempt,
    RunExecutionIntent,
    RunOutput,
    RunPin,
)
from actions.server.run_outputs.service import (
    AccessDenied,
    RunOutputService,
    _lock_workspace,
    _one,
    _transaction,
)
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    ExecutionSnapshot,
    OutputRef,
    canonical_uuid,
)

_LIMIT = 65536
_NAME = "generated-action-result.json"


@dataclass(frozen=True)
class GeneratedProjection:
    binding_id: str
    run_id: str
    attempt_id: str
    canonical_json: str

    @property
    def data(self) -> Any:
        """Return an isolated value parsed from the same canonical output bytes."""
        return json.loads(self.canonical_json)

    def as_dict(self) -> dict[str, Any]:
        return {
            "bindingId": self.binding_id,
            "runId": self.run_id,
            "attemptId": self.attempt_id,
            "canonicalJson": self.canonical_json,
            "data": self.data,
        }


def terminal_preimage(outputs: RunOutputService, run_id: str, attempt_id: str) -> str:
    """SQL-only identity pin; caller must hold its existing validation transaction."""
    if not outputs.db.in_transaction():
        raise AccessDenied("terminal identity pin requires a transaction")
    run = _one(outputs.db, Run, run_id)
    pin = _one(outputs.db, RunPin, run_id)
    attempt = _one(outputs.db, RunAttempt, attempt_id)
    envelope = json.loads(run.result or "null")
    raw = envelope.get("outputs") if isinstance(envelope, dict) else None
    if not isinstance(raw, list) or not 1 <= len(raw) <= 64:
        raise AccessDenied("bounded attached output inventory required")
    refs = [OutputRef.model_validate(value) for value in raw]
    return json.dumps(
        {
            "run": asdict(run),
            "pin": asdict(pin),
            "attempt": asdict(attempt),
            "intents": [
                asdict(value)
                for value in outputs.db.all(
                    RunExecutionIntent, where="id=?", values=[run_id]
                )
            ],
            "outputs": [
                asdict(_one(outputs.db, RunOutput, ref.output_id)) for ref in refs
            ],
        },
        sort_keys=True,
    )


def project_generated_result(
    outputs: RunOutputService,
    actor: Actor,
    *,
    snapshot: ExecutionSnapshot,
    binding_id: str,
    run_id: str,
    attempt_id: str,
    require_current: Callable[[], None],
) -> GeneratedProjection:
    """Caller binds app/binding association and queue artifact grants in callback.

    IDs/snapshot are host-derived from the existing selected app and ticket, not
    accepted as sufficient authority. The callback runs before and after reading
    and must perform current SQL checks only. This helper owns no grants or state.
    """
    if outputs.db.in_transaction():
        raise AccessDenied("projection must resolve outside an enclosing transaction")
    actor = Actor.model_validate(actor)
    snapshot = ExecutionSnapshot.model_validate(snapshot)
    canonical_uuid(run_id)
    canonical_uuid(attempt_id)
    if (
        not isinstance(binding_id, str)
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", binding_id) is None
    ):
        raise AccessDenied("exact binding required")

    def current():
        with _transaction(outputs.db):
            _lock_workspace(outputs.db, snapshot.workspace_id)
            require_current()
            pin = _one(outputs.db, RunPin, run_id)
            run = _one(outputs.db, Run, run_id)
            attempt = _one(outputs.db, RunAttempt, attempt_id)
            if (
                pin.current_attempt_id != attempt_id
                or pin.cancel_requested
                or pin.admission_principal_id != actor.principal_id
                or outputs._pinned(pin) != snapshot
                or run.status != RunStatus.PASSED
                or attempt.state != "succeeded"
                or attempt.run_id != run_id
                or attempt.workspace_id != snapshot.workspace_id
                or attempt.epoch != pin.epoch
            ):
                raise AccessDenied("successful current generated Run required")
            outputs._authorize(actor, snapshot, "read")
            envelope = json.loads(run.result or "null")
            if (
                not isinstance(envelope, dict)
                or isinstance(envelope.get("version"), bool)
                or envelope.get("version") != 1
            ):
                raise AccessDenied("attached output envelope required")
            raw = envelope.get("outputs")
            receipt = envelope.get("result")
            if (
                not isinstance(raw, list)
                or not 1 <= len(raw) <= 64
                or not isinstance(receipt, dict)
            ):
                raise AccessDenied("bounded generated output inventory required")
            if receipt.get("version") not in {EXECUTION_V1, EXECUTION_V2, EXECUTION_V3}:
                raise AccessDenied("generated execution receipt required")
            fence = AttemptFence.model_validate(receipt.get("publicationFence"))
            if (fence.run_id, fence.attempt_id, fence.owner_id, fence.epoch) != (
                run_id,
                attempt_id,
                attempt.owner_id,
                attempt.epoch,
            ):
                raise AccessDenied("generated publication Attempt differs")
            refs = [OutputRef.model_validate(value) for value in raw]
            if len({ref.output_id for ref in refs}) != len(refs) or any(
                ref.run_id != run_id or ref.workspace_id != snapshot.workspace_id
                for ref in refs
            ):
                raise AccessDenied("output outside exact generated Run")
            selected = []
            for ref in refs:
                row = _one(outputs.db, RunOutput, ref.output_id)
                if (
                    row.run_id != run_id
                    or row.workspace_id != snapshot.workspace_id
                    or row.run_attempt_id != attempt_id
                    or row.epoch != attempt.epoch
                    or row.state != "final"
                ):
                    raise AccessDenied("attached output identity differs")
                if row.name == _NAME:
                    selected.append((ref, row))
            if len(selected) != 1:
                raise AccessDenied("unique generated result artifact required")
            ref, row = selected[0]
            if (
                row.run_id != run_id
                or row.workspace_id != snapshot.workspace_id
                or row.run_attempt_id != attempt_id
                or row.epoch != attempt.epoch
                or row.media_type != "application/json"
                or row.state != "final"
                or not 0 <= row.size <= _LIMIT
            ):
                raise AccessDenied("bounded exact generated result required")
            records = receipt.get("outputs")
            if not isinstance(records, list) or len(records) > 64:
                raise AccessDenied("bounded generated output receipts required")
            matches = [
                record
                for record in records
                if isinstance(record, dict) and record.get("name") == _NAME
            ]
            expected = {
                "name": _NAME,
                "ref": ref.model_dump(mode="json"),
                "digest": row.digest,
                "size": row.size,
            }
            if len(matches) != 1 or canonicalize_json(
                json.dumps(matches[0]).encode()
            ) != canonicalize_json(json.dumps(expected).encode()):
                raise AccessDenied("generated result receipt differs")
            preimage = terminal_preimage(outputs, run_id, attempt_id)
            return ref, row.digest, row.size, preimage

    ref, digest, size, preimage = current()
    with outputs.resolve(actor, snapshot.workspace_id, ref.handle) as resolved:
        if (
            resolved.run_id != run_id
            or resolved.name != _NAME
            or resolved.media_type != "application/json"
            or resolved.size != size
            or resolved.digest != digest
        ):
            raise AccessDenied("resolved generated artifact differs")
        raw = resolved.read(_LIMIT + 1)
        if (
            len(raw) > _LIMIT
            or len(raw) != size
            or "sha256:" + hashlib.sha256(raw).hexdigest() != digest
        ):
            raise AccessDenied("generated result bytes differ or exceed limit")
    canonical = canonicalize_json(raw)
    if len(canonical) > _LIMIT:
        raise AccessDenied("canonical projection exceeds limit")
    if current() != (ref, digest, size, preimage):
        raise AccessDenied("generated projection changed during resolution")
    return GeneratedProjection(
        binding_id, run_id, attempt_id, canonical.decode("utf-8")
    )
