"""Offline failure and egress-gate coverage for the hosted provider."""

import pytest
from action_server_tests.test_decisions import request

from actions.server.decisions.openai import (
    HostedPolicy,
    OpenAIDecisionsProvider,
    ProviderFailure,
)


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


def test_live_smoke_disabled_before_secret_access(monkeypatch):
    from action_server_tests.test_decisions_openai_live import (
        test_one_synthetic_hosted_decision,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("disabled live smoke accessed secrets or network")

    monkeypatch.delenv("DECISIONS_OPENAI_LIVE", raising=False)
    monkeypatch.setattr("pathlib.Path.read_text", forbidden)
    monkeypatch.setattr("requests.Session.post", forbidden)
    with pytest.raises(pytest.skip.Exception):
        test_one_synthetic_hosted_decision()


def test_native_provider_scopes_project_without_global_patches(monkeypatch):
    import json

    from action_server_tests.test_decisions import response

    class Reply:
        status_code = 200
        headers = {"x-request-id": "synthetic-request"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_content(self, size):
            for byte in json.dumps(response()).encode():
                yield bytes([byte])

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            assert kwargs["headers"]["OpenAI-Project"] == "proj_synthetic"
            assert self.trust_env is False
            return Reply()

    monkeypatch.setattr("actions.server.decisions.openai.requests.Session", Session)
    result = OpenAIDecisionsProvider(
        HostedPolicy(enabled=True, secret_ref="synthetic", project_id="proj_synthetic"),
        lambda _: "synthetic-not-a-key",
    ).evaluate(request())
    assert result.request_id == "synthetic-request"


def test_project_change_changes_protected_provider_identity():
    first = OpenAIDecisionsProvider(
        HostedPolicy(secret_ref="fresh-key", project_id="proj_first"), lambda _: None
    )
    second = OpenAIDecisionsProvider(
        HostedPolicy(secret_ref="fresh-key", project_id="proj_second"), lambda _: None
    )
    rotated = OpenAIDecisionsProvider(
        HostedPolicy(secret_ref="rotated-key", project_id="proj_first"), lambda _: None
    )
    assert first.identity != second.identity
    assert first.identity == rotated.identity
    assert len(first.identity) <= 128
