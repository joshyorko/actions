"""Add empty provider metadata tables without provisioning permissions."""
from actions.server._database import Database
from actions.server._models import get_model_db_rules
from actions.server.foundry.provider_models import MODEL_CLASSES
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration


def migrate(db: Database) -> None:
    rules = get_model_db_rules()
    for cls in MODEL_CLASSES:
        db.execute(db.create_table_sql(cls, rules))
        for statement in db.create_unique_indexes_sql(
            cls, rules
        ) + db.create_non_unique_indexes_sql(cls, rules):
            db.execute(statement)
    db.insert(Migration(id=19, name=MIGRATION_ID_TO_NAME[19]))
