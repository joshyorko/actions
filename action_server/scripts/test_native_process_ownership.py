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
