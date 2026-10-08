"""Gate semantics everywhere; real Job lifetime assertions on Windows only."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import verify_native_acceptance as native


class OwnedProcessTests(unittest.TestCase):
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
                },
            )

    @unittest.skipUnless(os.name == "nt", "Requires real Windows Job Objects")
    def test_job_closes_descendant_after_its_leader_exits(self):
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
        handle = None
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            leader = (
                "import subprocess,sys; from pathlib import Path; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],"
                "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                "Path('descendant.pid').write_text(str(child.pid))"
            )
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
                    # Hold the exact process handle so PID reuse cannot affect proof.
                    handle = kernel.OpenProcess(0x00100000 | 0x0001, False, pid)
                    self.assertTrue(handle)
                    self.assertEqual(kernel.WaitForSingleObject(handle, 0), 258)
                self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
            finally:
                if handle:
                    # Clean up even when the old, faulty implementation fails this test.
                    kernel.TerminateProcess(handle, 1)
                    kernel.WaitForSingleObject(handle, 5000)
                    kernel.CloseHandle(handle)


if __name__ == "__main__":
    unittest.main()
