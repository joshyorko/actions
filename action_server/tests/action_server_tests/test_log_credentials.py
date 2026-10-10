import importlib
import logging
import secrets
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    "name", ["Authorization", "Proxy-Authorization", "Cookie", "Set-Cookie", "cOoKiE"]
)
def test_configured_debug_handlers_redact_transport_credentials(
    name, tmp_path: Path, monkeypatch, capsys
):
    from actions.server._cli_impl import _setup_logging, _setup_stderr_logging

    root = logging.getLogger()
    previous_handlers = list(root.handlers)
    previous_level = root.level
    monkeypatch.setenv("NO_COLOR", "true")
    try:
        root.setLevel(logging.DEBUG)
        _setup_stderr_logging(logging.DEBUG)
        _setup_logging(tmp_path, logging.DEBUG)
        logging.getLogger("uvicorn.error").debug(
            "< %s: %s", name, "SYNTHETIC-CREDENTIAL-SENTINEL"
        )
        for handler in root.handlers:
            handler.flush()
        stderr = capsys.readouterr().err
        disk = (tmp_path / "server_log.txt").read_text()
        for output in [stderr, disk]:
            assert name in output
            assert "<redacted>" in output
            assert "SYNTHETIC-CREDENTIAL-SENTINEL" not in output
    finally:
        for handler in list(root.handlers):
            if handler not in previous_handlers:
                root.removeHandler(handler)
                handler.close()
        root.setLevel(previous_level)


def test_debug_cli_arguments_never_include_api_key_values():
    from actions.server._cli_impl import _redact_cli_arguments

    result = _redact_cli_arguments(
        [
            "action-server",
            "start",
            "--api-key",
            "SYNTHETIC-KEY",
            "--api-key=SYNTHETIC-SECOND",
            "--port",
            "8080",
        ]
    )
    assert result == [
        "action-server",
        "start",
        "--api-key",
        "<redacted>",
        "--api-key=<redacted>",
        "--port",
        "8080",
    ]


@pytest.mark.parametrize(
    "module_name",
    [
        "actions.server._common.process",
        "actions.server._robo_utils.process",
    ],
)
@pytest.mark.parametrize("argument_form", ["joined", "separate-abbreviated"])
def test_subprocess_debug_diagnostics_redact_api_key_arguments(
    module_name, argument_form, monkeypatch, caplog, tmp_path
):
    process_module = importlib.import_module(module_name)
    api_key = secrets.token_urlsafe(32)
    if argument_form == "joined":
        key_arguments = [f"--api-key={api_key}"]
    else:
        key_arguments = ["--api-k", api_key]
    fake_process = SimpleNamespace(pid=123, stdin=None, stdout=None, stderr=None)
    monkeypatch.setattr(
        process_module,
        "_popen_raise",
        lambda *_args, **_kwargs: fake_process,
    )
    monkeypatch.setattr(process_module, "_start_reader_threads", lambda *_args: None)
    caplog.set_level(logging.DEBUG, logger=process_module.log.name)

    child = process_module.Process(
        ["action-server", "start", *key_arguments], cwd=tmp_path
    )
    child.start()
    diagnostics = caplog.text
    if module_name.endswith("_common.process"):
        diagnostics += str(child)
    if api_key in diagnostics:
        raise AssertionError("subprocess diagnostics exposed an API key")
    if "<redacted>" not in diagnostics.casefold():
        raise AssertionError("subprocess diagnostics omitted the redaction marker")


@pytest.mark.integration_test
def test_assembled_websocket_session_credentials_never_reach_logs(tmp_path: Path):
    import json
    import os
    import socket
    import subprocess
    import sys
    import time

    import httpx
    from websockets.sync.client import connect
    from websockets.typing import Origin

    # The regular CLI leaves uvicorn at INFO. Exercise its supported DEBUG
    # transport through the same assembled CLI, changing only logging config.
    launcher = tmp_path / "debug_transport.py"
    launcher.write_text(
        "from actions.server._settings import Settings\n"
        "original = Settings.to_uvicorn\n"
        "def debug(self):\n"
        "    settings = original(self)\n"
        "    settings['log_level'] = 'debug'\n"
        "    return settings\n"
        "Settings.to_uvicorn = debug\n"
        "from actions.server.cli import main\n"
        "main()\n"
    )
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    api_key = "SYNTHETIC-ASSEMBLED-API-KEY"
    datadir = tmp_path / "data"
    stderr_path = tmp_path / "stderr.txt"
    stdout_path = tmp_path / "stdout.txt"
    with stderr_path.open("w") as stderr, stdout_path.open("w") as stdout:
        process = subprocess.Popen(
            [
                sys.executable,
                str(launcher),
                "start",
                "--address",
                "127.0.0.1",
                "--port",
                str(port),
                "--datadir",
                str(datadir),
                "--actions-sync=false",
                f"--api-k={api_key}",
                "-v",
            ],
            cwd=tmp_path,
            stdout=stdout,
            stderr=stderr,
            env={**os.environ, "ACTIONS_SKIP_UPDATE_CHECK": "1"},
        )
        try:
            with httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        if client.get("/config").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    assert process.poll() is None, "Runtime exited before readiness"
                    assert time.monotonic() < deadline, "Runtime readiness deadline"
                    time.sleep(0.05)
                login = client.post(
                    "/browser-session",
                    headers={"Origin": origin, "Authorization": f"Bearer {api_key}"},
                )
                assert login.status_code == 200
                token = client.cookies["actions_browser_session"]
                with connect(
                    origin.replace("http", "ws", 1) + "/api/ws",
                    origin=Origin(origin),
                    additional_headers={"Cookie": f"actions_browser_session={token}"},
                    proxy=None,
                    open_timeout=10,
                ) as ws:
                    ws.send(json.dumps({"event": "echo", "data": "verified-handshake"}))
                    assert json.loads(ws.recv(timeout=10)) == {
                        "event": "echo",
                        "data": "verified-handshake",
                    }
                assert (
                    client.delete(
                        "/browser-session", headers={"Origin": origin}
                    ).status_code
                    == 204
                )
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    output = stdout_path.read_text() + stderr_path.read_text()
    disk = (datadir / "server_log.txt").read_text()
    for text in (output, disk):
        assert "cookie: <redacted>" in text.casefold()
        assert "verified-handshake" in text
        assert token not in text
        assert api_key not in text


@pytest.mark.parametrize("option", ["--ap", "--api", "--api-", "--api-k", "--api-ke"])
@pytest.mark.parametrize("joined", [False, True])
def test_accepted_api_key_option_abbreviations_are_redacted(option, joined):
    from actions.server._cli_impl import _create_parser, _redact_cli_arguments

    flags = (
        [f"{option}=SYNTHETIC-ABBREVIATED-KEY"]
        if joined
        else [option, "SYNTHETIC-ABBREVIATED-KEY"]
    )
    assert (
        _create_parser().parse_args(["start", *flags]).api_key
        == "SYNTHETIC-ABBREVIATED-KEY"
    )
    result = _redact_cli_arguments(["action-server", "start", *flags])
    assert "SYNTHETIC-ABBREVIATED-KEY" not in " ".join(result)
    assert "<redacted>" in " ".join(result)
