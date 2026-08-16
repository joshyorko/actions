import pytest

from actions.server._selftest import ActionServerClient, ActionServerProcess


@pytest.mark.integration_test
def test_devenv(datadir):
    from pathlib import Path

    from action_server_tests.fixtures import actions_server_run

    cwd = Path(datadir) / "pack1"

    # Error: No task names specified.
    actions_server_run(["devenv", "task"], returncode=2, cwd=cwd)

    actions_server_run(
        [
            "devenv",
            "--verbose",
            "task",
            "test-ok",
        ],
        returncode=0,
        cwd=cwd,
    )

    actions_server_run(["devenv", "task", "test-fail"], returncode=1, cwd=cwd)

    result = actions_server_run(
        ["devenv", "task", "echo-arg1-arg2"], returncode=0, cwd=cwd
    )
    assert [x.strip() for x in result.stdout.splitlines()] == ["['arg1']", "['arg2']"]


@pytest.mark.integration_test
def test_run_actions_with_custom_pythonpath(
    action_server_process: ActionServerProcess,
    client: ActionServerClient,
    datadir,
):
    import json
    from pathlib import Path

    from action_server_tests.fixtures import BUILD_ENV_IN_TESTS_TIMEOUT

    cwd = Path(datadir) / "pack1"

    action_server_process.start(
        cwd=cwd,
        actions_sync=True,
        db_file="server.db",
        lint=True,
        timeout=BUILD_ENV_IN_TESTS_TIMEOUT,
    )

    found = client.post_get_str(
        "api/actions/action-package-example/doit/run",
        {"validate": True},
    )
    assert "Ok validated" == json.loads(found)
