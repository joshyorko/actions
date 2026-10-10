"""Persist ownership of future MCP catalog names without inventing past history."""

from actions.server._database import Database
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration


def migrate(db: Database) -> None:
    from actions.server._models import McpCatalogName, get_model_db_rules

    rules = get_model_db_rules()
    db.execute(db.create_table_sql(McpCatalogName, rules))
    for sql in db.create_unique_indexes_sql(McpCatalogName, rules):
        db.execute(
            sql.replace("CREATE UNIQUE INDEX", "CREATE UNIQUE INDEX IF NOT EXISTS", 1)
        )
    db.insert(Migration(id=13, name=MIGRATION_ID_TO_NAME[13]))
