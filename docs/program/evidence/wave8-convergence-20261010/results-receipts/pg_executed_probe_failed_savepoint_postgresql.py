from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

repo = Path("/workspace/work/actions-mk3-wave8-postgres").resolve()
expected_module = repo / "action_server/src/actions/server/_database.py"
module_source = expected_module.read_bytes()
module_sha256 = hashlib.sha256(module_source).hexdigest()
url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
if not url:
    raise SystemExit("ACTIONS_TEST_DATABASE_URL is required")
parsed = urlsplit(url)
if parsed.scheme not in {"postgres", "postgresql"}:
    raise SystemExit("the test requires an explicit PostgreSQL URL")
if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit("the test accepts loopback PostgreSQL only")

sys.path[:0] = [str(repo / "actions/src"), str(repo / "action_server/src")]
import psycopg
from actions.server._database import DBError, Database
import actions.server._database as database_module

if Path(database_module.__file__).resolve() != expected_module:
    raise SystemExit("Database module did not resolve to the bound source checkout")
if module_sha256 != "c48ff5838d333ebd2c483be30036d9e3b8588d29c8d6dbbe324e247b9168bdd4":
    raise SystemExit("bound Database source hash differs from reviewed start")

def cause_with_sqlstate(exc: BaseException) -> BaseException | None:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if getattr(current, "sqlstate", None):
            return current
        current = current.__cause__ or current.__context__
    return None


def status(connection) -> str:
    return connection.info.transaction_status.name


database = Database(url)
if database.backend_name != "postgresql":
    raise SystemExit("Database selected a non-PostgreSQL backend")
result: dict[str, object] = {
    "source_module": str(Path(database_module.__file__).resolve()),
    "source_module_sha256": module_sha256,
    "python_pid": os.getpid(),
    "python_executable": sys.executable,
    "python_version": sys.version.split()[0],
    "psycopg_version": psycopg.__version__,
    "backend": database.backend_name,
}

with database.connect():
    connection = database._tlocal.conn
    if connection is None:
        raise AssertionError("production Database connection is missing")
    server_version = connection.execute("SHOW server_version").fetchone()[0]
    result["postgres_server_version"] = server_version
    if not str(server_version).startswith("17.11"):
        raise AssertionError("unexpected PostgreSQL server version")

    # A fresh task-owned container/database makes this table name exclusive.
    with database.transaction():
        database.execute(
            "CREATE TABLE savepoint_failure_probe (value TEXT PRIMARY KEY);"
        )
    result["state_after_setup"] = status(connection)

    first_statement_error: BaseException | None = None
    nested_error: BaseException | None = None
    nested_body_entered = False
    outer_error: BaseException | None = None
    status_after_abort = None
    nesting_before_nested = None
    try:
        with database.transaction():
            nesting_before_nested = database._tlocal.in_transaction
            try:
                database.execute("SELECT 1 / 0;")
            except DBError as exc:
                first_statement_error = exc
            else:
                raise AssertionError("division-by-zero statement unexpectedly succeeded")
            status_after_abort = status(connection)
            if status_after_abort != "INERROR":
                raise AssertionError("failed SQL did not leave PostgreSQL transaction INERROR")
            if database._tlocal.in_transaction != 1:
                raise AssertionError("outer transaction nesting count was not one")
            with database.transaction():
                nested_body_entered = True
    except BaseException as exc:
        outer_error = exc
        nested_error = exc

    first_cause = cause_with_sqlstate(first_statement_error) if first_statement_error else None
    nested_cause = cause_with_sqlstate(nested_error) if nested_error else None
    nesting_after_failure = database._tlocal.in_transaction
    cleanup_status = status(connection)
    connection_in_transaction = connection.info.transaction_status.name != "IDLE"
    result.update(
        {
            "outer_nesting_before_nested": nesting_before_nested,
            "first_sqlstate": getattr(first_cause, "sqlstate", None),
            "transaction_state_before_savepoint": status_after_abort,
            "savepoint_body_entered": nested_body_entered,
            "savepoint_failure_type": type(nested_error).__name__ if nested_error else None,
            "savepoint_failure_sqlstate": getattr(nested_cause, "sqlstate", None),
            "savepoint_failure_text": str(nested_error) if nested_error else None,
            "savepoint_command_observed_in_error": bool(
                nested_error and "savepoint savepoint_0;" in str(nested_error)
            ),
            "outer_exception_type": type(outer_error).__name__ if outer_error else None,
            "nesting_after_failed_outer_cleanup": nesting_after_failure,
            "connection_status_after_failed_outer_cleanup": cleanup_status,
            "connection_in_transaction_after_failed_outer_cleanup": connection_in_transaction,
        }
    )
    if not isinstance(first_statement_error, DBError):
        raise AssertionError("the first production Database SQL failure was not DBError")
    if not isinstance(nested_error, DBError):
        raise AssertionError("failed SAVEPOINT did not propagate the production DBError")
    if getattr(first_cause, "sqlstate", None) != "22012":
        raise AssertionError("the intended PostgreSQL division-by-zero failure was not observed")
    if getattr(nested_cause, "sqlstate", None) != "25P02":
        raise AssertionError("the nested SAVEPOINT did not fail in PostgreSQL's aborted transaction")
    if nested_body_entered:
        raise AssertionError("nested transaction body ran after SAVEPOINT failure")
    if str(nested_error) != "Error running sql: 'savepoint savepoint_0;' with values: None":
        raise AssertionError("production Database did not report the expected SAVEPOINT command")
    if nesting_after_failure != 0 or cleanup_status != "IDLE" or connection_in_transaction:
        raise AssertionError("outer cleanup did not restore nesting and PostgreSQL connection state")

    # Reuse the same connection: a later outer commit, nested rollback, and
    # another nested commit must all work after the failed SAVEPOINT cleanup.
    class ExpectedNestedRollback(Exception):
        pass

    with database.transaction():
        database.execute(
            "INSERT INTO savepoint_failure_probe (value) VALUES (?);", ["outer-kept"]
        )
        try:
            with database.transaction():
                database.execute(
                    "INSERT INTO savepoint_failure_probe (value) VALUES (?);",
                    ["inner-rolled-back"],
                )
                raise ExpectedNestedRollback()
        except ExpectedNestedRollback:
            pass
        with database.transaction():
            database.execute(
                "INSERT INTO savepoint_failure_probe (value) VALUES (?);",
                ["inner-committed"],
            )

    recovered_rows = connection.execute(
        "SELECT value FROM savepoint_failure_probe ORDER BY value;"
    ).fetchall()
    recovered_rows_text = [row[0] for row in recovered_rows]
    result["same_connection_recovery_rows"] = recovered_rows_text
    result["nesting_after_recovery"] = database._tlocal.in_transaction
    result["connection_status_after_recovery"] = status(connection)
    result["same_connection_recovery_passed"] = recovered_rows_text == [
        "inner-committed",
        "outer-kept",
    ]
    if recovered_rows_text != ["inner-committed", "outer-kept"]:
        raise AssertionError("same connection did not commit/rollback nested transactions correctly")
    if database._tlocal.in_transaction != 0 or status(connection) != "IDLE":
        raise AssertionError("recovery transaction did not return to idle state")

result["status"] = "PASS"
receipt = Path(os.environ["ACTIONS_SAVEPOINT_RECEIPT"])
tmp = receipt.with_suffix(receipt.suffix + ".tmp")
tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(tmp, 0o600)
tmp.replace(receipt)
print(json.dumps({"status": result["status"], "receipt": str(receipt)}))
