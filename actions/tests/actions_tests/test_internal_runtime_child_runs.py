"""Contract tests for Runtime-injected delegated child Run operations."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from actions.internal_runtime import (
    ChildResultReference,
    ChildRunContractError,
    ChildRunHandle,
    ChildRunState,
    ChildRunStatus,
    ChildRunUnavailable,
    cancel_child_run,
    child_run_status,
    submit_child_run,
)
from actions.internal_runtime._context import install_runtime_transport
from actions.internal_runtime._models import MAX_RESULT_REFERENCE_COUNT


class _Transport:
    def __init__(self):
        self.requests = []
        self.state = ChildRunState.PENDING
        self.references = ()
        self.handle = None

    def submit_child_run(self, binding_name, invocation_key, canonical_inputs):
        self.requests.append((binding_name, invocation_key, canonical_inputs))
        self.handle = ChildRunHandle(str(uuid4()))
        return self.handle

    def child_run_status(self, handle):
        self.requests.append(("status", handle.id))
        return ChildRunStatus(handle, self.state, self.references)

    def cancel_child_run(self, handle):
        self.requests.append(("cancel", handle.id))
        self.state = ChildRunState.CANCEL_PENDING
        return ChildRunStatus(handle, self.state, self.references)


def test_client_is_unavailable_without_runtime_injection():
    with pytest.raises(ChildRunUnavailable, match="unavailable"):
        submit_child_run("billing", key="invoice-42", inputs={"amount": 12})


def test_submit_status_cancel_use_only_typed_child_contract():
    transport = _Transport()
    reference = ChildResultReference(
        handle="result-opaque-1",
        name="summary.json",
        media_type="application/json",
        size_bytes=128,
        digest="sha256:" + "a" * 64,
    )
    transport.references = (reference,)
    original = {"amount": 12, "memo": "renewal"}
    with install_runtime_transport(transport):
        handle = submit_child_run("billing", key="invoice-42", inputs=original)
        original["amount"] = 99

        assert child_run_status(handle) == ChildRunStatus(
            handle, ChildRunState.PENDING, (reference,)
        )
        cancelled = cancel_child_run(handle)
        transport.state = ChildRunState.CANCELLED
        terminal = child_run_status(handle)

    assert cancelled == ChildRunStatus(
        handle, ChildRunState.CANCEL_PENDING, (reference,)
    )
    assert cancelled.state is not ChildRunState.CANCELLED
    assert terminal == ChildRunStatus(handle, ChildRunState.CANCELLED, (reference,))
    assert transport.requests[0] == (
        "billing",
        "invoice-42",
        '{"amount":12,"memo":"renewal"}',
    )
    assert transport.requests[1] == ("status", handle.id)
    assert transport.requests[2] == ("cancel", handle.id)
    assert transport.requests[3] == ("status", handle.id)
    assert tuple(ChildRunHandle.__dataclass_fields__) == ("id",)
    assert tuple(ChildRunStatus.__dataclass_fields__) == (
        "handle",
        "state",
        "result_references",
    )
    assert tuple(ChildResultReference.__dataclass_fields__) == (
        "handle",
        "name",
        "media_type",
        "size_bytes",
        "digest",
    )
    with pytest.raises(FrozenInstanceError):
        handle.id = str(uuid4())


@pytest.mark.parametrize(
    ("binding", "key", "inputs"),
    [
        ("../private", "key-1", {}),
        ("billing", "bad key", {}),
        ("billing", "key-1", {1: "non-string key"}),
        ("billing", "key-1", {"value": object()}),
        ("billing", "key-1", {"value": float("inf")}),
        ("billing", "key-1", {"value": "x" * (256 * 1024)}),
    ],
)
def test_submit_rejects_malformed_or_unbounded_calls(binding, key, inputs):
    transport = _Transport()
    with install_runtime_transport(transport):
        with pytest.raises(ChildRunContractError):
            submit_child_run(binding, key=key, inputs=inputs)
    assert transport.requests == []


def test_submit_rejects_excessive_json_depth():
    nested = 0
    for _ in range(40):
        nested = [nested]
    transport = _Transport()
    with install_runtime_transport(transport):
        with pytest.raises(ChildRunContractError, match="structural bounds"):
            submit_child_run("billing", key="key-1", inputs={"nested": nested})
    assert transport.requests == []


def test_child_handle_and_runtime_state_are_validated():
    with pytest.raises(ValueError, match="canonical child handle"):
        ChildRunHandle("not-a-run-id")

    class BadStateTransport(_Transport):
        def child_run_status(self, handle):
            return "unknown-state"

    handle = ChildRunHandle(str(uuid4()))
    with install_runtime_transport(BadStateTransport()):
        with pytest.raises(ChildRunUnavailable, match="invalid child Run status"):
            child_run_status(handle)


@pytest.mark.parametrize(
    "references",
    [
        tuple(
            ChildResultReference(
                f"result-{index}", "out.json", "application/json", 1
            )
            for index in range(MAX_RESULT_REFERENCE_COUNT + 1)
        ),
        tuple(
            ChildResultReference(
                f"result-{index}",
                "n" * 256,
                "a" * 63 + "/" + "b" * 64,
                1,
                "sha256:" + "a" * 64,
            )
            for index in range(MAX_RESULT_REFERENCE_COUNT)
        ),
    ],
)
def test_child_status_rejects_unbounded_result_references(references):
    handle = ChildRunHandle(str(uuid4()))
    with pytest.raises(ValueError):
        ChildRunStatus(handle, ChildRunState.SUCCEEDED, references)


def test_status_rejects_a_host_response_for_another_handle():
    class MismatchedTransport(_Transport):
        def child_run_status(self, handle):
            return ChildRunStatus(ChildRunHandle(str(uuid4())), ChildRunState.PENDING)

    handle = ChildRunHandle(str(uuid4()))
    with install_runtime_transport(MismatchedTransport()):
        with pytest.raises(ChildRunUnavailable, match="invalid child Run status"):
            child_run_status(handle)


def test_runtime_transport_cannot_be_nested_and_client_has_no_wait_api():
    transport = _Transport()
    with install_runtime_transport(transport):
        with pytest.raises(RuntimeError, match="nested"):
            with install_runtime_transport(_Transport()):
                pass
    assert not hasattr(
        __import__("actions.internal_runtime", fromlist=["internal_runtime"]),
        "wait",
    )
