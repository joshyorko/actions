"""Scratch pytest plugin to retain the existing #153 harness diagnostics."""

import json
import os
from pathlib import Path

import psutil


def _write(name: str, value: object) -> None:
    destination = Path(os.environ["PR153_CAPTURE_DIR"]) / name
    destination.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def pytest_collection_modifyitems(items):
    _write(
        "pytest-selection.json",
        {
            "collected_nodeids": [item.nodeid for item in items],
            "collected_count": len(items),
        },
    )
    for item in items:
        if item.name != "test_live_runtime_browser_origin_and_ambient_session_matrix":
            continue

        module = item.module
        original_harness = module._run_browser_harness

        def capture_harness(*args, **kwargs):
            completed = original_harness(*args, **kwargs)
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            (Path(os.environ["PR153_CAPTURE_DIR"]) / "browser-harness-stdout.log").write_text(
                stdout.replace("test-key", "[redacted]")
            )
            (Path(os.environ["PR153_CAPTURE_DIR"]) / "browser-harness-stderr.log").write_text(
                stderr.replace("test-key", "[redacted]")
            )
            _write(
                "browser-harness-result.json",
                {
                    "returncode": completed.returncode,
                    "stdout_bytes": len(stdout.encode()),
                    "stderr_bytes": len(stderr.encode()),
                    "synthetic_key_occurrences_in_raw_stdout": stdout.count("test-key"),
                    "synthetic_key_occurrences_in_raw_stderr": stderr.count("test-key"),
                },
            )
            return completed

        module._run_browser_harness = capture_harness

        from actions.server._selftest import ActionServerProcess

        original_start = ActionServerProcess.start

        def capture_server_start(self, *args, **kwargs):
            result = original_start(self, *args, **kwargs)
            process = self.process
            root = psutil.Process(process.pid)
            processes = [root, *root.children(recursive=True)]
            snapshot = []
            for child in processes:
                try:
                    argv = [part.replace("test-key", "[redacted]") for part in child.cmdline()]
                    snapshot.append(
                        {
                            "pid": child.pid,
                            "ppid": child.ppid(),
                            "status": child.status(),
                            "name": child.name(),
                            "argv": argv,
                        }
                    )
                except psutil.Error as exc:
                    snapshot.append({"pid": child.pid, "observation_error": type(exc).__name__})
            _write(
                "runtime-process-start.json",
                {
                    "kind": "ActionServerProcess selected binary",
                    "root_pid": process.pid,
                    "process_tree_at_ready": snapshot,
                },
            )
            return result

        ActionServerProcess.start = capture_server_start

