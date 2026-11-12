"""Retained exact input seals outlive query handles without granting authority.

These real-SQL publication cases use synthetic output receipts; actual pinned
RCC execution and installed replay are qualified by the dedicated RCC gate.
"""

import json

import pytest
from action_server_tests import test_generated_work_item_execution as fixtures
from action_server_tests.test_activated_reviewed_execution import (
    adapter,
    release,
    setup_activated,
)
from actions.work_items import State

from actions.server._models import Run
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
)
from actions.server.run_outputs.types import output_id_from_handle

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = fixtures.pytestmark
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def expire_source(service, ticket):
    with service.db.transaction():
        service.db.update_by_id(
            RunOutput,
            output_id_from_handle(ticket.proposal.binding.handle),
            {"expires_ms": "0"},
        )


@pytest.mark.parametrize("completed", [False, True])
def test_admitted_exact_inputs_replay_after_source_expiry(
    reviewed, foundry_package_store, completed
):
    service, actor, ticket = fixtures.approved_ticket(reviewed, foundry_package_store)
    outputs = service.outputs(actor, ticket)
    if completed:
        output = outputs.stage(
            ticket.fence,
            [b'"synthetic retained result"'],
            name="result.json",
            media_type="application/json",
            retention_seconds=300,
        )
        outputs.publish(actor, ticket.fence, [output], fixtures.receipt(ticket))
    before = len(service.db.all(Run))
    expire_source(service, ticket)
    assert (
        service.dispatch(
            actor, ticket.proposal, ticket.claim.as_claim(), lease_seconds=30
        )
        == ticket
    )
    assert len(service.db.all(Run)) == before
    item = next(
        item
        for item in service.reviews.queue(service.scope).list_items()
        if item["id"] == ticket.claim.item_id
    )
    assert item["claim_epoch"] == ticket.claim.epoch
    assert item["state"] == (State.DONE.value if completed else State.IN_PROGRESS.value)
    if completed:
        with service.base.resolve(
            actor,
            service.scope.application.workspace_id,
            output.handle,
            canvas_scope=service.scope,
        ) as found:
            assert found.read() == b'"synthetic retained result"'
    else:
        outputs.heartbeat(ticket.fence, lease_seconds=30)
        assert outputs.execution_context(actor, ticket.fence)[1]["value"]
        output = outputs.stage(
            ticket.fence,
            [b'"completed after query expiry"'],
            name="result.json",
            media_type="application/json",
            retention_seconds=300,
        )
        outputs.publish(actor, ticket.fence, [output], fixtures.receipt(ticket))
        assert (
            service.dispatch(
                actor, ticket.proposal, ticket.claim.as_claim(), lease_seconds=30
            )
            == ticket
        )


@pytest.mark.parametrize("tamper", ["value", "extra", "not-object", "noncanonical"])
def test_retained_input_replay_rejects_changed_shape_bytes_or_canonical_seal(
    reviewed, foundry_package_store, tamper
):
    service, actor, ticket = fixtures.approved_ticket(reviewed, foundry_package_store)
    run = service.db.first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id])
    original = json.loads(run.inputs)
    changed = (
        {"value": "altered exact result"}
        if tamper == "value"
        else dict(original, replacement="denied")
        if tamper == "extra"
        else [original]
    )
    raw = (
        " " + run.inputs
        if tamper == "noncanonical"
        else json.dumps(changed, separators=(",", ":"), sort_keys=True)
    )
    with service.db.transaction():
        service.db.update_by_id(Run, run.id, {"inputs": raw})
    expire_source(service, ticket)
    # Immutable admission rejects mutation before the retained seal is read.
    with pytest.raises(AccessDenied):
        service.dispatch(
            actor, ticket.proposal, ticket.claim.as_claim(), lease_seconds=30
        )
    from actions.server.foundry.work_item_execution import require_reviewed_run_inputs

    with pytest.raises(FenceRejected):
        require_reviewed_run_inputs(
            service.db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]),
            ticket.proposal,
        )


def test_expired_source_does_not_grant_new_dispatch_or_resurrect_live_authorization(
    reviewed, foundry_package_store
):
    case = setup_activated(reviewed, foundry_package_store)
    release(case)
    case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    with case.db.transaction():
        case.db.update_by_id(
            RunOutput,
            output_id_from_handle(case.proposal.binding.handle),
            {"expires_ms": "0"},
        )
    before = len(case.db.all(Run))
    with pytest.raises(AccessDenied):
        adapter(case).dispatch(case.actor, case.scope, "run", case.proposal)
    assert len(case.db.all(Run)) == before
    assert all(
        item["claim_epoch"] == 0 for item in case.reviews.queue(case.scope).list_items()
    )


def test_retained_replay_rechecks_revocation_after_query_expiry(
    reviewed, foundry_package_store
):
    service, actor, ticket = fixtures.approved_ticket(reviewed, foundry_package_store)
    expire_source(service, ticket)
    RunOutputControlPlane(service.db).revoke(actor, service.scope.deployment)
    with pytest.raises((AccessDenied, PermissionError)):
        service.dispatch(
            actor, ticket.proposal, ticket.claim.as_claim(), lease_seconds=30
        )
