"""Align migrated databases with the schema generated from current models."""

from actions.server._database import Database
from actions.server.migrations import Migration


def _has_column(db: Database, table: str, column: str) -> bool:
    return column in db.list_table_and_columns().get(table, [])


def _has_index(db: Database, index: str) -> bool:
    with db.cursor() as cursor:
        db.execute_query(
            cursor,
            "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?",
            [index],
        )
        return cursor.fetchone() is not None


def migrate(db: Database) -> None:
    from actions.server.migrations import MIGRATION_ID_TO_NAME

    sqls = []
    for column in ("stdout", "stderr"):
        if _has_column(db, "run", column):
            sqls.append(f"ALTER TABLE run DROP COLUMN {column};")

    if not _has_index(db, "run_run_type_non_unique_index"):
        sqls.append("CREATE INDEX run_run_type_non_unique_index ON run(run_type);")
    if _has_index(db, "schedule_enabled_next_non_unique_index"):
        sqls.append("DROP INDEX schedule_enabled_next_non_unique_index;")
    if _has_index(db, "schedule_depends_on_non_unique_index"):
        sqls.append("DROP INDEX schedule_depends_on_non_unique_index;")
    if not _has_index(db, "schedule_depends_on_schedule_id_non_unique_index"):
        sqls.append(
            "CREATE INDEX schedule_depends_on_schedule_id_non_unique_index "
            "ON schedule(depends_on_schedule_id);"
        )
    if _has_index(db, "trigger_type_non_unique_index"):
        sqls.append("DROP INDEX trigger_type_non_unique_index;")
    if not _has_index(db, "trigger_trigger_type_non_unique_index"):
        sqls.append(
            "CREATE INDEX trigger_trigger_type_non_unique_index ON trigger(trigger_type);"
        )
    for sql in sqls:
        db.execute(sql)

    db.insert(Migration(id=11, name=MIGRATION_ID_TO_NAME[11]))
