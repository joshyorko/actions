"""Common SQL catalog routing preserves exact immutable admission authority."""
import asyncio
import json

import httpx
import pytest
from action_server_tests import test_generic_work_item_execution as generic_fixtures
from fastapi import FastAPI

from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.managed_work_items.api import create_router
from actions.server.managed_work_items.composite import CompositeManagedWorkItemsService
from actions.server.managed_work_items.contracts import API_PREFIX, Enqueue, Queues
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService

pytest_plugins = ["action_server_tests.foundry_fixtures"]
generic = generic_fixtures.generic


def service(g):
    reviewed = SQLManagedWorkItemsService(
        InvoiceReviewService(InvoiceQueryService(g.owner.base, {})),
        g.owner.authorization,
    )
    return CompositeManagedWorkItemsService(reviewed, g.owner.deployments, g.owner.base)


def test_catalog_discovers_explicit_policy_before_first_item(generic):
    g = generic()
    composite = service(g)
    query = Queues(
        operation="queues.list", workspace_id=g.owner.snapshot.deployment.workspace_id
    )
    before = composite.call(g.caller, query)
    assert len(before["queues"]) == 1
    queue = g.owner.queue_ref(g.owner.policy.input_queue)
    assert before["queues"][0]["queue"] == queue.model_dump(mode="json")
    command = Enqueue(
        operation="items.enqueue",
        queue=queue,
        snapshot=g.owner.snapshot,
        payload={"value": "generic"},
        idempotency_key="http-item",
    )

    async def check():
        app = FastAPI()

        async def authenticate(_):
            return g.caller

        app.include_router(create_router(composite, authenticate))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                API_PREFIX + "/operations", json=command.model_dump(mode="json")
            )
            assert response.status_code == 200, response.text
            return response.json()["result"]

    result = asyncio.run(check())
    assert result["item"]["payload"] == {"value": "generic"}
    assert composite.call(g.caller, query)["queues"][0]["counts"]["PENDING"] == 1
    assert composite.call(g.caller, command)["item"]["id"] == result["item"]["id"]


@pytest.mark.parametrize("unsupported", ["caller-choice", "output-routing"])
def test_unsupported_unreadable_policy_does_not_disable_existing_queue(
    generic, unsupported
):
    from actions.server.deployments.foundry_values import DeploymentSpecification
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.run_outputs.service import _update

    g = generic(outputs=True)
    original = g.owner.snapshot.deployment
    repository = g.owner.deployments._repository
    stored = repository.get_revision(original)
    values = stored.revision.specification.model_dump(mode="json")
    if unsupported == "caller-choice":
        values["capability_plans"][0]["mode"] = "caller-may-choose"
        values["capability_plans"][0]["default_plan"] = None
    else:
        values["work_item_policies"][0]["output_queue"] = "unsupported-target"
    with g.db.transaction():
        _update(
            g.db,
            FoundryAccessGrant,
            g.grant.id,
            {
                "operations_json": json.dumps(
                    json.loads(g.grant.operations_json) + ["deploy"]
                )
            },
        )
    new = g.owner.deployments.publish(
        g.caller.actor,
        original.workspace_id,
        original.deployment_id,
        original,
        DeploymentSpecification.model_validate_json(json.dumps(values)),
        idempotency_key="unsupported",
    )
    assert new.ref != original
    composite = service(g)
    page = composite.call(
        g.caller, Queues(operation="queues.list", workspace_id=original.workspace_id)
    )
    assert len(page["queues"]) == 1
    assert (
        page["queues"][0]["queue"]["deployment"]["revision_id"]
        == original.revision_id.root
    )
