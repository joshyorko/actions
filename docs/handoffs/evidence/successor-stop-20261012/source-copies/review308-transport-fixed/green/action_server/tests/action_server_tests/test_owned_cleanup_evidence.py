"""Injected source controls for opt-in supervisor cleanup metadata only."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def _harness():
    path = Path(__file__).parents[2] / "scripts/verify_dakota_rcc_acceptance.py"
    spec = importlib.util.spec_from_file_location(
        "owned_cleanup_evidence_control", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _process(pid, birth, status="sleeping"):
    return SimpleNamespace(pid=pid, create_time=lambda: birth, status=lambda: status)


def _observer(harness):
    observer = harness._OwnedCleanupObserver()
    observer.root = harness.OwnedIdentity.from_values(1, 1.0)
    observer.root_capture_verified = True
    observer.root_wait_reaped = True
    observer.root_wait_returncode = 0
    return observer


def test_uncapped_identity_rows_preserve_same_pid_different_births():
    harness = _harness()
    observer = _observer(harness)
    captured = [
        _process(pid, float(birth)) for pid in range(2, 82) for birth in (10, 20)
    ]
    observer.capture_snapshot(captured)
    evidence = observer.freeze()
    assert len(evidence.census) == 160
    assert len({row.identity for row in evidence.census}) == 160
    assert not evidence.census_reap_complete
    restored = harness.OwnedCleanupEvidence.from_dict(
        json.loads(json.dumps(evidence.to_dict()))
    )
    assert restored == evidence
    assert len(restored.census) > 64


def test_empty_enumeration_and_failed_enumeration_are_distinct():
    harness = _harness()
    success = _observer(harness)
    success.capture_snapshot([])
    failed = _observer(harness)
    failed.record_enumeration_error(OSError("private enumeration detail"))
    assert success.freeze().enumeration_succeeded is True
    assert failed.freeze().enumeration_succeeded is False
    assert failed.freeze().enumeration_errors == ("OSError",)
    assert not success.freeze().census_reap_complete
    assert not failed.freeze().census_reap_complete
    assert "private enumeration detail" not in json.dumps(failed.freeze().to_dict())


def test_unknown_and_reused_observations_are_never_signal_targets():
    harness = _harness()
    observer = _observer(harness)
    observer.capture_snapshot([_process(2, 10.0), _process(3, 10.0)])

    class Missing(Exception):
        pass

    class Error(Exception):
        pass

    def lookup(pid):
        if pid == 2:
            return _process(pid, 20.0)
        raise Error("private lookup detail")

    observer.observe_final(lookup, missing_error=Missing, observed_at=4.0)
    rows = observer.freeze().census
    assert [row.state for row in rows] == ["reused", "unknown"]
    assert rows[1].error == "Error"
    assert not observer.freeze().census_reap_complete
    assert "private lookup detail" not in json.dumps(observer.freeze().to_dict())


@pytest.mark.parametrize(
    "pid,birth", [(True, 1), (0, 1), (1, True), (1, float("nan")), (1, float("inf"))]
)
def test_invalid_identity_is_rejected_without_normalizing_unknown(pid, birth):
    harness = _harness()
    with pytest.raises(ValueError):
        harness.OwnedIdentity.from_values(pid, birth)


@pytest.mark.parametrize("kind", ["result", "timeout", "cleanup_error"])
def test_attachment_preserves_primary_object_and_legacy_outputs(kind):
    harness = _harness()
    evidence = _observer(harness).freeze()
    if kind == "result":
        original = subprocess.CompletedProcess(["command"], 7, "stdout", "stderr")
    elif kind == "timeout":
        original = subprocess.TimeoutExpired(
            ["command"], 1, output=b"stdout", stderr=b"stderr"
        )
    else:
        original = harness.ProcessTreeCleanupError(
            "primary",
            command_returncode=7,
            command_stdout="stdout",
            command_stderr="stderr",
        )
    before = dict(vars(original))
    assert harness._attach_cleanup_evidence(original, evidence) is original
    assert original.cleanup_evidence is evidence
    for name, value in before.items():
        assert getattr(original, name) is value


def _transport(monkeypatch, harness, payload):
    calls = []

    class Supervisor:
        returncode = 0

        def communicate(self, request, timeout):
            calls.append((json.loads(request), timeout))
            return json.dumps(payload), "supervisor-stderr"

    monkeypatch.setattr(
        harness,
        "subprocess",
        SimpleNamespace(
            **{**vars(subprocess), "Popen": lambda *_args, **_kwargs: Supervisor()}
        ),
    )
    monkeypatch.setattr(
        harness, "sys", SimpleNamespace(**{**vars(sys), "platform": "linux"})
    )
    return calls


def _wire_result(evidence):
    return {
        "returncode": 7,
        "stdout": "command-stdout",
        "stderr": "command-stderr",
        "cleanup_disposition": "clean_no_descendants",
        "reaped_descendants": 0,
        "unexpected_live_descendants": False,
        "timed_out": False,
        "cleanup_evidence": evidence.to_dict(),
    }


@pytest.mark.parametrize(
    "kind", ["result", "timeout", "cleanup_error", "malformed_evidence"]
)
def test_existing_result_transport_attaches_actual_metadata(monkeypatch, kind):
    harness = _harness()
    evidence = _observer(harness).freeze()
    payload = _wire_result(evidence)
    if kind == "timeout":
        payload["timed_out"] = True
    elif kind == "cleanup_error":
        payload["unexpected_live_descendants"] = True
    elif kind == "malformed_evidence":
        payload["cleanup_evidence"]["root"] = {"pid": 1, "create_time": float("nan")}
    calls = _transport(monkeypatch, harness, payload)
    try:
        outcome = harness.run_owned_process(
            ["command"], timeout_seconds=1, env={}, collect_cleanup_evidence=True
        )
    except (subprocess.TimeoutExpired, harness.ProcessTreeCleanupError) as error:
        outcome = error
    assert calls[0][0]["collect_cleanup_evidence"] is True
    if kind == "malformed_evidence":
        assert outcome.cleanup_evidence.root is None
        assert outcome.cleanup_evidence.enumeration_succeeded is None
        assert outcome.cleanup_evidence.observation_errors == ("ValueError",)
    else:
        assert outcome.cleanup_evidence == evidence
    if kind in ("result", "malformed_evidence"):
        assert outcome.returncode == 7
        assert (outcome.stdout, outcome.stderr) == ("command-stdout", "command-stderr")
    elif kind == "timeout":
        assert (outcome.output, outcome.stderr) == ("command-stdout", "command-stderr")
    else:
        assert (outcome.command_stdout, outcome.command_stderr) == (
            "command-stdout",
            "command-stderr",
        )


def test_default_transport_neither_requests_nor_attaches_metadata(monkeypatch):
    harness = _harness()
    payload = {
        "returncode": 0,
        "stdout": "out",
        "stderr": "err",
        "cleanup_disposition": "clean_no_descendants",
        "reaped_descendants": 0,
        "unexpected_live_descendants": False,
        "timed_out": False,
    }
    calls = _transport(monkeypatch, harness, payload)
    result = harness.run_owned_process(["command"], timeout_seconds=1, env={})
    assert "collect_cleanup_evidence" not in calls[0][0]
    assert not hasattr(result, "cleanup_evidence")
    assert (result.stdout, result.stderr) == ("out", "err")


def test_existing_wait_events_and_echild_are_observations_not_invented_reaps(
    monkeypatch,
):
    harness = _harness()
    observer = _observer(harness)
    observer.capture_snapshot([_process(2, 10.0), _process(3, 10.0), _process(3, 20.0)])
    waits = iter([(2, 512), (3, 0), ChildProcessError()])

    def waitpid(*_):
        value = next(waits)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(
        harness, "os", SimpleNamespace(**{**vars(harness.os), "waitpid": waitpid})
    )
    monkeypatch.setattr(harness, "time", SimpleNamespace(monotonic=lambda: 12.0))
    assert (
        harness._reap_adopted_children(deadline=15.0, evidence_observer=observer) == 2
    )
    evidence = observer.freeze()
    assert evidence.terminal_echild is True
    assert [(event.pid, event.raw_wait_status) for event in evidence.reap_events] == [
        (2, 512),
        (3, 0),
    ]
    assert evidence.reap_events[0].matched_identity is None
    assert evidence.reap_events[1].matched_identity is None
    assert evidence.deadline_facts[0].remaining == 3.0
    assert not evidence.census_reap_complete


def test_wait_timeout_keeps_primary_cleanup_error_and_unavailable_echild(monkeypatch):
    harness = _harness()
    observer = _observer(harness)
    monkeypatch.setattr(
        harness,
        "os",
        SimpleNamespace(**{**vars(harness.os), "waitpid": lambda *_: (0, 0)}),
    )
    monkeypatch.setattr(harness, "time", SimpleNamespace(monotonic=lambda: 12.0))
    with pytest.raises(harness.ProcessTreeCleanupError) as caught:
        harness._reap_adopted_children(deadline=11.0, evidence_observer=observer)
    assert caught.value.cleanup_evidence.terminal_echild is False
    assert caught.value.cleanup_evidence.deadline_facts[0].remaining == 0.0
    assert not caught.value.cleanup_evidence.census_reap_complete


def test_wait_pid_alone_cannot_match_a_stale_singleton_birth_capture():
    harness = _harness()
    observer = _observer(harness)
    observer.capture_snapshot([_process(2, 10.0)])
    # Another owner could have reaped birth10 before a new birth reused PID2.
    # waitpid reports PID/status, not the birth of the process just reaped.
    observer.record_reap(2, 0)
    assert observer.freeze().reap_events[0].matched_identity is None


@pytest.mark.parametrize("opt_in", [False, True])
def test_actual_supervisor_wires_observer_only_when_requested(
    tmp_path, monkeypatch, capsys, opt_in
):
    import io

    harness = _harness()
    polls = []
    waits = []
    lookups = []

    class ProcessError(Exception):
        pass

    class Missing(ProcessError):
        pass

    class Child:
        pid = 1
        returncode = None

        def __init__(self, *_args, **kwargs):
            kwargs["stdout"].write(b"command-out")
            kwargs["stderr"].write(b"command-err")

        def poll(self):
            polls.append(True)
            if len(polls) > (2 if opt_in else 0):
                self.returncode = 0
            return self.returncode

        def wait(self, timeout=None):
            waits.append(timeout)
            assert self.returncode == 0
            return self.returncode

    child = Child.__new__(Child)

    def create_child(*args, **kwargs):
        child.__init__(*args, **kwargs)
        return child

    class Process:
        def create_time(self):
            return 1.0

        def children(self, recursive=True):
            return []

    def lookup(pid):
        lookups.append(pid)
        if pid == 1 and child.returncode is not None:
            raise Missing()
        return Process()

    class Scratch:
        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, *_args):
            pass

    request = {
        "command": ["unused"],
        "cwd": None,
        "env": {},
        "timeout_seconds": 1,
        "cleanup_grace_seconds": 1,
    }
    if opt_in:
        request["collect_cleanup_evidence"] = True
    monkeypatch.setattr(
        harness,
        "sys",
        SimpleNamespace(
            **{
                **vars(sys),
                "platform": "linux",
                "stdin": io.StringIO(json.dumps(request)),
            }
        ),
    )
    monkeypatch.setattr(
        harness,
        "ctypes",
        SimpleNamespace(
            CDLL=lambda *_args, **_kwargs: SimpleNamespace(prctl=lambda *_: 0)
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "psutil",
        SimpleNamespace(
            Process=lookup,
            Error=ProcessError,
            NoSuchProcess=Missing,
            STATUS_ZOMBIE="zombie",
        ),
    )
    monkeypatch.setattr(
        harness,
        "subprocess",
        SimpleNamespace(**{**vars(subprocess), "Popen": create_child}),
    )
    monkeypatch.setattr(
        harness,
        "tempfile",
        SimpleNamespace(TemporaryDirectory=lambda **_kwargs: Scratch()),
    )

    def echild(*_):
        raise ChildProcessError()

    monkeypatch.setattr(
        harness, "os", SimpleNamespace(**{**vars(harness.os), "waitpid": echild})
    )
    monkeypatch.setattr(harness, "time", SimpleNamespace(monotonic=lambda: 12.0))
    assert harness._supervisor_main() == 0
    output = json.loads(capsys.readouterr().out)
    assert (output["stdout"], output["stderr"], output["returncode"]) == (
        "command-out",
        "command-err",
        0,
    )
    assert waits == [None]
    if opt_in:
        evidence = harness.OwnedCleanupEvidence.from_dict(output["cleanup_evidence"])
        assert evidence.root == harness.OwnedIdentity(1, 1.0)
        assert evidence.root_capture_verified and evidence.root_wait_reaped
        assert evidence.terminal_echild is True
        assert evidence.census_reap_complete
        assert (
            evidence.readers
            is evidence.sampler
            is evidence.whole_operation_enforcer
            is None
        )
    else:
        assert "cleanup_evidence" not in output
        assert 1 not in lookups


def test_raw_wait_error_retains_original_exception_identity(monkeypatch):
    harness = _harness()
    observer = _observer(harness)
    original = OSError("private wait detail")

    def fail(*_):
        raise original

    monkeypatch.setattr(
        harness, "os", SimpleNamespace(**{**vars(harness.os), "waitpid": fail})
    )
    monkeypatch.setattr(harness, "time", SimpleNamespace(monotonic=lambda: 12.0))
    with pytest.raises(OSError) as caught:
        harness._reap_adopted_children(deadline=15.0, evidence_observer=observer)
    assert caught.value is original
    assert original.cleanup_evidence.observation_errors == ("OSError",)
    assert original.cleanup_evidence.terminal_echild is None
    assert "private wait detail" not in json.dumps(original.cleanup_evidence.to_dict())


@pytest.mark.parametrize(
    "field,value",
    [
        ("root_wait_returncode", None),
        ("root_wait_returncode", True),
        ("readers", []),
        ("schema_version", True),
        ("observation_errors", ["private error detail"]),
    ],
)
def test_serialized_poison_becomes_unavailable_and_preserves_result(
    monkeypatch, field, value
):
    harness = _harness()
    payload = _wire_result(_observer(harness).freeze())
    payload["cleanup_evidence"][field] = value
    _transport(monkeypatch, harness, payload)
    result = harness.run_owned_process(
        ["command"], timeout_seconds=1, env={}, collect_cleanup_evidence=True
    )
    assert result.returncode == 7
    assert (result.stdout, result.stderr) == ("command-stdout", "command-stderr")
    assert result.cleanup_evidence.root is None
    assert result.cleanup_evidence.enumeration_succeeded is None
    assert result.cleanup_evidence.observation_errors == ("ValueError",)
    assert not result.cleanup_evidence.census_reap_complete


def test_rejected_metadata_attachment_does_not_replace_wait_primary(monkeypatch):
    harness = _harness()
    observer = _observer(harness)

    class WaitError(OSError):
        def __setattr__(self, name, value):
            if name == "cleanup_evidence":
                raise RuntimeError("private attachment detail")
            return super().__setattr__(name, value)

    original = WaitError("primary")

    def fail(*_):
        raise original

    monkeypatch.setattr(
        harness, "os", SimpleNamespace(**{**vars(harness.os), "waitpid": fail})
    )
    monkeypatch.setattr(harness, "time", SimpleNamespace(monotonic=lambda: 12.0))
    with pytest.raises(WaitError) as caught:
        harness._reap_adopted_children(deadline=15.0, evidence_observer=observer)
    assert caught.value is original
    assert observer.observation_errors == ["WaitError", "RuntimeError"]


def test_failed_observer_serialization_does_not_replace_legacy_result(monkeypatch):
    harness = _harness()
    observer = _observer(harness)

    def fail():
        raise OSError("private serialization detail")

    monkeypatch.setattr(observer, "freeze", fail)
    original = subprocess.CompletedProcess(["command"], 7, "out", "err")
    assert harness._attach_observed_cleanup(original, observer) is original
    assert original.cleanup_evidence.observation_errors == ("OSError",)
    assert original.cleanup_evidence.root is None
    assert (original.stdout, original.stderr) == ("out", "err")


def test_genuine_supervisor_failure_has_explicitly_unavailable_metadata(monkeypatch):
    harness = _harness()

    class Supervisor:
        returncode = 2

        def communicate(self, request, timeout):
            return "not-a-success-report", "original supervisor failure"

    monkeypatch.setattr(
        harness,
        "subprocess",
        SimpleNamespace(
            **{**vars(subprocess), "Popen": lambda *_args, **_kwargs: Supervisor()}
        ),
    )
    monkeypatch.setattr(
        harness, "sys", SimpleNamespace(**{**vars(sys), "platform": "linux"})
    )
    with pytest.raises(
        harness.ProcessTreeCleanupError, match="original supervisor failure"
    ) as caught:
        harness.run_owned_process(
            ["command"], timeout_seconds=1, env={}, collect_cleanup_evidence=True
        )
    evidence = caught.value.cleanup_evidence
    assert (
        evidence.root
        is evidence.enumeration_succeeded
        is evidence.terminal_echild
        is None
    )
    assert evidence.observation_errors == ("SupervisorFailure",)
    assert not evidence.census_reap_complete


def _absent_child_evidence(harness):
    observer = _observer(harness)
    observer.capture_snapshot([_process(1, 1.0), _process(2, 10.0)])

    class Missing(Exception):
        pass

    def absent(_pid):
        raise Missing()

    observer.observe_final(absent, missing_error=Missing, observed_at=20.0)
    observer.terminal_echild = True
    return observer.freeze()


@pytest.mark.parametrize("wait_pid", [2, 999])
def test_schema1_rejects_every_unwitnessed_wait_birth_assertion(monkeypatch, wait_pid):
    harness = _harness()
    evidence = _absent_child_evidence(harness)
    wire = evidence.to_dict()
    wire["reap_events"] = [
        {
            "pid": wait_pid,
            "raw_wait_status": 0,
            "observed_at": 20.0,
            "matched_identity": {"pid": 2, "create_time": 10.0},
        }
    ]
    with pytest.raises(ValueError, match="unwitnessed"):
        harness.OwnedCleanupEvidence.from_dict(wire)
    payload = _wire_result(evidence)
    payload["cleanup_evidence"] = wire
    _transport(monkeypatch, harness, payload)
    outcome = harness.run_owned_process(
        ["command"], timeout_seconds=1, env={}, collect_cleanup_evidence=True
    )
    assert outcome.returncode == 7
    assert (outcome.stdout, outcome.stderr) == ("command-stdout", "command-stderr")
    assert not outcome.cleanup_evidence.census_reap_complete
    assert outcome.cleanup_evidence.observation_errors == ("ValueError",)


@pytest.mark.parametrize("observed_pid", [None, 999])
def test_known_census_identity_requires_matching_observed_pid(observed_pid):
    harness = _harness()
    wire = _absent_child_evidence(harness).to_dict()
    wire["census"][1]["observed_pid"] = observed_pid
    with pytest.raises(ValueError, match="PID identity"):
        harness.OwnedCleanupEvidence.from_dict(wire)


def test_disappearance_after_birth_read_preserves_absent_census_without_reap():
    harness = _harness()
    observer = _observer(harness)
    observer.capture_snapshot([_process(1, 1.0), _process(2, 10.0)])

    class Missing(Exception):
        pass

    class Disappearing:
        def __init__(self, birth):
            self.birth = birth

        def create_time(self):
            return self.birth

        def status(self):
            raise Missing()

    observer.observe_final(
        lambda pid: Disappearing(1.0 if pid == 1 else 10.0),
        missing_error=Missing,
        observed_at=20.0,
    )
    observer.terminal_echild = True
    evidence = observer.freeze()
    assert all(
        row.state == "absent" and row.current_create_time is None
        for row in evidence.census
    )
    restored = harness.OwnedCleanupEvidence.from_dict(evidence.to_dict())
    assert restored == evidence
    assert len(restored.census) == 2
    assert not restored.census_reap_complete
    assert restored.reap_events == ()
    assert restored.observation_errors == ()


def test_schema1_in_memory_poison_cannot_claim_scoped_reaping():
    harness = _harness()
    evidence = _absent_child_evidence(harness)
    forged = evidence._replace(
        reap_events=(
            harness.OwnedReapEvent(999, 0, 20.0, harness.OwnedIdentity(2, 10.0)),
        )
    )
    assert not forged.census_reap_complete
