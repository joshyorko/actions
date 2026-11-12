"""Real owned PostgreSQL versions; no canonical ingestion/search readiness claim."""
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_database_shared import _postgresql_schema_url
from action_server_tests.test_knowledge_versions import build, normalize

from actions.server.data_queries.knowledge_versions import PostgreSQLKnowledgeVersions
from actions.server.data_queries.sealed_sources import ReadBudget, SealedReadRejected

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.fixture
def postgres():
    import psycopg
    from psycopg import sql

    base = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
    if not base:
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            pytest.fail("owned PostgreSQL required")
        pytest.skip("owned PostgreSQL not configured")
    schema = "knowledge_versions_" + uuid4().hex
    with psycopg.connect(base, autocommit=True) as owner:
        owner.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        url = _postgresql_schema_url(base, schema)

        def connect():
            return psycopg.connect(url, autocommit=True)

        try:
            yield SimpleNamespace(
                connect=connect, url=url, store=PostgreSQLKnowledgeVersions(connect)
            )
        finally:
            owner.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )


def budget():
    return ReadBudget(30000, threading.Event())


def test_versions_replay_and_fresh_process(postgres, foundry_package_store):
    inputs = build(foundry_package_store, b"retained document")
    first = normalize(foundry_package_store, inputs)
    changed = inputs[0].model_copy(update={"max_results": 2})
    second = normalize(foundry_package_store, (changed, inputs[1], inputs[2]))
    store = postgres.store
    with pytest.raises(SealedReadRejected):
        store.put(first, operation_id="one", budget=budget())
    store.provision()
    store.put(first, operation_id="one", budget=budget())
    assert store.put(first, operation_id="one", budget=budget()) == inputs[0].reference
    with pytest.raises(SealedReadRejected, match="conflicts"):
        store.put(second, operation_id="one", budget=budget())
    store.put(second, operation_id="two", budget=budget())
    assert store.read(inputs[0].reference, budget=budget()) == first
    assert store.read(changed.reference, budget=budget()) == second
    script = """
import os, sys, threading, psycopg
from actions.server.data_queries.knowledge_versions import PostgreSQLKnowledgeVersions
from actions.server.data_queries.knowledge_values import KnowledgeRevisionRef
from actions.server.data_queries.sealed_sources import ReadBudget
store = PostgreSQLKnowledgeVersions(lambda: psycopg.connect(os.environ['ACTIONS_KNOWLEDGE_PG_TEST_URL'], autocommit=True))
print(store.read(KnowledgeRevisionRef.model_validate_json(sys.argv[1]), budget=ReadBudget(30000, threading.Event())).digest)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, inputs[0].reference.model_dump_json()],
        env=dict(os.environ, ACTIONS_KNOWLEDGE_PG_TEST_URL=postgres.url),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert result.stdout.strip() == first.digest


def test_document_failure_rolls_back_version_and_operation(
    postgres, foundry_package_store, monkeypatch
):
    corpus = normalize(foundry_package_store, build(foundry_package_store, b"document"))
    store = postgres.store
    store.provision()
    execute = store._execute

    def fail(connection, statement, parameters=()):
        if statement.startswith("INSERT INTO actions_knowledge_documents"):
            raise RuntimeError("synthetic write interruption")
        return execute(connection, statement, parameters)

    monkeypatch.setattr(store, "_execute", fail)
    with pytest.raises(SealedReadRejected, match="unavailable"):
        store.put(corpus, operation_id="one", budget=budget())
    with postgres.connect() as connection:
        for table in ("versions", "documents", "operations"):
            assert connection.execute(
                "SELECT count(*) FROM actions_knowledge_" + table
            ).fetchone() == (0,)
    monkeypatch.setattr(store, "_execute", execute)
    store.put(corpus, operation_id="one", budget=budget())


@pytest.mark.parametrize("conflict", [False, True])
def test_independent_connections_serialize_operation_identity(
    postgres, foundry_package_store, conflict
):
    inputs = build(foundry_package_store, b"document")
    first = normalize(foundry_package_store, inputs)
    second = (
        normalize(
            foundry_package_store,
            (inputs[0].model_copy(update={"max_results": 2}), inputs[1], inputs[2]),
        )
        if conflict
        else first
    )
    postgres.store.provision()
    start = threading.Barrier(2)

    def put(corpus):
        store = PostgreSQLKnowledgeVersions(postgres.connect)
        start.wait(timeout=10)
        try:
            return store.put(corpus, operation_id="same", budget=budget())
        except SealedReadRejected:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(put, [first, second]))
    assert sum(result is not None for result in results) == (1 if conflict else 2)
    with postgres.connect() as connection:
        assert connection.execute(
            "SELECT count(*) FROM actions_knowledge_operations"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT count(*) FROM actions_knowledge_versions"
        ).fetchone() == (1,)


def test_cancel_while_waiting_for_provider_lock(postgres, foundry_package_store):
    corpus = normalize(foundry_package_store, build(foundry_package_store, b"document"))
    postgres.store.provision()
    cancel = threading.Event()
    entered = threading.Event()
    worker_pid = []

    def connect():
        connection = postgres.connect()
        worker_pid.append(connection.info.backend_pid)
        entered.set()
        return connection

    store = PostgreSQLKnowledgeVersions(connect)
    with postgres.connect() as blocker:
        blocker.execute("BEGIN")
        blocker.execute(
            "LOCK TABLE actions_knowledge_operations IN ACCESS EXCLUSIVE MODE"
        )
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(
                    store.put,
                    corpus,
                    operation_id="cancelled",
                    budget=ReadBudget(30000, cancel),
                )
                try:
                    assert entered.wait(timeout=10)
                    with postgres.connect() as observer:
                        deadline = time.monotonic() + 5
                        while time.monotonic() < deadline:
                            state = observer.execute(
                                "SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s",
                                (worker_pid[0],),
                            ).fetchone()
                            if state == ("Lock",):
                                break
                            time.sleep(0.01)
                        else:
                            pytest.fail("provider write did not reach the held lock")
                finally:
                    cancel.set()
                with pytest.raises(SealedReadRejected):
                    pending.result(timeout=10)
        finally:
            blocker.execute("ROLLBACK")
    with postgres.connect() as connection:
        assert connection.execute(
            "SELECT count(*) FROM actions_knowledge_operations"
        ).fetchone() == (0,)
    assert store.put(corpus, operation_id="cancelled", budget=budget())


def test_corrupted_retained_document_refuses_replay(postgres, foundry_package_store):
    inputs = build(foundry_package_store, b"document")
    corpus = normalize(foundry_package_store, inputs)
    postgres.store.provision()
    postgres.store.put(corpus, operation_id="one", budget=budget())
    with postgres.connect() as connection:
        connection.execute("UPDATE actions_knowledge_documents SET document_json='{}'")
    with pytest.raises(SealedReadRejected):
        postgres.store.read(inputs[0].reference, budget=budget())
    with pytest.raises(SealedReadRejected):
        postgres.store.put(corpus, operation_id="one", budget=budget())
