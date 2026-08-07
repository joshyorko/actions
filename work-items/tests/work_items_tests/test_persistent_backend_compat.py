"""Compatibility tests for historical persistent-backend records."""

import pytest

from actions.work_items import State
from actions.work_items._adapters._docdb import DocumentDBAdapter
from actions.work_items._adapters._redis import (
    DatabaseTemporarilyUnavailable,
    RedisAdapter,
    RedisConnectionError,
)


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
        self.written_keys = []

    def _record(self, key, *args, **kwargs):
        self.keys.append(key)
        self.keys.extend(arg for arg in args if isinstance(arg, str) and ":" in arg)

    lrem = _record
    srem = _record
    sadd = _record
    expire = _record
    set = _record

    def delete(self, key, *args):
        self._record(key, *args)

    def hset(self, key, *args, **kwargs):
        self._record(key, *args, **kwargs)
        self.written_keys.append(key)

    def hgetall(self, key):
        self.keys.append(key)
        return {}

    def hdel(self, key, *args):
        self.keys.append(key)

    def pipeline(self, transaction=True):
        assert transaction is True
        return self

    def execute(self):
        return []


class _FailingRedisPipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def __getattr__(self, name):
        def queue(*args, **kwargs):
            self.commands.append((name, args, kwargs))
            return self

        return queue

    def execute(self):
        raise RedisConnectionError("injected terminal metadata write failure")


class _RedisReleaseFailureFake(_RedisWriteFake):
    def __init__(self):
        super().__init__()
        self.values = {
            "jobs:state:item-1": "FAILED",
            "jobs:timestamps:item-1": "historical-timestamp",
            "jobs:exception:item-1": "historical-exception",
        }

    def pipeline(self, transaction=True):
        assert transaction is True
        return _FailingRedisPipeline(self)

    def delete(self, key, *args):
        super().delete(key, *args)
        for candidate in (key, *args):
            self.values.pop(candidate, None)


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
    assert "jobs:exception:item-1" not in adapter._client.written_keys


def test_redis_release_preserves_legacy_metadata_when_current_write_fails():
    """A failed terminal transaction cannot erase the only lifecycle metadata."""
    adapter = RedisAdapter.__new__(RedisAdapter)
    adapter.queue_name = "jobs"
    adapter.output_queue_name = "results"
    adapter._queue_cache = {"item-1": "results"}
    adapter._client = _RedisReleaseFailureFake()

    with pytest.raises(DatabaseTemporarilyUnavailable):
        adapter.release_input("item-1", State.DONE)

    assert adapter._client.values == {
        "jobs:state:item-1": "FAILED",
        "jobs:timestamps:item-1": "historical-timestamp",
        "jobs:exception:item-1": "historical-exception",
    }


def test_redis_reads_historical_input_queue_metadata_for_output_item():
    adapter = RedisAdapter.__new__(RedisAdapter)
    adapter.queue_name = "jobs"
    adapter.output_queue_name = "results"
    adapter._queue_cache = {"item-1": "results"}
    adapter._client = _RedisReadFake(
        {
            "results:payload:item-1": {b"payload": b"{}"},
            "jobs:timestamps:item-1": {b"created_at": b"2026-01-01T00:00:00"},
            "jobs:exception:item-1": {b"code": b"E1", b"message": b"failed"},
        },
        {"jobs:state:item-1": b"FAILED"},
    )
    adapter.list_files = lambda item_id: []

    item = adapter._item_to_api("item-1", "results")

    assert item["state"] == State.FAILED.value
    assert item["created_at"] == "2026-01-01T00:00:00"
    assert item["error_code"] == "E1"


def test_redis_delete_cleans_queue_scoped_and_historical_input_metadata():
    adapter = RedisAdapter.__new__(RedisAdapter)
    adapter.queue_name = "jobs"
    adapter.output_queue_name = "results"
    adapter._queue_cache = {"item-1": "results"}
    adapter._client = _RedisWriteFake()

    adapter.delete_item("item-1")

    for suffix in ("timestamps", "state", "exception"):
        assert f"results:{suffix}:item-1" in adapter._client.keys
        assert f"jobs:{suffix}:item-1" in adapter._client.keys


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
