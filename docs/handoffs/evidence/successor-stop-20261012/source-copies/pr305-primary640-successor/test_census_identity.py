"""Source-only controls; no process launch, old grant, or RCC execution."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


def load_owner():
    path = Path(os.environ["CENSUS_OWNER_SOURCE"])
    spec = importlib.util.spec_from_file_location("bound_owner_source", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "current_birth,current_status,expected",
    [(20.0, "running", "reused"), (10.0, "zombie", "zombie"), (10.0, "running", "live")],
)
def test_census_uses_fresh_pid_identity_before_cached_liveness(
    current_birth, current_status, expected
):
    owner = load_owner()
    cached = SimpleNamespace(
        pid=4242,
        create_time=lambda: 10.0,
        is_running=lambda: False,
        status=lambda: "running",
    )
    current = SimpleNamespace(
        pid=4242,
        create_time=lambda: current_birth,
        status=lambda: current_status,
    )
    self_process = SimpleNamespace(children=lambda recursive: [])
    api = SimpleNamespace(
        Process=lambda pid: self_process if pid == os.getpid() else current,
        NoSuchProcess=ProcessLookupError,
        STATUS_ZOMBIE="zombie",
    )
    result = owner.census(api, {(4242, 10.0): cached})
    assert result[expected] == [{"pid": 4242, "create_time": 10.0}]
    assert result["absent"] == []


def test_census_uninspectable_current_identity_remains_unknown():
    owner = load_owner()
    cached = SimpleNamespace(pid=4242, is_running=lambda: False)

    def process(pid):
        if pid == os.getpid():
            return SimpleNamespace(children=lambda recursive: [])
        raise PermissionError("synthetic inaccessible identity")

    api = SimpleNamespace(Process=process, NoSuchProcess=ProcessLookupError)
    result = owner.census(api, {(4242, 10.0): cached})
    assert result["absent"] == []
    assert result["unknown"] == [
        {"pid": 4242, "create_time": 10.0, "error_type": "PermissionError"}
    ]


def test_census_current_pid_absence_is_not_pid_reuse():
    owner = load_owner()
    cached = SimpleNamespace(pid=4242, create_time=lambda: 10.0)

    def process(pid):
        if pid == os.getpid():
            return SimpleNamespace(children=lambda recursive: [])
        raise ProcessLookupError(pid)

    api = SimpleNamespace(Process=process, NoSuchProcess=ProcessLookupError)
    result = owner.census(api, {(4242, 10.0): cached})
    assert result["absent"] == [{"pid": 4242, "create_time": 10.0}]
    assert result["reused"] == []
    assert result["unknown"] == []


def test_census_enumeration_failure_is_not_a_complete_empty_snapshot():
    owner = load_owner()

    def fail_enumeration(*, recursive):
        assert recursive is True
        raise PermissionError("synthetic child enumeration failure")

    api = SimpleNamespace(
        Process=lambda _pid: SimpleNamespace(children=fail_enumeration),
        NoSuchProcess=ProcessLookupError,
    )
    result = owner.census(api, {})
    assert result["snapshot_complete"] is False
    assert result["errors"] == [{"stage": "enumeration", "type": "PermissionError"}]


@pytest.mark.parametrize("failure", ["reused", "denied"])
def test_signal_owned_fails_closed_on_reused_or_denied_identity(failure):
    owner = load_owner()
    signals = []
    cached = SimpleNamespace(
        pid=4242,
        create_time=lambda: 10.0,
        send_signal=lambda sig: signals.append(sig),
    )
    self_process = SimpleNamespace(children=lambda recursive: [])

    def process(pid):
        if pid == os.getpid():
            return self_process
        if failure == "denied":
            raise PermissionError("synthetic inaccessible identity")
        return SimpleNamespace(create_time=lambda: 20.0, status=lambda: "running")

    api = SimpleNamespace(
        Process=process,
        NoSuchProcess=ProcessLookupError,
        STATUS_ZOMBIE="zombie",
    )
    with pytest.raises(owner.BoundaryFailure, match="SIGNAL_OWNERSHIP_UNRESOLVED"):
        owner.signal_owned(api, {(4242, 10.0): cached}, 15)
    assert signals == []
