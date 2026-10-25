"""Assembled outer-key and native/custom output routing boundaries."""

import sys
from dataclasses import replace
from types import SimpleNamespace

import pytest
from action_server_tests.run_outputs.test_service import publish
from action_server_tests.run_outputs.test_service import store as output_store
from action_server_tests.test_auth_route_enforcement import KEY
from action_server_tests.test_auth_route_enforcement import (
    assembled_runtime as runtime_fixture,
)
from action_server_tests.test_foundry_server_wiring import HTML

from actions.server.foundry.run_output_transport import create_run_output_transport
from actions.server.managed_work_items.authorization import bearer_authenticator
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.task_service import TaskPolicy, TaskService

store = output_store
assembled_runtime = runtime_fixture
pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux native storage")


@pytest.fixture
def configure_output_host(store, monkeypatch, request):
    from actions.server import _models, _server
    from actions.server.foundry import bootstrap
    from actions.server.run_outputs import transport

    _, _, service, snapshot, actor, _, _ = store
    _, _, output = publish(store, body=b"sealed native output")
    native = create_run_output_transport(
        service, bearer_authenticator(KEY, ManagedCaller(actor=actor))
    )
    custom = create_run_output_transport(
        service, bearer_authenticator(KEY, ManagedCaller(actor=actor))
    )
    # The sealed-output fixture remains explicitly bound to its own database.
    # Permit the assembled server fixture to own the process-global database.
    _models._global_db = None
    original_bootstrap = bootstrap.create_runtime_canvas
    original_start = _server.start_server
    original_install = transport.install_run_output_transport
    selected = []

    def build(*args, **kwargs):
        result = original_bootstrap(*args, **kwargs, html=HTML)
        tasks = TaskService(
            SimpleNamespace(outputs=service, db=service.db),
            readiness=SimpleNamespace(require_ready=lambda *args: None),
            policy=TaskPolicy(
                policy_id="routes/v1", ttl_ms=600000, poll_interval_ms=50
            ),
        )
        return replace(
            result,
            task_service=None if request.param == "disabled" else tasks,
            run_output_transport=native,
        )

    def start(*args, **kwargs):
        if request.param == "custom":
            kwargs["run_output_transport"] = custom
        return original_start(*args, **kwargs)

    def install(app, configured, dependencies):
        selected.append((configured, tuple(dependencies)))
        return original_install(app, configured, dependencies)

    monkeypatch.setattr(bootstrap, "create_runtime_canvas", build)
    monkeypatch.setattr(_server, "start_server", start)
    monkeypatch.setattr(transport, "install_run_output_transport", install)
    return SimpleNamespace(
        native=native,
        custom=custom,
        selected=selected,
        path=f"/api/workspaces/{snapshot.workspace_id}/outputs/{output.handle}",
        mode=request.param,
    )


@pytest.mark.parametrize(
    "configure_output_host", ["native", "custom", "disabled"], indirect=True
)
def test_assembled_native_output_selection_and_outer_gate(
    configure_output_host, assembled_runtime
):
    config = configure_output_host
    client = assembled_runtime.client
    assert client.get(config.path).status_code == 403
    assert (
        client.get(
            config.path, headers={"Authorization": "Bearer app-session"}
        ).status_code
        == 403
    )
    response = client.get(config.path, headers={"Authorization": "Bearer " + KEY})
    if config.mode == "disabled":
        assert response.status_code == 404
        assert config.selected == []
    else:
        assert response.status_code == 200
        assert response.content == b"sealed native output"
        expected = config.custom if config.mode == "custom" else config.native
        assert len(config.selected) == 1 and config.selected[0][0] is expected
        assert config.selected[0][1], "existing endpoint dependencies must remain"
