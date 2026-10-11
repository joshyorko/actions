import pytest

from canvas_query import UI_URI, canvas_fixture_search, canvas_view


def test_search_returns_typed_view_rows_and_no_artifact_claim():
    assert canvas_fixture_search(" alpha ") == {
        "rows": [
            {"id": "record-001", "title": "Alpha guide", "category": "Guide"},
            {
                "id": "record-002",
                "title": "Alpha checklist",
                "category": "Checklist",
            },
        ],
        "artifact": None,
        "error": None,
    }


def test_search_uses_a_fixed_error_for_unknown_terms():
    expected = {
        "rows": [],
        "artifact": None,
        "error": {
            "code": "no_matches",
            "message": "No records matched that query.",
        },
    }
    assert canvas_fixture_search("private-marker-17") == expected
    assert "private-marker-17" not in str(expected)


def test_search_enforces_query_boundaries_without_echoing_input():
    valid_query = "😀" * 64
    assert canvas_fixture_search(valid_query) == {
        "rows": [],
        "artifact": None,
        "error": {
            "code": "no_matches",
            "message": "No records matched that query.",
        },
    }

    private_query = "private-marker-" + ("x" * 65)
    for invalid_query in ("", "   ", "😀" * 65, private_query):
        with pytest.raises(ValueError) as error:
            canvas_fixture_search(invalid_query)
        if invalid_query:
            assert invalid_query not in str(error.value)


def test_view_resource_matches_its_recorded_identity_and_digest():
    import hashlib
    import json
    from pathlib import Path

    resource = Path(__file__).parents[1] / "canvas.html"
    metadata = json.loads(
        (Path(__file__).parents[1] / "canvas-resource.json").read_text(encoding="utf-8")
    )

    assert metadata["uri"] == UI_URI
    assert metadata["mime_type"] == "text/html;profile=mcp-app"
    assert hashlib.sha256(resource.read_bytes()).hexdigest() == metadata["sha256"]
    assert canvas_view() == resource.read_text(encoding="utf-8")
