"""A local catalog exposed through the public MCP Apps decorators."""

import re
from pathlib import Path

from actions.mcp import resource, tool

UI_URI = "ui://action-canvas/v1/canvas.html?query-fixture=0.1"
_NO_MATCHES = {
    "code": "no_matches",
    "message": "No records matched that query.",
}
_RECORDS = (
    {"id": "record-001", "title": "Alpha guide", "category": "Guide"},
    {"id": "record-002", "title": "Alpha checklist", "category": "Checklist"},
    {"id": "record-003", "title": "Bravo checklist", "category": "Checklist"},
)
_MAX_QUERY_CODE_POINTS = 64


@resource(
    UI_URI,
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"csp": {}}},
)
def canvas_view() -> str:
    """Serve the built Canvas View included in this template archive."""
    return Path(__file__).with_name("canvas.html").read_text(encoding="utf-8")


@tool(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
    meta={"ui": {"resourceUri": UI_URI, "visibility": ["model", "app"]}},
)
def canvas_fixture_search(query: str) -> dict[str, object]:
    """Search a small local catalog and return a partial local result shape.

    Args:
        query: Text to match in a record title or category.

    Returns:
        Matching records or a fixed no-match result. This example intentionally
        does not return an artifact handle because Runtime has no
        Workspace-scoped artifact resolver for this view.
    """
    if (
        not query
        or re.search(r"\S", query) is None
        or len(query) > _MAX_QUERY_CODE_POINTS
    ):
        raise ValueError(
            "Query must be 1 to 64 characters and contain at least one "
            "non-whitespace character."
        )

    normalized_query = query.strip().casefold()

    rows = [
        record
        for record in _RECORDS
        if normalized_query in f"{record['title']} {record['category']}".casefold()
    ]
    if not rows:
        return {"rows": [], "artifact": None, "error": dict(_NO_MATCHES)}

    return {"rows": rows, "artifact": None, "error": None}
