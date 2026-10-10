"""Run the expected-red regression with its Database import bound to this checkout."""
from __future__ import annotations

import sys
from pathlib import Path

expected_source = Path(
    "/workspace/work/actions-mk3-db-savepoint/action_server/src"
).resolve()
from actions.server._database import Database

origin = Path(sys.modules["actions.server._database"].__file__).resolve()
print("python:", sys.executable)
print("database_module:", origin)
print("expected_source:", expected_source)
if not origin.is_relative_to(expected_source):
    raise SystemExit("Database module did not resolve from the isolated evidence checkout")

import pytest

raise SystemExit(
    pytest.main(
        [
            "-q",
            "/workspace/work/actions-mk3-db-savepoint/action_server/tests/action_server_tests/test_database.py::test_nested_transaction_savepoint_start_failure_preserves_error_and_counter",
        ]
    )
)
