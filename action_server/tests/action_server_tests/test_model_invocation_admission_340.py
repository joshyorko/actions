"""Model publication must be enforced at the existing invocation boundary."""

import pytest

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
