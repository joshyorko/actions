"""Public bundle defaults cannot replace an operator's OAuth registration."""

import importlib
import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


@pytest.mark.parametrize("module_name", ["_common", "vendored_deps"])
@pytest.mark.parametrize("client_id", ["", " \t\n"])
def test_custom_registration_rejects_blank_client_id(tmp_path, module_name, client_id):
    settings = importlib.import_module(f"actions.server.{module_name}.oauth2_settings")
    path = tmp_path / "private.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "oauth2Config": {
                    "providers": {
                        "google": {
                            "mode": "custom",
                            "clientId": client_id,
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="nonblank.*clientId"):
        settings.get_oauthlib2_provider_settings("google", str(path))


def test_default_config_creation_is_private_and_preserves_existing(
    tmp_path, monkeypatch
):
    from actions.server._oauth2 import (
        USER_CONFIG_FILE_NAME,
        print_user_oauth2_config_path,
    )

    monkeypatch.setattr(
        "actions.server._settings.get_default_settings_dir", lambda: tmp_path
    )
    monkeypatch.setitem(
        sys.modules,
        "actions.server._oauth2_config",
        SimpleNamespace(
            FILE_CONTENTS={"default_user_config": "oauth2Config:\n  providers: {}\n"}
        ),
    )
    previous_umask = os.umask(0)
    try:
        assert print_user_oauth2_config_path() == 0
    finally:
        os.umask(previous_umask)
    path = tmp_path / USER_CONFIG_FILE_NAME
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    private = b"operator-owned configuration\n"
    path.write_bytes(private)
    assert print_user_oauth2_config_path() == 0
    assert path.read_bytes() == private


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink fixture")
def test_default_config_refuses_symlink(tmp_path, monkeypatch):
    from actions.server._oauth2 import (
        USER_CONFIG_FILE_NAME,
        print_user_oauth2_config_path,
    )

    monkeypatch.setattr(
        "actions.server._settings.get_default_settings_dir", lambda: tmp_path
    )
    target = tmp_path / "target"
    target.write_bytes(b"private\n")
    (tmp_path / USER_CONFIG_FILE_NAME).symlink_to(target)
    assert print_user_oauth2_config_path() == 1
    assert target.read_bytes() == b"private\n"


def test_community_catalog_rejects_hosted_registration(tmp_path, monkeypatch):
    from actions.server.vendored_deps.oauth2_settings import (
        get_oauthlib2_provider_settings,
    )

    # Source-only suites need no pre-existing generated build module.
    catalog = Path(__file__).resolve().parents[2] / "oauth2/actions-oauth-config.yaml"
    monkeypatch.setattr(
        "actions.server._oauth2.get_actions_provided_oauth2_config",
        lambda: catalog.read_text(encoding="utf-8"),
    )
    path = tmp_path / "operator.yaml"
    path.write_text(
        "oauth2Config:\n  providers:\n    google:\n      mode: actions\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="unsupported provider.*custom"):
        get_oauthlib2_provider_settings("google", str(path))


@pytest.mark.parametrize("client_secret", [None, "test-issuer-secret"])
def test_custom_oauth_exchanges_with_owned_issuer(tmp_path, monkeypatch, client_secret):
    """Exercise requests-oauthlib and a real local token endpoint, without credentials."""
    import base64
    import hashlib
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs, urlsplit

    from actions.server._api_oauth2 import _create_oauth2_session

    received = []

    class Issuer(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append(parse_qs(body.decode()))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"access_token": "test-issuer-token", "token_type": "Bearer"}
                ).encode()
            )

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Issuer)
    server.timeout = 5
    reader = threading.Thread(target=server.handle_request)
    reader.start()
    try:
        origin = f"http://127.0.0.1:{server.server_port}"
        provider = {
            "mode": "custom",
            "clientId": "test-issuer-client",
            "authorizationEndpoint": origin + "/authorize",
            "tokenEndpoint": origin + "/token",
        }
        if client_secret:
            provider["clientSecret"] = client_secret
        path = tmp_path / "operator.yaml"
        path.write_text(
            yaml.safe_dump({"oauth2Config": {"providers": {"owned-issuer": provider}}}),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "actions.server._settings.get_settings",
            lambda: SimpleNamespace(
                base_url=origin, oauth2_settings=str(path), use_https=False
            ),
        )
        session = _create_oauth2_session("owned-issuer")
        url, state = session.authorization_url(provider["authorizationEndpoint"])
        authorization = parse_qs(urlsplit(url).query)
        assert authorization["client_id"] == ["test-issuer-client"]
        assert authorization["redirect_uri"] == [origin + "/actions/oauth2/"]
        assert authorization["state"] == [state]
        if client_secret is None:
            assert authorization["code_challenge_method"] == ["S256"]
            expected = (
                base64.urlsafe_b64encode(
                    hashlib.sha256(session._code_verifier.encode()).digest()
                )
                .decode()
                .rstrip("=")
            )
            assert authorization["code_challenge"] == [expected]
        else:
            assert "code_challenge" not in authorization
        token = session.fetch_token(
            provider["tokenEndpoint"],
            authorization_response=origin
            + "/actions/oauth2/?code=owned-code&state="
            + state,
            client_secret=client_secret,
            include_client_id=True,
            timeout=3,
        )
        assert token["access_token"] == "test-issuer-token"
        assert received[0]["client_id"] == ["test-issuer-client"]
        assert received[0]["code"] == ["owned-code"]
        if client_secret is None:
            assert received[0]["code_verifier"] == [session._code_verifier]
        else:
            assert received[0]["client_secret"] == [client_secret]
    finally:
        reader.join(6)
        server.server_close()
        assert not reader.is_alive()
