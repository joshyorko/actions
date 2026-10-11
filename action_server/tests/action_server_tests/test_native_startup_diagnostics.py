import json
import subprocess
import threading
from asyncio import CancelledError

import pytest
from action_server_tests import native_startup_diagnostics as diagnostics


@pytest.mark.parametrize("failure_type", [TimeoutError, CancelledError])
def test_failure_keeps_exception_and_observes_before_cleanup(failure_type):
    sampled = threading.Event()
    cleaned = threading.Event()
    failure = failure_type("original startup failure")
    reports = []
    calls = []

    def snapshot(server):
        assert not cleaned.is_set()
        return {"pending": True}

    def publish(report):
        reports.append(report)
        if "snapshot" in report:
            sampled.set()

    def start(server, **kwargs):
        calls.append(kwargs)
        assert sampled.wait(2), "observer did not sample pending startup"
        cleaned.set()  # the original starter owns cleanup
        raise failure

    with pytest.raises(failure_type) as caught:
        diagnostics.observe_start(
            start,
            object(),
            snapshot=snapshot,
            publish=publish,
            offsets=(0, 60),
            timeout=90,
            actions_sync=True,
        )
    assert caught.value is failure
    assert calls == [{"timeout": 90, "actions_sync": True}]
    assert reports[0]["snapshot"] == {"pending": True}
    assert reports[-1]["outcome"] == "failed"
    assert reports[-1]["exception"] == failure_type.__name__
    assert reports[-1]["sampler_cancelled"] is True


def test_ready_start_cancels_future_samples():
    reports = []
    result = object()

    def snapshot(server):
        pytest.fail("successful startup should cancel future samples")

    assert (
        diagnostics.observe_start(
            lambda server, **kwargs: result,
            object(),
            snapshot=snapshot,
            publish=reports.append,
            offsets=(60, 80),
            timeout=90,
        )
        is result
    )
    assert reports == [
        {
            "outcome": "ready",
            "exception": None,
            "sampler_cancelled": True,
            "sampler_alive": False,
        }
    ]


def test_observation_failure_does_not_replace_startup_failure():
    sampled = threading.Event()
    failure = TimeoutError("do not mask me")
    reports = []

    def snapshot(server):
        raise ValueError("secret https://private/path?token=poison")

    def publish(report):
        reports.append(report)
        if "observation" in report:
            sampled.set()

    def start(server, **kwargs):
        assert sampled.wait(2)
        raise failure

    with pytest.raises(TimeoutError) as caught:
        diagnostics.observe_start(
            start,
            object(),
            snapshot=snapshot,
            publish=publish,
            offsets=(0,),
            timeout=90,
        )
    assert caught.value is failure
    assert "poison" not in json.dumps(reports)
    assert reports[0]["observation"] == "unavailable"


@pytest.mark.parametrize("nodeid", sorted(diagnostics.NODES))
def test_explicit_gate_only_enables_selected_windows_native_nodes(nodeid):
    environ = {
        "ACTIONS_NATIVE_STARTUP_DIAGNOSTICS_DIR": "private/path",
        "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE": "native.exe",
    }
    assert diagnostics.enabled(nodeid, "win32", environ)
    assert diagnostics.enabled("tests/" + nodeid, "win32", environ)
    assert not diagnostics.enabled(nodeid, "linux", environ)
    assert not diagnostics.enabled(nodeid + "extra", "win32", environ)
    assert not diagnostics.enabled(nodeid, "win32", {})


def test_allowlist_omits_poisoned_command_and_stderr(tmp_path):
    poison = "https://private.example/?token=poison"
    command = [
        str(tmp_path / "rcc.exe"),
        "holotree",
        "variables",
        "--space",
        "460c42919b8a21c5",
        str(tmp_path / "package.yaml"),
        "--config",
        str(tmp_path / "config.yaml"),
        "--json",
        "--no-retry-build",
        "--no-pyc-management",
        "--controller",
        "action-server",
        "--bundled",
        "--robocorp",
        poison,
    ]
    report = diagnostics.command_summary(command)
    assert report["operation"] == "holotree variables"
    assert report["space"] == "460c42919b8a21c5"
    assert report["unrecognized_arguments"] == 1
    assert report["no_retry_build"] is True
    assert str(tmp_path) not in json.dumps(report)
    assert poison not in json.dumps(report)
    stage = diagnostics.stderr_summary(
        "Running: " + subprocess.list2cmdline(command) + "\n" + poison
    )
    assert stage["last_rcc_command"] == report
    assert poison not in json.dumps(stage)


def test_failed_artifact_write_does_not_mask_original_error():
    failure = TimeoutError("original")

    def start(server, **kwargs):
        raise failure

    def publish(report):
        raise OSError("private artifact path")

    with pytest.raises(TimeoutError) as caught:
        diagnostics.observe_start(
            start,
            object(),
            snapshot=lambda server: {},
            publish=publish,
            offsets=(60, 80),
        )
    assert caught.value is failure


def test_snapshot_rejects_descendant_whose_parent_changed(monkeypatch, tmp_path):
    from io import StringIO
    from types import SimpleNamespace

    import psutil

    poison = "https://private.example/?token=poison"

    class Observed:
        pid = 42

        def ppid(self):
            return 7

        def create_time(self):
            return 1.0

        def status(self):
            return "sleeping"

        def cpu_times(self):
            return (0.0, 0.0)

        def cmdline(self):
            return ["native.exe", poison]

        def children(self):
            return [Reparented()] if self.pid == 42 else []

    class Reparented(Observed):
        pid = 43

        def ppid(self):
            return 999  # no longer owned by the observed wrapper

        def cmdline(self):
            pytest.fail("must not inspect a child after its parent changed")

    monkeypatch.setattr(psutil, "Process", lambda pid: Observed())
    reader = threading.Thread()
    server = SimpleNamespace(
        _process=SimpleNamespace(
            _proc=SimpleNamespace(
                pid=42,
                poll=lambda: None,
                stdout=SimpleNamespace(closed=False),
                stderr=SimpleNamespace(closed=False),
            ),
            _args=["native.exe"],
            _reader_threads=[reader],
            _env={},
        ),
        _stdout=StringIO(),
        _stderr=StringIO(poison),
        get_stderr=lambda: poison,
        datadir=tmp_path,
    )
    report = diagnostics.snapshot(server)
    assert [entry["pid"] for entry in report["processes"]] == [42]
    assert report["descendant_identity_unavailable"] is True
    assert report["pipes_closed"] == {"stdout": False, "stderr": False}
    assert report["rcc_internal_readers"] == "unavailable_from_host"
    assert poison not in json.dumps(report)


def test_installed_observer_hashes_native_only_after_original_cleanup(
    monkeypatch, tmp_path
):
    import hashlib

    from actions.server._selftest import ActionServerProcess

    native = tmp_path / "private-native.exe"
    native.write_bytes(b"native-byte-identity")
    config = tmp_path / "private-config.yaml"
    config.write_text("secret-config-content")
    cleaned = threading.Event()
    original_identity = diagnostics.file_identity
    failure = TimeoutError("original startup error")

    def identity(path, *args):
        if path == native:
            assert cleaned.is_set(), "do not pre-read a cold native executable"
        return original_identity(path, *args)

    def start(server, **kwargs):
        assert kwargs == {"timeout": 90, "actions_sync": True}
        cleaned.set()
        raise failure

    monkeypatch.setattr(diagnostics, "file_identity", identity)
    monkeypatch.setattr(ActionServerProcess, "start", start)
    directory = tmp_path / "reports"
    diagnostics.install(
        monkeypatch,
        directory,
        sorted(diagnostics.NODES)[0],
        {
            "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE": str(native),
            "GITHUB_SHA": "a" * 40,
            "PRIVATE_SECRET": "poison",
        },
        config,
    )
    with pytest.raises(TimeoutError) as caught:
        ActionServerProcess(tmp_path / "datadir").start(timeout=90, actions_sync=True)
    assert caught.value is failure
    reports = [
        json.loads(path.read_text()) for path in sorted(directory.glob("*.json"))
    ]
    assert len(reports) == 2
    assert (
        reports[-1]["native_executable"]["sha256"]
        == hashlib.sha256(native.read_bytes()).hexdigest()
    )
    serialized = json.dumps(reports)
    assert str(tmp_path) not in serialized
    assert "poison" not in serialized
    assert "secret-config-content" not in serialized
    assert all(
        "sha256" in value for value in reports[0]["identity"]["source_files"].values()
    )
