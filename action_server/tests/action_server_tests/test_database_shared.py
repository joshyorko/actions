import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic.dataclasses import dataclass

from actions.server._database import Database
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
