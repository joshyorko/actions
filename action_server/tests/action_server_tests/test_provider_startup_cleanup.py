"""Source-only controls for the retained RCC provider startup pipe reader."""

import importlib.util
import io
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


def _harness():
    path = Path(__file__).parents[2] / "scripts/verify_dakota_rcc_acceptance.py"
    spec = importlib.util.spec_from_file_location("provider_startup_control", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _provider(harness, tmp_path, monkeypatch, code):
    monkeypatch.setattr(
        harness, "_provider_command", lambda *_: [sys.executable, "-c", code]
    )
    return harness.start_provider(
        "/unused/rcc", tmp_path, os.environ.copy(), deadline=harness.Deadline.after(2)
    )


def _dispose(process):
    if process.poll() is None:
        process.kill()
    process.wait(timeout=2)
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            stream.close()


def test_real_provider_retains_original_startup_reader_and_typed_cleanup(
    tmp_path, monkeypatch
):
    harness = _harness()
    process, url = _provider(
        harness,
        tmp_path,
        monkeypatch,
        'import time; print(\'{"url":"http://127.0.0.1:1234"}\',flush=True); time.sleep(60)',
    )
    try:
        owner = process._rcc_provider_owner
        original = owner.reader.thread
        assert isinstance(original, threading.Thread)
        assert url == "http://127.0.0.1:1234"
        result = harness.cleanup_provider_until(process, time.monotonic() + 1)
        assert owner.reader.thread is original
        assert result.complete
        assert result.ownership_confirmed
        assert result.reader.joined and result.reader.alive is False
        assert result.reader.error is None
        assert result.tree.wrapper_reaped and result.tree.descendant_reap_complete
        assert result.pid == process.pid and isinstance(result.create_time, float)
        assert (
            result.to_dict()["scope"]
            == "captured_provider_tree_and_startup_reader_only"
        )
        assert process.poll() is not None
    finally:
        _dispose(process)


def test_blocked_startup_reader_keeps_same_object_until_finite_retry(
    tmp_path, monkeypatch
):
    harness = _harness()
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        owner = harness._capture_provider_ownership(process)
        with pytest.raises(TimeoutError, match="startup timed out"):
            harness._readline_with_timeout(process.stdout, 0.02, owner=owner)
        original = owner.reader.thread
        join_timeouts = []
        actual_join = original.join

        def record_join(timeout):
            join_timeouts.append(timeout)
            actual_join(timeout=timeout)

        with monkeypatch.context() as control:
            control.setattr(original, "join", record_join)
            result = harness.cleanup_provider_until(process, time.monotonic())
        assert join_timeouts == [0.0]
        assert not result.complete
        assert result.reader.alive is True
        assert owner.reader.thread is original
        result = harness.cleanup_provider_until(process, time.monotonic() + 1)
        assert result.complete
        assert owner.reader.thread is original
        assert result.reader.joined and result.reader.alive is False
    finally:
        _dispose(process)


def test_read_error_crosses_real_queue_boundary_with_original_identity():
    harness = _harness()
    error = OSError("private detail must not enter cleanup evidence")

    class BrokenStream:
        def readline(self):
            raise error

    owner = SimpleNamespace(reader=None)
    with pytest.raises(OSError) as caught:
        harness._readline_with_timeout(BrokenStream(), 0.2, owner=owner)
    assert caught.value is error
    owner.reader.thread.join(timeout=0.2)
    assert owner.reader.error == "OSError"
    assert not owner.reader.thread.is_alive()


def test_second_startup_read_is_rejected_without_creating_another_thread():
    harness = _harness()
    owner = SimpleNamespace(reader=None)
    assert (
        harness._readline_with_timeout(io.StringIO("ready\n"), 0.2, owner=owner)
        == "ready\n"
    )
    original = owner.reader.thread
    with pytest.raises(RuntimeError, match="PROVIDER_READER_ALREADY_STARTED"):
        harness._readline_with_timeout(io.StringIO("again\n"), 0.2, owner=owner)
    assert owner.reader.thread is original
    original.join(timeout=0.2)


@pytest.mark.parametrize(
    "poison",
    [
        "missing",
        "wrong_process",
        "wrong_pid",
        "wrong_create_time",
        "missing_reader",
        "wrong_reader_owner",
    ],
)
def test_unknown_provider_owner_or_reader_never_claims_completion(tmp_path, poison):
    harness = _harness()
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        owner = harness._capture_provider_ownership(process)
        harness._readline_with_timeout(io.StringIO("ready\n"), 0.2, owner=owner)
        original = owner.reader
        if poison == "missing":
            del process._rcc_provider_owner
        elif poison == "wrong_process":
            owner.process = object()
        elif poison == "wrong_pid":
            owner.pid += 1
        elif poison == "wrong_create_time":
            owner.create_time += 1
        elif poison == "missing_reader":
            owner.reader = None
        else:
            owner.reader.owner = object()
        result = harness.cleanup_provider_until(process, time.monotonic() + 0.3)
        assert not result.complete
        assert result.errors or result.reader.error
        if poison in ("missing", "wrong_process", "wrong_pid", "wrong_create_time"):
            assert process.poll() is None
            assert not result.ownership_confirmed
        json.dumps(result.to_dict())
        original.thread.join(timeout=0.2)
    finally:
        _dispose(process)


def test_startup_failure_keeps_primary_when_cleanup_observation_fails(
    tmp_path, monkeypatch
):
    harness = _harness()
    captured = []
    actual_capture = harness._capture_provider_ownership

    def capture(process):
        captured.append(process)
        return actual_capture(process)

    monkeypatch.setattr(harness, "_capture_provider_ownership", capture)
    secondary = RuntimeError("cleanup failed")

    def fail_cleanup(*_):
        raise secondary

    monkeypatch.setattr(harness, "cleanup_provider_until", fail_cleanup)
    try:
        with pytest.raises(RuntimeError, match="startup JSON") as caught:
            _provider(harness, tmp_path, monkeypatch, "print('invalid',flush=True)")
        assert caught.value.provider_cleanup_error == "RuntimeError"
        assert caught.value is not secondary
    finally:
        for process in captured:
            _dispose(process)


def test_tree_and_original_reader_share_the_supplied_absolute_deadline(monkeypatch):
    from actions.server._common import process as process_utils

    harness = _harness()
    release = threading.Event()

    class BlockedStream:
        def readline(self):
            assert release.wait(timeout=2)
            return "ready\n"

    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    owner = harness._capture_provider_ownership(process)
    seen = []
    now = [100.0]
    join_timeouts = []

    def bounded_tree(_process, _descendants, deadline, _complete):
        seen.append(deadline)
        now[0] += 0.03
        return process_utils.ProcessTreeCleanupResult(True, (), (), ())

    monkeypatch.setattr(process_utils, "force_kill_process_tree_until", bounded_tree)
    try:
        with pytest.raises(TimeoutError):
            harness._readline_with_timeout(BlockedStream(), 0.01, owner=owner)
        actual_join = owner.reader.thread.join

        def record_join(timeout):
            join_timeouts.append(timeout)
            actual_join(timeout=0)

        monkeypatch.setattr(harness, "time", SimpleNamespace(monotonic=lambda: now[0]))
        monkeypatch.setattr(owner.reader.thread, "join", record_join)
        deadline = 100.05
        result = harness.cleanup_provider_until(process, deadline)
        assert seen == [deadline]
        assert join_timeouts == [pytest.approx(0.02)]
        assert result.reader.alive is True and not result.complete
    finally:
        release.set()
        # The real reader is still owned; the injected join only observes budget.
        threading.Thread.join(owner.reader.thread, timeout=1)
        _dispose(process)


@pytest.mark.parametrize("operation", ["join", "is_alive"])
def test_reader_observation_error_is_fixed_class_and_not_success(
    tmp_path, monkeypatch, operation
):
    harness = _harness()
    process, _ = _provider(
        harness,
        tmp_path,
        monkeypatch,
        'import time; print(\'{"url":"http://127.0.0.1:1234"}\',flush=True); time.sleep(60)',
    )
    original = process._rcc_provider_owner.reader.thread
    original.join(timeout=0.2)

    def fail(*args, **kwargs):
        raise RuntimeError("private observation detail")

    try:
        with monkeypatch.context() as control:
            control.setattr(original, operation, fail)
            result = harness.cleanup_provider_until(process, time.monotonic() + 1)
        assert not result.complete
        assert result.reader.error in (
            "PROVIDER_JOIN_RuntimeError",
            "PROVIDER_ALIVE_RuntimeError",
        )
        assert "private observation detail" not in json.dumps(result.to_dict())
    finally:
        original.join(timeout=0.2)
        _dispose(process)


@pytest.mark.parametrize("deadline", [True, float("nan"), float("inf")])
def test_invalid_deadline_is_rejected_before_process_signalling(deadline):
    harness = _harness()
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        harness._capture_provider_ownership(process)
        with pytest.raises(ValueError, match="PROVIDER_CLEANUP_DEADLINE"):
            harness.cleanup_provider_until(process, deadline)
        assert process.poll() is None
    finally:
        _dispose(process)


@pytest.mark.parametrize(
    "race", ["already_exited", "exits_during_capture", "birth_changes"]
)
def test_root_capture_is_transactional_and_never_forwards_foreign_descendants(
    monkeypatch, race
):
    from actions.server._common import process as process_utils

    harness = _harness()
    lookups = []
    delegated = []
    exited = [race == "already_exited"]
    original = SimpleNamespace(pid=123, poll=lambda: 0 if exited[0] else None)
    child = SimpleNamespace(pid=777, create_time=lambda: 150.0)

    class ProcessError(Exception):
        pass

    class Root:
        def create_time(self):
            return 200.0 if race == "birth_changes" and len(lookups) > 1 else 100.0

        def children(self, recursive):
            assert recursive is True
            if race == "exits_during_capture":
                exited[0] = True
            return [child]

    def lookup(pid):
        lookups.append(pid)
        return Root()

    monkeypatch.setitem(
        sys.modules, "psutil", SimpleNamespace(Process=lookup, Error=ProcessError)
    )

    def forbidden_delegation(*args):
        delegated.append(args)
        return process_utils.ProcessTreeCleanupResult(True, (), (), ())

    monkeypatch.setattr(
        process_utils, "force_kill_process_tree_until", forbidden_delegation
    )
    owner = harness._capture_provider_ownership(original)
    result = harness.cleanup_provider_until(original, time.monotonic() + 1)
    assert not delegated
    assert not owner.snapshot_complete
    assert not owner.descendants
    assert not result.ownership_confirmed and not result.complete
    if race == "already_exited":
        assert not lookups


def test_verified_descendants_remain_owned_after_original_provider_exits(monkeypatch):
    from actions.server._common import process as process_utils

    harness = _harness()
    exited = [False]
    original = SimpleNamespace(pid=123, poll=lambda: 0 if exited[0] else None)
    child = SimpleNamespace(pid=777, create_time=lambda: 150.0)
    lookups = []
    delegated = []

    class ProcessError(Exception):
        pass

    class Root:
        def create_time(self):
            return 100.0

        def children(self, recursive):
            return [child]

    def lookup(pid):
        lookups.append(pid)
        if pid == 123:
            assert exited[0] is False, "exited root must not acquire a fresh PID's tree"
            return Root()
        assert pid == 777
        return child

    monkeypatch.setitem(
        sys.modules, "psutil", SimpleNamespace(Process=lookup, Error=ProcessError)
    )

    def captured_cleanup(process, descendants, deadline, complete):
        delegated.append((process, list(descendants), complete))
        return process_utils.ProcessTreeCleanupResult(True, (), (), ())

    monkeypatch.setattr(
        process_utils, "force_kill_process_tree_until", captured_cleanup
    )
    owner = harness._capture_provider_ownership(original)
    harness._readline_with_timeout(io.StringIO("ready\n"), 0.2, owner=owner)
    owner.reader.thread.join(timeout=0.2)
    exited[0] = True
    result = harness.cleanup_provider_until(original, time.monotonic() + 1)
    assert result.complete
    assert delegated == [(original, [child], True)]


def test_reused_captured_descendant_is_not_delegated_as_original_identity(monkeypatch):
    from actions.server._common import process as process_utils

    harness = _harness()
    original = SimpleNamespace(pid=123, poll=lambda: None)
    child = SimpleNamespace(pid=777, create_time=lambda: 150.0)
    reuse = [False]
    delegated = []

    class ProcessError(Exception):
        pass

    class Root:
        def create_time(self):
            return 100.0

        def children(self, recursive):
            return [child]

    def lookup(pid):
        if pid == 123:
            return Root()
        assert pid == 777
        return SimpleNamespace(create_time=lambda: 250.0 if reuse[0] else 150.0)

    monkeypatch.setitem(
        sys.modules, "psutil", SimpleNamespace(Process=lookup, Error=ProcessError)
    )

    def forbidden_delegation(*args):
        delegated.append(args)
        return process_utils.ProcessTreeCleanupResult(True, (), (), ())

    monkeypatch.setattr(
        process_utils, "force_kill_process_tree_until", forbidden_delegation
    )
    owner = harness._capture_provider_ownership(original)
    harness._readline_with_timeout(io.StringIO("ready\n"), 0.2, owner=owner)
    owner.reader.thread.join(timeout=0.2)
    reuse[0] = True
    result = harness.cleanup_provider_until(original, time.monotonic() + 1)
    assert not delegated
    assert not result.complete
    assert result.errors
