"""Ordinary authenticated Runtime joins managed SQL without creating grants."""

import asyncio
import sys

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_server_wiring import HTML
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from actions.server.foundry.bootstrap import create_runtime_canvas
from actions.server.managed_work_items.api import create_router
from actions.server.managed_work_items.contracts import API_PREFIX

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="private native storage currently requires Linux"
)


def test_native_bootstrap_joins_managed_identity_and_live_sql(
    database_location, tmp_path
):
    refs = _refs()
    with _runtime_database(database_location, refs.workspace, ()) as db:
        native = create_runtime_canvas(db, tmp_path / "native", "owned-key", html=HTML)
        try:
            assert native.managed_work_items.db is db
            assert native.managed_work_items.reviews.outputs.capabilities is not None
            identity = asyncio.run(
                native.managed_authenticate(
                    Request(
                        {
                            "type": "http",
                            "headers": [(b"authorization", b"Bearer owned-key")],
                        }
                    )
                )
            )
            assert identity.actor == native.actor
            assert identity.worker_id is None
            app = FastAPI()
            app.include_router(
                create_router(native.managed_work_items, native.managed_authenticate)
            )
            client = TestClient(app)
            assert client.get(API_PREFIX + "/schema").status_code == 401
            headers = {"authorization": "Bearer owned-key"}
            assert (
                client.get(API_PREFIX + "/schema", headers=headers).status_code == 200
            )
            # Merely mounting the joined service never creates Work Items grants.
            denied = client.get(
                API_PREFIX + "/capabilities",
                params={"workspace_id": str(native.workspace.root)},
                headers=headers,
            )
            assert denied.status_code == 403
            assert denied.json()["error"]["code"] == "forbidden"
        finally:
            native.close()


def test_configured_native_completion_joins_same_sql_without_retry_or_grants(
    database_location, tmp_path, monkeypatch
):
    from types import SimpleNamespace
    from uuid import uuid4

    from actions.server.foundry import bootstrap
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.managed_work_items.contracts import Operation, Permission

    refs = _refs()
    with _runtime_database(database_location, refs.workspace, ()) as db:
        initial = create_runtime_canvas(db, tmp_path / "native", "owned-key", html=HTML)
        workspace = initial.workspace
        initial.close()
        before = db.all(FoundryAccessGrant)
        # Wiring-only fixture: no descriptor validation or RCC execution claim.
        profile = SimpleNamespace(
            worker=SimpleNamespace(workspace_id=workspace),
            worker_id=str(uuid4()),
            prepared_receipt="/tmp/owned-unused",
            provider_key="owned-output-provider",
        )
        monkeypatch.setattr(bootstrap, "read_runtime_profile", lambda path: profile)
        monkeypatch.setattr(
            bootstrap, "load_prepared_rcc_environment", lambda path: object()
        )
        configured = create_runtime_canvas(
            db, tmp_path / "native", "owned-key", html=HTML
        )
        try:
            service = configured.managed_work_items
            assert service.native_completion.db is db
            assert service.native_completion.execution.worker_id == profile.worker_id
            assert service.worker_for is None
            operations = service._operations(set(Permission), False, True)
            assert Operation.COMPLETE in operations
            assert Operation.RETRY not in operations
            assert db.all(FoundryAccessGrant) == before
        finally:
            configured.close()
