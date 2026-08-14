import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic.dataclasses import dataclass

from actions.server._database import (
    DBError,
    Database,
    normalize_database_url,
    redact_database_url,
)
from actions.server.migrations import MigrationStatus, db_migration_status, migrate_db


@dataclass
class SharedCounter:
    id: str
    value: int


def test_database_selects_postgres_for_explicit_url():
    db = Database("postgresql://localhost/actions_test")

    assert db.backend_name == "postgresql"


def test_database_selects_postgres_for_case_insensitive_url_without_exposing_it_as_path():
    value = "POSTGRESQL://SENTINEL_USER:SENTINEL_PASSWORD@localhost/actions_test"
    db = Database(value)

    assert db.backend_name == "postgresql"
    assert db.db_path == value


def test_migration_status_accepts_case_insensitive_postgresql_url(monkeypatch):
    value = "POSTGRESQL://localhost/actions_test"

    class FakeDatabase:
        backend_name = "postgresql"

        def __init__(self, db_path):
            assert db_path == value

        def connect(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def log_internal_info(self):
            pass

    monkeypatch.setattr("actions.server._database.Database", FakeDatabase)
    monkeypatch.setattr(
        "actions.server.migrations._db_migration_status",
        lambda database: MigrationStatus.UP_TO_DATE,
    )

    assert db_migration_status(value) is MigrationStatus.UP_TO_DATE


@pytest.mark.parametrize(
    "value", ["mysql://localhost/actions_test", "example://db", "postgresql://[bad"]
)
def test_database_rejects_unsupported_url_schemes(value):
    with pytest.raises(ValueError) as error:
        Database(value)

    assert "localhost" not in str(error.value)
    assert "bad" not in str(error.value)


def test_database_rejects_malformed_postgresql_url_without_exposing_credentials():
    with pytest.raises(ValueError, match="Invalid PostgreSQL database URL") as error:
        Database("postgresql://user:secret@")

    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "value",
    [
        "postgresql://SENTINEL_USER:SENTINEL_PASSWORD@db.example:abc/actions",
        "postgresql://SENTINEL_USER:SENTINEL_PASSWORD@db.example:0/actions",
        "postgresql://SENTINEL_USER:SENTINEL_PASSWORD@db.example:65536/actions",
        "postgresql://SENTINEL_USER:SENTINEL_PASSWORD@:5432/actions",
        "postgresql:/SENTINEL_USER:SENTINEL_PASSWORD@db.example/actions",
    ],
)
def test_database_rejects_invalid_postgresql_urls_before_connection(value):
    with pytest.raises(ValueError, match="Invalid PostgreSQL database URL") as error:
        Database(value)

    message = str(error.value)
    assert "SENTINEL_USER" not in message
    assert "SENTINEL_PASSWORD" not in message


@pytest.mark.parametrize(
    "value",
    [
        "postgresql://user:password@db.example:1/actions?sslmode=require",
        "postgres://user:password@db.example:5432/actions?sslmode=require",
    ],
)
def test_database_accepts_valid_postgresql_urls_without_mutating_connection_value(value):
    normalized = normalize_database_url(value)
    database = Database(value)

    assert isinstance(normalized, str)
    assert database.db_path == normalized


@pytest.mark.parametrize(
    "value",
    [
        "postgresql://SENTINEL_USER:SENTINEL_PASSWORD@db.example:55432/actions?secret=SENTINEL_QUERY",
        "postgres://SENTINEL_USER%40encoded:SENTINEL_PASSWORD%21@db.example/actions?secret=SENTINEL_QUERY",
        "POSTGRESQL://SENTINEL_USER:SENTINEL_PASSWORD@db.example/actions#SENTINEL_FRAGMENT",
    ],
)
def test_redact_database_url_removes_credentials_and_query(value):
    redacted = redact_database_url(value)

    assert "SENTINEL_USER" not in redacted
    assert "SENTINEL_PASSWORD" not in redacted
    assert "SENTINEL_QUERY" not in redacted
    assert "@" not in redacted.split("://", 1)[1].split("/", 1)[0]
    assert "?" not in redacted


def test_cli_database_url_credentials_are_redacted_from_early_and_datadir_logs(
    tmp_path: Path,
):
    database_url = (
        "postgresql://SENTINEL_USER%40encoded:SENTINEL_PASSWORD%21@"
        "127.0.0.1:1/actions?secret=SENTINEL_QUERY"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "actions.server",
            "migrate",
            "--datadir",
            str(tmp_path),
            "--database-url",
            database_url,
            "-v",
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode != 0
    log_contents = (tmp_path / "server_log.txt").read_text()
    for output in (result.stdout, result.stderr, log_contents):
        assert "SENTINEL_USER" not in output
        assert "SENTINEL_PASSWORD" not in output
        assert "SENTINEL_QUERY" not in output


def test_cli_argument_error_does_not_echo_database_url_credentials():
    database_url = (
        "postgres://SENTINEL_USER:SENTINEL_PASSWORD@127.0.0.1:1/actions"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "actions.server",
            "server-expose",
            "--database-url",
            database_url,
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode != 0
    assert "SENTINEL_USER" not in result.stderr
    assert "SENTINEL_PASSWORD" not in result.stderr


def test_legacy_migration_error_does_not_echo_database_url_credentials():
    from actions.server.migrations.migration_initial import migrate

    database = Database(
        "postgresql://SENTINEL_USER:SENTINEL_PASSWORD@db.example/actions"
    )
    with pytest.raises(RuntimeError) as error:
        migrate(database)

    assert "SENTINEL_USER" not in str(error.value)
    assert "SENTINEL_PASSWORD" not in str(error.value)


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


def test_postgresql_placeholder_adapter_preserves_json_operators_and_array_rhs():
    db = Database("postgresql://localhost/actions_test")

    assert db._adapt_sql("payload ? ? AND payload ?| ? AND payload ?& ?", [1, 2, 3]) == (
        "payload ? %s AND payload ?| %s AND payload ?& %s"
    )
    assert db._adapt_sql("? = ANY(?)", ["key", ["key", "other"]]) == "%s = ANY(%s)"


def test_postgresql_placeholder_adapter_handles_lexical_json_operator_contexts():
    db = Database("postgresql://localhost/actions_test")
    sql = (
        "payload /* before */ ? /* after */ (('key')) AND "
        "payload ?::text AND payload ? 'key' AND "
        "payload ?| ARRAY[?] AND payload ?& (?::text) AND "
        "? = ANY(?) AND '\\?' = ? AND \"?\" = ? AND $$ ? $$ = ?"
    )

    assert db._adapt_sql(sql, list(range(8))) == (
        "payload /* before */ ? /* after */ (('key')) AND "
        "payload %s::text AND payload ? 'key' AND "
        "payload ?| ARRAY[%s] AND payload ?& (%s::text) AND "
        "%s = ANY(%s) AND '\\?' = %s AND \"?\" = %s AND $$ ? $$ = %s"
    )


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_postgresql_bound_json_operators_and_array_rhs_execute():
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")

    db = Database(url)
    with db.connect():
        with db.transaction():
            db.execute("CREATE TEMP TABLE json_operator_probe (payload JSONB)")
            db.execute(
                "INSERT INTO json_operator_probe VALUES (?::jsonb)",
                ['{"key": "value"}'],
            )
            with db.cursor() as cursor:
                db.execute_query(
                    cursor,
                    "SELECT payload ? ? FROM json_operator_probe",
                    ["key"],
                )
                assert cursor.fetchone()[0]
                db.execute_query(cursor, "SELECT ? = ANY(?)", ["key", ["other", "key"]])
                assert cursor.fetchone()[0]


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
