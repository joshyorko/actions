"""Compatibility tests for historical persistent-backend records."""

from actions.work_items import State
from actions.work_items._adapters._docdb import DocumentDBAdapter
from actions.work_items._adapters._redis import RedisAdapter


class _RedisReadFake:
    def __init__(self, hashes, values):
        self.hashes = hashes
        self.values = values

    def hgetall(self, key):
        return self.hashes.get(key, {})

    def get(self, key):
        return self.values.get(key)


class _RedisWriteFake:
    def __init__(self):
        self.keys = []

    def _record(self, key, *args, **kwargs):
        self.keys.append(key)

    lrem = _record
    srem = _record
    sadd = _record
    delete = _record
    hset = _record
    expire = _record
    set = _record


def test_redis_decodes_historical_state_exception_and_scalar_payload():
    adapter = RedisAdapter.__new__(RedisAdapter)
    adapter.queue_name = "jobs"
    adapter.output_queue_name = "jobs_output"
    adapter._queue_cache = {}
    adapter._client = _RedisReadFake(
        {
            "jobs:payload:item-1": {b"payload": b"[1, 2]", b"queue_name": b"jobs"},
            "jobs:timestamps:item-1": {b"created_at": b"2026-01-01T00:00:00"},
            "jobs:exception:item-1": {
                b"exception_code": b"E1",
                b"exception_message": b"failed",
            },
        },
        {"jobs:state:item-1": b"DONE"},
    )
    adapter.list_files = lambda item_id: []

    item = adapter._item_to_api("item-1", "jobs")

    assert item["state"] == State.DONE.value
    assert item["payload"] == [1, 2]
    assert item["error_code"] == "E1"
    assert item["error_message"] == "failed"


def test_redis_release_routes_all_metadata_to_output_queue():
    adapter = RedisAdapter.__new__(RedisAdapter)
    adapter.queue_name = "jobs"
    adapter.output_queue_name = "results"
    adapter._queue_cache = {"item-1": "results"}
    adapter._client = _RedisWriteFake()

    adapter.release_input("item-1", State.FAILED, code="E1", message="failed")

    assert "results:exception:item-1" in adapter._client.keys
    assert "results:timestamps:item-1" in adapter._client.keys
    assert "results:state:item-1" in adapter._client.keys
    assert "jobs:exception:item-1" not in adapter._client.keys


def test_docdb_decodes_flat_historical_state_exception_and_timestamps():
    adapter = DocumentDBAdapter.__new__(DocumentDBAdapter)
    adapter.queue_name = "jobs"

    item = adapter._item_to_api(
        {
            "item_id": "item-1",
            "queue_name": "jobs",
            "state": "COMPLETED",
            "payload": [1, 2],
            "created_at": "2026-01-01T00:00:00",
            "reserved_at": "2026-01-01T00:01:00",
            "exception_code": "E1",
            "exception_message": "failed",
            "files": {},
        }
    )

    assert item["state"] == State.DONE.value
    assert item["payload"] == [1, 2]
    assert item["error_code"] == "E1"
    assert item["error_message"] == "failed"
    assert item["created_at"] == "2026-01-01T00:00:00"
    assert item["updated_at"] == "2026-01-01T00:01:00"
