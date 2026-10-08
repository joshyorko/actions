import asyncio
import subprocess
from types import SimpleNamespace

import pytest

from actions.server._community_expose import (
    BaseTunnelProvider,
    TunnelInfo,
    TunnelManager,
    TunnelProvider,
    CloudflareProvider,
    LocalhostRunProvider,
    _stop_process,
)
from actions.server._server import (
    _community_expose_lifespan,
    _start_community_expose_impl,
)


class _FakeProvider(BaseTunnelProvider):
    def __init__(self, provider, *, failure=None):
        self._name = provider
        self.failure = failure
        self.started_ports = []
        self.stopped_tunnels = []

    @property
    def name(self):
        return self._name

    def is_available(self):
        return True

    async def start(self, port):
        self.started_ports.append(port)
        if self.failure:
            raise self.failure
        return TunnelInfo(self.name, f"https://{self.name.value}.test", port)

    async def stop(self, tunnel):
        self.stopped_tunnels.append(tunnel)


def test_tunnel_manager_selects_public_provider_and_cleans_up():
    provider = _FakeProvider(TunnelProvider.CLOUDFLARE)
    manager = TunnelManager(preferred_provider=TunnelProvider.CLOUDFLARE)
    manager._providers = [provider]

    tunnel = asyncio.run(manager.start(8080))
    asyncio.run(manager.stop())

    assert tunnel.public_url == "https://cloudflare.test"
    assert provider.started_ports == [8080]
    assert provider.stopped_tunnels == [tunnel]
    assert not manager.is_active


def test_tunnel_manager_falls_back_after_provider_start_failure():
    failed = _FakeProvider(
        TunnelProvider.LOCALHOST_RUN, failure=RuntimeError("offline")
    )
    working = _FakeProvider(TunnelProvider.CLOUDFLARE)
    manager = TunnelManager()
    manager._providers = [failed, working]

    tunnel = asyncio.run(manager.start(8080))

    assert tunnel.provider is TunnelProvider.CLOUDFLARE
    assert failed.started_ports == [8080]
    assert working.started_ports == [8080]


def test_automatic_provider_selection_never_falls_back_to_plain_http():
    failed_https = _FakeProvider(
        TunnelProvider.LOCALHOST_RUN, failure=RuntimeError("offline")
    )
    bore = _FakeProvider(TunnelProvider.BORE)
    manager = TunnelManager()
    manager._providers = [failed_https, bore]

    with pytest.raises(RuntimeError, match="All tunnel providers failed"):
        asyncio.run(manager.start(8080))

    assert failed_https.started_ports == [8080]
    assert bore.started_ports == []


def test_owned_process_stop_escalates_and_does_not_signal_twice():
    class Process:
        running = True
        terminated = 0
        killed = 0
        waited = 0

        def poll(self):
            return None if self.running else 0

        def terminate(self):
            self.terminated += 1

        def wait(self, timeout):
            self.waited += 1
            if self.waited == 1:
                raise subprocess.TimeoutExpired("provider", timeout)
            return_code = 0
            self.running = False
            return return_code

        def kill(self):
            self.killed += 1

    process = Process()

    _stop_process(process)
    _stop_process(process)

    assert process.terminated == 1
    assert process.killed == 1
    assert process.waited == 2


def test_cloudflare_configured_tunnel_requires_public_https_url(monkeypatch):
    class Process:
        pid = 1234
        returncode = None
        terminated = False

        def poll(self):
            return self.returncode

        def terminate(self):
            self.terminated = True
            self.returncode = 0

        def wait(self, timeout):
            return self.returncode

    process = Process()
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/cloudflared")
    monkeypatch.setattr("subprocess.Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setenv("CLOUDFLARE_TUNNEL_TOKEN", "synthetic-secret")
    monkeypatch.delenv("CLOUDFLARE_TUNNEL_URL", raising=False)

    with pytest.raises(RuntimeError, match="URL is invalid") as error:
        asyncio.run(CloudflareProvider().start(8080))

    assert process.terminated
    assert "synthetic-secret" not in str(error.value)


@pytest.mark.parametrize(
    "provider_name",
    ["localhost.run", "bore", "cloudflare"],
)
def test_provider_reaps_owned_process_when_url_wait_fails(monkeypatch, provider_name):
    from actions.server._community_expose import (
        BoreProvider,
        CloudflareProvider,
        LocalhostRunProvider,
    )

    provider = {
        "localhost.run": LocalhostRunProvider,
        "bore": BoreProvider,
        "cloudflare": CloudflareProvider,
    }[provider_name]()
    if provider_name == "bore":
        provider._bore_path = "bore"
    elif provider_name == "cloudflare":
        provider._cloudflared_path = "cloudflared"
        monkeypatch.delenv("CLOUDFLARE_TUNNEL_TOKEN", raising=False)

    class OwnedProcess:
        terminated = False
        returncode = None

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            assert timeout == 5

    process = OwnedProcess()
    monkeypatch.setattr(
        "actions.server._community_expose.subprocess.Popen", lambda *_a, **_k: process
    )

    async def fail_wait(*_args, **_kwargs):
        raise TimeoutError("startup timeout")

    monkeypatch.setattr(provider, "_wait_for_url", fail_wait)
    with pytest.raises(TimeoutError, match="startup timeout"):
        asyncio.run(provider.start(8080))
    assert process.terminated


def test_localhost_run_requires_existing_trusted_ssh_host_key(monkeypatch):
    captured = {}

    class Process:
        pid = 1234

    process = Process()

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return process

    provider = LocalhostRunProvider()
    monkeypatch.setattr("actions.server._community_expose.subprocess.Popen", fake_popen)
    monkeypatch.setattr(
        provider,
        "_wait_for_url",
        lambda _process: asyncio.sleep(0, result="https://t.lhr.life"),
    )

    asyncio.run(provider.start(8080))

    command = captured["command"]
    assert "StrictHostKeyChecking=yes" in command
    assert "StrictHostKeyChecking=no" not in command
    assert "BatchMode=yes" in command
    assert "UserKnownHostsFile" not in " ".join(command)


def test_cloudflare_token_is_passed_through_child_environment(monkeypatch, caplog):
    captured = {}

    class Process:
        pid = 1234

        def poll(self):
            return None

    process = Process()

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return process

    monkeypatch.setenv("CLOUDFLARE_TUNNEL_TOKEN", "synthetic-secret")
    monkeypatch.setenv("CLOUDFLARE_TUNNEL_URL", "https://runtime.example.test")
    monkeypatch.setenv("TUNNEL_TOKEN", "inherited-override")
    monkeypatch.setattr("actions.server._community_expose.subprocess.Popen", fake_popen)
    provider = CloudflareProvider()
    provider._cloudflared_path = "cloudflared"

    asyncio.run(provider.start(8080))

    assert "synthetic-secret" not in captured["command"]
    assert "inherited-override" not in captured["env"].values()
    assert captured["env"]["TUNNEL_TOKEN"] == "synthetic-secret"
    assert "CLOUDFLARE_TUNNEL_TOKEN" not in captured["env"]
    assert "synthetic-secret" not in caplog.text


def test_cloudflare_pipe_reader_does_not_depend_on_select(monkeypatch):
    class Stream:
        def __init__(self, lines):
            self.lines = iter(lines)

        def readline(self):
            return next(self.lines, "")

    class Process:
        stdout = Stream([])
        stderr = Stream(["Quick Tunnel is ready! https://sample.trycloudflare.com\n"])

        def poll(self):
            return None

    import select

    monkeypatch.setattr(
        select,
        "select",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("Windows pipe")),
    )

    result = asyncio.run(CloudflareProvider()._wait_for_url(Process(), timeout=0.2))

    assert result == "https://sample.trycloudflare.com"


def test_cloudflare_reader_timeout_reaps_process_and_unblocks_pipes(monkeypatch):
    import threading

    class BlockingStream:
        def __init__(self):
            self.closed = False
            self.release = threading.Event()

        def readline(self):
            self.release.wait()
            return ""

        def close(self):
            self.closed = True
            self.release.set()

    class Process:
        pid = 1234

        def __init__(self):
            self.stdout = BlockingStream()
            self.stderr = BlockingStream()
            self.running = True

        def poll(self):
            return None if self.running else 0

        def terminate(self):
            self.running = False

        def wait(self, timeout):
            return 0

    process = Process()
    monkeypatch.setattr(
        "actions.server._community_expose.subprocess.Popen",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.delenv("CLOUDFLARE_TUNNEL_TOKEN", raising=False)
    provider = CloudflareProvider()
    provider._cloudflared_path = "cloudflared"
    original_wait = provider._wait_for_url

    async def short_wait(owned_process):
        return await original_wait(owned_process, timeout=0.02)

    monkeypatch.setattr(provider, "_wait_for_url", short_wait)
    with pytest.raises(TimeoutError):
        asyncio.run(provider.start(8080))

    assert not process.running
    assert process.stdout.closed and process.stderr.closed


def test_server_expose_suppresses_all_provider_failure_without_active_tunnel(
    monkeypatch, caplog
):
    failed = _FakeProvider(
        TunnelProvider.LOCALHOST_RUN, failure=RuntimeError("offline")
    )
    failed_again = _FakeProvider(TunnelProvider.BORE, failure=RuntimeError("blocked"))
    manager = TunnelManager()
    manager._providers = [failed, failed_again]

    monkeypatch.setattr(
        "actions.server._community_expose.TunnelManager", lambda **_: manager
    )

    with caplog.at_level("ERROR"):
        result = asyncio.run(
            _start_community_expose_impl(
                8080, SimpleNamespace(expose_provider="auto"), None
            )
        )

    assert result is manager
    assert not manager.is_active
    assert "Failed to start tunnel (RuntimeError)." in caplog.text
    assert "offline" not in caplog.text


def test_legacy_expose_refuses_bore_even_when_selected(monkeypatch, caplog):
    manager = TunnelManager(preferred_provider=TunnelProvider.BORE)
    provider = _FakeProvider(TunnelProvider.BORE)
    manager._providers = [provider]
    monkeypatch.setattr(
        "actions.server._community_expose.TunnelManager", lambda **_: manager
    )

    result = asyncio.run(
        _start_community_expose_impl(
            8080, SimpleNamespace(expose_provider="bore"), "configured-key"
        )
    )

    assert result is manager
    assert provider.started_ports == []
    assert not manager.is_active


def test_community_expose_lifespan_awaits_manager_before_child_cleanup(monkeypatch):
    events = []

    class _StartedManager:
        async def stop(self):
            events.append("tunnel_stop")

    manager = _StartedManager()

    class _Child:
        pid = 42

        def name(self):
            return "tunnel-provider"

    class _Process:
        def children(self, recursive):
            assert recursive
            events.append("children_listed")
            return [_Child()]

    monkeypatch.setattr("psutil.Process", lambda _pid: _Process())
    monkeypatch.setattr(
        "actions.server._robo_utils.process.kill_process_and_subprocesses",
        lambda _pid: events.append("child_killed"),
    )

    async def run_lifespan():
        async with _community_expose_lifespan(
            None,
            expose=False,
            file_watcher=None,
            expose_later=lambda _loop: None,
            get_tunnel_manager=lambda: manager,
        ):
            events.append("running")

    asyncio.run(run_lifespan())

    assert events == [
        "running",
        "tunnel_stop",
        "children_listed",
        "child_killed",
    ]


def test_community_expose_lifespan_preserves_body_error_and_runs_cleanup(
    monkeypatch, caplog
):
    events = []

    class _FailingManager:
        async def stop(self):
            events.append("tunnel_stop")
            raise RuntimeError("stop failure")

    class _FileWatcher:
        def stop(self):
            events.append("watcher_stop")

    class _Child:
        pid = 42

        def name(self):
            return "tunnel-provider"

    class _Process:
        def children(self, recursive):
            assert recursive
            events.append("children_listed")
            return [_Child()]

    monkeypatch.setattr("psutil.Process", lambda _pid: _Process())
    monkeypatch.setattr(
        "actions.server._robo_utils.process.kill_process_and_subprocesses",
        lambda _pid: events.append("child_killed"),
    )

    async def run_lifespan():
        async with _community_expose_lifespan(
            None,
            expose=False,
            file_watcher=_FileWatcher(),
            expose_later=lambda _loop: None,
            get_tunnel_manager=lambda: _FailingManager(),
        ):
            events.append("running")
            raise RuntimeError("body failure")

    with caplog.at_level("ERROR"), pytest.raises(RuntimeError, match="body failure"):
        asyncio.run(run_lifespan())

    assert events == [
        "running",
        "tunnel_stop",
        "watcher_stop",
        "children_listed",
        "child_killed",
    ]
    assert "Error stopping community tunnel manager" in caplog.text


def test_community_expose_lifespan_isolates_tunnel_stop_failure(monkeypatch, caplog):
    events = []

    class _FailingManager:
        async def stop(self):
            events.append("tunnel_stop")
            raise RuntimeError("stop failure")

    class _FileWatcher:
        def stop(self):
            events.append("watcher_stop")

    class _Child:
        pid = 42

        def name(self):
            return "tunnel-provider"

    class _Process:
        def children(self, recursive):
            assert recursive
            events.append("children_listed")
            return [_Child()]

    monkeypatch.setattr("psutil.Process", lambda _pid: _Process())
    monkeypatch.setattr(
        "actions.server._robo_utils.process.kill_process_and_subprocesses",
        lambda _pid: events.append("child_killed"),
    )

    async def run_lifespan():
        async with _community_expose_lifespan(
            None,
            expose=False,
            file_watcher=_FileWatcher(),
            expose_later=lambda _loop: None,
            get_tunnel_manager=lambda: _FailingManager(),
        ):
            events.append("running")

    with caplog.at_level("ERROR"):
        asyncio.run(run_lifespan())

    assert events == [
        "running",
        "tunnel_stop",
        "watcher_stop",
        "children_listed",
        "child_killed",
    ]
    assert "Error stopping community tunnel manager" in caplog.text


def test_community_expose_lifespan_handles_child_list_failure(monkeypatch, caplog):
    events = []

    class _Process:
        def children(self, recursive):
            assert recursive
            events.append("children_listed")
            raise RuntimeError("process lookup failed")

    monkeypatch.setattr("psutil.Process", lambda _pid: _Process())

    async def run_lifespan():
        async with _community_expose_lifespan(
            None,
            expose=False,
            file_watcher=None,
            expose_later=lambda _loop: None,
            get_tunnel_manager=lambda: None,
        ):
            events.append("running")

    with caplog.at_level("ERROR"):
        asyncio.run(run_lifespan())

    assert events == ["running", "children_listed"]
    assert "Error listing subprocesses" in caplog.text
