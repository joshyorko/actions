"""Run processor-state acceptance against both built native Runtime forms."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import tempfile
from pathlib import Path

TEST = Path(__file__).resolve().parents[1] / "tests" / "action_server_tests" / "test_dakota_workitems_native_acceptance.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    suffix = ".exe" if os.name == "nt" else ""
    parser.add_argument(
        "--frozen",
        type=Path,
        default=TEST.parents[2] / "dist" / "action-server" / f"action-server{suffix}",
    )
    parser.add_argument(
        "--go-wrapper",
        type=Path,
        default=TEST.parents[2] / "dist" / "final" / f"action-server{suffix}",
    )
    parser.add_argument("--source-sha", required=True)
    parser.add_argument(
        "--rcc-home", type=Path, required=True, help="Task-owned RCC home/cache directory."
    )
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("source SHA must be a full lowercase commit SHA")

    cases = []
    core_wheel = args.rcc_home / "wheels" / "actions_core-1.0.2-py3-none-any.whl"
    receipt = {
        "schema_version": 1,
        "source_sha": args.source_sha,
        "platform": platform.system(),
        "architecture": platform.machine(),
        "status": "IN_PROGRESS",
        "consumer_execution": "Runtime action executed by the packaged Runtime worker",
        "test_harness_sqlite_writes": ["seed stale reservation fixture only"],
        "worker_dependencies": {
            "actions-core": "1.0.2 (task-local wheel)",
            "actions-work-items": "0.4.4",
        },
        "checks": [
            "consumer_action_reserves_input_and_releases_completed_with_parent_linked_output",
            "consumer_action_releases_failed_with_error_details_then_fails_run",
            "consumer_action_recovers_orphaned_reservation_retries_and_completes",
            "runtime_restart_state_and_output_persistence",
        ],
        "cases": cases,
    }
    try:
        if not core_wheel.is_file():
            raise FileNotFoundError("actions_core_1_0_2_task_local_wheel_missing")
        receipt["actions_core_wheel_sha256"] = sha256(core_wheel)
        for kind, path in (("frozen", args.frozen), ("go-wrapper", args.go_wrapper)):
            if not path.is_file():
                raise FileNotFoundError(f"{kind}_executable_missing")
            cases.append({"kind": kind, "sha256": sha256(path), "status": "READY"})

        args.rcc_home.mkdir(parents=True, exist_ok=True)
        os.environ["DAKOTA_WORKITEMS_RCC_HOME"] = str(args.rcc_home.resolve())
        os.environ["ACTIONS_HOME"] = str(args.rcc_home.resolve())
        os.environ["ROBOCORP_HOME"] = str(args.rcc_home.resolve())
        os.environ["DAKOTA_WORKITEMS_FROZEN_EXECUTABLE"] = str(args.frozen.resolve())
        os.environ["DAKOTA_WORKITEMS_GO_WRAPPER_EXECUTABLE"] = str(args.go_wrapper.resolve())
        import pytest

        result = pytest.main(
            ["-q", "-m", "integration_test", str(TEST)],
        )
        if result != pytest.ExitCode.OK:
            receipt["status"] = "FAIL"
            receipt["failed_phase"] = "packaged_processor_lifecycle"
            return_code = int(result)
        else:
            for case in cases:
                case["status"] = "PASS"
            receipt["status"] = "PASS"
            return_code = 0
        return return_code
    except (OSError, ValueError) as error:
        receipt["status"] = "FAIL"
        receipt["failed_phase"] = str(error)[:120]
        return 1
    finally:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=args.receipt.parent, delete=False
        ) as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
            temporary = Path(stream.name)
        temporary.replace(args.receipt)


if __name__ == "__main__":
    raise SystemExit(main())
