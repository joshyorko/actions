# Imported pytest fixture names are intentionally used as parameters.
# ruff: noqa: F811
"""Independent-connection Robot publication boundaries; no Robot process launch."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier, Event

import pytest
from action_server_tests.test_robot_claimed_work_items_327 import claimed as claimed
from action_server_tests.test_robot_claimed_work_items_327 import (
    disable_feedback as disable_feedback,
)
from action_server_tests.test_robot_runtime_runner import SyntheticAdapter
from actions.work_items import State
from actions.work_items._adapters._sql_review import SQLReviewQueue
from actions.work_items._fencing import ClaimRejected

from actions.server._database import Database
from actions.server._models import Run, RunStatus, get_all_model_classes
from actions.server.data_queries.review import _SQLStore
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.robot_work_item_authority import (
    prepare_robot_work_item_authority,
)
from actions.server.managed_work_items.contracts import Permission
from actions.server.run_outputs.models import RunAttempt, RunOutput
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputService,
    _one,
    _update,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def queue_for(db, c):
    return SQLReviewQueue(
        _SQLStore(db, c.owner.snapshot.workspace_id),
        c.owner.snapshot.workspace_id,
        c.owner.policy.input_queue,
    )


@pytest.mark.parametrize("mutation", ["cancel", "complete"])
def test_committed_late_authority_change_blocks_publication(
    claimed, database_location, mutation
):
    c = claimed()
    staged = Barrier(2)
    committed = Event()

    def contender():
        db = Database(database_location)
        with db.connect():
            db.initialize(get_all_model_classes())
            staged.wait(timeout=20)
            try:
                if mutation == "cancel":
                    assert queue_for(db, c).cancel(c.item)
                else:
                    changed = 0
                    with db.transaction():
                        for grant in db.all(FoundryAccessGrant):
                            operations = json.loads(grant.operations_json)
                            if (
                                grant.principal_id == c.caller.actor.principal_id
                                and Permission.COMPLETE.value in operations
                            ):
                                operations.remove(Permission.COMPLETE.value)
                                _update(
                                    db,
                                    FoundryAccessGrant,
                                    grant.id,
                                    {"operations_json": json.dumps(operations)},
                                )
                                changed += 1
                    assert changed
            finally:
                committed.set()

    class Adapter(SyntheticAdapter):
        def execute(self, *args, **kwargs):
            result = super().execute(*args, **kwargs)
            staged.wait(timeout=20)
            assert committed.wait(20)
            other.result(timeout=20)
            return result

    with ThreadPoolExecutor(max_workers=1) as pool:
        other = pool.submit(contender)
        with pytest.raises((AccessDenied, FenceRejected, ClaimRejected)):
            replace(c.runner, adapter_factory=Adapter).execute(
                c.caller, c.ticket, c.owner
            )
        other.result(timeout=20)
    assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.RUNNING
    assert _one(c.db, RunAttempt, c.ticket.fence.attempt_id).state == "running"
    assert all(row.state == "provisional" for row in c.db.all(RunOutput))
    assert len(c.db.all(RunOutput)) == 3
    item = _one(c.db, FencedWorkItem, c.item)
    assert item.state == (
        State.FAILED.value if mutation == "cancel" else State.IN_PROGRESS.value
    )


def test_attempt_renewal_failure_rolls_back_claim_renewal(
    claimed, database_location, monkeypatch
):
    c = claimed()
    authority = prepare_robot_work_item_authority(c.owner, c.caller, c.ticket)
    outputs = c.owner.outputs(c.caller, c.ticket)
    before = (
        _one(c.db, FencedWorkItem, c.item).claim_deadline_ms,
        _one(c.db, RunAttempt, c.ticket.fence.attempt_id).lease_deadline_ms,
    )
    renewed = Barrier(2)
    observed = Event()

    def observer():
        db = Database(database_location)
        with db.connect():
            db.initialize(get_all_model_classes())
            renewed.wait(timeout=20)
            try:
                visible = (
                    _one(db, FencedWorkItem, c.item).claim_deadline_ms,
                    _one(db, RunAttempt, c.ticket.fence.attempt_id).lease_deadline_ms,
                )
                assert visible == before
            finally:
                observed.set()

    def fail_attempt(self, fence, *, lease_seconds):
        # Injection is after the real queue UPDATE, before Attempt publication.
        assert int(_one(self.db, FencedWorkItem, c.item).claim_deadline_ms) > int(
            before[0]
        )
        renewed.wait(timeout=20)
        assert observed.wait(20)
        raise FenceRejected("synthetic Attempt renewal failure")

    with outputs.bind_execution_authority(authority), ThreadPoolExecutor(
        max_workers=1
    ) as pool:
        other = pool.submit(observer)
        with monkeypatch.context() as patch:
            patch.setattr(RunOutputService, "heartbeat", fail_attempt)
            with pytest.raises(FenceRejected, match="synthetic Attempt"):
                outputs.heartbeat(c.ticket.fence, lease_seconds=120)
        other.result(timeout=20)
        assert (
            _one(c.db, FencedWorkItem, c.item).claim_deadline_ms,
            _one(c.db, RunAttempt, c.ticket.fence.attempt_id).lease_deadline_ms,
        ) == before
        outputs.heartbeat(c.ticket.fence, lease_seconds=120)
    assert int(_one(c.db, FencedWorkItem, c.item).claim_deadline_ms) > int(before[0])
    assert int(
        _one(c.db, RunAttempt, c.ticket.fence.attempt_id).lease_deadline_ms
    ) > int(before[1])


def test_cancel_contender_cannot_split_terminal_publication(
    claimed, database_location, monkeypatch
):
    c = claimed()
    finishing = Barrier(2)
    attempted = Event()
    original = SQLReviewQueue.finish_fenced

    def contender():
        db = Database(database_location)
        with db.connect():
            db.initialize(get_all_model_classes())
            finishing.wait(timeout=20)
            attempted.set()
            return queue_for(db, c).cancel(c.item)

    def finish(self, *args, **kwargs):
        # Run/Attempt finalization has happened in the still-uncommitted transaction.
        assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.PASSED
        finishing.wait(timeout=20)
        assert attempted.wait(20)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(SQLReviewQueue, "finish_fenced", finish)
    with ThreadPoolExecutor(max_workers=1) as pool:
        other = pool.submit(contender)
        c.runner.execute(c.caller, c.ticket, c.owner)
        assert other.result(timeout=20) is False
    assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.PASSED
    assert _one(c.db, RunAttempt, c.ticket.fence.attempt_id).state == "succeeded"
    assert _one(c.db, FencedWorkItem, c.item).state == State.DONE.value
    assert all(row.state == "final" for row in c.db.all(RunOutput))
