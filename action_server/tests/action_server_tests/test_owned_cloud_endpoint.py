"""Legacy cloud compatibility requires an explicit operator endpoint."""
from types import SimpleNamespace

import pytest

from actions.server import _storage
from actions.server._errors_action_server import ActionServerValidationError


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.mark.parametrize(
    "stored",
    [
        None,
        SimpleNamespace(cloud=SimpleNamespace(hostname="")),
        SimpleNamespace(cloud=SimpleNamespace(hostname="   ")),
    ],
)
def test_missing_cloud_endpoint_has_no_vendor_fallback(monkeypatch, stored):
    monkeypatch.setattr(_storage, "load_storage", lambda: stored)
    with pytest.raises(ActionServerValidationError, match="explicit"):
        _storage.get_hostname()


def test_existing_explicit_endpoint_is_preserved(monkeypatch):
    monkeypatch.setattr(
        _storage,
        "load_storage",
        lambda: SimpleNamespace(
            cloud=SimpleNamespace(hostname="https://owned.invalid")
        ),
    )
    assert _storage.get_hostname() == "https://owned.invalid"


def test_prompt_requires_endpoint_without_default(monkeypatch):
    from actions.server._ask_user import ask_user_for_hostname

    monkeypatch.setattr(_storage, "load_storage", lambda: None)
    replies = iter(["", "https://owned.invalid"])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    assert ask_user_for_hostname() == "https://owned.invalid"


def test_cloud_list_without_endpoint_never_requests(monkeypatch):
    import actions_http

    from actions.server._actions_cloud import handle_list_organizations_command

    monkeypatch.setattr(_storage, "load_storage", lambda: None)

    def forbidden(*args, **kwargs):
        raise AssertionError("cloud request without explicit endpoint")

    monkeypatch.setattr(actions_http, "get", forbidden)
    args = SimpleNamespace(
        access_credentials="synthetic:nonsecret", hostname=None, json=True
    )
    assert handle_list_organizations_command(args) == 1
