"""One ownership contract against local SQLite and an actual PostgreSQL service."""

import hashlib
import os
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from uuid import uuid4

import pytest

from actions.work_items._adapters._postgres_fenced import PostgreSQLFencedQueue
from actions.work_items._adapters._sqlite import SQLiteAdapter
from actions.work_items._exceptions import EmptyQueue
from actions.work_items._fencing import (
    ClaimRejected,
    QueueStorageError,
    RetryEvidence,
    payload_fingerprint,
)
from actions.work_items._types import State


@dataclass
class Backend:
    queue: object
    reopen: object
    expire: object
    abort_finish: object
    storage_error: type[Exception]


@pytest.fixture(
    params=["sqlite", pytest.param("postgresql", marks=pytest.mark.fenced_postgres_service)]
)
def backend(request, tmp_path):
    if request.param == "sqlite":

        def reopen(queue_name="default"):
            return SQLiteAdapter(
                str(tmp_path / "queue.db"), queue_name=queue_name, files_dir=str(tmp_path / "files")
            )

        def expire(item):
            with sqlite3.connect(tmp_path / "queue.db") as conn:
                conn.execute("UPDATE work_items SET claim_deadline_ms=0 WHERE id=?", (item,))

        def abort_finish():
            with sqlite3.connect(tmp_path / "queue.db") as conn:
                conn.execute(
                    f"CREATE TRIGGER fail_finish BEFORE UPDATE OF state ON work_items WHEN NEW.state='{State.DONE.value}' BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END"
                )

        yield Backend(reopen(), reopen, expire, abort_finish, sqlite3.IntegrityError)
        return

    yield request.getfixturevalue("postgres_backend")


@pytest.fixture
def postgres_backend(request):
    request.node.add_marker(pytest.mark.fenced_postgres_service)
    dsn = os.environ.get("ACTIONS_FENCED_TEST_POSTGRES")
    if not dsn:
        if os.environ.get("ACTIONS_REQUIRE_FENCED_POSTGRES") == "1":
            pytest.fail("owned PostgreSQL fixture is required")
        pytest.skip("run the canonical FencedWorkItemsTest service gate")
    import psycopg
    from psycopg import sql

    schema = "fenced_test_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:

        def reopen(queue_name="default"):
            return PostgreSQLFencedQueue(dsn, schema=schema, queue_name=queue_name)

        queue = reopen()
        queue.initialize_empty_schema()

        def expire(item):
            with psycopg.connect(dsn) as conn:
                conn.execute(
                    sql.SQL("UPDATE {}.work_items SET claim_deadline_ms=0 WHERE id=%s").format(
                        sql.Identifier(schema)
                    ),
                    (item,),
                )

        def abort_finish():
            with psycopg.connect(dsn) as conn:
                conn.execute(
                    sql.SQL(
                        "CREATE FUNCTION {}.fail_finish() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rollback'; END $$"
                    ).format(sql.Identifier(schema))
                )
                conn.execute(
                    sql.SQL(
                        "CREATE TRIGGER fail_finish BEFORE UPDATE OF state ON {}.work_items FOR EACH ROW WHEN (NEW.state='COMPLETED') EXECUTE FUNCTION {}.fail_finish()"
                    ).format(sql.Identifier(schema), sql.Identifier(schema))
                )

        yield Backend(queue, reopen, expire, abort_finish, QueueStorageError)
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_two_owners_have_one_current_claim(backend):
    item = backend.queue.seed_input({"invoice": "synthetic"})
    queues = [backend.reopen(), backend.reopen()]
    barrier = threading.Barrier(2)

    def claim(queue):
        barrier.wait(timeout=10)
        try:
            return queue.reserve_fenced(str(uuid4()), lease_seconds=30)
        except EmptyQueue:
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(claim, queues))
    winners = [token for token in outcomes if token is not None]
    assert len(winners) == 1
    assert winners[0].item_id == item and winners[0].epoch == 1


def test_takeover_rejects_stale_final_completion_outputs_and_renew(backend):
    queue = backend.queue
    item = queue.seed_input({"result": "pinned"})
    old = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    backend.expire(item)
    reopened = backend.reopen()
    current = reopened.reserve_fenced(str(uuid4()), lease_seconds=30)
    assert current.item_id == old.item_id and current.epoch == old.epoch + 1
    with pytest.raises(ClaimRejected):
        queue.renew_fenced(old, lease_seconds=30)
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(old, State.DONE, outputs=({"stale": True},))
    assert queue.list_items(queue_name="default_output") == []
    reopened.renew_fenced(current, lease_seconds=30)
    ids = reopened.finish_fenced(current, State.DONE, outputs=({"report": "retained"},))
    assert len(ids) == 1
    assert reopened.get_item(ids[0])["parent_id"] == item
    assert reopened.load_payload(ids[0]) == {"report": "retained"}


def test_duplicate_delivery_and_terminal_failure_are_not_implicit_retries(backend):
    queue = backend.queue
    item = queue.seed_input({})
    token = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    queue.finish_fenced(token, State.FAILED, message="synthetic application failure")
    assert queue.get_item(item)["state"] == State.FAILED.value
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(token, State.DONE, outputs=({"duplicate": True},))
    with pytest.raises(EmptyQueue):
        backend.reopen().reserve_fenced(str(uuid4()), lease_seconds=30)
    assert queue.list_items(queue_name="default_output") == []


def test_expired_claim_rejected_without_takeover(backend):
    queue = backend.queue
    item = queue.seed_input({})
    token = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    backend.expire(item)
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(token, State.DONE)
    with pytest.raises(ClaimRejected):
        queue.renew_fenced(token, lease_seconds=30)


def test_wrong_owner_epoch_or_queue_cannot_finish(backend):
    queue = backend.queue
    queue.seed_input({})
    token = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    for bad in (replace(token, owner_id=str(uuid4())), replace(token, epoch=token.epoch + 1)):
        with pytest.raises(ClaimRejected):
            queue.finish_fenced(bad, State.DONE)
    with pytest.raises(ClaimRejected):
        backend.reopen(queue_name="other").finish_fenced(token, State.DONE)


def test_output_and_completion_roll_back_together(backend):
    queue = backend.queue
    item = queue.seed_input({})
    token = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    backend.abort_finish()
    with pytest.raises(backend.storage_error):
        queue.finish_fenced(token, State.DONE, outputs=({"invisible": True},))
    assert queue.list_items(queue_name="default_output") == []
    assert queue.get_item(item)["state"] == State.IN_PROGRESS.value


def test_successful_duplicate_finish_never_republishes(backend):
    queue = backend.queue
    queue.seed_input({})
    token = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    queue.finish_fenced(token, State.DONE, outputs=({"once": True},))
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(token, State.DONE, outputs=({"twice": True},))
    assert len(queue.list_items(queue_name="default_output")) == 1


@pytest.mark.parametrize("effect", ["no_effect", "reconciled"])
def test_explicit_verified_retry_survives_reopen_and_increments_epoch(backend, effect, tmp_path):
    queue = backend.queue
    item = queue.seed_input({"invoice": "pinned"})
    old = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    receipt = tmp_path / "effect-receipt"
    receipt.write_text(f"{item}:{old.epoch}:{effect}")
    evidence = RetryEvidence(
        payload_fingerprint(queue.load_payload(item)),
        effect,
        "sha256:" + hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "application",
    )

    def verify(actual, claim):
        return (
            actual == evidence
            and claim == old
            and actual.receipt_sha256
            == "sha256:" + hashlib.sha256(receipt.read_bytes()).hexdigest()
        )

    queue.retry_fenced(old, evidence=evidence, verify_receipt=verify, max_claims=2)
    reopened = backend.reopen()
    history = reopened.retry_history(item)
    assert len(history) == 1
    assert history[0]["epoch"] == old.epoch and history[0]["effect"] == effect
    current = reopened.reserve_fenced(str(uuid4()), lease_seconds=30)
    assert current.epoch == old.epoch + 1
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(old, State.DONE, outputs=({"stale": True},))
    reopened.finish_fenced(current, State.DONE, outputs=({"receipt": evidence.receipt_sha256},))


def test_retry_requires_receipt_input_binding_and_budget(backend):
    queue = backend.queue
    item = queue.seed_input({"protected": True})
    claim = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    evidence = RetryEvidence(
        payload_fingerprint(queue.load_payload(item)),
        "no_effect",
        "sha256:" + "a" * 64,
        "infrastructure",
    )
    with pytest.raises(ClaimRejected):
        queue.retry_fenced(claim, evidence=evidence, verify_receipt=lambda *_: False, max_claims=3)
    with pytest.raises(ClaimRejected):
        queue.retry_fenced(
            claim,
            evidence=replace(evidence, input_sha256="sha256:" + "b" * 64),
            verify_receipt=lambda *_: True,
            max_claims=3,
        )
    with pytest.raises(ClaimRejected):
        queue.retry_fenced(claim, evidence=evidence, verify_receipt=lambda *_: True, max_claims=1)
    assert queue.retry_history(item) == []
    assert queue.get_item(item)["state"] == State.IN_PROGRESS.value
    with pytest.raises(ValueError):
        replace(evidence, effect="unknown")


def test_takeover_during_receipt_verification_rejects_retry(backend):
    queue = backend.queue
    item = queue.seed_input({})
    old = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    evidence = RetryEvidence(
        payload_fingerprint({}), "reconciled", "sha256:" + "a" * 64, "infrastructure"
    )
    current = []

    def verify(*_):
        backend.expire(item)
        current.append(backend.reopen().reserve_fenced(str(uuid4()), lease_seconds=30))
        return True

    with pytest.raises(ClaimRejected):
        queue.retry_fenced(old, evidence=evidence, verify_receipt=verify, max_claims=3)
    assert queue.retry_history(item) == []
    queue.finish_fenced(current[0], State.DONE)
