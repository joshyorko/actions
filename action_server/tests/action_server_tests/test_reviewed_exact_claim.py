"""Exact approved-target claims use the installed SDK and real host SQL stores."""

from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from actions.work_items import EmptyQueue, State
from actions.work_items._adapters._sql_review import SQLReviewQueue
from actions.work_items._fencing import ClaimRejected

from actions.server.data_queries.review import _SQLStore
from actions.server.data_queries.review_models import FencedWorkItem

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def test_specific_claim_never_leases_an_older_approved_neighbor(database_location):
    refs = _refs()
    with _runtime_database(database_location, refs.workspace, ()) as db:
        queue = SQLReviewQueue(
            _SQLStore(db, str(refs.workspace.root)),
            str(refs.workspace.root),
            "owned-exact",
        )
        first, target = str(uuid4()), str(uuid4())
        queue.seed_input({"result": "older"}, item_id=first)
        queue.seed_input({"result": "selected"}, item_id=target)
        with db.transaction():
            db.update_by_id(FencedWorkItem, first, {"created_ms": "0"})
        owner = str(uuid4())
        selected = queue.reserve_item_fenced(target, owner, lease_seconds=30)
        assert selected.item_id == target and selected.epoch == 1
        assert queue.load_payload(selected.item_id) == {"result": "selected"}
        older = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
        assert older.item_id == first and older.epoch == 1


def test_exact_claim_rejects_live_owner_and_fences_expired_takeover(database_location):
    refs = _refs()
    with _runtime_database(database_location, refs.workspace, ()) as db:
        queue = SQLReviewQueue(
            _SQLStore(db, str(refs.workspace.root)),
            str(refs.workspace.root),
            "owned-takeover",
        )
        target = queue.seed_input({"result": "selected"}, item_id=str(uuid4()))
        old = queue.reserve_item_fenced(target, str(uuid4()), lease_seconds=30)
        with pytest.raises(EmptyQueue):
            queue.reserve_item_fenced(target, str(uuid4()), lease_seconds=30)
        with db.transaction():
            db.update_by_id(FencedWorkItem, target, {"claim_deadline_ms": "0"})
        current = queue.reserve_item_fenced(target, str(uuid4()), lease_seconds=30)
        assert current.epoch == 2 and current.owner_id != old.owner_id
        with pytest.raises(ClaimRejected):
            queue.renew_fenced(old, lease_seconds=30)
        with pytest.raises(ClaimRejected):
            queue.finish_fenced(old, State.DONE)
        queue.finish_fenced(current, State.DONE)
        with pytest.raises(EmptyQueue):
            queue.reserve_item_fenced(target, str(uuid4()), lease_seconds=30)


@pytest.mark.parametrize("blocked", ["cancelled", "other-queue", "missing"])
def test_unclaimable_exact_target_does_not_fall_back_to_neighbor(
    database_location, blocked
):
    refs = _refs()
    with _runtime_database(database_location, refs.workspace, ()) as db:
        workspace = str(refs.workspace.root)
        queue = SQLReviewQueue(_SQLStore(db, workspace), workspace, "owned-scoped")
        neighbor = queue.seed_input({"result": "neighbor"}, item_id=str(uuid4()))
        target = str(uuid4())
        if blocked == "other-queue":
            SQLReviewQueue(_SQLStore(db, workspace), workspace, "other").seed_input(
                {}, item_id=target
            )
        elif blocked == "cancelled":
            queue.seed_input({}, item_id=target)
            assert queue.cancel(target)
        with pytest.raises(EmptyQueue):
            queue.reserve_item_fenced(target, str(uuid4()), lease_seconds=30)
        assert queue.reserve_fenced(str(uuid4()), lease_seconds=30).item_id == neighbor
