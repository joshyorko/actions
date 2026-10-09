import asyncio
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from actions.server._community_expose import (
    BaseTunnelProvider,
    CloudflareProvider,
    LocalhostRunProvider,
    TunnelInfo,
    TunnelManager,
    TunnelProvider,
    _stop_process,
)
from actions.server._server import (
    _community_expose_lifespan,
    _start_community_expose_impl,
)


def _scripted_pipe_reads(monkeypatch, process):
    """Control chunk boundaries; real subprocess tests cover native pipe IO."""
    import os

    streams = {}
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            descriptor = id(stream)
            streams[descriptor] = stream
            monkeypatch.setattr(
                stream, "fileno", lambda value=descriptor: value, raising=False
            )
    operations = SimpleNamespace(**vars(os))
    operations.set_blocking = lambda descriptor, blocking: None
    operations.read = lambda descriptor, size: streams[descriptor].read1(size)
    monkeypatch.setattr("actions.server._community_expose.os", operations)


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
            self.chunks = iter(line.encode() for line in lines)

        def read1(self, _size):
            return next(self.chunks, b"")

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

    process = Process()
    _scripted_pipe_reads(monkeypatch, process)
    result = asyncio.run(CloudflareProvider()._wait_for_url(process, timeout=0.2))

    assert result == "https://sample.trycloudflare.com"


def test_cloudflare_does_not_join_url_fragments_from_different_streams(monkeypatch):
    import queue
    import threading

    stdout_queued = threading.Event()

    class OrderedQueue(queue.Queue):
        def put(self, item, *args, **kwargs):
            result = super().put(item, *args, **kwargs)
            if item[0] == "stdout" and item[1] is not None:
                stdout_queued.set()
            return result

    class Stream:
        def __init__(self, chunks, *, wait_for_stdout=False):
            self.chunks = iter(chunks)
            self.wait_for_stdout = wait_for_stdout

        def read1(self, _size):
            if self.wait_for_stdout:
                stdout_queued.wait()
            return next(self.chunks, b"")

        def close(self):
            pass

    class Process:
        stdout = Stream([b"https://synthetic.trycloudflare."])
        stderr = Stream([b"com"], wait_for_stdout=True)

        def poll(self):
            return 0

    monkeypatch.setattr("actions.server._community_expose.queue.Queue", OrderedQueue)
    process = Process()
    _scripted_pipe_reads(monkeypatch, process)
    with pytest.raises(RuntimeError, match="before a public URL"):
        asyncio.run(CloudflareProvider()._wait_for_url(process, timeout=0.5))


@pytest.mark.parametrize("stream_name", ["stdout", "stderr"])
def test_cloudflare_joins_url_fragments_within_one_stream(monkeypatch, stream_name):
    chunks = iter([b"https://split.trycloudflare.", b"com"])
    stream = SimpleNamespace(read1=lambda _size: next(chunks, b""), close=lambda: None)
    process = SimpleNamespace(stdout=None, stderr=None, poll=lambda: 0)
    setattr(process, stream_name, stream)
    _scripted_pipe_reads(monkeypatch, process)
    try:
        assert asyncio.run(CloudflareProvider()._wait_for_url(process, timeout=1)) == (
            "https://split.trycloudflare.com"
        )
    finally:
        _stop_process(process)


def test_cloudflare_reader_timeout_reaps_process_and_unblocks_pipes(monkeypatch):
    import threading

    class BlockingStream:
        def __init__(self):
            self.closed = False
            self.release = threading.Event()

        def read1(self, _size):
            raise BlockingIOError

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
    _scripted_pipe_reads(monkeypatch, process)
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


def test_cloudflare_reader_is_async_and_cancellable_with_newline_free_output():
    code = "import os; data = b'x' * 65536; exec('while True: os.write(1, data)')"
    process = subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=-1,
    )
    provider = CloudflareProvider()

    async def exercise_reader():
        reader = asyncio.create_task(provider._wait_for_url(process, timeout=10))
        await asyncio.sleep(0.05)
        assert process.poll() is None
        reader.cancel()
        with pytest.raises(asyncio.CancelledError):
            await reader
        assert process.poll() is not None
        assert all(not thread.is_alive() for thread in process._cloudflared_readers)

    asyncio.run(exercise_reader())


def test_cloudflare_cancellation_runs_while_output_queue_is_always_full(monkeypatch):
    import queue
    import threading

    queue_full = threading.Event()

    class AlwaysFullQueue:
        def __init__(self, maxsize):
            assert maxsize == 64

        def get_nowait(self):
            return "stdout", b"x" * 4096

        def put(self, *_args, **_kwargs):
            queue_full.set()
            raise queue.Full

    class Stream:
        closed = False

        def read1(self, _size):
            return b"x" * 4096

        def close(self):
            self.closed = True

    class Process:
        def __init__(self):
            self.stdout = Stream()
            self.stderr = None
            self.running = True

        def poll(self):
            return None if self.running else 0

        def terminate(self):
            self.running = False

        def wait(self, timeout):
            return 0

    process = Process()
    _scripted_pipe_reads(monkeypatch, process)
    monkeypatch.setattr("actions.server._community_expose.queue.Queue", AlwaysFullQueue)

    async def exercise_cancellation():
        waiter = asyncio.create_task(
            CloudflareProvider()._wait_for_url(process, timeout=10)
        )
        assert await asyncio.to_thread(queue_full.wait, 1)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert not process.running
        assert all(not reader.is_alive() for reader in process._cloudflared_readers)

    asyncio.run(exercise_cancellation())


def test_cloudflare_waiter_does_not_kill_inherited_pipe_writer(tmp_path):
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    marker = tmp_path / "finished"
    helper = (
        "import pathlib,sys,time; "
        "root=pathlib.Path(sys.argv[1]); (root/'ready').touch(); "
        "deadline=time.monotonic()+5; "
        "exec('while not (root/\"release\").exists() and time.monotonic()<deadline: time.sleep(.01)'); "
        "(root/'finished').touch()"
    )
    owner = (
        "import subprocess,sys; "
        "subprocess.Popen([sys.executable, '-c', sys.argv[2], sys.argv[1]])"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", owner, str(tmp_path), helper],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=-1,
    )

    async def wait_for_owner_then_timeout():
        await asyncio.to_thread(process.wait, timeout=2)
        deadline = time.monotonic() + 2
        while not ready.exists():
            assert time.monotonic() < deadline
            await asyncio.sleep(0.01)
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            await CloudflareProvider()._wait_for_url(process, timeout=0.05)
        assert time.monotonic() - started < 1
        assert not marker.exists(), "cleanup must not wait for the inherited writer"
        assert all(not reader.is_alive() for reader in process._cloudflared_readers)

    try:
        asyncio.run(wait_for_owner_then_timeout())
    finally:
        release.touch()
        _stop_process(process)
        deadline = time.monotonic() + 6
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
    assert marker.exists(), "the inherited writer must survive owned-process cleanup"


def test_cloudflare_full_queue_reader_keeps_draining_after_url(monkeypatch):
    import queue

    blocked = threading.Event()
    drained = threading.Event()

    class FullQueue(queue.Queue):
        def put(self, item, *args, **kwargs):
            if item == ("stderr", b"blocked"):
                blocked.set()
                raise queue.Full
            return super().put(item, *args, **kwargs)

        def get_nowait(self):
            if not blocked.is_set():
                raise queue.Empty
            return super().get_nowait()

    class Stream:
        def __init__(self, chunks):
            self.chunks = iter(chunks)

        def read1(self, _size):
            chunk = next(self.chunks, b"")
            if chunk == b"drained":
                drained.set()
            return chunk

        def close(self):
            pass

    process = SimpleNamespace(
        stdout=Stream([b"https://sample.trycloudflare.com"]),
        stderr=Stream([b"blocked", b"drained"]),
        poll=lambda: 0,
    )
    monkeypatch.setattr("actions.server._community_expose.queue.Queue", FullQueue)
    _scripted_pipe_reads(monkeypatch, process)

    async def exercise_reader():
        try:
            url = await CloudflareProvider()._wait_for_url(process, timeout=1)
            assert url == "https://sample.trycloudflare.com"
            assert await asyncio.to_thread(drained.wait, 0.5)
        finally:
            await asyncio.to_thread(_stop_process, process)

    asyncio.run(exercise_reader())


def test_cloudflare_stop_does_not_block_event_loop(monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    watchdog_fired = threading.Event()

    def slow_stop(_process):
        entered.set()
        if not release.wait(1):
            watchdog_fired.set()

    monkeypatch.setattr("actions.server._community_expose._stop_process", slow_stop)

    async def exercise_stop():
        stop = asyncio.create_task(
            CloudflareProvider().stop(TunnelInfo(TunnelProvider.CLOUDFLARE, "", 8080))
        )
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            assert not watchdog_fired.is_set()
        finally:
            release.set()
            await stop

    asyncio.run(exercise_stop())


def test_cloudflare_cancellation_survives_cleanup_failure(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    class Stream:
        def read1(self, _size):
            entered.set()
            assert release.wait(2)
            return b""

        def close(self):
            pass

    def failed_stop(_process):
        raise RuntimeError("synthetic-cleanup-failure")

    process = SimpleNamespace(stdout=Stream(), stderr=None, poll=lambda: 0)
    _scripted_pipe_reads(monkeypatch, process)
    monkeypatch.setattr("actions.server._community_expose._stop_process", failed_stop)

    async def exercise_cancel():
        waiter = asyncio.create_task(CloudflareProvider()._wait_for_url(process))
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter
        finally:
            release.set()
            for reader in process._cloudflared_readers:
                reader.join(2)

    asyncio.run(exercise_cancel())


def test_cloudflare_repeated_cancellation_waits_for_cleanup(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    def slow_stop(_process):
        entered.set()
        assert release.wait(2)

    monkeypatch.setattr("actions.server._community_expose._stop_process", slow_stop)

    async def exercise_cancel():
        stop = asyncio.create_task(
            CloudflareProvider().stop(TunnelInfo(TunnelProvider.CLOUDFLARE, "", 8080))
        )
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            stop.cancel()
            await asyncio.sleep(0)
            stop.cancel()
            await asyncio.sleep(0)
            assert not stop.done()
        finally:
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await stop

    asyncio.run(exercise_cancel())


def test_cloudflare_partial_pipe_setup_failure_reaps_process(monkeypatch):
    import os

    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    set_blocking = os.set_blocking

    def fail_second_pipe(descriptor, blocking):
        if descriptor == process.stderr.fileno():
            raise OSError("synthetic-nonblocking-setup-failure")
        set_blocking(descriptor, blocking)

    monkeypatch.setattr("os.set_blocking", fail_second_pipe)
    try:
        with pytest.raises(OSError, match="synthetic-nonblocking-setup-failure"):
            asyncio.run(CloudflareProvider()._wait_for_url(process))
        assert process.poll() is not None
        assert process.stdout.closed and process.stderr.closed
        assert all(not reader.is_alive() for reader in process._cloudflared_readers)
    finally:
        _stop_process(process)


def test_stop_process_does_not_close_pipe_under_lingering_reader():
    closed = []
    process = SimpleNamespace(
        poll=lambda: 0,
        stdout=SimpleNamespace(close=lambda: closed.append("stdout")),
        stderr=None,
        _cloudflared_reader_cancel=threading.Event(),
        _cloudflared_readers=[
            SimpleNamespace(
                name="lingering", join=lambda timeout: None, is_alive=lambda: True
            )
        ],
    )
    with pytest.raises(
        RuntimeError, match="cloudflared-output-reader-shutdown-timeout"
    ):
        _stop_process(process)
    assert process._cloudflared_reader_cancel.is_set()
    assert closed == []


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


def test_failed_authenticated_tunnel_probe_stops_owned_manager_without_logging_key(
    monkeypatch, caplog
):
    from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

    class Manager:
        def __init__(self, **_kwargs):
            self.stopped = False
            self.stop_callbacks = []

        async def start(self, _port):
            return SimpleNamespace(
                public_url="https://edge.example.test",
                provider=SimpleNamespace(value="synthetic"),
            )

        async def stop(self):
            self.stopped = True
            for callback in self.stop_callbacks:
                callback()

        def add_stop_callback(self, callback):
            self.stop_callbacks.append(callback)

    manager = Manager()
    monkeypatch.setattr(
        "actions.server._community_expose.TunnelManager", lambda **_: manager
    )

    async def fail_probe(*_args):
        raise RuntimeError("synthetic-api-key")

    monkeypatch.setattr("actions.server._server._verify_public_tunnel", fail_probe)
    app = SimpleNamespace(mtime_uuid="synthetic-runtime-id")
    routes = SimpleNamespace(mcp_server_setup_helper=McpServerSetupHelper())
    with caplog.at_level("INFO"):
        result = asyncio.run(
            _start_community_expose_impl(
                8080,
                SimpleNamespace(expose_provider="auto"),
                "synthetic-api-key",
                app=app,
                action_routes=routes,
            )
        )
    assert result is manager
    assert manager.stopped
    assert (
        "edge.example.test"
        not in routes.mcp_server_setup_helper.transport_security.allowed_hosts
    )
    assert "synthetic-api-key" not in caplog.text
    assert "Public URL" not in caplog.text
    assert "Failed to start tunnel (RuntimeError)." in caplog.text


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
