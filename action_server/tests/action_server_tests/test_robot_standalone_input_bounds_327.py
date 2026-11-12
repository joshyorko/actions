"""Robot input byte limits must reject before standalone admission writes."""
# Imported fixtures are injected by pytest.
# ruff: noqa: F811
import json

import pytest
from action_server_tests.test_robot_runtime_runner import admitted as admitted
from action_server_tests.test_robot_runtime_runner import case as case
from action_server_tests.test_robot_runtime_runner import (
    disable_feedback as disable_feedback,
)

from actions.server._models import Run
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import AccessDenied, FenceRejected

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def payload(kind):
    value = {"value": "a" * 65536 if kind == "ascii" else "\u00e9" * 12000}
    escaped = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    utf8 = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    assert len(escaped) > 65536
    if kind == "unicode":
        assert len(utf8) < 65536
    return value, len(utf8), len(escaped)


@pytest.mark.parametrize("kind", ["ascii", "unicode"])
def test_standalone_robot_input_bound_precedes_admission(case, monkeypatch, kind):
    c = case
    value, utf8_bytes, escaped_bytes = payload(kind)
    before = {model: len(c.db.all(model)) for model in (Run, RunPin, RunAttempt)}
    calls = []
    original = c.service.base.admit

    def admit(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(c.service.base, "admit", admit)
    rejected = False
    try:
        c.service.dispatch_standalone(c.caller, value, "pre-admission-bound-" + kind)
    except (ValueError, AccessDenied, FenceRejected):
        rejected = True
    deltas = {
        model.__name__: len(c.db.all(model)) - count for model, count in before.items()
    }
    observed = {"rejected": rejected, "base_admit_calls": len(calls), **deltas}
    assert observed == {
        "rejected": True,
        "base_admit_calls": 0,
        "Run": 0,
        "RunPin": 0,
        "RunAttempt": 0,
    }, {
        "observed": observed,
        "utf8_bytes": utf8_bytes,
        "robot_escaped_bytes": escaped_bytes,
    }
