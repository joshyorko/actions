"""Keep opt-in real RCC execution in its mandatory dedicated gate."""

import importlib.util
from pathlib import Path


def test_portable_suite_does_not_repeat_the_dedicated_rcc_environment_build():
    script = (
        Path(__file__).parents[2] / "action_server/scripts/verify_invoice_queries.py"
    )
    spec = importlib.util.spec_from_file_location("invoice_gate", script)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    source = {"ACTIONS_ROBOT_INPUT_RCC": "/owned/rcc", "ROBOTS_HOME": "/owned/robots"}
    assert gate.suite_environment("worker", source) == source
    assert gate.suite_environment("portable", source) == {
        "ROBOTS_HOME": "/owned/robots"
    }
    assert source["ACTIONS_ROBOT_INPUT_RCC"] == "/owned/rcc"
