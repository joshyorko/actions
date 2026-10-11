"""Additive migration preserves legacy authority and fresh schema parity."""

from pathlib import Path

from action_server_tests.fixtures import database_v0

from actions.server._database import Database
from actions.server._models import create_db, get_all_model_classes
from actions.server.migrations import CURRENT_VERSION, migrate_db
from actions.server.run_outputs.models import RunPin


def test_legacy_migration_preserves_runs_and_creates_no_synthetic_pins(tmp_path):
    old = database_v0.__wrapped__(tmp_path)
    database = Database(old)
    with database.connect():
        with database.cursor() as cursor:
            database.execute_query(
                cursor,
                "SELECT id,status,inputs,result,relative_artifacts_dir FROM run ORDER BY id",
            )
            before = cursor.fetchall()
    assert migrate_db(old, CURRENT_VERSION)
    with database.connect():
        database.initialize(get_all_model_classes())
        with database.cursor() as cursor:
            database.execute_query(
                cursor,
                "SELECT id,status,inputs,result,relative_artifacts_dir FROM run ORDER BY id",
            )
            assert cursor.fetchall() == before
        assert database.all(RunPin) == []
        upgraded_schema = database.list_table_and_columns()
        upgraded_indexes = database.list_indexes()
    with create_db(tmp_path / "fresh.db") as fresh:
        assert fresh.list_table_and_columns() == upgraded_schema
        assert fresh.list_indexes() == upgraded_indexes


def test_sqlite_schema_matches_committed_golden():
    from actions.server._models import get_model_db_rules

    db = Database(":memory:")
    classes = get_all_model_classes()
    rules = get_model_db_rules()
    db.register_classes(classes)
    snippets = []
    for cls in classes:
        snippets.append("'''\n" + db.create_table_sql(cls, rules).strip() + "\n''',")
        snippets.extend(
            "'''\n" + sql.strip() + "\n''',"
            for sql in db.create_unique_indexes_sql(cls, rules)
            + db.create_non_unique_indexes_sql(cls, rules)
        )
    actual = (
        "IMPORTANT: If this file changes a new migration must be put in place!\n\n[\n"
        + "\n\n\n".join(snippets)
        + "\n]"
    )
    expected = (
        Path(__file__).parents[1]
        / "test_database"
        / "test_database_schema_evolution.txt"
    )
    assert actual.strip() == expected.read_text().strip()
