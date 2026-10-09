"""Python serialization checks for the shared Canvas query-results fixture.

These tests cover fixture interchange only. They do not exercise Runtime
dispatch, app bindings, authorization, or artifact-handle resolution.
"""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE_DIRECTORY = (
    _REPOSITORY_ROOT / "docs" / "contracts" / "canvas" / "fixtures"
)
_SCHEMA = json.loads(
    (_FIXTURE_DIRECTORY / "query-results-v0.1.schema.json").read_text(
        encoding="utf-8"
    )
)
_FIXTURE = json.loads(
    (_FIXTURE_DIRECTORY / "query-results-v0.1.fixture.json").read_text(
        encoding="utf-8"
    )
)
_VALIDATOR = Draft202012Validator(_SCHEMA)


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

