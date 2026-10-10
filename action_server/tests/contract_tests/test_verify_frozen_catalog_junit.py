import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "verify_frozen_catalog_junit.py"
SPEC = importlib.util.spec_from_file_location("verify_frozen_catalog_junit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)

EXPECTED_CASES = {
    (
        "tests.action_server_tests.test_cli_mcp_catalog_rollback",
        "test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[resource]",
    ),
    (
        "tests.action_server_tests.test_cli_mcp_catalog_rollback",
        "test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[template]",
    ),
    (
        "tests.action_server_tests.test_cli_mcp_catalog_rollback",
        "test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[prompt]",
    ),
    (
        "tests.action_server_tests.test_cli_live_reload_multi_package",
        "test_failed_watched_reload_keeps_both_packages_and_recovers",
    ),
    (
        "tests.action_server_tests.test_cli_successful_generation_drain",
        "test_successful_generation_switch_drains_old_run_on_its_source_snapshot",
    ),
    (
        "tests.action_server_tests.test_cli_multi_package_sync",
        "test_additive_import_serves_duplicate_action_names_across_restart",
    ),
    (
        "tests.action_server_tests.test_cli_multi_package_sync",
        "test_start_sync_treats_repeated_dirs_as_one_desired_set",
    ),
    (
        "tests.action_server_tests.test_cli_multi_package_sync",
        "test_start_sync_rejects_bad_later_package_without_partial_database_update",
    ),
    (
        "tests.action_server_tests.test_cli_multi_package_sync",
        "test_failed_sync_keeps_last_good_unmanaged_package_sources",
    ),
    (
        "tests.action_server_tests.test_cli_multi_package_sync",
        "test_sync_rejects_historical_mcp_alias_capture_and_rename_recovers",
    ),
}


def _write_junit(path: Path, status: str | None = None) -> None:
    suite = ET.Element("testsuite", tests="10", failures="0", errors="0", skipped="0")
    for classname, name in sorted(EXPECTED_CASES):
        case = ET.SubElement(suite, "testcase", classname=classname, name=name)
        if status and name.endswith("rename_recovers"):
            ET.SubElement(case, status, message="synthetic validator test")
            suite.set("skipped" if status == "skipped" else "failures", "1")
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def _run_validator(monkeypatch, junit: Path, output: Path) -> None:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(junit), str(output)])
    VERIFIER.main()


def test_frozen_junit_requires_exact_ten_cases_and_records_pass(tmp_path, monkeypatch):
    assert VERIFIER.EXPECTED_CASES == EXPECTED_CASES
    junit = tmp_path / "result.xml"
    output = tmp_path / "summary.json"
    _write_junit(junit)

    _run_validator(monkeypatch, junit, output)

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["tests"] == 10
    assert summary["failures"] == summary["errors"] == summary["skipped"] == 0
    assert summary["status"] == "PASS"


@pytest.mark.parametrize("status", ["failure", "error", "skipped"])
def test_frozen_junit_rejects_failure_error_or_skip(tmp_path, monkeypatch, status):
    junit = tmp_path / "result.xml"
    _write_junit(junit, status=status)

    with pytest.raises(SystemExit, match="exactly ten passing expected cases"):
        _run_validator(monkeypatch, junit, tmp_path / "summary.json")
