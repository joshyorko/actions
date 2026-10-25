import pytest

from actions.agent._client import AgentApiClientException, _AgentAPIClient


@pytest.fixture
def isolated(monkeypatch):
    monkeypatch.delenv("ACTIONS_AGENTS_SERVICE_URL", raising=False)
    monkeypatch.delenv("SEMA4AI_AGENTS_SERVICE_URL", raising=False)

    def forbidden(*args, **kwargs):
        pytest.fail("Implicit PID discovery is forbidden")

    monkeypatch.setattr(_AgentAPIClient, "_try_get_url_from_pid_file", forbidden)
    return monkeypatch


def test_missing_endpoint_fails_before_network(isolated):
    def forbidden(*args):
        pytest.fail("No configured endpoint must mean no probe")

    isolated.setattr(_AgentAPIClient, "_is_url_accessible", forbidden)
    with pytest.raises(AgentApiClientException, match="ACTIONS_AGENTS_SERVICE_URL"):
        _AgentAPIClient()


@pytest.mark.parametrize(
    "owned,legacy,expected",
    [
        ("https://owned.example", "https://legacy.example", "https://owned.example"),
        (None, "https://legacy.example", "https://legacy.example"),
    ],
)
def test_explicit_endpoint_precedence(isolated, owned, legacy, expected):
    if owned is not None:
        isolated.setenv("ACTIONS_AGENTS_SERVICE_URL", owned)
    isolated.setenv("SEMA4AI_AGENTS_SERVICE_URL", legacy)
    calls = []
    isolated.setattr(
        _AgentAPIClient,
        "_is_url_accessible",
        lambda self, url: calls.append(url) or True,
    )
    assert _AgentAPIClient().api_url == expected + "/api/v2/"
    assert calls == [expected + "/api/v2/ok"]


def test_failed_explicit_endpoint_does_not_fall_back(isolated):
    isolated.setenv("ACTIONS_AGENTS_SERVICE_URL", "https://owned.example")
    isolated.setenv("SEMA4AI_AGENTS_SERVICE_URL", "https://legacy.example")
    calls = []
    isolated.setattr(
        _AgentAPIClient,
        "_is_url_accessible",
        lambda self, url: calls.append(url) or False,
    )
    with pytest.raises(AgentApiClientException):
        _AgentAPIClient()
    assert calls == ["https://owned.example/api/v2/ok"]


def test_empty_owned_configuration_does_not_select_legacy(isolated):
    isolated.setenv("ACTIONS_AGENTS_SERVICE_URL", "")
    isolated.setenv("SEMA4AI_AGENTS_SERVICE_URL", "https://legacy.example")
    isolated.setattr(
        _AgentAPIClient,
        "_is_url_accessible",
        lambda *args: pytest.fail("Unexpected probe"),
    )
    with pytest.raises(AgentApiClientException):
        _AgentAPIClient()
