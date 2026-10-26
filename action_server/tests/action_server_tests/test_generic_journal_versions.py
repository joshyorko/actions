"""Retained dispatch and terminal result formats are immutable authority."""
import json

import pytest
from action_server_tests.test_generic_work_item_execution import dispatch
from action_server_tests.test_generic_work_item_execution import (
    generic as _generic_fixture,
)
from action_server_tests.test_generic_work_item_execution import synthetic_completion

from actions.server._models import Run
from actions.server.run_outputs.service import FenceRejected, _canonical, _one, _update

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def generic(database_location, foundry_package_store):
    yield from _generic_fixture.__wrapped__(database_location, foundry_package_store)


@pytest.mark.parametrize("marker", ["missing", "unknown", "wrong_type"])
@pytest.mark.parametrize("phase", ["dispatch", "terminal_outer", "terminal_result"])
def test_retained_journal_version_is_required(generic, marker, phase):
    g = generic()
    ticket, claim = dispatch(g)
    if phase != "dispatch":
        guarded, output, result = synthetic_completion(g, ticket, "hello")
        guarded.publish(g.caller.actor, ticket.fence, [output], result)
    row = _one(g.db, Run, ticket.fence.run_id)
    journal = json.loads(row.result)
    target = journal["result"] if phase == "terminal_result" else journal
    if marker == "missing":
        target.pop("version")
    else:
        target["version"] = True if marker == "wrong_type" else "unknown/v99"
    with g.db.transaction():
        _update(g.db, Run, row.id, {"result": _canonical(journal, 65536)})
    with pytest.raises(FenceRejected, match="version"):
        g.owner.dispatch(g.caller, claim, lease_seconds=60)
