"""Real local process cleanup; receipt fixtures are not real RCC evidence."""

import json
import os
import subprocess
import sys
import time

import pytest

from actions.server.foundry.rcc_execution import (
    GeneratedRccExecution,
    RccCleanupIncomplete,
    _OwnedProcessCapture,
)


@pytest.fixture(autouse=True)
def reap_owned_orphans():
    # Linux PID 1 may not reap test orphans. Adopt them in this serial test
    # process so psutil's owned descendant waits can reap them after cleanup.
    if sys.platform != "linux":
        yield
        return
    import ctypes

    libc = ctypes.CDLL(None)
    previous = ctypes.c_int()
    assert libc.prctl(37, ctypes.byref(previous), 0, 0, 0) == 0
    assert libc.prctl(36, 1, 0, 0, 0) == 0
    try:
        yield
    finally:
        assert libc.prctl(36, previous.value, 0, 0, 0) == 0


def child(tmp_path):
    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-c",
            "import subprocess,sys,time; subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)']); print('owned child',flush=True); time.sleep(0.4); sys.exit(3)",
        ],
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    owner = _OwnedProcessCapture(process, owns_session=True)
    setattr(process, "_actions_capture_owned", owner.capture)
    runner = object.__new__(GeneratedRccExecution)
    try:
        captures = runner._capture_process(
            process, None, None, {}, lambda: False, time.monotonic() + 5
        )
        process.wait(timeout=2)
        assert owner.owned, "test must observe real descendant before wrapper exits"
        return runner, process, owner, captures
    except BaseException:
        owner.cleanup()
        raise


def _receipt_value(case, artifact):
    value = {
        "artifactDigest": artifact,
        "verification": {"valid": True},
        "leaseId": "owned-fixture",
        "status": "failed",
        "exitCode": 3,
    }
    if case == "wrong-artifact":
        value["artifactDigest"] = "sha256:" + "b" * 64
    if case == "wrong-exit":
        value["exitCode"] = 4
    if case == "invalid-trust":
        value["verification"]["valid"] = False
    return value


def _write_receipt(tmp_path, case, value):
    receipt = tmp_path / "receipt.json"
    if case != "missing":
        receipt.write_text(json.dumps(value))
    return receipt


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "missing",
        "wrong-artifact",
        "wrong-exit",
        "invalid-trust",
        "uncertain-cleanup",
    ],
)
@pytest.mark.skipif(os.name != "posix", reason="owned POSIX process-group pipe capture")
def test_only_matching_receipt_and_complete_cleanup_permit_failure(tmp_path, case):
    runner, process, owner, captures = child(tmp_path)
    artifact = "sha256:" + "a" * 64
    value = _receipt_value(case, artifact)
    receipt = _write_receipt(tmp_path, case, value)
    if case == "uncertain-cleanup":
        owner.failed = True
    try:
        if case == "valid":
            raw, cleanup = runner._confirmed_failed_receipt(
                process, owner, receipt, artifact
            )
            assert cleanup.execution_stopped and json.loads(raw) == value
            assert captures[0] == b"owned child\n"
            assert process.returncode == 3
        else:
            with pytest.raises(
                (RuntimeError, ValueError, OSError, RccCleanupIncomplete)
            ):
                runner._confirmed_failed_receipt(process, owner, receipt, artifact)
    finally:
        # The helper cleanup already stops observed descendants, including on
        # missing/mismatched receipts; no domain publication exists in this test.
        owner.cleanup()


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "missing",
        "wrong-artifact",
        "wrong-exit",
        "invalid-trust",
        "uncertain-cleanup",
    ],
)
def test_receipt_and_cleanup_decisions_are_platform_neutral(tmp_path, case):
    from types import SimpleNamespace

    runner = object.__new__(GeneratedRccExecution)
    process = SimpleNamespace(returncode=3)
    cleanup = SimpleNamespace(execution_stopped=case != "uncertain-cleanup")
    owner = SimpleNamespace(cleanup=lambda: cleanup)
    artifact = "sha256:" + "a" * 64
    value = _receipt_value(case, artifact)
    receipt = _write_receipt(tmp_path, case, value)

    if case == "valid":
        raw, result = runner._confirmed_failed_receipt(
            process, owner, receipt, artifact
        )
        assert result.execution_stopped
        assert json.loads(raw) == value
    else:
        with pytest.raises((RuntimeError, ValueError, OSError, RccCleanupIncomplete)):
            runner._confirmed_failed_receipt(process, owner, receipt, artifact)


def test_already_exited_wrapper_without_descendant_snapshot_is_uncertain(tmp_path):
    process = subprocess.Popen([sys.executable, "-I", "-c", "raise SystemExit(3)"])
    process.wait(timeout=5)
    owner = _OwnedProcessCapture(process)
    runner = object.__new__(GeneratedRccExecution)
    assert not owner.complete
    with pytest.raises(RccCleanupIncomplete):
        runner._confirmed_failed_receipt(
            process, owner, tmp_path / "missing.json", "sha256:" + "a" * 64
        )


@pytest.mark.skipif(sys.platform != "linux", reason="Linux isolated subreaper harness")
@pytest.mark.parametrize("wrapper_exits", [False, True])
def test_late_child_after_empty_snapshot_is_stopped(tmp_path, wrapper_exits):
    # Isolate subreaper state from pytest and reap exactly this fixture's orphan.
    code = r"""
import ctypes, json, subprocess, sys
import psutil
from actions.server.foundry.rcc_execution import _OwnedProcessCapture
assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
wrapper_exits = sys.argv[1] == "True"
wrapper = "import subprocess,sys,time; print('ready',flush=True); sys.stdin.readline(); p=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(60)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True); " + ("sys.exit(3)" if wrapper_exits else "time.sleep(60)")
p = subprocess.Popen([sys.executable, '-I', '-c', wrapper], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, start_new_session=True)
child = None
try:
    assert p.stdout.readline().strip() == 'ready'
    owner = _OwnedProcessCapture(p, owns_session=True)
    assert owner.complete and not owner.owned
    p.stdin.write('spawn\n'); p.stdin.flush()
    child = psutil.Process(int(p.stdout.readline()))
    if wrapper_exits: assert p.wait(timeout=5) == 3
    cleanup = owner.cleanup()
    assert cleanup.execution_stopped, cleanup
    assert not child.is_running() or child.status() == psutil.STATUS_ZOMBIE
    if wrapper_exits: assert p.returncode == 3
finally:
    if child is not None:
        try:
            child.kill(); child.wait(timeout=5)
        except psutil.NoSuchProcess: pass
    if p.poll() is None: p.kill(); p.wait(timeout=5)
    p.stdin.close(); p.stdout.close()
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(wrapper_exits)],
        capture_output=True,
        timeout=25,
    )
    assert completed.returncode == 0, completed.stderr.decode()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX owned process group")
def test_confirmed_cleanup_does_not_resignal_reused_group(monkeypatch):
    process = subprocess.Popen(
        [sys.executable, "-I", "-c", "raise SystemExit(3)"],
        start_new_session=True,
    )
    process.wait(timeout=5)
    owner = _OwnedProcessCapture(process, owns_session=True)
    first = owner.cleanup()
    assert first.execution_stopped

    def forbidden(*args, **kwargs):
        raise AssertionError("settled ownership must not enumerate or signal again")

    monkeypatch.setattr(owner, "capture", forbidden)
    monkeypatch.setattr("os.killpg", forbidden)
    assert owner.cleanup() is first
