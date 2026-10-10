"""Exercise the exact always-run hosted admission script with synthetic evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = ROOT / ".github/workflows/_gen_workflows.py"


def _summary_script() -> str:
    spec = importlib.util.spec_from_file_location("workflow_generator", GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    return generator.RCC_ROLLBACK_SUMMARY_SCRIPT


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _make_repository(root: Path, files: dict[str, bytes]) -> tuple[str, str]:
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Rollback Workflow Test")
    _git(root, "config", "user.email", "rollback-test@example.invalid")
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return _git(root, "rev-parse", "HEAD"), _git(root, "rev-parse", "HEAD^{tree}")


def _fixture(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    control_sha, control_tree = _make_repository(
        workspace / "control", {"control.txt": b"control"}
    )
    source_files = {
        "action_server/src/actions/server/_action_package_handler.py": b"package handler\n",
        "action_server/src/actions/server/_actions_import.py": b"actions import\n",
        "action_server/src/actions/server/_rcc_runtime_adapter.py": b"runtime adapter\n",
        "action_server/tests/action_server_tests/test_current_candidate_import_rollback.py": b"test\n",
        "action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py": b"staged test\n",
        "action_server/src/actions/server/deployments/source_staging.py": b"staging module\n",
        "action_server/src/actions/server/deployments/source_read.py": b"source reader\n",
        "action_server/src/actions/server/deployments/source_manifest.py": b"manifest policy\n",
        "action_server/scripts/verify_dakota_rcc_acceptance.py": b"helper\n",
    }
    candidate_sha, candidate_tree = _make_repository(
        workspace / "candidate", source_files
    )
    candidate = workspace / "candidate"
    module_files = {
        "action_package_handler": source_files[
            "action_server/src/actions/server/_action_package_handler.py"
        ],
        "actions_import": source_files[
            "action_server/src/actions/server/_actions_import.py"
        ],
        "runtime_adapter": source_files[
            "action_server/src/actions/server/_rcc_runtime_adapter.py"
        ],
    }
    module_paths = {
        "action_package_handler": candidate
        / "action_server/src/actions/server/_action_package_handler.py",
        "actions_import": candidate
        / "action_server/src/actions/server/_actions_import.py",
        "runtime_adapter": candidate
        / "action_server/src/actions/server/_rcc_runtime_adapter.py",
    }
    if os.name == "nt":
        # subprocess.run([path, "--version"]) dispatches batch files through
        # cmd.exe on Windows; a POSIX shebang fixture is not executable there.
        rcc_binary = tmp_path / "rcc.cmd"
        rcc_binary.write_text(
            "@echo off\r\n"
            'if "%~1"=="--version" (\r\n'
            "  echo v18.19.3\r\n"
            "  exit /b 0\r\n"
            ")\r\n"
            "exit /b 2\r\n",
            encoding="utf-8",
            newline="",
        )
    else:
        rcc_binary = tmp_path / "rcc"
        rcc_binary.write_text("#!/bin/sh\nprintf '%s\\n' v18.19.3\n", encoding="utf-8")
        rcc_binary.chmod(0o700)
    rcc_sha = hashlib.sha256(rcc_binary.read_bytes()).hexdigest()
    default_name = (
        "action-server-default-rcc.cmd"
        if os.name == "nt"
        else "action-server-default-rcc"
    )
    default_rcc = tmp_path / default_name
    default_rcc.write_bytes(rcc_binary.read_bytes())
    default_rcc.chmod(0o700)
    receipt = {
        "status": "PASS",
        "source": {
            "commit": candidate_sha,
            "tree": candidate_tree,
            "module_origins": {name: str(path) for name, path in module_paths.items()},
            "runtime_module_sha256": {
                name: hashlib.sha256(content).hexdigest()
                for name, content in module_files.items()
            },
        },
        "rcc_version": "v18.19.3",
        "rcc_sha256": rcc_sha,
        "provider": "http://user:secret@127.0.0.1/private?token=do-not-export",
        "provider_ops_before_failure": [
            {"phase": "publish", "secret": "do-not-export"}
        ],
        "provider_ops_after_failure": [{"phase": "publish", "secret": "do-not-export"}],
        "provider_ops_after_recovery": [
            {"phase": "publish", "secret": "do-not-export"}
        ],
        "first_run": {"status": 2, "result": "last-good"},
        "second_run": {"status": 2, "result": "last-good"},
        "recovered_run": {"status": 2, "result": "recovered"},
        "action_server_process_exit": {
            "pid": 2401,
            "natural_exit_status": "PASS",
            "returncode_before_forced_cleanup": 0,
            "shutdown_request_succeeded": True,
            "forced_stop_used": False,
            "forced_cleanup_returncode_observed": True,
            "same_owned_descendants_remaining_after_stop": [],
            "owned_descendants_before_stop": [
                {"pid": 2402, "create_time": 1234.5, "argv": ["do-not-export"]}
            ],
            "argv": ["do-not-export"],
        },
    }
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "lifecycle-receipt.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuite tests="3" failures="0" errors="0" skipped="0">'
        '<testcase classname="tests.action_server_tests.test_current_candidate_import_rollback" '
        'name="test_current_candidate_failed_reload_keeps_last_good_action_usable"/>'
        '<testcase classname="tests.action_server_tests.test_source_staging_rcc_consumer" '
        'name="test_staged_package_executes_in_managed_rcc_runtime"/>'
        '<testcase classname="tests.action_server_tests.test_source_staging_rcc_consumer" '
        'name="test_published_artifact_details_preserves_one_rcc_identity_pair"/>'
        "</testsuite>",
        encoding="utf-8",
    )
    staged_receipt = {
        "status": "PASS",
        "source_commit": candidate_sha,
        "source_tree": candidate_tree,
        "source_inventory": json.dumps(
            {
                "sourcePolicyVersion": 1,
                "entries": [
                    {"path": "action.py", "sha256": "a" * 64},
                    {"path": "package.yaml", "sha256": "b" * 64},
                ],
            }
        ),
        "staged_inventory": json.dumps(
            {
                "sourcePolicyVersion": 1,
                "entries": [
                    {"path": "action.py", "sha256": "a" * 64},
                    {"path": "package.yaml", "sha256": "b" * 64},
                ],
            }
        ),
        "source_sha256": {"action.py": "a" * 64, "package.yaml": "b" * 64},
        "staged_sha256": {"action.py": "a" * 64, "package.yaml": "b" * 64},
        "managed_root": "/tmp/actions-home/holotree",
        "typed_action_result": {
            "action_source_sha256": "a" * 64,
            "action_source_path": "/tmp/runtime-data/.rcc-runtime-sources/staged/action.py",
            "core_version": "1.0.2",
            "core_origin": "/tmp/actions-home/holotree/env/site-packages/actions/__init__.py",
            "python_executable": "/tmp/actions-home/holotree/env/bin/python",
        },
    }
    (evidence / "staged-consumer-receipt.json").write_text(
        json.dumps(staged_receipt), encoding="utf-8"
    )
    specification_digest = "sha256:" + "c" * 64
    artifact_digest = "sha256:" + "d" * 64
    raw_json = json.dumps(
        {
            "specificationDigest": specification_digest,
            "artifactDigest": artifact_digest,
            "legacyBlueprintKey": "fixture-blueprint",
            "objectCount": 1,
            "uploadedBytes": 12,
            "reusedBytes": 34,
        },
        separators=(",", ":"),
    )
    minimal_environment = tmp_path / "minimal-package" / "package.yaml"
    details_receipt = {
        "schema_version": 1,
        "status": "PASS",
        "source": {"commit": candidate_sha, "tree": candidate_tree},
        "control": {"commit": control_sha, "tree": control_tree},
        "rcc": {"version": "v18.19.3", "sha256": rcc_sha},
        "publication": {
            "invocation_count": 1,
            "provider": "http://127.0.0.1:43210",
            "args": [
                str(rcc_binary),
                "env",
                "publish",
                "--environment",
                str(minimal_environment),
                "--json",
                "--provider",
                "http://127.0.0.1:43210",
            ],
            "specification_digest": specification_digest,
            "artifact_digest": artifact_digest,
            "raw_json": raw_json,
            "raw_json_sha256": hashlib.sha256(raw_json.encode("utf-8")).hexdigest(),
        },
    }
    (evidence / "published-details-receipt.json").write_text(
        json.dumps(details_receipt), encoding="utf-8"
    )
    env = {
        **os.environ,
        "GITHUB_WORKSPACE": str(workspace),
        "EVIDENCE_DIR": str(evidence),
        "JUNIT_PATH": str(junit),
        "EXPECTED_CANDIDATE_SHA": candidate_sha,
        "EXPECTED_CANDIDATE_TREE": candidate_tree,
        "EXPECTED_CONTROL_SHA": control_sha,
        "EXPECTED_RCC_SHA256": rcc_sha,
        "RCC_PROVIDER_ROLLBACK_TEST_EXIT_CODE": "0",
        "RCC_WORKER_LIBC_NAME": "glibc",
        "RCC_WORKER_LIBC_VERSION": "2.39",
        "ACTIONS_RUNTIME_RCC_BINARY": str(rcc_binary),
        "ACTION_SERVER_RCC_DEFAULT": str(default_rcc),
    }
    return evidence, junit, receipt, env


def _run_summary(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _summary_script()],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_exact_summary_script_admits_complete_passing_receipt(tmp_path: Path) -> None:
    evidence, _, _, env = _fixture(tmp_path)
    result = _run_summary(env)

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((evidence / "acceptance-summary.json").read_text())
    assert summary["admission"] == {"passed": True, "issues": []}
    assert summary["source"]["receipt_source_matches_candidate"] is True
    assert len(summary["source"]["candidate_tree"]) == 40
    assert summary["source"]["runtime_module_hashes_match_candidate"] is True
    assert summary["source"]["runtime_module_origins_match_candidate"] is True
    assert summary["test"]["provider_operations_unchanged"] is True
    assert summary["test"]["natural_exit_status"] == "PASS"
    assert summary["test"]["natural_return_code_before_cleanup"] == 0
    assert summary["test"]["forced_cleanup_returncode_observed"] is True
    assert summary["test"]["expected_test_identity_matches"] is True
    assert summary["test"]["staged_consumer_receipt_status"] == "PASS"
    assert summary["test"]["staged_consumer_receipt_valid"] is True
    assert summary["test"]["staged_action_sha256_matches"] is True
    assert summary["test"]["published_details_receipt_valid"] is True
    assert summary["published_details"]["specification_digest"] == "sha256:" + "c" * 64
    assert summary["published_details"]["artifact_digest"] == "sha256:" + "d" * 64
    assert summary["published_details"]["single_invocation"] is True
    assert summary["published_details"]["provider_is_loopback"] is True
    lifecycle = json.loads((evidence / "lifecycle-summary.json").read_text())
    assert lifecycle["action_server_process_exit"]["natural_exit_status"] == "PASS"
    assert "argv" not in lifecycle["action_server_process_exit"]
    assert lifecycle["action_server_process_exit"]["pid"] == 2401
    assert lifecycle["owned_descendants_before_stop"] == [
        {"pid": 2402, "create_time": 1234.5}
    ]
    assert summary["runner"] == {
        "libc_name": "glibc",
        "libc_version": "2.39",
        "meets_artifact_minimum": True,
    }
    text = (evidence / "acceptance-summary.json").read_text()
    assert "do-not-export" not in text
    assert "user:secret" not in text
    lifecycle_text = (evidence / "lifecycle-summary.json").read_text()
    assert "do-not-export" not in lifecycle_text
    assert "user:secret" not in lifecycle_text


def test_exact_summary_script_ignores_unexpected_nested_source_fields(
    tmp_path: Path,
) -> None:
    evidence, _, receipt, env = _fixture(tmp_path)
    receipt["source"]["runtime_module_sha256"]["unexpected_observer"] = {
        "argv": "PRIVATE_OBSERVER_SENTINEL"
    }
    receipt["action_server_process_exit"]["owned_descendants_before_stop"][0][
        "create_time"
    ] = 10**1000
    (evidence / "lifecycle-receipt.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )

    result = _run_summary(env)

    assert result.returncode == 0, result.stderr + result.stdout
    lifecycle = json.loads((evidence / "lifecycle-summary.json").read_text())
    assert "unexpected_observer" not in lifecycle["source"]["runtime_module_sha256"]
    assert "PRIVATE_OBSERVER_SENTINEL" not in json.dumps(lifecycle)
    assert "create_time" not in lifecycle["owned_descendants_before_stop"][0]


def test_exact_summary_script_sanitizes_malformed_failure_fields(
    tmp_path: Path,
) -> None:
    evidence, _, receipt, env = _fixture(tmp_path)
    sentinel = "PRIVATE_OBSERVER_SENTINEL"
    receipt["status"] = sentinel
    receipt["failure_type"] = sentinel
    receipt["provider_ops_before_failure"] = [{"phase": [sentinel]}]
    receipt["provider_ops_after_recovery"] = [{"phase": [sentinel]}]
    receipt["action_server_process_exit"]["pid"] = [sentinel]
    receipt["action_server_process_exit"]["natural_exit_status"] = sentinel
    receipt["first_run"]["status"] = sentinel
    (evidence / "lifecycle-receipt.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )

    result = _run_summary(env)

    assert result.returncode != 0
    lifecycle_text = (evidence / "lifecycle-summary.json").read_text()
    assert sentinel not in lifecycle_text
    lifecycle = json.loads(lifecycle_text)
    assert lifecycle["status"] == "NOT_RECORDED"
    assert lifecycle["provider_operation_phases_before_failure"] == ["INVALID"]
    assert "pid" not in lifecycle["action_server_process_exit"]
    assert lifecycle["action_server_process_exit"]["natural_exit_status"] == "UNKNOWN"
    assert lifecycle["run_statuses"]["first_run"] == "INVALID"


@pytest.mark.parametrize(
    ("mutation", "expected_issue"),
    [
        ("skip", "test_result_not_exactly_three_passes"),
        ("glibc_too_old", "runner_glibc_below_artifact_minimum_or_unknown"),
        ("missing_glibc", "runner_glibc_below_artifact_minimum_or_unknown"),
        ("missing_junit", "junit_missing_or_invalid"),
        ("malformed_junit", "junit_missing_or_invalid"),
        ("missing_testcase", "junit_suite_counts_do_not_match_testcases"),
        ("undeclared_skip", "junit_suite_counts_do_not_match_testcases"),
        ("undeclared_failure", "junit_suite_counts_do_not_match_testcases"),
        ("undeclared_error", "junit_suite_counts_do_not_match_testcases"),
        ("wrong_test_identity", "unexpected_test_identity"),
        ("missing_receipt", "receipt_status_not_pass"),
        ("stale_source", "receipt_source_commit_mismatch"),
        ("candidate_tree_mismatch", "candidate_checkout_tree_mismatch"),
        ("stale_staged_source", "staged_consumer_receipt_missing_or_invalid"),
        ("cleanup_failure", "forced_stop_was_used_or_unknown"),
        ("unobserved_cleanup", "forced_cleanup_return_code_unobserved"),
        ("invalid_natural_exit", "natural_return_code_missing_or_abnormal"),
        ("provider_changed", "provider_operations_changed_or_missing"),
        ("rcc_mismatch", "receipt_rcc_hash_mismatch"),
        ("staged_receipt_missing", "staged_consumer_receipt_missing_or_invalid"),
        ("staged_digest_mismatch", "staged_consumer_receipt_missing_or_invalid"),
        ("staged_result_digest_mismatch", "staged_consumer_receipt_missing_or_invalid"),
        (
            "duplicate_source_inventory_path",
            "staged_consumer_receipt_missing_or_invalid",
        ),
        ("missing_source_inventory_path", "staged_consumer_receipt_missing_or_invalid"),
        (
            "unexpected_source_inventory_path",
            "staged_consumer_receipt_missing_or_invalid",
        ),
        (
            "duplicate_staged_inventory_path",
            "staged_consumer_receipt_missing_or_invalid",
        ),
        ("missing_staged_inventory_path", "staged_consumer_receipt_missing_or_invalid"),
        (
            "unexpected_staged_inventory_path",
            "staged_consumer_receipt_missing_or_invalid",
        ),
    ],
)
def test_exact_summary_script_rejects_incomplete_receipt(
    tmp_path: Path, mutation: str, expected_issue: str
) -> None:
    evidence, junit, receipt, env = _fixture(tmp_path)
    staged_receipt_path = evidence / "staged-consumer-receipt.json"
    if mutation == "skip":
        junit.write_text(
            '<testsuite tests="1" failures="0" errors="0" skipped="1">'
            '<testcase classname="rollback" name="accepted"><skipped/></testcase>'
            "</testsuite>",
            encoding="utf-8",
        )
    elif mutation == "glibc_too_old":
        env["RCC_WORKER_LIBC_VERSION"] = "2.35"
    elif mutation == "missing_glibc":
        env.pop("RCC_WORKER_LIBC_VERSION")
    elif mutation == "missing_junit":
        junit.unlink()
    elif mutation == "malformed_junit":
        junit.write_text("<testsuite>", encoding="utf-8")
    elif mutation == "missing_testcase":
        junit.write_text(
            '<testsuite tests="1" failures="0" errors="0" skipped="0"/>',
            encoding="utf-8",
        )
    elif mutation == "undeclared_skip":
        junit.write_text(
            '<testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase classname="rollback" name="accepted"><skipped/></testcase>'
            "</testsuite>",
            encoding="utf-8",
        )
    elif mutation == "undeclared_failure":
        junit.write_text(
            '<testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase classname="rollback" name="accepted"><failure/></testcase>'
            "</testsuite>",
            encoding="utf-8",
        )
    elif mutation == "undeclared_error":
        junit.write_text(
            '<testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase classname="rollback" name="accepted"><error/></testcase>'
            "</testsuite>",
            encoding="utf-8",
        )
    elif mutation == "wrong_test_identity":
        junit.write_text(
            '<testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase classname="tests.action_server_tests.unrelated_test" '
            'name="test_unrelated_pass"/></testsuite>',
            encoding="utf-8",
        )
    elif mutation == "missing_receipt":
        (evidence / "lifecycle-receipt.json").unlink()
    elif mutation == "stale_source":
        receipt["source"]["commit"] = "0" * 40
    elif mutation == "candidate_tree_mismatch":
        env["EXPECTED_CANDIDATE_TREE"] = "0" * 40
    elif mutation == "stale_staged_source":
        staged_receipt = json.loads(staged_receipt_path.read_text(encoding="utf-8"))
        staged_receipt["source_tree"] = "0" * 40
        staged_receipt_path.write_text(json.dumps(staged_receipt), encoding="utf-8")
    elif mutation == "cleanup_failure":
        receipt["action_server_process_exit"]["forced_stop_used"] = True
    elif mutation == "unobserved_cleanup":
        receipt["action_server_process_exit"][
            "forced_cleanup_returncode_observed"
        ] = False
    elif mutation == "invalid_natural_exit":
        receipt["action_server_process_exit"]["returncode_before_forced_cleanup"] = True
    elif mutation == "provider_changed":
        receipt["provider_ops_after_recovery"].append({"phase": "acquire"})
    elif mutation == "rcc_mismatch":
        receipt["rcc_sha256"] = "0" * 64
    elif mutation == "staged_receipt_missing":
        staged_receipt_path.unlink()
    elif mutation in {"staged_digest_mismatch", "staged_result_digest_mismatch"}:
        staged_receipt = json.loads(staged_receipt_path.read_text(encoding="utf-8"))
        if mutation == "staged_digest_mismatch":
            staged_receipt["staged_sha256"]["action.py"] = "c" * 64
        else:
            staged_receipt["typed_action_result"]["action_source_sha256"] = "c" * 64
        staged_receipt_path.write_text(json.dumps(staged_receipt), encoding="utf-8")
    elif "_inventory_path" in mutation:
        staged_receipt = json.loads(staged_receipt_path.read_text(encoding="utf-8"))
        inventory_name = (
            "source_inventory"
            if mutation.endswith("source_inventory_path")
            else "staged_inventory"
        )
        inventory = json.loads(staged_receipt[inventory_name])
        entries = inventory["entries"]
        if mutation.startswith("duplicate_"):
            entries.append(dict(entries[0]))
        elif mutation.startswith("missing_"):
            entries.pop()
        else:
            entries[1]["path"] = "unexpected.json"
        staged_receipt[inventory_name] = json.dumps(inventory)
        staged_receipt_path.write_text(json.dumps(staged_receipt), encoding="utf-8")
    if mutation != "missing_receipt":
        (evidence / "lifecycle-receipt.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )

    result = _run_summary(env)
    assert result.returncode != 0
    summary = json.loads((evidence / "acceptance-summary.json").read_text())
    assert summary["admission"]["passed"] is False
    assert expected_issue in summary["admission"]["issues"]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "malformed",
        "wrong_source_commit",
        "wrong_source_tree",
        "wrong_control_commit",
        "wrong_control_tree",
        "wrong_rcc_hash",
        "missing_specification_digest",
        "malformed_specification_digest",
        "conflicting_artifact_digest",
        "conflicting_payload_alias",
        "payload_digest_mismatch",
        "raw_hash_mismatch",
        "multiple_invocations",
        "credentialed_provider",
        "argument_provider_mismatch",
        "provider_control_character",
        "boolean_invocation_count",
        "non_object_root",
    ],
)
def test_exact_summary_script_rejects_invalid_published_details(
    tmp_path: Path, mutation: str
) -> None:
    evidence, _, _, env = _fixture(tmp_path)
    receipt_path = evidence / "published-details-receipt.json"
    if mutation == "missing":
        receipt_path.unlink()
    elif mutation == "malformed":
        receipt_path.write_text("{", encoding="utf-8")
    elif mutation == "non_object_root":
        receipt_path.write_text("[]", encoding="utf-8")
    else:
        details = json.loads(receipt_path.read_text(encoding="utf-8"))
        publication = details["publication"]
        if mutation == "wrong_source_commit":
            details["source"]["commit"] = "0" * 40
        elif mutation == "wrong_source_tree":
            details["source"]["tree"] = "0" * 40
        elif mutation == "wrong_control_commit":
            details["control"]["commit"] = "0" * 40
        elif mutation == "wrong_control_tree":
            details["control"]["tree"] = "0" * 40
        elif mutation == "wrong_rcc_hash":
            details["rcc"]["sha256"] = "0" * 64
        elif mutation == "missing_specification_digest":
            del publication["specification_digest"]
        elif mutation == "malformed_specification_digest":
            publication["specification_digest"] = "sha256:" + "z" * 64
        elif mutation == "conflicting_artifact_digest":
            publication["artifact_digest"] = "sha256:" + "e" * 64
        elif mutation == "payload_digest_mismatch":
            raw = json.loads(publication["raw_json"])
            raw["artifactDigest"] = "sha256:" + "e" * 64
            publication["raw_json"] = json.dumps(raw, separators=(",", ":"))
            publication["raw_json_sha256"] = hashlib.sha256(
                publication["raw_json"].encode("utf-8")
            ).hexdigest()
        elif mutation == "conflicting_payload_alias":
            raw = json.loads(publication["raw_json"])
            raw["artifact_digest"] = "sha256:" + "e" * 64
            publication["raw_json"] = json.dumps(raw, separators=(",", ":"))
            publication["raw_json_sha256"] = hashlib.sha256(
                publication["raw_json"].encode("utf-8")
            ).hexdigest()
        elif mutation == "raw_hash_mismatch":
            publication["raw_json_sha256"] = "0" * 64
        elif mutation == "multiple_invocations":
            publication["invocation_count"] = 2
        elif mutation == "boolean_invocation_count":
            publication["invocation_count"] = True
        elif mutation == "credentialed_provider":
            publication["provider"] = "http://user:secret@127.0.0.1:43210"
            publication["args"][-1] = publication["provider"]
        elif mutation == "argument_provider_mismatch":
            publication["args"][-1] = "http://127.0.0.1:43211"
        elif mutation == "provider_control_character":
            publication["provider"] = "http://127.0.0.1:43210\n"
            publication["args"][-1] = publication["provider"]
        receipt_path.write_text(json.dumps(details), encoding="utf-8")

    result = _run_summary(env)
    assert result.returncode != 0
    summary = json.loads((evidence / "acceptance-summary.json").read_text())
    assert summary["admission"]["passed"] is False
    assert (
        "published_details_receipt_missing_or_invalid" in summary["admission"]["issues"]
    )
