from actions.server._database import Database
from actions.server.migrations import Migration


def migrate(db: Database) -> None:
    from actions.server.migrations import MIGRATION_ID_TO_NAME

    column_type = "BOOLEAN" if db.backend_name == "postgresql" else "INTEGER"
    db.execute(
        f"""
ALTER TABLE action
ADD COLUMN is_consequential {column_type};
"""
    )

    db.insert(Migration(id=3, name=MIGRATION_ID_TO_NAME[3]))
