"""Robot carrier limits must reject input before queue or Run admission."""
# ruff: noqa: F811
import json
from pathlib import Path

import pytest
from action_server_tests.test_robot_claimed_work_items_327 import claimed as claimed
from action_server_tests.test_robot_claimed_work_items_327 import (
    disable_feedback as disable_feedback,
)

from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry import generic_work_item_execution
from actions.server.foundry.models import FoundryRequest
from actions.server.foundry.robot_execution_selection import prepare_robot_selection
from actions.server.run_outputs.models import RunAttempt

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def count_admissions(db):
    return {
        model.__name__: len(db.all(model))
        for model in (FencedWorkItem, FoundryRequest, Run, RunAttempt)
    }


def isolated_origin():
    assert (
        Path(generic_work_item_execution.__file__)
        .resolve()
        .is_relative_to(Path(__file__).resolve().parents[2] / "src")
    )


@pytest.mark.parametrize(
    "value",
    ["x" * 70000, "\u20ac" * 12000],
    ids=["ascii-over64k", "utf8-under64k-escaped-over64k"],
)
@pytest.mark.parametrize(
    "standalone", [False, True], ids=["enqueue", "optional-standalone"]
)
def test_oversized_input_rejected_without_admission(claimed, value, standalone):
    isolated_origin()
    c = claimed(
        mode="optional" if standalone else "consumer", with_claim=not standalone
    )
    inputs = {"value": value}
    assert (
        len(json.dumps(inputs, ensure_ascii=False).encode())
        < c.owner.policy.max_input_bytes
        == 262144
    )
    assert (
        len(
            json.dumps(
                inputs, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        )
        > 65536
    )
    before = count_admissions(c.db)
    with pytest.raises(ValueError):
        if standalone:
            c.owner.dispatch_standalone(
                c.caller, inputs, "oversized-input", lease_seconds=60
            )
        else:
            c.owner.enqueue(c.caller, inputs, "oversized-input")
    assert count_admissions(c.db) == before


@pytest.mark.parametrize(
    "standalone", [False, True], ids=["claimed", "optional-standalone"]
)
def test_exact_robot_carrier_boundary_is_admitted_and_prepares(claimed, standalone):
    isolated_origin()
    c = claimed(
        mode="optional" if standalone else "consumer", with_claim=not standalone
    )
    inputs = {"value": "x" * (65536 - len(b'{"value":""}'))}
    expected = json.dumps(
        inputs, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    assert len(expected) == 65536
    if standalone:
        ticket = c.owner.dispatch_standalone(
            c.caller, inputs, "exact-boundary", lease_seconds=60
        )
    else:
        item = c.owner.enqueue(c.caller, inputs, "exact-boundary")
        claim = c.owner.queue(c.owner.policy.input_queue).reserve_item_fenced(
            item, c.caller.worker_id, lease_seconds=60
        )
        ticket = c.owner.dispatch(c.caller, claim, lease_seconds=60)
    prepared = prepare_robot_selection(
        c.owner.base,
        c.owner.registry,
        c.caller.actor,
        ticket.fence,
        require_current=lambda *_: None,
    )
    assert prepared.selection.inputs == expected
