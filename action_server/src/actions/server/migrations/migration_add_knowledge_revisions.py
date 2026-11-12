"""Migration22: empty immutable definitions; no adoption, grants or readiness.

The historical shape/rules are frozen here, independently of future live models.
There is no down migration; older Runtime versions must refuse the newer schema.
"""
from dataclasses import dataclass

from actions.server._database import Database, DBRules
from actions.server.migrations import Migration


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


def migrate(db: Database) -> None:
    rules = DBRules()
    rules.foreign_keys.update(
        {
            "KnowledgeCollectionRevision.workspace_id",
            "KnowledgeCollectionRevision.foundry_source_revision_id",
            "KnowledgeCollectionRevision.foundry_request_id",
        }
    )
    rules.indexes.update(
        {
            "KnowledgeCollectionRevision.workspace_id",
            "KnowledgeCollectionRevision.collection_id",
        }
    )
    db.execute(db.create_table_sql(KnowledgeCollectionRevision, rules))
    for statement in db.create_non_unique_indexes_sql(
        KnowledgeCollectionRevision, rules
    ):
        db.execute(statement)
    db.insert(Migration(22, "add_knowledge_revisions"))
