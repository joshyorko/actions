"""Trusted Deployment-backed model Work Item publication policy tests."""

import asyncio
import json
from uuid import uuid4

import pytest
from action_server_tests import test_generic_work_item_execution as generic_fixtures
from starlette.concurrency import run_in_threadpool

from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.deployments.foundry_values import DeploymentSpecification
from actions.server.foundry.models import FoundryAccessGrant, FoundryDeploymentHead
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.managed_work_items import publication_policy as policy_module
from actions.server.managed_work_items.authorization import SqlQueueAuthorization
from actions.server.managed_work_items.composite import CompositeManagedWorkItemsService
from actions.server.managed_work_items.contracts import (
    ManagedCaller,
    Operation,
    Permission,
    QueueRef,
)
from actions.server.managed_work_items.publication_policy import (
    DeploymentModelWorkItemPublicationPolicy,
)
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def generic_world(database_location, foundry_package_store):
    source = generic_fixtures.generic.__wrapped__(
        database_location, foundry_package_store
    )
    setup = next(source)
    try:
        yield setup("optional")
    finally:
        try:
            next(source)
        except StopIteration:
            pass


def _publish_queues(g, selections, key):
    snapshot = g.owner.snapshot
    current = g.owner.deployments._repository.current(
        snapshot.deployment.workspace_id, snapshot.deployment.deployment_id
    )
    generic_fixtures.grant(
        g.db,
        g.caller.actor,
        snapshot.deployment.workspace_id,
        "reference",
        reference_grant_subject(current.revision.ref),
        ["deploy"],
    )
    values = current.revision.specification.model_dump(mode="json", by_alias=True)
    values["model_published_work_item_queues"] = selections
    spec = DeploymentSpecification.model_validate_json(json.dumps(values))
    revision = g.owner.deployments.publish(
        g.caller.actor,
        snapshot.deployment.workspace_id,
        snapshot.deployment.deployment_id,
        current.revision.ref,
        spec,
        idempotency_key=key,
    )
    generic_fixtures.grant(
        g.db,
        g.caller.actor,
        snapshot.deployment.workspace_id,
        "reference",
        reference_grant_subject(revision.ref),
        [
            "deploy",
            "execute",
            "read_application",
            *[permission.value for permission in Permission],
        ],
    )
    return QueueRef(
        workspace_id=snapshot.deployment.workspace_id,
        deployment=revision.ref,
        queue_id="generic-input",
    )


def _composite_port(g):
    reviews = InvoiceReviewService(InvoiceQueryService(g.owner.base, {}))
    reviewed = SQLManagedWorkItemsService(reviews, SqlQueueAuthorization(g.db))
    return CompositeManagedWorkItemsService(reviewed, g.owner.deployments, g.owner.base)


def test_policy_intersects_current_exact_publication_with_composite_catalog(
    generic_world,
):
    g = generic_world
    queue = _publish_queues(
        g,
        [
            {
                "queue_id": "generic-input",
                "operations": ["items.list", "items.enqueue"],
            },
            {"queue_id": "unpublished-secret", "operations": ["items.list"]},
        ],
        "publication-policy-current",
    )
    caller = ManagedCaller(actor=g.caller.actor)
    policy = DeploymentModelWorkItemPublicationPolicy(
        g.owner.deployments,
        _composite_port(g),
        caller.actor,
        queue.workspace_id,
    )

    assert policy.workspaces(caller) == (str(queue.workspace_id.root),)
    assert policy.queues(caller, queue.workspace_id, Operation.LIST) == (queue,)
    assert policy.queues(caller, queue.workspace_id, Operation.ENQUEUE) == (queue,)
    assert policy.queues(caller, queue.workspace_id, Operation.CANCEL) == ()


def test_policy_resolves_exact_selected_queue_in_worker_thread(generic_world):
    g = generic_world
    queue = _publish_queues(
        g,
        [{"queue_id": "generic-input", "operations": ["items.list"]}],
        "publication-policy-worker-thread",
    )
    caller = ManagedCaller(actor=g.caller.actor)
    policy = DeploymentModelWorkItemPublicationPolicy(
        g.owner.deployments,
        _composite_port(g),
        caller.actor,
        queue.workspace_id,
    )

    async def resolve():
        return await run_in_threadpool(
            policy.queues, caller, queue.workspace_id, Operation.LIST
        )

    assert asyncio.run(resolve()) == (queue,)


def test_policy_rechecks_current_head_and_live_queue_grants(generic_world):
    g = generic_world
    queue = _publish_queues(
        g,
        [{"queue_id": "generic-input", "operations": ["items.list", "items.enqueue"]}],
        "publication-policy-live-grants",
    )
    caller = ManagedCaller(actor=g.caller.actor)
    port = _composite_port(g)
    policy = DeploymentModelWorkItemPublicationPolicy(
        g.owner.deployments, port, caller.actor, queue.workspace_id
    )

    assert policy.queues(caller, queue.workspace_id, Operation.ENQUEUE) == (queue,)
    grants = g.db.all(
        FoundryAccessGrant,
        where="principal_id=? AND subject_kind='reference' AND subject_id=?",
        values=[g.caller.actor.principal_id, reference_grant_subject(queue.deployment)],
    )
    assert len(grants) == 1
    with g.db.connect(), g.db.transaction():
        g.db.update_by_id(
            FoundryAccessGrant,
            grants[0].id,
            {"operations_json": json.dumps(["deploy", "execute", "work_items.read"])},
        )

    assert policy.queues(caller, queue.workspace_id, Operation.LIST) == (queue,)
    assert policy.queues(caller, queue.workspace_id, Operation.ENQUEUE) == ()

    _publish_queues(g, [], "publication-policy-revoke")
    assert policy.queues(caller, queue.workspace_id, Operation.LIST) == ()


def test_policy_rejects_wrong_actor_worker_identity_and_other_workspace(generic_world):
    g = generic_world
    queue = _publish_queues(
        g,
        [{"queue_id": "generic-input", "operations": ["items.list"]}],
        "publication-policy-caller",
    )
    caller = ManagedCaller(actor=g.caller.actor)
    policy = DeploymentModelWorkItemPublicationPolicy(
        g.owner.deployments,
        _composite_port(g),
        caller.actor,
        queue.workspace_id,
    )

    assert (
        policy.workspaces(ManagedCaller(actor=Actor(principal_id=str(uuid4())))) == ()
    )
    assert (
        policy.queues(
            ManagedCaller(actor=caller.actor, worker_id=str(uuid4())),
            queue.workspace_id,
            Operation.LIST,
        )
        == ()
    )
    assert (
        policy.queues(
            caller,
            type(queue.workspace_id)(uuid4()),
            Operation.LIST,
        )
        == ()
    )


def test_policy_fails_closed_on_bounded_current_head_overflow(
    generic_world, monkeypatch
):
    g = generic_world
    queue = _publish_queues(
        g,
        [{"queue_id": "generic-input", "operations": ["items.list"]}],
        "publication-policy-overflow",
    )
    caller = ManagedCaller(actor=g.caller.actor)
    port = _composite_port(g)
    policy = DeploymentModelWorkItemPublicationPolicy(
        g.owner.deployments, port, caller.actor, queue.workspace_id
    )
    monkeypatch.setattr(policy_module, "MAX_CURRENT_DEPLOYMENTS", 1)
    original_select = g.db.select
    calls = []

    def overfull_select(model, query, values):
        if model is FoundryDeploymentHead:
            calls.append(model)
            rows = original_select(model, query, values)
            return rows + rows
        return original_select(model, query, values)

    monkeypatch.setattr(g.db, "select", overfull_select)
    assert policy.queues(caller, queue.workspace_id, Operation.LIST) == ()
    assert calls
