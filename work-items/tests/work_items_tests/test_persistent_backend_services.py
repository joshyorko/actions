"""Release-gate tests against repository-owned Redis and MongoDB services."""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from actions.work_items import EmptyQueue, State

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PERSISTENT_BACKEND_SERVICES") != "1",
    reason="set RUN_PERSISTENT_BACKEND_SERVICES=1 with Compose services running",
)


@pytest.fixture
def redis_adapter(tmp_path, monkeypatch):
    redis = pytest.importorskip("redis")
    from actions.work_items import RedisAdapter

    url = os.getenv("TEST_REDIS_URL", "redis://127.0.0.1:16379/15")
    client = redis.from_url(url)
    client.flushdb()
    monkeypatch.setenv("RC_REDIS_URL", url)
    monkeypatch.setenv("RC_WORKITEM_QUEUE_NAME", "service_jobs")
    monkeypatch.setenv("RC_WORKITEM_OUTPUT_QUEUE_NAME", "service_results")
    monkeypatch.setenv("RC_WORKITEM_FILES_DIR", str(tmp_path / "redis-files"))
    monkeypatch.setenv("RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES", "0")
    adapter = RedisAdapter()
    yield adapter
    client.flushdb()
    client.close()


@pytest.fixture
def mongo_adapter(monkeypatch):
    pymongo = pytest.importorskip("pymongo")
    from actions.work_items import DocumentDBAdapter

    uri = os.getenv("TEST_MONGODB_URI", "mongodb://127.0.0.1:27027")
    database = "actions_work_items_service_gate"
    client = pymongo.MongoClient(uri)
    client.drop_database(database)
    monkeypatch.setenv("DOCDB_URI", uri)
    monkeypatch.setenv("DOCDB_DATABASE", database)
    monkeypatch.setenv("RC_WORKITEM_QUEUE_NAME", "service_jobs")
    monkeypatch.setenv("RC_WORKITEM_OUTPUT_QUEUE_NAME", "service_results")
    monkeypatch.setenv("RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES", "0")
    adapter = DocumentDBAdapter()
    yield adapter
    client.drop_database(database)
    client.close()


def _claim_all(adapter, count):
    def reserve_once(_):
        try:
            return adapter.reserve_input()
        except EmptyQueue:
            return None

    with ThreadPoolExecutor(max_workers=count + 2) as executor:
        return list(executor.map(reserve_once, range(count + 2)))


def _exercise_atomic_fifo_recovery(adapter):
    first = adapter.seed_input(payload={"order": 1})
    second = adapter.seed_input(payload={"order": 2})
    assert adapter.reserve_input() == first
    assert adapter.reserve_input() == second
    with pytest.raises(EmptyQueue):
        adapter.reserve_input()

    adapter.recover_orphaned_work_items()
    assert adapter.get_item(first)["state"] == State.PENDING.value
    assert adapter.get_item(second)["state"] == State.PENDING.value

    claimed = [item_id for item_id in _claim_all(adapter, 2) if item_id is not None]
    assert sorted(claimed) == sorted([first, second])
    assert len(claimed) == len(set(claimed))
    for item_id in claimed:
        adapter.delete_item(item_id)


def _exercise_attachments_output_and_cleanup(adapter):
    item_id = adapter.seed_input(payload=[1, 2])
    adapter.add_file(item_id, "small.txt", "small.txt", b"small")
    adapter.add_file(item_id, "large.bin", "large.bin", b"x" * 1_000_001)
    assert adapter.get_file(item_id, "small.txt") == b"small"
    assert adapter.get_file(item_id, "large.bin") == b"x" * 1_000_001
    with pytest.raises(FileExistsError):
        adapter.add_file(item_id, "small.txt", "small.txt", b"duplicate")

    output_id = adapter.create_output(item_id, payload={"result": True})
    assert adapter.get_item(output_id)["queue_name"] == "service_results"
    adapter.release_input(output_id, State.DONE)
    assert adapter.get_item(output_id)["state"] == State.DONE.value

    adapter.delete_item(item_id)
    adapter.delete_item(output_id)
    with pytest.raises(ValueError):
        adapter.get_item(item_id)
    with pytest.raises(ValueError):
        adapter.get_item(output_id)


def test_redis_service_atomic_fifo_recovery_attachments_routing_cleanup(redis_adapter):
    _exercise_atomic_fifo_recovery(redis_adapter)
    _exercise_attachments_output_and_cleanup(redis_adapter)
    assert list(redis_adapter._client.scan_iter(match="service_*")) == []
    assert list(redis_adapter._client.scan_iter(match="origin:*")) == []


def test_mongodb_service_atomic_fifo_recovery_attachments_routing_cleanup(mongo_adapter):
    _exercise_atomic_fifo_recovery(mongo_adapter)
    _exercise_attachments_output_and_cleanup(mongo_adapter)
    assert mongo_adapter._db["fs.files"].count_documents({}) == 0
    assert mongo_adapter._db["service_jobs_work_items"].count_documents({}) == 0
    assert mongo_adapter._db["service_results_work_items"].count_documents({}) == 0
