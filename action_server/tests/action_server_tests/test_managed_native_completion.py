"""Native terminal receipt readback; synthetic publication, never RCC acceptance."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests import test_managed_work_items_sql_service as fixtures
from action_server_tests.test_activated_reviewed_execution import (
    adapter,
    release,
    setup_activated,
)
from action_server_tests.test_managed_work_items_sql_service import (
    _caller,
    _Policy,
    _queue,
)

from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import (
    ClaimRef,
    Complete,
    Operation,
    Permission,
)
from actions.server.managed_work_items.native_completion import NativeTerminalCompletion
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = fixtures.provider
reviewed = fixtures.reviewed


@pytest.fixture
def completed(reviewed, foundry_package_store):
    case = setup_activated(reviewed, foundry_package_store)
    case.reviews.outputs = case.outputs
    case.reviews.queries.outputs = case.outputs
    release(case)
    approved = case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    first = case.reviews.queue(case.scope).reserve_item_fenced(
        approved.work_item_id, str(uuid4()), lease_seconds=30
    )
    with case.db.transaction():
        case.db.update_by_id(FencedWorkItem, first.item_id, {"claim_deadline_ms": "0"})
    execution = adapter(case)
    ticket = execution.dispatch(case.actor, case.scope, "run", case.proposal)
    assert ticket.claim.epoch == 2 and ticket.fence.epoch == 1
    owner = execution.resume(case.actor, ticket)
    outputs = owner.outputs(case.actor, ticket)
    refs, receipts = [], []
    for name, media, value in (
        ("generated-action-result.json", "application/json", b'{"ok":true}'),
        ("rcc-receipt.json", "application/json", b'{"fixture":true}'),
        ("rcc-stdout.log", "application/octet-stream", b"out"),
        ("rcc-stderr.log", "application/octet-stream", b""),
    ):
        ref = outputs.stage(
            ticket.fence, [value], name=name, media_type=media, retention_seconds=300
        )
        refs.append(ref)
        receipts.append(
            {
                "name": name,
                "ref": ref.model_dump(mode="json"),
                "digest": "sha256:" + hashlib.sha256(value).hexdigest(),
                "size": len(value),
            }
        )
    outputs.publish(
        case.actor,
        ticket.fence,
        refs,
        {
            "version": "actions.generated-rcc-execution/v1",
            "mode": "work-items",
            "claim": ticket.claim.model_dump(),
            "publicationFence": ticket.fence.model_dump(),
            "outputs": receipts,
        },
    )
    queue = _queue(case.reviews, case.scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(case.actor, Permission.READ, Permission.COMPLETE)
    native = NativeTerminalCompletion(execution)

    def service():
        return SQLManagedWorkItemsService(
            case.reviews, policy, native_completion=native
        )

    command = Complete(
        operation="items.complete",
        queue=queue,
        idempotency_key="native-complete",
        claim=ClaimRef(
            queue=queue,
            item_id=ticket.claim.item_id,
            owner_id=ticket.claim.owner_id,
            epoch=ticket.claim.epoch,
        ),
        outcome="done",
    )
    return SimpleNamespace(
        case=case,
        ticket=ticket,
        refs=refs,
        policy=policy,
        queue=queue,
        service=service,
        command=command,
        caller=_caller(case.actor, ticket.claim.owner_id),
    )


def test_native_complete_is_authorized_readback_not_execution(completed, monkeypatch):
    from actions.work_items._adapters._sql_review import SQLReviewQueue

    from actions.server.foundry.rcc_execution import GeneratedRccExecution

    c = completed
    before = {
        model: len(c.case.db.all(model))
        for model in (Run, RunAttempt, RunOutput, FencedWorkItem)
    }

    def forbidden(*args, **kwargs):
        pytest.fail("terminal readback must never execute or finish again")

    monkeypatch.setattr(SQLReviewQueue, "finish_fenced", forbidden)
    monkeypatch.setattr(GeneratedRccExecution, "execute", forbidden)
    capabilities = c.service().capabilities(c.caller, c.queue.workspace_id)
    assert Operation.COMPLETE in capabilities.operations
    assert Operation.RETRY not in capabilities.operations
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: c.service().call(c.caller, c.command), range(2))
        )
    first = results[0]
    assert sum(result["replay"] for result in results) == 1
    replay = c.service().call(c.caller, c.command)
    assert first["item"]["queue_state"] == "DONE"
    assert replay["replay"] is True
    assert {model: len(c.case.db.all(model)) for model in before} == before
    receipts = [
        r
        for r in c.case.db.all(FoundryRequest)
        if r.operation.endswith("items.complete")
    ]
    assert len(receipts) == 1
    assert (
        len(
            [
                a
                for a in c.case.db.all(FoundryAudit)
                if a.foundry_request_id == receipts[0].id
            ]
        )
        == 1
    )


@pytest.mark.parametrize(
    "change",
    [
        "owner",
        "claim",
        "attempt",
        "pin",
        "inputs",
        "permission",
        "output",
        "client-output",
        "package-grant",
        "cancel",
        "output-expired",
        "queue",
    ],
)
def test_native_completion_rejects_changed_authority(completed, change):
    c = completed
    c.service().call(c.caller, c.command)
    command = c.command
    if change == "owner":
        c.caller = _caller(c.case.actor, str(uuid4()))
    elif change == "claim":
        command = command.model_copy(
            update={"claim": command.claim.model_copy(update={"epoch": 3})}
        )
    elif change == "permission":
        c.policy.grant(c.case.actor, Permission.READ)
    elif change == "client-output":
        command = command.model_copy(update={"output_payloads": ({"forged": True},)})
    elif change == "queue":
        other = command.queue.model_copy(update={"queue_id": "other"})
        command = command.model_copy(
            update={
                "queue": other,
                "claim": command.claim.model_copy(update={"queue": other}),
            }
        )
    else:
        with c.case.db.transaction():
            if change == "attempt":
                c.case.db.update_by_id(
                    RunAttempt, c.ticket.fence.attempt_id, {"epoch": 2}
                )
            elif change == "pin":
                c.case.db.update_by_id(RunPin, c.ticket.fence.run_id, {"epoch": 2})
            elif change == "inputs":
                c.case.db.update_by_id(
                    Run, c.ticket.fence.run_id, {"inputs": '{"value":"changed"}'}
                )
            elif change == "package-grant":
                for grant in c.case.db.all(FoundryAccessGrant):
                    c.case.db.update_by_id(
                        FoundryAccessGrant, grant.id, {"operations_json": "[]"}
                    )
            elif change == "cancel":
                c.case.db.update_by_id(
                    FencedWorkItem, c.ticket.claim.item_id, {"cancel_requested": 1}
                )
            elif change == "output-expired":
                c.case.db.update_by_id(
                    RunOutput, c.refs[0].output_id, {"expires_ms": "0"}
                )
            else:
                c.case.db.update_by_id(
                    RunOutput, c.refs[0].output_id, {"digest": "sha256:" + "0" * 64}
                )
    with pytest.raises(ManagedError):
        c.service().call(c.caller, command)


@pytest.mark.parametrize("model", [FoundryRequest, FoundryAudit])
def test_native_completion_receipt_failure_rolls_back(completed, monkeypatch, model):
    c = completed
    before = {cls: len(c.case.db.all(cls)) for cls in (FoundryRequest, FoundryAudit)}
    insert = c.case.db.insert

    def fail(value):
        insert(value)
        if isinstance(value, model):
            raise RuntimeError("synthetic receipt failure")

    with monkeypatch.context() as patch:
        patch.setattr(c.case.db, "insert", fail)
        with pytest.raises(ManagedError, match="storage_unavailable"):
            c.service().call(c.caller, c.command)
    assert {cls: len(c.case.db.all(cls)) for cls in before} == before
    assert c.service().call(c.caller, c.command)["item"]["queue_state"] == "DONE"


def test_native_completion_does_not_reopen_expired_source(completed):
    from actions.server.run_outputs.types import output_id_from_handle

    c = completed
    with c.case.db.transaction():
        c.case.db.update_by_id(
            RunOutput,
            output_id_from_handle(c.case.proposal.binding.handle),
            {"expires_ms": "0"},
        )
    assert c.service().call(c.caller, c.command)["item"]["queue_state"] == "DONE"
