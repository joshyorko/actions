"""Current release parity using the canonical historical database fixture."""

import pytest
from action_server_tests.fixtures import database_v0

from actions.server._database import Database
from actions.server._models import create_db, get_all_model_classes
from actions.server.migrations import CURRENT_VERSION, migrate_db


@pytest.mark.parametrize("intermediate", [None, 15, 19, 21])
def test_historical_database_reaches_current_release(tmp_path, intermediate):
    path = database_v0.__wrapped__(tmp_path)
    db = Database(path)

    def retained_runs():
        with db.connect(), db.cursor() as cursor:
            db.execute_query(
                cursor, "SELECT id,status,inputs,result FROM run ORDER BY id"
            )
            return cursor.fetchall()

    original = retained_runs()
    if intermediate is not None:
        assert migrate_db(path, intermediate)
    assert migrate_db(path, CURRENT_VERSION)
    assert retained_runs() == original
    with db.connect():
        db.initialize(get_all_model_classes())
        upgraded = db.list_table_and_columns(), db.list_indexes()
        with db.cursor() as cursor:
            db.execute_query(cursor, "SELECT MAX(id) FROM migration")
            assert cursor.fetchone()[0] == CURRENT_VERSION
    with create_db(tmp_path / "fresh.db") as fresh:
        assert upgraded == (fresh.list_table_and_columns(), fresh.list_indexes())
