from actions import action
from actions.knowledge import ingest

try:
    ingest('documents', 'documents.ingest/v1')
except ValueError:
    pass
else:
    raise RuntimeError('Knowledge context leaked into module import')

@action
def report(fail: bool = False) -> dict:
    """Ingest the explicitly prepared synthetic document."""
    value = ingest('documents', 'documents.ingest/v1')
    try:
        ingest('undeclared', 'documents.ingest/v1')
    except ValueError:
        pass
    else:
        raise RuntimeError('Undeclared context lookup succeeded')
    if fail:
        raise RuntimeError('Synthetic requested Knowledge failure')
    return value
