"""Independently archived pre-change v20 schema and pinned Run upgrade."""
import json
from pathlib import Path

from actions.server._database import Database
from actions.server._models import create_db, get_all_model_classes
from actions.server.migrations import migrate_db
from actions.server.run_outputs.models import RunPin, RunTaskReceipt

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def test_v20_pinned_run_upgrade(database_location, tmp_path):
    golden = json.loads(
        (Path(__file__).parent / "test_database/task_clock_v20.json").read_text()
    )
    assert golden["source"] == "ba3aba9e8f623ccd0a17803d29b3cc8b85f65cf2"
    db = Database(database_location)
    with db.connect():
        db.initialize(get_all_model_classes())
        with db.transaction():
            for sql in golden["schema"][db.backend_name]:
                db.execute(sql)
            for table, data in golden["data"].items():
                for row in data["rows"]:
                    if db.backend_name == "postgresql" and table == "action":
                        row = [
                            bool(value) if column == "enabled" else value
                            for column, value in zip(data["columns"], row)
                        ]
                    db.execute(
                        f"INSERT INTO {table} ({','.join(data['columns'])}) VALUES ({','.join('?' for _ in row)})",
                        row,
                    )
        assert "run_task_receipt" not in db.list_table_names()
        with db.cursor() as cursor:
            db.execute_query(cursor, "SELECT * FROM run_pin")
            assert "state_updated_ms" not in [x[0] for x in cursor.description]
    assert migrate_db(database_location, 21, database=db)
    with db.connect():
        db.initialize(get_all_model_classes())
        assert db.all(RunTaskReceipt) == []
        assert db.all(RunPin)[0].state_updated_ms == ""
        for table in ["run", "run_pin", "run_admission", "run_access_grant"]:
            data = golden["data"][table]
            with db.cursor() as cursor:
                db.execute_query(
                    cursor, f"SELECT {','.join(data['columns'])} FROM {table}"
                )
                assert [list(row) for row in cursor.fetchall()] == data["rows"]
        upgraded = db.list_table_and_columns(), db.list_indexes()
    # SQLite parity also covers default/column handling; PG parity uses SQL model DDL.
    if db.backend_name == "sqlite":
        with create_db(tmp_path / "fresh.db") as fresh:
            assert upgraded == (fresh.list_table_and_columns(), fresh.list_indexes())
