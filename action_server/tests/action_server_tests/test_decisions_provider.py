"""Offline failure and egress-gate coverage for the hosted provider."""

import pytest

from actions.server.decisions.openai import (
    HostedPolicy,
    OpenAIDecisionsProvider,
    ProviderFailure,
)
from action_server_tests.test_decisions import request


def test_disabled_provider_never_resolves_key_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network accessed while disabled")

    monkeypatch.setattr("requests.Session.post", forbidden)
    provider = OpenAIDecisionsProvider(
        HostedPolicy(secret_ref="key"),
        lambda _: (_ for _ in ()).throw(AssertionError("key accessed")),
    )
    with pytest.raises(ProviderFailure, match="egress_disabled"):
        provider.evaluate(request())


def test_enabled_provider_rejects_oversized_input_before_key_lookup():
    lookups = []
    provider = OpenAIDecisionsProvider(
        HostedPolicy(enabled=True, secret_ref="key", max_input_bytes=1),
        lambda ref: lookups.append(ref),
    )
    with pytest.raises(ProviderFailure, match="input_budget_exceeded"):
        provider.evaluate(request())
    assert lookups == []
