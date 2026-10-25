"""Common SQL immutable definitions only; no publication or job state."""
from pydantic.dataclasses import dataclass

from actions.server._models import _db_rules


@dataclass
class KnowledgeCollectionRevision:
    id: str
    workspace_id: str
    collection_id: str
    revision_id: str
    specification_json: str
    foundry_source_revision_id: str
    source_provider_json: str
    foundry_request_id: str
    _db_rules.foreign_keys.update(
        {
            "KnowledgeCollectionRevision.workspace_id",
            "KnowledgeCollectionRevision.foundry_source_revision_id",
            "KnowledgeCollectionRevision.foundry_request_id",
        }
    )
    _db_rules.indexes.update(
        {
            "KnowledgeCollectionRevision.workspace_id",
            "KnowledgeCollectionRevision.collection_id",
        }
    )


MODEL_CLASSES = [KnowledgeCollectionRevision]
