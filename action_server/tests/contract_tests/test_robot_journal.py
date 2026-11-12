"""Real common Run authority; the immutable selection callback is prebound."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.run_outputs.test_service import insert_action, snapshot

from actions.server._database import Database
from actions.server._models import Run, create_db, get_all_model_classes
from actions.server.foundry.robot_execution import RobotLaunchIntent, RobotSelection
from actions.server.foundry.robot_journal import RobotJournal
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def store(database_location, foundry_package_store):
    with create_db(database_location) as db:
        control = RunOutputControlPlane(db)
        snap = snapshot()
        actor = Actor(principal_id=str(uuid4()))
        insert_action(db, snap)
        control.register(snap)
        control.grant(actor, snap.deployment, {"execute", "read", "cancel"})
        provider = foundry_package_store
        yield (
            db,
            control,
            RunOutputService(db, {snap.provider_key: provider}),
            snap,
            actor,
            provider,
            None,
        )


@pytest.fixture
def case(store):
    db, control, outputs, snapshot, actor, provider, root = store
    run = outputs.admit(actor, snapshot, {"query": "alpha"}, "robot")
    fence = outputs.claim(run.id, str(uuid4()), lease_seconds=60)
    selection = RobotSelection(
        snapshot,
        "direct",
        "task.robot",
        "Task",
        "Run",
        "sha256:" + "a" * 64,
        b'{"type":"object"}',
        b'{"type":"object"}',
        b'{"query":"alpha"}',
    )
    envelope = dict(
        version="actions.robot-dispatch/v1",
        mode="standalone",
        claim=None,
        fence=fence.model_dump(mode="json"),
        launch=None,
    )
    with db.transaction():
        db.update_by_id(Run, run.id, {"result": json.dumps(envelope)})
    journal = RobotJournal(outputs, lambda a, f: selection)
    intent = RobotLaunchIntent(selection, fence, str(uuid4()))
    return SimpleNamespace(
        db=db,
        control=control,
        outputs=outputs,
        selection=selection,
        actor=actor,
        provider=provider,
        run=run,
        fence=fence,
        journal=journal,
        intent=intent,
        envelope=envelope,
    )


def test_roundtrip_reopen_and_duplicate_denial_no_io(case, monkeypatch):
    c = case
    monkeypatch.setattr(
        c.provider, "open", lambda *a: pytest.fail("provider read inside journal")
    )
    monkeypatch.setattr(
        c.provider, "stage", lambda *a: pytest.fail("provider write inside journal")
    )
    from pathlib import Path

    monkeypatch.setattr(
        Path, "read_bytes", lambda *a: pytest.fail("filesystem read inside journal")
    )
    assert c.journal.launch_intent(c.actor, c.fence) is None
    assert c.journal.record_launch_intent(c.actor, c.fence, c.intent) == c.intent
    db = Database(c.db.db_path)
    with db.connect():
        db.initialize(get_all_model_classes())
        reopened = RobotJournal(RunOutputService(db, {}), lambda a, f: c.selection)
        assert reopened.launch_intent(c.actor, c.fence) == c.intent
        with pytest.raises(FenceRejected):
            reopened.record_launch_intent(c.actor, c.fence, c.intent)


@pytest.mark.parametrize(
    "mutation",
    [
        "input",
        "snapshot",
        "selection",
        "launch",
        "extra",
        "version",
        "claim",
        "bool-epoch",
    ],
)
def test_mutations_rejected(case, mutation):
    c = case
    if mutation == "input":
        with c.db.transaction():
            c.db.update_by_id(Run, c.run.id, {"inputs": '{"query":"changed"}'})
    elif mutation == "snapshot":
        c.journal.require_selection = lambda a, f: replace(
            c.selection,
            snapshot=c.selection.snapshot.model_copy(
                update={"runtime_kind": "changed"}
            ),
        )
    elif mutation == "selection":
        c.intent = replace(c.intent, selection=replace(c.selection, task_name="Other"))
    elif mutation == "launch":
        c.intent = replace(c.intent, launch_id="not-a-uuid")
    else:
        envelope = dict(c.envelope)
        if mutation == "extra":
            envelope["unexpected"] = True
        if mutation == "bool-epoch":
            envelope["fence"] = {**envelope["fence"], "epoch": True}
        if mutation == "version":
            envelope["version"] = "actions.generated-rcc-dispatch/v1"
        if mutation == "claim":
            envelope["claim"] = {"item_id": str(uuid4())}
        with c.db.transaction():
            c.db.update_by_id(Run, c.run.id, {"result": json.dumps(envelope)})
    with pytest.raises((FenceRejected, AccessDenied, ValueError)):
        c.journal.record_launch_intent(c.actor, c.fence, c.intent)


@pytest.mark.parametrize("denial", ["actor", "cancel", "epoch", "revoked", "callback"])
def test_live_authority_denies(case, denial):
    c = case
    actor = c.actor
    fence = c.fence
    if denial == "actor":
        actor = Actor(principal_id=str(uuid4()))
    if denial == "cancel":
        c.outputs.cancel(c.actor, c.run.id)
    if denial == "epoch":
        fence = c.fence.model_copy(update={"epoch": c.fence.epoch + 1})
    if denial == "revoked":
        c.control.grant(c.actor, c.selection.snapshot.deployment, {"read"})
    if denial == "callback":

        def denied(a, f):
            raise FenceRejected("canonical source pin revoked")

        c.journal.require_selection = denied
    with pytest.raises((FenceRejected, AccessDenied)):
        c.journal.record_launch_intent(actor, fence, c.intent)


def test_lost_ack_preserves_intent_and_forbids_retry(case, monkeypatch):
    c = case

    def lost(*args):
        raise RuntimeError("acknowledgement lost")

    monkeypatch.setattr(c.journal, "launch_intent", lost)
    with pytest.raises(RuntimeError, match="acknowledgement"):
        c.journal.record_launch_intent(c.actor, c.fence, c.intent)
    reopened = RobotJournal(c.outputs, lambda a, f: c.selection)
    assert reopened.launch_intent(c.actor, c.fence) == c.intent
    with pytest.raises(FenceRejected):
        reopened.record_launch_intent(c.actor, c.fence, c.intent)


def test_competing_connections_only_one_intent(case):
    c = case
    barrier = Barrier(2)

    def compete(_):
        db = Database(c.db.db_path)
        with db.connect():
            db.initialize(get_all_model_classes())
            journal = RobotJournal(RunOutputService(db, {}), lambda a, f: c.selection)
            intent = replace(c.intent, launch_id=str(uuid4()))
            barrier.wait(timeout=10)
            try:
                return journal.record_launch_intent(c.actor, c.fence, intent)
            except FenceRejected:
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(compete, range(2)))
    assert sum(r is not None for r in results) == 1
    assert c.journal.launch_intent(c.actor, c.fence) == next(
        r for r in results if r is not None
    )


def test_work_item_claim_epoch_is_independent_and_exact(case):
    c = case
    claim = SimpleNamespace(item_id=str(uuid4()), owner_id=c.fence.owner_id, epoch=7)
    c.outputs.ticket = SimpleNamespace(claim=claim)
    envelope = dict(c.envelope, mode="work-items", claim=vars(claim))
    with c.db.transaction():
        c.db.update_by_id(Run, c.run.id, {"result": json.dumps(envelope)})
    assert c.journal.record_launch_intent(c.actor, c.fence, c.intent) == c.intent
    claim.item_id = str(uuid4())
    with pytest.raises(FenceRejected):
        c.journal.launch_intent(c.actor, c.fence)


def test_duplicate_keys_and_untrusted_claim_rejected(case):
    c = case
    raw = json.dumps(c.envelope)[:-1] + ', "launch": null}'
    with c.db.transaction():
        c.db.update_by_id(Run, c.run.id, {"result": raw})
    with pytest.raises(FenceRejected, match="duplicate"):
        c.journal.launch_intent(c.actor, c.fence)
    envelope = dict(
        c.envelope,
        mode="work-items",
        claim={"item_id": str(uuid4()), "owner_id": c.fence.owner_id, "epoch": 1},
    )
    with c.db.transaction():
        c.db.update_by_id(Run, c.run.id, {"result": json.dumps(envelope)})
    with pytest.raises(FenceRejected, match="canonical independent"):
        c.journal.launch_intent(c.actor, c.fence)


def test_expiry_and_retained_selection_mutation(case):
    from actions.server.run_outputs.models import RunAttempt

    c = case
    c.journal.record_launch_intent(c.actor, c.fence, c.intent)
    changed = replace(c.selection, source_digest="sha256:" + "b" * 64)
    c.journal.require_selection = lambda a, f: changed
    with pytest.raises(FenceRejected):
        c.journal.launch_intent(c.actor, c.fence)
    c.journal.require_selection = lambda a, f: c.selection
    with c.db.transaction():
        c.db.update_by_id(RunAttempt, c.fence.attempt_id, {"lease_deadline_ms": 0})
    with pytest.raises(FenceRejected):
        c.journal.launch_intent(c.actor, c.fence)


def test_retained_intent_encoding_cannot_coerce_boolean_epoch(case):
    c = case
    c.journal.record_launch_intent(c.actor, c.fence, c.intent)
    with c.db.transaction():
        run = c.db.first(Run, "SELECT * FROM run WHERE id=?", [c.run.id])
        value = json.loads(run.result)
        value["launch"]["fence"]["epoch"] = True
        c.db.update_by_id(Run, c.run.id, {"result": json.dumps(value)})
    with pytest.raises((FenceRejected, ValueError)):
        c.journal.launch_intent(c.actor, c.fence)


def test_outer_transaction_cannot_acknowledge_launch_before_rollback(case):
    c = case
    acknowledgements = []

    class OuterAbort(Exception):
        pass

    with pytest.raises(OuterAbort):
        with c.db.transaction():
            with pytest.raises(FenceRejected, match="outer transaction"):
                acknowledgements.append(
                    c.journal.record_launch_intent(c.actor, c.fence, c.intent)
                )
            raise OuterAbort()
    assert acknowledgements == []
    assert c.journal.launch_intent(c.actor, c.fence) is None
    # Outside the rejected outer transaction the ordinary durable path works.
    assert c.journal.record_launch_intent(c.actor, c.fence, c.intent) == c.intent
