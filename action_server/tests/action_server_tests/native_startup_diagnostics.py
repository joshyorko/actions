"""Test-owned, allowlisted observations; never read subprocess pipes."""

import hashlib
import json
import math
import re
import shlex
import threading
import time
from pathlib import Path

NODES = {
    "action_server_tests/test_cli_live_reload_multi_package.py::test_failed_watched_reload_keeps_both_packages_and_recovers",
    "action_server_tests/test_cli_mcp_catalog_rollback.py::test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[resource]",
}


class DeliveredObservations:
    """Bounded categorical observations of existing completed-line callbacks."""

    PROGRESS = re.compile(
        r"^####\s+Progress:\s+(\d{1,3})/(\d{1,3})\s+v([0-9.]{1,20})\s+"
        r"([\w.+-]{1,32})s(?:\s|$)"
    )
    ANSI = re.compile(r"\x1b\[[0-9;]*m")

    def __init__(self, *, began, use_https=False, clock=time.monotonic):
        self.began, self.clock = began, clock
        scheme = "https" if use_https else "http"
        self.ready = re.compile(
            r"Local Action Server: " + scheme + r"://([\w.-]+):(\d+)"
        )
        self.lock = threading.Lock()
        self.loss = threading.Event()
        self.lock_loss = threading.Event()
        self.probe_error = threading.Event()
        self.count_overflow = threading.Event()
        self.mark_cap = threading.Event()
        self.counts = {"stdout_lines": 0, "stderr_lines": 0, "truncated_lines": 0}
        self.marks = []
        self.progress_channel = None
        self.start_return_offset = None
        self.start_return_instant = None
        self.match_instants = {
            channel: {"first": None, "last": None} for channel in ("stdout", "stderr")
        }
        self.port_positive = None
        self.cleanup = {"status": "unavailable"}
        self.readiness = {
            channel: {
                "literal_marker_count": 0,
                "exact_match_count": 0,
                "first_match_offset_seconds": None,
                "last_match_offset_seconds": None,
            }
            for channel in ("stdout", "stderr")
        }

    def _record(self, function):
        """Never block a pipe callback or expose probe exceptions to its logger."""
        acquired = False
        try:
            acquired = self.lock.acquire(blocking=False)
            if not acquired:
                self.loss.set()
                self.lock_loss.set()
                return
            function()
        except BaseException:
            self.loss.set()
            self.probe_error.set()
        finally:
            if acquired:
                try:
                    self.lock.release()
                except BaseException:
                    self.loss.set()
                    self.probe_error.set()

    def _count(self, mapping, key, amount=1):
        value = mapping[key] + amount
        if value > 65535:
            self.loss.set()
            self.count_overflow.set()
        mapping[key] = min(value, 65535)

    def _instant(self):
        instant = self.clock()
        value = instant - self.began
        if not math.isfinite(value) or not 0 <= value <= 3600:
            raise ValueError("invalid observation clock")
        return instant

    def line(self, channel, line):
        def record():
            self._count(self.counts, channel + "_lines")
            if len(line) > 8192:
                self._count(self.counts, "truncated_lines")
                self.loss.set()
                return
            instant = self._instant()
            offset = round(instant - self.began, 3)
            ready = self.readiness[channel]
            self._count(
                ready, "literal_marker_count", line.count("Local Action Server:")
            )
            matches = self.ready.findall(
                line
            )  # Exactly the starter's original matcher.
            if matches:
                self._count(ready, "exact_match_count", len(matches))
                if ready["first_match_offset_seconds"] is None:
                    ready["first_match_offset_seconds"] = offset
                    self.match_instants[channel]["first"] = instant
                ready["last_match_offset_seconds"] = offset
                self.match_instants[channel]["last"] = instant
            normalized = self.ANSI.sub("", line)
            if not re.match(r"^####\s*Progress:", normalized):
                return
            match = self.PROGRESS.match(normalized)
            if not match:
                self.loss.set()
                return
            step, total, version, duration = match.groups()
            step, total, duration = int(step), int(total), float(duration)
            if (
                not 0 <= step <= 15
                or total != 15
                or version != "18.19.3"
                or not math.isfinite(duration)
                or not 0 <= duration <= 3600
            ):
                self.loss.set()
                return
            if self.progress_channel is None:
                self.progress_channel = channel
            if step != len(self.marks) or channel != self.progress_channel:
                self.loss.set()
            if len(self.marks) == 32:
                self.loss.set()
                self.mark_cap.set()
                return
            self.marks.append(
                {
                    "step": step,
                    "total": total,
                    "version": "18.19.3",
                    "since_previous_seconds": duration,
                    "channel": channel,
                    "arrival_offset_seconds": offset,
                }
            )

        self._record(record)

    def process_start_returned(self):
        def record():
            instant = self._instant()
            self.start_return_instant = instant
            self.start_return_offset = round(instant - self.began, 3)

        self._record(record)

    def start_finished(self, server):
        self._record(lambda: setattr(self, "port_positive", server._port > 0))

    def cleanup_returned(self, returned):
        def record():
            result, readers = returned
            if result is None:
                self.cleanup = {"status": "unavailable"}
                return
            flags = {
                "wrapper_reaped": result.wrapper_reaped,
                "execution_stopped": result.execution_stopped,
                "descendant_snapshot_complete": result.descendant_snapshot_complete,
                "descendant_reap_complete": result.descendant_reap_complete,
            }
            counts = {
                "observed_live_child_count": len(result.live_descendant_pids),
                "observed_zombie_child_count": len(result.zombie_descendant_pids),
                "cleanup_error_count": len(result.errors),
                "active_reader_count": len(readers),
            }
            if any(not isinstance(value, bool) for value in flags.values()) or any(
                value > 65535 for value in counts.values()
            ):
                self.loss.set()
                return
            self.cleanup = {"status": "returned", **flags, **counts}

        self._record(record)

    def cleanup_raised(self):
        self._record(lambda: setattr(self, "cleanup", {"status": "raised"}))

    def summary(self):
        report = {"status": "unavailable", "observation_loss": True}

        def record():
            ready = {
                channel: dict(values) for channel, values in self.readiness.items()
            }
            for channel, values in ready.items():
                for position in ("first", "last"):
                    instant = self.match_instants[channel][position]
                    values[position + "_match_before_deadline_lower_bound"] = (
                        instant < self.start_return_instant + 90
                        if instant is not None and self.start_return_instant is not None
                        else None
                    )
            lost = self.loss.is_set()
            report.update(
                {
                    "status": "observed",
                    "observation_loss": lost,
                    "lock_loss": self.lock_loss.is_set(),
                    "probe_error": self.probe_error.is_set(),
                    "count_overflow": self.count_overflow.is_set(),
                    "mark_cap_reached": self.mark_cap.is_set(),
                    "counts": dict(self.counts),
                    "progress": {
                        "marks": [dict(mark) for mark in self.marks],
                        "interval_sum_seconds": round(
                            sum(mark["since_previous_seconds"] for mark in self.marks),
                            3,
                        )
                        if not lost and len(self.marks) == 16
                        else None,
                    },
                    "readiness": ready,
                    "process_start_return_offset_seconds": self.start_return_offset,
                    "readiness_future": "unavailable_from_host",
                    "port_positive_after_start": self.port_positive,
                    "cleanup": dict(self.cleanup),
                }
            )

        self._record(record)
        if self.loss.is_set():
            report["observation_loss"] = True
            if "progress" in report:
                report["progress"]["interval_sum_seconds"] = None
        return report


def observe_owned_start(monkeypatch, start, server, **kwargs):
    """Observe only the already-owned Process; delegate every operation unchanged."""
    from actions.server._robo_utils.process import Process

    try:
        probe = DeliveredObservations(
            began=time.monotonic(), use_https=kwargs.get("use_https", False)
        )
    except BaseException:
        return observe_start(start, server, **kwargs)
    original_start = Process.start
    original_cleanup = Process._stop_and_reap_until
    registrations = []

    def process_start(process, *args, **arguments):
        if process is not server._process:
            return original_start(process, *args, **arguments)
        try:
            for channel in ("stdout", "stderr"):

                def callback(line, channel=channel):
                    probe.line(channel, line)

                owner = getattr(process, "on_" + channel)
                owner.register(callback)
                registrations.append((owner, callback))
        except BaseException:
            probe.loss.set()
            probe.probe_error.set()
        result = original_start(process, *args, **arguments)
        probe.process_start_returned()
        return result

    def process_cleanup(process, deadline):
        if process is not server._process:
            return original_cleanup(process, deadline)
        try:
            result = original_cleanup(process, deadline)
        except BaseException:
            probe.cleanup_raised()
            raise
        probe.cleanup_returned(result)
        return result

    def unregister():
        while registrations:
            owner, callback = registrations.pop()
            try:
                owner.unregister(callback)
            except BaseException:
                probe.loss.set()
                probe.probe_error.set()

    def delegated(server, **arguments):
        try:
            return start(server, **arguments)
        finally:
            unregister()

    try:
        with monkeypatch.context() as context:
            context.setattr(Process, "start", process_start)
            context.setattr(Process, "_stop_and_reap_until", process_cleanup)
            return observe_start(delegated, server, delivered=probe, **kwargs)
    finally:
        unregister()


def enabled(nodeid, platform, environ):
    return (
        platform == "win32"
        and nodeid.removeprefix("tests/") in NODES
        and bool(environ.get("ACTIONS_NATIVE_STARTUP_DIAGNOSTICS_DIR"))
        and bool(environ.get("SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE"))
    )


def observe_start(
    start, server, *, snapshot, publish, offsets=(80.0, 88.0), delivered=None, **kwargs
):
    cancelled = threading.Event()
    began = time.monotonic()

    def emit(report):
        try:
            if delivered is not None:
                report["delivered_observations"] = delivered.summary()
            publish(report)
        except Exception:
            # A failed artifact write must not change startup or its cleanup.
            if delivered is not None:
                delivered.loss.set()

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
        if delivered is not None:
            delivered.start_finished(server)
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
        return observe_owned_start(
            monkeypatch, original, server, snapshot=snapshot, publish=publish, **kwargs
        )

    monkeypatch.setattr(ActionServerProcess, "start", start)
