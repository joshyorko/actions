"""Real SQL domain adapter tests; no generated execution evidence implied."""
import pytest
from action_server_tests import test_generic_work_item_execution as _domain

from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import (
    Claim,
    Enqueue,
    Inspect,
    Operation,
    Queues,
    Renew,
)
from actions.server.managed_work_items.generic_service import (
    GenericManagedWorkItemsService,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def generic(database_location, foundry_package_store):
    yield from _domain.generic.__wrapped__(database_location, foundry_package_store)


def service(g):
    return GenericManagedWorkItemsService(g.owner)


def enqueue(g, key="enqueue"):
    return Enqueue(
        operation="items.enqueue",
        queue=g.owner.queue_ref(g.owner.policy.input_queue),
        snapshot=g.owner.snapshot,
        payload={"value": "managed"},
        idempotency_key=key,
    )


def test_discovery_enqueue_restart_single_receipt(generic):
    g = generic()
    s = service(g)
    caps = s.capabilities(g.caller, enqueue(g).queue.workspace_id)
    assert Operation.ENQUEUE in caps.operations
    assert Operation.RETRY not in caps.operations
    page = s.call(
        g.caller,
        Queues(operation="queues.list", workspace_id=enqueue(g).queue.workspace_id),
    )
    assert len(page["queues"]) == 1
    before = len(g.db.all(FoundryRequest))
    first = s.call(g.caller, enqueue(g))
    assert service(g).call(g.caller, enqueue(g))["item"]["id"] == first["item"]["id"]
    assert len(g.db.all(FoundryRequest)) == before + 1
    assert len(g.db.all(FencedWorkItem)) == 1
    assert not first["item"]["run_ids"]


def test_claim_renew_replay_no_new_epoch(generic):
    g = generic()
    s = service(g)
    s.call(g.caller, enqueue(g))
    c = Claim(
        operation="items.claim",
        queue=enqueue(g).queue,
        idempotency_key="claim",
        lease_seconds=60,
    )
    first = s.call(g.caller, c)
    assert service(g).call(g.caller, c)["claim"] == first["claim"]
    from actions.server.managed_work_items.contracts import ClaimRef

    ref = ClaimRef.model_validate_json(__import__("json").dumps(first["claim"]))
    renew = Renew(
        operation="items.renew",
        queue=c.queue,
        idempotency_key="renew",
        claim=ref,
        lease_seconds=120,
    )
    result = s.call(g.caller, renew)
    assert (
        service(g).call(g.caller, renew)["lease_deadline_ms"]
        == result["lease_deadline_ms"]
    )
    assert g.db.all(FencedWorkItem)[0].claim_epoch == 1


def test_claim_audit_failure_rolls_back(generic, monkeypatch):
    g = generic()
    s = service(g)
    s.call(g.caller, enqueue(g))
    insert = g.db.insert

    def broken(row):
        if isinstance(row, FoundryAudit):
            raise RuntimeError("synthetic audit failure")
        return insert(row)

    monkeypatch.setattr(g.db, "insert", broken)
    with pytest.raises(ManagedError):
        s.call(
            g.caller,
            Claim(
                operation="items.claim",
                queue=enqueue(g).queue,
                idempotency_key="claim",
                lease_seconds=60,
            ),
        )
    assert g.db.all(FencedWorkItem)[0].claim_epoch == 0


def claimed(g):
    import json

    from actions.server.managed_work_items.contracts import ClaimRef

    s = service(g)
    s.call(g.caller, enqueue(g))
    result = s.call(
        g.caller,
        Claim(
            operation="items.claim",
            queue=enqueue(g).queue,
            idempotency_key="claim",
            lease_seconds=60,
        ),
    )
    return ClaimRef.model_validate_json(json.dumps(result["claim"]))


def test_dual_renew_and_observer_run_projection(generic):
    from actions.work_items._fencing import WorkItemClaim

    from actions.server.managed_work_items.contracts import ManagedCaller
    from actions.server.run_outputs.models import RunAttempt

    g = generic()
    ref = claimed(g)
    ticket = g.owner.dispatch(
        g.caller, WorkItemClaim(ref.item_id, ref.owner_id, ref.epoch), lease_seconds=30
    )
    s = service(g)
    renew = Renew(
        operation="items.renew",
        queue=ref.queue,
        idempotency_key="dual",
        claim=ref,
        lease_seconds=120,
    )
    s.call(g.caller, renew)
    row = g.db.all(FencedWorkItem)[0]
    attempt = g.db.all(RunAttempt)[0]
    assert abs(int(row.claim_deadline_ms) - int(attempt.lease_deadline_ms)) < 1000
    view = s.call(
        ManagedCaller(actor=g.caller.actor),
        Inspect(operation="runs.get", queue=ref.queue, run_id=ticket.fence.run_id),
    )
    assert view["run"]["attempts"][0]["epoch"] == ticket.fence.epoch
    assert s.call(
        g.caller, Inspect(operation="items.get", queue=ref.queue, item_id=ref.item_id)
    )["item"]["run_ids"] == [ticket.fence.run_id]


def complete_fixture(g):
    from action_server_tests.test_generic_work_item_execution import (
        synthetic_completion,
    )
    from actions.work_items._fencing import WorkItemClaim

    ref = claimed(g)
    ticket = g.owner.dispatch(
        g.caller, WorkItemClaim(ref.item_id, ref.owner_id, ref.epoch), lease_seconds=60
    )
    guarded, unused, result = synthetic_completion(g, ticket, "managed")
    outputs, records = [], []
    for name, media in [
        ("generated-action-result.json", "application/json"),
        ("rcc-receipt.json", "application/json"),
        ("rcc-stdout.log", "application/octet-stream"),
        ("rcc-stderr.log", "application/octet-stream"),
    ]:
        raw = b"hello\n" if name.endswith(".log") else b"{}"
        out = guarded.stage(
            ticket.fence, [raw], name=name, media_type=media, retention_seconds=120
        )
        from actions.server.run_outputs.models import RunOutput

        row = g.db.all(RunOutput, where="id=?", values=[out.output_id])[0]
        outputs.append(out)
        records.append(
            dict(name=name, ref=out.model_dump(), digest=row.digest, size=row.size)
        )
    result["outputs"] = records
    guarded.publish(g.caller.actor, ticket.fence, outputs, result)
    return ref, ticket


def test_terminal_readback_artifact_and_replay(generic):
    from actions.server._models import Run
    from actions.server.managed_work_items.contracts import Complete

    g = generic()
    ref, ticket = complete_fixture(g)
    s = service(g)
    command = Complete(
        operation="items.complete",
        queue=ref.queue,
        claim=ref,
        outcome="done",
        idempotency_key="complete",
    )
    first = s.call(g.caller, command)
    assert first["item"]["queue_state"] == "DONE"
    assert service(g).call(g.caller, command)["replay"] is True
    assert len(g.db.all(Run)) == 1 and len(g.db.all(FencedWorkItem)) == 1
    run = s.call(
        g.caller,
        Inspect(operation="runs.get", queue=ref.queue, run_id=ticket.fence.run_id),
    )["run"]
    assert len(run["artifacts"]) == 4
    chunk = s.call(
        g.caller,
        Inspect(
            operation="artifacts.read",
            queue=ref.queue,
            artifact_handle=run["artifacts"][0]["handle"],
        ),
    )
    assert chunk["eof"]


@pytest.mark.parametrize("mutation", ["revoked", "changed_input", "worker", "audit"])
def test_claim_replay_rejects_changed_authority(generic, mutation):
    from uuid import uuid4

    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.managed_work_items.contracts import ManagedCaller
    from actions.server.run_outputs.service import _update

    g = generic()
    claimed(g)
    caller = g.caller
    with g.db.transaction():
        if mutation == "revoked":
            _update(g.db, FoundryAccessGrant, g.grant.id, {"operations_json": "[]"})
        elif mutation == "changed_input":
            row = g.db.all(FencedWorkItem)[0]
            _update(
                g.db,
                FencedWorkItem,
                row.id,
                {"payload": row.payload.replace("managed", "changed")},
            )
        elif mutation == "worker":
            caller = ManagedCaller(actor=g.caller.actor, worker_id=str(uuid4()))
        else:
            row = [
                a
                for a in g.db.all(FoundryAudit)
                if a.operation == "generic-managed/items.claim"
            ][0]
            _update(g.db, FoundryAudit, row.id, {"deployment_id": str(uuid4())})
    with pytest.raises(ManagedError):
        service(g).call(
            caller,
            Claim(
                operation="items.claim",
                queue=enqueue(g).queue,
                idempotency_key="claim",
                lease_seconds=60,
            ),
        )
    assert len(g.db.all(FencedWorkItem)) == 1


def test_expired_claim_not_reclaimed(generic):
    from actions.server.run_outputs.service import _update

    g = generic()
    ref = claimed(g)
    with g.db.transaction():
        _update(g.db, FencedWorkItem, ref.item_id, {"claim_deadline_ms": "1"})
    result = service(g).call(
        g.caller,
        Claim(
            operation="items.claim",
            queue=ref.queue,
            idempotency_key="other",
            lease_seconds=60,
        ),
    )
    assert result["item"] is None and g.db.all(FencedWorkItem)[0].claim_epoch == 1


def test_neighboring_legacy_row_never_claimed(generic):
    from uuid import uuid4

    g = generic()
    queue = g.owner.queue(g.owner.policy.input_queue)
    neighbor = queue.seed_input(
        {"invoice": "not a generic admission"}, item_id=str(uuid4())
    )
    ref = claimed(g)
    assert ref.item_id != neighbor
    assert [r for r in g.db.all(FencedWorkItem) if r.id == neighbor][0].claim_epoch == 0
    listed = service(g).call(g.caller, Inspect(operation="items.list", queue=ref.queue))
    assert [i["id"] for i in listed["items"]] == [ref.item_id]


@pytest.mark.parametrize(
    "damage",
    [
        "claim",
        "output_seal",
        "output_receipt",
        "permission",
        "envelope_version",
        "execution_version",
        "boolean_version",
    ],
)
def test_completion_replay_revalidates(generic, damage):
    import json

    from actions.server._models import Run
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.managed_work_items.contracts import Complete
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import _update

    g = generic()
    ref, ticket = complete_fixture(g)
    s = service(g)
    cmd = Complete(
        operation="items.complete",
        queue=ref.queue,
        claim=ref,
        outcome="done",
        idempotency_key="complete",
    )
    s.call(g.caller, cmd)
    with g.db.transaction():
        if damage == "claim":
            _update(g.db, FencedWorkItem, ref.item_id, {"claim_epoch": ref.epoch + 1})
        elif damage == "output_seal":
            row = [r for r in g.db.all(RunOutput) if r.state == "final"][0]
            _update(g.db, RunOutput, row.id, {"digest": "sha256:" + "0" * 64})
        elif damage == "permission":
            _update(g.db, FoundryAccessGrant, g.grant.id, {"operations_json": "[]"})
        else:
            run = g.db.all(Run)[0]
            data = json.loads(run.result)
            if damage == "envelope_version":
                data["version"] = 2
            elif damage == "boolean_version":
                data["version"] = True
            elif damage == "execution_version":
                data["result"]["version"] = "actions.generated-rcc-execution/v999"
            else:
                data["result"]["outputs"].pop()
            _update(g.db, Run, run.id, {"result": json.dumps(data)})
    with pytest.raises(ManagedError):
        service(g).call(g.caller, cmd)


def test_logs_read_actual_output_bytes(generic):
    g = generic()
    ref, ticket = complete_fixture(g)
    result = service(g).call(
        g.caller,
        Inspect(
            operation="runs.logs", queue=ref.queue, run_id=ticket.fence.run_id, limit=1
        ),
    )
    assert result["lines"] == [{"offset": 0, "text": "hello"}]
    assert result["next_cursor"] == "1"


def test_completion_audit_failure_preserves_terminal_domain(generic, monkeypatch):
    from actions.server.managed_work_items.contracts import Complete

    g = generic()
    ref, _ = complete_fixture(g)
    prior = len(g.db.all(FoundryRequest))
    insert = g.db.insert

    def broken(row):
        if isinstance(row, FoundryAudit):
            raise RuntimeError("synthetic receipt failure")
        return insert(row)

    monkeypatch.setattr(g.db, "insert", broken)
    with pytest.raises(ManagedError):
        service(g).call(
            g.caller,
            Complete(
                operation="items.complete",
                queue=ref.queue,
                claim=ref,
                outcome="done",
                idempotency_key="completion-rollback",
            ),
        )
    assert len(g.db.all(FoundryRequest)) == prior
    assert g.db.all(FencedWorkItem)[0].state == "COMPLETED"


def test_exact_queue_scope_rejects_same_logical_name(generic):
    from uuid import uuid4

    from actions.server.deployments.ids import WorkspaceId

    g = generic()
    command = enqueue(g)
    foreign_workspace = WorkspaceId(uuid4())
    deployment = command.queue.deployment.model_copy(
        update={"workspace_id": foreign_workspace}
    )
    queue = command.queue.model_copy(
        update={"workspace_id": foreign_workspace, "deployment": deployment}
    )
    with pytest.raises(ManagedError):
        service(g).call(g.caller, Inspect(operation="items.list", queue=queue))
    assert not g.db.all(FencedWorkItem)


def test_same_queue_foreign_revision_filtered_before_count_and_claim(generic):
    from uuid import uuid4

    from actions.server.deployments.ids import DeploymentRevisionId

    g = generic()
    item = g.owner.enqueue(g.caller, {"value": "owned"}, "owned")
    envelope = g.owner.read_input(g.caller, item)
    foreign_deployment = envelope.snapshot.deployment.model_copy(
        update={"revision_id": DeploymentRevisionId("sha256:" + "f" * 64)}
    )
    foreign_snapshot = envelope.snapshot.model_copy(
        update={"deployment": foreign_deployment}
    )
    foreign = envelope.model_copy(update={"snapshot": foreign_snapshot})
    neighbor = str(uuid4())
    queue = g.owner.queue(g.owner.policy.input_queue)
    queue.seed_input(foreign.model_dump(mode="json", by_alias=True), item_id=neighbor)
    s = service(g)
    page = s.call(
        g.caller, Queues(operation="queues.list", workspace_id=s.queue_ref.workspace_id)
    )
    assert page["queues"][0]["counts"] == {"PENDING": 1}
    claim = s.call(
        g.caller,
        Claim(
            operation="items.claim",
            queue=s.queue_ref,
            lease_seconds=60,
            idempotency_key="exact",
        ),
    )
    assert claim["item"]["id"] == item
    assert [r for r in g.db.all(FencedWorkItem) if r.id == neighbor][0].claim_epoch == 0
    with pytest.raises(ManagedError, match="not_found"):
        s.call(
            g.caller,
            Inspect(operation="items.get", queue=s.queue_ref, item_id=neighbor),
        )


def test_real_router_and_concurrent_duplicate_enqueue(generic):
    import asyncio

    import httpx2
    from fastapi import FastAPI

    from actions.server.managed_work_items.api import create_router
    from actions.server.managed_work_items.contracts import API_PREFIX

    g = generic()
    app = FastAPI()

    async def authenticate(request):
        return g.caller

    app.include_router(create_router(service(g), authenticate))

    async def check():
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://127.0.0.1"
        ) as client:
            responses = await asyncio.gather(
                *(
                    client.post(
                        API_PREFIX + "/operations",
                        json=enqueue(g).model_dump(mode="json"),
                    )
                    for _ in range(2)
                )
            )
            assert [r.status_code for r in responses] == [200, 200]
            assert (
                responses[0].json()["result"]["item"]["id"]
                == responses[1].json()["result"]["item"]["id"]
            )

    asyncio.run(check())
    assert len(g.db.all(FencedWorkItem)) == 1
