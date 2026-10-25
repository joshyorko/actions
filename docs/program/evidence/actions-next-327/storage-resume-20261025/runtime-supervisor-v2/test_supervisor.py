"""No PostgreSQL/RCC: only receipt objects and owned dummy Python processes."""
import ctypes
import importlib.util
import json
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def load(name):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


supervisor = load("supervise")
plugin = load("progress_plugin")


class Tests(unittest.TestCase):
    def test_pass_requires_clean_unchanged_source_and_session_finish(self):
        before = {"source_sha": "a" * 40, "worktree_clean": True, "source_tests_fingerprint": "one"}
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "progress.jsonl"
            self.assertFalse(supervisor.passes_gate(0, None, before, before, p))
            p.write_text(json.dumps({"event": "session_finish", "exitstatus": 0}) + "\n")
            self.assertTrue(supervisor.passes_gate(0, None, before, before, p))
            for key, value in [("source_sha", "b" * 40), ("worktree_clean", False),
                               ("source_tests_fingerprint", "two")]:
                self.assertFalse(supervisor.passes_gate(0, None, before, dict(before, **{key: value}), p))
            self.assertFalse(supervisor.passes_gate(0, "disk_floor", before, before, p))
            p.write_text(json.dumps({"event": "session_finish", "exitstatus": 2}) + "\n")
            self.assertFalse(supervisor.passes_gate(0, None, before, before, p))

    def test_source_snapshot_detects_dirty_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = root / "action_server"
            (package / "src").mkdir(parents=True)
            (package / "tests").mkdir()
            (package / "pyproject.toml").write_text("version='one'")
            path = package / "src/a.py"
            path.write_text("one")
            with patch.object(supervisor.subprocess, "check_output", side_effect=["a"*40, b""]):
                first = supervisor.source_snapshot(root)
            path.write_text("two")
            with patch.object(supervisor.subprocess, "check_output", side_effect=["a"*40, b" M a.py"]):
                second = supervisor.source_snapshot(root)
            self.assertTrue(first["worktree_clean"])
            self.assertFalse(second["worktree_clean"])
            self.assertNotEqual(first["source_tests_fingerprint"], second["source_tests_fingerprint"])

    def test_sigterm_routes_to_finally(self):
        with tempfile.TemporaryDirectory() as folder:
            receipt = Path(folder) / "finally.txt"
            code = ("import importlib.util,os,signal,sys;"
                    "s=importlib.util.spec_from_file_location('s',sys.argv[1]);"
                    "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                    "m.install_stop_handlers()\n"
                    "try: os.kill(os.getpid(),signal.SIGTERM)\n"
                    "except m.SupervisorStop: pass\n"
                    "finally:\n"
                    " os.kill(os.getpid(),signal.SIGTERM)\n"
                    " open(sys.argv[2],'w').write('cleanup reached')\n")
            result = subprocess.run([sys.executable, "-c", code, str(Path(supervisor.__file__)), str(receipt)],
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(receipt.read_text(), "cleanup reached")

    def test_escalation_for_unresponsive_dummy(self):
        original = supervisor.shutdown
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "dummy.log"
            program = "import signal,time;signal.signal(signal.SIGINT,signal.SIG_IGN);signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(20)"
            with patch.object(supervisor, "shutdown", lambda p: original(p, (
                (signal.SIGINT, .2), (signal.SIGTERM, .2), (signal.SIGKILL, 1)))):
                code, reason = supervisor.run_process([sys.executable, "-c", program], {},
                    output, .4, 0, capacity=False)
            self.assertEqual((code, reason), (-9, "deadline"))
            stages = json.loads(output.with_suffix('.process.json').read_text())["shutdown"]
            self.assertEqual([s["signal"] for s in stages], ["SIGINT", "SIGTERM", "SIGKILL"])

    def test_receipt_does_not_capture_traceback_or_parameter_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "progress.jsonl"
            reporter = plugin.Progress(p)
            reporter.pytest_sessionstart(None)
            reporter.pytest_runtest_logreport(SimpleNamespace(
                nodeid="tests/test_a.py::test_a[token-secret]", when="call", outcome="failed",
                duration=.2, longrepr="do not serialize secret traceback"))
            partial = supervisor.summary(p)
            self.assertEqual(partial["phase_counts"], {"call:failed": 1})
            self.assertIsNone(partial["pytest_session_finish"])
            reporter.pytest_sessionfinish(None, 1)
            self.assertNotIn("token-secret", p.read_text())
            self.assertNotIn("traceback", p.read_text())
            self.assertEqual(supervisor.summary(p)["pytest_session_finish"]["exitstatus"], 1)

    def test_secret_split_across_writes_is_redacted(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "dummy.log"
            code, reason = supervisor.run_process(
                [sys.executable, "-c", "import os,time;os.write(1,b'abc');time.sleep(.1);os.write(1,b'def\\n')"],
                {}, output, 5, 0, ("abcdef",), capacity=False)
            self.assertEqual((code, reason), (0, None))
            self.assertEqual(output.read_text(), "[redacted]\n")
            self.assertEqual(json.loads(output.with_suffix('.process.json').read_text())["shutdown"], [])

    def test_deadline_interrupt_preserves_child_receipt_and_reaps_session(self):
        libc = ctypes.CDLL(None)
        previous = ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(previous), 0, 0, 0), 0)
        self.assertEqual(libc.prctl(36, 1, 0, 0, 0), 0)
        try:
            with tempfile.TemporaryDirectory() as folder:
                receipt = Path(folder) / "flushed.json"
                output = Path(folder) / "dummy.log"
                child = ("import signal,time,sys;from pathlib import Path;"
                         "signal.signal(signal.SIGINT,lambda *a:(Path(sys.argv[1]).write_text('flushed'),sys.exit(0)));"
                         "print('ready',flush=True);time.sleep(20)")
                code, reason = supervisor.run_process([sys.executable, "-c", child, str(receipt)],
                    {}, output, .4, 0, capacity=False)
                self.assertEqual(reason, "deadline")
                self.assertEqual(receipt.read_text(), "flushed")
                self.assertEqual(supervisor.reap(None), [])
                self.assertEqual(json.loads(output.with_suffix('.process.json').read_text())["shutdown"][0]["signal"], "SIGINT")
        finally:
            self.assertEqual(libc.prctl(36, previous.value, 0, 0, 0), 0)

    def test_adopted_separate_session_child_is_reaped(self):
        libc = ctypes.CDLL(None)
        previous = ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(previous), 0, 0, 0), 0)
        self.assertEqual(libc.prctl(36, 1, 0, 0, 0), 0)
        try:
            with tempfile.TemporaryDirectory() as folder:
                output = Path(folder) / "dummy.log"
                program = "import subprocess,sys;subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'],start_new_session=True)"
                _, reason = supervisor.run_process([sys.executable, "-c", program], {},
                    output, .4, 0, capacity=False)
                self.assertEqual(reason, "deadline")
                self.assertEqual(supervisor.reap(None), [])
        finally:
            self.assertEqual(libc.prctl(36, previous.value, 0, 0, 0), 0)


if __name__ == "__main__":
    unittest.main()
