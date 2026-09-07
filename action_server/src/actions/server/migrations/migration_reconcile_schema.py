from actions.server._database import Database
from actions.server.migrations import Migration


def migrate(db: Database) -> None:
    from actions.server.migrations import MIGRATION_ID_TO_NAME

    db.execute("DROP INDEX IF EXISTS schedule_enabled_next_non_unique_index")
    db.execute("DROP INDEX IF EXISTS schedule_depends_on_non_unique_index")
    db.execute("DROP INDEX IF EXISTS trigger_type_non_unique_index")
    db.execute(
        "CREATE INDEX IF NOT EXISTS schedule_depends_on_schedule_id_non_unique_index "
        "ON schedule(depends_on_schedule_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS trigger_trigger_type_non_unique_index "
        "ON trigger(trigger_type)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS run_run_type_non_unique_index ON run(run_type)"
    )
    db.insert(Migration(id=11, name=MIGRATION_ID_TO_NAME[11]))
