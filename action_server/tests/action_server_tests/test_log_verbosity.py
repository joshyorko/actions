import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar, cast

import pytest
from robocorp.log._log_formatting import pretty_format_logs_from_log_html_contents

from actions.server._selftest import ActionServerClient, ActionServerProcess
from actions.server._protocols import ArgumentsNamespaceStart
from actions.server._settings import HEADER_ACTION_SERVER_RUN_ID


def test_verbose_server_startup_redacts_database_url_credentials(
    tmp_path: Path, caplog, monkeypatch
):
    database_url = (
        "postgresql://SENTINEL_USER%40encoded:SENTINEL_PASSWORD%21@"
        "127.0.0.1:1/actions?application_name=SENTINEL_TOKEN%20SENTINEL_QUERY"
        "#SENTINEL_FRAGMENT"
    )
    from actions.server._server import start_server
    from actions.server._settings import Settings

    settings = Settings(
        artifacts_dir=tmp_path / "artifacts",
        datadir=tmp_path,
        database_url=database_url,
        min_processes=0,
        max_processes=0,
        enable_scheduler=False,
        enable_triggers=False,
        verbose=True,
    )
    settings.artifacts_dir.mkdir()
    monkeypatch.setattr("actions.server._settings.get_settings", lambda: settings)
    monkeypatch.setattr(
        "actions.server._server.asyncio.run", lambda coroutine: coroutine.close()
    )

    class FakeActionRoutes:
        action_package_id_to_action_package: ClassVar[dict[str, Any]] = {}
        actions: ClassVar[list[Any]] = []

        def __init__(self, *args):
            pass

        def setup_mcp_server(self, *args):
            pass

        def register_actions(self):
            pass

    monkeypatch.setattr(
        "actions.server._api_action_routes._ActionRoutes", FakeActionRoutes
    )
    monkeypatch.setattr(
        "actions.server._actions_process_pool.setup_actions_process_pool",
        lambda *args: __import__("contextlib").nullcontext(),
    )
    monkeypatch.setattr(
        "actions.server._artifact_storage.get_artifact_storage",
        lambda: SimpleNamespace(root=tmp_path / "artifacts"),
    )

    caplog.set_level("DEBUG")
    start_server(
        cast(
            ArgumentsNamespaceStart,
            SimpleNamespace(expose=False, whitelist=None, auto_reload=False),
        ),
        api_key=None,
        before_start=(),
    )
    output = caplog.text

    assert settings.database_url == database_url
    assert "Starting server. Settings:" in output
    assert "database_url = 'postgresql://127.0.0.1:1/actions'" in output
    for secret in (
        "SENTINEL_USER",
        "SENTINEL_USER%40encoded",
        "SENTINEL_PASSWORD",
        "SENTINEL_PASSWORD%21",
        "SENTINEL_TOKEN",
        "SENTINEL_QUERY",
        "SENTINEL_FRAGMENT",
    ):
        assert secret not in output


@pytest.mark.integration_test
def test_logs_dont_contain_secrets(
    action_server_process: ActionServerProcess, client: ActionServerClient, tmpdir
):
    """Test to verify that logs don't contain secrets or sensitive information."""
    # Create a simple action that receives a secret password
    action_file = Path(tmpdir) / "secret_action" / "secret_action.py"
    action_file.parent.mkdir(parents=True, exist_ok=True)

    action_file.write_text(
        """
from actions import action

@action
def handle_secret(username: str, password: str) -> str:
    '''Test action that handles sensitive information'''
    print(f"Processing request for user: {username}")
    # We deliberately don't log the password
    # but we use it in the action logic
    return f"User {username} authenticated successfully"
"""
    )

    # Start the action server
    action_server_process.start(
        actions_sync=True,
        cwd=action_file.parent,
        db_file="server.db",
    )

    # Run the action with a username and a secret password
    username = "testuser"
    password = "supersecretpassword123!"

    response = client.post_get_response(
        "api/actions/secret-action/handle-secret/run",
        {"username": username, "password": password},
    )

    # Verify that the action ran successfully
    assert response.status_code == 200
    assert json.loads(response.text) == f"User {username} authenticated successfully"

    # Get the run ID from the response headers
    run_id = response.headers[HEADER_ACTION_SERVER_RUN_ID]

    # Retrieve and check the log content
    log_html_contents = client.get_str(
        f"api/runs/{run_id}/artifacts/binary-content",
        params={"artifact_name": "log.html"},
    )

    log_contents = pretty_format_logs_from_log_html_contents(log_html_contents)

    # Verify the logs include the username but not the password
    assert username in log_contents
    assert password not in log_contents

    assert "supersecretpassword123!" not in action_server_process.get_stdout()
    assert "supersecretpassword123!" not in action_server_process.get_stderr()

    # The result should not be logged either.
    assert "authenticated successfully" not in action_server_process.get_stdout()
    assert "authenticated successfully" not in action_server_process.get_stderr()
