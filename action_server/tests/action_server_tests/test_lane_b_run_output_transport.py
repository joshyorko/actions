"""Host managed identity adapter through existing SQL/output HTTP authority."""
from types import SimpleNamespace

import pytest
from action_server_tests.run_outputs.test_service import publish
from action_server_tests.run_outputs.test_service import store as output_store
from action_server_tests.run_outputs.test_service import uid
from fastapi import FastAPI
from fastapi.testclient import TestClient

from actions.server.foundry.run_output_transport import create_run_output_transport
from actions.server.managed_work_items.authorization import bearer_authenticator
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.transport import install_run_output_transport

store = output_store
OWNER = {"Authorization": "Bearer owned-credential"}


@pytest.fixture
def endpoint(store):
    _, _, service, snapshot, actor, _, _ = store
    _, _, output = publish(store, body=b"owned sealed output")
    auth = bearer_authenticator("owned-credential", ManagedCaller(actor=actor))
    config = create_run_output_transport(service, auth)
    app = FastAPI()
    install_run_output_transport(app, config, [])
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            config=config,
            path=f"/api/workspaces/{snapshot.workspace_id}/outputs/{output.handle}",
        )


def test_exact_host_identity_reads_existing_sealed_output(endpoint, store):
    assert endpoint.config.service is store[2]
    assert endpoint.config.canvas_scope is None
    response = endpoint.client.get(endpoint.path, headers=OWNER)
    assert response.status_code == 200
    assert response.content == b"owned sealed output"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer invalid"},
        {"Authorization": "Bearer app-session-token"},
        {"X-App-Session": "app-session-token", "X-Actions-Audience": "app"},
        {"Cookie": "actions_session=app-session-token"},
        {"X-Principal-Id": "owner", "X-Workspace-Id": "owned"},
    ],
)
def test_no_identity_from_missing_invalid_or_app_credentials(endpoint, headers):
    response = endpoint.client.get(endpoint.path, headers=headers)
    assert response.status_code == 404
    assert response.text == "Output unavailable or access denied"


def test_live_revocation_still_denies_host_owner(endpoint, store):
    _, control, _, snapshot, actor, _, _ = store
    control.revoke(actor, snapshot.deployment)
    assert endpoint.client.get(endpoint.path, headers=OWNER).status_code == 404


def test_cross_workspace_handle_cannot_be_rebound(endpoint, store):
    other = endpoint.path.replace(store[3].workspace_id, uid())
    assert endpoint.client.get(other, headers=OWNER).status_code == 404


def test_app_audience_object_is_not_a_managed_identity(store):
    from actions.server.foundry.mcp import CanvasCaller

    async def app_identity(request):
        return CanvasCaller(store[4], store[3].workspace_id, "app")

    config = create_run_output_transport(store[2], app_identity)
    app = FastAPI()
    install_run_output_transport(app, config, [])
    with TestClient(app) as client:
        response = client.get(
            f"/api/workspaces/{store[3].workspace_id}/outputs/art_" + "A" * 22
        )
    assert response.status_code == 404


def test_host_authentication_failure_uses_existing_unavailable_response(store):
    async def unavailable(request):
        raise RuntimeError("private detail must not escape")

    config = create_run_output_transport(store[2], unavailable)
    app = FastAPI()
    install_run_output_transport(app, config, [])
    with TestClient(app) as client:
        response = client.get(
            f"/api/workspaces/{store[3].workspace_id}/outputs/art_" + "A" * 22
        )
    assert response.status_code == 503
    assert "private detail" not in response.text


def test_factory_refuses_unconfigured_authentication(store):
    with pytest.raises(TypeError):
        create_run_output_transport(store[2], None)
