from actions.server._database import Database
from actions.server.migrations import Migration


def migrate(db: Database) -> None:
    from actions.server.migrations import MIGRATION_ID_TO_NAME

    column_type = "BOOLEAN" if db.backend_name == "postgresql" else "INTEGER CHECK(enabled IN (0, 1))"
    db.execute(
        f"""
ALTER TABLE action 
ADD COLUMN enabled {column_type} NOT NULL DEFAULT {"TRUE" if db.backend_name == "postgresql" else "1"};
"""
    )

    db.insert(Migration(id=2, name=MIGRATION_ID_TO_NAME[2]))
