"""Standalone current-source PostgreSQL migration-lock gate proposal.

Run from the prepared canonical RCC interpreter against a fresh,
root-owned PostgreSQL test service. Never aim this at a user or shared DB.
The URL is read from ACTIONS_TEST_DATABASE_URL and is never printed or passed
on a process command line.
"""
from __future__ import annotations

import json
import hashlib
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
import resource
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

WORKER = r"""
import hashlib, importlib, json, os, sys
from pathlib import Path
from actions.server.migrations import db_migration_status, migrate_db
url = os.environ['ACTIONS_TEST_DATABASE_URL']
ok = migrate_db(url)
status = db_migration_status(url).name
modules = [
    importlib.import_module('actions.server._database'),
    importlib.import_module('actions.server.migrations'),
    importlib.import_module('actions.server.migrations.migration_add_mcp_catalog_names'),
]
module_identity = {}
for module in modules:
    path = Path(module.__file__).resolve()
    module_identity[module.__name__] = {
        'path': str(path),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
print('RESULT_JSON=' + json.dumps({
    'pid': os.getpid(), 'migrate_ok': ok, 'status': status,
    'executable': sys.executable, 'version': sys.version,
    'module_identity': module_identity,
}), flush=True)
raise SystemExit(0 if ok and status == 'UP_TO_DATE' else 1)
"""

EXPECTED_HEAD = "4e8a26296608c232ce3dbd1f250ddb709b9459c9"
EXPECTED_TREE = "1b582dd02b367e5216e60796a8da031e520aa12f"
EXPECTED_REPO = Path("/workspace/work/actions-mk3-database-gates")


def with_application_name(url: str, application_name: str) -> str:
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if key.lower() not in {"application_name", "connect_timeout", "options"}]
    query.extend([
        ("application_name", application_name),
        ("connect_timeout", "10"),
        ("options", "-c statement_timeout=120000 -c lock_timeout=90000"),
    ])
    result = urlunsplit((parts.scheme, parts.netloc, parts.path,
                         urlencode(query, quote_via=quote), parts.fragment))
    expected_options = "-c statement_timeout=120000 -c lock_timeout=90000"
    parsed_options = dict(parse_qsl(urlsplit(result).query, keep_blank_values=True)).get("options")
    if parsed_options != expected_options:
        raise ValueError("Database URI does not preserve PostgreSQL timeout options")
    # Validate the value with libpq's own DSN parser before opening a socket.
    from psycopg.conninfo import conninfo_to_dict
    if conninfo_to_dict(result).get("options") != expected_options:
        raise ValueError("libpq did not preserve PostgreSQL timeout options")
    return result


def source_identity() -> dict[str, str]:
    cwd = os.getcwd()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=cwd, check=True,
        capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout
    if head != EXPECTED_HEAD or tree != EXPECTED_TREE or Path(top) != EXPECTED_REPO:
        raise SystemExit(f"Unexpected source identity: {top} {head} {tree}")
    if status:
        raise SystemExit("Source worktree is dirty; refusing migration gate")
    return {"head": head, "tree": tree, "dirty": False}


def module_identity() -> dict[str, dict[str, str]]:
    import importlib

    result = {}
    for name in (
        "actions.server._database",
        "actions.server.migrations",
        "actions.server.migrations.migration_add_mcp_catalog_names",
    ):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        if EXPECTED_REPO / "action_server" / "src" not in path.parents:
            raise SystemExit(f"Module imported outside exact source tree: {name} at {path}")
        result[name] = {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    return result


def _limit_child_output() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))


def _terminate_runner(_signum, _frame) -> None:
    raise SystemExit("Runner interrupted; child cleanup is being performed")


def main() -> int:
    from actions.server._database import Database
    from actions.server.migrations import (
        CURRENT_VERSION,
        MIGRATION_ID_TO_NAME,
        Migration,
        MigrationStatus,
        db_migration_status,
        migrate_db,
    )

    source = source_identity()
    expected_modules = module_identity()

    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        raise SystemExit("ACTIONS_TEST_DATABASE_URL is required; no URL was printed")
    if CURRENT_VERSION != 13 or MIGRATION_ID_TO_NAME.get(13) != "add_mcp_catalog_names":
        raise SystemExit("This gate is pinned to source migration 13; re-review before adapting")

    evidence_dir_value = os.environ.get("ACTIONS84_EVIDENCE_DIR")
    if not evidence_dir_value:
        raise SystemExit("ACTIONS84_EVIDENCE_DIR is required for retained bounded logs")
    evidence_dir = Path(evidence_dir_value)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, _terminate_runner)
    fixture_url = with_application_name(url, "actions84_fixture")
    probe = Database(fixture_url)
    if probe.backend_name != "postgresql":
        raise SystemExit("A PostgreSQL URL is required")
    with probe.connect():
        tables = probe.list_table_names()
    if tables:
        raise SystemExit("The test database must be empty; refusing to mutate existing tables")

    # Build an exact v12 starting point via the production migrator, then undo
    # only migration 13's table/record inside a Database transaction. This
    # exercises a real pending migration instead of empty-database bootstrap.
    if not migrate_db(fixture_url):
        raise SystemExit("Production bootstrap did not complete")
    v13_schema = schema_signature(probe)
    v13_counts = table_counts(probe)
    v13_counters = counter_snapshot(probe)
    with probe.connect():
        with probe.cursor() as cursor:
            probe.execute_query(cursor, "SELECT id, name FROM migration ORDER BY id", [])
            bootstrap_history = cursor.fetchall()
    if bootstrap_history != [(13, "add_mcp_catalog_names")]:
        raise RuntimeError("Fresh production bootstrap did not seed only CURRENT_VERSION")
    with probe.connect():
        with probe.transaction():
            probe.execute("DROP TABLE mcp_catalog_name")
            probe.execute("DELETE FROM migration WHERE id=?", [13])
            probe.insert(Migration(id=12, name=MIGRATION_ID_TO_NAME[12]))
    with probe.connect():
        with probe.cursor() as cursor:
            probe.execute_query(cursor, "SELECT id, name FROM migration ORDER BY id", [])
            pending_history = cursor.fetchall()
    if pending_history != [(12, "reconcile_run_columns")]:
        raise RuntimeError("Fixture did not retain exactly the expected v12 history")
    if db_migration_status(fixture_url) is not MigrationStatus.NEEDS_MIGRATION:
        raise SystemExit("Fixture did not reach the expected v12 migration state")

    app_name = "actions84_" + uuid.uuid4().hex[:12]
    worker_app_names = [f"{app_name}_{index}" for index in range(2)]
    observer = Database(with_application_name(url, app_name + "_observer"))
    lock_owner = Database(with_application_name(url, app_name + "_controller"))
    processes: list[subprocess.Popen[str]] = []
    outputs: dict[int, tuple[str, str]] = {}
    raw_output_paths: dict[int, tuple[Path, Path]] = {}
    deadline_seconds = 60
    wait_deadline = time.monotonic() + deadline_seconds
    waiting_backends: dict[str, int] = {}
    wait_observations: dict[str, dict[str, object]] = {}

    try:
        # Probe the exact pg_stat_activity prefix predicate before starting
        # child processes, so SQL/driver compatibility fails without creating
        # migration contention or child cleanup work.
        with observer.connect():
            with observer.cursor() as cursor:
                observer.execute_query(
                    cursor,
                    "SELECT starts_with(?, ?), starts_with(?, ?)",
                    [
                        "SELECT pg_advisory_xact_lock(1, 2)",
                        "SELECT pg_advisory_xact_lock",
                        "SELECT pg_sleep(1)",
                        "SELECT pg_advisory_xact_lock",
                    ],
                )
                predicate_probe = cursor.fetchone()
        if predicate_probe != (True, False):
            raise RuntimeError("PostgreSQL starts_with predicate preflight failed")

        # Hold the exact production transaction-scoped lock until both OS
        # subprocesses have independently passed status inspection and are
        # visibly queued on the migration lock in pg_stat_activity.
        with lock_owner.connect():
            with lock_owner.transaction():
                with lock_owner.cursor() as cursor:
                    lock_owner.execute_query(cursor, "SELECT pg_backend_pid()", [])
                    controller_backend_pid = cursor.fetchone()[0]
                lock_owner.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(?))",
                    ["actions-runtime-schema-migrations"],
                )
                cwd = os.getcwd()  # Invoke from action_server in its prepared environment.
                for worker_app_name in worker_app_names:
                    env = os.environ.copy()
                    env["ACTIONS_TEST_DATABASE_URL"] = with_application_name(
                        url, worker_app_name
                    )
                    index = len(processes)
                    stdout_path = evidence_dir / f".worker-{index}.stdout.raw"
                    stderr_path = evidence_dir / f".worker-{index}.stderr.raw"
                    stdout_file = stdout_path.open("wb")
                    stderr_file = stderr_path.open("wb")
                    try:
                        process = subprocess.Popen(
                            [sys.executable, "-c", WORKER],
                            cwd=cwd,
                            env=env,
                            stdout=stdout_file,
                            stderr=stderr_file,
                            preexec_fn=_limit_child_output,
                        )
                    except BaseException:
                        stdout_file.close()
                        stderr_file.close()
                        stdout_path.unlink(missing_ok=True)
                        stderr_path.unlink(missing_ok=True)
                        raise
                    else:
                        stdout_file.close()
                        stderr_file.close()
                        processes.append(process)
                        raw_output_paths[index] = (stdout_path, stderr_path)

                while time.monotonic() < wait_deadline:
                    if any(process.poll() is not None for process in processes):
                        raise RuntimeError("A migration worker exited before reaching the lock")
                    current_waiting: dict[str, tuple[int, list[int]]] = {}
                    with observer.connect():
                        with observer.cursor() as cursor:
                            observer.execute_query(
                                cursor,
                                """SELECT application_name, pid, pg_blocking_pids(pid)
                                   FROM pg_stat_activity
                                   WHERE application_name IN (?, ?)
                                     AND datname=current_database()
                                     AND state='active'
                                     AND wait_event_type='Lock'
                                     AND wait_event='advisory'
                                     AND starts_with(query, 'SELECT pg_advisory_xact_lock')""",
                                worker_app_names,
                            )
                            rows = cursor.fetchall()
                            current_waiting = {
                                row[0]: (row[1], list(row[2]))
                                for row in rows
                                if controller_backend_pid in row[2]
                            }
                    if set(current_waiting) == set(worker_app_names):
                        waiting_backends = {
                            name: backend_pid
                            for name, (backend_pid, _blockers) in current_waiting.items()
                        }
                        if len(set(waiting_backends.values())) != 2:
                            raise RuntimeError("Workers did not use separate PostgreSQL backends")
                        wait_observations = {
                            name: {
                                "backend_pid": backend_pid,
                                "blocking_pids": blocker_pids,
                            }
                            for name, (backend_pid, blocker_pids) in current_waiting.items()
                        }
                        break
                    time.sleep(0.05)
                if set(waiting_backends) != set(worker_app_names):
                    raise TimeoutError("Both OS processes did not reach the migration advisory lock")
        # Exiting the owner transaction releases the lock; workers now serialize
        # on the production migrator's own advisory lock.

        for process in processes:
            remaining = wait_deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Shared migration-worker deadline expired")
            process.wait(timeout=remaining)
        for index, paths in raw_output_paths.items():
            stdout_path, stderr_path = paths
            outputs[index] = (
                stdout_path.read_bytes()[:65536].decode("utf-8", "replace"),
                stderr_path.read_bytes()[:65536].decode("utf-8", "replace"),
            )
        if any(process.returncode != 0 for process in processes):
            raise RuntimeError("A migration worker failed; inspect retained sanitized outputs")

        result_records = []
        for index in sorted(outputs):
            stdout, _stderr = outputs[index]
            lines = [line.removeprefix("RESULT_JSON=") for line in stdout.splitlines()
                     if line.startswith("RESULT_JSON=")]
            if len(lines) != 1:
                raise RuntimeError("Worker did not produce exactly one result record")
            result_records.append(json.loads(lines[0]))
        if any(not item["migrate_ok"] or item["status"] != "UP_TO_DATE"
               for item in result_records):
            raise RuntimeError("Workers did not both report current schema")
        if [item["pid"] for item in result_records] != [process.pid for process in processes]:
            raise RuntimeError("Worker result PID did not match its OS child PID")
        if len(set(process.pid for process in processes)) != 2:
            raise RuntimeError("Workers were not separate OS processes")
        if any(item["module_identity"] != expected_modules for item in result_records):
            raise RuntimeError("Worker imported different production source modules")
        if any(item["executable"] != sys.executable for item in result_records):
            raise RuntimeError("Workers did not use the reviewed interpreter")
        if any(item["version"] != sys.version for item in result_records):
            raise RuntimeError("Workers did not use the reviewed interpreter version")

        with probe.connect():
            with probe.cursor() as cursor:
                probe.execute_query(cursor, "SELECT id, name FROM migration ORDER BY id", [])
                migration_rows = cursor.fetchall()
                probe.execute_query(cursor, "SELECT COUNT(*) FROM migration WHERE id=?", [13])
                migration_13_count = cursor.fetchone()[0]
                probe.execute_query(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=current_schema() AND table_name=?",
                    ["mcp_catalog_name"],
                )
                catalog_table_count = cursor.fetchone()[0]

        if [row[0] for row in migration_rows] != [12, 13]:
            raise RuntimeError("Migration history did not match the controlled v12 fixture")
        if migration_rows != [(12, "reconcile_run_columns"), (13, "add_mcp_catalog_names")]:
            raise RuntimeError("Migration history names did not match source registry")
        if migration_13_count != 1 or catalog_table_count != 1:
            raise RuntimeError("Migration 13 did not converge to exactly one complete schema record")
        final_schema = schema_signature(probe)
        final_counts = table_counts(probe)
        if final_schema != v13_schema:
            raise RuntimeError("Migrated v13 table columns/indexes differ from production bootstrap schema")
        unchanged_tables = (set(v13_counts) & set(final_counts)) - {"migration", "mcp_catalog_name"}
        if any(v13_counts[name] != final_counts[name] for name in unchanged_tables):
            raise RuntimeError("Migration changed existing fixture table row counts")
        if counter_snapshot(probe) != v13_counters:
            raise RuntimeError("Migration changed existing counter fixture values")
        if final_counts.get("mcp_catalog_name") != 0:
            raise RuntimeError("New catalog table was not empty after migration")
        final_status = db_migration_status(fixture_url).name
        if final_status != "UP_TO_DATE":
            raise RuntimeError("Final database migration status is not current")
        print(json.dumps({
            "source": source,
            "module_identity": expected_modules,
            "worker_results": result_records,
            "worker_application_names": worker_app_names,
            "worker_identity_map": {
                worker_app_names[index]: {
                    "os_pid": processes[index].pid,
                    "backend_pid": waiting_backends[worker_app_names[index]],
                }
                for index in range(len(processes))
            },
            "waiting_backend_pids": waiting_backends,
            "wait_observations": wait_observations,
            "controller_backend_pid": controller_backend_pid,
            "os_child_pids": [process.pid for process in processes],
            "migration_rows": migration_rows,
            "migration_13_count": migration_13_count,
            "catalog_table_count": catalog_table_count,
            "catalog_schema_signature": final_schema,
            "interpreter": {"path": sys.executable, "version": sys.version},
            "final_status": final_status,
        }, sort_keys=True))
        return 0
    finally:
        cleanup_errors = []
        for index, process in enumerate(processes):
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)
            except BaseException as error:
                cleanup_errors.append({"pid": process.pid, "error": type(error).__name__})
                try:
                    process.kill()
                    process.wait(timeout=10)
                except BaseException as second_error:
                    cleanup_errors.append({"pid": process.pid, "kill_wait_error": type(second_error).__name__})
        for index, (stdout_path, stderr_path) in raw_output_paths.items():
            if index not in outputs:
                outputs[index] = (
                    stdout_path.read_bytes()[:65536].decode("utf-8", "replace")
                    if stdout_path.exists() else "",
                    stderr_path.read_bytes()[:65536].decode("utf-8", "replace")
                    if stderr_path.exists() else "",
                )
        log_receipts = {}
        parsed_url = urlsplit(url)
        secrets = [url, parsed_url.password or ""]
        for index, (stdout, stderr) in outputs.items():
            safe_stdout = redact_and_bound(stdout, secrets)
            safe_stderr = redact_and_bound(stderr, secrets)
            stdout_path = evidence_dir / f"worker-{index}.stdout.log"
            stderr_path = evidence_dir / f"worker-{index}.stderr.log"
            stdout_path.write_text(safe_stdout)
            stderr_path.write_text(safe_stderr)
            log_receipts[str(index)] = {
                "pid": processes[index].pid,
                "returncode": processes[index].returncode,
                "reaped": processes[index].poll() is not None,
                "stdout_sha256": hashlib.sha256(stdout_path.read_bytes()).hexdigest(),
                "stderr_sha256": hashlib.sha256(stderr_path.read_bytes()).hexdigest(),
                "stdout_bytes": stdout_path.stat().st_size,
                "stderr_bytes": stderr_path.stat().st_size,
            }
            for raw_path in raw_output_paths.get(index, ()):
                raw_path.unlink(missing_ok=True)
        cleanup_path = evidence_dir / "harness-child-cleanup.json"
        cleanup_path.write_text(json.dumps({
            "children": [
                {"pid": process.pid, "returncode": process.returncode,
                 "reaped": process.poll() is not None}
                for process in processes
            ],
            "controller_backend_pid": locals().get("controller_backend_pid"),
            "worker_application_names": locals().get("worker_app_names", []),
            "worker_logs": log_receipts,
            "waiting_backend_pids": waiting_backends,
            "wait_observations": wait_observations,
            "cleanup_errors": cleanup_errors,
        }, sort_keys=True, indent=2) + "\n")
        receipt_path = evidence_dir / "migration-worker-receipt.json"
        receipt_path.write_text(json.dumps({
            "source": source if "source" in locals() else None,
            "module_identity": expected_modules if "expected_modules" in locals() else None,
            "worker_identity_map": {
                worker_app_names[index]: {
                    "os_pid": processes[index].pid,
                    "backend_pid": waiting_backends.get(worker_app_names[index]),
                    "returncode": processes[index].returncode,
                }
                for index in range(len(processes))
            } if "worker_app_names" in locals() else {},
            "controller_backend_pid": locals().get("controller_backend_pid"),
            "wait_observations": wait_observations,
            "worker_logs": log_receipts,
            "cleanup_errors": cleanup_errors,
        }, sort_keys=True, indent=2) + "\n")
        if cleanup_errors:
            raise RuntimeError("One or more migration child processes could not be fully reaped")


def schema_signature(db) -> dict[str, list[tuple]]:
    with db.connect():
        with db.cursor() as cursor:
            db.execute_query(
                cursor,
                """SELECT column_name, data_type, is_nullable, column_default
                   FROM information_schema.columns
                   WHERE table_schema=current_schema() AND table_name='mcp_catalog_name'
                   ORDER BY ordinal_position""",
                [],
            )
            columns = cursor.fetchall()
            db.execute_query(
                cursor,
                """SELECT indexname, indexdef FROM pg_indexes
                   WHERE schemaname=current_schema() AND tablename='mcp_catalog_name'
                   ORDER BY indexname""",
                [],
            )
            indexes = cursor.fetchall()
    return {"columns": columns, "indexes": indexes}


def table_counts(db) -> dict[str, int]:
    counts = {}
    with db.connect():
        for table in db.list_table_names():
            escaped = table.replace('"', '""')
            with db.cursor() as cursor:
                db.execute_query(cursor, f'SELECT COUNT(*) FROM "{escaped}"', [])
                counts[table] = cursor.fetchone()[0]
    return counts


def counter_snapshot(db) -> list[tuple[str, int]]:
    from actions.server._models import Counter

    with db.connect():
        return sorted((row.id, row.value) for row in db.all(Counter))


def redact_and_bound(text: str, secrets: list[str], maximum: int = 65536) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    if len(text) > maximum:
        return text[:maximum] + "\n[TRUNCATED at 65536 characters]\n"
    return text


if __name__ == "__main__":
    raise SystemExit(main())
