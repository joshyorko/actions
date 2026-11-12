"""Ordinary host identity/output wiring; no worker execution claim."""

import asyncio
import json
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_server_wiring import HTML
from starlette.requests import Request

from actions.server.foundry import bootstrap

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux native storage")


@pytest.mark.parametrize("tasks", [False, True])
def test_native_output_transport_requires_task_policy(
    database_location, tmp_path, monkeypatch, tasks
):
    monkeypatch.delenv("ACTIONS_FOUNDRY_EXECUTION_PROFILE", raising=False)
    monkeypatch.delenv("ACTIONS_FOUNDRY_TASK_POLICY", raising=False)
    refs = _refs()
    with _runtime_database(database_location, refs.workspace, ()) as db:
        initial = bootstrap.create_runtime_canvas(
            db, tmp_path / "native", "owned-key", html=HTML
        )
        workspace = initial.workspace
        assert initial.run_output_transport is None
        initial.close()
        profile = SimpleNamespace(
            worker=SimpleNamespace(workspace_id=workspace),
            worker_id=str(uuid4()),
            prepared_receipt="/tmp/unused-wiring-only",
            provider_key="owned-output-provider",
        )
        monkeypatch.setattr(bootstrap, "read_runtime_profile", lambda _: profile)
        monkeypatch.setattr(
            bootstrap, "load_prepared_rcc_environment", lambda _: object()
        )
        if tasks:
            policy = tmp_path / "policy.json"
            policy.write_text(
                json.dumps(
                    {
                        "schema_version": "actions.runtime-task-policy/v1",
                        "policy_id": "wiring/v1",
                        "ttl_ms": 600000,
                        "poll_interval_ms": 50,
                    }
                )
            )
            policy.chmod(0o600)
            monkeypatch.setenv("ACTIONS_FOUNDRY_TASK_POLICY", str(policy))
            monkeypatch.setattr(
                "actions.server.run_outputs.task_host.DetachedTaskHost",
                lambda *args, **kwargs: SimpleNamespace(
                    require_ready=lambda *args: None, close=lambda: True
                ),
            )
        native = bootstrap.create_runtime_canvas(
            db, tmp_path / "native", "owned-key", html=HTML
        )
        try:
            if not tasks:
                assert native.run_output_transport is None
                return
            transport = native.run_output_transport
            assert transport.service is native.task_service.outputs
            assert transport.canvas_scope is None
            for credential, expected in [
                ("owned-key", native.actor),
                ("app-session", None),
                ("different-worker", None),
            ]:
                request = Request(
                    {
                        "type": "http",
                        "headers": [
                            (b"authorization", ("Bearer " + credential).encode())
                        ],
                    }
                )
                assert asyncio.run(transport.authenticate(request)) == expected
        finally:
            native.close()
