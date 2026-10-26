from actions import action
from actions.knowledge import search

@action
def report(ingestion_handle: str, query: str, offset: int, limit: int, fail: bool = False) -> dict:
    """Search only the exact publicly authorized prepared invocation."""
    value = search('documents', 'documents.search/v1', ingestion_handle=ingestion_handle, query=query, offset=offset, limit=limit)
    try:
        search('documents', 'documents.search/v1', ingestion_handle=ingestion_handle, query=query+'-changed', offset=offset, limit=limit)
    except ValueError:
        pass
    else:
        raise RuntimeError('Changed invocation escaped its prepared context')
    if fail:
        raise RuntimeError('Synthetic requested Knowledge failure')
    return value
