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
