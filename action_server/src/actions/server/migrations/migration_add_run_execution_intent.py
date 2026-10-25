"""Add detached execution metadata without inventing legacy admissions."""
from actions.server._database import Database
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration


def migrate(db: Database) -> None:
    from actions.server._models import get_model_db_rules
    from actions.server.run_outputs.models import RunExecutionIntent

    rules = get_model_db_rules()
    db.execute(db.create_table_sql(RunExecutionIntent, rules))
    db.insert(Migration(id=20, name=MIGRATION_ID_TO_NAME[20]))
