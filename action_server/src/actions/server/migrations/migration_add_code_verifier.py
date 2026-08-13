from actions.server._database import Database
from actions.server.migrations import Migration


def migrate(db: Database) -> None:
    from actions.server.migrations import MIGRATION_ID_TO_NAME

    db.execute(
        """
ALTER TABLE o_auth2_user_data 
ADD COLUMN code_verifier TEXT NOT NULL DEFAULT "";
"""
    )

    db.insert(Migration(id=7, name=MIGRATION_ID_TO_NAME[7]))
