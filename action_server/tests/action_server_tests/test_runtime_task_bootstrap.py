"""Resource ownership and default-off Task wiring, not actual worker proof."""
from types import SimpleNamespace

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_server_wiring import HTML

from actions.server.foundry.bootstrap import RuntimeCanvas, create_runtime_canvas

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def test_task_shutdown_retains_provider_until_worker_join():
    calls = []

    class Host:
        joined = False

        def start(self):
            calls.append("start")

        def close(self):
            calls.append("join")
            return self.joined

    host = Host()
    native = RuntimeCanvas(
        None,
        None,
        None,
        SimpleNamespace(close=lambda: calls.append("provider")),
        None,
        None,
        task_host=host,
    )
    assert calls == []
    native.start()
    with pytest.raises(RuntimeError, match="worker shutdown"):
        native.close()
    assert calls == ["start", "join"]
    host.joined = True
    native.close()
    assert calls == ["start", "join", "join", "provider"]


def test_default_off_and_policy_without_runtime_fails(
    database_location, tmp_path, monkeypatch
):
    monkeypatch.delenv("ACTIONS_FOUNDRY_EXECUTION_PROFILE", raising=False)
    monkeypatch.delenv("ACTIONS_FOUNDRY_TASK_POLICY", raising=False)
    refs = _refs()
    with _runtime_database(database_location, refs.workspace, ()) as db:
        native = create_runtime_canvas(db, tmp_path / "native", "owned-key", html=HTML)
        try:
            assert native.task_host is None and native.task_service is None
            native.start()
        finally:
            native.close()
        monkeypatch.setenv(
            "ACTIONS_FOUNDRY_TASK_POLICY", str(tmp_path / "missing-policy.json")
        )
        with pytest.raises(ValueError, match="Task policy requires"):
            create_runtime_canvas(db, tmp_path / "native", "owned-key", html=HTML)
