"""Gate semantics everywhere; real Job lifetime assertions on Windows only."""

import contextlib
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import verify_native_acceptance as native


class JobClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, duration):
        self.now += duration


class JobKernel:
    """WinAPI boundary model: accounting clears before process handles signal."""

    job_handle = 9000

    def __init__(self, clock, pids=(11, 22)):
        self.clock = clock
        self.pids = pids
        self.total = len(pids) + 4
        self.terminated = False
        self.handles = {self.job_handle: None}
        self.signaled = set()
        self.signal_delays = {pid: 0.05 for pid in pids}
        self.wait_budgets = []
        self.closed = []
        self.CreateJobObjectW = mock.Mock(return_value=self.job_handle)
        self.SetInformationJobObject = mock.Mock(return_value=True)
        self.AssignProcessToJobObject = mock.Mock(return_value=True)
        self.QueryInformationJobObject = mock.Mock(side_effect=self.query)
        self.OpenProcess = mock.Mock(side_effect=self.open_process)
        self.IsProcessInJob = mock.Mock(side_effect=self.is_member)
        self.TerminateJobObject = mock.Mock(side_effect=self.terminate)
        self.WaitForSingleObject = mock.Mock(side_effect=self.wait)
        self.CloseHandle = mock.Mock(side_effect=self.close)

    def query(self, job, info_class, result, size, returned):
        if job != self.job_handle:
            raise AssertionError("query must address the owned Job")
        value = result._obj
        if info_class == 1:
            value.TotalProcesses = self.total
            value.ActiveProcesses = 0 if self.terminated else len(self.pids)
        elif info_class == 3:
            value.NumberOfAssignedProcesses = len(self.pids)
            value.NumberOfProcessIdsInList = min(
                len(value.ProcessIdList), len(self.pids)
            )
            for index in range(value.NumberOfProcessIdsInList):
                value.ProcessIdList[index] = self.pids[index]
        else:
            raise AssertionError("unexpected Job query")
        return True

    def open_process(self, access, inherit, pid):
        if pid not in self.pids or inherit:
            raise AssertionError("only owned non-inherited process handles may open")
        handle = 1000 + pid
        self.handles[handle] = pid
        return handle

    def is_member(self, handle, job, result):
        result._obj.value = job == self.job_handle and self.handles[handle] in self.pids
        return True

    def terminate(self, job, exit_code):
        if job != self.job_handle:
            raise AssertionError("must not terminate an unrelated Job")
        self.terminated = True
        self.terminated_at = self.clock.now
        return True

    def wait(self, handle, milliseconds):
        pid = self.handles[handle]
        self.wait_budgets.append(milliseconds)
        if not self.terminated:
            raise AssertionError("must request termination before waiting")
        signals_at = self.terminated_at + self.signal_delays[pid]
        if signals_at > self.clock.now + milliseconds / 1000:
            self.clock.now += milliseconds / 1000
            return 258
        self.clock.now = max(self.clock.now, signals_at)
        self.signaled.add(pid)
        return 0

    def close(self, handle):
        del self.handles[handle]
        self.closed.append(handle)
        return True


@contextlib.contextmanager
def modeled_job(kernel):
    with mock.patch.object(ctypes, "WinDLL", return_value=kernel, create=True):
        with mock.patch.object(native, "time", kernel.clock):
            job = native._WindowsJob()
            try:
                yield job
            finally:
                job.close()


class JobHandleDrainTests(unittest.TestCase):
    def test_zero_accounting_does_not_bypass_unsignaled_owned_handles(self):
        kernel = JobKernel(JobClock())
        with modeled_job(kernel) as job:
            job.terminate_and_wait(timeout=1)
            self.assertEqual(kernel.signaled, set(kernel.pids))
            self.assertEqual(kernel.handles, {kernel.job_handle: None})
        self.assertEqual(kernel.handles, {})

    def test_all_handle_waits_share_one_deadline(self):
        clock = JobClock()
        kernel = JobKernel(clock)
        kernel.signal_delays = {11: 0.06, 22: 0.2}
        with modeled_job(kernel) as job:
            with self.assertRaisesRegex(
                native.AcceptanceFailure, "windows_job_process_wait_timeout"
            ):
                job.terminate_and_wait(timeout=0.1)
            self.assertEqual(kernel.signaled, {11})
            self.assertLessEqual(clock.now, 0.1)
            self.assertEqual(kernel.handles, {kernel.job_handle: None})
        self.assertEqual(kernel.handles, {})

    def test_capture_time_consumes_the_same_deadline(self):
        clock = JobClock()
        kernel = JobKernel(clock)

        def slow_open(*args):
            clock.now += 0.04
            return kernel.open_process(*args)

        kernel.OpenProcess.side_effect = slow_open
        with modeled_job(kernel) as job:
            with self.assertRaisesRegex(
                native.AcceptanceFailure, "windows_job_process_wait_timeout"
            ):
                job.terminate_and_wait(timeout=0.1)
        self.assertLessEqual(clock.now, 0.1)
        self.assertEqual(kernel.handles, {})

    def test_more_than_64_handles_are_all_waited_and_closed(self):
        kernel = JobKernel(JobClock(), pids=tuple(range(1, 71)))
        with modeled_job(kernel) as job:
            job.terminate_and_wait(timeout=1)
            self.assertEqual(kernel.signaled, set(kernel.pids))
        self.assertEqual(kernel.handles, {})

    def test_query_failures_never_accept_shutdown_and_close_captured_handles(self):
        for failed_stage in ("initial", "list", "captured", "terminated"):
            with self.subTest(stage=failed_stage):
                kernel = JobKernel(JobClock())
                account_queries = 0

                def query(job, kind, *args):
                    nonlocal account_queries
                    if kind == 1:
                        account_queries += 1
                    if (
                        (failed_stage == "initial" and kind == 1)
                        or (failed_stage == "list" and kind == 3)
                        or (failed_stage == "captured" and account_queries == 2)
                        or (failed_stage == "terminated" and kernel.terminated)
                    ):
                        return False
                    return kernel.query(job, kind, *args)

                kernel.QueryInformationJobObject.side_effect = query
                with modeled_job(kernel) as job:
                    with self.assertRaises(native.AcceptanceFailure):
                        job.terminate_and_wait(timeout=1)
                self.assertEqual(kernel.handles, {})

    def test_incomplete_or_invalid_pid_lists_fail_closed(self):
        for kind in ("incomplete", "duplicate", "zero"):
            with self.subTest(kind=kind):
                kernel = JobKernel(JobClock())

                def query(job, info, result, *args):
                    ok = kernel.query(job, info, result, *args)
                    if info == 3:
                        ids = result._obj
                        if kind == "incomplete":
                            ids.NumberOfAssignedProcesses += 1
                        else:
                            ids.ProcessIdList[1] = 11 if kind == "duplicate" else 0
                    return ok

                kernel.QueryInformationJobObject.side_effect = query
                with modeled_job(kernel) as job:
                    with self.assertRaises(native.AcceptanceFailure):
                        job.terminate_and_wait(timeout=1)
                    self.assertFalse(kernel.terminated)
                self.assertEqual(kernel.handles, {})

    def test_open_or_membership_failure_closes_every_acquired_handle(self):
        for failure in ("open", "membership_query", "reused_pid"):
            with self.subTest(failure=failure):
                kernel = JobKernel(JobClock())

                def open_process(access, inherit, pid):
                    if pid == 22 and failure == "open":
                        return None
                    handle = kernel.open_process(access, inherit, pid)
                    if pid == 22 and failure == "reused_pid":
                        kernel.handles[handle] = 99
                    return handle

                def is_member(handle, *args):
                    if handle == 1022 and failure == "membership_query":
                        return False
                    return kernel.is_member(handle, *args)

                kernel.OpenProcess.side_effect = open_process
                kernel.IsProcessInJob.side_effect = is_member
                with modeled_job(kernel) as job:
                    with self.assertRaises(native.AcceptanceFailure):
                        job.terminate_and_wait(timeout=1)
                    self.assertFalse(kernel.terminated)
                self.assertEqual(kernel.handles, {})

    def test_new_processes_during_capture_termination_or_wait_fail_closed(self):
        for stage in ("capture", "terminate", "wait"):
            with self.subTest(stage=stage):
                kernel = JobKernel(JobClock())

                def changing_call(operation, *args):
                    result = operation(*args)
                    kernel.total += 1
                    return result

                function = {
                    "capture": kernel.OpenProcess,
                    "terminate": kernel.TerminateJobObject,
                    "wait": kernel.WaitForSingleObject,
                }[stage]
                original = function.side_effect
                function.side_effect = lambda *args: changing_call(original, *args)
                with modeled_job(kernel) as job:
                    with self.assertRaisesRegex(
                        native.AcceptanceFailure, "windows_job_process_churn"
                    ):
                        job.terminate_and_wait(timeout=1)
                self.assertEqual(kernel.handles, {})

    def test_wait_failure_and_unexpected_wait_result_fail_closed(self):
        for result in (0xFFFFFFFF, 0x80):
            with self.subTest(result=result):
                kernel = JobKernel(JobClock())
                kernel.WaitForSingleObject.side_effect = None
                kernel.WaitForSingleObject.return_value = result
                with modeled_job(kernel) as job:
                    with self.assertRaisesRegex(
                        native.AcceptanceFailure, "windows_job_process_wait"
                    ):
                        job.terminate_and_wait(timeout=1)
                self.assertEqual(kernel.handles, {})

    def test_termination_failure_closes_captured_handles(self):
        kernel = JobKernel(JobClock())
        kernel.TerminateJobObject.side_effect = None
        kernel.TerminateJobObject.return_value = False
        with modeled_job(kernel) as job:
            with self.assertRaisesRegex(
                native.AcceptanceFailure, "windows_job_terminate"
            ):
                job.terminate_and_wait(timeout=1)
        self.assertEqual(kernel.handles, {})

    def test_handle_close_failure_does_not_skip_other_handles(self):
        kernel = JobKernel(JobClock())

        def close(handle):
            if handle == 1022:
                return False
            return kernel.close(handle)

        kernel.CloseHandle.side_effect = close
        with modeled_job(kernel) as job:
            with self.assertRaisesRegex(
                native.AcceptanceFailure, "windows_job_process_close"
            ):
                job.terminate_and_wait(timeout=1)
        self.assertEqual(kernel.handles, {1022: 22})

    def test_empty_initial_accounting_still_checks_the_process_list(self):
        kernel = JobKernel(JobClock(), pids=())

        def new_process(job, kind, *args):
            if kind == 3:
                kernel.pids = (11,)
                kernel.total += 1
            return kernel.query(job, kind, *args)

        kernel.QueryInformationJobObject.side_effect = new_process
        with modeled_job(kernel) as job:
            with self.assertRaises(native.AcceptanceFailure):
                job.terminate_and_wait(timeout=1)
        self.assertEqual(kernel.handles, {})

    def test_empty_stable_job_requires_no_process_handles(self):
        kernel = JobKernel(JobClock(), pids=())
        with modeled_job(kernel) as job:
            job.terminate_and_wait(timeout=1)
            self.assertEqual(kernel.wait_budgets, [])
        self.assertEqual(kernel.handles, {})

    def test_signaled_handles_do_not_bypass_nonzero_final_accounting(self):
        clock = JobClock()
        kernel = JobKernel(clock)

        def query(job, kind, result, *args):
            ok = kernel.query(job, kind, result, *args)
            if kind == 1 and kernel.terminated:
                result._obj.ActiveProcesses = 1
            return ok

        kernel.QueryInformationJobObject.side_effect = query
        with modeled_job(kernel) as job:
            with self.assertRaisesRegex(
                native.AcceptanceFailure, "windows_job_drain_timeout"
            ):
                job.terminate_and_wait(timeout=0.1)
        self.assertEqual(kernel.signaled, set(kernel.pids))
        self.assertLessEqual(clock.now, 0.1)
        self.assertEqual(kernel.handles, {})

    def test_capture_rejects_excessive_process_counts(self):
        kernel = JobKernel(JobClock(), pids=tuple(range(1, 4098)))
        with modeled_job(kernel) as job:
            with self.assertRaisesRegex(
                native.AcceptanceFailure, "windows_job_process_limit"
            ):
                job.terminate_and_wait(timeout=1)
            self.assertFalse(kernel.terminated)
        self.assertEqual(kernel.handles, {})

    def test_invalid_deadlines_cannot_start_termination(self):
        for timeout in (0, -1, 301, float("nan"), float("inf")):
            with self.subTest(timeout=timeout):
                kernel = JobKernel(JobClock())
                with modeled_job(kernel) as job:
                    with self.assertRaisesRegex(
                        native.AcceptanceFailure, "windows_job_drain_timeout_range"
                    ):
                        job.terminate_and_wait(timeout=timeout)
                    self.assertFalse(kernel.terminated)
                self.assertEqual(kernel.handles, {})


class OwnedProcessTests(unittest.TestCase):
    def test_job_drain_waits_until_query_reports_no_active_processes(self):
        active_counts = iter([2, 1, 0])

        class Clock:
            now = 0.0

            @classmethod
            def monotonic(cls):
                return cls.now

            @classmethod
            def sleep(cls, duration):
                cls.now += duration

        with mock.patch.object(native, "time", Clock):
            native._wait_for_job_drain(lambda: next(active_counts), deadline=1)

        self.assertEqual(Clock.now, 0.1)

    def test_job_drain_fails_closed_at_the_bounded_timeout(self):
        class Clock:
            now = 0.0

            @classmethod
            def monotonic(cls):
                return cls.now

            @classmethod
            def sleep(cls, duration):
                cls.now += duration

        with mock.patch.object(native, "time", Clock):
            with self.assertRaisesRegex(
                native.AcceptanceFailure, "windows_job_drain_timeout"
            ):
                native._wait_for_job_drain(lambda: 1, deadline=0.1)

        self.assertEqual(Clock.now, 0.1)

    def test_child_gate_preserves_following_stdin_bytes(self):
        payload = b'{"synthetic":"browser-input"}'
        result = subprocess.run(
            [
                sys.executable,
                native.__file__,
                "--owned-child",
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())",
            ],
            input=b"GO\n" + payload,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, payload)

    def test_child_gate_rejects_invalid_or_incomplete_signal_without_spawn(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "spawned"
            for gate in (b"", b"G", b"NO\n", b"GO\r"):
                with self.subTest(gate=gate):
                    result = subprocess.run(
                        [
                            sys.executable,
                            native.__file__,
                            "--owned-child",
                            sys.executable,
                            "-c",
                            "from pathlib import Path; Path('spawned').write_text('bad')",
                        ],
                        cwd=directory,
                        input=gate,
                        capture_output=True,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 125)
                    self.assertFalse(marker.exists())

    def test_startup_diagnostics_retain_identifiers_without_messages_or_key(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "process.log"
            log.write_text(
                "Authorization: Bearer synthetic_secret\nCookie: private\n"
                "ModuleNotFoundError: No module named 'actions.missing'\n"
                "ImportError: cannot import name 'private' from 'actions.core' (/private/path)\n"
                "ModuleNotFoundError: No module named 'synthetic_secret'\n"
            )
            self.assertEqual(
                native.startup_diagnostics(log, 7, "synthetic_secret"),
                {
                    "exit_code": 7,
                    "exception_classes": ["ModuleNotFoundError", "ImportError"],
                    "import_modules": ["actions.missing", "actions.core"],
                    "traceback_frames": [],
                    "markers": [],
                    "log_sources_present": 1,
                },
            )

    def test_startup_diagnostics_normalize_colored_prefixed_secondary_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "process.log"
            log.write_text(
                "\x1b[31mERROR:   OSError: private message [WinError 6]\x1b[0m\n"
            )
            (root / "server_log.txt").write_text(
                "Traceback (most recent call last):\n"
                '  File "C:\\private\\user\\_server.py", line 123, in start\n'
                "    private_source_with_secret()\n"
                "ERROR: ModuleNotFoundError: No module named 'actions.missing'\n"
                "Cookie: ModuleNotFoundError: No module named 'private.cookie'\n"
            )
            result = native.startup_diagnostics(log, 1, "synthetic_secret")
            self.assertEqual(
                result["exception_classes"], ["OSError", "ModuleNotFoundError"]
            )
            self.assertEqual(result["import_modules"], ["actions.missing"])
            self.assertEqual(
                result["traceback_frames"],
                [{"file": "_server.py", "line": 123, "function": "start"}],
            )
            self.assertEqual(
                result["markers"], ["python_traceback", "invalid_windows_handle"]
            )
            self.assertEqual(result["log_sources_present"], 2)
            self.assertNotIn("private", str(result))

    @unittest.skipUnless(os.name == "nt", "Requires real Windows path aliases")
    def test_artifact_root_accepts_short_names_and_rejects_junctions(self):
        import ctypes
        from ctypes import wintypes
        from actions.server._artifact_storage import (
            create_artifact_storage,
            ArtifactStorageConfigurationError,
        )

        kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)
        kernel.GetShortPathNameW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        kernel.GetShortPathNameW.restype = wintypes.DWORD
        with tempfile.TemporaryDirectory(
            prefix="actions-native-long-directory-"
        ) as directory:
            root = Path(directory).resolve()
            buffer = ctypes.create_unicode_buffer(32768)
            length = kernel.GetShortPathNameW(str(root), buffer, len(buffer))
            self.assertTrue(0 < length < len(buffer))
            alias = Path(buffer.value)
            self.assertNotEqual(
                alias, root, "Windows CI must provide an actual 8.3 alias"
            )
            storage = create_artifact_storage("local", alias)
            self.assertEqual(storage.root, root)
            storage.create_run_artifacts_dir("run-a")
            junction = root / "junction"
            target = root / "target"
            target.mkdir()
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0)
            try:
                with self.assertRaises(ArtifactStorageConfigurationError):
                    create_artifact_storage("local", junction)
                with self.assertRaises(ArtifactStorageConfigurationError):
                    storage.create_run_artifacts_dir("junction/run-b")
                target.rmdir()
                self.assertFalse(junction.exists())
                with self.assertRaises(ArtifactStorageConfigurationError):
                    storage.create_run_artifacts_dir("junction/run-c")
            finally:
                junction.rmdir()

    @unittest.skipUnless(os.name == "nt", "Requires real Windows Job Objects")
    def test_job_drains_descendant_handle_before_owned_process_returns(self):
        import ctypes
        from ctypes import wintypes

        kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.TerminateProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        kernel.IsProcessInJob.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.BOOL),
        ]
        kernel.IsProcessInJob.restype = wintypes.BOOL

        class ProcessIds(ctypes.Structure):
            _fields_ = [
                ("assigned", wintypes.DWORD),
                ("listed", wintypes.DWORD),
                ("pids", ctypes.c_size_t * 64),
            ]

        diagnostics = []
        drain_observations = {"phase": "drain_queries", "count": 0}
        jobs = []
        handle = None

        def snapshot(job, phase):
            # Fixed fields and a capped PID list only: no paths, logs or messages.
            result = {"phase": phase}
            diagnostics.append(result)
            try:
                # Observe the held handle before diagnostic queries add latency.
                if handle:
                    result["descendant_wait"] = kernel.WaitForSingleObject(handle, 0)
                    result["descendant_pid"] = pid
                    member = wintypes.BOOL()
                    ok = kernel.IsProcessInJob(
                        handle, job._handle, ctypes.byref(member)
                    )
                    result["membership_query_ok"] = bool(ok)
                    if ok:
                        result["descendant_in_job"] = bool(member.value)
                    else:
                        result["membership_error"] = ctypes.get_last_error()
                accounting = job._basic_accounting()
                ok = job._kernel.QueryInformationJobObject(
                    job._handle,
                    1,
                    ctypes.byref(accounting),
                    ctypes.sizeof(accounting),
                    None,
                )
                result["accounting_query_ok"] = bool(ok)
                if ok:
                    result["active"] = accounting.ActiveProcesses
                    result["total"] = accounting.TotalProcesses
                else:
                    result["accounting_error"] = ctypes.get_last_error()
                ids = ProcessIds()
                ok = job._kernel.QueryInformationJobObject(
                    job._handle, 3, ctypes.byref(ids), ctypes.sizeof(ids), None
                )
                result["pid_query_ok"] = bool(ok)
                if not ok:
                    result["pid_query_error"] = ctypes.get_last_error()
                result["assigned"] = ids.assigned
                result["listed"] = ids.listed
                result["pids"] = list(ids.pids[: min(ids.listed, 64)])
                result["pid_list_complete"] = (
                    bool(ok) and ids.listed == ids.assigned and ids.listed <= 64
                )
            except Exception:
                # Diagnostics must never replace the original assertion/failure.
                result["diagnostic_error"] = True

        class DiagnosticJob(native._WindowsJob):
            def __init__(self):
                super().__init__()
                jobs.append(self)

            def terminate_and_wait(self, *, timeout=10):
                snapshot(self, "before_drain")
                return super().terminate_and_wait(timeout=timeout)

            def active_process_count(self):
                # Retain the existing query result; add no native query or wait
                # between production termination and the strict assertion.
                count = super().active_process_count()
                if not drain_observations["count"]:
                    drain_observations["first_active"] = count
                drain_observations["count"] += 1
                drain_observations["last_active"] = count
                drain_observations["last_observed_at"] = native.time.monotonic()
                return count

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            leader = (
                "import subprocess,sys; from pathlib import Path; "
                "child=subprocess.Popen([sys.executable,'-c',"
                '\'import time; from pathlib import Path; f=Path("held.txt").open("w"); '
                'f.write("held"); f.flush(); Path("descendant.ready").write_text("ready"); '
                "time.sleep(60)'],"
                "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                "Path('descendant.pid').write_text(str(child.pid))"
            )
            patcher = mock.patch.object(native, "_WindowsJob", DiagnosticJob)
            patcher.start()
            try:
                with native.owned_process(
                    [sys.executable, "-c", leader],
                    cwd=root,
                    env=dict(os.environ),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ) as process:
                    self.assertEqual(process.wait(timeout=10), 0)
                    pid = int((root / "descendant.pid").read_text())
                    deadline = native.time.monotonic() + 5
                    while not (root / "descendant.ready").exists():
                        self.assertLess(native.time.monotonic(), deadline)
                        native.time.sleep(0.01)
                    # Hold the exact process handle so PID reuse cannot affect proof.
                    handle = kernel.OpenProcess(
                        0x00100000 | 0x1000 | 0x0001, False, pid
                    )
                    self.assertTrue(handle)
                    self.assertEqual(kernel.WaitForSingleObject(handle, 0), 258)
                    member = wintypes.BOOL()
                    self.assertTrue(
                        kernel.IsProcessInJob(
                            handle, jobs[-1]._handle, ctypes.byref(member)
                        )
                    )
                    self.assertTrue(
                        member.value, "descendant must belong to the exact owned Job"
                    )
                # This must remain the first native observation after return.
                returned_wait = kernel.WaitForSingleObject(handle, 0)
                diagnostics.append(
                    {"phase": "after_context", "descendant_wait": returned_wait}
                )
                self.assertEqual(returned_wait, 0)
                (root / "held.txt").unlink()
            finally:
                patcher.stop()
                if handle:
                    diagnostics.append(
                        {
                            "phase": "before_cleanup",
                            "descendant_wait": kernel.WaitForSingleObject(handle, 0),
                        }
                    )
                    # Clean up even when the old, faulty implementation fails this test.
                    kernel.TerminateProcess(handle, 1)
                    kernel.WaitForSingleObject(handle, 5000)
                    kernel.CloseHandle(handle)
                diagnostics.append(drain_observations)
                print(
                    "WINDOWS_JOB_DIAGNOSTICS " + json.dumps(diagnostics, sort_keys=True)
                )

    @unittest.skipUnless(os.name == "nt", "Requires real Windows Job Objects")
    def test_job_drains_descendant_and_grandchild_handles_before_return(self):
        from ctypes import wintypes

        kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.TerminateProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handles = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def hold_file(name):
                return (
                    "import os,time; from pathlib import Path; "
                    f"stream=Path('{name}.held').open('w'); "
                    f"Path('{name}.pid').write_text(str(os.getpid())); "
                    f"Path('{name}.ready').write_text('ready'); time.sleep(60)"
                )

            def spawn(code):
                return (
                    "import subprocess,sys; "
                    f"subprocess.Popen([sys.executable,'-c',{code!r}], "
                    "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
                    "stderr=subprocess.DEVNULL); "
                )

            leader = spawn(spawn(hold_file("grandchild")) + hold_file("child"))
            try:
                with native.owned_process(
                    [sys.executable, "-c", leader],
                    cwd=root,
                    env=dict(os.environ),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ) as process:
                    self.assertEqual(process.wait(timeout=10), 0)
                    deadline = native.time.monotonic() + 5
                    for name in ("child", "grandchild"):
                        ready = root / f"{name}.ready"
                        while not ready.exists():
                            self.assertLess(native.time.monotonic(), deadline)
                            native.time.sleep(0.01)
                        pid = int((root / f"{name}.pid").read_text())
                        handle = kernel.OpenProcess(0x00100000 | 0x0001, False, pid)
                        self.assertTrue(handle)
                        handles.append(handle)
                        self.assertEqual(kernel.WaitForSingleObject(handle, 0), 258)
                returned_waits = [kernel.WaitForSingleObject(h, 0) for h in handles]
                self.assertEqual(returned_waits, [0, 0])
                for name in ("child", "grandchild"):
                    (root / f"{name}.held").unlink()
            finally:
                for handle in handles:
                    kernel.TerminateProcess(handle, 1)
                    kernel.WaitForSingleObject(handle, 5000)
                    kernel.CloseHandle(handle)


if __name__ == "__main__":
    unittest.main()
