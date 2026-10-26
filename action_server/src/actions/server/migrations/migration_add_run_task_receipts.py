"""Add Task association and lifecycle evidence without adopting historical Runs."""
from actions.server._database import Database
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration


def migrate(db: Database) -> None:
    from actions.server._models import get_model_db_rules
    from actions.server.run_outputs.models import RunTaskReceipt

    db.execute(
        "ALTER TABLE run_pin ADD COLUMN state_updated_ms TEXT NOT NULL DEFAULT ''"
    )
    rules = get_model_db_rules()
    db.execute(db.create_table_sql(RunTaskReceipt, rules))
    for sql in db.create_unique_indexes_sql(
        RunTaskReceipt, rules
    ) + db.create_non_unique_indexes_sql(RunTaskReceipt, rules):
        db.execute(sql)
    db.insert(Migration(id=21, name=MIGRATION_ID_TO_NAME[21]))
