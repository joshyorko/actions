"""Atomic exact-queue model publication checks on the existing SQL fixture."""

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

import pytest
from action_server_tests import test_generic_work_item_execution as fixtures

import actions.server.deployments.foundry_repository as repository_module
import actions.server.managed_work_items.model_publication as publication_module
from actions.server.deployments.foundry_values import (
    AccessDenied,
    DeploymentSpecification,
)
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.managed_work_items.contracts import (
    ManagedCaller,
    Permission,
    QueueRef,
)
from actions.server.managed_work_items.model_publication import (
    ModelWorkItemPublicationGuard,
)
from actions.server.run_outputs.models import Workspace

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def generic_world(database_location, foundry_package_store):
    source = fixtures.generic.__wrapped__(database_location, foundry_package_store)
    setup = next(source)
    try:
        yield setup("optional")
    finally:
        try:
            next(source)
        except StopIteration:
            pass


def _publish_queue_selection(g, queue_selection, idempotency_key):
    snapshot = g.owner.snapshot
    current = g.owner.deployments._repository.current(
        snapshot.deployment.workspace_id, snapshot.deployment.deployment_id
    )
    fixtures.grant(
        g.db,
        g.caller.actor,
        snapshot.deployment.workspace_id,
        "reference",
        reference_grant_subject(current.revision.ref),
        ["deploy"],
    )
    values = current.revision.specification.model_dump(mode="json", by_alias=True)
    values["model_published_work_item_queues"] = queue_selection
    selection = DeploymentSpecification.model_validate_json(json.dumps(values))
    revision = g.owner.deployments.publish(
        g.caller.actor,
        snapshot.deployment.workspace_id,
        snapshot.deployment.deployment_id,
        current.revision.ref,
        selection,
        idempotency_key=idempotency_key,
    )
    fixtures.grant(
        g.db,
        g.caller.actor,
        snapshot.deployment.workspace_id,
        "reference",
        reference_grant_subject(revision.ref),
        ["deploy", "execute", "read_application", *[p.value for p in Permission]],
    )
    return QueueRef(
        workspace_id=snapshot.deployment.workspace_id,
        deployment=revision.ref,
        queue_id="generic-input",
    )


def _published_queue(g):
    return _publish_queue_selection(
        g,
        [{"queue_id": "generic-input", "operations": ["items.list"]}],
        "model-queue-publish",
    )


def test_selected_exact_queue_runs_callback_under_counter_workspace_locks(
    generic_world, monkeypatch
):
    g = generic_world
    queue = _published_queue(g)
    caller = ManagedCaller(actor=g.caller.actor)
    guard = ModelWorkItemPublicationGuard(g.owner.deployments)
    order = []
    returning = publication_module._returning
    lock_workspace = publication_module._lock_workspace

    def record_returning(db, sql, values):
        if "UPDATE counter SET value=value" in sql:
            order.append("counter")
        return returning(db, sql, values)

    def record_workspace_lock(db, workspace_id):
        order.append("workspace")
        return lock_workspace(db, workspace_id)

    monkeypatch.setattr(publication_module, "_returning", record_returning)
    monkeypatch.setattr(publication_module, "_lock_workspace", record_workspace_lock)

    def domain_call(identity, target, operation):
        assert g.db.in_transaction()
        assert identity == caller
        assert target == queue
        assert operation == "items.list"
        return {"authorized": True}

    assert guard.call(caller, queue, "items.list", domain_call) == {"authorized": True}
    assert order == ["counter", "workspace"]


def test_unselected_queue_or_operation_is_denied_before_domain_call(generic_world):
    g = generic_world
    queue = _published_queue(g)
    caller = ManagedCaller(actor=g.caller.actor)
    guard = ModelWorkItemPublicationGuard(g.owner.deployments)
    invoked = []

    def domain_call(*args):
        invoked.append(args)

    guessed = queue.model_copy(update={"queue_id": "generic-other"})
    with pytest.raises(AccessDenied):
        guard.call(caller, guessed, "items.list", domain_call)
    with pytest.raises(AccessDenied):
        guard.call(caller, queue, "items.enqueue", domain_call)
    with pytest.raises(AccessDenied):
        guard.call(caller, queue, "items.claim", domain_call)
    assert invoked == []


def test_worker_identity_is_rejected_before_domain_call(generic_world):
    g = generic_world
    queue = _published_queue(g)
    guard = ModelWorkItemPublicationGuard(g.owner.deployments)
    invoked = []

    with pytest.raises(AccessDenied):
        guard.call(g.caller, queue, "items.list", lambda *args: invoked.append(args))
    assert invoked == []


def test_old_queue_revision_is_denied_after_active_revision_changes(generic_world):
    g = generic_world
    old_queue = _published_queue(g)
    current_queue = _publish_queue_selection(g, [], "model-queue-revoke")
    caller = ManagedCaller(actor=g.caller.actor)
    guard = ModelWorkItemPublicationGuard(g.owner.deployments)
    invoked = []

    assert old_queue.deployment != current_queue.deployment
    with pytest.raises(AccessDenied):
        guard.call(caller, old_queue, "items.list", lambda *args: invoked.append(args))
    with pytest.raises(AccessDenied):
        guard.call(
            caller,
            current_queue,
            "items.list",
            lambda *args: invoked.append(args),
        )
    assert invoked == []


def test_oversized_domain_result_rolls_back_callback_write(generic_world):
    g = generic_world
    queue = _published_queue(g)
    caller = ManagedCaller(actor=g.caller.actor)
    guard = ModelWorkItemPublicationGuard(g.owner.deployments)
    workspace_id = str(queue.workspace_id.root)
    before = g.db.all(Workspace, where="id=?", values=[workspace_id])[0].lock_version

    def domain_call(*_):
        with g.db.cursor() as cursor:
            g.db.execute_update_returning(
                cursor,
                "UPDATE workspace SET lock_version=lock_version+1 "
                "WHERE id=? RETURNING id",
                [workspace_id],
            )
            assert cursor.fetchall()
        return {"large": "x" * (512 * 1024 + 1)}

    with pytest.raises(AccessDenied):
        guard.call(caller, queue, "items.list", domain_call)
    after = g.db.all(Workspace, where="id=?", values=[workspace_id])[0].lock_version
    assert after == before


def test_inflight_queue_mutation_serializes_with_publication_revocation(
    generic_world, monkeypatch
):
    g = generic_world
    queue = _published_queue(g)
    caller = ManagedCaller(actor=g.caller.actor)
    guard = ModelWorkItemPublicationGuard(g.owner.deployments)
    repository = g.owner.deployments._repository
    publication_waiting_for_transaction = Event()
    callback_started = Event()
    finish_callback = Event()
    workspace_id = str(queue.workspace_id.root)
    current = repository.current(queue.workspace_id, queue.deployment.deployment_id)
    revoked_spec = current.revision.specification.model_dump(mode="json", by_alias=True)
    revoked_spec["model_published_work_item_queues"] = []
    revoked_specification = DeploymentSpecification.model_validate_json(
        json.dumps(revoked_spec)
    )

    original_transaction = repository_module._transaction

    @contextmanager
    def observe_publication_transaction(db):
        publication_waiting_for_transaction.set()
        with original_transaction(db):
            yield

    monkeypatch.setattr(
        repository_module, "_transaction", observe_publication_transaction
    )

    def mutate_queue(*_):
        assert g.db.in_transaction()
        with g.db.cursor() as cursor:
            g.db.execute_update_returning(
                cursor,
                "UPDATE workspace SET lock_version=lock_version+1 "
                "WHERE id=? RETURNING id",
                [workspace_id],
            )
            assert cursor.fetchall()
        callback_started.set()
        if not finish_callback.wait(timeout=15):
            raise TimeoutError("guard callback release timed out")
        return {"mutation": "committed"}

    def revoke_publication():
        return g.owner.deployments.publish(
            g.caller.actor,
            queue.workspace_id,
            queue.deployment.deployment_id,
            queue.deployment,
            revoked_specification,
            idempotency_key="model-queue-concurrent-revoke",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        guarded_call = pool.submit(
            guard.call, caller, queue, "items.list", mutate_queue
        )
        try:
            assert callback_started.wait(timeout=15)
            revocation = pool.submit(revoke_publication)
            assert publication_waiting_for_transaction.wait(timeout=15)
            assert not revocation.done()
        finally:
            finish_callback.set()
        assert guarded_call.result(timeout=15) == {"mutation": "committed"}
        revoked_revision = revocation.result(timeout=15)

    assert revoked_revision.ref != queue.deployment
    with pytest.raises(AccessDenied):
        guard.call(caller, queue, "items.list", lambda *_: {"unexpected": True})
