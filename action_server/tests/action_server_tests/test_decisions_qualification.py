"""Independent qualification of decision replay and failure retention."""

import pytest
from action_server_tests import test_decisions as fixtures
from action_server_tests.test_decisions import composed, request

from actions.server.decisions.openai import ProviderFailure
from actions.server.decisions.service import DecisionService
from actions.server.foundry.models import FoundryRequest

reviewed = fixtures.reviewed
provider = fixtures.provider


def test_exact_input_replay_and_changed_delivery(reviewed):
    _, _, _, _, actor, scope, handle, _ = reviewed
    service, stub = composed(reviewed)
    first = service.evaluate(actor, scope, handle, request(), "delivery-a")
    restarted = DecisionService(service.reviews, service.bindings)
    assert restarted.evaluate(actor, scope, handle, request(), "delivery-b") == first
    with pytest.raises(ProviderFailure, match="changed_input"):
        restarted.evaluate(
            actor,
            scope,
            handle,
            request().model_copy(update={"evidence": "different"}),
            "delivery-a",
        )
    assert stub.calls == 1


def test_provider_exception_is_sanitized_in_exception_and_retained_record(reviewed):
    db, _, _, _, actor, scope, handle, _ = reviewed
    service, stub = composed(reviewed)
    marker = "sensitive-provider-message-363"

    def fail():
        raise RuntimeError(marker)

    stub.hook = fail
    for delivery in ("first", "second"):
        with pytest.raises(ProviderFailure) as error:
            service.evaluate(actor, scope, handle, request(), delivery)
        assert str(error.value) == "provider_unavailable"
        assert marker not in str(error.value)
    rows = db.all(FoundryRequest, where="operation=?", values=["decisions/v1"])
    assert len(rows) == 1
    assert marker not in rows[0].result_json
    assert stub.calls == 1
