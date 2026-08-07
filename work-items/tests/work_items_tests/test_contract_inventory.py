# Copyright 2022-2026 Robocorp and contributors.
# Licensed under the Apache License, Version 2.0.
"""Expected-red inventory for the immutable upstream contract suites.

Each parameter is an attributed upstream test node. Strict xfail makes an
unclassified pass fail CI; closing a gap requires replacing the inventory node
with its executable port before changing the manifest status.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "contracts" / "ported-tests.json").read_text())


def _expected_red_cases():
    return [
        pytest.param(
            case,
            id=case["id"],
            marks=pytest.mark.xfail(strict=True, reason=f"{case['implementation_task']}: {case['id']}"),
        )
        for case in MANIFEST["cases"]
        if case["status"] == "expected_red"
    ]


@pytest.mark.parametrize("case", _expected_red_cases())
def test_ported_contract_expected_red(case):
    pytest.fail(f"contract port pending: {case['source_test']}")


