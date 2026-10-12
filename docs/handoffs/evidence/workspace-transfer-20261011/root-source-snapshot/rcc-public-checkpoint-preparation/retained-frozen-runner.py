#!/usr/bin/env python3
"""Bounded RCC local-ready env exec diagnostic; see adjacent proposal/receipt.

This script builds the exact minimal PR302 fixture through pinned RCC, stages
it across task-owned private homes A and B, then tests local-ready env exec.
It never installs or bootstraps developer dependencies or edits repository
source.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import http.server
import json
import os
from pathlib import Path
import queue
import re
import selectors
import signal
import subprocess
import sys
import threading
import time
from typing import Any
from urllib.parse import unquote, urlsplit


RCC = Path("/workspace/actions-cloud/bin/rcc")
RCC_SHA256 = "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428"
SUBJECT_HEAD = "4e8a26296608c232ce3dbd1f250ddb709b9459c9"
SUBJECT_TREE = "1b582dd02b367e5216e60796a8da031e520aa12f"
SUBJECT_ROOT = Path("/workspace/work/actions-mk3-rcc-warm-audit")
FIXTURE_SOURCE = SUBJECT_ROOT / "action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py"
FIXTURE_SOURCE_SHA256 = "2345704fa32e0d477a2f6b1c71be86e06a8de5e509e750d62098da22d0e808f9"
CANONICAL_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
OVERALL_SECONDS = 300.0
CLEANUP_RESERVE_SECONDS = 20.0
CHILD_SECONDS = 30.0
PUBLISH_SECONDS = 180.0
PROVIDER_START_SECONDS = 10.0
OUTPUT_TAIL_BYTES = 32 * 1024
PROBE_EVENT_RETAIN_LIMIT = 256
PR_SET_CHILD_SUBREAPER = 36
PROXY_ENV_NAMES = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
)
NO_PROXY_ENV_NAMES = ("NO_PROXY", "no_proxy")
CA_ENV_NAMES = (
    "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE", "PIP_CERT", "NODE_EXTRA_CA_CERTS",
)


def tail_append(current: bytearray, chunk: bytes) -> None:
    current.extend(chunk)
    if len(current) > OUTPUT_TAIL_BYTES:
        del current[: len(current) - OUTPUT_TAIL_BYTES]


def process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def enable_child_subreaper() -> None:
    """Adopt and reap orphaned descendants from the runner's owned groups."""
    if not sys.platform.startswith("linux"):
        raise RuntimeError("owned descendant reaping requires Linux PR_SET_CHILD_SUBREAPER")
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))


def reap_adopted_group_children(pgid: int) -> None:
    """Reap only adopted children whose process group is the owned group."""
    while True:
        try:
            child_pid, _status = os.waitpid(-pgid, os.WNOHANG)
        except ChildProcessError:
            return
        if child_pid == 0:
            return


def stop_process_group(
    process: subprocess.Popen[bytes], *, grace_seconds: float = 1.0,
    cleanup_deadline: float,
) -> bool:
    """Stop an owned group, reap its leader, then verify group absence."""
    pgid = process.pid
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.0, cleanup_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                return False
        if process.returncode is not None:
            reap_adopted_group_children(pgid)
        return True
    term_until = min(cleanup_deadline, time.monotonic() + grace_seconds)
    while time.monotonic() < term_until:
        process.poll()  # reap the group leader before checking whether its PID exists
        if process.returncode is not None:
            reap_adopted_group_children(pgid)
        if not process_group_exists(pgid):
            return True
        time.sleep(min(0.05, max(0.0, term_until - time.monotonic())))
    if process_group_exists(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    while time.monotonic() < cleanup_deadline:
        if process.poll() is None:
            remaining = cleanup_deadline - time.monotonic()
            try:
                process.wait(timeout=min(0.05, max(0.0, remaining)))
            except subprocess.TimeoutExpired:
                pass
        if process.returncode is not None:
            reap_adopted_group_children(pgid)
        if not process_group_exists(pgid):
            return True
        time.sleep(min(0.05, max(0.0, cleanup_deadline - time.monotonic())))
    return not process_group_exists(pgid)


def run_bounded(
    command: list[str], *, env: dict[str, str], deadline: float,
    cleanup_deadline: float, timeout_cap: float = CHILD_SECONDS,
) -> dict[str, Any]:
    """Run one child with process-group cleanup and bounded output tails."""
    started = time.monotonic()
    end = min(deadline, started + timeout_cap)
    process: subprocess.Popen[bytes] | None = None
    selector = selectors.DefaultSelector()
    stdout_tail = bytearray()
    stderr_tail = bytearray()
    timed_out = False
    spawn_error: str | None = None
    run_exception: str | None = None
    cleanup_errors: list[str] = []
    group_gone: bool | None = None
    try:
        if time.monotonic() >= end:
            return {
                "command": command,
                "spawn_error": "deadline expired before child spawn",
                "returncode": None,
                "timed_out": True,
                "stdout_tail": "",
                "stderr_tail": "",
                "stdout_truncated": False,
                "stderr_truncated": False,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "cleanup_errors": [],
            }
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=env.get("TMPDIR", "/tmp"),
                close_fds=True,
                start_new_session=True,
            )
        except OSError as exc:
            spawn_error = f"{type(exc).__name__}: {exc}"
            return {
                "command": command,
                "spawn_error": spawn_error,
                "returncode": None,
                "timed_out": False,
                "stdout_tail": "",
                "stderr_tail": "",
                "stdout_truncated": False,
                "stderr_truncated": False,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "cleanup_errors": [],
            }

        assert process.stdout is not None and process.stderr is not None
        for stream, sink in ((process.stdout, stdout_tail), (process.stderr, stderr_tail)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, sink)

        while selector.get_map() or process.poll() is None:
            remaining = end - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            selected = selector.select(min(0.1, remaining)) if selector.get_map() else []
            for key, _ in selected:
                try:
                    chunk = os.read(key.fd, 8192)
                except BlockingIOError:
                    continue
                if chunk:
                    tail_append(key.data, chunk)
                else:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
        if timed_out or process_group_exists(process.pid):
            if process.poll() is not None and not timed_out:
                cleanup_errors.append("child leader exited with owned descendants remaining")
            group_gone = stop_process_group(process, cleanup_deadline=cleanup_deadline)
            if not group_gone:
                cleanup_errors.append("owned process group remained after SIGKILL")
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.0, cleanup_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                cleanup_errors.append("child process did not reap after process-group cleanup")
        if group_gone is None:
            group_gone = not process_group_exists(process.pid)
    except BaseException as exc:
        run_exception = f"{type(exc).__name__}: {exc}"
        if process is not None:
            try:
                group_gone = stop_process_group(
                    process, grace_seconds=0.0, cleanup_deadline=cleanup_deadline
                )
                if not group_gone:
                    cleanup_errors.append("owned process group survived exception cleanup")
            except Exception as group_exc:
                cleanup_errors.append(f"process-group cleanup: {type(group_exc).__name__}: {group_exc}")
            try:
                process.wait(timeout=max(0.0, cleanup_deadline - time.monotonic()))
            except Exception as reap_exc:  # preserve cleanup and primary error
                cleanup_errors.append(f"reap: {type(reap_exc).__name__}: {reap_exc}")
            if group_gone is None:
                group_gone = not process_group_exists(process.pid)
    finally:
        selector.close()
        if process is not None:
            for stream in (process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()

    stdout = bytes(stdout_tail).decode("utf-8", errors="replace")
    stderr = bytes(stderr_tail).decode("utf-8", errors="replace")
    return {
        "command": command,
        "pid": process.pid if process is not None else None,
        "pgid": process.pid if process is not None else None,
        "returncode": process.returncode if process is not None else None,
        "timed_out": timed_out,
        "run_exception": run_exception,
        "stdout_tail": stdout,
        "stderr_tail": stderr,
        "stdout_truncated": len(stdout_tail) == OUTPUT_TAIL_BYTES,
        "stderr_truncated": len(stderr_tail) == OUTPUT_TAIL_BYTES,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "reaped": process is not None and process.returncode is not None,
        "process_group_gone": group_gone if process is not None else None,
        "cleanup_errors": cleanup_errors,
    }


def parse_digest(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    candidates: list[object] = []
    for name in ("artifact", "artifact_digest", "artifactDigest", "digest"):
        if name in payload:
            candidates.append(payload[name])
    artifact = payload.get("artifact")
    if isinstance(artifact, dict) and "digest" in artifact:
        candidates.append(artifact["digest"])
    env_artifact = payload.get("environment_artifact")
    if isinstance(env_artifact, dict) and "digest" in env_artifact:
        candidates.append(env_artifact["digest"])
    values = {candidate for candidate in candidates if isinstance(candidate, str)}
    if len(values) == 1:
        value = next(iter(values))
        return value if CANONICAL_DIGEST.fullmatch(value) else None
    return None


def json_result(result: dict[str, Any]) -> object | None:
    if (
        result.get("returncode") != 0
        or result.get("timed_out")
        or result.get("run_exception")
        or result.get("reaped") is not True
        or result.get("process_group_gone") is not True
        or result.get("cleanup_errors")
    ):
        return None
    try:
        return json.loads(result.get("stdout_tail", ""))
    except (json.JSONDecodeError, TypeError):
        return None


class RejectProbeHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._reject()

    def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._reject()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._reject()

    def do_PUT(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._reject()

    def do_DELETE(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._reject()

    def _reject(self) -> None:
        server = self.server
        assert isinstance(server, RejectProbeServer)
        with server.events_lock:
            server.event_total += 1
            if len(server.events) < PROBE_EVENT_RETAIN_LIMIT:
                server.events.append({
                    "sequence": server.event_total,
                    "method": self.command,
                    "path": self.path[:512],
                    "status": 503,
                    "monotonic": time.monotonic(),
                })
            else:
                server.event_truncated += 1
        body = b'{"error":"diagnostic provider unavailable"}'
        self.send_response(503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


class RejectProbeServer(http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port: int) -> None:
        super().__init__(("127.0.0.1", port), RejectProbeHandler)
        self.timeout = 0.2
        self.events: list[dict[str, Any]] = []
        self.event_total = 0
        self.event_truncated = 0
        self.events_lock = threading.Lock()

    def get_request(self) -> tuple[Any, Any]:
        request, client_address = super().get_request()
        request.settimeout(0.5)
        return request, client_address

    def event_mark(self) -> tuple[int, int]:
        with self.events_lock:
            return self.event_total, self.event_truncated

    def events_snapshot(self, mark: tuple[int, int]) -> dict[str, Any]:
        with self.events_lock:
            total_mark, truncated_mark = mark
            return {
                "total": self.event_total - total_mark,
                "retained": [event for event in self.events if event["sequence"] > total_mark],
                "truncated": self.event_truncated - truncated_mark,
            }


def safe_environment(
    task_root: Path, robocorp_home: Path, temp_dir: Path, xdg_root: Path
) -> dict[str, str]:
    allowed = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(temp_dir / "home"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "ROBOCORP_HOME": str(robocorp_home),
        "ACTIONS_HOME": str(robocorp_home),
        "TMPDIR": str(temp_dir),
        "XDG_CACHE_HOME": str(xdg_root / "cache"),
        "XDG_CONFIG_HOME": str(xdg_root / "config"),
        "XDG_DATA_HOME": str(xdg_root / "data"),
        "XDG_STATE_HOME": str(xdg_root / "state"),
        "RCC_HOLOTREE_MODE": "private",
        "PYTHONNOUSERSITE": "1",
    }
    for name in PROXY_ENV_NAMES + CA_ENV_NAMES:
        value = os.environ.get(name)
        if value is not None:
            allowed[name] = value
    for name, other_name in (("NO_PROXY", "no_proxy"), ("no_proxy", "NO_PROXY")):
        value = os.environ.get(name, os.environ.get(other_name, ""))
        entries = [entry.strip() for entry in value.split(",") if entry.strip()]
        for local_host in ("127.0.0.1", "localhost"):
            if local_host not in entries:
                entries.append(local_host)
        allowed[name] = ",".join(entries)
    return allowed


def environment_redaction_values(*environments: dict[str, str]) -> list[str]:
    values: set[str] = set()
    for environment in environments:
        for name in PROXY_ENV_NAMES + NO_PROXY_ENV_NAMES + CA_ENV_NAMES:
            value = environment.get(name)
            if value:
                values.add(value)
                if name in NO_PROXY_ENV_NAMES:
                    values.update(part.strip() for part in value.split(",") if part.strip())
            if name in PROXY_ENV_NAMES and value:
                try:
                    parts = urlsplit(value)
                    for part in (parts.netloc, parts.hostname, parts.username, parts.password):
                        if part:
                            values.add(part)
                            values.add(unquote(part))
                except ValueError:
                    pass
    return sorted(values, key=len, reverse=True)


def redact_text(value: str, redactions: list[str]) -> str:
    for secret in redactions:
        value = value.replace(secret, "<redacted-network-setting>")
    return value


def redact_record_strings(value: Any, redactions: list[str], parent_key: str = "") -> Any:
    """Redact inherited network settings from free-form persisted text only."""
    if isinstance(value, dict):
        return {
            key: redact_record_strings(item, redactions, str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_record_strings(item, redactions, parent_key) for item in value]
    if isinstance(value, str):
        if parent_key in {"path", "url", "digest", "artifactDigest", "artifact_digest"}:
            return value
        return redact_text(value, redactions)
    return value


class ServiceOutputPump:
    """Drain a long-lived service's pipes while retaining bounded tails."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process
        self.ready: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self.stdout_tail = bytearray()
        self.stderr_tail = bytearray()
        self.lock = threading.Lock()
        self.threads = [
            threading.Thread(
                target=self._drain,
                args=(process.stdout, self.stdout_tail, True),
                name="rcc-cache-stdout",
                daemon=True,
            ),
            threading.Thread(
                target=self._drain,
                args=(process.stderr, self.stderr_tail, False),
                name="rcc-cache-stderr",
                daemon=True,
            ),
        ]

    def start(self) -> None:
        for thread in self.threads:
            thread.start()

    def _drain(
        self,
        stream: Any,
        tail: bytearray,
        parse_ready: bool,
    ) -> None:
        if stream is None:
            return
        pending = bytearray()
        try:
            while True:
                chunk = stream.read1(8192)
                if not chunk:
                    break
                with self.lock:
                    tail_append(tail, chunk)
                if not parse_ready:
                    continue
                pending.extend(chunk)
                if len(pending) > 64 * 1024:
                    del pending[:-64 * 1024]
                while b"\n" in pending:
                    line, _, rest = pending.partition(b"\n")
                    pending = bytearray(rest)
                    try:
                        value = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if isinstance(value, dict) and isinstance(value.get("url"), str):
                        try:
                            self.ready.put_nowait(value)
                        except queue.Full:
                            pass
        except (OSError, ValueError):
            return

    def tails(self) -> dict[str, str]:
        with self.lock:
            return {
                "stdout_tail": bytes(self.stdout_tail).decode("utf-8", errors="replace"),
                "stderr_tail": bytes(self.stderr_tail).decode("utf-8", errors="replace"),
            }

    def join(self, cleanup_deadline: float) -> bool:
        for thread in self.threads:
            thread.join(timeout=max(0.0, cleanup_deadline - time.monotonic()))
        return all(not thread.is_alive() for thread in self.threads)


def stop_owned_process(
    process: subprocess.Popen[bytes] | None, *, cleanup_deadline: float
) -> dict[str, Any]:
    if process is None:
        return {"created": False, "reaped": True, "process_group_gone": True, "errors": []}
    errors: list[str] = []
    group_gone = False
    try:
        group_gone = stop_process_group(
            process, grace_seconds=2.0, cleanup_deadline=cleanup_deadline
        )
    except Exception as exc:
        errors.append(f"process-group stop: {type(exc).__name__}: {exc}")
    try:
        if process.poll() is None:
            process.wait(timeout=max(0.0, cleanup_deadline - time.monotonic()))
    except Exception as exc:
        errors.append(f"owned service leader reap: {type(exc).__name__}: {exc}")
    try:
        if process.poll() is None:
            process.wait(timeout=max(0.0, cleanup_deadline - time.monotonic()))
        group_gone = group_gone and not process_group_exists(process.pid)
    except Exception as exc:
        errors.append(f"process-group verification: {type(exc).__name__}: {exc}")
    if not group_gone:
        errors.append("owned service process group remained after SIGKILL")
    return {
        "created": True,
        "pid": process.pid,
        "returncode": process.returncode,
        "reaped": process.returncode is not None,
        "process_group_gone": group_gone,
        "errors": errors,
    }


def verify_subject_checkout() -> dict[str, Any]:
    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(SUBJECT_ROOT), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=3.0,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"},
        )
        return completed.stdout.decode("utf-8").strip()

    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    status = git("status", "--porcelain", "--untracked-files=all")
    fixture_hash = hashlib.sha256(FIXTURE_SOURCE.read_bytes()).hexdigest()
    if head != SUBJECT_HEAD or tree != SUBJECT_TREE or status:
        raise RuntimeError("subject checkout identity or cleanliness changed")
    if fixture_hash != FIXTURE_SOURCE_SHA256:
        raise RuntimeError("accepted source fixture hash changed")
    return {
        "root": str(SUBJECT_ROOT), "head": head, "tree": tree,
        "clean": not status, "fixture_source": str(FIXTURE_SOURCE),
        "fixture_source_sha256": fixture_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    task_root = args.task_root.resolve()
    receipt_path = args.receipt.resolve()
    started = time.monotonic()
    deadline = started + OVERALL_SECONDS
    work_deadline = deadline - CLEANUP_RESERVE_SECONDS
    manifest = (
        b"version: 0.1\nspec-version: v2\ndependencies:\n"
        b"  conda-forge:\n    - python=3.12.15\n"
        b"  pypi:\n    - actions-core=1.0.2\n"
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "purpose": "bounded RCC A-to-B local-ready env exec provider comparison",
        "source": {"head": SUBJECT_HEAD, "tree": SUBJECT_TREE},
        "rcc": {"path": str(RCC), "sha256": RCC_SHA256, "version": "v18.19.3"},
        "limits": {
            "overall_seconds": OVERALL_SECONDS,
            "work_deadline_seconds": OVERALL_SECONDS - CLEANUP_RESERVE_SECONDS,
            "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "per_child_seconds": CHILD_SECONDS,
            "producer_publish_seconds": PUBLISH_SECONDS,
            "provider_start_seconds": PROVIDER_START_SECONDS,
            "output_tail_bytes_per_stream": OUTPUT_TAIL_BYTES,
            "concurrent_children": 1,
            "linux_child_subreaper": True,
        },
        "fixture": {
            "origin": "PR302 accepted staged RCC consumer test fixture",
            "python_pin": "3.12.15",
            "package_yaml_sha256": hashlib.sha256(manifest).hexdigest(),
            "dependencies": [
                "conda-forge: python=3.12.15",
                "pypi: actions-core=1.0.2",
            ],
        },
        "commands": {},
        "exec_cases": {},
        "cleanup": {},
        "status": "NOT_RUN",
    }
    exit_code = 1
    if task_root.exists():
        print("refusing to reuse an existing task root", file=sys.stderr)
        return 2
    if os.path.commonpath(
        ("/workspace/work/actions-mk3-evidence/rcc-warm-readiness", str(task_root))
    ) != "/workspace/work/actions-mk3-evidence/rcc-warm-readiness":
        print("task root must be under the RCC warm-readiness scratch directory", file=sys.stderr)
        return 2
    task_root.mkdir(mode=0o700, parents=True)
    receipt_path_valid = False
    network_redactions: list[str] = []
    service_process: subprocess.Popen[bytes] | None = None
    service_pump: ServiceOutputPump | None = None
    service_stopped = False
    probe: RejectProbeServer | None = None
    probe_thread: threading.Thread | None = None
    probe_started = threading.Event()

    try:
        if os.path.commonpath((str(task_root.parent), str(receipt_path))) != str(task_root.parent):
            raise ValueError("receipt path must remain under the task scratch directory")
        if os.path.commonpath((str(task_root), str(receipt_path))) != str(task_root):
            raise ValueError("receipt must be written beneath this unique task root")
        if receipt_path.exists():
            raise FileExistsError("refusing to overwrite an existing receipt")
        receipt_path_valid = True
        if not RCC.is_file() or not os.access(RCC, os.X_OK):
            raise FileNotFoundError(f"pinned RCC binary unavailable: {RCC}")
        binary_hash = hashlib.sha256(RCC.read_bytes()).hexdigest()
        if binary_hash != RCC_SHA256:
            raise RuntimeError("pinned RCC binary hash mismatch")
        if time.monotonic() >= work_deadline:
            raise TimeoutError("work deadline expired during preflight")
        enable_child_subreaper()
        record["cleanup_policy"] = {
            "linux_child_subreaper_enabled": True,
            "adopted_descendants_reaped_by_owned_process_group": True,
            "escaped_process_groups_contained": False,
        }

        dirs = {
            "producer_home": task_root / "producer-home",
            "consumer_home": task_root / "consumer-home",
            "producer_tmp": task_root / "producer-tmp",
            "consumer_tmp": task_root / "consumer-tmp",
            "provider_root": task_root / "provider-root",
            "package_dir": task_root / "minimal-package",
        }
        for path in dirs.values():
            path.mkdir(mode=0o700)
        (dirs["producer_tmp"] / "home").mkdir(mode=0o700)
        (dirs["consumer_tmp"] / "home").mkdir(mode=0o700)
        for name in ("producer_xdg", "consumer_xdg"):
            dirs[name] = task_root / name
            dirs[name].mkdir(mode=0o700)
            for child in ("cache", "config", "data", "state"):
                (dirs[name] / child).mkdir(mode=0o700)
        environment_file = dirs["package_dir"] / "package.yaml"
        environment_file.write_bytes(manifest)
        producer_env = safe_environment(
            task_root, dirs["producer_home"], dirs["producer_tmp"], dirs["producer_xdg"]
        )
        consumer_env = safe_environment(
            task_root, dirs["consumer_home"], dirs["consumer_tmp"], dirs["consumer_xdg"]
        )
        network_redactions = environment_redaction_values(producer_env, consumer_env)
        record["source"] = verify_subject_checkout()
        record["execution_context"] = {
            "subject_checkout_inspection_root": str(SUBJECT_ROOT),
            "producer_child_cwd": str(dirs["producer_tmp"]),
            "consumer_child_cwd": str(dirs["consumer_tmp"]),
            "service_child_cwd": str(task_root),
            "producer_home": producer_env["HOME"],
            "consumer_home": consumer_env["HOME"],
            "producer_xdg": str(dirs["producer_xdg"]),
            "consumer_xdg": str(dirs["consumer_xdg"]),
            "network_environment_variable_names": {
                "proxy": [name for name in PROXY_ENV_NAMES if name in producer_env],
                "no_proxy": [name for name in NO_PROXY_ENV_NAMES if name in producer_env],
                "ca_trust": [name for name in CA_ENV_NAMES if name in producer_env],
            },
        }

        # Start one owned random-port provider. Drain stdout/stderr in bounded
        # background readers so neither pipe can block the publisher.
        service_command = [
            str(RCC), "cache", "serve", "--root", str(dirs["provider_root"]),
            "--listen", "127.0.0.1:0", "--backend", "filesystem", "--json",
        ]
        service_process = subprocess.Popen(
            service_command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=producer_env,
            cwd=task_root,
            close_fds=True,
            start_new_session=True,
        )
        service_pump = ServiceOutputPump(service_process)
        service_pump.start()
        service_json: dict[str, Any] | None = None
        startup_deadline = min(work_deadline, time.monotonic() + PROVIDER_START_SECONDS)
        while time.monotonic() < startup_deadline:
            try:
                service_json = service_pump.ready.get(timeout=0.1)
                break
            except queue.Empty:
                if service_process.poll() is not None:
                    break
        if not isinstance(service_json, dict):
            raise RuntimeError("task-owned cache service failed to emit startup JSON")
        provider_url = service_json.get("url")
        if not isinstance(provider_url, str):
            raise RuntimeError("cache service startup JSON lacks provider URL")
        provider_parts = urlsplit(provider_url)
        if (
            provider_parts.scheme != "http"
            or provider_parts.hostname != "127.0.0.1"
            or provider_parts.port is None
            or provider_parts.username is not None
            or provider_parts.password is not None
            or provider_parts.path not in ("", "/")
            or provider_parts.query
            or provider_parts.fragment
        ):
            raise RuntimeError("cache service returned a non-root/non-loopback URL")
        provider_port = provider_parts.port
        announced_root = service_json.get("root")
        if announced_root is not None and Path(str(announced_root)).resolve() != dirs["provider_root"].resolve():
            raise RuntimeError("cache service startup root differs from owned provider root")
        record["provider"] = {
            "url": provider_url,
            "port": provider_port,
            "root": str(dirs["provider_root"]),
            "startup": service_json,
            "pid": service_process.pid,
        }

        publish_command = [
            str(RCC), "env", "publish", "--environment", str(environment_file),
            "--json", "--provider", provider_url,
        ]
        publish_result = run_bounded(
            publish_command, env=producer_env, deadline=work_deadline,
            cleanup_deadline=deadline, timeout_cap=PUBLISH_SECONDS,
        )
        publish_payload = json_result(publish_result)
        artifact_digest = parse_digest(publish_payload)
        record["commands"]["publish_A"] = {
            **publish_result,
            "artifact_digest": artifact_digest,
            "passed": (
                publish_result.get("returncode") == 0
                and artifact_digest is not None
            ),
        }
        if not record["commands"]["publish_A"]["passed"]:
            raise RuntimeError("producer A did not publish a canonical Artifact")
        record["artifact_digest"] = artifact_digest

        acquire_command = [
            str(RCC), "env", "acquire", "--artifact", artifact_digest,
            "--json", "--permissive-local", "--provider", provider_url,
        ]
        acquire_result = run_bounded(
            acquire_command, env=consumer_env, deadline=work_deadline,
            cleanup_deadline=deadline, timeout_cap=30.0,
        )
        acquire_payload = json_result(acquire_result)
        acquire_ok = (
            acquire_result.get("returncode") == 0
            and parse_digest(acquire_payload) == artifact_digest
            and isinstance(acquire_payload, dict)
            and isinstance(acquire_payload.get("verification"), dict)
            and acquire_payload["verification"].get("valid") is True
            and isinstance(acquire_payload.get("path"), str)
            and Path(acquire_payload["path"]).resolve().is_relative_to(dirs["consumer_home"].resolve())
        )
        record["commands"]["acquire_B"] = {
            **acquire_result,
            "returned_digest": parse_digest(acquire_payload),
            "verification_valid": (
                acquire_payload.get("verification", {}).get("valid")
                if isinstance(acquire_payload, dict)
                and isinstance(acquire_payload.get("verification"), dict)
                else None
            ),
            "passed": acquire_ok,
        }
        if not acquire_ok:
            raise RuntimeError("consumer B did not acquire and verify exact Artifact")

        # Independently prove B's already-local materialization before taking
        # the provider offline and before comparing exec flag behavior.
        local_acquire = [
            str(RCC), "env", "acquire", "--artifact", artifact_digest,
            "--json", "--permissive-local",
        ]
        local_result = run_bounded(
            local_acquire, env=consumer_env, deadline=work_deadline,
            cleanup_deadline=deadline, timeout_cap=20.0,
        )
        local_payload = json_result(local_result)
        local_ok = (
            local_result.get("returncode") == 0
            and parse_digest(local_payload) == artifact_digest
            and isinstance(local_payload, dict)
            and isinstance(local_payload.get("verification"), dict)
            and local_payload["verification"].get("valid") is True
            and local_payload.get("cacheHit") == "local-materialization"
            and isinstance(local_payload.get("path"), str)
            and Path(local_payload["path"]).resolve().is_relative_to(dirs["consumer_home"].resolve())
        )
        record["commands"]["provider_free_acquire_B"] = {
            **local_result,
            "returned_digest": parse_digest(local_payload),
            "verification_valid": (
                local_payload.get("verification", {}).get("valid")
                if isinstance(local_payload, dict)
                and isinstance(local_payload.get("verification"), dict)
                else None
            ),
            "passed": local_ok,
        }
        if not local_ok:
            raise RuntimeError("B did not independently verify exact local Artifact")

        for action in ("inspect", "verify"):
            command = [
                str(RCC), "env", "lifecycle", action,
                "--artifact", artifact_digest, "--json",
            ]
            result = run_bounded(
                command, env=consumer_env, deadline=work_deadline,
                cleanup_deadline=deadline, timeout_cap=10.0,
            )
            payload = json_result(result)
            reported_digest = parse_digest(payload)
            passed = (
                result.get("returncode") == 0
                and isinstance(payload, dict)
                and reported_digest == artifact_digest
            )
            if action == "inspect":
                passed = (
                    passed and payload.get("ready") is True
                    and payload.get("state") == "ready"
                    and isinstance(payload.get("path"), str)
                    and Path(payload["path"]).resolve().is_relative_to(dirs["consumer_home"].resolve())
                )
            else:
                passed = passed and payload.get("verified") is True
            record["commands"][f"lifecycle_{action}_B"] = {
                **result,
                "reported_digest": reported_digest,
                "ready": payload.get("ready") if isinstance(payload, dict) else None,
                "state": payload.get("state") if isinstance(payload, dict) else None,
                "path": payload.get("path") if isinstance(payload, dict) else None,
                "verified": payload.get("verified") if isinstance(payload, dict) else None,
                "passed": passed,
            }
            if not passed:
                raise RuntimeError(f"consumer B lifecycle {action} did not pass")

        service_cleanup = stop_owned_process(service_process, cleanup_deadline=deadline)
        record["cleanup"]["provider_service"] = service_cleanup
        service_stopped = True
        if (not service_cleanup.get("reaped") or service_cleanup.get("errors")
                or not service_cleanup.get("process_group_gone")):
            raise RuntimeError("provider service did not cleanly stop before probe")
        if service_pump is not None:
            record["cleanup"]["provider_output_threads_stopped"] = service_pump.join(deadline)
            record["provider"]["logs"] = service_pump.tails()
            if not record["cleanup"]["provider_output_threads_stopped"]:
                raise RuntimeError("provider output drain threads did not stop")

        # Rebind the exact random port chosen by RCC cache serve. This rejecting
        # probe cannot serve artifact/trust objects.
        probe = RejectProbeServer(provider_port)
        probe_url = provider_url
        def serve_probe() -> None:
            probe_started.set()
            probe.serve_forever(poll_interval=0.05)

        probe_thread = threading.Thread(
            target=serve_probe,
            name="rcc-local-ready-reject-probe",
            daemon=True,
        )
        probe_thread.start()
        if not probe_started.wait(timeout=1.0):
            raise RuntimeError("rejecting provider probe thread did not start")
        record["probe"] = {
            "url": probe_url,
            "bind": "127.0.0.1",
            "port": provider_port,
            "role": "count-and-reject only; cannot serve artifact/trust data",
            "server_pid": os.getpid(),
        }

        for name, include_provider in (("with_provider", True), ("provider_omitted", False)):
            receipt = task_root / f"exec-{name}.json"
            if receipt.exists():
                raise FileExistsError(f"refusing to overwrite {receipt.name}")
            command = [
                str(RCC), "env", "exec",
                "--artifact", artifact_digest,
            ]
            if include_provider:
                command.extend(["--provider", probe_url])
            probe_mark = probe.event_mark()
            python_snippet = (
                "import json,sys;print('RCC_DIAG_PYTHON='+json.dumps({"
                "'executable':sys.executable,'prefix':sys.prefix,'version':list(sys.version_info[:3])}))"
            )
            command.extend(
                [
                    "--permissive-local",
                    "--inherit-streams",
                    "--receipt-file", str(receipt),
                    "--",
                    "python",
                    "-c",
                    python_snippet,
                ]
            )
            result = run_bounded(
                command, env=consumer_env, deadline=work_deadline,
                cleanup_deadline=deadline, timeout_cap=20.0
            )
            events = probe.events_snapshot(probe_mark)
            execution_receipt: object | None = None
            receipt_error = None
            if receipt.is_file():
                try:
                    if receipt.stat().st_size <= 1024 * 1024:
                        execution_receipt = json.loads(receipt.read_text(encoding="utf-8"))
                    else:
                        receipt_error = "execution receipt exceeds 1 MiB cap"
                except (OSError, json.JSONDecodeError) as exc:
                    receipt_error = f"{type(exc).__name__}: {exc}"
            result_valid = (
                isinstance(execution_receipt, dict)
                and execution_receipt.get("status") == "completed"
                and type(execution_receipt.get("exitCode")) is int
                and execution_receipt.get("exitCode") == 0
                and execution_receipt.get("artifactDigest") == artifact_digest
                and execution_receipt.get("cacheHit") == "local-materialization"
                and isinstance(execution_receipt.get("path"), str)
                and Path(execution_receipt["path"]).resolve().is_relative_to(dirs["consumer_home"].resolve())
                and isinstance(execution_receipt.get("verification"), dict)
                and execution_receipt["verification"].get("valid") is True
            )
            marker_prefix = "RCC_DIAG_PYTHON="
            python_identity: dict[str, Any] | None = None
            for output_line in result.get("stdout_tail", "").splitlines():
                if output_line.startswith(marker_prefix):
                    try:
                        python_identity = json.loads(output_line[len(marker_prefix):])
                    except json.JSONDecodeError:
                        pass
            materialization = execution_receipt.get("path") if isinstance(execution_receipt, dict) else None
            python_ok = (
                isinstance(python_identity, dict)
                and python_identity.get("version") == [3, 12, 15]
                and isinstance(python_identity.get("executable"), str)
                and isinstance(materialization, str)
                and Path(python_identity["executable"]).resolve().is_relative_to(Path(materialization).resolve())
            )
            record["exec_cases"][name] = {
                **result,
                "provider_argument_included": include_provider,
                "provider_requests": events["retained"],
                "provider_request_count": events["total"],
                "provider_request_events_truncated": events["truncated"],
                "execution_receipt": execution_receipt,
                "execution_receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest() if receipt.is_file() else None,
                "execution_receipt_error": receipt_error,
                "execution_receipt_valid_success": result_valid,
                "python_identity": python_identity,
                "python_identity_valid": python_ok,
                "child_marker_observed": python_identity is not None,
                "case_passed": (
                    result.get("returncode") == 0
                    and not result.get("timed_out")
                    and result.get("run_exception") is None
                    and result.get("reaped") is True
                    and result.get("process_group_gone") is True
                    and not result.get("cleanup_errors")
                    and result_valid
                    and python_ok
                ),
            }
            if time.monotonic() >= work_deadline:
                raise TimeoutError("work deadline exceeded before cleanup reserve")

        with_provider = record["exec_cases"]["with_provider"]
        omitted = record["exec_cases"]["provider_omitted"]
        if (with_provider["case_passed"] and with_provider["provider_request_count"] == 0
                and omitted["case_passed"] and omitted["provider_request_count"] == 0):
            outcome = "both_modes_local_ready_success_no_provider_request"
        elif not with_provider["case_passed"] and with_provider["provider_request_count"] > 0 and omitted["case_passed"] and omitted["provider_request_count"] == 0:
            outcome = "provider_option_path_differs_from_local_only_control"
        else:
            outcome = "other_or_fixture_failure_review_receipt"
        record["diagnostic_outcome"] = outcome
        record["status"] = "COMPLETE_DIAGNOSTIC"
        exit_code = 0
    except BaseException as exc:
        record["fatal"] = f"{type(exc).__name__}: {exc}"
        record["status"] = "PREFLIGHT_OR_RUN_FAILURE"
    finally:
        if service_process is not None and not service_stopped:
            try:
                record["cleanup"]["provider_service"] = stop_owned_process(
                    service_process, cleanup_deadline=deadline
                )
            except Exception as exc:
                record["cleanup"]["provider_service"] = {
                    "created": True, "pid": service_process.pid,
                    "cleanup_exception": f"{type(exc).__name__}: {exc}",
                    "reaped": service_process.returncode is not None,
                    "process_group_gone": False,
                }
            try:
                if service_pump is not None:
                    record["cleanup"]["provider_output_threads_stopped"] = service_pump.join(deadline)
                    record.setdefault("provider", {})["logs"] = service_pump.tails()
            except Exception as exc:
                record["cleanup"]["provider_output_threads_stopped"] = False
                record["cleanup"]["provider_output_error"] = f"{type(exc).__name__}: {exc}"
            if (not record["cleanup"]["provider_service"].get("reaped")
                    or record["cleanup"]["provider_service"].get("errors")
                    or not record["cleanup"]["provider_service"].get("process_group_gone")
                    or not record["cleanup"].get("provider_output_threads_stopped", True)):
                exit_code = 1
        if probe is not None:
            try:
                if probe_started.is_set():
                    shutdown_done = threading.Event()

                    def shutdown_probe() -> None:
                        try:
                            probe.shutdown()
                        finally:
                            shutdown_done.set()

                    shutdown_thread = threading.Thread(
                        target=shutdown_probe,
                        name="rcc-probe-shutdown",
                        daemon=True,
                    )
                    shutdown_thread.start()
                    shutdown_thread.join(timeout=max(0.0, deadline - time.monotonic()))
                    if shutdown_thread.is_alive() or not shutdown_done.is_set():
                        raise TimeoutError("reject probe shutdown exceeded remaining cleanup deadline")
                probe.server_close()
                record["cleanup"]["probe_shutdown"] = True
            except Exception as exc:
                record["cleanup"]["probe_shutdown_error"] = f"{type(exc).__name__}: {exc}"
                exit_code = 1
        if probe_thread is not None:
            probe_thread.join(timeout=max(0.0, deadline - time.monotonic()))
            record["cleanup"]["probe_thread_stopped"] = not probe_thread.is_alive()
            if probe_thread.is_alive():
                exit_code = 1
        record["cleanup"]["child_processes_reaped"] = all(
            item.get("reaped") is True and item.get("process_group_gone") is True
            and not item.get("cleanup_errors") and not item.get("run_exception")
            for item in record["commands"].values()
        ) and all(
            item.get("reaped") is True and item.get("process_group_gone") is True
            and not item.get("cleanup_errors") and not item.get("run_exception")
            for item in record["exec_cases"].values()
        )
        if not record["cleanup"]["child_processes_reaped"]:
            exit_code = 1
        record["cleanup"]["all_owned_processes_reaped"] = (
            record["cleanup"].get("child_processes_reaped") is True
            and record["cleanup"].get("provider_service", {}).get("reaped", True) is True
            and not record["cleanup"].get("provider_service", {}).get("errors", [])
            and record["cleanup"].get("provider_service", {}).get("process_group_gone", True) is True
            and record["cleanup"].get("probe_thread_stopped", True) is True
        )
        if not record["cleanup"]["all_owned_processes_reaped"]:
            exit_code = 1
        if exit_code != 0 and record.get("status") == "COMPLETE_DIAGNOSTIC":
            record["status"] = "CLEANUP_FAILED"
        if exit_code != 0 and record["status"] == "COMPLETE_DIAGNOSTIC":
            record["status"] = "CLEANUP_FAILED"
        record["duration_ms"] = round((time.monotonic() - started) * 1000)
        # Remove task-local paths and loopback URLs from bounded output tails.
        replacements = {
            str(task_root): "<task-root>",
            str(task_root / "producer-home"): "<producer-home>",
            str(task_root / "consumer-home"): "<consumer-home>",
            (record.get("probe") or {}).get("url", ""): "<reject-probe>",
        }
        for group in (record["commands"], record["exec_cases"]):
            for result in group.values():
                for field in ("stdout_tail", "stderr_tail"):
                    value = result.get(field)
                    if isinstance(value, str):
                        value = redact_text(value, network_redactions)
                        for original, replacement in replacements.items():
                            if original:
                                value = value.replace(original, replacement)
                        result[field] = value[-OUTPUT_TAIL_BYTES:]
        provider_service = record.get("cleanup", {}).get("provider_service", {})
        for field in ("stdout_tail", "stderr_tail"):
            value = provider_service.get(field)
            if isinstance(value, str):
                provider_service[field] = redact_text(value, network_redactions)[-OUTPUT_TAIL_BYTES:]
        provider_logs = record.get("provider", {}).get("logs", {})
        for field in ("stdout_tail", "stderr_tail"):
            value = provider_logs.get(field)
            if isinstance(value, str):
                provider_logs[field] = redact_text(value, network_redactions)[-OUTPUT_TAIL_BYTES:]
        record = redact_record_strings(record, network_redactions)
        try:
            if not receipt_path_valid:
                raise ValueError("receipt path was not validated beneath task root")
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = receipt_path.with_name(receipt_path.name + ".tmp")
            temporary.write_text(
                json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            os.replace(temporary, receipt_path)
        except Exception as exc:
            print(f"unable to persist receipt: {type(exc).__name__}: {exc}", file=sys.stderr)
            exit_code = 1
    print(json.dumps({"status": record["status"], "receipt": str(receipt_path)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
