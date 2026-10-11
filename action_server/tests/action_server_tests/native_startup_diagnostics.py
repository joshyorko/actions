"""Test-owned, allowlisted observations; never read subprocess pipes."""

import hashlib
import json
import re
import shlex
import threading
import time
from pathlib import Path

NODES = {
    "action_server_tests/test_cli_live_reload_multi_package.py::test_failed_watched_reload_keeps_both_packages_and_recovers",
    "action_server_tests/test_cli_mcp_catalog_rollback.py::test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[resource]",
}


def enabled(nodeid, platform, environ):
    return (
        platform == "win32"
        and nodeid.removeprefix("tests/") in NODES
        and bool(environ.get("ACTIONS_NATIVE_STARTUP_DIAGNOSTICS_DIR"))
        and bool(environ.get("SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE"))
    )


def observe_start(start, server, *, snapshot, publish, offsets=(80.0, 88.0), **kwargs):
    cancelled = threading.Event()
    began = time.monotonic()

    def emit(report):
        try:
            publish(report)
        except Exception:
            # A failed artifact write must not change startup or its cleanup.
            pass

    def sample():
        for offset in offsets:
            if cancelled.wait(max(0, began + offset - time.monotonic())):
                return
            try:
                report = {"snapshot": snapshot(server)}
            except Exception:
                report = {"observation": "unavailable"}
            if cancelled.is_set():
                return
            report["elapsed_seconds"] = round(time.monotonic() - began, 3)
            emit(report)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    outcome, exception = "ready", None
    try:
        return start(server, **kwargs)
    except BaseException as error:
        outcome, exception = "failed", type(error).__name__
        raise
    finally:
        # Delegated start has already performed its existing failure cleanup.
        cancelled.set()
        sampler.join(timeout=0.05)
        emit(
            {
                "outcome": outcome,
                "exception": exception,
                "sampler_cancelled": True,
                "sampler_alive": sampler.is_alive(),
            }
        )


def file_identity(path, limit=128 * 1024 * 1024):
    """Bounded bytes only; no contents or paths appear in the receipt."""
    try:
        size = path.stat().st_size
        if size > limit:
            return {"status": "over_limit"}
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            remaining = limit + 1
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                digest.update(chunk)
        if remaining == 0:
            return {"status": "over_limit"}
        return {"size": size, "sha256": digest.hexdigest()}
    except (OSError, ValueError):
        return {"status": "unavailable"}


def command_summary(args):
    """Retain known RCC operation/flags, never arbitrary argument values."""
    summary = {"operation": "unavailable"}
    if len(args) < 3 or args[1:3] not in (["holotree", "variables"], ["ht", "hash"]):
        return summary
    summary["operation"] = " ".join(args[1:3])
    known = {
        "--json",
        "--no-retry-build",
        "--no-pyc-management",
        "--bundled",
        "--robocorp",
    }
    unknown = 0
    index = 3
    while index < len(args):
        arg = args[index]
        if arg in known:
            summary[arg[2:].replace("-", "_")] = True
        elif arg == "--space" and index + 1 < len(args):
            index += 1
            if re.fullmatch(r"[0-9a-f]{16,64}", args[index]):
                summary["space"] = args[index]
            else:
                unknown += 1
        elif arg == "--controller" and index + 1 < len(args):
            index += 1
            if args[index] == "action-server":
                summary["controller"] = "action-server"
            else:
                unknown += 1
        elif arg == "--config" and index + 1 < len(args):
            index += 1
            summary["config_argument_present"] = True
        elif index == 5 and summary["operation"] == "holotree variables":
            summary["package_argument_present"] = True
        else:
            unknown += 1
        index += 1
    summary["unrecognized_arguments"] = unknown
    return summary


def stderr_summary(stderr):
    """Summarize completed, already captured lines without publishing text."""
    result = {"characters": len(stderr), "last_rcc_command": None}
    for line in stderr[-8192:].splitlines():
        if "Running: " in line:
            try:
                args = [
                    arg.strip('"')
                    for arg in shlex.split(line.split("Running: ", 1)[1], posix=False)
                ]
                command = command_summary(args)
                if command["operation"] != "unavailable":
                    result["last_rcc_command"] = command
            except ValueError:
                pass
    return result


def snapshot(server):
    """Only the owned wrapper, its descendants and registered host readers."""
    import psutil

    process = server._process
    if process is None or process._proc is None:
        return {"owned_process": "unavailable"}
    result = {
        "wrapper_pid": process._proc.pid,
        "wrapper_returncode": process._proc.poll(),
        "host_readers": [
            {"alive": reader.is_alive(), "ident": reader.ident}
            for reader in process._reader_threads[:2]
        ],
        "pipes_closed": {
            name: getattr(process._proc, name).closed
            if getattr(process._proc, name)
            else None
            for name in ("stdout", "stderr")
        },
        "captured_stdout_characters": server._stdout.tell(),
        "captured_stderr": stderr_summary(server.get_stderr())
        if server._stderr.tell() <= 256 * 1024
        else {"status": "over_limit"},
        "rcc_internal_readers": "unavailable_from_host",
        "processes": [],
    }
    try:
        if process._proc.poll() is not None:
            result["owned_process"] = "exited"
            return result
        owner = psutil.Process(process._proc.pid)
        if owner.cmdline()[:1] != process._args[:1]:
            result["owned_process"] = "identity_unavailable"
            return result
        queue = [(owner, None)]
        seen = set()
        probe_deadline = time.monotonic() + 1.0
        while queue and len(seen) < 64 and time.monotonic() < probe_deadline:
            child, expected_parent = queue.pop(0)
            if child.pid in seen:
                continue
            seen.add(child.pid)
            entry = {"pid": child.pid}
            try:
                parent = child.ppid()
                if expected_parent is not None and parent != expected_parent:
                    result["descendant_identity_unavailable"] = True
                    continue
                result["processes"].append(entry)
                entry.update(
                    {
                        "parent_pid": parent,
                        "created": child.create_time(),
                        "status": child.status(),
                        "cpu_seconds": sum(child.cpu_times()[:2]),
                    }
                )
                try:
                    io = child.io_counters()
                    entry["io_bytes"] = {"read": io.read_bytes, "write": io.write_bytes}
                    if hasattr(child, "num_handles"):
                        entry["handles"] = child.num_handles()
                except (psutil.Error, AttributeError):
                    entry["io_observation"] = "unavailable"
                args = child.cmdline()
                command = command_summary(args)
                entry["command"] = command
                if command["operation"] == "holotree variables":
                    entry["rcc_executable"] = file_identity(Path(args[0]))
                    package = Path(args[5])
                    # Staged package bytes only within this server's datadir.
                    if package.resolve().is_relative_to(server.datadir.resolve()):
                        entry["staged_package"] = file_identity(package, 1024 * 1024)
                    else:
                        entry["staged_package"] = {"status": "outside_owned_datadir"}
                    space = command.get("space")
                    if space:
                        entry["env_info_cache_exists"] = (
                            server.datadir / "env-info" / f"{space}.json"
                        ).exists()
                    # Query only the named effective home, emit equality alone.
                    effective = child.environ().get("ROBOCORP_HOME")
                    expected = process._env.get("ACTIONS_HOME")
                    entry["effective_home_matches_launch"] = (
                        effective == expected
                        if effective and expected
                        else "unavailable"
                    )
                queue.extend(
                    (descendant, child.pid)
                    for descendant in child.children()[: 64 - len(seen) - len(queue)]
                )
            except (psutil.Error, OSError, ValueError, IndexError):
                entry["observation"] = "partly_unavailable"
        result["descendant_limit_reached"] = bool(queue)
    except psutil.Error:
        result["owned_process"] = "unavailable"
    return result


def install(monkeypatch, directory, nodeid, environ, config):
    from actions.server._selftest import ActionServerProcess

    original = ActionServerProcess.start
    prefix = hashlib.sha256(nodeid.encode()).hexdigest()[:16]
    count = 0

    def start(server, **kwargs):
        nonlocal count
        if count or kwargs.get("timeout") != 90 or not kwargs.get("actions_sync"):
            return original(server, **kwargs)
        count += 1
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            return original(server, **kwargs)
        sequence = 0
        sequence_lock = threading.Lock()

        def publish(report):
            nonlocal sequence
            with sequence_lock:
                sequence += 1
                report_number = sequence
            if "outcome" in report:
                # Hash native bytes after delegated startup/cleanup to avoid
                # pre-reading the executable during this cold bootstrap probe.
                report["native_executable"] = file_identity(
                    Path(environ["SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE"])
                )
                process = server._process
                report["after_start_returned"] = {
                    "returncode": process._proc.poll()
                    if process and process._proc
                    else None,
                    "host_readers_alive": [
                        reader.is_alive() for reader in process._reader_threads[:2]
                    ]
                    if process
                    else [],
                    "observation": "host_only",
                }
            target = directory / f"{prefix}-{report_number}.json"
            target.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")

        root = Path(__file__).resolve().parents[2]
        identity = {
            "nodeid": nodeid,
            "schema": 1,
            "readiness_seconds": 90,
            "failure_cleanup_seconds": 20,
            "sample_seconds": [80, 88],
            "native_executable": {"status": "measured_after_start_returns"},
            "rcc_config": file_identity(config, 1024 * 1024),
            "source_files": {
                relative: file_identity(root / relative)
                for relative in (
                    "src/actions/server/_selftest.py",
                    "src/actions/server/_rcc.py",
                    "src/actions/server/_robo_utils/process.py",
                    "tests/action_server_tests/fixtures.py",
                    "tests/action_server_tests/native_startup_diagnostics.py",
                    "tests/action_server_tests/test_cli_live_reload_multi_package.py",
                    "tests/action_server_tests/test_cli_mcp_catalog_rollback.py",
                )
            },
        }
        for name in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
            value = environ.get(name, "")
            identity[name] = (
                value if re.fullmatch(r"[0-9a-f]{1,40}", value) else "unavailable"
            )
        try:
            publish({"identity": identity})
        except OSError:
            return original(server, **kwargs)
        return observe_start(
            original, server, snapshot=snapshot, publish=publish, **kwargs
        )

    monkeypatch.setattr(ActionServerProcess, "start", start)
