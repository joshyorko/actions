import logging
from pathlib import Path

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
