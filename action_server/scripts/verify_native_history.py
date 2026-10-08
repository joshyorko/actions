"""Verify packaged Run history with >867 MB of temporary synthetic results."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sqlite3
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from verify_native_acceptance import NativeServer, digest, require, run_output

PACKAGE = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--node", default="node")
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("--source-sha must be a complete lowercase commit SHA")
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    count, payload_bytes = 210, 4 * 1024 * 1024
    receipt = {
        "source_sha": args.source_sha,
        "synthetic_results_bytes": count * payload_bytes,
        "run_count": count,
        "cases": [],
        "status": "IN_PROGRESS",
    }
    suffix = ".exe" if os.name == "nt" else ""
    binaries = [
        ("frozen", PACKAGE / "dist/action-server" / f"action-server{suffix}"),
        ("go-wrapper", PACKAGE / "dist/final" / f"action-server{suffix}"),
    ]
    try:
        with tempfile.TemporaryDirectory(prefix="actions-native-history-") as directory:
            root = Path(directory)
            project, data = root / "project", root / "data"
            project.mkdir()
            data.mkdir()
            env = {
                key: value
                for key, value in os.environ.items()
                if key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
            }
            env["ACTIONS_SKIP_UPDATE_CHECK"] = "1"
            key = secrets.token_urlsafe(32)
            server = NativeServer(binaries[0][1], project, data, env, key, 120)
            with server.running():
                pass
            result = json.dumps("x" * (payload_bytes - 2))
            with sqlite3.connect(data / "native-acceptance.db") as connection:
                for number in range(count):
                    connection.execute(
                        "INSERT INTO run (id,status,action_id,start_time,run_time,inputs,result,error_message,relative_artifacts_dir,numbered_id,request_id,run_type,robot_package_path,robot_task_name,robot_env_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            f"synthetic-{number}",
                            2,
                            "",
                            "2026-10-08T00:00:00+00:00",
                            1.0,
                            "{}",
                            result,
                            None,
                            f"synthetic-{number}",
                            number,
                            "",
                            "robot",
                            "synthetic-package",
                            f"synthetic-task-{number}",
                            None,
                        ),
                    )
                stored = connection.execute(
                    "SELECT SUM(length(result)) FROM run"
                ).fetchone()[0]
                require(stored == count * payload_bytes, "synthetic_fixture_size")
            for kind, binary in binaries:
                server = NativeServer(binary, project, data, env, key, 120)
                case: dict[str, Any] = {
                    "kind": kind,
                    "sha256": digest(binary),
                    "status": "IN_PROGRESS",
                }
                receipt["cases"].append(case)
                with server.running():
                    code, output = run_output(
                        [
                            args.node,
                            str(
                                PACKAGE
                                / "frontend/scripts/native-history-acceptance.mjs"
                            ),
                        ],
                        cwd=project,
                        env=env,
                        timeout=120,
                        input_text=json.dumps(
                            {
                                "origin": server.origin,
                                "api_key": key,
                                "run_count": count,
                                "browser_executable": args.browser_executable,
                            }
                        ),
                    )
                    browser = json.loads(output)
                    require(
                        code == 0 and browser.get("status") == "PASS",
                        "native_history_browser_" + browser.get("phase", "unknown"),
                    )
                    case["browser"] = browser

                    request = urllib.request.Request(
                        server.origin + "/api/runs/synthetic-0",
                        headers={"Authorization": "Bearer " + key},
                    )
                    with server.opener.open(request, timeout=10) as response:
                        content = response.read(payload_bytes + 65537)
                        require(
                            response.status == 200
                            and len(content) < payload_bytes + 65537,
                            "detail_response_limit",
                        )
                        require(
                            len(json.loads(content)["result"]) == payload_bytes,
                            "full_detail_preserved",
                        )
                    case["detail_bytes"] = len(content)
                require(
                    key.encode() not in (data / "process.log").read_bytes(),
                    "native_log_key",
                )
                case["status"] = "PASS"
                print(f"{kind}: large native history PASS", flush=True)
        receipt["status"] = "PASS"
        return 0
    finally:
        if receipt["status"] != "PASS":
            receipt["status"] = "FAIL"
            for case in receipt["cases"]:
                if case["status"] == "IN_PROGRESS":
                    case["status"] = "FAIL"
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
