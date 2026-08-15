from actions.server._database import Database
from actions.server.migrations import Migration


def migrate(db: Database) -> None:
    from actions.server.migrations import MIGRATION_ID_TO_NAME

    columns = set(db.list_table_and_columns().get("run", []))
    for column in ("stdout", "stderr"):
        if column in columns:
            db.execute(f"ALTER TABLE run DROP COLUMN {column}")

    db.insert(Migration(id=12, name=MIGRATION_ID_TO_NAME[12]))
