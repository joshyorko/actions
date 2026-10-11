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


def delivered(clock=lambda: 10.0, use_https=False):
    return diagnostics.DeliveredObservations(
        began=0.0, use_https=use_https, clock=clock
    )


def progress(step, seconds="0.001", version="18.19.3", total="15"):
    return f"####  Progress: {step:02d}/{total}  v{version}  {seconds}s  secret suffix token=poison\n"


def complete(probe, channel="stderr"):
    for step in range(16):
        probe.line(channel, progress(step, "1.000"))
    return probe.summary()


def test_delivered_valid_stream_and_exact_ready_without_private_text():
    probe = delivered()
    assert complete(probe)["progress"]["interval_sum_seconds"] == 16.0
    probe.process_start_returned()
    probe.line("stderr", "Local Action Server: http://private.host:12345 poison")
    report = probe.summary()
    assert report["readiness"]["stderr"]["exact_match_count"] == 1
    assert (
        report["readiness"]["stderr"]["first_match_before_deadline_lower_bound"] is True
    )
    assert report["readiness_future"] == "unavailable_from_host"
    assert "private" not in json.dumps(report) and "poison" not in json.dumps(report)
    assert len(json.dumps(report)) < 16 * 1024


@pytest.mark.parametrize(
    "poison",
    [
        "missing",
        "duplicate",
        "reorder",
        "channel",
        "version",
        "total",
        "negative",
        "nan",
        "infinite",
        "large",
        "malformed",
        "long",
        "cap",
    ],
)
def test_progress_each_invalid_boundary_permanently_rejects_later_valid_stream(poison):
    assert complete(delivered())["progress"]["interval_sum_seconds"] == 16.0
    probe = delivered()
    if poison == "missing":
        probe.line("stderr", progress(1))
    elif poison == "duplicate":
        probe.line("stderr", progress(0))
        probe.line("stderr", progress(0))
    elif poison == "reorder":
        probe.line("stderr", progress(0))
        probe.line("stderr", progress(2))
    elif poison == "channel":
        probe.line("stdout", progress(0))
        probe.line("stderr", progress(1))
    elif poison == "version":
        probe.line("stderr", progress(0, version="18.19.4"))
    elif poison == "total":
        probe.line("stderr", progress(0, total="16"))
    elif poison in {"negative", "nan", "infinite", "large"}:
        value = {
            "negative": "-0.1",
            "nan": "nan",
            "infinite": "inf",
            "large": "3600.001",
        }[poison]
        probe.line("stderr", progress(0, value))
    elif poison == "malformed":
        probe.line("stderr", "#### Progress: broken poison")
    elif poison == "long":
        probe.line("stderr", "poison" * 2000)
    elif poison == "cap":
        for _ in range(33):
            probe.line("stderr", progress(0))
    report = complete(probe)
    assert report["progress"]["interval_sum_seconds"] is None
    assert report["observation_loss"] is True
    assert len(report["progress"]["marks"]) <= 32
    assert "poison" not in json.dumps(report)


@pytest.mark.parametrize(
    "channel,https,line,expected",
    [
        ("stderr", False, "Local Action Server: http://secret:123", 1),
        ("stdout", False, "Local Action Server: http://secret:123", 1),
        ("stderr", True, "Local Action Server: http://secret:123", 0),
        ("stderr", True, "Local Action Server: https://secret:123", 1),
        ("stderr", False, "Local Action Server: http://secret:\x1b[31m123", 0),
        ("stderr", False, "Local Action Server: malformed poison", 0),
    ],
)
def test_ready_exact_starter_regex_channel_no_acceptance_normalization(
    channel, https, line, expected
):
    probe = delivered(use_https=https)
    probe.process_start_returned()
    probe.line(channel, line)
    report = probe.summary()
    assert report["readiness"][channel]["exact_match_count"] == expected
    assert report["readiness"][channel]["literal_marker_count"] == 1
    assert (
        report["readiness"]["stderr" if channel == "stdout" else "stdout"][
            "exact_match_count"
        ]
        == 0
    )
    assert "secret" not in json.dumps(report) and "poison" not in json.dumps(report)


def test_ready_deadline_is_process_return_lower_bound_and_late_is_not_predeadline():
    now = [80.0]
    probe = delivered(clock=lambda: now[0])
    probe.process_start_returned()
    now[0] = 150.0
    probe.line("stderr", "Local Action Server: http://secret:123")
    assert (
        probe.summary()["readiness"]["stderr"][
            "first_match_before_deadline_lower_bound"
        ]
        is True
    )
    now[0] = 171.0
    probe.line("stderr", "Local Action Server: http://secret:123")
    assert (
        probe.summary()["readiness"]["stderr"]["last_match_before_deadline_lower_bound"]
        is False
    )


def test_lock_loss_and_secret_callback_exception_never_recover_or_log(
    monkeypatch, capsys
):
    from actions.server._robo_utils.callback import Callback, logger

    probe = delivered()
    callback = Callback()
    callback.register(lambda line: probe.line("stderr", line))
    monkeypatch.setattr(
        logger,
        "exception",
        lambda *a, **k: pytest.fail("probe exception escaped to Callback logger"),
    )
    probe.lock.acquire()
    try:
        callback(progress(0))
    finally:
        probe.lock.release()
    assert complete(probe)["progress"]["interval_sum_seconds"] is None

    def secret_clock():
        raise RuntimeError("secret token=poison")

    probe = delivered(clock=secret_clock)
    callback = Callback()
    callback.register(lambda line: probe.line("stderr", line))
    callback(progress(0))
    probe.clock = lambda: 10.0
    assert complete(probe)["progress"]["interval_sum_seconds"] is None
    captured = capsys.readouterr()
    assert "poison" not in json.dumps(probe.summary()) + captured.out + captured.err


def test_count_overflow_latches_unavailable():
    probe = delivered()
    probe.counts["stderr_lines"] = 65535
    probe.line("stderr", "unknown poison")
    assert complete(probe)["progress"]["interval_sum_seconds"] is None
    assert probe.summary()["counts"]["stderr_lines"] == 65535


@pytest.mark.parametrize(
    "dimension",
    ["wrapper", "live", "zombie", "errors", "snapshot", "reap", "readers", "none"],
)
def test_actual_cleanup_summary_keeps_each_dimension_without_text_or_identity(
    dimension,
):
    from actions.server._common.process import ProcessTreeCleanupResult

    kwargs = dict(
        wrapper_reaped=True,
        live_descendant_pids=(),
        zombie_descendant_pids=(),
        errors=(),
        descendant_snapshot_complete=True,
    )
    if dimension == "wrapper":
        kwargs["wrapper_reaped"] = False
    if dimension == "live":
        kwargs["live_descendant_pids"] = (123,)
    if dimension == "zombie":
        kwargs["zombie_descendant_pids"] = (456,)
    if dimension == "errors":
        kwargs["errors"] = ("secret token=poison",)
    if dimension == "snapshot":
        kwargs["descendant_snapshot_complete"] = False
    if dimension == "reap":
        kwargs["zombie_descendant_pids"] = (456,)
    result = ProcessTreeCleanupResult(**kwargs)
    probe = delivered()
    probe.cleanup_returned(
        (
            None if dimension == "none" else result,
            ("secret-reader",) if dimension == "readers" else (),
        )
    )
    report = probe.summary()["cleanup"]
    if dimension == "none":
        assert report["status"] == "unavailable"
    else:
        assert report["status"] == "returned"
        assert report["wrapper_reaped"] == result.wrapper_reaped
        assert report["execution_stopped"] == result.execution_stopped
        assert (
            report["descendant_snapshot_complete"]
            == result.descendant_snapshot_complete
        )
        assert report["descendant_reap_complete"] == result.descendant_reap_complete
        assert report["observed_live_child_count"] == len(result.live_descendant_pids)
        assert report["observed_zombie_child_count"] == len(
            result.zombie_descendant_pids
        )
        assert report["cleanup_error_count"] == len(result.errors)
        assert report["active_reader_count"] == (dimension == "readers")
    assert "secret" not in json.dumps(report) and "poison" not in json.dumps(report)


def test_owned_process_hooks_preserve_calls_callbacks_cleanup_tuple_and_other_process(
    monkeypatch,
):
    from types import SimpleNamespace

    from actions.server._common.process import ProcessTreeCleanupResult
    from actions.server._robo_utils.process import Process

    calls = []
    captured = []
    reports = []
    cleanup = (ProcessTreeCleanupResult(True, (), (), (), True), ())

    def process_start(process, *args, **kwargs):
        calls.append(("start", process, args, kwargs))
        if process is server._process:
            for i in range(16):
                process.on_stderr(progress(i))
            process.on_stdout("Local Action Server: http://private:123")

    def process_cleanup(process, deadline):
        calls.append(("cleanup", process, deadline))
        return cleanup

    monkeypatch.setattr(Process, "start", process_start)
    monkeypatch.setattr(Process, "_stop_and_reap_until", process_cleanup)
    server = SimpleNamespace(_process=None, _port=0)
    other = Process(["other"])
    result = object()

    def start(server, **kwargs):
        assert kwargs == {"timeout": 90, "actions_sync": True}
        server._process = Process(["owned"])
        server._process.on_stderr.register(captured.append)
        server._process.start(read_stdout=True, read_stderr=True, private="unchanged")
        assert other.start() is None
        assert server._process._stop_and_reap_until(123.5) is cleanup
        server._port = 42
        return result

    assert (
        diagnostics.observe_owned_start(
            monkeypatch,
            start,
            server,
            snapshot=lambda s: {},
            publish=reports.append,
            offsets=(60,),
            timeout=90,
            actions_sync=True,
        )
        is result
    )
    assert calls[0][2:] == (
        (),
        {"read_stdout": True, "read_stderr": True, "private": "unchanged"},
    )
    assert calls[-1] == ("cleanup", server._process, 123.5)
    assert len(captured) == 16
    assert server._process.on_stderr._callbacks == (captured.append,)
    assert (
        len(server._process.on_stdout) == 0
        and len(other.on_stdout) == 0
        and len(other.on_stderr) == 0
    )
    report = reports[-1]["delivered_observations"]
    assert report["progress"]["interval_sum_seconds"] == 0.016
    assert report["cleanup"]["status"] == "returned"
    assert report["port_positive_after_start"] is True


def test_owned_hook_original_exceptions_and_secret_probe_errors_preserved(monkeypatch):
    from types import SimpleNamespace

    from actions.server._robo_utils.process import Process

    server = SimpleNamespace(_process=None, _port=0)
    failure = TimeoutError("original")
    cleanup_error = RuntimeError("original cleanup")
    failure.add_note("retained note")
    reports = []

    def process_start(process, **kwargs):
        process.on_stderr(progress(0))

    def process_cleanup(process, deadline):
        raise cleanup_error

    monkeypatch.setattr(Process, "start", process_start)
    monkeypatch.setattr(Process, "_stop_and_reap_until", process_cleanup)

    def start(server, **kwargs):
        server._process = Process(["owned"])
        server._process.start()
        with pytest.raises(RuntimeError) as caught:
            server._process._stop_and_reap_until(123)
        assert caught.value is cleanup_error
        raise failure

    with pytest.raises(TimeoutError) as caught:
        diagnostics.observe_owned_start(
            monkeypatch,
            start,
            server,
            snapshot=lambda s: {},
            publish=reports.append,
            offsets=(60,),
            timeout=90,
            actions_sync=True,
        )
    assert caught.value is failure and caught.value.__notes__ == ["retained note"]
    assert reports[-1]["delivered_observations"]["cleanup"]["status"] == "raised"
    assert len(server._process.on_stderr) == 0


def test_ansi_progress_only_and_incomplete_stream_never_has_sum():
    probe = delivered()
    probe.line("stderr", "\x1b[32m" + progress(0) + "\x1b[0m")
    assert probe.summary()["progress"]["marks"][0]["step"] == 0
    assert probe.summary()["progress"]["interval_sum_seconds"] is None
    for step in range(1, 16):
        probe.line("stderr", progress(step))
    assert probe.summary()["progress"]["interval_sum_seconds"] == 0.016


def test_cleanup_none_and_probe_error_stay_unavailable_with_original_tuple():
    from types import SimpleNamespace

    probe = delivered()
    probe.cleanup_returned((SimpleNamespace(wrapper_reaped="private poison"), ()))
    report = probe.summary()
    assert (
        report["cleanup"]["status"] == "unavailable" and report["probe_error"] is True
    )
    assert "poison" not in json.dumps(report)


def test_publish_failure_latches_sum_and_preserves_primary():
    from types import SimpleNamespace

    probe = delivered()
    complete(probe)
    reports = []
    failure = TimeoutError("primary")

    def publish(report):
        reports.append(report)
        raise OSError("private poison")

    with pytest.raises(TimeoutError) as caught:
        diagnostics.observe_start(
            lambda s, **k: (_ for _ in ()).throw(failure),
            SimpleNamespace(_port=0),
            snapshot=lambda s: {},
            publish=publish,
            offsets=(60,),
            delivered=probe,
        )
    assert caught.value is failure
    assert probe.summary()["progress"]["interval_sum_seconds"] is None
    assert "poison" not in json.dumps(reports)


@pytest.mark.parametrize(
    "kwargs",
    [{"timeout": 30, "actions_sync": True}, {"timeout": 90, "actions_sync": False}],
)
def test_unwatched_start_budget_installs_no_process_hooks(
    monkeypatch, tmp_path, kwargs
):
    from actions.server._robo_utils.process import Process
    from actions.server._selftest import ActionServerProcess

    original_start = Process.start
    original_cleanup = Process._stop_and_reap_until
    calls = []

    def start(server, **arguments):
        assert (
            Process.start is original_start
            and Process._stop_and_reap_until is original_cleanup
        )
        calls.append(arguments)

    monkeypatch.setattr(ActionServerProcess, "start", start)
    diagnostics.install(
        monkeypatch,
        tmp_path / "reports",
        sorted(diagnostics.NODES)[0],
        {"SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE": "unused"},
        tmp_path / "config",
    )
    ActionServerProcess(tmp_path / "data").start(**kwargs)
    assert calls == [kwargs] and not (tmp_path / "reports").exists()


def test_second_native_start_does_not_reinstall_owned_hooks(monkeypatch, tmp_path):
    from actions.server._robo_utils.process import Process
    from actions.server._selftest import ActionServerProcess

    original_start = Process.start
    original_cleanup = Process._stop_and_reap_until
    calls = []

    def start(server, **arguments):
        calls.append(arguments)
        if len(calls) == 2:
            assert (
                Process.start is original_start
                and Process._stop_and_reap_until is original_cleanup
            )

    monkeypatch.setattr(ActionServerProcess, "start", start)
    diagnostics.install(
        monkeypatch,
        tmp_path / "reports",
        sorted(diagnostics.NODES)[0],
        {"SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE": "unused"},
        tmp_path / "config",
    )
    for _ in range(2):
        ActionServerProcess(tmp_path / "data").start(timeout=90, actions_sync=True)
    assert len(calls) == 2 and len(list((tmp_path / "reports").glob("*.json"))) == 2


def test_probe_setup_failure_delegates_original_without_callback_logging(monkeypatch):
    from types import SimpleNamespace

    failure = TimeoutError("primary")
    reports = []

    def setup(**kwargs):
        raise ValueError("private token=poison")

    monkeypatch.setattr(diagnostics, "DeliveredObservations", setup)
    with pytest.raises(TimeoutError) as caught:
        diagnostics.observe_owned_start(
            monkeypatch,
            lambda s, **k: (_ for _ in ()).throw(failure),
            SimpleNamespace(),
            snapshot=lambda s: {},
            publish=reports.append,
            offsets=(60,),
        )
    assert caught.value is failure and "poison" not in json.dumps(reports)


@pytest.mark.parametrize(
    "line",
    [
        "####Progress: 00/15 v18.19.3 0.001s",
        "#### Progress: 16/15 v18.19.3 0.001s",
        "#### Progress: 000/15 v18.19.3 -infseconds",
    ],
)
def test_progress_anchor_step_and_numeric_shape_reject_later_stream(line):
    assert complete(delivered())["progress"]["interval_sum_seconds"] == 16.0
    probe = delivered()
    probe.line("stderr", line)
    assert complete(probe)["progress"]["interval_sum_seconds"] is None


def test_unknown_lines_do_not_disqualify_valid_sequence():
    probe = delivered()
    probe.line("stderr", "private secret token=poison")
    probe.line("stderr", "#### unrelated private output")
    assert complete(probe)["progress"]["interval_sum_seconds"] == 16.0
    assert "private" not in json.dumps(probe.summary()) and "poison" not in json.dumps(
        probe.summary()
    )


def test_existing_readiness_callback_sees_identical_line_once_with_no_pipe_read(
    monkeypatch,
):
    import re
    from concurrent.futures import Future
    from types import SimpleNamespace

    from actions.server._robo_utils.process import Process

    server = SimpleNamespace(_process=None, _port=0)
    future = Future()
    captured = []
    reports = []
    marker = "Local Action Server: http://private:12345\n"
    result = object()

    class ForbiddenPipe:
        def read(self, *args):
            pytest.fail("new pipe read")

        def readline(self, *args):
            pytest.fail("new pipe readline")

    def process_start(process, **kwargs):
        process._proc = SimpleNamespace(stdout=ForbiddenPipe(), stderr=ForbiddenPipe())
        process.on_stderr(marker)

    monkeypatch.setattr(Process, "start", process_start)

    def start(server, **kwargs):
        server._process = Process(["unchanged"])
        server._process.on_stderr.register(captured.append)

        def ready(line):
            match = re.findall(r"Local Action Server: http://([\w.-]+):(\d+)", line)
            if match:
                future.set_result(match[0])

        with server._process.on_stderr.register(ready):
            server._process.start()
        assert future.result() == ("private", "12345")
        server._port = 12345
        return result

    assert (
        diagnostics.observe_owned_start(
            monkeypatch,
            start,
            server,
            snapshot=lambda s: {},
            publish=reports.append,
            offsets=(60,),
            timeout=90,
            actions_sync=True,
        )
        is result
    )
    assert captured == [marker] and server._process.on_stderr._callbacks == (
        captured.append,
    )
    assert (
        reports[-1]["delivered_observations"]["readiness"]["stderr"][
            "exact_match_count"
        ]
        == 1
    )
    assert "private" not in json.dumps(reports)


def test_secret_parser_failure_stays_inside_existing_callback(monkeypatch, capsys):
    from types import SimpleNamespace

    from actions.server._robo_utils.callback import Callback, logger

    probe = delivered()
    callback = Callback()
    callback.register(lambda line: probe.line("stderr", line))

    def fail(line):
        raise ValueError("private token=poison")

    monkeypatch.setattr(probe, "PROGRESS", SimpleNamespace(match=fail))
    monkeypatch.setattr(
        logger,
        "exception",
        lambda *a, **k: pytest.fail("observer parse exception leaked"),
    )
    callback(progress(0))
    report = probe.summary()
    captured = capsys.readouterr()
    assert (
        report["probe_error"] is True
        and report["progress"]["interval_sum_seconds"] is None
    )
    assert "poison" not in json.dumps(report) + captured.out + captured.err


def test_summary_contention_returns_only_unavailable_and_latches():
    probe = delivered()
    complete(probe)
    probe.lock.acquire()
    try:
        assert probe.summary() == {"status": "unavailable", "observation_loss": True}
    finally:
        probe.lock.release()
    assert probe.summary()["progress"]["interval_sum_seconds"] is None


def test_mark_cap_and_state_size_are_explicit():
    probe = delivered()
    for _ in range(33):
        probe.line("stderr", progress(0, "3600"))
    report = probe.summary()
    assert report["mark_cap_reached"] is True and len(report["progress"]["marks"]) == 32
    assert len(json.dumps(report)) < 16 * 1024


@pytest.mark.parametrize("origin", [0.0, 1000.125, 1048576.0, 1000000000.0])
@pytest.mark.parametrize("delta", [-0.0001, 0.0, 0.0001])
def test_ready_lower_bound_uses_exact_instants_not_rounded_display(origin, delta):
    now = [origin + 2.06651]
    probe = diagnostics.DeliveredObservations(began=origin, clock=lambda: now[0])
    probe.process_start_returned()
    exact_bound = now[0] + 90.0
    now[0] = exact_bound + delta
    probe.line("stderr", "Local Action Server: http://private:123")
    ready = probe.summary()["readiness"]["stderr"]
    expected = now[0] < exact_bound
    assert ready["first_match_before_deadline_lower_bound"] is expected
    assert ready["last_match_before_deadline_lower_bound"] is expected
    assert ready["first_match_offset_seconds"] == round(now[0] - origin, 3)
    assert "private" not in json.dumps(probe.summary())


def test_reported_rounding_counterexample_stays_postbound():
    now = [2.06651]
    probe = delivered(clock=lambda: now[0])
    probe.process_start_returned()
    now[0] = 92.06661
    probe.line("stderr", "Local Action Server: http://private:123")
    report = probe.summary()
    assert report["process_start_return_offset_seconds"] == 2.067
    assert report["readiness"]["stderr"]["first_match_offset_seconds"] == 92.067
    assert (
        report["readiness"]["stderr"]["first_match_before_deadline_lower_bound"]
        is False
    )


def test_unknown_start_return_clock_keeps_deadline_classification_unknown():
    now = [float("nan")]
    probe = delivered(clock=lambda: now[0])
    probe.process_start_returned()
    now[0] = 100.0
    probe.line("stderr", "Local Action Server: http://private:123")
    ready = probe.summary()["readiness"]["stderr"]
    assert ready["first_match_before_deadline_lower_bound"] is None
    assert ready["last_match_before_deadline_lower_bound"] is None
