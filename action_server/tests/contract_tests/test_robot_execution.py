"""Adapter proof with a host-port spy, not canonical admission/queue wiring."""

import hashlib
import io
import json
import os
import platform
import stat
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from action_server_tests.run_outputs.test_service import snapshot

from actions.server.foundry.robot_execution import (
    DirectRobotPreparation,
    RobotExecution,
    RobotExecutionError,
    RobotSelection,
)
from actions.server.run_outputs.types import Actor, AttemptFence, OutputRef


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _archive(text, extra=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in {"tasks.robot": text.encode(), **(extra or {})}.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            archive.writestr(info, content)
    return stream.getvalue()


class Host:
    """Only the approved lifecycle seam is simulated; Robot execution is real."""

    def __init__(self, selected):
        self.selected = selected
        self.intent = None
        self.live = True
        self.staged = []
        self.heartbeats = 0

    def check_live(self, actor, fence, selection):
        assert selection == self.selected
        if not self.live:
            raise RuntimeError("stale fence")
        return selection.snapshot

    def heartbeat(self, actor, fence, selection):
        self.check_live(actor, fence, selection)
        self.heartbeats += 1

    def launch_intent(self, actor, fence):
        return self.intent

    def record_launch_intent(self, actor, fence, intent):
        if self.intent is not None:
            raise RuntimeError("reconciliation required")
        self.intent = intent
        return intent

    def stage_output(self, actor, fence, *, name, media_type, content):
        assert self.live
        ref = OutputRef(
            workspace_id=str(self.selected.snapshot.deployment.workspace_id.root),
            run_id=fence.run_id,
            output_id=str(uuid4()),
        )
        self.staged.append((name, media_type, content, ref))
        return ref


@pytest.fixture
def case(tmp_path):
    if sys.platform != "linux" or platform.machine().lower() != "x86_64":
        pytest.skip("Robot process supervision currently qualifies Linux x86_64 only")
    archive = _archive("*** Tasks ***\nSelected\n    Log To Console    genuine robot\n")
    selected = RobotSelection(
        snapshot=snapshot(),
        plan_kind="direct",
        suite_path="tasks.robot",
        suite_name="Tasks",
        task_name="Selected",
        source_digest="sha256:" + hashlib.sha256(archive).hexdigest(),
        input_schema=_json({"type": "object", "additionalProperties": False}),
        output_schema=_json({"type": "object"}),
        inputs=b"{}",
    )
    actor = Actor(principal_id=str(uuid4()))
    fence = AttemptFence(
        run_id=str(uuid4()), attempt_id=str(uuid4()), owner_id=str(uuid4()), epoch=1
    )
    runner = RobotExecution(
        tmp_path / "executions", DirectRobotPreparation(Path(sys.executable))
    )
    return runner, selected, archive, actor, fence, Host(selected)


def _execute(case, **kwargs):
    runner, selection, archive, actor, fence, host = case
    return runner.execute(
        actor,
        fence,
        selection=selection,
        source_archive=archive,
        lifecycle=host,
        cancelled=lambda: False,
        timeout_seconds=kwargs.pop("timeout_seconds", 10),
        **kwargs,
    )


def test_real_direct_returns_xml_and_staged_refs_without_terminalization(case):
    result = _execute(case)
    host = case[-1]
    assert result.status == "PASS" and result.return_code == 0
    assert result.discriminator == "actions.robot-dispatch/v1"
    assert result.cleanup.execution_stopped
    assert {x.name for x in result.outputs} == {
        "robot-output.xml",
        "robot-stdout.log",
        "robot-stderr.log",
    }
    assert b"genuine robot" in next(
        x[2] for x in host.staged if x[0] == "robot-stdout.log"
    )
    assert host.intent is not None and host.heartbeats >= 1
    with pytest.raises(RobotExecutionError, match="reconciliation"):
        _execute(case)


def test_source_tamper_rejected_before_intent(case):
    runner, selection, archive, actor, fence, host = case
    with pytest.raises(ValueError, match="source"):
        runner.execute(
            actor,
            fence,
            selection=selection,
            source_archive=archive + b"x",
            lifecycle=host,
            cancelled=lambda: False,
            timeout_seconds=10,
        )
    assert host.intent is None and not host.staged


def test_stale_fence_rejected_before_intent(case):
    case[-1].live = False
    with pytest.raises(RuntimeError, match="stale"):
        _execute(case)
    assert case[-1].intent is None


def _with_source(case, text, **changes):
    runner, selected, _, actor, fence, _ = case
    archive = _archive(text)
    selected = replace(
        selected,
        source_digest="sha256:" + hashlib.sha256(archive).hexdigest(),
        **changes,
    )
    return runner, selected, archive, actor, fence, Host(selected)


def test_real_failed_robot_returns_failure_xml_not_action_result(case):
    result = _execute(
        _with_source(case, "*** Tasks ***\nSelected\n    Fail    deliberate failure\n")
    )
    assert result.status == "FAIL" and result.return_code == 1
    assert (
        next(x for x in result.outputs if x.name == "robot-output.xml").media_type
        == "application/xml"
    )


def test_exact_model_selection_does_not_run_normalized_name_neighbor(case):
    case = _with_source(
        case,
        "*** Tasks ***\nSelected\n    No Operation\nS_e_l_e_c_t_e_d\n    Fail    must not execute\n",
    )
    assert _execute(case).status == "PASS"


@pytest.mark.parametrize(
    "changes",
    [
        {"adapter_version": "2"},
        {"robot_version": "7.4.1"},
        {"python_version": (3, 13)},
        {"platform_tag": "win32-amd64"},
        {"plan_kind": "other"},
        {"suite_path": "../tasks.robot"},
        {"rcc_artifact_digest": "sha256:" + "1" * 64},
        {"input_schema": b'{"$ref":"https://example.invalid/schema"}'},
        {"inputs": b'{"extra":1}'},
    ],
)
def test_selection_refuses_unknown_changed_or_unsafe_contract(case, changes):
    with pytest.raises(Exception):
        replace(case[1], **changes)


def test_uncertain_launch_ack_never_starts_task(case, monkeypatch):
    host = case[-1]
    original = host.record_launch_intent

    def uncertain(actor, fence, intent):
        original(actor, fence, intent)
        return None

    monkeypatch.setattr(host, "record_launch_intent", uncertain)
    with pytest.raises(RobotExecutionError, match="uncertain"):
        _execute(case)
    assert host.intent is not None
    assert not list(case[0].root.glob("*/stdout.log"))
    with pytest.raises(RobotExecutionError, match="reconciliation"):
        _execute(case)


def test_cancel_before_start_does_not_record_intent(case):
    runner, selection, archive, actor, fence, host = case
    with pytest.raises(RobotExecutionError, match="cancelled"):
        runner.execute(
            actor,
            fence,
            selection=selection,
            source_archive=archive,
            lifecycle=host,
            cancelled=lambda: True,
            timeout_seconds=10,
        )
    assert host.intent is None


def test_cancel_running_task_retains_stdout_and_blocks_retry(case):
    case = _with_source(
        case,
        "*** Tasks ***\nSelected\n    Log To Console    started\n    Sleep    30\n",
    )
    runner, selection, archive, actor, fence, host = case

    def cancelled():
        return bool(list(runner.root.glob("*/stdout.log")))

    with pytest.raises(RobotExecutionError, match="cancelled") as raised:
        runner.execute(
            actor,
            fence,
            selection=selection,
            source_archive=archive,
            lifecycle=host,
            cancelled=cancelled,
            timeout_seconds=10,
        )
    assert raised.value.directory.is_dir()
    assert (raised.value.directory / "stdout.log").read_bytes()
    assert not host.staged
    with pytest.raises(RobotExecutionError, match="reconciliation"):
        _execute(case)


def test_timeout_stops_process_and_keeps_diagnostics(case):
    case = _with_source(
        case,
        "*** Tasks ***\nSelected\n    Log To Console    started\n    Sleep    30\n",
    )
    runner, selection, archive, actor, fence, host = case
    with pytest.raises(RobotExecutionError, match="deadline") as raised:
        runner.execute(
            actor,
            fence,
            selection=selection,
            source_archive=archive,
            lifecycle=host,
            cancelled=lambda: False,
            timeout_seconds=1,
        )
    assert (raised.value.directory / "stdout.log").is_file()
    assert not host.staged


def test_stale_fence_while_running_never_stages(case, monkeypatch):
    case = _with_source(
        case,
        "*** Tasks ***\nSelected\n    Log To Console    started\n    Sleep    30\n",
    )
    runner, _, _, _, _, host = case
    original = host.check_live

    def live(actor, fence, selection):
        if list(runner.root.glob("*/stdout.log")):
            host.live = False
        return original(actor, fence, selection)

    monkeypatch.setattr(host, "check_live", live)
    with pytest.raises(RuntimeError, match="stale"):
        _execute(case)
    assert not host.staged and host.intent is not None


def test_bounded_noisy_output_has_explicit_truncation(case, monkeypatch):
    import actions.server.foundry.robot_execution as module

    monkeypatch.setattr(module, "_LOG_LIMIT", 128)
    case = _with_source(
        case, "*** Tasks ***\nSelected\n    Log To Console    " + "x" * 1000 + "\n"
    )
    result = _execute(case)
    stdout = next(x for x in result.outputs if x.name == "robot-stdout.log")
    assert (
        stdout.byte_length == 128 and stdout.truncated and stdout.observed_bytes > 128
    )


def test_cleanup_uncertainty_prevents_staging_and_keeps_resources(case, monkeypatch):
    import actions.server.foundry.robot_execution as module

    original = module.force_kill_process_tree_until

    def uncertain(*args, **kwargs):
        actual = original(*args, **kwargs)
        return replace(actual, descendant_snapshot_complete=False)

    monkeypatch.setattr(module, "force_kill_process_tree_until", uncertain)
    with pytest.raises(module.RobotCleanupIncomplete) as raised:
        _execute(case)
    assert raised.value.directory.is_dir() and not case[-1].staged


def test_plan_cannot_fall_back_to_direct_preparation(case):
    selected = replace(
        case[1],
        plan_kind="rcc",
        rcc_specification_digest="sha256:" + "1" * 64,
        rcc_artifact_digest="sha256:" + "2" * 64,
        package_yaml_digest="sha256:" + "3" * 64,
    )
    runner, _, archive, actor, fence, _ = case
    host = Host(selected)
    with pytest.raises(ValueError, match="no fallback"):
        runner.execute(
            actor,
            fence,
            selection=selected,
            source_archive=archive,
            lifecycle=host,
            cancelled=lambda: False,
            timeout_seconds=10,
        )
    assert host.intent is None


@pytest.mark.skipif(sys.platform != "linux", reason="POSIX FIFO boundary")
@pytest.mark.parametrize("name", ["output.xml", "rcc-receipt.json"])
def test_evidence_fifo_refuses_without_blocking(tmp_path, name):
    fifo = tmp_path / name
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="regular"):
        RobotExecution._read(fifo, 1024)


def test_selector_initialization_failure_still_reaps_process(case, monkeypatch):
    import actions.server.foundry.robot_execution as module

    processes = []
    original = module.subprocess.Popen

    def launched(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    def unavailable():
        raise OSError("selector unavailable")

    monkeypatch.setattr(module.subprocess, "Popen", launched)
    monkeypatch.setattr(module.selectors, "DefaultSelector", unavailable)
    with pytest.raises(OSError, match="selector"):
        _execute(case)
    assert len(processes) == 1 and processes[0].poll() is not None
    assert case[-1].intent is not None and not case[-1].staged


def test_orphaned_same_group_child_is_stopped(case):
    import psutil

    text = (
        "*** Settings ***\nLibrary    spawn.py\n*** Tasks ***\nSelected\n    Launch\n"
    )
    extra = {
        "spawn.py": b'import subprocess,sys\nfrom pathlib import Path\ndef launch():\n p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n Path("../child.pid").write_text(str(p.pid))\n'
    }
    runner, selected, _, actor, fence, _ = case
    archive = _archive(text, extra)
    selected = replace(
        selected, source_digest="sha256:" + hashlib.sha256(archive).hexdigest()
    )
    host = Host(selected)
    result = _execute((runner, selected, archive, actor, fence, host))
    pid = int((runner.root / result.launch.launch_id / "child.pid").read_text())
    assert result.cleanup.execution_stopped
    try:
        assert psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        # An outer subreaper can reap the stopped orphan while we inspect it.
        # Absence is already the stronger accepted outcome; do not race a
        # separate pid_exists() check against process metadata access.
        pass


def test_xml_identity_tampering_refuses_staging(case, monkeypatch):
    original = RobotExecution._read

    def changed(path, limit):
        value = original(path, limit)
        return (
            value.replace(b'name="Selected"', b'name="Other"')
            if path.name == "output.xml"
            else value
        )

    monkeypatch.setattr(RobotExecution, "_read", staticmethod(changed))
    with pytest.raises(RobotExecutionError, match="identity"):
        _execute(case)
    assert not case[-1].staged


@pytest.mark.real_rcc
@pytest.mark.parametrize("failure", [False, True])
def test_real_retained_rcc_robot_plan(case, failure):
    from actions.server.deployments.package_revision_compiler import (
        load_prepared_rcc_environment,
    )
    from actions.server.foundry.robot_execution import RccRobotPreparation

    receipt = os.environ.get("ACTIONS_ROBOT_PREPARED_RCC_RECEIPT")
    if not receipt:
        pytest.skip(
            "requires genuine prepared Robot RCC receipt and adjacent package.yaml"
        )
    prepared = load_prepared_rcc_environment(Path(receipt))
    package = Path(receipt).with_name("package.yaml").read_bytes()
    runner, selected, _, actor, fence, _ = case
    archive = _archive(
        "*** Tasks ***\nSelected\n    "
        + (
            "Fail    deliberate failure"
            if failure
            else "Log To Console    genuine retained RCC"
        )
        + "\n",
        {"package.yaml": package},
    )
    selected = replace(
        selected,
        plan_kind="rcc",
        source_digest="sha256:" + hashlib.sha256(archive).hexdigest(),
        rcc_specification_digest=prepared.build_identity.specification_digest,
        rcc_artifact_digest=prepared.build_identity.artifact_digest,
        package_yaml_digest=prepared.package_yaml_digest,
    )
    runner = RobotExecution(
        runner.root,
        RccRobotPreparation(Path(os.environ["ACTIONS_RUNTIME_RCC_BINARY"]), prepared),
    )
    host = Host(selected)
    result = _execute(
        (runner, selected, archive, actor, fence, host), timeout_seconds=60
    )
    assert result.status == ("FAIL" if failure else "PASS")
    assert {x.name for x in result.outputs} == {
        "robot-output.xml",
        "robot-stdout.log",
        "robot-stderr.log",
        "rcc-receipt.json",
    }
    assert result.cleanup.execution_stopped


def test_wrapper_exit_between_poll_and_snapshot_is_not_execution_failure(
    case, monkeypatch
):
    import psutil

    import actions.server.foundry.robot_execution as module

    processes = []
    original = module.subprocess.Popen

    def launched(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    def exited(pid):
        processes[0].wait(timeout=5)
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(module.subprocess, "Popen", launched)
    monkeypatch.setattr(module, "snapshot_process_descendants", exited)
    assert _execute(case).status == "PASS"


def test_unsupported_host_refuses_before_resource_creation(tmp_path, monkeypatch):
    import actions.server.foundry.robot_execution as module

    monkeypatch.setattr(module.sys, "platform", "unsupported")
    with pytest.raises(ValueError, match="unsupported host"):
        RobotExecution(
            tmp_path / "unused", DirectRobotPreparation(Path(sys.executable))
        )
    assert not (tmp_path / "unused").exists()


def test_workload_cannot_change_retained_source_before_staging(case):
    case = _with_source(
        case,
        "*** Settings ***\nLibrary    OperatingSystem\n*** Tasks ***\nSelected\n    Create File    ${CURDIR}/tasks.robot    altered source\n",
    )
    with pytest.raises(RobotExecutionError, match="source changed"):
        _execute(case)
    assert not case[-1].staged
