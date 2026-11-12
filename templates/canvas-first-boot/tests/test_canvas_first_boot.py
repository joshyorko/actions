"""The exported example consumes public CanvasSpec and local Action contracts."""

import json
import sys
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FIXTURE_ROOT))

from first_boot_actions import search_catalog  # noqa: E402


def test_public_canvas_spec_fixture_is_validated_by_actions_core():
    canvas_contract = pytest.importorskip(
        "actions.canvas_contract",
        reason="the public CanvasSpec contract is staged separately in #100",
    )
    source = (FIXTURE_ROOT / "canvas-spec.json").read_bytes()

    spec = canvas_contract.CanvasSpec.from_json(source)

    assert spec.schema_version == "actions.canvas-spec/v1"
    assert json.loads(spec.to_json()) == json.loads(source)


def test_local_catalog_action_is_deterministic_and_rejects_empty_search():
    assert search_catalog("alpha") == {
        "items": [
            {"name": "Alpha guide", "category": "Guide"},
            {"name": "Alpha checklist", "category": "Checklist"},
        ],
        "status": "ready",
    }
    with pytest.raises(ValueError, match="non-whitespace"):
        search_catalog("  ")
