"""Small local Action used by the Canvas first-boot example fixture."""

from actions import action

_RECORDS: tuple[dict[str, str], ...] = (
    {"name": "Alpha guide", "category": "Guide"},
    {"name": "Alpha checklist", "category": "Checklist"},
    {"name": "Bravo checklist", "category": "Checklist"},
)


@action
def search_catalog(query: str) -> dict[str, object]:
    """Search fixed local records without credentials, network or side effects."""

    normalized = query.strip().casefold()
    if not normalized:
        raise ValueError("Search terms must include a non-whitespace character.")
    items = [
        dict(record)
        for record in _RECORDS
        if normalized in f"{record['name']} {record['category']}".casefold()
    ]
    return {"items": items, "status": "ready"}
