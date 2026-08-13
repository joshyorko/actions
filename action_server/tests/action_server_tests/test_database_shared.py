import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic.dataclasses import dataclass

from actions.server._database import DBError, Database
from actions.server.migrations import db_migration_status, migrate_db


@dataclass
class SharedCounter:
    id: str
    value: int


def test_database_selects_postgres_for_explicit_url():
    db = Database("postgresql://localhost/actions_test")

    assert db.backend_name == "postgresql"


def test_cli_accepts_explicit_shared_database_url():
    from actions.server._cli_impl import _create_parser

    args = _create_parser().parse_args(
        ["start", "--database-url", "postgresql://localhost/actions_test"]
    )

    assert args.database_url == "postgresql://localhost/actions_test"


def test_postgresql_placeholder_adapter_only_rewrites_parameters():
    db = Database("postgresql://localhost/actions_test")

    sql = r'''SELECT ?, '?', "?", $$ ? $$, col ? 'key', col ?| array['?'], col ?& array['?'], -- ?
/* ? */ ?\\?'''

    assert db._adapt_sql(sql) == (
        r'''SELECT %s, '?', "?", $$ ? $$, col ? 'key', col ?| array['?'], col ?& array['?'], -- ?
/* ? */ %s\\?'''
    )

    with pytest.raises(DBError, match="expected 2 parameters, got 1"):
        db._adapt_sql(sql, ["only-one"])


def test_postgresql_boolean_schema_uses_native_boolean_without_changing_sqlite():
    from actions.server._models import Action, ActionPackage, get_model_db_rules

    sqlite = Database(":memory:")
    postgres = Database("postgresql://localhost/actions_test")
    classes = [ActionPackage, Action]
    sqlite.initialize(classes)
    postgres.initialize(classes)

    sqlite_sql = sqlite.create_table_sql(Action, get_model_db_rules())
    postgres_sql = postgres.create_table_sql(Action, get_model_db_rules())

    assert "enabled INTEGER CHECK(enabled IN (0, 1))" in sqlite_sql
    assert "enabled BOOLEAN NOT NULL DEFAULT TRUE" in postgres_sql
    assert "is_consequential BOOLEAN" in postgres_sql


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_two_database_instances_preserve_concurrent_atomic_updates():
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")
    first = Database(url)
    second = Database(url)

    with first.connect():
        first.initialize([SharedCounter])
        with first.transaction():
            first.create_tables()
            first.execute("DELETE FROM shared_counter")
            first.insert(SharedCounter("shared", 0))

    def increment(db: Database) -> None:
        with db.connect():
            with db.transaction():
                with db.cursor() as cursor:
                    db.execute_update_returning(
                        cursor,
                        "UPDATE shared_counter SET value=value+1 WHERE id=? RETURNING value",
                        ["shared"],
                    )
                    cursor.fetchone()

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda index: increment(first if index % 2 else second), range(40)))

    with first.connect():
        assert first.first(SharedCounter).value == 40


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_postgresql_transaction_rolls_back_failed_state_update():
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")
    db = Database(url)

    with db.connect():
        db.initialize([SharedCounter])
        with pytest.raises(RuntimeError):
            with db.transaction():
                db.insert(SharedCounter("rolled-back", 1))
                raise RuntimeError("test failure")

        with pytest.raises(KeyError):
            db.first(SharedCounter, "SELECT * FROM shared_counter WHERE id=?", ["rolled-back"])


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_concurrent_postgresql_startup_applies_migrations_once():
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: migrate_db(url), range(2)))

    assert results == [True, True]
    assert db_migration_status(url).name == "UP_TO_DATE"


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_postgresql_production_models_are_visible_across_instances():
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")

    from actions.server._models import Action, ActionPackage, Run, RunStatus

    first = Database(url)
    second = Database(url)
    suffix = uuid.uuid4().hex
    with first.connect():
        first.initialize([ActionPackage, Action, Run])
        with first.transaction():
            package = ActionPackage(
                f"pkg-cross-instance-{suffix}", f"cross-{suffix}", ".", "hash", "{}"
            )
            action = Action(
                f"action-cross-instance-{suffix}",
                package.id,
                "run",
                "docs",
                "actions.py",
                1,
                "{}",
                "{}",
                True,
            )
            run = Run(
                f"run-cross-instance-{suffix}",
                RunStatus.RUNNING,
                action.id,
                "2026-08-13T00:00:00",
                None,
                "{}",
                None,
                None,
                ".",
                int(suffix[:6], 16),
            )
            first.insert(package)
            first.insert(action)
            first.insert(run)

        with second.connect():
            assert second.first(ActionPackage, "SELECT * FROM action_package WHERE id=?", [package.id]) == package
            loaded_action = second.first(Action, "SELECT * FROM action WHERE id=?", [action.id])
            assert loaded_action.enabled is True
            assert second.first(Run, "SELECT * FROM run WHERE id=?", [run.id]) == run
            with second.transaction():
                second.update_by_id(Action, action.id, {"enabled": False})

        assert first.first(Action, "SELECT * FROM action WHERE id=?", [action.id]).enabled is False
        assert "action" in first.list_table_names()
        assert "enabled" in first.list_table_and_columns()["action"]
        assert any(row[0] == "action" for row in first.list_indexes())
