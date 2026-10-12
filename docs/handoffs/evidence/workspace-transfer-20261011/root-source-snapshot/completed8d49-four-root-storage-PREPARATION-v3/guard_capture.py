"""Retain one metadata-only subprocess outcome before checking admission."""
import hashlib
import json
import os
from pathlib import Path
import subprocess


def _bytes(value):
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    raise TypeError("NONBYTE_SUBPROCESS_CAPTURE_REFUSED")


def _write(path, value):
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_dir(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def captured_guard_call(argv, *, cwd, env, phase, capture_parent, run=subprocess.run):
    assert phase in ("before", "after", "readonly-probe")
    parent = Path(capture_parent)
    assert parent.is_dir() and not parent.is_symlink()
    assert parent.stat().st_mode & 0o777 == 0o700
    capture = parent / phase
    capture.mkdir(mode=0o700)  # Refuse duplicate phase before launching anything.
    _fsync_dir(parent)
    primary = None
    result = None
    stdout = stderr = b""
    terminal = {"schema": "ONE_METADATA_GUARD_CAPTURE", "phase": phase,
                "returncode": None, "exception_type": None,
                "stdout_available": False, "stderr_available": False,
                "timeout_seconds": 60, "native_execution": "NOT_RUN"}
    try:
        result = run(argv, cwd=cwd, env=env, capture_output=True, timeout=60, check=False)
        stdout, stderr = _bytes(result.stdout), _bytes(result.stderr)
        terminal.update(returncode=result.returncode, stdout_available=True, stderr_available=True)
        if result.returncode != 0:
            primary = AssertionError("CURRENT_DATA_ONLY_SOURCE_ENV_NATIVE_GUARD_FAIL")
    except BaseException as exc:
        primary = exc
        terminal["exception_type"] = type(exc).__name__
        if isinstance(exc, subprocess.TimeoutExpired):
            stdout, stderr = _bytes(exc.stdout), _bytes(exc.stderr)
            terminal.update(stdout_available=exc.stdout is not None, stderr_available=exc.stderr is not None)
    terminal.update(stdout_bytes=len(stdout), stdout_sha256=hashlib.sha256(stdout).hexdigest(),
                    stderr_bytes=len(stderr), stderr_sha256=hashlib.sha256(stderr).hexdigest(),
                    admission="PASS" if primary is None else "FAIL")
    try:
        _write(capture / "stdout.private.log", stdout)
        _write(capture / "stderr.private.log", stderr)
        _write(capture / "terminal.json", (json.dumps(terminal, indent=2, sort_keys=True) + "\n").encode())
        _fsync_dir(capture)
        _fsync_dir(parent)
    except BaseException as retention:
        if primary is None:
            raise
        if hasattr(primary, "add_note"):
            primary.add_note("Guard capture retention also failed: " + type(retention).__name__)
    if primary is not None:
        raise primary
    return result, terminal
