"""Fail closed unless all frozen rollback cases ran and passed without skips."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

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
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("junit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = ET.parse(args.junit).getroot()
    cases = root.findall(".//testcase")
    names = {
        (case.attrib.get("classname", ""), case.attrib.get("name", ""))
        for case in cases
    }
    failures = sum(len(case.findall("failure")) for case in cases)
    errors = sum(len(case.findall("error")) for case in cases)
    skipped = sum(len(case.findall("skipped")) for case in cases)
    if names != EXPECTED_CASES or len(cases) != 4 or failures or errors or skipped:
        raise SystemExit(
            "frozen rollback JUnit result did not contain exactly four passing expected cases"
        )
    args.output.write_text(
        json.dumps(
            {
                "expected_test_cases": [
                    {"classname": classname, "name": name}
                    for classname, name in sorted(EXPECTED_CASES)
                ],
                "tests": len(cases),
                "failures": failures,
                "errors": errors,
                "skipped": skipped,
                "status": "PASS",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
