import http.client
import os
import signal
import socket
import sys
import time

import pytest
from devutils.fixtures import wait_for_condition

from actions.server._robo_utils.process import Process
from actions.server._selftest import ActionServerClient, ActionServerProcess


def _read_response_headers(connection: socket.socket) -> bytes:
    response = bytearray()
    while b"\r\n\r\n" not in response:
        chunk = connection.recv(4096)
        if not chunk:
            break
        response.extend(chunk)
        if len(response) > 64 * 1024:
            raise AssertionError("response headers exceeded 64 KiB")
    return bytes(response)


def _is_live_process(pid: int) -> bool:
    import psutil

    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


@pytest.mark.integration_test
@pytest.mark.skipif(sys.platform == "win32", reason="requires POSIX SIGTERM")
def test_mcp_sse_does_not_starve_server_or_sigterm(
    action_server_process: ActionServerProcess,
):
    from action_server_tests.fixtures import get_in_resources

    from actions.server._robo_utils.process import kill_process_and_subprocesses

    pack = get_in_resources("no_conda", "greeter")
    action_server_process.start(
        cwd=pack,
        actions_sync=True,
        db_file="server.db",
        reuse_processes=True,
        min_processes=2,
    )
    process = action_server_process.process
    child_pids: list[int] = []
    sse_connection: socket.socket | None = None
    try:
        import psutil

        child_pids = [child.pid for child in psutil.Process(process.pid).children()]
        assert len(child_pids) >= 2
        sse_connection = socket.create_connection(
            (action_server_process.host, action_server_process.port), timeout=2
        )
        sse_connection.sendall(
            (
                "GET /mcp HTTP/1.1\r\n"
                f"Host: localhost:{action_server_process.port}\r\n"
                "Accept: text/event-stream\r\n"
                "Connection: keep-alive\r\n\r\n"
            ).encode()
        )
        response_headers = _read_response_headers(sse_connection)
        assert response_headers.startswith(b"HTTP/1.1 200")
        assert b"content-type: text/event-stream" in response_headers.lower()

        health_connection = http.client.HTTPConnection(
            action_server_process.host, action_server_process.port, timeout=1
        )
        try:
            health_connection.request("GET", "/")
            assert health_connection.getresponse().status == 200
        finally:
            health_connection.close()

        os.kill(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + 5
        while process.returncode is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert process.returncode is not None, "SIGTERM did not stop Action Server"
        while (
            any(_is_live_process(pid) for pid in child_pids)
            and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        assert not any(_is_live_process(pid) for pid in child_pids)
    finally:
        if sse_connection is not None:
            sse_connection.close()
        if process.returncode is None:
            kill_process_and_subprocesses(process.pid)
            process.join()
        for child_pid in child_pids:
            if _is_live_process(child_pid):
                kill_process_and_subprocesses(child_pid)
        cleanup_deadline = time.monotonic() + 5
        while (
            any(_is_live_process(pid) for pid in child_pids)
            and time.monotonic() < cleanup_deadline
        ):
            time.sleep(0.05)
        surviving_child_pids = [pid for pid in child_pids if _is_live_process(pid)]
        assert (
            not surviving_child_pids
        ), f"recorded child processes survived cleanup: {surviving_child_pids}"


@pytest.mark.integration_test
def test_action_server_parent_pid(
    action_server_process: ActionServerProcess, data_regression
):
    from action_server_tests.fixtures import get_in_resources

    from actions.server._robo_utils.process import kill_process_and_subprocesses

    process = Process(["python", "-c", "import time;time.sleep(1000000)"])
    process.start()
    pid = process.pid

    pack = get_in_resources("no_conda", "greeter")
    action_server_process.start(
        cwd=pack,
        actions_sync=True,
        db_file="server.db",
        reuse_processes=True,
        min_processes=1,
        additional_args=[f"--parent-pid={pid}"],
    )

    client = ActionServerClient(action_server_process)

    found = client.post_get_str(
        "api/actions/greeter/greet/run",
        {"name": "Foo"},
        {"Authorization": "Bearer Foo"},
    )
    assert found == '"Hello Mr. Foo."', f"{found} != '\"Hello Mr. Foo.\"'"

    assert action_server_process.process.is_alive()

    kill_process_and_subprocesses(pid)

    wait_for_condition(lambda: not action_server_process.process.is_alive())
