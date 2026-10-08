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
from typing import Any

PACKAGE = Path(__file__).resolve().parents[1]
BROWSER_SCRIPT = PACKAGE / "frontend" / "scripts" / "native-browser-acceptance.mjs"


class AcceptanceFailure(Exception):
    """A bounded phase label, never a raw response, subprocess log or credential."""


def require(condition: bool, phase: str) -> None:
    if not condition:
        raise AcceptanceFailure(phase)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


@contextlib.contextmanager
def owned_process(command: list[str], *, cwd: Path, env: dict[str, str], **kwargs):
    """Own a process tree, not a process-name pattern or unrelated runner process."""
    options = (
        {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP")}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    process = subprocess.Popen(command, cwd=cwd, env=env, **options, **kwargs)
    try:
        yield process
    finally:
        if os.name == "nt":
            if process.poll() is None:
                with contextlib.suppress(subprocess.TimeoutExpired):
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=15,
                        check=False,
                    )
        else:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        finally:
            if os.name != "nt":
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
            "--api-key",
            self.key,
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
                    require(process.poll() is None, "native_startup_exit")
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
        temporary = Path(directory)
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
            "accessibility",
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
        print(f"Native acceptance failed: {receipt['failed_phase']}", file=sys.stderr)
        return 1
    finally:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
