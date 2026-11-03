"""Model publication must be enforced at the existing invocation boundary."""

import pytest
from pydantic import ValidationError

from action_server_tests.test_generic_execution_port import (
    generic,
    invoke,
    standalone,
    wrapper,
)
from actions.server._models import Run
from actions.server.deployments.foundry_values import AccessDenied

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def test_unpublished_generic_capability_is_denied_before_run_admission(generic):
    world = generic("optional")
    port, caller, runner, _ = wrapper(world)
    before = list(world.db.all(Run))
    with pytest.raises(AccessDenied):
        invoke(port, caller, standalone(world))
    assert world.db.all(Run) == before
    assert runner.calls == 0


def test_published_headless_capability_has_a_discovery_operation(generic):
    world = generic("optional", model_publication=True)
    port, caller, runner, _ = wrapper(world)
    reply = invoke(port, caller, {}, name="capability_discover")
    assert reply.model_result["descriptors"][0]["snapshot"] == world.owner.snapshot.model_dump(mode="json")
    assert reply.model_result["readiness"] == "not-checked"
    assert runner.calls == 0
    assert world.db.all(Run) == []

    for invalid in ({"limit": 0}, {"limit": True}, {"extra": "not allowed"}):
        with pytest.raises(ValidationError):
            invoke(port, caller, invalid, name="capability_discover")
    assert world.db.all(Run) == []
