"""Contract tests for the experimental Yorko HTTP adapter."""

from __future__ import annotations

import json

import pytest

from actions.work_items import ApplicationException, EmptyQueue, ExceptionType, State
from actions.work_items._adapters._yorko import YorkoAdapter


class FakeResponse:
    """Small deterministic response stand-in for adapter boundary tests."""

    def __init__(self, status_code=200, payload=None, content=b"", text=""):
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    """Records HTTP calls and consumes prearranged responses or exceptions."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def _request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def get(self, url, **kwargs):
        return self._request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._request("POST", url, **kwargs)

    def patch(self, url, **kwargs):
        return self._request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self._request("DELETE", url, **kwargs)


@pytest.fixture
def yorko_env(monkeypatch):
    monkeypatch.setenv("YORKO_API_URL", "https://control.example.test/")
    monkeypatch.setenv("YORKO_API_TOKEN", "secret-token")
    monkeypatch.setenv("YORKO_WORKSPACE_ID", "workspace-1")
    monkeypatch.setenv("YORKO_WORKER_ID", "worker-1")
    monkeypatch.setenv("YORKO_REQUEST_TIMEOUT", "17")


def adapter(yorko_env, *outcomes):
    return YorkoAdapter(session=FakeSession(outcomes))


def test_reserve_authenticates_and_returns_reserved_id(yorko_env):
    subject = adapter(yorko_env, FakeResponse(payload={"id": "input-1"}))

    assert subject.reserve_input() == "input-1"
    method, url, kwargs = subject.session.calls[0]
    assert (method, url) == (
        "GET",
        "https://control.example.test/api/v1/workspaces/workspace-1/work-items/next",
    )
    assert kwargs == {
        "headers": {"Authorization": "Bearer secret-token"},
        "params": {"worker_id": "worker-1"},
        "timeout": 17.0,
    }


def test_reserve_empty_response_raises_empty_queue(yorko_env):
    subject = adapter(yorko_env, FakeResponse(payload={}))

    with pytest.raises(EmptyQueue):
        subject.reserve_input()


def test_release_creates_expected_completion_and_failure_payloads(yorko_env):
    subject = adapter(yorko_env, FakeResponse(), FakeResponse())

    subject.release_input("input-1", State.DONE)
    subject.release_input(
        "input-2",
        State.FAILED,
        exception_type=ExceptionType.APPLICATION,
        code="E_TIMEOUT",
        message="upstream timed out",
    )

    assert subject.session.calls == [
        (
            "POST",
            "https://control.example.test/api/v1/workspaces/workspace-1/work-items/input-1/complete",
            {
                "headers": {"Authorization": "Bearer secret-token"},
                "json": {"worker_id": "worker-1", "output_data": {}},
                "timeout": 17.0,
            },
        ),
        (
            "POST",
            "https://control.example.test/api/v1/workspaces/workspace-1/work-items/input-2/fail",
            {
                "headers": {"Authorization": "Bearer secret-token"},
                "json": {
                    "worker_id": "worker-1",
                    "error_message": "upstream timed out",
                    "exception_data": {
                        "type": "APPLICATION",
                        "code": "E_TIMEOUT",
                        "message": "upstream timed out",
                    },
                },
                "timeout": 17.0,
            },
        ),
    ]


def test_create_output_and_payload_operations_use_expected_payloads(yorko_env):
    subject = adapter(
        yorko_env,
        FakeResponse(payload={"id": "output-1"}),
        FakeResponse(payload={"payload": {"source": "input"}}),
        FakeResponse(),
    )

    assert subject.create_output("input-1", {"result": True}) == "output-1"
    assert subject.load_payload("input-1") == {"source": "input"}
    subject.save_payload("input-1", ["saved"])

    assert [call[2].get("json") for call in subject.session.calls] == [
        {"name": "Output from input-1", "parent_id": "input-1", "payload": {"result": True}},
        None,
        {"payload": ["saved"]},
    ]


def test_file_operations_preserve_binary_content_and_original_name(yorko_env):
    subject = adapter(
        yorko_env,
        FakeResponse(payload={"files": [{"name": "report.csv"}]}),
        FakeResponse(content=b"csv-bytes"),
        FakeResponse(),
        FakeResponse(),
    )

    assert subject.list_files("input-1") == ["report.csv"]
    assert subject.get_file("input-1", "report.csv") == b"csv-bytes"
    subject.add_file("input-1", "report.csv", "source.csv", b"csv-bytes")
    subject.remove_file("input-1", "report.csv")

    assert subject.session.calls[2][2] == {
        "files": {"file": ("source.csv", b"csv-bytes")},
        "headers": {"Authorization": "Bearer secret-token"},
        "params": {"name": "report.csv"},
        "timeout": 17.0,
    }


def test_malformed_success_response_raises_redacted_application_error(yorko_env):
    subject = adapter(yorko_env, FakeResponse(payload=json.JSONDecodeError("bad", "{", 1)))

    with pytest.raises(ApplicationException, match="invalid JSON") as error:
        subject.reserve_input()

    assert "secret-token" not in str(error.value)


def test_malformed_file_metadata_raises_application_error(yorko_env):
    subject = adapter(yorko_env, FakeResponse(payload={"files": [{"id": "file-1"}]}))

    with pytest.raises(ApplicationException, match="malformed file metadata"):
        subject.list_files("input-1")


def test_timeout_error_is_redacted(yorko_env):
    subject = adapter(yorko_env, TimeoutError("https://control.example.test/?token=secret-token"))

    with pytest.raises(ApplicationException, match="timed out") as error:
        subject.reserve_input()

    assert "secret-token" not in str(error.value)


def test_http_error_is_redacted(yorko_env):
    subject = adapter(yorko_env, FakeResponse(status_code=401, text="token=secret-token"))

    with pytest.raises(ApplicationException, match="HTTP 401") as error:
        subject.reserve_input()

    assert "secret-token" not in str(error.value)
