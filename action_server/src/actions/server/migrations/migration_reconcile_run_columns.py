from actions.server._database import Database


_ARCHIVE_TABLE = "run_legacy_output_archive"


def migrate(db: Database) -> None:
    from actions.server.migrations import MIGRATION_ID_TO_NAME

    columns = set(db.list_table_and_columns().get("run", []))
    legacy_columns = [column for column in ("stdout", "stderr") if column in columns]
    if legacy_columns:
        stdout_expression = "stdout" if "stdout" in legacy_columns else "NULL"
        stderr_expression = "stderr" if "stderr" in legacy_columns else "NULL"
        non_null_condition = " OR ".join(
            f"{column} IS NOT NULL" for column in legacy_columns
        )
        with db.cursor() as cursor:
            db.execute_query(
                cursor,
                f"SELECT 1 FROM run WHERE {non_null_condition} LIMIT 1",
            )
            has_legacy_output = cursor.fetchone() is not None

        if has_legacy_output:
            db.execute(
                f"""
CREATE TABLE IF NOT EXISTS {_ARCHIVE_TABLE} (
    run_id TEXT NOT NULL PRIMARY KEY,
    stdout TEXT,
    stderr TEXT,
    CHECK (stdout IS NOT NULL OR stderr IS NOT NULL)
)
"""
            )
            db.execute(
                f"""
INSERT INTO {_ARCHIVE_TABLE} (run_id, stdout, stderr)
SELECT id, {stdout_expression}, {stderr_expression}
FROM run
WHERE {non_null_condition}
ON CONFLICT (run_id) DO NOTHING
"""
            )

    for column in legacy_columns:
        db.execute(f"ALTER TABLE run DROP COLUMN {column}")

    db.execute(
        "INSERT INTO migration (id, name) VALUES (?, ?) ON CONFLICT (id) DO NOTHING",
        [12, MIGRATION_ID_TO_NAME[12]],
    )
