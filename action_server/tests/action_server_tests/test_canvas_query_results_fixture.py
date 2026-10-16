"""Python serialization checks for the shared Canvas query-results fixture.

These tests cover fixture interchange only. They do not exercise Runtime
dispatch, app bindings, authorization, or artifact-handle resolution.
"""

import copy
import json
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE_DIRECTORY = _REPOSITORY_ROOT / "docs" / "contracts" / "canvas" / "fixtures"
_SCHEMA = json.loads(
    (_FIXTURE_DIRECTORY / "query-results-v0.1.schema.json").read_text(encoding="utf-8")
)
_FIXTURE = json.loads(
    (_FIXTURE_DIRECTORY / "query-results-v0.1.fixture.json").read_text(encoding="utf-8")
)
_VALIDATOR = Draft202012Validator(_SCHEMA)
_FRONTEND_DIRECTORY = _REPOSITORY_ROOT / "action_server" / "frontend"
_TYPESCRIPT_ROUND_TRIP_TEST = (
    _FRONTEND_DIRECTORY
    / "apps"
    / "canvas-view"
    / "src"
    / "query-results"
    / "CanvasContractRoundTrip.test.tsx"
)


def _require_frontend_bridge(node: str | None, vitest: Path, required: bool) -> None:
    if node is not None and vitest.is_file():
        return

    message = "Cross-language acceptance requires the prepared frontend Node/Vitest workspace."
    if required:
        raise AssertionError(
            f"Required Python-TypeScript fixture bridge is unavailable: {message}"
        )
    pytest.skip(message)


def test_query_results_fixture_schema_is_valid() -> None:
    Draft202012Validator.check_schema(_SCHEMA)


def test_shared_query_results_fixture_round_trips_as_json() -> None:
    serialized = json.dumps(_FIXTURE, allow_nan=False)
    decoded = json.loads(serialized)

    assert decoded == _FIXTURE
    _VALIDATOR.validate(decoded)
    assert decoded["input"] == {"query": "alpha"}
    assert len(decoded["success"]["rows"]) == 2
    assert decoded["success"]["artifact"]["handle"].startswith("art_")
    assert decoded["domainError"]["error"]["code"] == "no_matches"


def test_python_json_round_trips_through_typescript_and_back(tmp_path: Path) -> None:
    node = shutil.which("node")
    vitest = _FRONTEND_DIRECTORY / "node_modules" / "vitest" / "vitest.mjs"
    _require_frontend_bridge(
        node,
        vitest,
        required=os.environ.get("ACTIONS_CANVAS_REQUIRE_ROUNDTRIP") == "1",
    )
    assert node is not None

    python_json_path = tmp_path / "python-fixture.json"
    typescript_json_path = tmp_path / "typescript-fixture.json"
    python_json = json.dumps(_FIXTURE, allow_nan=False, separators=(",", ":"))
    python_json_path.write_text(python_json, encoding="utf-8")

    environment = os.environ.copy()
    environment["ACTIONS_CANVAS_PYTHON_JSON_PATH"] = str(python_json_path)
    environment["ACTIONS_CANVAS_TYPESCRIPT_JSON_PATH"] = str(typescript_json_path)
    command = [
        node,
        str(vitest),
        "--run",
        "--config",
        "apps/canvas-view/vitest.config.ts",
        str(_TYPESCRIPT_ROUND_TRIP_TEST),
        "--maxWorkers=1",
        "--fileParallelism=false",
    ]
    completed = subprocess.run(
        command,
        cwd=_FRONTEND_DIRECTORY,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert (
        completed.returncode == 0
    ), f"TypeScript schema validation failed.\n{completed.stdout}\n{completed.stderr}"
    assert typescript_json_path.is_file(), (
        f"TypeScript did not write its round-trip JSON.\n"
        f"{completed.stdout}\n{completed.stderr}"
    )

    typescript_json = typescript_json_path.read_text(encoding="utf-8")
    typescript_value = json.loads(typescript_json)
    _VALIDATOR.validate(typescript_value)
    assert typescript_value == _FIXTURE
    assert typescript_json == python_json


def test_required_python_typescript_bridge_fails_closed_without_node() -> None:
    vitest = _FRONTEND_DIRECTORY / "node_modules" / "vitest" / "vitest.mjs"
    with pytest.raises(
        AssertionError, match="Required Python-TypeScript fixture bridge"
    ):
        _require_frontend_bridge(None, vitest, required=True)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda fixture: fixture.update(unrecognized=True),
        lambda fixture: fixture["input"].update(query="   "),
        lambda fixture: fixture["success"]["artifact"].update(handle="../file"),
        lambda fixture: fixture["success"]["rows"].pop(),
    ],
    ids=["unknown-field", "blank-query", "malformed-handle", "missing-row"],
)
def test_invalid_fixture_values_are_rejected(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    invalid = copy.deepcopy(_FIXTURE)
    mutate(invalid)

    assert list(_VALIDATOR.iter_errors(invalid))
