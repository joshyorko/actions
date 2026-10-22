"""PostgreSQL initialization never adopts a user's existing queue or upgrades it."""

from uuid import uuid4

import pytest

from actions.work_items._adapters._postgres_fenced import PostgreSQLFencedQueue

from . import test_fenced_queue_conformance as fixtures

postgres_backend = fixtures.postgres_backend

pytestmark = pytest.mark.fenced_postgres_service


def test_future_service_format_is_rejected_without_mutating_items(postgres_backend):
    import psycopg
    from psycopg import sql

    queue = postgres_backend.queue
    item = queue.seed_input({"retained": True})
    with psycopg.connect(queue._dsn) as conn:
        conn.execute(
            sql.SQL("UPDATE {}.fenced_queue_schema SET version=2").format(
                sql.Identifier(queue._schema)
            )
        )
    with pytest.raises(ValueError, match="Unsupported"):
        queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    with pytest.raises(ValueError, match="Unsupported"):
        queue.initialize_empty_schema()
    with psycopg.connect(queue._dsn) as conn:
        row = conn.execute(
            sql.SQL("SELECT state,claim_epoch,payload FROM {}.work_items WHERE id=%s").format(
                sql.Identifier(queue._schema)
            ),
            (item,),
        ).fetchone()
    assert row == ("PENDING", 0, {"retained": True})


def test_nonempty_schema_is_not_adopted_or_migrated(postgres_backend):
    import psycopg
    from psycopg import sql

    dsn = postgres_backend.queue._dsn
    schema = "unmanaged_test_" + uuid4().hex
    with psycopg.connect(dsn) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(
            sql.SQL("CREATE TABLE {}.work_items (payload TEXT)").format(sql.Identifier(schema))
        )
        conn.execute(
            sql.SQL("INSERT INTO {}.work_items VALUES (%s)").format(sql.Identifier(schema)),
            ("retained-marker",),
        )
    try:
        queue = PostgreSQLFencedQueue(dsn, schema=schema)
        with pytest.raises(ValueError, match="Refusing to adopt"):
            queue.initialize_empty_schema()
        with psycopg.connect(dsn) as conn:
            assert conn.execute(
                sql.SQL("SELECT payload FROM {}.work_items").format(sql.Identifier(schema))
            ).fetchall() == [("retained-marker",)]
    finally:
        with psycopg.connect(dsn) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_initialization_requires_existing_schema_and_is_repeatable(postgres_backend):
    queue = postgres_backend.queue
    queue.initialize_empty_schema()
    with pytest.raises(ValueError, match="existing owned"):
        PostgreSQLFencedQueue(
            queue._dsn, schema="missing_test_" + uuid4().hex
        ).initialize_empty_schema()


def test_schema_identifier_rejects_sql_before_connecting():
    with pytest.raises(ValueError, match="canonical dedicated schema"):
        PostgreSQLFencedQueue("unusable-synthetic-dsn", schema="public; DROP TABLE work_items")


def test_matching_version_does_not_adopt_unknown_column_layout(postgres_backend):
    import psycopg
    from psycopg import sql

    queue = postgres_backend.queue
    item = queue.seed_input({"retained": True})
    with psycopg.connect(queue._dsn) as conn:
        conn.execute(
            sql.SQL("ALTER TABLE {}.work_items ADD COLUMN unreviewed TEXT").format(
                sql.Identifier(queue._schema)
            )
        )
    with pytest.raises(ValueError, match="column layout"):
        queue.initialize_empty_schema()
    with pytest.raises(ValueError, match="column layout"):
        queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    with psycopg.connect(queue._dsn) as conn:
        assert conn.execute(
            sql.SQL("SELECT state,claim_epoch FROM {}.work_items WHERE id=%s").format(
                sql.Identifier(queue._schema)
            ),
            (item,),
        ).fetchone() == ("PENDING", 0)
