"""Record future routing projections; exact keys cannot reconstruct old winners."""

from actions.server._database import Database
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration


def migrate(db: Database) -> None:
    from actions.server._models import McpResourceRouting, get_model_db_rules

    rules = get_model_db_rules()
    db.execute(db.create_table_sql(McpResourceRouting, rules))
    for sql in db.create_unique_indexes_sql(McpResourceRouting, rules):
        db.execute(
            sql.replace("CREATE UNIQUE INDEX", "CREATE UNIQUE INDEX IF NOT EXISTS", 1)
        )
    db.insert(Migration(id=14, name=MIGRATION_ID_TO_NAME[14]))
