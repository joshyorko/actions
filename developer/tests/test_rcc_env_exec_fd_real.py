"""Opt-in RCC descriptor-inheritance check; not an Actions/Core integration proof."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.skipif(
        sys.platform != "linux", reason="RCC descriptor passing check is Linux-only"
    ),
    pytest.mark.skipif(
        os.environ.get("ACTIONS_REAL_RCC_FD_TEST") != "1",
        reason="explicit real RCC FD qualification required",
    ),
]


_SUPERVISOR = r"""
import ctypes
import os
import select
import signal
import subprocess
import sys
import time

import psutil

timeout = float(sys.argv[1])
assert 0 < timeout <= 900
assert hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal")
libc = ctypes.CDLL(None, use_errno=True)
if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
    raise SystemExit(125)
pass_fds = tuple(int(fd) for fd in sys.argv[2].split(",") if fd)
separator = sys.argv.index("--", 3)
command = sys.argv[separator + 1:]
if not command:
    raise SystemExit(125)
owned = {}
reaped = set()

def exited(fd):
    return bool(select.select([fd], [], [], 0)[0])

def collect():
    # This process is a dedicated subreaper: direct adopted children can only
    # descend from the one command launched below.
    for child in psutil.Process().children(recursive=True):
        fd = None
        try:
            created = child.create_time()
            fd = os.pidfd_open(child.pid)
            current = psutil.Process(child.pid).create_time()
            if current != created:
                continue
            identity = (child.pid, current)
            if identity not in owned:
                owned[identity] = fd
                fd = None
        except (ProcessLookupError, psutil.NoSuchProcess):
            continue
        finally:
            if fd is not None:
                os.close(fd)

def reap_adopted(root_pid):
    for child in psutil.Process().children():
        if child.pid == root_pid:
            continue  # Popen owns and reaps the command process.
        try:
            pid, _ = os.waitpid(child.pid, os.WNOHANG)
            if pid:
                reaped.add(pid)
        except ChildProcessError:
            pass

def signal_live(sig):
    for fd in owned.values():
        if not exited(fd):
            try:
                signal.pidfd_send_signal(fd, sig)
            except ProcessLookupError:
                pass

def settle(proc, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        proc.poll()
        collect()
        reap_adopted(proc.pid)
        if all(exited(fd) for fd in owned.values()):
            return
        time.sleep(0.025)

proc = subprocess.Popen(command, close_fds=True, pass_fds=pass_fds)
deadline = time.monotonic() + timeout
timed_out = False
stop_requested = False
def request_stop(_signum, _frame):
    global stop_requested
    stop_requested = True

signal.signal(signal.SIGTERM, request_stop)
try:
    while proc.poll() is None and time.monotonic() < deadline and not stop_requested:
        collect()
        reap_adopted(proc.pid)
        time.sleep(0.025)
    collect()
    reap_adopted(proc.pid)
    if proc.poll() is None and (time.monotonic() >= deadline or stop_requested):
        timed_out = True
        signal_live(signal.SIGTERM)
        settle(proc, 2)
        signal_live(signal.SIGKILL)
        settle(proc, 3)
    else:
        # Allow fast daemonization/reparenting to become visible to the
        # subreaper, then treat any surviving descendant as a cleanup failure.
        time.sleep(0.1)
        collect()
        reap_adopted(proc.pid)
    live = [identity for identity, fd in owned.items() if not exited(fd)]
    leaked_descendant = bool(live)
    if live:
        signal_live(signal.SIGTERM)
        settle(proc, 2)
        signal_live(signal.SIGKILL)
        settle(proc, 3)
    live = [identity for identity, fd in owned.items() if not exited(fd)]
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        raise SystemExit(125)
    if live or timed_out or leaked_descendant:
        raise SystemExit(125 if live else 124)
    raise SystemExit(proc.returncode)
finally:
    if proc.poll() is None:
        signal_live(signal.SIGTERM)
        settle(proc, 2)
        signal_live(signal.SIGKILL)
        settle(proc, 3)
    collect()
    reap_adopted(proc.pid)
    if any(not exited(fd) for fd in owned.values()):
        signal_live(signal.SIGTERM)
        settle(proc, 2)
        signal_live(signal.SIGKILL)
        settle(proc, 3)
    collect()
    reap_adopted(proc.pid)
    remaining = [identity for identity, fd in owned.items() if not exited(fd)]
    for fd in owned.values():
        try:
            os.close(fd)
        except OSError:
            pass
    if remaining:
        raise SystemExit(125)
"""


def _require_supervisor_support():
    if sys.platform != "linux":
        pytest.skip("Linux subreaper and pidfd support is required")
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        pytest.fail("host Python must provide pidfd_open and pidfd_send_signal")
    if not hasattr(ctypes.CDLL(None), "prctl"):
        pytest.fail("host Linux libc must provide prctl for subreaper ownership")
    try:
        import psutil  # noqa: F401
    except ImportError:
        pytest.fail("host Python must provide psutil for owned-process discovery")


def _run_reaped(command, *, env, timeout, pass_fds=()):
    _require_supervisor_support()
    outer_timeout = timeout + 15
    supervisor_command = [
        sys.executable,
        "-c",
        _SUPERVISOR,
        str(timeout),
        ",".join(str(fd) for fd in pass_fds),
        "--",
        *command,
    ]
    process = subprocess.Popen(
        supervisor_command,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        close_fds=True,
        pass_fds=tuple(pass_fds),
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=outer_timeout)
    except subprocess.TimeoutExpired:
        # The inner subreaper normally completes its own cleanup first. This
        # final group kill bounds a wedged supervisor; such a timeout is failed
        # closed by raising and is never accepted as a clean result.
        try:
            os.kill(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                raise RuntimeError("supervisor termination is unconfirmed") from None
        assert process.poll() is not None, "RCC process was not reaped after timeout"
        raise TimeoutError("bounded supervised command did not settle") from None
    assert process.poll() is not None, "supervisor process did not exit"
    return process.returncode, stdout, stderr


def test_subreaper_cleans_a_detached_orphan_without_rcc():
    _require_supervisor_support()
    orphan_script = (
        "import os,time\n"
        "pid=os.fork()\n"
        "if pid==0:\n"
        " os.setsid()\n"
        " time.sleep(30)\n"
        "else:\n"
        " print('ORPHAN_PID='+str(pid),flush=True)\n"
    )
    status, stdout, stderr = _run_reaped(
        [sys.executable, "-c", orphan_script],
        env=os.environ.copy(),
        timeout=5,
    )
    assert status == 124, "the supervisor must clean and reject an orphaned descendant"
    assert b"ORPHAN_PID=" in stdout, stderr.decode(errors="replace")[-1000:]
    pid = int(stdout.split(b"ORPHAN_PID=", 1)[1].splitlines()[0])
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_subreaper_accepts_a_clean_command_without_rcc():
    _require_supervisor_support()
    status, stdout, stderr = _run_reaped(
        [sys.executable, "-c", "print('CLEAN_OWNED_PROCESS')"],
        env=os.environ.copy(),
        timeout=5,
    )
    assert status == 0, stderr.decode(errors="replace")[-1000:]
    assert b"CLEAN_OWNED_PROCESS" in stdout


def test_rcc_no_build_env_exec_forwards_one_inherited_pipe_fd(tmp_path: Path):
    if os.environ.get("ACTIONS_REAL_RCC_FD_TEST") != "1":
        pytest.skip("set ACTIONS_REAL_RCC_FD_TEST=1 for the opt-in real RCC check")
    rcc_value = os.environ.get("ACTIONS_RUNTIME_RCC_BINARY")
    if not rcc_value:
        pytest.fail("ACTIONS_RUNTIME_RCC_BINARY is required for the real RCC check")
    rcc = Path(rcc_value).resolve(strict=True)
    if not rcc.is_file():
        pytest.fail("ACTIONS_RUNTIME_RCC_BINARY must name a regular file")
    version_status, version_stdout, version_stderr = _run_reaped(
        [str(rcc), "--version"],
        env={"PATH": os.environ.get("PATH", ""), "HOME": str(tmp_path)},
        timeout=10,
    )
    assert version_status == 0, version_stderr.decode(errors="replace")[-1000:]
    version = version_stdout.decode(errors="replace").strip()
    assert version == "v18.19.3"

    task_home = tmp_path / "home"
    rcc_home = tmp_path / "robocorp"
    task_tmp = tmp_path / "tmp"
    evidence = tmp_path / "evidence"
    for path in (task_home, rcc_home, task_tmp, evidence):
        path.mkdir(mode=0o700)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(task_home),
        "ROBOCORP_HOME": str(rcc_home),
        "ACTIONS_HOME": str(rcc_home),
        "TMPDIR": str(task_tmp),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    manifest = tmp_path / "package.yaml"
    manifest.write_text(
        "version: 0.1\nspec-version: v2\ndependencies:\n"
        "  conda-forge:\n    - python=3.12.15\n",
        encoding="utf-8",
    )
    prepare_status, prepare_stdout, prepare_stderr = _run_reaped(
        [
            str(rcc),
            "env",
            "publish",
            "--environment",
            str(manifest),
            "--provider",
            "local",
            "--json",
        ],
        env=env,
        timeout=900,
    )
    assert prepare_status == 0, prepare_stderr.decode(errors="replace")[-2000:]
    prepared = json.loads(prepare_stdout)
    artifact = prepared.get("artifactDigest")
    assert (
        isinstance(artifact, str)
        and artifact.startswith("sha256:")
        and len(artifact) == 71
        and all(char in "0123456789abcdef" for char in artifact[7:])
    )
    carrier = str(rcc_home / "artifacts/v1/trust")
    acquire_status, acquire_stdout, acquire_stderr = _run_reaped(
        [
            str(rcc),
            "env",
            "acquire",
            "--artifact",
            artifact,
            "--provider",
            "local",
            "--trust-carrier",
            carrier,
            "--trust-carrier-type",
            "filesystem",
            "--permissive-local",
            "--json",
        ],
        env=env,
        timeout=120,
    )
    assert acquire_status == 0, acquire_stderr.decode(errors="replace")[-2000:]
    acquisition = json.loads(acquire_stdout)
    assert acquisition.get("artifactDigest") == artifact
    assert acquisition.get("verification", {}).get("valid") is True

    nonce = "fd-check-" + uuid4().hex
    read_fd, write_fd = os.pipe()
    positive_receipt = evidence / "positive-receipt.json"
    child = (
        "import os,sys\n"
        "fd=int(sys.argv[1])\n"
        "data=os.read(fd,256)\n"
        "assert os.read(fd,1)==b''\n"
        "print('RCC_FD_RESULT:'+data.decode('ascii'))\n"
    )
    positive = [
        str(rcc),
        "--no-build",
        "env",
        "exec",
        "--artifact",
        artifact,
        "--provider",
        "local",
        "--trust-carrier",
        carrier,
        "--trust-carrier-type",
        "filesystem",
        "--permissive-local",
        "--inherit-streams",
        "--receipt-file",
        str(positive_receipt),
        "--",
        "python",
        "-c",
        child,
        str(read_fd),
    ]
    try:
        os.write(write_fd, nonce.encode("ascii"))
        os.close(write_fd)
        write_fd = -1
        positive_status, positive_stdout, positive_stderr = _run_reaped(
            positive, env=env, timeout=120, pass_fds=(read_fd,)
        )
    finally:
        os.close(read_fd)
        if write_fd >= 0:
            os.close(write_fd)
    assert positive_status == 0, positive_stderr.decode(errors="replace")[-2000:]
    assert f"RCC_FD_RESULT:{nonce}".encode() in positive_stdout
    receipt = json.loads(positive_receipt.read_text(encoding="utf-8"))
    assert receipt.get("artifactDigest") == artifact
    assert receipt.get("verification", {}).get("valid") is True
    assert isinstance(receipt.get("leaseId"), str) and receipt["leaseId"]
    assert receipt.get("status") == "completed" and receipt.get("exitCode") == 0
    digest = hashlib.sha256()
    with rcc.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    print(f"RCC_FD_ARTIFACT={artifact} RCC_BINARY_SHA256={digest.hexdigest()}")

    negative_receipt = evidence / "negative-receipt.json"
    invalid_fd = 1_048_576
    command_separator = positive.index("--")
    negative = positive[: command_separator + 1] + [
        "python",
        "-c",
        "import os,sys; os.read(int(sys.argv[1]),1)",
        str(invalid_fd),
    ]
    negative[negative.index(str(positive_receipt))] = str(negative_receipt)
    negative_status, negative_stdout, negative_stderr = _run_reaped(
        negative, env=env, timeout=120
    )
    assert negative_status != 0
    assert b"RCC_FD_RESULT:" not in negative_stdout
    assert b"Bad file descriptor" in negative_stdout + negative_stderr
    negative_data = json.loads(negative_receipt.read_text(encoding="utf-8"))
    assert negative_data.get("artifactDigest") == artifact
    assert negative_data.get("verification", {}).get("valid") is True
    assert negative_data.get("exitCode") != 0
