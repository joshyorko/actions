import asyncio

from actions.server._community_expose import (
    BaseTunnelProvider,
    TunnelInfo,
    TunnelManager,
    TunnelProvider,
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
    working = _FakeProvider(TunnelProvider.BORE)
    manager = TunnelManager()
    manager._providers = [failed, working]

    tunnel = asyncio.run(manager.start(8080))

    assert tunnel.provider is TunnelProvider.BORE
    assert failed.started_ports == [8080]
    assert working.started_ports == [8080]
