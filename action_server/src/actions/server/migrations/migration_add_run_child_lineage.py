"""Add identity-only linkage for internal child Runs; adopt no historical Runs."""
from actions.server._database import Database
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration


def migrate(db: Database) -> None:
    from actions.server._models import get_model_db_rules
    from actions.server.run_outputs.models import RunChildLineage

    rules = get_model_db_rules()
    db.execute(db.create_table_sql(RunChildLineage, rules))
    for sql in db.create_unique_indexes_sql(
        RunChildLineage, rules
    ) + db.create_non_unique_indexes_sql(RunChildLineage, rules):
        db.execute(sql)
    db.insert(Migration(id=23, name=MIGRATION_ID_TO_NAME[23]))
