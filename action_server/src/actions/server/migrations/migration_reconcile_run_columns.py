from actions.server._database import Database


_ARCHIVE_TABLE = "run_legacy_output_archive"


def archive_legacy_run_output(db: Database) -> None:
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
            conflict_conditions = [
                f"archive.{column} IS NOT NULL"
                f" AND run.{column} IS NOT NULL"
                f" AND archive.{column} <> run.{column}"
                for column in legacy_columns
            ]
            with db.cursor() as cursor:
                db.execute_query(
                    cursor,
                    f"""
SELECT archive.run_id
FROM {_ARCHIVE_TABLE} AS archive
JOIN run ON run.id = archive.run_id
WHERE {" OR ".join(conflict_conditions)}
LIMIT 1
""",
                )
                conflict = cursor.fetchone()
            if conflict is not None:
                raise ValueError(
                    f"Cannot reconcile run output archive collision for {conflict[0]}"
                )
            db.execute(
                f"""
INSERT INTO {_ARCHIVE_TABLE} (run_id, stdout, stderr)
SELECT id, {stdout_expression}, {stderr_expression}
FROM run
WHERE {non_null_condition}
ON CONFLICT (run_id) DO UPDATE SET
    stdout = COALESCE({_ARCHIVE_TABLE}.stdout, excluded.stdout),
    stderr = COALESCE({_ARCHIVE_TABLE}.stderr, excluded.stderr)
"""
            )

def migrate(db: Database) -> None:
    from actions.server.migrations import MIGRATION_ID_TO_NAME

    archive_legacy_run_output(db)
    for column in ("stdout", "stderr"):
        if column in db.list_table_and_columns().get("run", []):
            db.execute(f"ALTER TABLE run DROP COLUMN {column}")

    db.execute(
        "INSERT INTO migration (id, name) VALUES (?, ?) ON CONFLICT (id) DO NOTHING",
        [12, MIGRATION_ID_TO_NAME[12]],
    )
