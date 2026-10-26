"""One isolated, bounded canvas_get boundary observation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
import urllib.request

ROOT = Path("/workspace/327-probes/node-canvas-boundary-luna")
FIXTURE = Path("/workspace/327-probes/a53-claimed/terminal-success-failure")
PASS_FIXTURE = Path("/workspace/327-probes/node-generated-luna/modern-auto/prior-pass.json")
CANDIDATE = Path("/workspace/327-artifacts/a53")
CONSUMER = CANDIDATE / "consumer"
SOURCE = Path("/workspace/actions")
NODE = Path("/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/node"
)
SDK = SOURCE / "action_server/frontend/node_modules/@modelcontextprotocol/client"
REC = {
    "status": "RUNNING",
    "scope": "single canvas_get call; stop before enqueue or capability invocation",
    "candidate": "actions-runtime 1.1.0a53; actions-core 1.1.0a8; actions-work-items 0.5.0a2",
    "node_sdk": "@modelcontextprotocol/client 2.0.0",
    "node": str(NODE),
    "protocol_expected": "2026-07-28",
    "auth_mode": "existing synthetic loopback bearer; unchanged fixture profile and grants",
    "instrumentation": {
        "location": "test-only PYTHONPATH sitecustomize import-loader transformation",
        "modules": ["actions.server.foundry.mcp", "actions.server.foundry.authoring"],
        "records": [
            "authenticated caller present",
            "Canvas port entered and returned",
            "appId parse passed",
            "read_application authorization returned",
            "latest revision found",
            "revision ownership validation returned",
            "caught exception class only",
        ],
        "does_not_record": [
            "exception messages",
            "request headers",
            "credentials",
            "source paths",
            "object values",
        ],
    },
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save():
    (ROOT / "receipt.json").write_text(json.dumps(REC, indent=2) + "\n")


def prepare():
    for child in ROOT.iterdir():
        if child.name in {
            "sitecustomize.py",
            "node_canvas_get.mjs",
            "run_probe.py",
            "supervisor-receipt.json",
            "supervisor.log",
            "attempt-2",
        }:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    for name in ("datadir", "actions-home", "robots-home", "empty"):
        shutil.copytree(FIXTURE / name, ROOT / name)
    (ROOT / "datadir" / "action_server.lock").unlink(missing_ok=True)
    (ROOT / "datadir" / "server_log.txt").unlink(missing_ok=True)
    shutil.copy2(FIXTURE / "profile.json", ROOT / "profile.json")
    shutil.copy2(FIXTURE / "robot-profile.json", ROOT / "robot-profile.json")
    shutil.copy2(PASS_FIXTURE, ROOT / "prior-pass.json")
    for path in FIXTURE.glob("authorization-*.json"):
        shutil.copy2(path, ROOT / path.name)
    REC["fixture"] = {
        "source_profile_sha256": digest(FIXTURE / "profile.json"),
        "task_profile_sha256": digest(ROOT / "profile.json"),
        "source_datadir_sqlite_sha256": digest(FIXTURE / "datadir" / "server.db"),
        "task_datadir_sqlite_sha256_before": digest(ROOT / "datadir" / "server.db"),
        "source_prior_pass_sha256": digest(PASS_FIXTURE),
        "task_prior_pass_sha256": digest(ROOT / "prior-pass.json"),
        "same_profile_bytes": digest(FIXTURE / "profile.json") == digest(ROOT / "profile.json"),
        "same_database_bytes_before": digest(FIXTURE / "datadir" / "server.db")
        == digest(ROOT / "datadir" / "server.db"),
        "app_id_source": "saved pass snapshot; exact value intentionally not copied into receipt",
        "prepared_receipt_sha256": digest(
            FIXTURE.parent / "compiler" / "prepared.json"
        ),
    }
    saved_canvas_get = json.loads(
        (FIXTURE / "evidence" / "08-canvas_get.json").read_text()
    )
    prior_pass = json.loads((ROOT / "prior-pass.json").read_text())
    required_inputs = (
        NODE,
        SDK / "package.json",
        SDK / "dist/index.mjs",
        SDK / "dist/index.d.mts",
        CONSUMER / "bin/python",
        CONSUMER / "bin/action-server",
        CONSUMER / "lib/python3.12/site-packages/actions/server/bin/rcc-18.19.3",
        FIXTURE.parent / "compiler" / "prepared.json",
        FIXTURE / "evidence" / "08-canvas_get.json",
        ROOT / "profile.json",
        ROOT / "robot-profile.json",
        ROOT / "prior-pass.json",
        ROOT / "node_canvas_get.mjs",
        ROOT / "sitecustomize.py",
        ROOT / "datadir" / "server.db",
    )
    REC["preflight"] = {
        "all_required_file_inputs_present": all(path.is_file() for path in required_inputs),
        "task_local_datadir_and_homes_present": all(
            path.is_dir()
            for path in (
                ROOT / "datadir" / "blobs",
                ROOT / "actions-home",
                ROOT / "robots-home",
                ROOT / "empty",
            )
        ),
        "prior_pass_copy_matches_source": digest(PASS_FIXTURE)
        == digest(ROOT / "prior-pass.json"),
        "app_and_revision_match_saved_canvas_result": (
            prior_pass["snapshot"]["canvas_application"]["app_id"]
            == saved_canvas_get["_meta"]["actions.canvas"]["applicationId"]
            and prior_pass["snapshot"]["deployment"]["revision_id"]
            == saved_canvas_get["_meta"]["actions.canvas"]["revisionId"]
        ),
    }
    if not all(REC["preflight"].values()):
        raise RuntimeError("task_local_input_preflight_failed")
    REC["source_hashes"] = {
        "candidate_mcp_py": digest(
            CONSUMER / "lib/python3.12/site-packages/actions/server/foundry/mcp.py"
        ),
        "candidate_authoring_py": digest(
            CONSUMER / "lib/python3.12/site-packages/actions/server/foundry/authoring.py"
        ),
        "node_client_entry": digest(SDK / "dist/index.mjs"),
        "node_client_types": digest(SDK / "dist/index.d.mts"),
        "node_probe": digest(ROOT / "node_canvas_get.mjs"),
        "sitecustomize": digest(ROOT / "sitecustomize.py"),
        "controller": digest(ROOT / "run_probe.py"),
    }
    REC["installed_identity"] = json.loads(
        subprocess.check_output(
            [
                str(CONSUMER / "bin/python"),
                "-c",
                "import actions.server,importlib.metadata,json;print(json.dumps({'runtime':importlib.metadata.version('actions-runtime'),'core':importlib.metadata.version('actions-core'),'work_items':importlib.metadata.version('actions-work-items'),'server':actions.server.__file__}))",
            ],
            text=True,
        )
    )
    if REC["installed_identity"]["runtime"] != "1.1.0a53":
        raise RuntimeError("candidate_runtime_identity_mismatch")
    REC["node_version"] = subprocess.check_output(
        [str(NODE), "-p", "process.version"], text=True
    ).strip()
    REC["node_undici_version"] = subprocess.check_output(
        [str(NODE), "-p", "process.versions.undici"], text=True
    ).strip()


def server_env():
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(("PYTHON", "ACTIONS_", "ROBOCORP_", "RC_")):
            env.pop(key, None)
    env.pop("VIRTUAL_ENV", None)
    env.update(
        OMP_NUM_THREADS="1",
        ACTIONS_HOME=str(ROOT / "actions-home"),
        ROBOTS_HOME=str(ROOT / "robots-home"),
        ROBOCORP_HOME="/workspace/327-probes/a53-claimed/compiler/robocorp",
        PYTHON_EXE=str(CONSUMER / "bin/python"),
        ACTIONS_FOUNDRY_EXECUTION_PROFILE=str(ROOT / "profile.json"),
        ACTIONS_FOUNDRY_ROBOT_PROFILE=str(ROOT / "robot-profile.json"),
        ACTIONS_CANVAS_PROBE_ENABLE="1",
        ACTIONS_CANVAS_PROBE_EVENTS=str(ROOT / "boundary-events.jsonl"),
        PYTHONPATH=str(ROOT),
    )
    env["PATH"] = (
        str(CONSUMER / "bin")
        + ":/workspace/actions-cloud/bin:"
        + env.get("PATH", "")
    )
    return env


def start_server(port, key, env):
    log = (ROOT / "runtime.log").open("w", encoding="utf-8")
    command = [
        str(CONSUMER / "bin/action-server"),
        "start",
        "--address",
        "127.0.0.1",
        "--port",
        str(port),
        "--datadir",
        str(ROOT / "datadir"),
        "--actions-sync=false",
        "--api-key=" + key,
        "--cors-allow-origin",
        "http://localhost:8080",
    ]
    proc = subprocess.Popen(
        command,
        cwd=ROOT / "empty",
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("runtime_exited_before_readiness")
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/managed-work-items/v1/schema",
                headers={"Authorization": "Bearer " + key},
            )
            with urllib.request.urlopen(request, timeout=1) as response:
                if response.status == 200:
                    return proc, log
        except Exception:
            pass
        time.sleep(0.2)
    raise TimeoutError("runtime_readiness_deadline")


def stop_server(pair):
    proc, log = pair
    path = ROOT / "datadir" / "server_log.txt"
    offset = path.stat().st_size if path.exists() else 0
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
    try:
        code = proc.wait(timeout=25)
    except subprocess.TimeoutExpired:
        REC["runtime_forced_cleanup"] = True
        proc.kill()
        code = proc.wait(timeout=5)
    finally:
        log.close()
    tail = (
        path.read_bytes()[offset:].decode("utf-8", errors="replace")
        if path.exists()
        else ""
    )
    REC["runtime_shutdown"] = {
        "exit_code": code,
        "graceful_lifespan": (
            "Application shutdown complete." in tail
            and f"Finished server process [{proc.pid}]" in tail
            and "Application shutdown failed." not in tail
        ),
    }
    if code not in (0, -signal.SIGTERM) or not REC["runtime_shutdown"]["graceful_lifespan"]:
        raise RuntimeError("runtime_graceful_shutdown_not_confirmed")


def run_client(port, key, env):
    client_env = dict(
        env,
        NODE_SDK_ROOT=str(SDK),
        RUNTIME_ENDPOINT=f"http://127.0.0.1:{port}/mcp",
        RUNTIME_BEARER=key,
        PROBE_ROOT=str(ROOT),
    )
    log_path = ROOT / "node-client.jsonl"
    with log_path.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(
            [str(NODE), str(ROOT / "node_canvas_get.mjs")],
            cwd=ROOT / "empty",
            env=client_env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            raise TimeoutError("node_canvas_get_deadline")
    REC["client"] = {
        "exit_code": code,
        "natural_exit": True,
        "events": [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ],
    }
    REC["client"]["stage"] = next(
        (event.get("stage") for event in REC["client"]["events"] if event.get("event") == "client_failure"),
        "canvas_get_response" if any(event.get("event") == "canvas_get_response" for event in REC["client"]["events"]) else "completed_without_failure_event",
    )
    if code != 0:
        raise RuntimeError("node_client_probe_failed")


def main():
    phase = "prepare_and_preflight"
    prepare()
    with socket.socket() as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        port = server_socket.getsockname()[1]
    key = __import__("secrets").token_urlsafe(32)
    env = server_env()
    pair = None
    save()
    try:
        phase = "runtime_start_and_readiness"
        pair = start_server(port, key, env)
        REC["runtime_ready"] = True
        save()
        phase = "node_client"
        run_client(port, key, env)
        REC["authorization_boundary_events"] = (
            [
                json.loads(line)
                for line in (ROOT / "boundary-events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
            if (ROOT / "boundary-events.jsonl").exists()
            else []
        )
        phase = "runtime_shutdown"
        stop_server(pair)
        pair = None
        REC["task_datadir_sqlite_sha256_after"] = digest(
            ROOT / "datadir" / "server.db"
        )
        REC["status"] = "PASS" if (
            REC["client"]["natural_exit"]
            and REC["runtime_shutdown"]["graceful_lifespan"]
            and REC["client"]["exit_code"] == 0
        ) else "FAILED"
    except BaseException as error:
        REC["status"] = "FAILED"
        REC["failure_class"] = type(error).__name__
        REC["failure_phase"] = phase
        raise
    finally:
        if pair is not None:
            try:
                stop_server(pair)
            except Exception as error:
                REC["cleanup_exception_class"] = type(error).__name__
        for path in ROOT.glob("*.log"):
            path.write_text(
                path.read_text(encoding="utf-8", errors="replace").replace(
                    key, "[REDACTED_SYNTHETIC_KEY]"
                ),
                encoding="utf-8",
            )
        save()


if __name__ == "__main__":
    main()
