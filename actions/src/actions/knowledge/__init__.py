"""Select bounded Knowledge results prepared by the trusted Runtime.

These functions do not query providers or read files, environment or credentials.
An ingestion result describes staged work; only canonical Run completion proves
publication. Search arguments must match the exact host-prepared invocation.
"""
from actions.data._context import _knowledge_result


def ingest(requirement_id: str, operation: str) -> dict:
    """Return a fresh prepared ingestion result, not publication authority."""
    return _knowledge_result(requirement_id, operation, {}, ingest=True)


def search(
    requirement_id: str,
    operation: str,
    *,
    ingestion_handle: str,
    query: str,
    offset: int = 0,
    limit: int = 20,
) -> dict:
    """Return the prepared search result only when every parameter matches.

    The Runtime validates handle authority and provider-specific bounds. Changing
    arguments here cannot perform another search or access another corpus.
    """
    return _knowledge_result(
        requirement_id,
        operation,
        dict(
            ingestion_handle=ingestion_handle, query=query, offset=offset, limit=limit
        ),
        ingest=False,
    )


__all__ = ["ingest", "search"]
