#!/usr/bin/env python3
"""Run one unchanged PR304 #153 browser test against a measured Linux binary."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path("/workspace/work/actions-mk3-browser-security")
EVIDENCE = Path("/workspace/work/actions-mk3-evidence/pr304-browser-security")
PACKAGE_PYTHON = Path("/workspace/work/actions-mk3-pr302/action_server/.venv/bin/python")
TEST_RELATIVE = Path("action_server/tests/action_server_tests/test_browser_origin_acceptance.py")
TEST_NAME = "test_live_runtime_browser_origin_and_ambient_session_matrix"
MERGE_SHA = "856c0a47e27dda373d4e44aea2a5a26a1db287d0"
MERGE_TREE = "a8fe00af1858077273912d0b590f0f7a662c83d5"
MANIFEST_SHA256 = "738964dda8ccf202db4ce9dd3537abd5666badfe021ba9ecde0a2bb7850d5494"
EXPECTED_BINARY_HASHES = {
    "frozen": "08aa825cb3b6bc8ec0d3747f2323de89d18f5df42bc78d72c934579648e0a85e",
    "go-wrapper": "2d4913eae246409a7ff1814b01e56a050285cdbaa2312175063467e66b19b36b",
}
EXPECTED_BROWSER_HASH = "e11fc9ce65c96313476f7ee9844b6fb6a9220fb048693cfe9eee00acf4170a9f"
EXPECTED_BROWSER = Path(
    "/workspace/actions-cloud/cache/playwright/chromium_headless_shell-1234/"
    "chrome-headless-shell-linux64/chrome-headless-shell"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_environment() -> dict[str, str]:
    allowed = (
        "PATH",
        "LANG",
        "LC_ALL",
        "TZ",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "NODE_EXTRA_CA_CERTS",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    )
    return {name: os.environ[name] for name in allowed if name in os.environ}


def source_pythonpath() -> str:
    paths = (
        ROOT / "action_server/src",
        ROOT / "actions/src",
        ROOT / "actions-http-helper/src",
        ROOT / "common/src",
        ROOT / "work-items/src",
    )
    return os.pathsep.join(str(path) for path in paths)


def git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()


def run_preflight(binary: Path, kind: str) -> dict:
    assert kind in EXPECTED_BINARY_HASHES
    assert binary.is_file() and os.access(binary, os.X_OK)
    runtime_hash = sha256(binary)
    assert runtime_hash == EXPECTED_BINARY_HASHES[kind], (runtime_hash, kind)
    assert PACKAGE_PYTHON.is_file()
    expected_prefix = PACKAGE_PYTHON.parent.parent
    assert Path(sys.executable).absolute() == PACKAGE_PYTHON, (
        sys.executable,
        PACKAGE_PYTHON,
    )
    assert Path(sys.prefix).resolve() == expected_prefix.resolve(), (
        sys.prefix,
        expected_prefix,
    )
    import psutil

    psutil_origin = Path(psutil.__file__).resolve()
    assert psutil_origin.is_relative_to(expected_prefix.resolve()), psutil_origin
    assert EXPECTED_BROWSER.is_file()
    browser_hash = sha256(EXPECTED_BROWSER)
    assert browser_hash == EXPECTED_BROWSER_HASH, browser_hash
    browser_version = subprocess.run(
        [str(EXPECTED_BROWSER), "--version"], text=True, capture_output=True, check=True
    ).stdout.strip()
    assert browser_version == "Google Chrome for Testing 151.0.7922.34", browser_version

    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    branch = git("branch", "--show-current")
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    assert head == "73605934c1c948895410a5abaed6c225a396e038", head
    assert tree == MERGE_TREE, tree
    assert branch == "mk3/browser-security-20261010", branch
    assert not status, status
    source = subprocess.run(
        ["git", "show", f"HEAD:{TEST_RELATIVE.as_posix()}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    source_hash = hashlib.sha256(source).hexdigest()
    assert source_hash == sha256(ROOT / TEST_RELATIVE)

    env = clean_environment()
    env["PYTHONPATH"] = source_pythonpath()
    env["NODE_PATH"] = ""
    py_probe = subprocess.run(
        [
            str(PACKAGE_PYTHON),
            "-c",
            "import actions, actions.server, mcp; import json, sys; "
            "print(json.dumps({'python':sys.version,'prefix':sys.prefix,'actions':actions.__file__,'actions_server':actions.server.__file__,'mcp_sdk':mcp.__file__}))",
        ],
        cwd=ROOT / "action_server",
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    modules = json.loads(py_probe.stdout.strip().splitlines()[-1])
    assert str(ROOT / "actions/src") in modules["actions"]
    assert str(ROOT / "action_server/src") in modules["actions_server"]
    assert str(Path(modules["prefix"]).resolve()) in str(Path(modules["mcp_sdk"]).resolve())

    node = shutil.which("node")
    assert node is not None, "RCC task PATH must provide its pinned Node runtime"
    node_version = subprocess.run(
        [node, "--version"], text=True, capture_output=True, check=True
    ).stdout.strip()
    assert node_version == "v20.19.3", node_version
    node_probe = subprocess.run(
        [node, "-p", "require('@playwright/test/package.json').version"],
        cwd=ROOT / "action_server/frontend",
        env=env,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    assert node_probe == "1.62.1", node_probe

    return {
        "checkout_head": head,
        "checkout_tree": tree,
        "checkout_branch": branch,
        "tracked_checkout_clean": True,
        "pr304_synthetic_merge": MERGE_SHA,
        "pr304_synthetic_merge_tree": MERGE_TREE,
        "pr304_linux_manifest_sha256": MANIFEST_SHA256,
        "workflow_run_id": "38081495661",
        "source_test_sha256": source_hash,
        "runner_python_executable": sys.executable,
        "runner_python_prefix": sys.prefix,
        "runner_python_base_prefix": sys.base_prefix,
        "runner_psutil_origin": str(psutil_origin),
        "package_python": modules["python"],
        "package_python_prefix": modules["prefix"],
        "actions_core_origin": modules["actions"],
        "actions_server_origin": modules["actions_server"],
        "mcp_sdk_installed_origin": modules["mcp_sdk"],
        "node_path": node,
        "node_version": node_version,
        "playwright_test_version": node_probe,
        "playwright_revision": "1234",
        "browser_executable_preflight": str(EXPECTED_BROWSER),
        "browser_sha256_preflight": browser_hash,
        "browser_version_preflight": browser_version,
        "selected_runtime_kind": kind,
        "selected_runtime_path": str(binary),
        "selected_runtime_sha256": runtime_hash,
    }


def inspect_owned_pids(entries: list[dict]) -> list[dict]:
    import psutil

    results = []
    for entry in entries:
        pid = entry["pid"]
        try:
            process = psutil.Process(pid)
            results.append(
                {
                    "pid": pid,
                    "status": process.status(),
                    "is_running": process.is_running(),
                    "name": process.name(),
                    "argv": [value.replace("test-key", "[redacted]") for value in process.cmdline()],
                }
            )
        except psutil.NoSuchProcess:
            results.append({"pid": pid, "status": "gone", "is_running": False})
        except psutil.Error as exc:
            results.append({"pid": pid, "status": "observation_error", "error": type(exc).__name__})
    return results


def exact_test_result(run_dir: Path) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    selected_path = run_dir / "pytest-selection.json"
    junit_path = run_dir / "junit.xml"
    stdout_path = run_dir / "browser-harness-stdout.log"
    result_path = run_dir / "browser-harness-result.json"
    if not all(path.is_file() for path in (selected_path, junit_path, stdout_path, result_path)):
        return None, ["missing collection/JUnit/browser-harness receipt"]
    try:
        selected = json.loads(selected_path.read_text())
        nodeid = str(TEST_RELATIVE.relative_to("action_server")) + "::" + TEST_NAME
        if selected != {"collected_nodeids": [nodeid], "collected_count": 1}:
            errors.append(f"unexpected collected test selection: {selected}")
        root = ET.parse(junit_path).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        totals = {
            name: sum(int(suite.attrib.get(name, "0")) for suite in suites)
            for name in ("tests", "failures", "errors", "skipped")
        }
        if totals != {"tests": 1, "failures": 0, "errors": 0, "skipped": 0}:
            errors.append(f"unexpected JUnit result: {totals}")
        harness = json.loads(stdout_path.read_text().splitlines()[-1])
        if harness.get("status") != "PASS":
            errors.append(f"browser harness result was {harness.get('status')!r}")
        capture = json.loads(result_path.read_text())
        if capture.get("returncode") != 0:
            errors.append("browser harness returned nonzero")
        if capture.get("synthetic_key_occurrences_in_raw_stdout") or capture.get("synthetic_key_occurrences_in_raw_stderr"):
            errors.append("synthetic key appeared in captured browser harness output")
        return {"selected_nodeid": nodeid, **totals, "harness_status": harness.get("status")}, errors
    except (IndexError, OSError, ValueError, ET.ParseError) as exc:
        return None, [f"could not validate collected test/JUnit/harness receipt: {type(exc).__name__}"]


def run_owned_pytest(run_dir: Path, binary: Path) -> tuple[int, bool, str, str, dict]:
    env = clean_environment()
    env.update(
        {
            "PYTHONPATH": source_pythonpath() + os.pathsep + str(EVIDENCE / "runner"),
            "PR153_CAPTURE_DIR": str(run_dir),
            "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE": str(binary.resolve()),
            "ACTIONS_HOME": str(run_dir / "actions-home"),
            "ROBOTS_HOME": str(run_dir / "robots-home"),
            "ROBOCORP_HOME": str(run_dir / "robocorp"),
            "PLAYWRIGHT_BROWSERS_PATH": "/workspace/actions-cloud/cache/playwright",
            "DEBUG": "pw:browser",
            "TMPDIR": str(run_dir / "tmp"),
            "TMP": str(run_dir / "tmp"),
            "TEMP": str(run_dir / "tmp"),
            "HOME": str(run_dir / "home"),
            "XDG_CACHE_HOME": str(run_dir / "xdg-cache"),
            "NODE_PATH": "",
        }
    )
    for name in ("ACTIONS_HOME", "ROBOTS_HOME", "ROBOCORP_HOME", "TMPDIR", "XDG_CACHE_HOME", "HOME"):
        Path(env[name]).mkdir(parents=True, exist_ok=True)
    command = [
        str(PACKAGE_PYTHON),
        "-m",
        "pytest",
        "-q",
        "-s",
        "--tb=short",
        "-m",
        "integration_test",
        "-p",
        "pr153_capture_plugin",
        "--basetemp",
        str(run_dir / "pytest-tmp"),
        "--junitxml",
        str(run_dir / "junit.xml"),
        str(TEST_RELATIVE.relative_to("action_server")) + "::" + TEST_NAME,
    ]
    helper_path = ROOT / "action_server/scripts/verify_dakota_rcc_acceptance.py"
    spec = importlib.util.spec_from_file_location("pr153_owned_process_helper", helper_path)
    assert spec is not None and spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    supervisor = {
        "implementation": str(helper_path),
        "timeout_seconds": 205,
        "cleanup_grace_seconds": 6,
    }
    try:
        completed = helper.run_owned_process(
            command,
            timeout_seconds=205,
            cleanup_grace_seconds=6,
            env=env,
            cwd=ROOT / "action_server",
        )
        supervisor.update(
            {
                "disposition": getattr(completed, "cleanup_disposition", "completed"),
                "reaped_descendants": getattr(completed, "reaped_descendants", None),
                "unexpected_live_descendants": False,
            }
        )
        return completed.returncode, False, completed.stdout, completed.stderr, supervisor
    except subprocess.TimeoutExpired as exc:
        supervisor["disposition"] = "timeout; owned helper completed process-tree cleanup before returning"
        out = exc.output or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
        return 124, True, out, err, supervisor
    except helper.ProcessTreeCleanupError as exc:
        supervisor["disposition"] = exc.cleanup_disposition
        supervisor["cleanup_error"] = str(exc).replace("test-key", "[redacted]")
        return 125, False, exc.command_stdout, exc.command_stderr, supervisor


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("frozen", "go-wrapper"), required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    began = time.monotonic()
    binary = args.binary.resolve()
    identity = run_preflight(binary, args.kind)
    if args.preflight_only:
        print(json.dumps({"status": "PREFLIGHT_PASS", "identity": identity}, sort_keys=True))
        return 0
    if args.run_dir.exists():
        raise FileExistsError(f"refusing to overwrite run directory: {args.run_dir}")
    args.run_dir.mkdir(parents=True, exist_ok=False)

    started_at = time.time()
    returncode, timed_out, stdout, stderr, supervisor = run_owned_pytest(args.run_dir, binary)
    stdout = stdout.replace("test-key", "[redacted]")
    stderr = stderr.replace("test-key", "[redacted]")
    (args.run_dir / "pytest-stdout.log").write_text(stdout)
    (args.run_dir / "pytest-stderr.log").write_text(stderr)

    trace_path = args.run_dir / "browser-harness-stderr.log"
    trace = trace_path.read_text() if trace_path.is_file() else ""
    path_match = re.search(
        r"(/[^\s\"']*chromium_headless_shell-1234/[^\s\"']*chrome-headless-shell[^\s\"']*)",
        trace,
    )
    browser_path = str(Path(path_match.group(1))) if path_match else None
    browser_sha = sha256(Path(browser_path)) if browser_path and Path(browser_path).is_file() else None
    browser_pids = sorted({int(value) for value in re.findall(r"<launched> pid=(\d+)", trace)})
    launch_excerpt = [
        line.replace("test-key", "[redacted]")
        for line in trace.splitlines()
        if "chrome-headless-shell" in line or "browser.close" in line.lower()
    ][:20]
    pytest_result, gate_errors = exact_test_result(args.run_dir) if returncode == 0 and not timed_out else (None, [])
    if returncode == 0 and not timed_out:
        if browser_sha != EXPECTED_BROWSER_HASH:
            gate_errors.append(f"observed browser hash did not match managed revision 1234: {browser_sha}")
        if not browser_pids:
            gate_errors.append("DEBUG=pw:browser did not record a launched browser PID")
    process_start_path = args.run_dir / "runtime-process-start.json"
    process_start = json.loads(process_start_path.read_text()) if process_start_path.is_file() else None
    if returncode == 0 and not timed_out and process_start is None:
        gate_errors.append("ActionServerProcess selected-runtime start was not recorded")
    runtime_states = inspect_owned_pids(process_start["process_tree_at_ready"]) if process_start else []
    browser_states = inspect_owned_pids([{"pid": pid} for pid in browser_pids])
    live_owned = [
        entry for entry in [*runtime_states, *browser_states]
        if entry.get("is_running") and entry.get("status") != "zombie"
    ]
    if live_owned:
        gate_errors.append(f"owned Runtime/browser PIDs remained live: {[row['pid'] for row in live_owned]}")

    pytest_stdout = (args.run_dir / "pytest-stdout.log").read_text()
    pytest_stderr = (args.run_dir / "pytest-stderr.log").read_text()
    if "test-key" in pytest_stdout or "test-key" in pytest_stderr:
        gate_errors.append("synthetic key was not redacted from retained pytest logs")
    result = {
        "schema": "actions.pr153-native-browser-runtime-check.v2",
        "status": "PASS" if returncode == 0 and not timed_out and not gate_errors else "FAIL",
        "elapsed_seconds": round(time.monotonic() - began, 3),
        "test_elapsed_seconds": round(time.time() - started_at, 3),
        "test": str(TEST_RELATIVE) + "::" + TEST_NAME,
        "identity": identity,
        "command": [
            str(PACKAGE_PYTHON), "-m", "pytest", "-q", "-s", "--tb=short",
            "-m", "integration_test", "-p", "pr153_capture_plugin", "--basetemp",
            str(args.run_dir / "pytest-tmp"), "--junitxml", str(args.run_dir / "junit.xml"),
            str(TEST_RELATIVE.relative_to("action_server")) + "::" + TEST_NAME,
        ],
        "environment": {
            "DEBUG": "pw:browser",
            "PLAYWRIGHT_BROWSERS_PATH": "/workspace/actions-cloud/cache/playwright",
            "ACTIONS_HOME": str(args.run_dir / "actions-home"),
            "ROBOTS_HOME": str(args.run_dir / "robots-home"),
            "ROBOCORP_HOME": str(args.run_dir / "robocorp"),
            "outer_active_python_environment_removed": True,
            "node_path_override": "empty; resolved @playwright/test through lock-matched target frontend node_modules symlink",
        },
        "pytest": {"returncode": returncode, "timed_out": timed_out, "result": pytest_result},
        "owned_process_supervisor": supervisor,
        "browser_launch": {
            "path_observed_in_debug_trace": browser_path,
            "sha256": browser_sha,
            "version": identity["browser_version_preflight"],
            "launch_pids": browser_pids,
            "trace_excerpt": launch_excerpt,
            "matches_expected_managed_browser": browser_sha == EXPECTED_BROWSER_HASH,
        },
        "runtime_process_at_ready": process_start,
        "runtime_pid_state_after_test": runtime_states,
        "browser_pid_state_after_test": browser_states,
        "cleanup_interpretation": {
            "live_owned_processes": [row["pid"] for row in live_owned],
            "owned_zombie_processes": [row["pid"] for row in [*runtime_states, *browser_states] if row.get("status") == "zombie"],
            "reaped_descendant_count_reported_by_supervisor": supervisor.get("reaped_descendants"),
            "claims_complete_reaping": False,
        },
        "synthetic_key_redaction": {
            "test_uses_synthetic_test_key": True,
            "browser_helper_output_scrubbed_before_retention": True,
            "test_assertion_checks_server_stdout_and_stderr": True,
            "retained_test_logs_contain_key": "test-key" in pytest_stdout or "test-key" in pytest_stderr,
        },
        "gate_errors": gate_errors,
        "log_paths": {
            "pytest_stdout": str(args.run_dir / "pytest-stdout.log"),
            "pytest_stderr": str(args.run_dir / "pytest-stderr.log"),
            "browser_harness_stdout": str(args.run_dir / "browser-harness-stdout.log"),
            "browser_harness_stderr": str(args.run_dir / "browser-harness-stderr.log"),
            "junit": str(args.run_dir / "junit.xml"),
        },
        "limitations": [
            "This check exercises one PR304 Linux packaged artifact with the existing local browser test.",
            "Actual ChatGPT was not run.",
            "Production deployment authorization, CSP, artifact resolution, and frozen release signing are not established.",
            "Linux results do not establish Windows/macOS coverage or blanket issue #153 acceptance.",
        ],
    }
    receipt_path = args.run_dir / "acceptance-receipt.json"
    receipt_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "receipt": str(receipt_path), "elapsed_seconds": result["elapsed_seconds"]}, sort_keys=True))
    return 0 if result["status"] == "PASS" else (returncode or 1)


if __name__ == "__main__":
    raise SystemExit(main())
