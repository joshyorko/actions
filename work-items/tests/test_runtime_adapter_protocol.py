from typing_extensions import get_overloads

from actions.work_items import Output, RuntimeAdapter
from actions.work_items._support import add_file, release_input
from actions.work_items._types import State


class CurrentAdapter:
    def __init__(self):
        self.calls = []

    def add_file(self, item_id, name, original_name, content):
        self.calls.append((item_id, name, original_name, content))

    def release_input(self, item_id, state, exception_type=None, code=None, message=None):
        self.calls.append((item_id, state, exception_type, code, message))


class UpstreamAdapter:
    def __init__(self):
        self.calls = []

    def add_file(self, item_id, name, content):
        self.calls.append((item_id, name, content))

    def release_input(self, item_id, state, exception=None):
        self.calls.append((item_id, state, exception))


def test_runtime_adapter_protocol_publishes_both_signature_generations():
    assert len(get_overloads(RuntimeAdapter.release_input)) == 2
    assert len(get_overloads(RuntimeAdapter.add_file)) == 2


def test_attachment_normalization_preserves_distinct_original_name():
    current = CurrentAdapter()
    upstream = UpstreamAdapter()

    add_file(current, "item", "stored.txt", "source.csv", b"data")
    add_file(upstream, "item", "stored.txt", "source.csv", b"data")

    assert current.calls == [("item", "stored.txt", "source.csv", b"data")]
    assert upstream.calls == [("item", "stored.txt", b"data")]


def test_output_staging_preserves_distinct_original_name():
    adapter = CurrentAdapter()
    adapter.create_output = lambda parent_id, payload: "output"
    adapter.save_payload = lambda item_id, payload: None
    adapter.remove_file = lambda item_id, name: None

    output = Output(adapter, parent_id="input")
    output.add_file(content=b"data", name="stored.txt", original_name="source.csv")
    output.save()

    assert adapter.calls == [("output", "stored.txt", "source.csv", b"data")]


def test_release_normalization_supports_both_signature_generations():
    exception = {"type": "APPLICATION", "code": "E", "message": "failed"}
    current = CurrentAdapter()
    upstream = UpstreamAdapter()

    release_input(current, "item", State.FAILED, exception)
    release_input(upstream, "item", State.FAILED, exception)

    assert current.calls == [("item", State.FAILED, "APPLICATION", "E", "failed")]
    assert upstream.calls == [("item", State.FAILED, exception)]
