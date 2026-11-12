"""Test-only in-memory guard removal; never changes repository production bytes."""
import pytest
import actions.server.foundry.run_output_transport as factory
from actions.server.run_outputs.transport import RunOutputTransport


def without_identity_guard(outputs, authenticate):
    async def current(request):
        return (await authenticate(request)).actor
    return RunOutputTransport(outputs, current)


if __name__ == "__main__":
    factory.create_run_output_transport = without_identity_guard
    raise SystemExit(pytest.main([
        "-p", "no:robocorp_log_pytest",
        "tests/action_server_tests/test_lane_b_run_output_transport.py::test_app_audience_object_is_not_a_managed_identity",
        "--junitxml=/workspace/lane-b-state/receipts/transport-audience-mutation.xml",
    ]))
