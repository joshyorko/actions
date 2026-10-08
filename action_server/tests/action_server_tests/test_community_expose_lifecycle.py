import json
from types import SimpleNamespace

import pytest

from actions.server import _community_expose_lifecycle as lifecycle
from actions.server._community_expose import (
    BoreProvider,
    CloudflareProvider,
    LocalhostRunProvider,
    TunnelInfo,
    TunnelProvider,
)


def test_provider_inventory_is_passive(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr(
        "actions.server._community_expose.download_bore",
        lambda: pytest.fail("inventory must not download bore"),
    )
    monkeypatch.setattr(
        "actions.server._community_expose.download_cloudflared",
        lambda: pytest.fail("inventory must not download cloudflared"),
    )

    inventory = lifecycle.providers()

    assert inventory == {
        "providers": [
            {"provider": "localhost.run", "available": False, "transport": "https"},
            {"provider": "bore", "available": False, "transport": "http"},
            {"provider": "cloudflare", "available": False, "transport": "https"},
        ]
    }


def test_provider_availability_checks_only_installed_executables(monkeypatch):
    checked = []
    monkeypatch.setattr("shutil.which", lambda name: checked.append(name) or None)

    assert LocalhostRunProvider().is_available() is False
    assert BoreProvider().is_available() is False
    assert CloudflareProvider().is_available() is False
    assert checked == ["ssh", "bore", "cloudflared"]


def test_expose_cli_providers_is_json_and_does_not_initialize_rcc(monkeypatch, capsys):
    monkeypatch.setattr(
        lifecycle,
        "providers",
        lambda: {"providers": [{"provider": "bore", "available": True}]},
    )
    monkeypatch.setattr(
        "actions.server._download_rcc.download_rcc",
        lambda: pytest.fail("expose providers must not initialize RCC"),
    )

    from actions.server._cli_impl import _main_retcode

    result = _main_retcode(["expose", "providers", "--json"])

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {
        "providers": [{"provider": "bore", "available": True}]
    }


def test_explicit_plain_http_provider_is_disabled(monkeypatch):
    monkeypatch.setenv("ACTIONS_HOME", "/tmp/expose-lifecycle-test")
    monkeypatch.setattr(
        lifecycle, "_read_state", lambda: pytest.fail("must reject before state")
    )

    with pytest.raises(ValueError, match="disabled"):
        lifecycle.start("bore", 8080)


def test_started_provider_is_reported_as_starting_until_edge_readiness(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("ACTIONS_HOME", str(tmp_path))
    fake_process = SimpleNamespace(pid=1234)
    tunnel = TunnelInfo(
        provider=TunnelProvider.CLOUDFLARE,
        public_url="https://example.trycloudflare.com",
        local_port=8080,
        process=fake_process,
    )

    class Manager:
        def __init__(self, **_kwargs):
            self.stopped = False

        async def start(self, _port, provider):
            assert provider is TunnelProvider.CLOUDFLARE
            return tunnel

        async def stop(self):
            self.stopped = True

    monkeypatch.setattr(lifecycle, "TunnelManager", Manager)
    monkeypatch.setattr(
        lifecycle.psutil,
        "Process",
        lambda _pid: SimpleNamespace(create_time=lambda: 10.0),
    )

    receipt = lifecycle.start("cloudflare", 8080)

    assert receipt["status"] == "starting"
    assert receipt["reason"] == "edge-readiness-not-verified"
    assert lifecycle.status()["status"] == "starting"


def test_stop_does_not_signal_a_pid_whose_start_identity_changed(monkeypatch, tmp_path):
    monkeypatch.setenv("ACTIONS_HOME", str(tmp_path))
    state = {
        "schema_version": 1,
        "status": "starting",
        "provider": "cloudflare",
        "pid": 1234,
        "process_created": 10.0,
    }
    state_path = tmp_path / lifecycle._STATE_NAME
    state_path.write_text(json.dumps(state), encoding="utf-8")
    state_path.chmod(0o600)

    class UnrelatedProcess:
        def create_time(self):
            return 11.0

        def terminate(self):
            pytest.fail("must not signal a reused pid")

    monkeypatch.setattr(lifecycle.psutil, "Process", lambda _pid: UnrelatedProcess())

    receipt = lifecycle.stop()

    assert receipt["status"] == "stale"
    assert (tmp_path / lifecycle._STATE_NAME).exists()


def test_stop_is_idempotent_and_signals_only_matching_owned_pid(monkeypatch, tmp_path):
    monkeypatch.setenv("ACTIONS_HOME", str(tmp_path))
    state = {
        "schema_version": 1,
        "status": "starting",
        "provider": "cloudflare",
        "pid": 1234,
        "process_created": 10.0,
    }
    state_path = tmp_path / lifecycle._STATE_NAME
    state_path.write_text(json.dumps(state), encoding="utf-8")
    state_path.chmod(0o600)

    class OwnedProcess:
        terminated = False

        def create_time(self):
            return 10.0

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            assert timeout == 5

    process = OwnedProcess()
    monkeypatch.setattr(lifecycle.psutil, "Process", lambda _pid: process)

    assert lifecycle.stop() == {"status": "stopped", "provider": "cloudflare"}
    assert process.terminated
    assert lifecycle.stop() == {"status": "stopped"}


def test_state_symlink_is_reported_failed_not_stopped(monkeypatch, tmp_path):
    monkeypatch.setenv("ACTIONS_HOME", str(tmp_path))
    target = tmp_path / "elsewhere"
    target.write_text("{}", encoding="utf-8")
    (tmp_path / lifecycle._STATE_NAME).symlink_to(target)

    assert lifecycle.status() == {
        "status": "failed",
        "reason": "state-path-unsafe",
    }
