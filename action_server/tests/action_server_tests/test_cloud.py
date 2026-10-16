import json
from contextlib import nullcontext


def test_cloud_list_organizations_uses_cli_http_contract(monkeypatch, capsysbinary):
    import actions_http

    from actions.server import _download_rcc, _rcc
    from actions.server.cli import main
    from actions.server.package._package_publish_api import HMACPayload, calculate_hmac

    requests = []
    response_payload = {
        "data": [{"id": "org-123", "name": "Local Test Org"}],
        "has_more": False,
        "next": None,
    }

    class Response:
        @staticmethod
        def ok():
            return True

        @staticmethod
        def json():
            return response_payload

    def fake_get(url, *, headers):
        requests.append((url, headers))
        return Response()

    monkeypatch.setattr(actions_http, "get", fake_get)
    # Cloud subcommands do not need RCC. Keep this contract test deterministic
    # and independent from RCC download or initialization.
    monkeypatch.setattr(_download_rcc, "download_rcc", lambda **_kwargs: None)
    monkeypatch.setattr(_rcc, "initialize_rcc_actions", lambda *_args: nullcontext())
    monkeypatch.setattr(_rcc, "initialize_rcc_robots", lambda *_args: nullcontext())

    access_credentials = "local-test-key:local-test-secret"
    exit_code = main(
        [
            "cloud",
            "list-organizations",
            "--access-credentials",
            access_credentials,
            "--hostname",
            "https://control-room.invalid",
            "--json",
        ],
        exit=False,
    )
    output = capsysbinary.readouterr().out.decode("utf-8")

    assert exit_code == 0
    assert len(requests) == 1
    url, headers = requests[0]
    assert url == "https://control-room.invalid/api/v1/organizations"
    timestamp = headers["authorization-timestamp"]
    expected_signature = calculate_hmac(
        HMACPayload(
            body="{}",
            path="/api/v1/organizations",
            timestamp=timestamp,
            http_method="GET",
            content_type="application/json",
        ),
        "local-test-secret",
    )
    assert headers["Authorization"] == (
        f"Sema4UserHMAC local-test-key {expected_signature}"
    )
    assert json.loads(output) == response_payload["data"]
    assert "local-test-secret" not in output
