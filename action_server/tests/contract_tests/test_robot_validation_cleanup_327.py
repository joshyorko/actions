"""Real validation subprocess boundary, independent of Robot and RCC installs."""
import ctypes
import os
import sys
import time
from dataclasses import replace

import psutil
import pytest

from actions.server.foundry.robot_execution import RobotExecution
from actions.server.foundry.robot_validation import RobotValidator

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="owned Linux sessions")


@pytest.fixture
def reap_owned_validation_orphans():
    # Tests run serially. Adopt our fixture's orphan so cleanup can reap it;
    # restore the original process setting after this bounded test.
    libc = ctypes.CDLL(None)
    previous = ctypes.c_int()
    assert libc.prctl(37, ctypes.byref(previous), 0, 0, 0) == 0
    assert libc.prctl(36, 1, 0, 0, 0) == 0
    try:
        yield
    finally:
        assert libc.prctl(36, previous.value, 0, 0, 0) == 0


def bounded_check():
    deadline = time.monotonic() + 5

    def check():
        if time.monotonic() >= deadline:
            raise TimeoutError("synthetic validation deadline")

    return check


def test_validation_run_preserves_output_and_proves_cleanup(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    cleanup = RobotExecution._cleanup
    observed = []

    def capture(process, descendants, *, owns_session=False):
        assert owns_session is True
        result = cleanup(process, descendants, owns_session=owns_session)
        observed.append(result)
        return result

    monkeypatch.setattr(RobotExecution, "_cleanup", staticmethod(capture))
    result = RobotValidator._run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; print('validation-ok'); print('diagnostic', file=sys.stderr)",
        ],
        source,
        {"PATH": os.defpath},
        bounded_check(),
        None,
    )
    assert result.exit_code == 0
    assert result.stdout == b"validation-ok\n"
    assert result.stderr == b"diagnostic\n"
    assert (tmp_path / "stdout.log").read_bytes() == result.stdout
    assert (tmp_path / "stderr.log").read_bytes() == result.stderr
    assert len(observed) == 1 and observed[0].execution_stopped


def test_validation_failure_with_descendant_rejects_uncertain_cleanup(
    tmp_path, monkeypatch, reap_owned_validation_orphans
):
    source = tmp_path / "source"
    source.mkdir()
    pid_file = source / "owned-child.pid"
    child = (
        "import os,time; from pathlib import Path; "
        "Path('owned-child.pid').write_text(str(os.getpid())); time.sleep(20)"
    )
    wrapper = (
        "import subprocess,sys,time; from pathlib import Path; "
        f"subprocess.Popen([sys.executable,'-I','-c',{child!r}], "
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
        "print('failed-validation',flush=True); time.sleep(0.3); sys.exit(1)"
    )
    cleanup = RobotExecution._cleanup
    observed = []

    def uncertain(process, descendants, *, owns_session=False):
        assert owns_session is True
        result = cleanup(process, descendants, owns_session=owns_session)
        observed.append(result)
        # Real cleanup happens first; inject uncertainty only in its receipt.
        return replace(result, descendant_snapshot_complete=False)

    monkeypatch.setattr(RobotExecution, "_cleanup", staticmethod(uncertain))
    with pytest.raises(RuntimeError, match="validation process cleanup unconfirmed"):
        RobotValidator._run(
            [sys.executable, "-I", "-c", wrapper],
            source,
            {"PATH": os.defpath},
            bounded_check(),
            None,
        )
    assert pid_file.exists(), "fixture must create a real descendant"
    assert len(observed) == 1 and observed[0].execution_stopped
    child_pid = int(pid_file.read_text())
    assert not psutil.pid_exists(child_pid), "owned fixture descendant must be reaped"
    assert (tmp_path / "stdout.log").read_bytes() == b"failed-validation\n"
