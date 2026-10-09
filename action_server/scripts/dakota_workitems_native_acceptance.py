"""Run processor-state acceptance against both built native Runtime forms."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import tempfile
import uuid
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

TEST = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "action_server_tests"
    / "test_dakota_workitems_native_acceptance.py"
)
CASE_ENV = {
    "frozen": "DAKOTA_WORKITEMS_FROZEN_EXECUTABLE",
    "go-wrapper": "DAKOTA_WORKITEMS_GO_WRAPPER_EXECUTABLE",
}
CASE_SUFFIX = {kind: f"[{kind}-{variable}]" for kind, variable in CASE_ENV.items()}
CONSUMER_ACTIONS = [
    {"scenario": "success", "http_status": 200},
    {"scenario": "failure", "http_status": 500},
    {"scenario": "recovery", "http_status": 200},
]
API_STATE_READBACKS = {
    "after_success": {
        "input_state": "COMPLETED",
        "output_state": "PENDING",
        "output_queue": "default_output",
        "parent_link_verified": True,
    },
    "after_failure": {
        "input_state": "FAILED",
        "error_code": "SYNTHETIC_PROCESSOR_FAILURE",
        "error_message": "synthetic consumer failure",
    },
    "after_recovery": {
        "input_state": "COMPLETED",
        "output_state": "PENDING",
        "parent_link_verified": True,
    },
    "after_restart": {
        "success_state": "COMPLETED",
        "failure_state": "FAILED",
        "recovery_state": "COMPLETED",
        "stats": {
            "queue_name": "default",
            "pending": 0,
            "in_progress": 0,
            "done": 2,
            "failed": 1,
            "total": 3,
        },
        "output_parent_links_verified": True,
    },
}
CORE_INSTALLATION_FIELDS = {
    "actions_core_version",
    "actions_module_owned_by_distribution",
    "install_source_matches_candidate",
    "wheel_sha256",
    "pip_report_sha256",
}


class AcceptanceFailure(ValueError):
    """A bounded acceptance phase label without paths or subprocess output."""


class PytestCaseCollector:
    """Retain setup, call, and teardown outcomes for exact-case admission."""

    def __init__(self) -> None:
        self.reports: list[tuple[str, str, str]] = []

    def pytest_runtest_logreport(self, report) -> None:
        if report.when in {"setup", "call", "teardown"}:
            self.reports.append((report.nodeid, report.when, report.outcome))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_build_manifest(
    manifest_path: Path,
    package: Path,
    source_sha: str,
    executables: dict[str, Path],
    executable_hashes: dict[str, str],
) -> dict[str, str]:
    """Bind caller-selected native files to the measured workflow manifest."""
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceFailure("build_manifest_unreadable") from error
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise AcceptanceFailure("build_manifest_schema_invalid")
    if manifest.get("source_sha") != source_sha:
        raise AcceptanceFailure("build_manifest_source_sha_mismatch")
    if manifest.get("platform") != platform.system():
        raise AcceptanceFailure("build_manifest_platform_mismatch")
    if manifest.get("architecture") != platform.machine():
        raise AcceptanceFailure("build_manifest_architecture_mismatch")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise AcceptanceFailure("build_manifest_artifacts_invalid")

    package = package.resolve()
    suffix = ".exe" if platform.system() == "Windows" else ""
    expected_paths = {
        "frozen": Path("dist/action-server") / f"action-server{suffix}",
        "go-wrapper": Path("dist/final") / f"action-server{suffix}",
    }
    if set(executables) != set(CASE_ENV) or set(executable_hashes) != set(
        CASE_ENV
    ):
        raise AcceptanceFailure("build_manifest_executable_set_invalid")
    for kind in CASE_ENV:
        artifact = artifacts.get(kind)
        if not isinstance(artifact, dict):
            raise AcceptanceFailure(f"build_manifest_artifact_invalid_{kind}")
        expected = expected_paths[kind].as_posix()
        if artifact.get("path") != expected:
            raise AcceptanceFailure(f"build_manifest_artifact_path_mismatch_{kind}")
        if executables[kind].resolve() != (package / expected_paths[kind]).resolve():
            raise AcceptanceFailure(f"build_manifest_selected_path_mismatch_{kind}")
        if artifact.get("sha256") != executable_hashes[kind]:
            raise AcceptanceFailure(f"build_manifest_artifact_hash_mismatch_{kind}")
    return {
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_sha": source_sha,
    }


def validate_pytest_reports(
    result_code: int, reports: list[tuple[str, str, str]]
) -> dict[str, str]:
    """Require exactly one fully passed pytest case for each packaged binary."""
    if result_code != 0:
        raise AcceptanceFailure(f"pytest_exit_{result_code}")

    reports_by_kind: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for nodeid, phase, outcome in reports:
        matching_kinds = [
            kind for kind, suffix in CASE_SUFFIX.items() if nodeid.endswith(suffix)
        ]
        if len(matching_kinds) != 1:
            raise AcceptanceFailure("unexpected_pytest_case")
        reports_by_kind[matching_kinds[0]].append((phase, outcome))

    if set(reports_by_kind) != set(CASE_ENV):
        raise AcceptanceFailure("pytest_case_set_incomplete")

    expected_phases = {"setup", "call", "teardown"}
    for kind, case_reports in reports_by_kind.items():
        phases = [phase for phase, _ in case_reports]
        if len(phases) != len(set(phases)):
            raise AcceptanceFailure(f"duplicate_pytest_report_{kind}")
        if set(phases) != expected_phases:
            raise AcceptanceFailure(f"pytest_phases_incomplete_{kind}")
        if any(outcome != "passed" for _, outcome in case_reports):
            raise AcceptanceFailure(f"pytest_case_not_passed_{kind}")

    return {kind: "PASS" for kind in CASE_ENV}


@contextmanager
def fresh_proof_workspace(parent: Path) -> Iterator[Path]:
    """Create an empty, invocation-unique directory that cannot reuse stale proofs."""
    with tempfile.TemporaryDirectory(
        prefix="dakota-workitems-proof-", dir=parent
    ) as path:
        yield Path(path)


def _validate_proof_shape(proof: object, kind: str) -> dict:
    if not isinstance(proof, dict):
        raise AcceptanceFailure(f"proof_shape_{kind}")
    expected_keys = {
        "schema_version",
        "runtime_kind",
        "executable_sha256",
        "actions_core_wheel_sha256",
        "actions_core_installation",
        "consumer_actions",
        "api_state_readbacks",
    }
    if set(proof) != expected_keys:
        raise AcceptanceFailure(f"proof_fields_{kind}")
    if proof["schema_version"] != 2 or proof["runtime_kind"] != kind:
        raise AcceptanceFailure(f"proof_identity_{kind}")
    installation = proof["actions_core_installation"]
    if (
        not isinstance(installation, dict)
        or set(installation) != CORE_INSTALLATION_FIELDS
        or installation["actions_core_version"] != "1.0.2"
        or installation["actions_module_owned_by_distribution"] is not True
        or installation["install_source_matches_candidate"] is not True
        or installation["wheel_sha256"] != proof["actions_core_wheel_sha256"]
        or not re.fullmatch(r"[0-9a-f]{64}", installation["pip_report_sha256"])
    ):
        raise AcceptanceFailure(f"proof_core_installation_invalid_{kind}")
    if proof["consumer_actions"] != CONSUMER_ACTIONS:
        raise AcceptanceFailure(f"proof_actions_{kind}")
    if proof["api_state_readbacks"] != API_STATE_READBACKS:
        raise AcceptanceFailure(f"proof_readbacks_{kind}")
    return proof


def validate_case_proofs(
    proof_dir: Path,
    executable_hashes: dict[str, str],
    core_wheel_hash: str,
) -> dict[str, dict]:
    """Require one fresh proof per binary, bound to the measured executable and wheel."""
    expected_names = {f"{kind}.json" for kind in CASE_ENV}
    entries = list(proof_dir.iterdir())
    if any(not entry.is_file() for entry in entries):
        raise AcceptanceFailure("proof_directory_entry_invalid")
    if {entry.name for entry in entries} != expected_names or len(entries) != len(
        expected_names
    ):
        raise AcceptanceFailure("proof_file_set_incomplete_or_duplicate")
    if set(executable_hashes) != set(CASE_ENV):
        raise AcceptanceFailure("executable_hash_set_incomplete")

    proofs: dict[str, dict] = {}
    for kind in CASE_ENV:
        proof_path = proof_dir / f"{kind}.json"
        try:
            proof = _validate_proof_shape(
                json.loads(proof_path.read_text(encoding="utf-8")), kind
            )
        except (OSError, json.JSONDecodeError) as error:
            raise AcceptanceFailure(f"proof_unreadable_{kind}") from error
        if proof["executable_sha256"] != executable_hashes[kind]:
            raise AcceptanceFailure(f"proof_executable_hash_mismatch_{kind}")
        if proof["actions_core_wheel_sha256"] != core_wheel_hash:
            raise AcceptanceFailure(f"proof_core_wheel_hash_mismatch_{kind}")
        proofs[kind] = proof
    return proofs


def finalize_success(
    receipt: dict,
    result_code: int,
    reports: list[tuple[str, str, str]],
    proof_dir: Path,
    executable_hashes: dict[str, str],
    core_wheel_hash: str,
) -> None:
    """Mark PASS only after exact test cases and all bound proofs validate."""
    outcomes = validate_pytest_reports(result_code, reports)
    proofs = validate_case_proofs(proof_dir, executable_hashes, core_wheel_hash)
    for case in receipt["cases"]:
        kind = case["kind"]
        case["status"] = outcomes[kind]
        case["consumer_actions"] = proofs[kind]["consumer_actions"]
        case["actions_core_installation"] = proofs[kind]["actions_core_installation"]
        case["api_state_readbacks"] = proofs[kind]["api_state_readbacks"]
    receipt["pytest_output"] = f"{len(outcomes)} passed, 0 failed"
    receipt["status"] = "PASS"


def initial_receipt(source_sha_claim: str, build_version_claim: str) -> dict:
    return {
        "schema_version": 2,
        "attempt_id": str(uuid.uuid4()),
        "source_sha_claim": source_sha_claim,
        "build_version_claim": build_version_claim,
        "build_claim_verification": "caller supplied; not verified against a retained build manifest",
        "platform": platform.system(),
        "architecture": platform.machine(),
        "status": "IN_PROGRESS",
        "consumer_execution": "Runtime action executed by the packaged Runtime worker",
        "test_harness_sqlite_writes": ["seed stale reservation fixture only"],
        "recovery_fixture_limit": "stale persisted reservation seeded by harness; process crash not simulated",
        "worker_dependencies": {
            "actions-core": "1.0.2 candidate wheel installed by post-install",
            "actions-work-items": "0.4.4",
        },
        "checks": [
            "consumer_action_reserves_input_and_releases_completed_with_parent_linked_output",
            "consumer_action_releases_failed_with_error_details_then_fails_run",
            "consumer_action_recovers_seeded_stale_reservation_retries_and_completes",
            "runtime_restart_state_and_output_persistence",
            "consumer_action_verified_installed_actions_core_candidate_wheel",
        ],
        "cases": [],
    }


def _write_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


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
    parser.add_argument("--build-version", required=True)
    parser.add_argument(
        "--rcc-home",
        type=Path,
        required=True,
        help="Task-owned RCC home/cache directory.",
    )
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--build-manifest",
        type=Path,
        help="Optional measured native build manifest to bind source and executable bytes.",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("source SHA must be a full lowercase commit SHA")

    core_wheel = args.rcc_home / "wheels" / "actions_core-1.0.2-py3-none-any.whl"
    receipt = initial_receipt(args.source_sha, args.build_version)

    return_code = 1
    try:
        # Remove earlier success before publishing this attempt. If this process
        # is terminated during the atomic write or later work, it cannot leave a
        # stale PASS at the receipt path.
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.unlink(missing_ok=True)
        _write_receipt(args.receipt, receipt)

        if not core_wheel.is_file():
            raise AcceptanceFailure("actions_core_1_0_2_task_local_wheel_missing")
        wheel_hash = sha256(core_wheel)
        receipt["actions_core_wheel_sha256"] = wheel_hash

        executables = {
            kind: Path(getattr(args, kind.replace("-", "_"))) for kind in CASE_ENV
        }
        executable_hashes: dict[str, str] = {}
        for kind, executable in executables.items():
            if not executable.is_file():
                raise AcceptanceFailure(f"{kind}_executable_missing")
            executable_hashes[kind] = sha256(executable)
            receipt["cases"].append(
                {
                    "kind": kind,
                    "executable_sha256": executable_hashes[kind],
                    "status": "READY",
                }
            )

        if args.build_manifest is not None:
            receipt["build_claim_verification"] = (
                "verified against supplied measured native artifact manifest; "
                "manifest checks Git HEAD, not a clean-source attestation"
            )
            manifest_binding = validate_build_manifest(
                args.build_manifest,
                TEST.parents[2],
                args.source_sha,
                executables,
                executable_hashes,
            )
            receipt["build_manifest"] = manifest_binding

        args.rcc_home.mkdir(parents=True, exist_ok=True)
        os.environ["PYTEST_ADDOPTS"] = ""
        os.environ["DAKOTA_WORKITEMS_RCC_HOME"] = str(args.rcc_home.resolve())
        os.environ["DAKOTA_WORKITEMS_CORE_WHEEL"] = str(core_wheel.resolve())
        os.environ["DAKOTA_WORKITEMS_CORE_WHEEL_SHA256"] = wheel_hash
        os.environ["ACTIONS_HOME"] = str(args.rcc_home.resolve())
        os.environ["ROBOCORP_HOME"] = str(args.rcc_home.resolve())
        for kind, executable in executables.items():
            env_suffix = kind.upper().replace("-", "_")
            os.environ[CASE_ENV[kind]] = str(executable.resolve())
            os.environ[f"DAKOTA_WORKITEMS_{env_suffix}_SHA256"] = executable_hashes[
                kind
            ]

        import pytest

        collector = PytestCaseCollector()
        with fresh_proof_workspace(args.receipt.parent) as proof_dir:
            os.environ["DAKOTA_WORKITEMS_PROOF_DIR"] = str(proof_dir)
            result = pytest.main(
                ["-q", "-m", "integration_test", str(TEST)],
                plugins=[collector],
            )
            for kind, executable in executables.items():
                if sha256(executable) != executable_hashes[kind]:
                    raise AcceptanceFailure(
                        f"executable_changed_during_acceptance_{kind}"
                    )
            if sha256(core_wheel) != wheel_hash:
                raise AcceptanceFailure("core_wheel_changed_during_acceptance")
            finalize_success(
                receipt,
                int(result),
                collector.reports,
                proof_dir,
                executable_hashes,
                wheel_hash,
            )

        return_code = 0
    except AcceptanceFailure as error:
        receipt["status"] = "FAIL"
        receipt["failed_phase"] = str(error)[:120]
    except Exception as error:
        receipt["status"] = "FAIL"
        receipt["failed_phase"] = f"runner_exception_{type(error).__name__}"
    finally:
        if return_code != 0:
            receipt["status"] = "FAIL"
            receipt.pop("pytest_output", None)
            for case in receipt["cases"]:
                case.pop("consumer_actions", None)
                case.pop("api_state_readbacks", None)
                case.pop("actions_core_installation", None)
                case["status"] = "NOT_VERIFIED"
        _write_receipt(args.receipt, receipt)

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
