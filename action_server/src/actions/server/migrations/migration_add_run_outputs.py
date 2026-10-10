"""Add common Run pins/output authority without assigning synthetic legacy pins."""

from actions.server._database import Database
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration


def migrate(db: Database) -> None:
    from actions.server._models import get_model_db_rules
    from actions.server.run_outputs.models import MODEL_CLASSES

    rules = get_model_db_rules()
    for cls in MODEL_CLASSES:
        db.execute(db.create_table_sql(cls, rules))
        for sql in db.create_unique_indexes_sql(
            cls, rules
        ) + db.create_non_unique_indexes_sql(cls, rules):
            db.execute(sql)
    db.insert(Migration(id=15, name=MIGRATION_ID_TO_NAME[15]))
