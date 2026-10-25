"""Current release names and independent SQLite index-definition qualification."""

import sqlite3
from contextlib import closing

import pytest
from action_server_tests.fixtures import database_v0

from actions.server._database import Database
from actions.server._models import create_db, get_all_model_classes
from actions.server.migrations import CURRENT_VERSION, migrate_db


def sqlite_index_definitions(path):
    """Observe actual indexes without Database.list_indexes' SQLite filter.

    Index-list enumeration order and column storage offsets are not definitions.
    Preserve key order, uniqueness, origin, partial flag, collation/direction,
    auxiliary columns and original SQL (including expressions and predicates).
    Raw SQL equality is deliberately conservative, not SQL semantic equivalence.
    """
    definitions = {}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        for (table,) in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall():
            for _, name, unique, origin, partial in db.execute(
                "SELECT * FROM pragma_index_list(?)", (table,)
            ).fetchall():
                columns = tuple(
                    (seq, column, descending, collation, key)
                    for seq, _, column, descending, collation, key in db.execute(
                        "SELECT * FROM pragma_index_xinfo(?) ORDER BY seqno", (name,)
                    )
                )
                sql = db.execute(
                    "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
                    (name,),
                ).fetchone()[0]
                definitions[(table, name)] = (unique, origin, partial, columns, sql)
    return definitions


@pytest.mark.parametrize(
    "changed",
    [
        "CREATE INDEX idx ON t(b) WHERE b > 0",
        "CREATE UNIQUE INDEX idx ON t(a) WHERE b > 0",
        "CREATE INDEX idx ON t(a) WHERE b > 1",
    ],
    ids=["columns", "uniqueness", "predicate"],
)
def test_index_observer_detects_same_name_definition_changes(tmp_path, changed):
    path = tmp_path / "index-control.db"
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE t(a INTEGER, b INTEGER)")
        db.execute("CREATE INDEX idx ON t(a) WHERE b > 0")
    original = sqlite_index_definitions(path)
    assert original and original == sqlite_index_definitions(path)
    with closing(sqlite3.connect(path)) as db:
        db.execute("DROP INDEX idx")
        db.execute(changed)
    observed = sqlite_index_definitions(path)
    assert observed.keys() == original.keys()
    assert observed != original


@pytest.mark.parametrize("intermediate", [None, 15, 19, 21])
def test_historical_database_reaches_current_release(
    tmp_path, intermediate, record_property
):
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
    upgraded_definitions = sqlite_index_definitions(path)
    fresh_definitions = sqlite_index_definitions(tmp_path / "fresh.db")
    assert upgraded_definitions and fresh_definitions
    record_property("sqlite_index_definition_count", len(upgraded_definitions))
    assert upgraded_definitions == fresh_definitions
