# Imported pytest fixture names are intentionally used as test parameters.
# ruff: noqa: F811
"""Fresh-connection terminal Robot receipt contracts; SQLite and synthetic adapter."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest
from action_server_tests.test_robot_claimed_work_items_327 import claimed as claimed
from action_server_tests.test_robot_claimed_work_items_327 import (
    disable_feedback as disable_feedback,
)
from action_server_tests.test_robot_runtime_runner import SyntheticAdapter
from actions.work_items import State

from actions.server._database import Database
from actions.server._models import Run, get_all_model_classes
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.robot_receipts import validate_robot_record
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputService,
    _one,
    _update,
)
from actions.server.run_outputs.types import Actor, OutputRef

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def validate_fresh(c, location, *, allow_expired=False):
    """Reopen persisted SQL, authorize metadata read, and validate exact receipt."""
    db = Database(location)
    with db.connect():
        db.initialize(get_all_model_classes())
        outputs = RunOutputService(
            db, c.owner.base.providers, capabilities=c.owner.registry
        )
        outputs._authorize(c.caller.actor, c.owner.snapshot, "read")
        run = _one(db, Run, c.ticket.fence.run_id)
        outer = json.loads(run.result)
        validate_robot_record(
            db,
            None,
            c.owner.snapshot,
            run,
            c.ticket.fence,
            outer["result"],
            claim=c.ticket.claim.model_dump() if c.ticket.claim else None,
            terminal=True,
            outputs=outer["outputs"],
            _allow_expired_terminal=allow_expired,
        )
        return outer


@pytest.mark.parametrize("with_claim", [True, False])
@pytest.mark.parametrize("failed", [False, True])
def test_reopened_claimed_and_optional_terminal(
    claimed, database_location, with_claim, failed
):
    c = claimed(
        mode="optional" if not with_claim else "consumer", with_claim=with_claim
    )

    class Adapter(SyntheticAdapter):
        def execute(self, *args, **kwargs):
            result = super().execute(*args, **kwargs)
            return replace(result, status="FAIL", return_code=1) if failed else result

    replace(c.runner, adapter_factory=Adapter).execute(c.caller, c.ticket, c.owner)
    if with_claim:
        # Terminal provenance does not borrow the completed input's old lease.
        with c.db.transaction():
            _update(c.db, FencedWorkItem, c.item, {"claim_deadline_ms": "1"})
    record = validate_fresh(c, database_location)["result"]
    assert record["status"] == ("FAIL" if failed else "PASS")
    assert record["mode"] == ("work-items" if with_claim else "standalone")
    assert record["claim"] == (c.ticket.claim.model_dump() if with_claim else None)


@pytest.mark.parametrize("change", ["epoch", "queue", "payload", "state", "owner"])
def test_reopened_terminal_rejects_item_corruption(claimed, database_location, change):
    c = claimed()
    c.runner.execute(c.caller, c.ticket, c.owner)
    validate_fresh(c, database_location)
    row = _one(c.db, FencedWorkItem, c.item)
    values = {
        "epoch": {"claim_epoch": row.claim_epoch + 1},
        "queue": {"queue_name": "other-queue"},
        "payload": {
            "payload": json.dumps(
                {**json.loads(row.payload), "inputs": {"value": "changed"}}
            )
        },
        "state": {"state": State.FAILED.value},
        "owner": {"claim_owner": str(uuid4())},
    }
    with c.db.transaction():
        _update(c.db, FencedWorkItem, c.item, values[change])
    with pytest.raises(FenceRejected):
        validate_fresh(c, database_location)


def test_expired_metadata_ack_does_not_grant_output_read(claimed, database_location):
    c = claimed()
    c.runner.execute(c.caller, c.ticket, c.owner)
    outer = validate_fresh(c, database_location)
    ref = OutputRef.model_validate(outer["result"]["outputs"][0]["ref"])
    # Knowing a valid terminal receipt/handle does not authorize a different reader.
    outsider = Actor(principal_id=str(uuid4()))
    with pytest.raises(AccessDenied):
        with c.owner.base.resolve(outsider, ref.workspace_id, ref.handle):
            pytest.fail("Receipt possession granted output read")
    with c.db.transaction():
        _update(c.db, RunOutput, ref.output_id, {"expires_ms": "1"})
    with pytest.raises(FenceRejected):
        validate_fresh(c, database_location)
    validate_fresh(c, database_location, allow_expired=True)
    with pytest.raises((AccessDenied, FenceRejected)):
        with c.owner.base.resolve(c.caller.actor, ref.workspace_id, ref.handle):
            pytest.fail("Expired metadata acknowledgement granted output read")
