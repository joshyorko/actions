"""Deterministic admission tests for the Dakota native acceptance receipt."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

RUNNER_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "dakota_workitems_native_acceptance.py"
)
SPEC = importlib.util.spec_from_file_location(
    "dakota_workitems_native_acceptance", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
NATIVE_TEST_PATH = Path(__file__).with_name(
    "test_dakota_workitems_native_acceptance.py"
)
NATIVE_TEST_SPEC = importlib.util.spec_from_file_location(
    "dakota_workitems_native_case", NATIVE_TEST_PATH
)
assert NATIVE_TEST_SPEC is not None and NATIVE_TEST_SPEC.loader is not None
NATIVE_TEST = importlib.util.module_from_spec(NATIVE_TEST_SPEC)
NATIVE_TEST_SPEC.loader.exec_module(NATIVE_TEST)


def reports_for(
    *kinds: str, call_outcome: str = "passed"
) -> list[tuple[str, str, str]]:
    reports = []
    for kind in kinds:
        suffix = RUNNER.CASE_SUFFIX[kind]
        nodeid = (
            "tests/action_server_tests/"
            "test_dakota_workitems_native_acceptance.py::"
            "test_packaged_runtime_executes_work_item_consumer_lifecycle"
            f"{suffix}"
        )
        for phase in ("setup", "call", "teardown"):
            outcome = call_outcome if phase == "call" else "passed"
            reports.append((nodeid, phase, outcome))
    return reports


def proof_record(kind: str, executable_hash: str, wheel_hash: str) -> dict:
    return {
        "schema_version": 1,
        "runtime_kind": kind,
        "executable_sha256": executable_hash,
        "actions_core_wheel_sha256": wheel_hash,
        "consumer_actions": copy.deepcopy(RUNNER.CONSUMER_ACTIONS),
        "api_state_readbacks": copy.deepcopy(RUNNER.API_STATE_READBACKS),
    }


def write_proofs(
    directory: Path, executable_hashes: dict[str, str], wheel_hash: str
) -> None:
    for kind in RUNNER.CASE_ENV:
        (directory / f"{kind}.json").write_text(
            json.dumps(proof_record(kind, executable_hashes[kind], wheel_hash)),
            encoding="utf-8",
        )


def test_rejects_a_single_selected_native_case():
    with pytest.raises(RUNNER.AcceptanceFailure, match="pytest_case_set_incomplete"):
        RUNNER.validate_pytest_reports(0, reports_for("frozen"))


def test_rejects_duplicate_pytest_case_reports():
    reports = reports_for("frozen", "go-wrapper")
    reports.append(reports[1])
    with pytest.raises(
        RUNNER.AcceptanceFailure, match="duplicate_pytest_report_frozen"
    ):
        RUNNER.validate_pytest_reports(0, reports)


def test_rejects_skipped_case_even_when_pytest_exits_successfully():
    reports = reports_for("frozen", "go-wrapper", call_outcome="passed")
    reports[4] = (reports[4][0], "call", "skipped")
    with pytest.raises(
        RUNNER.AcceptanceFailure, match="pytest_case_not_passed_go-wrapper"
    ):
        RUNNER.validate_pytest_reports(0, reports)


def test_fresh_proof_workspace_does_not_reuse_stale_files(tmp_path: Path):
    stale_workspace = tmp_path / "stale"
    stale_workspace.mkdir()
    (stale_workspace / "frozen.json").write_text("stale", encoding="utf-8")

    with RUNNER.fresh_proof_workspace(tmp_path) as fresh_workspace:
        assert fresh_workspace != stale_workspace
        assert list(fresh_workspace.iterdir()) == []


def test_case_proof_is_atomically_replaced_without_temp_file_residue(tmp_path: Path):
    proof_path = NATIVE_TEST._write_atomic_proof(tmp_path, "frozen", {"sequence": 1})
    assert json.loads(proof_path.read_text(encoding="utf-8")) == {"sequence": 1}

    NATIVE_TEST._write_atomic_proof(tmp_path, "frozen", {"sequence": 2})
    assert json.loads(proof_path.read_text(encoding="utf-8")) == {"sequence": 2}
    assert {path.name for path in tmp_path.iterdir()} == {"frozen.json"}


def test_rejects_missing_or_duplicate_proof_files(tmp_path: Path):
    hashes = {"frozen": "a" * 64, "go-wrapper": "b" * 64}
    wheel_hash = "c" * 64
    write_proofs(tmp_path, hashes, wheel_hash)
    (tmp_path / "go-wrapper.json").unlink()
    with pytest.raises(
        RUNNER.AcceptanceFailure, match="proof_file_set_incomplete_or_duplicate"
    ):
        RUNNER.validate_case_proofs(tmp_path, hashes, wheel_hash)

    write_proofs(tmp_path, hashes, wheel_hash)
    (tmp_path / "frozen-copy.json").write_text("{}", encoding="utf-8")
    with pytest.raises(
        RUNNER.AcceptanceFailure, match="proof_file_set_incomplete_or_duplicate"
    ):
        RUNNER.validate_case_proofs(tmp_path, hashes, wheel_hash)


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("runtime_kind", "go-wrapper", "proof_identity_frozen"),
        ("executable_sha256", "f" * 64, "proof_executable_hash_mismatch_frozen"),
        (
            "actions_core_wheel_sha256",
            "f" * 64,
            "proof_core_wheel_hash_mismatch_frozen",
        ),
    ],
)
def test_rejects_mismatched_proof_binding(
    tmp_path: Path, field: str, value: str, failure: str
):
    hashes = {"frozen": "a" * 64, "go-wrapper": "b" * 64}
    wheel_hash = "c" * 64
    write_proofs(tmp_path, hashes, wheel_hash)
    proof_path = tmp_path / "frozen.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof[field] = value
    proof_path.write_text(json.dumps(proof), encoding="utf-8")

    with pytest.raises(RUNNER.AcceptanceFailure, match=failure):
        RUNNER.validate_case_proofs(tmp_path, hashes, wheel_hash)


def test_incomplete_pytest_run_cannot_finalize_pass(tmp_path: Path):
    hashes = {"frozen": "a" * 64, "go-wrapper": "b" * 64}
    wheel_hash = "c" * 64
    write_proofs(tmp_path, hashes, wheel_hash)
    receipt = {
        "status": "IN_PROGRESS",
        "cases": [{"kind": kind, "status": "READY"} for kind in hashes],
    }

    with pytest.raises(RUNNER.AcceptanceFailure):
        RUNNER.finalize_success(
            receipt,
            0,
            reports_for("frozen"),
            tmp_path,
            hashes,
            wheel_hash,
        )

    assert receipt["status"] != "PASS"
    assert "pytest_output" not in receipt


def test_acceptance_claims_are_not_presented_as_build_provenance():
    receipt = RUNNER.initial_receipt("a" * 40, "dakota-local")

    assert receipt["source_sha_claim"] == "a" * 40
    assert receipt["build_version_claim"] == "dakota-local"
    assert receipt["build_claim_verification"] == (
        "caller supplied; not verified against a retained build manifest"
    )
    assert "source_sha" not in receipt
    assert "build_output" not in receipt


@pytest.mark.parametrize("final_check", ["unchanged", "changed", "interrupted"])
def test_receipt_requires_completed_final_artifact_checks(
    tmp_path, monkeypatch, final_check
):
    """Even passed native cases cannot admit changed or unverified final artifacts."""
    monkeypatch.setattr(os, "environ", os.environ.copy())
    frozen = tmp_path / "frozen"
    wrapper = tmp_path / "wrapper"
    frozen.write_bytes(b"frozen artifact")
    wrapper.write_bytes(b"wrapper artifact")
    wheel = tmp_path / "rcc" / "wheels" / "actions_core-1.0.2-py3-none-any.whl"
    wheel.parent.mkdir(parents=True)
    wheel.write_bytes(b"wheel artifact")
    receipt_path = tmp_path / "receipt.json"
    hashes = {"frozen": RUNNER.sha256(frozen), "go-wrapper": RUNNER.sha256(wrapper)}
    wheel_hash = RUNNER.sha256(wheel)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "acceptance",
            "--frozen",
            str(frozen),
            "--go-wrapper",
            str(wrapper),
            "--rcc-home",
            str(wheel.parent.parent),
            "--receipt",
            str(receipt_path),
            "--source-sha",
            "a" * 40,
            "--build-version",
            "test",
        ],
    )

    def completed_native_cases(args, plugins):
        plugins[0].reports = reports_for("frozen", "go-wrapper")
        write_proofs(Path(os.environ["DAKOTA_WORKITEMS_PROOF_DIR"]), hashes, wheel_hash)
        if final_check == "changed":
            frozen.write_bytes(b"different artifact")
        elif final_check == "interrupted":

            def interrupted_hash(path):
                raise KeyboardInterrupt

            monkeypatch.setattr(RUNNER, "sha256", interrupted_hash)
        return 0

    monkeypatch.setattr(pytest, "main", completed_native_cases)
    if final_check == "interrupted":
        with pytest.raises(KeyboardInterrupt):
            RUNNER.main()
    else:
        assert RUNNER.main() == (0 if final_check == "unchanged" else 1)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if final_check == "unchanged":
        assert receipt["status"] == "PASS"
        assert all(case["status"] == "PASS" for case in receipt["cases"])
    else:
        assert receipt["status"] == "FAIL"
        assert all(case["status"] == "NOT_VERIFIED" for case in receipt["cases"])
        assert "pytest_output" not in receipt
        assert all("api_state_readbacks" not in case for case in receipt["cases"])
