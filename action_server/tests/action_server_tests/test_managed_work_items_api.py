"""Authenticated transport tests; this port fixture is not managed SQL acceptance."""

import asyncio
from uuid import uuid4

import httpx2
from fastapi import FastAPI

from actions.server.managed_work_items.api import ManagedError, create_router
from actions.server.managed_work_items.contracts import (
    API_PREFIX,
    Capabilities,
    ManagedCaller,
    Operation,
    Permission,
)
from actions.server.run_outputs.types import Actor


def test_unconfigured_managed_route_never_falls_back_to_legacy_storage(monkeypatch):
    def forbidden():
        raise AssertionError("managed transport used legacy storage")

    monkeypatch.setattr("actions.server._api_work_items._get_adapter", forbidden)
    app = FastAPI()
    app.include_router(create_router(None, None))

    async def check():
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://127.0.0.1"
        ) as client:
            response = await client.get(
                API_PREFIX + "/capabilities", params={"workspace_id": str(uuid4())}
            )
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "unconfigured"

    asyncio.run(check())


def test_auth_permission_worker_identity_and_safe_errors_are_transport_enforced():
    workspace, actor_id, worker_id = (str(uuid4()) for _ in range(3))
    queue = {
        "workspace_id": workspace,
        "deployment": {
            "workspace_id": workspace,
            "deployment_id": str(uuid4()),
            "revision_id": "sha256:" + "a" * 64,
        },
        "queue_id": "owned",
    }

    class Port:
        calls = 0

        def capabilities(self, caller, requested):
            if str(requested.root) != workspace:
                raise ManagedError("forbidden")
            operations = (
                Operation.GET,
                Operation.LIST,
                Operation.CLAIM,
                Operation.RENEW,
            )
            return Capabilities(
                runtime_version="1.1.0a13",
                sdk_version="0.5.0a1",
                workspace_id=requested,
                operations=operations,
                permissions=(Permission.READ, Permission.CLAIM),
                backend="sqlite",
                modes=("reviewed",),
            )

        def call(self, caller, command):
            self.calls += 1
            if command.operation == "items.get":
                raise RuntimeError("private-provider-path-must-not-leak")
            if command.operation == "items.renew":
                raise ManagedError("stale_claim")
            if command.operation == "items.claim":
                return {
                    "item": None,
                    "claim": None,
                    "lease_deadline_ms": None,
                    "server_time_ms": "0",
                }
            return {"items": [], "server_time_ms": "0"}

    port = Port()

    async def authenticate(request):
        token = request.headers.get("authorization")
        if token not in {"Bearer synthetic-reader", "Bearer synthetic-worker"}:
            return None
        return ManagedCaller(
            actor=Actor(principal_id=actor_id),
            worker_id=worker_id if token.endswith("worker") else None,
        )

    app = FastAPI()
    app.include_router(create_router(port, authenticate))

    async def check():
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://127.0.0.1"
        ) as client:
            url = API_PREFIX + "/operations"
            command = {"operation": "items.list", "queue": queue}
            assert (await client.post(url, json=command)).status_code == 401
            client.headers["authorization"] = "Bearer synthetic-reader"
            assert (await client.post(url, json=command)).status_code == 200
            assert port.calls == 1
            claim = {
                "operation": "items.claim",
                "queue": queue,
                "idempotency_key": "claim",
                "lease_seconds": 30,
            }
            assert (await client.post(url, json=claim)).status_code == 403
            assert (
                await client.post(url, json=dict(claim, owner_id=worker_id))
            ).status_code == 422
            client.headers["authorization"] = "Bearer synthetic-worker"
            assert (await client.post(url, json=claim)).status_code == 200
            fence = {
                "queue": queue,
                "item_id": str(uuid4()),
                "owner_id": str(uuid4()),
                "epoch": 1,
            }
            renew = dict(claim, operation="items.renew", claim=fence)
            assert (await client.post(url, json=renew)).status_code == 403
            fence["owner_id"] = worker_id
            assert (await client.post(url, json=renew)).status_code == 409
            failed = await client.post(
                url,
                json={
                    "operation": "items.get",
                    "queue": queue,
                    "item_id": str(uuid4()),
                },
            )
            assert failed.status_code == 503 and "private-provider" not in failed.text
            before = port.calls
            assert (
                await client.post(
                    url, content=b'{"operation":"items.list","operation":"items.claim"}'
                )
            ).status_code == 422
            assert (
                await client.post(url, content=b" " * (512 * 1024 + 1))
            ).status_code == 413
            assert port.calls == before
            assert (await client.get(API_PREFIX + "/schema")).status_code == 200

    asyncio.run(check())
