"""Lifecycle delegation tests: ports are spies, no installed admission claim."""
from dataclasses import replace
from uuid import uuid4

import pytest
from action_server_tests.run_outputs.test_service import snapshot
from action_server_tests.run_outputs.test_service import store as store

from actions.server.foundry.robot_execution import RobotLaunchIntent, RobotSelection
from actions.server.foundry.robot_lifecycle import VerifiedRobotLifecycle
from actions.server.run_outputs.service import FenceRejected
from actions.server.run_outputs.types import Actor, AttemptFence, OutputRef


@pytest.fixture
def case():
    selected = RobotSelection(
        snapshot(),
        "direct",
        "tasks.robot",
        "Tasks",
        "Selected",
        "sha256:" + "1" * 64,
        b'{"type":"object"}',
        b'{"type":"object"}',
        b'{"value":1}',
    )
    actor = Actor(principal_id=str(uuid4()))
    fence = AttemptFence(
        run_id=str(uuid4()), attempt_id=str(uuid4()), owner_id=str(uuid4()), epoch=1
    )

    class Outputs:
        live = True
        calls = []

        def execution_context(self, actor, fence):
            if not self.live:
                raise FenceRejected("stale")
            return selected.snapshot, {"value": 1}

        def heartbeat(self, fence, *, lease_seconds):
            self.execution_context(actor, fence)
            self.calls.append(("heartbeat", lease_seconds))

        def stage(self, fence, chunks, **kwargs):
            self.execution_context(actor, fence)
            self.calls.append(("stage", b"".join(chunks), kwargs))
            return OutputRef(
                workspace_id=str(selected.snapshot.deployment.workspace_id.root),
                run_id=fence.run_id,
                output_id=str(uuid4()),
            )

    class Journal:
        intent = None
        uncertain = False

        def launch_intent(self, actor, fence):
            return self.intent

        def record_launch_intent(self, actor, fence, intent):
            outputs.execution_context(actor, fence)
            if self.intent is not None:
                raise FenceRejected("existing")
            self.intent = intent
            if self.uncertain:
                raise RuntimeError("lost acknowledgement")
            return intent

    outputs, journal = Outputs(), Journal()
    lifecycle = VerifiedRobotLifecycle(
        outputs,
        lambda *args: selected,
        journal,
        lease_seconds=60,
        retention_seconds=300,
    )
    return lifecycle, outputs, journal, actor, fence, selected


def test_delegates_without_admit_publish_or_terminalize(case):
    life, outputs, _, actor, fence, selected = case
    assert life.check_live(actor, fence, selected) == selected.snapshot
    life.heartbeat(actor, fence, selected)
    intent = RobotLaunchIntent(selected, fence, str(uuid4()))
    assert life.record_launch_intent(actor, fence, intent) == intent
    ref = life.stage_output(
        actor,
        fence,
        name="robot-output.xml",
        media_type="application/xml",
        content=b"<robot/>",
    )
    assert ref.run_id == fence.run_id
    assert outputs.calls[0] == ("heartbeat", 60)
    assert outputs.calls[1][1] == b"<robot/>"
    with pytest.raises(FenceRejected, match="reconciliation"):
        life.record_launch_intent(actor, fence, intent)


def test_uncertain_ack_blocks_blind_retry(case):
    life, _, journal, actor, fence, selected = case
    journal.uncertain = True
    intent = RobotLaunchIntent(selected, fence, str(uuid4()))
    with pytest.raises(RuntimeError, match="acknowledgement"):
        life.record_launch_intent(actor, fence, intent)
    with pytest.raises(FenceRejected, match="reconciliation"):
        life.record_launch_intent(actor, fence, intent)
    assert journal.intent == intent


def test_stale_and_selection_mismatch_fail_closed(case):
    life, outputs, _, actor, fence, selected = case
    with pytest.raises(FenceRejected):
        life.check_live(actor, fence, replace(selected, task_name="Other"))
    life.resolve_selection = lambda *args: replace(selected, inputs=b'{"value":true}')
    with pytest.raises(FenceRejected, match="inputs"):
        life.check_live(actor, fence, selected)
    outputs.live = False
    with pytest.raises(FenceRejected, match="stale"):
        life.heartbeat(actor, fence, selected)
    assert not outputs.calls


def test_staging_requires_intent_and_bounded_bytes(case):
    life, _, _, actor, fence, selected = case
    with pytest.raises(FenceRejected, match="intent"):
        life.stage_output(actor, fence, name="x", media_type="text/plain", content=b"x")
    life.record_launch_intent(
        actor, fence, RobotLaunchIntent(selected, fence, str(uuid4()))
    )
    with pytest.raises(ValueError):
        life.stage_output(
            actor,
            fence,
            name="x",
            media_type="text/plain",
            content=b"x" * (1024 * 1024 + 1),
        )


def test_atomic_journal_rejects_stale_race(case):
    life, outputs, journal, actor, fence, selected = case
    original = journal.record_launch_intent

    def stale_before_cas(actor, fence, intent):
        outputs.live = False
        return original(actor, fence, intent)

    journal.record_launch_intent = stale_before_cas
    with pytest.raises(FenceRejected, match="stale"):
        life.record_launch_intent(
            actor, fence, RobotLaunchIntent(selected, fence, str(uuid4()))
        )
    assert journal.intent is None


def test_service_stage_rejects_stale_race(case):
    life, outputs, _, actor, fence, selected = case
    life.record_launch_intent(
        actor, fence, RobotLaunchIntent(selected, fence, str(uuid4()))
    )
    original = outputs.stage

    def stale_before_stage(*args, **kwargs):
        outputs.live = False
        return original(*args, **kwargs)

    outputs.stage = stale_before_stage
    with pytest.raises(FenceRejected, match="stale"):
        life.stage_output(actor, fence, name="x", media_type="text/plain", content=b"x")
    assert not outputs.calls


def test_real_run_output_authority_stages_and_rejects_cancel(store):  # noqa: F811 - pytest fixture
    _, _, outputs, snap, actor, _, _ = store
    run = outputs.admit(actor, snap, {"query": "alpha"}, "robot-lifecycle-proof")
    fence = outputs.claim(run.id, str(uuid4()), lease_seconds=60)
    selected = RobotSelection(
        snap,
        "direct",
        "tasks.robot",
        "Tasks",
        "Selected",
        "sha256:" + "1" * 64,
        b'{"type":"object"}',
        b'{"type":"object"}',
        b'{"query":"alpha"}',
    )

    class Journal:
        intent = None

        def launch_intent(self, actor, fence):
            outputs.execution_context(actor, fence)
            return self.intent

        def record_launch_intent(self, actor, fence, intent):
            # Single-threaded spy only, NOT the production atomic journal.
            outputs.execution_context(actor, fence)
            assert self.intent is None
            self.intent = intent
            return intent

    life = VerifiedRobotLifecycle(
        outputs,
        lambda *args: selected,
        Journal(),
        lease_seconds=60,
        retention_seconds=300,
    )
    life.heartbeat(actor, fence, selected)
    life.record_launch_intent(
        actor, fence, RobotLaunchIntent(selected, fence, str(uuid4()))
    )
    output = life.stage_output(
        actor,
        fence,
        name="robot-output.xml",
        media_type="application/xml",
        content=b"<robot/>",
    )
    assert output.run_id == run.id
    assert outputs.cancel(actor, run.id)
    with pytest.raises(FenceRejected):
        life.stage_output(
            actor,
            fence,
            name="later.xml",
            media_type="application/xml",
            content=b"<robot/>",
        )
