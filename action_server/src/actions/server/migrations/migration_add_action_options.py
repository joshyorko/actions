from actions.server._database import Database
from actions.server.migrations import Migration


def migrate(db: Database) -> None:
    from actions.server.migrations import MIGRATION_ID_TO_NAME

    db.execute(
        """
ALTER TABLE action 
ADD COLUMN options TEXT NOT NULL DEFAULT "";
"""
    )

    db.insert(Migration(id=5, name=MIGRATION_ID_TO_NAME[5]))
