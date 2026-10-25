"""Intent is additive; historical migration15 never creates future metadata."""
import pytest
from action_server_tests.fixtures import database_v0

from actions.server._database import Database
from actions.server._models import create_db, get_all_model_classes
from actions.server.migrations import migrate_db
from actions.server.run_outputs.models import RunExecutionIntent, RunPin


@pytest.mark.parametrize("intermediate", [None, 15, 19])
def test_supported_upgrade_paths_preserve_legacy_runs(tmp_path, intermediate):
    path = database_v0.__wrapped__(tmp_path)
    db = Database(path)
    with db.connect():
        with db.cursor() as cursor:
            db.execute_query(
                cursor, "SELECT id,status,inputs,result FROM run ORDER BY id"
            )
            before = cursor.fetchall()
    if intermediate:
        assert migrate_db(path, intermediate)
        with db.connect():
            assert "run_execution_intent" not in db.list_table_names()
    assert migrate_db(path, 20)
    with db.connect():
        db.initialize(get_all_model_classes())
        assert not db.all(RunExecutionIntent) and not db.all(RunPin)
        with db.cursor() as cursor:
            db.execute_query(
                cursor, "SELECT id,status,inputs,result FROM run ORDER BY id"
            )
            assert cursor.fetchall() == before
        upgraded, indexes = db.list_table_and_columns(), db.list_indexes()
    with create_db(tmp_path / "fresh.db") as fresh:
        assert fresh.list_table_and_columns() == upgraded
        assert fresh.list_indexes() == indexes
