"""Full bound publication wrapper must not reopen provider or Package files."""
import json

import pytest
from action_server_tests.test_generated_knowledge import (
    generated_knowledge as knowledge_execution_fixture,
)
from action_server_tests.test_generated_knowledge import knowledge as knowledge_fixture
from action_server_tests.test_generated_knowledge import publish_generated
from action_server_tests.test_local_provider_setup import local as local_fixture
from action_server_tests.test_local_provider_setup import provider as provider_fixture
from action_server_tests.test_logical_domain import domain as domain_fixture
from action_server_tests.test_logical_domain import logical as logical_fixture
from action_server_tests.test_logical_domain import measured, prepare, setup
from action_server_tests.test_logical_domain import tls_postgres as tls_fixture
from actions.work_items import State

from actions.server._models import Run, RunStatus
from actions.server.run_outputs.service import _one

local, provider, logical = local_fixture, provider_fixture, logical_fixture
knowledge, generated_knowledge = knowledge_fixture, knowledge_execution_fixture
domain, tls_postgres = domain_fixture, tls_fixture


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def forbid_io(g, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError(
            "full final publication performed file/provider projection I/O"
        )

    monkeypatch.setattr(type(g.blobs), "open", forbidden)
    monkeypatch.setattr(g.registry, "load_verified", forbidden)
    monkeypatch.setattr(g.registry, "schema_for", forbidden)
    monkeypatch.setattr(g.execution.deployments, "resolve", forbidden)
    monkeypatch.setattr(g.factory.registry, "_read", forbidden)


def test_standalone_full_publish_sql_only(domain, monkeypatch):
    g = domain
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        forbid_io(g, monkeypatch)
        with g.db.transaction():
            published = wrapper.publish(g.actor, g.fence, refs, result)
        assert published.status == RunStatus.PASSED
    g.execution.release(prepared)


def test_knowledge_full_publish_sql_only(generated_knowledge, monkeypatch):
    g = generated_knowledge
    prepared = prepare(g)
    owner, caller, wrapper, refs, result = publish_generated(g, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        forbid_io(g, monkeypatch)
        with g.db.transaction():
            published = wrapper.publish(g.actor, g.fence, refs, result)
        assert published.status == RunStatus.PASSED
    g.execution.release(prepared)


def test_generic_queue_full_publish_sql_only(domain, monkeypatch):
    from action_server_tests.test_generic_work_item_execution import grant

    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.foundry.generic_work_item_execution import (
        GenericWorkItemExecution,
    )
    from actions.server.foundry.sql_authorization import reference_grant_subject
    from actions.server.managed_work_items.authorization import SqlQueueAuthorization
    from actions.server.managed_work_items.contracts import ManagedCaller, Permission

    g = domain
    snapshot = g.outputs.execution_context(g.actor, g.fence)[0]
    policy = g.execution.repository.get_revision(
        snapshot.deployment
    ).revision.specification.work_item_policies[0]
    grant(
        g.db,
        g.actor,
        g.workspace,
        "reference",
        reference_grant_subject(snapshot.deployment),
        [p.value for p in Permission],
    )
    grant(
        g.db,
        g.actor,
        g.workspace,
        "workspace",
        str(g.workspace.root),
        [p.value for p in Permission],
    )
    owner = GenericWorkItemExecution(
        g.execution.deployments,
        g.outputs,
        snapshot,
        policy,
        SqlQueueAuthorization(g.db),
    )
    caller = ManagedCaller(actor=g.actor, worker_id=g.fence.owner_id)
    item = owner.enqueue(caller, {"value": "fixture"}, "publication-no-io")
    claim = owner.queue(policy.input_queue).reserve_item_fenced(
        item, caller.worker_id, lease_seconds=60
    )
    ticket = owner.dispatch(caller, claim, lease_seconds=60)
    g.fence = ticket.fence
    wrapper = owner.outputs(caller, ticket)
    seed = json.loads(_one(g.db, Run, g.fence.run_id).result)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        forbid_io(g, monkeypatch)
        with g.db.transaction():
            published = wrapper.publish(g.actor, g.fence, refs, result)
        assert published.status == RunStatus.PASSED
        assert _one(g.db, FencedWorkItem, item).state == State.DONE.value
    g.execution.release(prepared)


@pytest.mark.parametrize("mutation", ["grant", "package"])
def test_bound_publish_rechecks_sql_authority_without_io(domain, monkeypatch, mutation):
    from actions.server.foundry.models import FoundryAccessGrant, FoundryPackageRevision
    from actions.server.run_outputs.service import _update

    g = domain
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        forbid_io(g, monkeypatch)
        with g.db.transaction():
            if mutation == "grant":
                for grant in g.db.all(FoundryAccessGrant):
                    if grant.principal_id == g.actor.principal_id:
                        _update(
                            g.db,
                            FoundryAccessGrant,
                            grant.id,
                            {"operations_json": "[]"},
                        )
            else:
                row = g.db.all(FoundryPackageRevision)[0]
                _update(g.db, FoundryPackageRevision, row.id, {"manifest_json": "{}"})
            with pytest.raises((ValueError, PermissionError)):
                wrapper.publish(g.actor, g.fence, refs, result)
        assert _one(g.db, Run, g.fence.run_id).status != RunStatus.PASSED
    g.execution.release(prepared)
