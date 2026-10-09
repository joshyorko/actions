"""Static actions that expose the core MCP v2 surfaces."""

from actions import Response, Table
from actions.mcp import prompt, resource, tool

_ITEMS = (
    {
        "item_id": "alpha",
        "title": "Alpha field guide",
        "category": "guide",
        "summary": "A short guide to the sample catalog.",
    },
    {
        "item_id": "bravo",
        "title": "Bravo checklist",
        "category": "checklist",
        "summary": "A concise checklist for trying the demo.",
    },
    {
        "item_id": "charlie",
        "title": "Charlie reference",
        "category": "reference",
        "summary": "A small reference entry with no external data.",
    },
)
_NOT_FOUND = "No demo item matches this ID."
_COLUMNS = ["item_id", "title", "category", "summary"]


@tool(
    title="Search demo catalog",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)
def search_demo_catalog(query: str, limit: int = 2) -> Response[Table]:
    """Search the local showcase catalog by title, category, or summary.

    Args:
        query: Text to match in the local demo catalog.
        limit: Maximum number of matching rows to return, from one through three.

    Returns:
        Matching catalog rows as a structured table.
    """
    normalized_query = query.strip().casefold()
    if not normalized_query:
        return Response(error="Search text must not be empty.")

    matches = [
        item
        for item in _ITEMS
        if normalized_query in " ".join(item.values()).casefold()
    ][: max(1, min(limit, len(_ITEMS)))]
    return Response(
        result=Table(
            columns=_COLUMNS,
            rows=[[item[column] for column in _COLUMNS] for item in matches],
            name="demo_catalog",
            description="Static entries used by the core MCP v2 showcase.",
        )
    )


@tool(
    title="Look up demo item",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)
def lookup_demo_item(item_id: str) -> Response[dict[str, str]]:
    """Return a structured local catalog item for an identifier.

    Args:
        item_id: Identifier of a showcase item.

    Returns:
        The matching static item, or a fixed safe error.
    """
    item = next((item for item in _ITEMS if item["item_id"] == item_id), None)
    if item is None:
        return Response(error=_NOT_FOUND)
    return Response(result=dict(item))


@resource("showcase://catalog/overview", mime_type="text/plain")
def catalog_overview() -> str:
    """Describe the static showcase catalog."""
    return "Static demo catalog: alpha field guide, bravo checklist, charlie reference."


@resource("showcase://items/{item_id}", mime_type="text/plain")
def item_resource(item_id: str) -> str:
    """Read one item's summary from the static catalog."""
    item = next((item for item in _ITEMS if item["item_id"] == item_id), None)
    if item is None:
        return _NOT_FOUND
    return f"{item['title']}: {item['summary']}"


@prompt
def explain_demo_item(item_id: str) -> str:
    """Explain one item from the local demo catalog.

    Args:
        item_id: Identifier of a showcase item.
    """
    item = next((item for item in _ITEMS if item["item_id"] == item_id), None)
    if item is None:
        return "Explain a sample item from the local showcase catalog."
    return f"Explain {item['title']} using this summary: {item['summary']}"
