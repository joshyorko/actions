"""Permit UI-only Deployment revisions without manufacturing a Package.

The nullable integrity anchor retains its real Package FK. Runtime services
still validate every backend Package and deny execution for UI-only revisions.
Call within the common migration transaction; failures must roll back the DDL.
"""

from actions.server._database import Database
from actions.server._models import get_model_db_rules
from actions.server.foundry.models import FoundryDeploymentRevision
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration


def migrate(db: Database) -> None:
    if db.backend_name == "postgresql":
        db.execute(
            "ALTER TABLE foundry_deployment_revision "
            "ALTER COLUMN foundry_package_revision_id DROP NOT NULL"
        )
    else:
        # SQLite cannot alter nullability. No schema17 table references this
        # record's row ID; retained heads and audit use scoped revision digests.
        table = "foundry_deployment_revision"
        replacement = table + "_v18"
        rules = get_model_db_rules()
        sql = db.create_table_sql(FoundryDeploymentRevision, rules)
        db.execute(sql.replace(f"{table}(", f"{replacement}(", 1))
        columns = (
            "id,workspace_id,deployment_id,revision_id,"
            "foundry_package_revision_id,selection_json,snapshots_json"
        )
        db.execute(
            f"INSERT INTO {replacement} ({columns}) SELECT {columns} FROM {table}"
        )
        db.execute(f"DROP TABLE {table}")
        db.execute(f"ALTER TABLE {replacement} RENAME TO {table}")
        for statement in db.create_unique_indexes_sql(
            FoundryDeploymentRevision, rules
        ) + db.create_non_unique_indexes_sql(FoundryDeploymentRevision, rules):
            db.execute(statement)
    db.insert(Migration(id=18, name=MIGRATION_ID_TO_NAME[18]))
