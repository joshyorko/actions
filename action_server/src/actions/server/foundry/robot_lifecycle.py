"""Robot lifecycle delegation to canonical host authorities; no SQL or scheduler."""
from __future__ import annotations

import json
from typing import Callable, Protocol

from actions.server.foundry.robot_execution import RobotLaunchIntent, RobotSelection
from actions.server.run_outputs.service import FenceRejected, RunOutputService
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    ExecutionSnapshot,
    OutputRef,
)


class RobotJournalPort(Protocol):
    """Host-owned durable journal. Both calls must validate actor and live fence.

    record_launch_intent atomically validates canonical admitted selection, authority and
    fence while CAS-writing intent. Existing intent always rejects, including an
    identical one. An uncertain acknowledgement requires reconciliation.
    """

    def launch_intent(
        self, actor: Actor, fence: AttemptFence
    ) -> RobotLaunchIntent | None:
        ...

    def record_launch_intent(
        self, actor: Actor, fence: AttemptFence, intent: RobotLaunchIntent
    ) -> RobotLaunchIntent:
        ...


VerifiedSelectionResolver = Callable[
    [Actor, AttemptFence, ExecutionSnapshot, object], RobotSelection
]


class VerifiedRobotLifecycle:
    def __init__(
        self,
        outputs: RunOutputService,
        resolve_selection: VerifiedSelectionResolver,
        journal: RobotJournalPort,
        *,
        lease_seconds: int,
        retention_seconds: int,
    ):
        if (
            not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool)
        ) or not 1 <= lease_seconds <= 3600:
            raise ValueError("bounded lease required")
        if (
            not isinstance(retention_seconds, int)
            or isinstance(retention_seconds, bool)
        ) or not 1 <= retention_seconds <= 86400 * 365:
            raise ValueError("bounded retention required")
        self.outputs = outputs
        self.resolve_selection = resolve_selection
        self.journal = journal
        self.lease_seconds = lease_seconds
        self.retention_seconds = retention_seconds

    def _selected(self, actor: Actor, fence: AttemptFence) -> RobotSelection:
        snapshot, inputs = self.outputs.execution_context(actor, fence)
        selected = self.resolve_selection(actor, fence, snapshot, inputs)
        if type(selected) is not RobotSelection or selected.snapshot != snapshot:
            raise FenceRejected(
                "Robot selection differs from canonical execution context"
            )
        canonical_inputs = json.dumps(
            inputs, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        if selected.inputs != canonical_inputs:
            raise FenceRejected("Robot inputs differ from canonical execution context")
        return selected

    def check_live(
        self, actor: Actor, fence: AttemptFence, selection: RobotSelection
    ) -> ExecutionSnapshot:
        if self._selected(actor, fence) != selection:
            raise FenceRejected(
                "Robot selection differs from admitted source/plan/input"
            )
        return selection.snapshot

    def heartbeat(
        self, actor: Actor, fence: AttemptFence, selection: RobotSelection
    ) -> None:
        self.check_live(actor, fence, selection)
        self.outputs.heartbeat(fence, lease_seconds=self.lease_seconds)

    def launch_intent(
        self, actor: Actor, fence: AttemptFence
    ) -> RobotLaunchIntent | None:
        selected = self._selected(actor, fence)
        intent = self.journal.launch_intent(actor, fence)
        if intent is not None and (
            intent.fence != fence or intent.selection != selected
        ):
            raise FenceRejected("Robot journal identity differs")
        return intent

    def record_launch_intent(
        self, actor: Actor, fence: AttemptFence, intent: RobotLaunchIntent
    ) -> RobotLaunchIntent:
        if intent.fence != fence:
            raise FenceRejected("Robot launch fence differs")
        self.check_live(actor, fence, intent.selection)
        if self.journal.launch_intent(actor, fence) is not None:
            raise FenceRejected("existing Robot launch requires reconciliation")
        confirmed = self.journal.record_launch_intent(actor, fence, intent)
        if confirmed != intent or self.launch_intent(actor, fence) != intent:
            raise FenceRejected("uncertain Robot launch requires reconciliation")
        return confirmed

    def stage_output(
        self,
        actor: Actor,
        fence: AttemptFence,
        *,
        name: str,
        media_type: str,
        content: bytes,
    ) -> OutputRef:
        if self.launch_intent(actor, fence) is None:
            raise FenceRejected("Robot output requires confirmed launch intent")
        if not isinstance(content, bytes) or len(content) > 1024 * 1024:
            raise ValueError("bounded Robot output bytes required")
        return self.outputs.stage(
            fence,
            (content,),
            name=name,
            media_type=media_type,
            retention_seconds=self.retention_seconds,
        )
