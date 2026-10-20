"""Fenced ownership extends the existing queue; no second business authority."""

import multiprocessing
import sqlite3
from contextlib import contextmanager
from dataclasses import replace
from uuid import uuid4

import pytest

from actions.work_items._adapters._sqlite import SQLiteAdapter
from actions.work_items._exceptions import EmptyQueue
from actions.work_items._fencing import ClaimRejected
from actions.work_items._types import State


def adapter(tmp_path):
    return SQLiteAdapter(str(tmp_path / "queue.db"), files_dir=str(tmp_path / "files"))


def expire(queue, item):
    with sqlite3.connect(queue._db_path) as conn:
        conn.execute("UPDATE work_items SET claim_deadline_ms=0 WHERE id=?", (item,))


def test_owner_change_rejects_stale_finish_output_and_heartbeat_after_reopen(tmp_path):
    first = adapter(tmp_path)
    item = first.seed_input({"invoice_result": "immutable-result"})
    old = first.reserve_fenced(str(uuid4()), lease_seconds=30)
    assert old.item_id == item and old.epoch == 1
    expire(first, item)
    replacement = adapter(tmp_path)
    current = replacement.reserve_fenced(str(uuid4()), lease_seconds=30)
    assert current.item_id == item and current.epoch == 2
    for queue in (first, replacement):
        with pytest.raises(ClaimRejected):
            queue.finish_fenced(old, State.DONE, outputs=({"stale": True},))
        with pytest.raises(ClaimRejected):
            queue.renew_fenced(old, lease_seconds=30)
        with pytest.raises(ClaimRejected):
            queue.finish_fenced(replace(current, owner_id=str(uuid4())), State.DONE)
    assert replacement.list_items(queue_name="default_output") == []
    replacement.renew_fenced(current, lease_seconds=30)
    outputs = replacement.finish_fenced(current, State.DONE, outputs=({"report": "approved"},))
    assert len(outputs) == 1
    assert replacement.get_item(outputs[0])["parent_id"] == item
    assert replacement.load_payload(outputs[0]) == {"report": "approved"}
    with pytest.raises(ClaimRejected):
        replacement.finish_fenced(current, State.DONE, outputs=({"duplicate": True},))
    assert len(replacement.list_items(queue_name="default_output")) == 1


def test_expired_claim_cannot_finish_even_before_another_worker_claims(tmp_path):
    queue = adapter(tmp_path)
    queue.seed_input({})
    token = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    expire(queue, token.item_id)
    with pytest.raises(ClaimRejected):
        queue.finish_fenced(token, State.DONE)
    with pytest.raises(ClaimRejected):
        queue.renew_fenced(token, lease_seconds=30)


@pytest.mark.parametrize(
    "operation", ["release", "output", "payload", "add_file", "remove_file", "delete"]
)
def test_legacy_id_only_mutators_cannot_bypass_fenced_ownership(tmp_path, operation):
    queue = adapter(tmp_path)
    item = queue.seed_input({}, files={"original.txt": b"original"})
    token = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    operations = {
        "release": lambda: queue.release_input(item, State.DONE),
        "output": lambda: queue.create_output(item, {"bad": True}),
        "payload": lambda: queue.save_payload(item, {"changed": True}),
        "add_file": lambda: queue.add_file(item, "extra.txt", "extra.txt", b"bad"),
        "remove_file": lambda: queue.remove_file(item, "original.txt"),
        "delete": lambda: queue.delete_item(item),
    }
    with pytest.raises(ClaimRejected):
        operations[operation]()
    assert queue.load_payload(item) == {}
    assert queue.get_file(item, "original.txt") == b"original"
    queue.finish_fenced(token, State.DONE)
    with pytest.raises(ClaimRejected):
        operations[operation]()


def test_output_and_completion_roll_back_as_one_transition(tmp_path):
    queue = adapter(tmp_path)
    item = queue.seed_input({})
    token = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    with sqlite3.connect(queue._db_path) as conn:
        conn.execute(
            f"CREATE TRIGGER fail_finish BEFORE UPDATE OF state ON work_items WHEN NEW.state='{State.DONE.value}' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        queue.finish_fenced(token, State.DONE, outputs=({"not_published": True},))
    assert queue.list_items(queue_name="default_output") == []
    assert queue.get_item(item)["state"] == State.IN_PROGRESS.value


def test_legacy_orphan_recovery_cannot_reset_fenced_item(tmp_path):
    queue = adapter(tmp_path)
    item = queue.seed_input({})
    token = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    with sqlite3.connect(queue._db_path) as conn:
        conn.execute(
            "UPDATE work_items SET reserved_at='2000-01-01T00:00:00+00:00' WHERE id=?", (item,)
        )
    assert queue.recover_orphaned_work_items() == []
    queue.finish_fenced(token, State.DONE)


def _race_claim(db_path, files_dir, start, results):
    queue = SQLiteAdapter(db_path, files_dir=files_dir)
    start.wait(10)
    try:
        claim = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
        results.put((claim.item_id, claim.epoch))
    except EmptyQueue:
        results.put(None)


def test_competing_processes_have_one_current_work_item_owner(tmp_path):
    queue = adapter(tmp_path)
    item = queue.seed_input({})
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    results = context.Queue()
    processes = [
        context.Process(
            target=_race_claim, args=(str(queue._db_path), str(queue._files_dir), start, results)
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    start.set()
    outcomes = [results.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    assert outcomes.count((item, 1)) == 1
    assert outcomes.count(None) == 1


def test_database_clock_and_queue_identity_control_the_claim(tmp_path, monkeypatch):
    queue = adapter(tmp_path)
    item = queue.seed_input({})
    monkeypatch.setattr(queue, "_now", lambda: "1900-01-01T00:00:00+00:00")
    claim = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    foreign = SQLiteAdapter(
        str(queue._db_path), queue_name="other", files_dir=str(queue._files_dir)
    )
    with pytest.raises(ClaimRejected):
        foreign.finish_fenced(claim, State.DONE)
    assert queue.recover_orphaned_work_items() == []
    queue.finish_fenced(claim, State.DONE)
    assert queue.get_item(item)["state"] == State.DONE.value


def test_old_schema_writer_refuses_the_fenced_database(tmp_path, monkeypatch):
    from actions.work_items._adapters import _sqlite

    queue = adapter(tmp_path)
    queue.seed_input({})
    queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    monkeypatch.setattr(_sqlite, "SCHEMA_VERSION", 5)
    with pytest.raises(ValueError, match="newer than supported"):
        adapter(tmp_path)


def test_legacy_recovery_selection_cannot_overwrite_a_new_fenced_claim(tmp_path, monkeypatch):
    queue = adapter(tmp_path)
    item = queue.seed_input({})
    assert queue.reserve_input() == item
    with sqlite3.connect(queue._db_path) as conn:
        conn.execute(
            "UPDATE work_items SET reserved_at='2000-01-01T00:00:00+00:00' WHERE id=?", (item,)
        )
    replacement = adapter(tmp_path)
    current = []
    original = queue._get_conn

    class SelectedRows:
        def __init__(self, cursor):
            self.cursor = cursor

        def fetchall(self):
            rows = self.cursor.fetchall()
            # A second reconciler resets this legacy reservation. A real fenced
            # claimant then owns it before the first reconciler's stale UPDATE.
            assert replacement.recover_orphaned_work_items() == [item]
            current.append(replacement.reserve_fenced(str(uuid4()), lease_seconds=30))
            return rows

    class Connection:
        def __init__(self, conn):
            self.conn = conn

        def execute(self, sql, params=()):
            cursor = self.conn.execute(sql, params)
            if "SELECT id, reserved_at" in sql:
                return SelectedRows(cursor)
            return cursor

        def commit(self):
            self.conn.commit()

    @contextmanager
    def interleaved():
        with original() as conn:
            yield Connection(conn)

    monkeypatch.setattr(queue, "_get_conn", interleaved)
    assert queue.recover_orphaned_work_items() == []
    replacement.finish_fenced(current[0], State.DONE)
