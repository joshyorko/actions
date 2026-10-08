"""Run synthetic browser/storage acceptance against frozen and Go-wrapped Runtime.

Requires the declared frontend Playwright dependency and its installed Chromium.
Only a small, credential-free JSON receipt is retained; temporary data and logs
are removed on both success and failure. This does not execute Work Item workers.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import re
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

PACKAGE = Path(__file__).resolve().parents[1]
BROWSER_SCRIPT = PACKAGE / "frontend" / "scripts" / "native-browser-acceptance.mjs"


class AcceptanceFailure(Exception):
    """A bounded phase label, never a raw response, subprocess log or credential."""

    diagnostics: dict | None = None


def require(condition: bool, phase: str) -> None:
    if not condition:
        raise AcceptanceFailure(phase)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _wait_for_job_drain(
    active_process_count: Callable[[], int], *, timeout: float
) -> None:
    """Wait a bounded time for every process assigned to a Windows Job to exit."""
    require(0 < timeout <= 300, "windows_job_drain_timeout_range")
    deadline = time.monotonic() + timeout
    while True:
        active = active_process_count()
        require(isinstance(active, int) and active >= 0, "windows_job_process_count")
        if active == 0:
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AcceptanceFailure("windows_job_drain_timeout")
        time.sleep(min(0.05, remaining))


class _WindowsJob:
    """An un-inherited Job handle kills every assigned descendant when closed."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [
                (name, ctypes.c_ulonglong)
                for name in (
                    "ReadOperationCount",
                    "WriteOperationCount",
                    "OtherOperationCount",
                    "ReadTransferCount",
                    "WriteTransferCount",
                    "OtherTransferCount",
                )
            ]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimits),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        class BasicAccounting(ctypes.Structure):
            _fields_ = [
                ("TotalUserTime", ctypes.c_longlong),
                ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wintypes.DWORD),
                ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD),
                ("TotalTerminatedProcesses", wintypes.DWORD),
            ]

        kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel.SetInformationJobObject.restype = wintypes.BOOL
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.TerminateJobObject.restype = wintypes.BOOL
        kernel.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel.QueryInformationJobObject.restype = wintypes.BOOL
        self._kernel = kernel
        self._ctypes = ctypes
        self._basic_accounting = BasicAccounting
        self._handle = kernel.CreateJobObjectW(None, None)
        require(bool(self._handle), "windows_job_create")
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(
            self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            self.close()
            raise AcceptanceFailure("windows_job_limits")

    def assign(self, pid: int) -> None:
        # PROCESS_SET_QUOTA | PROCESS_TERMINATE, as required by assignment.
        handle = self._kernel.OpenProcess(0x0100 | 0x0001, False, pid)
        require(bool(handle), "windows_job_open_process")
        try:
            require(
                bool(self._kernel.AssignProcessToJobObject(self._handle, handle)),
                "windows_job_assign",
            )
        finally:
            self._kernel.CloseHandle(handle)

    def close(self) -> None:
        if self._handle:
            handle, self._handle = self._handle, None
            require(bool(self._kernel.CloseHandle(handle)), "windows_job_close")

    def active_process_count(self) -> int:
        require(bool(self._handle), "windows_job_closed")
        result = self._basic_accounting()
        if not self._kernel.QueryInformationJobObject(
            self._handle,
            1,  # JobObjectBasicAccountingInformation
            self._ctypes.byref(result),
            self._ctypes.sizeof(result),
            None,
        ):
            raise AcceptanceFailure("windows_job_query")
        return result.ActiveProcesses

    def terminate_and_wait(self, *, timeout: float = 10) -> None:
        """Terminate owned processes and observe the Job reaching zero before cleanup."""
        if self.active_process_count() == 0:
            return
        if not self._kernel.TerminateJobObject(self._handle, 1):
            raise AcceptanceFailure("windows_job_terminate")
        _wait_for_job_drain(self.active_process_count, timeout=timeout)


def _owned_child(command: list[str]) -> int:
    """Wait without buffering beyond the three-byte gate, then inherit the Job."""
    if os.name == "nt":
        import msvcrt

        getattr(msvcrt, "setmode")(sys.stdin.fileno(), getattr(os, "O_BINARY"))
    gate = b""
    while len(gate) < 3:
        chunk = os.read(sys.stdin.fileno(), 3 - len(gate))
        if not chunk:
            return 125
        gate += chunk
    if gate != b"GO\n" or not command:
        return 125
    # No shell and no breakaway flag: the actual command inherits Job membership
    # and the remaining stdin stream (including the browser JSON payload).
    return subprocess.call(command)


@contextlib.contextmanager
def owned_process(command: list[str], *, cwd: Path, env: dict[str, str], **kwargs):
    """Own a process tree, not a process-name pattern or unrelated runner process."""
    if os.name == "nt":
        requested_stdin = kwargs.pop("stdin", None)
        require(requested_stdin in (None, subprocess.PIPE), "windows_owned_stdin")
        job = _WindowsJob()
        process = None
        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--owned-child",
                    *command,
                ],
                cwd=cwd,
                env=env,
                stdin=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP"),
                **kwargs,
            )
            # The Python wrapper cannot spawn the real command until assigned.
            job.assign(process.pid)
            assert process.stdin is not None  # Popen was explicitly given PIPE.
            stream = (
                getattr(process.stdin, "buffer")
                if kwargs.get("text")
                else process.stdin
            )
            stream.write(b"GO\n")
            stream.flush()
            if requested_stdin is None:
                process.stdin.close()
                process.stdin = None
            yield process
        finally:
            try:
                # Kill-on-job-close is asynchronous: wait for the full tree before
                # TemporaryDirectory and log cleanup can remove their resources.
                try:
                    job.terminate_and_wait(timeout=10)
                finally:
                    job.close()
            finally:
                if process is not None:
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    if process.stdin is not None:
                        process.stdin.close()
        return

    process = subprocess.Popen(
        command, cwd=cwd, env=env, start_new_session=True, **kwargs
    )
    try:
        yield process
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        finally:
            # The leader can exit while an owned Chromium/Runtime child remains.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)


def run_output(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    input_text: str | None = None,
) -> tuple[int, str]:
    with owned_process(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ) as process:
        try:
            stdout, _ = process.communicate(input=input_text, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise AcceptanceFailure("subprocess_timeout") from error
        require(len(stdout) <= 65536, "subprocess_output_limit")
        return process.returncode, stdout


def startup_diagnostics(log: Path, exit_code: int, key: str) -> dict:
    """Extract bounded exception identifiers; never retain raw log/message text."""
    tails = []
    for source in (log, log.parent / "server_log.txt"):
        if not source.is_file():
            continue
        with source.open("rb") as stream:
            stream.seek(max(0, source.stat().st_size - 65536))
            text = stream.read(65536).decode("utf-8", errors="replace")
        # Strip ANSI before recognition, then remove credentials before extracting
        # identifiers. Never retain arbitrary message text or traceback source lines.
        text = re.sub(r"(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]", "", text)
        text = text.replace(key, "[redacted]")
        text = re.sub(
            r"(?im)^.*(?:authorization|cookie|api[_-]?key)\s*[:=].*$", "", text
        )
        tails.append(text)
    tail = "\n".join(tails)
    classes = re.findall(r"\b([A-Za-z_][A-Za-z_0-9]{0,190}(?:Error|Exception)):", tail)
    modules = re.findall(
        r"\bModuleNotFoundError: No module named ['\"]([A-Za-z_][A-Za-z_0-9.]*)['\"]",
        tail,
    )
    modules += re.findall(
        r"\bImportError: .* from ['\"]([A-Za-z_][A-Za-z_0-9.]*)['\"]", tail
    )
    frames = re.findall(
        r'File "[^"\r\n]*?([A-Za-z_][A-Za-z_0-9]*\.py)", line ([0-9]{1,7}), in ([A-Za-z_][A-Za-z_0-9]*|<module>)',
        tail,
    )
    markers = {
        "pyinstaller_unhandled_exception": "Failed to execute script",
        "python_traceback": "Traceback (most recent call last)",
        "database_creation": "Database file does not exist. Creating it",
        "application_startup_failed": "Application startup failed",
        "address_in_use": "address already in use",
        "windows_socket_access_denied": "WinError 10013",
        "invalid_windows_handle": "WinError 6",
        "permission_denied": "Permission denied",
        "argument_error": "error: unrecognized arguments",
        "rcc_download": "Downloading rcc",
    }
    return {
        "exit_code": exit_code,
        "exception_classes": list(dict.fromkeys(classes))[-8:],
        "import_modules": [name for name in dict.fromkeys(modules) if len(name) <= 200][
            -8:
        ],
        "traceback_frames": [
            {"file": file, "line": int(line), "function": function}
            for file, line, function in list(dict.fromkeys(frames))[-12:]
        ],
        "markers": [name for name, phrase in markers.items() if phrase in tail],
        "log_sources_present": len(tails),
    }


class NativeServer:
    def __init__(
        self,
        binary: Path,
        project: Path,
        data: Path,
        env: dict[str, str],
        key: str,
        timeout: float,
    ):
        self.binary, self.project, self.data = binary, project, data
        self.env, self.key, self.timeout = env, key, timeout
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.origin = f"http://127.0.0.1:{self.port}"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, path: str, *, authorized: bool = True) -> tuple[int, dict]:
        request = urllib.request.Request(
            self.origin + path,
            headers={"Authorization": f"Bearer {self.key}"} if authorized else {},
        )
        try:
            response = self.opener.open(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            content = response.read(1024 * 1024 + 1)
            require(len(content) <= 1024 * 1024, "response_size_limit")
            try:
                body = json.loads(content)
            except (ValueError, UnicodeError):
                body = {}
            require(isinstance(body, dict), "response_shape")
            return response.status, body

    @contextlib.contextmanager
    def running(self):
        command = [
            str(self.binary),
            "start",
            "--address",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--datadir",
            str(self.data),
            "--db-file",
            "native-acceptance.db",
            "--actions-sync=false",
            "--min-processes=0",
            "--max-processes=1",
            "--api-key=" + self.key,
        ]
        # No application logs are uploaded; synthetic temporary logs aid local debugging.
        with (self.data / "process.log").open("ab") as output:
            with owned_process(
                command,
                cwd=self.project,
                env=self.env,
                stdout=output,
                stderr=subprocess.STDOUT,
            ) as process:
                deadline = time.monotonic() + self.timeout
                while time.monotonic() < deadline:
                    exit_code = process.poll()
                    if exit_code is not None:
                        error = AcceptanceFailure("native_startup_exit")
                        error.diagnostics = startup_diagnostics(
                            self.data / "process.log", exit_code, self.key
                        )
                        raise error
                    try:
                        status, _ = self.request("/config", authorized=False)
                        if status == 200:
                            break
                    except (OSError, urllib.error.URLError):
                        pass
                    time.sleep(0.25)
                else:
                    raise AcceptanceFailure("native_startup_timeout")
                yield self


def browser(server: NativeServer, args, *, negative: bool) -> dict:
    code, output = run_output(
        [args.node, str(BROWSER_SCRIPT)],
        cwd=server.project,
        env=server.env,
        timeout=120,
        input_text=json.dumps(
            {
                "origin": server.origin,
                "api_key": server.key,
                "negative_control": negative,
                "browser_executable": str(args.browser_executable)
                if args.browser_executable
                else None,
            }
        ),
    )
    try:
        result = json.loads(output)
    except ValueError as error:
        raise AcceptanceFailure("browser_receipt_invalid") from error
    require(isinstance(result, dict), "browser_receipt_shape")
    if negative:
        require(
            code == 1
            and result.get("status") == "FAIL"
            and result.get("phase") == "empty_queue"
            and result.get("http_status") == 403,
            "negative_browser_control_not_rejected",
        )
    else:
        phase = result.get("phase", "unknown")
        if code != 0 or result.get("status") != "PASS":
            audits = result.get("accessibility", [])
            failures: set[str] = set()
            if isinstance(audits, list):
                for audit in audits[:8]:
                    if not isinstance(audit, dict):
                        continue
                    violations = audit.get("violations", [])
                    if not isinstance(violations, list):
                        continue
                    for violation in violations[:100]:
                        if not isinstance(violation, dict):
                            continue
                        rule = violation.get("id")
                        if isinstance(rule, str) and re.fullmatch(
                            r"[a-z][a-z0-9-]{0,80}", rule
                        ):
                            failures.add(rule)
            if failures:
                failure = AcceptanceFailure("browser_accessibility")
                failure.diagnostics = {"browser_accessibility": sorted(failures)[:50]}
                raise failure
        require(
            code == 0 and result.get("status") == "PASS",
            f"browser_{phase}"
            if phase
            in {
                "launch",
                "sign_in",
                "empty_queue",
                "session_cookie",
                "websocket_echo",
                "create_list_detail",
                "logout",
                "browser_errors",
                "browser_cleanup",
            }
            else "browser_failed",
        )
        require(
            isinstance(result.get("item_id"), str)
            and re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", result["item_id"]) is not None,
            "browser_item_identity",
        )
    return result


def verify_case(kind: str, binary: Path, args, receipt: dict) -> None:
    case: dict[str, Any] = {
        "kind": kind,
        "sha256": digest(binary),
        "status": "IN_PROGRESS",
        "checks": [],
    }
    receipt["cases"].append(case)
    with tempfile.TemporaryDirectory(prefix=f"actions-native-{kind}-") as directory:
        # Resolve only harness-owned POSIX temp aliases (macOS /var -> /private).
        # Preserve Windows spelling so native startup exercises 8.3 TEMP aliases.
        temporary = Path(directory) if os.name == "nt" else Path(directory).resolve()
        project, data = temporary / "project", temporary / "data"
        project.mkdir()
        data.mkdir()
        marker = project / "shadow-executed"
        (project / "actions.py").write_text(
            "open('shadow-executed', 'w').write('synthetic shadow executed')\nraise RuntimeError('synthetic untrusted actions module')\n",
            encoding="utf-8",
        )
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
        }
        env["ACTIONS_SKIP_UPDATE_CHECK"] = "1"
        code, version = run_output(
            [str(binary), "version"], cwd=project, env=env, timeout=args.startup_timeout
        )
        require(
            code == 0 and version.strip() == args.expected_version, "native_version"
        )
        case["version"] = version.strip()
        server = NativeServer(
            binary, project, data, env, secrets.token_urlsafe(32), args.startup_timeout
        )
        with server.running():
            status, body = server.request("/api/work-items", authorized=False)
            require(status == 403, "unauthorized_queue")
            status, body = server.request("/api/work-items")
            require(
                status == 200 and body.get("items") == [] and body.get("total") == 0,
                "empty_queue",
            )
            status, _ = server.request("/api/work-items/synthetic-missing-id")
            require(status == 404, "missing_item_not_404")
            case["checks"].extend(
                ["unauthorized_403", "empty_queue_200", "missing_item_404"]
            )
            negative = browser(server, args, negative=True)
            case["negative_control"] = {
                "status": "REJECTED_AS_EXPECTED",
                "phase": negative["phase"],
                "http_status": negative["http_status"],
            }
            case["checks"].append("browser_403_negative_control_rejected")
            browser_receipt = browser(server, args, negative=False)
            case["browser"] = browser_receipt
        with server.running():
            status, item = server.request(
                "/api/work-items/" + browser_receipt["item_id"]
            )
            require(
                status == 200
                and item.get("payload") == {"synthetic": "native-browser-acceptance"}
                and item.get("state") == "PENDING",
                "restart_persistence",
            )
            case["checks"].append("restart_persistence")
        # Corrupt only this stopped synthetic database, including recovery sidecars.
        for suffix in ("-wal", "-shm", "-journal"):
            (data / f"workitems.db{suffix}").unlink(missing_ok=True)
        (data / "workitems.db").write_bytes(b"synthetic corrupt database")
        with server.running():
            status, body = server.request("/api/work-items")
            detail = body.get("detail")
            require(
                status == 503
                and isinstance(detail, dict)
                and detail.get("code") == "work_items_storage_unavailable",
                "corrupt_storage_not_503",
            )
            case["checks"].append("corrupt_storage_503")
        require(not marker.exists(), "untrusted_cwd_module_executed")
        case["checks"].append("cwd_actions_shadow_not_executed")
        require(
            server.key.encode() not in (data / "process.log").read_bytes(),
            "native_log_contains_api_key",
        )
        case["checks"].append("api_key_absent_from_native_log")
    require(digest(binary) == case["sha256"], "binary_changed_during_acceptance")
    case["status"] = "PASS"
    print(f"{kind}: native browser/storage acceptance PASS", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    suffix = ".exe" if os.name == "nt" else ""
    parser.add_argument(
        "--frozen",
        type=Path,
        default=PACKAGE / "dist" / "action-server" / f"action-server{suffix}",
    )
    parser.add_argument(
        "--go-wrapper",
        type=Path,
        default=PACKAGE / "dist" / "final" / f"action-server{suffix}",
    )
    parser.add_argument(
        "--source-sha",
        required=True,
        help="Exact source SHA used to build these binaries, not the harness checkout SHA.",
    )
    parser.add_argument(
        "--expected-version",
        default=tomllib.loads((PACKAGE / "pyproject.toml").read_text("utf-8"))["tool"][
            "poetry"
        ]["version"],
    )
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--node", default="node")
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--startup-timeout", type=float, default=120)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("source SHA must be a full lowercase commit SHA")
    receipt = {
        "schema_version": 1,
        "source_sha": args.source_sha,
        "platform": platform.system(),
        "architecture": platform.machine(),
        "expected_version": args.expected_version,
        "status": "IN_PROGRESS",
        "cases": [],
        "not_exercised": [
            "Work Item worker state transitions",
            "attachments",
            "manual and full-route accessibility",
            "non-Chromium browsers",
        ],
    }
    try:
        require(0 < args.startup_timeout <= 300, "startup_timeout_range")
        for kind, path in (("frozen", args.frozen), ("go-wrapper", args.go_wrapper)):
            require(path.is_file(), f"{kind}_binary_missing")
            verify_case(kind, path.resolve(), args, receipt)
        receipt["status"] = "PASS"
        return 0
    except (AcceptanceFailure, OSError, subprocess.SubprocessError) as error:
        receipt["status"] = "FAIL"
        receipt["failed_phase"] = (
            str(error) if isinstance(error, AcceptanceFailure) else type(error).__name__
        )
        if isinstance(error, AcceptanceFailure) and error.diagnostics is not None:
            if "browser_accessibility" in error.diagnostics:
                receipt["browser_accessibility"] = error.diagnostics[
                    "browser_accessibility"
                ]
            else:
                receipt["startup_diagnostics"] = error.diagnostics
        print(f"Native acceptance failed: {receipt['failed_phase']}", file=sys.stderr)
        return 1
    finally:
        if receipt["status"] == "FAIL":
            for case in receipt["cases"]:
                if case["status"] == "IN_PROGRESS":
                    case["status"] = "FAIL"
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--owned-child"]:
        raise SystemExit(_owned_child(sys.argv[2:]))
    raise SystemExit(main())
