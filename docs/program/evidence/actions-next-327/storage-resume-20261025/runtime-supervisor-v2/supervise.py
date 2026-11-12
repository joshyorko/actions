"""Explicit-launch Runtime qualification with incremental results and one owned PG."""
import argparse
import ctypes
import hashlib
import json
import os
import re
import secrets
import selectors
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil

GIB = 1024**3
IMAGE = "postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81"
HERE = Path(__file__).resolve().parent


class SupervisorStop(BaseException):
    def __init__(self, signum):
        self.signum = signum


def install_stop_handlers():
    requested = []
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}

    def stop(signum, frame):
        # Only the first signal interrupts; later signals cannot skip finally.
        if not requested:
            requested.append(signum)
            raise SupervisorStop(signum)

    for sig in previous:
        signal.signal(sig, stop)
    return previous


def source_snapshot(source):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source,
                                   text=True, timeout=15).strip()
    dirty = bool(subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=source, timeout=15))
    package = source / "action_server"
    files = [package / "pyproject.toml", *sorted((package / "src").rglob("*.py")),
             *sorted((package / "tests").rglob("*.py"))]
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(package)).encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return {"source_sha": head, "worktree_clean": not dirty,
            "source_tests_fingerprint": digest.hexdigest()}


def passes_gate(code, abort, before, after, progress):
    finish = summary(progress)["pytest_session_finish"]
    return (code == 0 and abort is None and before == after
            and before["worktree_clean"] and after["worktree_clean"]
            and finish is not None and finish.get("exitstatus") == 0)


def write(path, value):
    temporary = path.with_suffix(".writing")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def send_owned(process, sig):
    # The only process group signaled was created by our start_new_session Popen.
    # Stop the group before each fresh descendant enumeration, including adoptees.
    if process is not None:
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
    for child in psutil.Process().children(recursive=True):
        try:
            if child.status() != psutil.STATUS_ZOMBIE:
                child.send_signal(sig)
        except psutil.NoSuchProcess:
            pass


def reap(process):
    if process is not None:
        process.poll()
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if not pid:
                break
        except ChildProcessError:
            break
    return psutil.Process().children(recursive=True)


def shutdown(process, stages=((signal.SIGINT, 45), (signal.SIGTERM, 10), (signal.SIGKILL, 5))):
    receipt = []
    # Normally completed suites must not receive duplicate group signals.
    if not reap(process):
        return receipt
    for sig, seconds in stages:
        send_owned(process, sig)
        receipt.append({"signal": sig.name, "wait_seconds": seconds})
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if not reap(process):
                return receipt
            # SIGKILL is repeated with fresh snapshots to cover session/fork escape.
            if sig == signal.SIGKILL:
                send_owned(process, sig)
            time.sleep(.1)
    if reap(process):
        raise RuntimeError("Owned descendants remain after bounded shutdown")
    return receipt


def clean_line(raw, secret_values):
    value = raw.decode("utf-8", "replace")
    for secret in secret_values:
        value = value.replace(secret, "[redacted]")
    value = re.sub(r"(https?://|postgresql://)[^/\s@]+@", r"\1[redacted]@", value)
    value = re.sub(r"(?i)(authorization:\s*(?:bearer|basic)\s+)\S+", r"\1[redacted]", value)
    return value.encode()


def run_process(command, env, output, seconds, floor, secret_values=(), capacity=True):
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    pending = b""
    reason = None
    deadline = time.monotonic() + seconds
    cleanup = []
    written = 0
    previous_logs = sum(p.stat().st_size for p in output.parent.glob("*.log") if p != output)
    try:
        with output.open("wb") as log:
            while selector.get_map() or process.poll() is None:
                if capacity and shutil.disk_usage(output.parent).free < floor:
                    reason = "disk_floor"
                elif time.monotonic() >= deadline:
                    reason = "deadline"
                if reason:
                    break
                for key, _ in selector.select(.25):
                    raw = os.read(key.fd, 65536)
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    pending += raw
                    # Never write split secret-bearing lines or unbounded log lines.
                    while b"\n" in pending:
                        line, pending = pending.split(b"\n", 1)
                        safe = clean_line(line + b"\n", secret_values)
                        if previous_logs + written + len(safe) > 50 * 1024**2:
                            reason = "log_limit"
                            break
                        log.write(safe)
                        log.flush()
                        written += len(safe)
                    if len(pending) > 1024**2:
                        reason = "oversized_log_line"
                    if reason:
                        break
            if pending and not reason:
                safe = clean_line(pending, secret_values)
                if previous_logs + written + len(safe) > 50 * 1024**2:
                    reason = "log_limit"
                else:
                    log.write(safe)
    except BaseException:
        reason = reason or "supervisor_exception"
        raise
    finally:
        # Closing the read end before graceful exit can break pytest's final flush.
        # A drain thread consumes remaining output while shutdown gives pytest 45s.
        import threading
        def drain():
            try:
                while process.stdout.read(65536):
                    pass
            except (OSError, ValueError):
                pass
        thread = threading.Thread(target=drain, daemon=True)
        thread.start()
        try:
            cleanup = shutdown(process)
        finally:
            thread.join(timeout=2)
            selector.close()
            process.stdout.close()
        write(output.with_suffix(".process.json"), {
            "returncode": process.returncode, "abort_reason": reason,
            "shutdown": cleanup, "log_bytes": written})
    return process.returncode, reason


def summary(progress):
    counts = {}
    finish = None
    if progress.exists():
        with progress.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if record.get("event") == "report":
                    key = record["phase"] + ":" + record["outcome"]
                    counts[key] = counts.get(key, 0) + 1
                elif record.get("event") == "session_finish":
                    finish = record
    return {"phase_counts": counts, "pytest_session_finish": finish}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--source", type=Path, default=Path("/workspace/actions"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        raise ValueError("Exact source SHA required")
    if shutil.disk_usage(args.output.parent).free < 13 * GIB:
        raise RuntimeError("Initial 13 GiB free-space gate failed")
    args.output.mkdir(mode=0o700)
    out = args.output.resolve()
    libc = ctypes.CDLL(None)
    previous = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(previous), 0, 0, 0) != 0 or libc.prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError("Dedicated Linux subreaper unavailable")
    state = {"status": "RUNNING", "source_sha": args.source_sha,
             "excluded_gates": ["browser_origin_acceptance", "native_artifact_test"],
             "initial_free_bytes": shutil.disk_usage(out).free}
    env = dict(os.environ)
    cid = None
    cidfile = out / "owned-postgres.cid"
    progress = out / "progress.jsonl"
    gateway = ["rcc", "task", "script", "-r", str(args.source / "developer/toolkit.yaml"),
               "--", "python", "/workspace/actions-cloud/package-command.py", "action_server",
               "run", "python", str(HERE / "pytest_entry.py"), "--source", str(args.source),
               "--source-sha", args.source_sha, "--progress", str(progress)]
    previous_handlers = install_stop_handlers()
    try:
        before = source_snapshot(args.source)
        state["source_before"] = before
        if not before["worktree_clean"] or before["source_sha"] != args.source_sha:
            state.update(status="PREFLIGHT_FAILED", abort_reason="dirty_or_changed_source")
            return 2
        code, abort = run_process(gateway + ["--receipt", str(out / "preflight.json"), "--preflight-only"],
                                  env, out / "preflight.log", 180, 10 * GIB)
        if code != 0 or abort:
            state.update(status="PREFLIGHT_FAILED", abort_reason=abort)
            return 2
        password = secrets.token_hex(24)
        env["POSTGRES_PASSWORD"] = password
        created = subprocess.run(["docker", "create", "--cidfile", str(cidfile), "--memory", "768m",
            "--tmpfs", "/var/lib/postgresql/data:rw,size=512m", "-p", "127.0.0.1::5432",
            "-e", "POSTGRES_PASSWORD", IMAGE], env=env, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=30)
        if cidfile.exists():
            cid = cidfile.read_text().strip()
            if not re.fullmatch(r"[0-9a-f]{64}", cid):
                cid = None
                raise RuntimeError("Invalid owned container identity")
        created.check_returncode()
        if cid is None:
            raise RuntimeError("Owned container identity absent")
        state["owned_postgres_id"] = cid
        subprocess.run(["docker", "start", cid], check=True, stdout=subprocess.DEVNULL, timeout=30)
        port = subprocess.check_output(["docker", "port", cid, "5432/tcp"], text=True, timeout=15).strip().rsplit(":", 1)[1]
        for _ in range(100):
            if subprocess.run(["docker", "exec", cid, "pg_isready", "-U", "postgres"], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=5).returncode == 0:
                break
            time.sleep(.2)
        else:
            raise RuntimeError("Owned PostgreSQL readiness timeout")
        env["ACTIONS_INVOICE_TEST_POSTGRES"] = "postgresql://postgres:" + password + "@127.0.0.1:" + port + "/postgres"
        write(out / "session.json", state)
        code, abort = run_process(gateway + ["--receipt", str(out / "test-preflight.json"),
            "--ignore=tests/action_server_tests/test_browser_origin_acceptance.py", "-m", "not native_artifact_test",
            "-q", "--maxfail=5", "--basetemp=" + str(out / "tmp"), "--junitxml=" + str(out / "junit.xml")],
            env, out / "pytest.log", 7200, 10 * GIB, (password, env["ACTIONS_INVOICE_TEST_POSTGRES"]))
        after = source_snapshot(args.source)
        state["source_after"] = after
        state.update(status="ABORTED" if abort else ("PASS" if passes_gate(code, abort, before, after, progress) else "FAILED"),
                     abort_reason=abort, pytest_returncode=code)
        if before != after or not after["worktree_clean"]:
            state["qualification_error"] = "postrun_source_changed_or_dirty"
            if not abort:
                state["status"] = "SOURCE_CHANGED"
        if code == 0 and summary(progress)["pytest_session_finish"] is None:
            state["qualification_error"] = "pytest_session_finish_missing"
        if (out / "test-preflight.json").exists():
            before = json.loads((out / "preflight.json").read_text())
            during = json.loads((out / "test-preflight.json").read_text())
            if before["source_tests_fingerprint"] != during["source_tests_fingerprint"]:
                state.update(status="SOURCE_CHANGED", abort_reason="preflight_source_changed")
        return 0 if state["status"] == "PASS" else 1
    except SupervisorStop as exc:
        state.update(status="ABORTED", abort_reason="external_" + signal.Signals(exc.signum).name,
                     requested_signal=signal.Signals(exc.signum).name)
        return 1
    except BaseException as exc:
        state.update(status="SUPERVISOR_FAILED", exception_type=type(exc).__name__)
        raise
    finally:
        # Cleanup is bounded internally; repeated external signals must not skip it.
        for sig in previous_handlers:
            signal.signal(sig, signal.SIG_IGN)
        if "source_before" in state and "source_after" not in state:
            try:
                state["source_after"] = source_snapshot(args.source)
            except Exception as exc:
                state["source_after_error"] = type(exc).__name__
        # Container cleanup is scoped to exactly the ID recorded by this create.
        # A timed-out create may already have persisted its ID: inspect it first.
        if cid is None and cidfile.exists():
            recorded = cidfile.read_text().strip()
            if re.fullmatch(r"[0-9a-f]{64}", recorded):
                cid = recorded
            else:
                state.update(status="CLEANUP_FAILED", owned_postgres_cleanup_error="InvalidCidfile")
        if cid is not None:
            try:
                subprocess.run(["docker", "stop", "--time", "5", cid], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                subprocess.run(["docker", "rm", cid], check=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=15)
                state["owned_postgres_stopped_removed"] = True
            except BaseException as exc:
                state["owned_postgres_cleanup_error"] = type(exc).__name__
                state["status"] = "CLEANUP_FAILED"
        state.update(summary(progress))
        write(out / "session.json", state)
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
        if libc.prctl(36, previous.value, 0, 0, 0) != 0:
            raise RuntimeError("Subreaper restoration failed")
        if state["status"] == "CLEANUP_FAILED":
            raise RuntimeError("Owned PostgreSQL cleanup failed")


if __name__ == "__main__":
    raise SystemExit(main())
