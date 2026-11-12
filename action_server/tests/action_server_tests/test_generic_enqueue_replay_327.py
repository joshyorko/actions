"""Public generic enqueue marker comes from the atomic domain request owner."""
import pytest
from action_server_tests import test_generic_managed_service as domain

from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.models import FoundryAudit, FoundryRequest

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def generic(database_location, foundry_package_store):
    yield from domain.generic.__wrapped__(database_location, foundry_package_store)


def test_enqueue_public_first_then_replay_preserves_one_atomic_receipt(generic):
    g = generic()
    command = domain.enqueue(g, "public-marker")
    first = domain.service(g).call(g.caller, command)
    replay = domain.service(g).call(g.caller, command)
    assert first["replay"] is False
    assert replay["replay"] is True
    assert first["item"] == replay["item"]
    assert set(first) == set(replay)
    assert first["server_time_ms"].isdigit() and replay["server_time_ms"].isdigit()
    assert (
        g.owner.enqueue(g.caller, command.payload, command.idempotency_key)
        == first["item"]["id"]
    )
    assert len(g.db.all(FencedWorkItem)) == 1
    for model in (FoundryRequest, FoundryAudit):
        assert (
            len(
                [
                    r
                    for r in g.db.all(model)
                    if r.operation == "generic-work-items.enqueue"
                ]
            )
            == 1
        )
