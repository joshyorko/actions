"""One bounded idle installed CLI smoke; no Action or tunnel invocation."""
import hashlib
import json
import os
import pathlib
import re
import secrets
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request

import psutil

from actions.server._common.process import force_kill_process_tree_until
from dataclasses import asdict


root = pathlib.Path(__file__).parent / "startup-once1"
root.mkdir(mode=0o700)
for name in ("datadir", "actions-home", "robots-home", "tmp"):
    (root / name).mkdir(mode=0o700)
current = int(pathlib.Path("/sys/fs/cgroup/memory.current").read_text())
limit = int(pathlib.Path("/sys/fs/cgroup/memory.max").read_text())
assert limit - current > 1073741824
record = {
    "scope": "installed Linux cp312 idle CLI startup only",
    "runtime_source": "23a6be5044f7a9377180f7ec7d33c50ad8c4c364",
    "runtime_version": "1.0.3",
    "public_core_helper_versions": "1.0.3",
    "visible_headroom_bytes": limit - current,
    "self_cgroup_binding": "UNQUALIFIED; no managed Action admission inferred",
    "managed_actions": 0,
    "rcc_feedback": "Normal CLI may launch shipped18.19.3 feedback metric; no environment/Action acquisition",
    "startup": "NOT_STARTED",
    "http": [],
    "cleanup": None,
}
env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "TZ") if k in os.environ}
env.update(ACTIONS_HOME=str(root / "actions-home"), ROBOTS_HOME=str(root / "robots-home"), TMPDIR=str(root / "tmp"))
with socket.socket() as reserve:
    reserve.bind(("127.0.0.1", 0))
    port = reserve.getsockname()[1]
api_key = secrets.token_urlsafe(32)
command = [sys.executable, "-m", "actions.server", "start", "--address", "127.0.0.1", "--port", str(port), "--actions-sync=false", "--min-processes", "0", "--max-processes", "1", "--api-key", api_key, "--datadir", str(root / "datadir")]
process = None
known = {}
snapshot_complete = False
started = time.monotonic()
with (root / "stdout.log").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
    os.chmod(stdout.name, 0o600)
    os.chmod(stderr.name, 0o600)
    try:
        process = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
        assert process.poll() is None
        owner = psutil.Process(process.pid)
        birth = owner.create_time()
        record["owner"] = {"pid": process.pid, "create_time": birth}
        deadline = started + 25
        ready = False
        while time.monotonic() < deadline:
            if process.poll() is not None:
                record["startup"] = "PROCESS_EXITED_BEFORE_HTTP"
                record["returncode"] = process.returncode
                break
            assert owner.create_time() == birth
            for child in owner.children(recursive=True):
                known[(child.pid, child.create_time())] = child
            snapshot_complete = True
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/openapi.json", timeout=0.5) as response:
                    raw = response.read(1048576)
                    json.loads(raw)
                    record["http"].append({"path": "/openapi.json", "status": response.status, "body_sha256": hashlib.sha256(raw).hexdigest()})
                    ready = True
                    break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        if ready:
            record["startup"] = "HTTP_READY"
            for authenticated in (False, True):
                request = urllib.request.Request(f"http://127.0.0.1:{port}/api/work-items/stats", headers={"Authorization": "Bearer " + api_key} if authenticated else {})
                try:
                    with urllib.request.urlopen(request, timeout=2) as response:
                        raw = response.read(1048576)
                        status = response.status
                except urllib.error.HTTPError as error:
                    raw = error.read(1048576)
                    status = error.code
                record["http"].append({"path": "/api/work-items/stats", "authenticated": authenticated, "status": status, "body_sha256": hashlib.sha256(raw).hexdigest()})
            assert record["http"][-2]["status"] == 401
            assert record["http"][-1]["status"] == 200
        else:
            record["startup"] = record["startup"] if record["startup"] != "NOT_STARTED" else "HTTP_DEADLINE"
    except BaseException as error:
        record["primary_error_class"] = type(error).__name__
    finally:
        if process is not None:
            record["cleanup"] = asdict(force_kill_process_tree_until(process, list(known.values()), time.monotonic() + 10, snapshot_complete))
        record["elapsed_seconds"] = time.monotonic() - started
        record["status"] = "PASS_IDLE_STARTUP_SCOPED" if record["startup"] == "HTTP_READY" and "primary_error_class" not in record and record["cleanup"] and record["cleanup"]["wrapper_reaped"] and not any(record["cleanup"][x] for x in ("live_descendant_pids", "zombie_descendant_pids", "errors")) else "FAIL"
        (root / "startup-receipt.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
raise SystemExit(0 if record["status"] == "PASS_IDLE_STARTUP_SCOPED" else 1)
