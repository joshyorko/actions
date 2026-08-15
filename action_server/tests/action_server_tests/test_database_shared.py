import hashlib
import json
import os
import subprocess
import sys
import textwrap
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from pydantic.dataclasses import dataclass

from actions.server._database import (
    DBError,
    Database,
    normalize_database_url,
    redact_database_url,
)
from actions.server.migrations import (
    CURRENT_VERSION,
    MIGRATION_ID_TO_NAME,
    MigrationStatus,
    db_migration_status,
    migrate_db,
)


HISTORICAL_MIGRATION_SHA256 = {
    1: "d5efbc8d68b73fa73cecaa669d5c68741f90ec57c20aabbca4b1c406696011a0",
    2: "96e6449f06e9393de851142d2bfc4c5cb7e52433d30981811eb91a95fcd75f12",
    3: "4f00c4896f6ac858135871b2c2f4d7c514b0bbadcc6c7c5d35896ab709d1683b",
    4: "d175f9320afbd22e1ef2818eba8b09685b829f4578e97f7482be85ed72b7b298",
    5: "695fec4aa4dc15e16d6947da52b34773a1c313bd6de89ff3f6b17a7673a48f2c",
    6: "2b16365078de37ca3dddde01dccc07d97e539725b4cff09196fedca38960ca84",
    7: "e983e4777b73ed0dcb64ac274229711ec96ab9dd7e9258de03c4f9f5f581b532",
    8: "6b46cc310473eb2feb6269bf4fa3d80d2550f20a24d7a410f66d7e2ebe68c2df",
    9: "df8e518b5c49d12cec47d4ecdd122227ae1034e1234ef14aa23fce065ae3bdf4",
    10: "864b9dfea5365e3dc873e83c8b935eae59aa74de6dab0b05ed8e1473e21e3515",
}


@dataclass
class SharedCounter:
    id: str
    value: int


def test_historical_migration_contents_are_immutable():
    migrations_dir = Path(__file__).parents[2] / "src/actions/server/migrations"

    for migration_id, expected_sha256 in HISTORICAL_MIGRATION_SHA256.items():
        migration_name = MIGRATION_ID_TO_NAME[migration_id]
        content = (migrations_dir / f"migration_{migration_name}.py").read_bytes()

        assert hashlib.sha256(content).hexdigest() == expected_sha256


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


def test_historical_migration_nine_retains_run_output_columns(tmp_path: Path):
    from actions.server.migrations import Migration
    from actions.server.migrations.migration_add_robot_run_columns import migrate

    db = Database(tmp_path / "migration-nine.db")
    with db.connect():
        db.initialize([Migration])
        with db.transaction():
            db.execute(
                """
                CREATE TABLE migration (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE run (
                    id TEXT NOT NULL PRIMARY KEY,
                    status INTEGER NOT NULL,
                    action_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    run_time REAL,
                    inputs TEXT NOT NULL,
                    result TEXT,
                    error_message TEXT,
                    relative_artifacts_dir TEXT NOT NULL,
                    numbered_id INTEGER NOT NULL,
                    request_id TEXT NOT NULL DEFAULT ''
                )
                """
            )
            db.insert(Migration(8, "add_request_id_to_run"))
            migrate(db)

        with db.cursor() as cursor:
            db.execute_query(cursor, "PRAGMA table_info(run)")
            columns = [row[1] for row in cursor.fetchall()]

        assert columns[-6:] == [
            "run_type",
            "robot_package_path",
            "robot_task_name",
            "robot_env_hash",
            "stdout",
            "stderr",
        ]

def test_forward_schema_repair_removes_accidental_run_output_columns(tmp_path: Path):
    from actions.server.migrations import Migration
    from actions.server.migrations.migration_reconcile_run_columns import migrate

    db = Database(tmp_path / "migration-repair.db")
    with db.connect():
        db.initialize([Migration])
        with db.transaction():
            db.execute(
                "CREATE TABLE migration (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE run (id TEXT PRIMARY KEY, result TEXT, "
                "stdout TEXT, stderr TEXT)"
            )
            db.execute(
                "INSERT INTO run (id, result, stdout, stderr) VALUES (?, ?, ?, ?)",
                ["empty-run", None, None, None],
            )
            migrate(db)

        with db.cursor() as cursor:
            db.execute_query(cursor, "PRAGMA table_info(run)")
            columns = [row[1] for row in cursor.fetchall()]
            db.execute_query(
                cursor,
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                ["run_legacy_output_archive"],
            )
            archive = cursor.fetchone()

    assert columns == ["id", "result"]
    assert archive is None


def test_forward_schema_repair_without_run_output_columns_has_no_archive(
    tmp_path: Path,
):
    from actions.server.migrations import Migration
    from actions.server.migrations.migration_reconcile_run_columns import migrate

    db = Database(tmp_path / "migration-repair-fresh.db")
    with db.connect():
        db.initialize([Migration])
        with db.transaction():
            db.execute(
                "CREATE TABLE migration (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
            migrate(db)

        assert "run_legacy_output_archive" not in db.list_table_names()


def test_forward_schema_repair_archives_populated_outputs_without_overwrite(
    tmp_path: Path,
):
    from actions.server.migrations import Migration
    from actions.server.migrations.migration_reconcile_run_columns import migrate

    db = Database(tmp_path / "migration-repair-populated.db")
    with db.connect():
        db.initialize([Migration])
        with db.transaction():
            db.execute("CREATE TABLE migration (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
            db.execute(
                "CREATE TABLE run (id TEXT PRIMARY KEY, result TEXT, "
                "stdout TEXT, stderr TEXT)"
            )
            db.execute(
                "CREATE TABLE run_legacy_output_archive ("
                "run_id TEXT PRIMARY KEY, stdout TEXT, stderr TEXT)"
            )
            db.execute(
                "INSERT INTO run_legacy_output_archive VALUES (?, ?, ?)",
                ["run-1", "existing stdout", "existing stderr"],
            )
            for values in (
                ["run-1", "result-1", "new stdout", "new stderr"],
                ["run-2", "result-2", "only stdout", None],
                ["run-3", "result-3", None, "only stderr"],
                ["run-4", "result-4", None, None],
            ):
                db.execute(
                    "INSERT INTO run (id, result, stdout, stderr) VALUES (?, ?, ?, ?)",
                    values,
                )

            migrate(db)
            migrate(db)

        with db.cursor() as cursor:
            db.execute_query(cursor, "PRAGMA table_info(run)")
            run_columns = [row[1] for row in cursor.fetchall()]
            db.execute_query(
                cursor,
                "SELECT run_id, stdout, stderr FROM run_legacy_output_archive "
                "ORDER BY run_id",
            )
            archived = cursor.fetchall()

    assert run_columns == ["id", "result"]
    assert archived == [
        ("run-1", "existing stdout", "existing stderr"),
        ("run-2", "only stdout", None),
        ("run-3", None, "only stderr"),
    ]


def test_forward_schema_repair_is_registered_after_historical_migration_nine():
    assert CURRENT_VERSION == 12
    assert MIGRATION_ID_TO_NAME[9] == "add_robot_run_columns"
    assert MIGRATION_ID_TO_NAME[12] == "reconcile_run_columns"


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


def test_postgresql_ddl_adapter_is_lexical_and_ddl_scoped():
    db = Database("postgresql://localhost/actions_test")

    sql = (
        "SELECT 'enabled INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1', "
        '"enabled INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1", '
        "/* external INTEGER CHECK(external IN (0, 1)) NOT NULL */ "
        "-- is_consequential INTEGER\n"
        "$$enabled INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1$$; "
        "CREATE TABLE legacy_flags ("
        "enabled INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1, "
        "external INTEGER CHECK(external IN (0, 1)) NOT NULL"
        ");"
    )

    assert db._adapt_sql(sql) == (
        "SELECT 'enabled INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1', "
        '"enabled INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1", '
        "/* external INTEGER CHECK(external IN (0, 1)) NOT NULL */ "
        "-- is_consequential INTEGER\n"
        "$$enabled INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1$$; "
        "CREATE TABLE legacy_flags ("
        "enabled BOOLEAN NOT NULL DEFAULT TRUE, "
        "external BOOLEAN NOT NULL"
        ");"
    )


def test_postgresql_ddl_adapter_is_idempotent_and_marker_count_safe():
    db = Database("postgresql://localhost/actions_test")
    ddl = (
        "CREATE TABLE legacy_flags ("
        "enabled INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1)"
    )
    sql = ddl + "; SELECT payload ? ? AND payload ?| ? AND payload ?& ?"

    adapted = db._adapt_sql(sql, [1, 2, 3])

    assert adapted == (
        "CREATE TABLE legacy_flags (enabled BOOLEAN NOT NULL DEFAULT TRUE); "
        "SELECT payload ? %s AND payload ?| %s AND payload ?& %s"
    )
    assert db._adapt_sql(db._adapt_sql(ddl)) == db._adapt_sql(ddl)


def test_postgresql_sql_adapter_translates_legacy_boolean_ddl():
    db = Database("postgresql://localhost/actions_test")

    assert db._adapt_sql(
        "ALTER TABLE action ADD COLUMN enabled "
        "INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1;"
    ) == "ALTER TABLE action ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT TRUE;"
    assert db._adapt_sql(
        "ALTER TABLE action ADD COLUMN is_consequential INTEGER;"
    ) == "ALTER TABLE action ADD COLUMN is_consequential BOOLEAN;"
    assert db._adapt_sql(
        "CREATE TABLE user_session (external INTEGER CHECK(external IN (0, 1)) NOT NULL)"
    ) == "CREATE TABLE user_session (external BOOLEAN NOT NULL)"
    assert db._adapt_sql(
        "CREATE TABLE schedule (enabled INTEGER CHECK(enabled IN (0, 1)) NOT NULL DEFAULT 1, "
        "retry_enabled INTEGER CHECK(retry_enabled IN (0, 1)) NOT NULL DEFAULT 0)"
    ) == (
        "CREATE TABLE schedule (enabled BOOLEAN NOT NULL DEFAULT TRUE, "
        "retry_enabled BOOLEAN NOT NULL DEFAULT FALSE)"
    )


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


def _postgresql_schema_url(url: str, schema: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["options"] = f"-csearch_path={schema}"
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def _create_postgresql_legacy_run_schema(url: str) -> tuple[Database, str, str]:
    schema = f"actions_run_output_{uuid.uuid4().hex}"
    database = Database(url)
    with database.connect():
        with database.transaction():
            database.execute(f"CREATE SCHEMA {schema}")
            database.execute(
                f"CREATE TABLE {schema}.migration ("
                "id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
            database.execute(
                f"CREATE TABLE {schema}.run ("
                "id TEXT PRIMARY KEY, result TEXT, stdout TEXT, stderr TEXT)"
            )
            database.execute(
                f"INSERT INTO {schema}.migration VALUES (?, ?)",
                [11, "reconcile_schema"],
            )
            for values in (
                ["run-1", "result-1", "postgres stdout", "postgres stderr"],
                ["run-2", "result-2", "only postgres stdout", None],
                ["run-3", "result-3", None, "only postgres stderr"],
                ["run-4", "result-4", None, None],
            ):
                database.execute(
                    f"INSERT INTO {schema}.run "
                    "(id, result, stdout, stderr) VALUES (?, ?, ?, ?)",
                    values,
                )
    return database, schema, _postgresql_schema_url(url, schema)


def _drop_postgresql_schema(database: Database, schema: str) -> None:
    with database.connect():
        with database.transaction():
            database.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_postgresql_run_output_archive_preserves_values_and_reruns():
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")

    from actions.server.migrations.migration_reconcile_run_columns import migrate

    owner, schema, schema_url = _create_postgresql_legacy_run_schema(url)
    database = Database(schema_url)
    try:
        with database.connect():
            with database.transaction():
                migrate(database)
            with database.transaction():
                migrate(database)

            columns = database.list_table_and_columns()
            with database.cursor() as cursor:
                database.execute_query(
                    cursor,
                    "SELECT run_id, stdout, stderr FROM run_legacy_output_archive "
                    "ORDER BY run_id",
                )
                archived = cursor.fetchall()

        assert columns["run"] == ["id", "result"]
        assert columns["run_legacy_output_archive"] == [
            "run_id",
            "stdout",
            "stderr",
        ]
        assert archived == [
            ("run-1", "postgres stdout", "postgres stderr"),
            ("run-2", "only postgres stdout", None),
            ("run-3", None, "only postgres stderr"),
        ]
    finally:
        _drop_postgresql_schema(owner, schema)


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_concurrent_postgresql_startup_archives_legacy_run_outputs_once():
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")

    owner, schema, schema_url = _create_postgresql_legacy_run_schema(url)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: migrate_db(schema_url), range(2)))

        database = Database(schema_url)
        with database.connect():
            columns = database.list_table_and_columns()
            with database.cursor() as cursor:
                database.execute_query(
                    cursor,
                    "SELECT run_id, stdout, stderr FROM run_legacy_output_archive "
                    "ORDER BY run_id",
                )
                archived = cursor.fetchall()
                database.execute_query(
                    cursor,
                    "SELECT COUNT(*) FROM migration WHERE id=?",
                    [12],
                )
                migration_count = cursor.fetchone()[0]

        assert results == [True, True]
        assert columns["run"] == ["id", "result"]
        assert archived == [
            ("run-1", "postgres stdout", "postgres stderr"),
            ("run-2", "only postgres stdout", None),
            ("run-3", None, "only postgres stderr"),
        ]
        assert migration_count == 1
    finally:
        _drop_postgresql_schema(owner, schema)


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_postgresql_schema_introspection_uses_effective_search_path():
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")

    schema = f"actions_schema_{uuid.uuid4().hex}"
    database = Database(url)
    try:
        with database.connect():
            with database.transaction():
                database.execute(f"CREATE SCHEMA {schema}")
                database.execute(
                    f"CREATE TABLE {schema}.introspection_probe "
                    "(id TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                database.execute(
                    f"CREATE INDEX introspection_probe_value_idx "
                    f"ON {schema}.introspection_probe(value)"
                )

        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["options"] = f"-csearch_path={schema}"
        schema_url = urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query),
                parts.fragment,
            )
        )
        schema_database = Database(schema_url)
        with schema_database.connect():
            assert schema_database.list_table_names() == ["introspection_probe"]
            assert schema_database.list_table_and_columns() == {
                "introspection_probe": ["id", "value"]
            }
            assert any(
                row[0] == "introspection_probe"
                for row in schema_database.list_indexes()
            )
    finally:
        with database.connect():
            with database.transaction():
                database.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def _runtime_schedule_worker_code() -> str:
    return textwrap.dedent(
        """
        import asyncio
        import sys
        import time
        from pathlib import Path

        import actions.server._settings as settings_module
        from actions.server._actions_process_pool import (
            get_actions_process_pool,
            setup_actions_process_pool,
        )
        from actions.server._models import Action, ActionPackage, load_db
        from actions.server._scheduler import SchedulerEngine
        from actions.server._settings import Settings

        url, datadir_value, ready_value, go_value = sys.argv[1:]
        datadir = Path(datadir_value)
        datadir.mkdir(parents=True, exist_ok=True)
        settings = Settings(
            datadir=datadir,
            artifacts_dir=datadir / "artifacts",
            database_url=url,
            min_processes=0,
            max_processes=1,
            reuse_processes=False,
        )
        settings_module._global_settings = settings

        with load_db(url) as database:
            with database.connect():
                packages = {
                    package.id: package for package in database.all(ActionPackage)
                }
                actions = database.all(Action)

            with setup_actions_process_pool(settings, packages, actions):
                Path(ready_value).touch()
                deadline = time.monotonic() + 30
                while not Path(go_value).exists():
                    if time.monotonic() >= deadline:
                        raise TimeoutError("runtime worker start barrier timed out")
                    time.sleep(0.01)

                try:
                    scheduler = SchedulerEngine(
                        check_interval=0.01,
                        max_concurrent_global=1,
                    )
                    asyncio.run(scheduler._check_and_execute_schedules())
                finally:
                    get_actions_process_pool().dispose()

        print("runtime worker complete", flush=True)
        """
    )


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_two_runtime_processes_claim_one_due_schedule(tmp_path: Path):
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")

    from actions.server._models import Action, ActionPackage, Schedule

    migrate_db(url)
    suffix = uuid.uuid4().hex
    package_id = f"package-schedule-{suffix}"
    action_id = f"action-schedule-{suffix}"
    schedule_id = f"schedule-{suffix}"
    request_id = f"schedule:{schedule_id}"
    now = datetime.now(timezone.utc)
    now_string = now.isoformat()
    scheduled_time = (now - timedelta(seconds=1)).isoformat()
    package_directory = Path(__file__).parent / "resources" / "no_conda" / "slow"
    package = ActionPackage(
        id=package_id,
        name=f"schedule-package-{suffix}",
        directory=str(package_directory),
        conda_hash="test",
        env_json="{}",
    )
    action = Action(
        id=action_id,
        action_package_id=package_id,
        name="long_running",
        docs="A scheduled test action.",
        file="action_slow.py",
        lineno=4,
        input_schema='{"type":"object","properties":{"duration":{"type":"number"}}}',
        output_schema='{"type":"string"}',
    )
    schedule = Schedule(
        id=schedule_id,
        name=f"schedule-{suffix}",
        description="",
        action_id=action_id,
        execution_mode="run",
        work_item_queue=None,
        inputs_json=json.dumps({"duration": 2.0}),
        schedule_type="once",
        cron_expression=None,
        interval_seconds=None,
        weekday_config_json=None,
        once_at=scheduled_time,
        timezone="UTC",
        enabled=True,
        created_at=now_string,
        updated_at=now_string,
        next_run_at=scheduled_time,
    )
    database = Database(url)
    processes = []
    process_outputs = {}
    try:
        with database.connect():
            database.initialize([ActionPackage, Action, Schedule])
            with database.transaction():
                database.insert(package)
                database.insert(action)
                database.insert(schedule)

        worker_code = _runtime_schedule_worker_code()
        ready_paths = [tmp_path / "runtime-a.ready", tmp_path / "runtime-b.ready"]
        go_path = tmp_path / "runtime.go"
        datadirs = [tmp_path / "runtime-a", tmp_path / "runtime-b"]
        for datadir, ready_path in zip(datadirs, ready_paths):
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        worker_code,
                        url,
                        str(datadir),
                        str(ready_path),
                        str(go_path),
                    ],
                    cwd=Path(__file__).parents[2],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )

        deadline = time.monotonic() + 30
        while not all(path.exists() for path in ready_paths):
            if any(process.poll() is not None for process in processes):
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("runtime worker readiness barrier timed out")
            time.sleep(0.02)
        process_statuses = [worker_process.poll() for worker_process in processes]
        assert all(path.exists() for path in ready_paths), process_statuses
        go_path.touch()

        for index, process in enumerate(processes):
            process_outputs[index] = process.communicate(timeout=45)
        for index, (stdout, stderr) in process_outputs.items():
            (tmp_path / f"runtime-{index}.stdout.log").write_text(stdout)
            (tmp_path / f"runtime-{index}.stderr.log").write_text(stderr)
        assert all(process.returncode == 0 for process in processes), process_outputs

        with database.connect():
            with database.cursor() as cursor:
                database.execute_query(
                    cursor,
                    "SELECT COUNT(*) FROM schedule_execution WHERE schedule_id=?",
                    [schedule_id],
                )
                execution_count = cursor.fetchone()[0]
                database.execute_query(
                    cursor,
                    "SELECT COUNT(*) FROM run WHERE request_id=?",
                    [request_id],
                )
                run_count = cursor.fetchone()[0]
                database.execute_query(
                    cursor,
                    "SELECT status FROM schedule_execution WHERE schedule_id=?",
                    [schedule_id],
                )
                execution_statuses = [row[0] for row in cursor.fetchall()]
                database.execute_query(
                    cursor,
                    "SELECT enabled, next_run_at FROM schedule WHERE id=?",
                    [schedule_id],
                )
                schedule_state = cursor.fetchone()

        assert execution_count == 1
        assert run_count == 1
        assert len(execution_statuses) == 1
        assert execution_statuses[0] in {"completed", "failed"}
        assert schedule_state == (False, None)
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        for index, process in enumerate(processes):
            if index not in process_outputs:
                process_outputs[index] = process.communicate()
            stdout, stderr = process_outputs[index]
            (tmp_path / f"runtime-{index}.stdout.log").write_text(stdout)
            (tmp_path / f"runtime-{index}.stderr.log").write_text(stderr)
        with database.connect():
            with database.transaction():
                database.execute(
                    "DELETE FROM schedule_execution WHERE schedule_id=?",
                    [schedule_id],
                )
                database.execute("DELETE FROM run WHERE request_id=?", [request_id])
                database.execute("DELETE FROM schedule WHERE id=?", [schedule_id])
                database.execute("DELETE FROM action WHERE id=?", [action_id])
                database.execute(
                    "DELETE FROM action_package WHERE id=?", [package_id]
                )
            with database.cursor() as cursor:
                database.execute_query(
                    cursor,
                    "SELECT COUNT(*) FROM schedule WHERE id=?",
                    [schedule_id],
                )
                assert cursor.fetchone()[0] == 0
                database.execute_query(
                    cursor,
                    "SELECT COUNT(*) FROM schedule_execution WHERE schedule_id=?",
                    [schedule_id],
                )
                assert cursor.fetchone()[0] == 0


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
