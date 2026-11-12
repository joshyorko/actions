"""PostgreSQL initialization never adopts a user's existing queue or upgrades it."""

from uuid import uuid4

import pytest

from actions.work_items._adapters._postgres_fenced import PostgreSQLFencedQueue
from actions.work_items._fencing import ClaimRejected, RetryEvidence, payload_fingerprint
from actions.work_items._types import State

from . import test_fenced_queue_conformance as fixtures

postgres_backend = fixtures.postgres_backend

pytestmark = pytest.mark.fenced_postgres_service


@pytest.mark.parametrize(
    "metadata", [(2, "actions.work-items.fenced-postgresql/v1"), (1, "unknown")]
)
def test_future_service_format_is_rejected_without_mutating_items(postgres_backend, metadata):
    import psycopg
    from psycopg import sql

    queue = postgres_backend.queue
    item = queue.seed_input({"retained": True})
    claim = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    before = queue.get_item(item)
    with psycopg.connect(queue._dsn) as conn:
        conn.execute(
            sql.SQL("UPDATE {}.fenced_queue_schema SET version=%s,format=%s").format(
                sql.Identifier(queue._schema)
            ),
            metadata,
        )
    evidence = RetryEvidence(
        payload_fingerprint({"retained": True}), "no_effect", "sha256:" + "a" * 64, "application"
    )
    operations = [
        queue.initialize_empty_schema,
        lambda: queue.seed_input({"must_not_exist": True}),
        lambda: queue.reserve_fenced(str(uuid4()), lease_seconds=30),
        lambda: queue.renew_fenced(claim, lease_seconds=30),
        lambda: queue.finish_fenced(claim, State.DONE, outputs=({"must_not_exist": True},)),
        lambda: queue.retry_fenced(
            claim, evidence=evidence, verify_receipt=lambda *_: True, max_claims=2
        ),
        lambda: queue.get_item(item),
        lambda: queue.load_payload(item),
        queue.list_items,
        lambda: queue.retry_history(item),
    ]
    for operation in operations:
        with pytest.raises(ValueError, match="Unsupported"):
            operation()
    with psycopg.connect(queue._dsn) as conn:
        row = conn.execute(
            sql.SQL("SELECT state,claim_epoch,payload,claim_owner,claim_deadline_ms FROM {}.work_items WHERE id=%s").format(
                sql.Identifier(queue._schema)
            ),
            (item,),
        ).fetchone()
        assert conn.execute(
            sql.SQL("SELECT COUNT(*) FROM {}.work_items").format(sql.Identifier(queue._schema))
        ).fetchone() == (1,)
        assert conn.execute(
            sql.SQL("SELECT COUNT(*) FROM {}.actions_fenced_retry_v1").format(
                sql.Identifier(queue._schema)
            )
        ).fetchone() == (0,)
    assert row == (
        State.IN_PROGRESS.value,
        claim.epoch,
        {"retained": True},
        claim.owner_id,
        before["claim_deadline_ms"],
    )


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


def test_initialization_refuses_an_empty_schema_owned_by_another_role(postgres_backend):
    import psycopg
    from psycopg import sql

    dsn = postgres_backend.queue._dsn
    schema = "foreign_test_" + uuid4().hex
    role = "fenced_owner_test_" + uuid4().hex
    # This NOLOGIN role exists only in the owned disposable service. It has no credentials.
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role)))
    try:
        with psycopg.connect(dsn) as conn:
            conn.execute(
                sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                    sql.Identifier(schema), sql.Identifier(role)
                )
            )
        with pytest.raises(ValueError, match="existing owned"):
            PostgreSQLFencedQueue(dsn, schema=schema).initialize_empty_schema()
        with psycopg.connect(dsn) as conn:
            assert conn.execute(
                "SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=%s", (schema,)
            ).fetchone() == (role,)
            assert conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s", (schema,)
            ).fetchone() == (0,)
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            conn.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))


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


def test_expiry_during_output_insertion_rolls_back_completion_and_children(postgres_backend):
    import psycopg
    from psycopg import sql

    queue = postgres_backend.queue
    item = queue.seed_input({"invoice": "pinned"})
    claim = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    before = queue.get_item(item)
    with psycopg.connect(queue._dsn) as conn:
        conn.execute(
            sql.SQL("""CREATE FUNCTION {}.expire_parent() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                UPDATE {}.work_items SET claim_deadline_ms=0 WHERE id=NEW.parent_id;
                RETURN NEW;
            END $$""").format(sql.Identifier(queue._schema), sql.Identifier(queue._schema))
        )
        conn.execute(
            sql.SQL("""CREATE TRIGGER expire_parent BEFORE INSERT ON {}.work_items
            FOR EACH ROW WHEN (NEW.parent_id IS NOT NULL)
            EXECUTE FUNCTION {}.expire_parent()""").format(
                sql.Identifier(queue._schema), sql.Identifier(queue._schema)
            )
        )
    with pytest.raises(ClaimRejected, match="expired before publication"):
        queue.finish_fenced(claim, State.DONE, outputs=({"unpublished": True},))
    assert queue.list_items(queue_name="default_output") == []
    assert queue.get_item(item) == before
    with psycopg.connect(queue._dsn) as conn:
        conn.execute(
            sql.SQL("DROP TRIGGER expire_parent ON {}.work_items").format(sql.Identifier(queue._schema))
        )
    outputs = queue.finish_fenced(claim, State.DONE, outputs=({"published": True},))
    assert len(outputs) == 1
    assert queue.get_item(item)["state"] == State.DONE.value
    assert queue.get_item(outputs[0])["parent_id"] == item
