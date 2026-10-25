"""Canonical Robot launch intent only; no admission, publication or retry."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import fields
from uuid import UUID

from actions.server._models import Run
from actions.server.foundry.robot_execution import (
    DISCRIMINATOR,
    RobotLaunchIntent,
    RobotSelection,
)
from actions.server.run_outputs.service import (
    MAX_RESULT_BYTES,
    FenceRejected,
    RunOutputService,
    _canonical,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import Actor, AttemptFence, ExecutionSnapshot

_ENCODING = "actions.robot-selection/utf8-json/v1"


def _closed_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FenceRejected("duplicate Robot journal key")
        result[key] = value
    return result


def _selection(value: RobotSelection) -> dict:
    if type(value) is not RobotSelection:
        raise FenceRejected("trusted Robot selection required")
    value.__post_init__()
    result = {field.name: getattr(value, field.name) for field in fields(value)}
    result["snapshot"] = value.snapshot.model_dump(mode="json")
    result["python_version"] = list(value.python_version)
    for key in ("input_schema", "output_schema", "inputs"):
        result[key] = result[key].decode("utf-8", errors="strict")
    return result


def _decode(value: object) -> RobotSelection:
    if not isinstance(value, dict) or set(value) != {
        field.name for field in fields(RobotSelection)
    }:
        raise FenceRejected("closed Robot selection required")
    raw = dict(value)
    raw["snapshot"] = ExecutionSnapshot.model_validate(raw["snapshot"])
    if not isinstance(raw["python_version"], list):
        raise FenceRejected("Robot version encoding differs")
    raw["python_version"] = tuple(raw["python_version"])
    for key in ("input_schema", "output_schema", "inputs"):
        if not isinstance(raw[key], str):
            raise FenceRejected("Robot JSON byte encoding differs")
        raw[key] = raw[key].encode("utf-8")
    return RobotSelection(**raw)


def _launch(value: RobotLaunchIntent) -> dict:
    if type(value) is not RobotLaunchIntent or value.discriminator != DISCRIMINATOR:
        raise FenceRejected("typed Robot launch intent required")
    if str(UUID(value.launch_id)) != value.launch_id:
        raise FenceRejected("canonical Robot launch identity required")
    return {
        "discriminator": value.discriminator,
        "selection_encoding": _ENCODING,
        "selection": _selection(value.selection),
        "fence": value.fence.model_dump(mode="json"),
        "launch_id": value.launch_id,
    }


class RobotJournal:
    """The callback validates current SQL authority against prebound immutable data.

    It must not load artifacts/providers/files. Work-item outputs must expose the
    canonical ticket.claim; its epoch remains independent from the Attempt epoch.
    The admission owner creates the closed launch:null envelope before this port.
    """

    def __init__(
        self,
        outputs: RunOutputService,
        require_selection: Callable[[Actor, AttemptFence], RobotSelection],
    ):
        self.outputs = outputs
        self.require_selection = require_selection

    def _read(self, actor, fence):
        # Acquire the existing Run write lock before any journal SELECT (SQLite
        # must not enter a deferred read transaction before competing writers).
        self.outputs._fence(fence)
        snapshot, inputs = self.outputs.execution_context(actor, fence)
        selection = self.require_selection(actor, fence)
        _selection(selection)
        if (
            selection.snapshot != snapshot
            or selection.inputs
            != json.dumps(
                inputs, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        ):
            raise FenceRejected("Robot selection differs from canonical admission")
        run = _one(self.outputs.db, Run, fence.run_id)
        if (
            not isinstance(run.result, str)
            or len(run.result.encode()) > MAX_RESULT_BYTES
        ):
            raise FenceRejected("bounded preexisting Robot journal required")
        journal = json.loads(run.result, object_pairs_hook=_closed_pairs)
        if (
            not isinstance(journal, dict)
            or set(journal) != {"version", "mode", "claim", "fence", "launch"}
            or journal["version"] != DISCRIMINATOR
            or _canonical(journal["fence"], MAX_RESULT_BYTES)
            != _canonical(fence.model_dump(mode="json"), MAX_RESULT_BYTES)
        ):
            raise FenceRejected("closed current Robot journal required")
        claim = getattr(getattr(self.outputs, "ticket", None), "claim", None)
        if journal["mode"] == "standalone":
            if journal["claim"] is not None or claim is not None:
                raise FenceRejected("standalone Robot claim differs")
        elif journal["mode"] == "work-items":
            actual = journal["claim"]
            if (
                claim is None
                or not isinstance(actual, dict)
                or set(actual) != {"item_id", "owner_id", "epoch"}
                or actual
                != {
                    "item_id": claim.item_id,
                    "owner_id": claim.owner_id,
                    "epoch": claim.epoch,
                }
                or actual["owner_id"] != fence.owner_id
                or not isinstance(actual["epoch"], int)
                or isinstance(actual["epoch"], bool)
                or not 1 <= actual["epoch"] <= 2_147_483_647
            ):
                raise FenceRejected("canonical independent Robot claim required")
            for key in ("item_id", "owner_id"):
                if str(UUID(actual[key])) != actual[key]:
                    raise FenceRejected("canonical Robot claim identity required")
        else:
            raise FenceRejected("unsupported Robot journal mode")
        return journal, selection

    def _intent(self, raw, fence, selection):
        if raw is None:
            return None
        if (
            not isinstance(raw, dict)
            or set(raw)
            != {
                "discriminator",
                "selection_encoding",
                "selection",
                "fence",
                "launch_id",
            }
            or raw["selection_encoding"] != _ENCODING
        ):
            raise FenceRejected("closed Robot intent required")
        intent = RobotLaunchIntent(
            _decode(raw["selection"]),
            AttemptFence.model_validate(raw["fence"]),
            raw["launch_id"],
            raw["discriminator"],
        )
        if (
            _canonical(_launch(intent), MAX_RESULT_BYTES)
            != _canonical(raw, MAX_RESULT_BYTES)
            or intent.fence != fence
            or intent.selection != selection
        ):
            raise FenceRejected("Robot intent differs from canonical selection")
        return intent

    def launch_intent(self, actor, fence) -> RobotLaunchIntent | None:
        actor, fence = Actor.model_validate(actor), AttemptFence.model_validate(fence)
        with _transaction(self.outputs.db):
            journal, selection = self._read(actor, fence)
            return self._intent(journal["launch"], fence, selection)

    def record_launch_intent(self, actor, fence, intent) -> RobotLaunchIntent:
        # A nested Database.transaction is only a savepoint. Acknowledging it
        # could permit a process launch before an outer rollback erases intent.
        # This method must own the durable commit, not merely release a savepoint.
        if self.outputs.db.in_transaction():
            raise FenceRejected(
                "Robot launch cannot be recorded in an outer transaction"
            )
        actor, fence = Actor.model_validate(actor), AttemptFence.model_validate(fence)
        encoded = _launch(intent)
        with _transaction(self.outputs.db):
            journal, selection = self._read(actor, fence)
            if journal["launch"] is not None:
                raise FenceRejected("existing Robot launch requires reconciliation")
            self._intent(encoded, fence, selection)
            journal["launch"] = encoded
            _update(
                self.outputs.db,
                Run,
                fence.run_id,
                {"result": _canonical(journal, MAX_RESULT_BYTES)},
            )
        # A failed acknowledgement must propagate; never turn it into permission
        # to spawn. Reopen reads are for reconciliation, never an idempotent CAS.
        confirmed = self.launch_intent(actor, fence)
        if confirmed is None or confirmed != intent:
            raise FenceRejected("Robot launch acknowledgement uncertain")
        return confirmed
