"""Real managed claims, sealed Data, inference receipts and separate human resolution."""

from uuid import uuid4

import pytest
from action_server_tests import test_managed_work_items_sql_service as fixtures

from actions.server.decisions.models import (
    Answer,
    OptionProbability,
    ProviderResult,
    Usage,
)
from actions.server.decisions.service import Binding, DecisionService
from actions.server.decisions.work_items import (
    ClaimedDecisionService,
    ClaimedEvaluation,
)
from actions.server.foundry.models import FoundryRequest
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import (
    ClaimRef,
    ManagedCaller,
    Permission,
)
from actions.server.run_outputs.types import Actor

reviewed = fixtures.reviewed
provider = fixtures.provider


class Classifier:
    identity = "synthetic-claimed-classifier/v1"
    model = "synthetic-claimed-classifier/v1"

    def __init__(self):
        self.calls = 0
        self.hook = lambda: None
        self.evidence = None

    def evaluate(self, request):
        self.calls += 1
        self.hook()
        self.evidence = request.evidence
        question = request.questions[0]
        return ProviderResult(
            answers=(
                Answer(
                    name=question.name,
                    kind="choice",
                    choice="invoice",
                    confidence=1.0,
                    probabilities=tuple(
                        OptionProbability(
                            value=o.value,
                            probability=1.0 if o.value == "invoice" else 0.0,
                        )
                        for o in question.options
                    ),
                ),
            ),
            model=self.model,
            response_digest="sha256:" + "b" * 64,
            usage=Usage(input_tokens=0),
        )


@pytest.fixture
def claimed(reviewed):
    _, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    admitted = reviews.decide(actor, scope, proposal, "approve")
    queue = fixtures._queue(reviews, scope)
    worker = str(uuid4())
    claim = reviews.queue(scope).reserve_item_fenced(
        admitted.work_item_id, worker, lease_seconds=120
    )
    ref = ClaimRef(
        queue=queue, item_id=claim.item_id, owner_id=worker, epoch=claim.epoch
    )
    caller = ManagedCaller(actor=actor, worker_id=worker)
    policy = fixtures._Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.CLAIM, Permission.REVIEW)
    managed = fixtures._service(reviewed, policy)
    stub = Classifier()
    from action_server_tests.test_decisions import request

    value = request()
    command = ClaimedEvaluation(
        claim=ref,
        questions=value.questions,
        policy_revision=value.policy_revision,
        delivery_key="one",
    )
    binding = Binding(
        policy_revision=value.policy_revision,
        provider_revision=stub.identity,
        model=stub.model,
    )
    service = ClaimedDecisionService(
        managed, {DecisionService.scope_key(scope): (binding, stub)}
    )
    return service, stub, caller, command, policy, reviewed


def test_claimed_decision_separate_approval_replay_and_no_queue_effect(claimed):
    service, stub, caller, command, _, reviewed = claimed
    db, _, _, reviews, _, scope, _, _ = reviewed
    before = reviews.queue(scope).list_items()
    result = service.evaluate(caller, command)
    assert result.recommendation == "NEEDS_REVIEW"
    assert result.claim == command.claim
    assert "North" not in stub.evidence and "customer" not in stub.evidence
    assert '"sample_limit":3' in stub.evidence
    assert (
        service.evaluate(caller, command.model_copy(update={"delivery_key": "two"}))
        == result
    )
    assert stub.calls == 1
    human = ManagedCaller(actor=caller.actor)
    resolution = service.resolve(human, result, command, "approve")
    assert resolution.execution_authorized is False
    assert service.resolve(human, result, command, "approve") == resolution
    assert service.read(human, result.receipt_id) == result
    assert reviews.queue(scope).list_items() == before
    assert (
        len(
            db.all(
                FoundryRequest,
                where="operation=?",
                values=["decisions/claimed-resolution/v1"],
            )
        )
        == 1
    )
    with pytest.raises(ManagedError, match="changed_input"):
        service.resolve(human, result, command, "reject")


def test_worker_mismatch_revocation_and_takeover_fail_closed(claimed):
    service, stub, caller, command, policy, reviewed = claimed
    with pytest.raises(ManagedError, match="forbidden"):
        service.evaluate(
            ManagedCaller(actor=caller.actor, worker_id=str(uuid4())), command
        )
    result = service.evaluate(caller, command)
    policy.grant(caller.actor, Permission.READ)
    with pytest.raises(ManagedError, match="forbidden"):
        service.evaluate(caller, command)
    policy.grant(caller.actor, Permission.READ, Permission.CLAIM, Permission.REVIEW)
    db = reviewed[0]
    from actions.server.data_queries.review_models import FencedWorkItem

    with db.transaction():
        db.update_by_id(
            FencedWorkItem,
            command.claim.item_id,
            {"claim_epoch": command.claim.epoch + 1},
        )
    with pytest.raises(ManagedError, match="stale_claim"):
        service.evaluate(caller, command)
    with pytest.raises(ManagedError, match="stale_claim"):
        service.resolve(ManagedCaller(actor=caller.actor), result, command, "approve")
    assert stub.calls == 1


def test_claim_loss_during_inference_cannot_publish_receipt(claimed):
    service, stub, caller, command, _, reviewed = claimed
    from actions.server.data_queries.review_models import FencedWorkItem

    def lose():
        with reviewed[0].transaction():
            reviewed[0].update_by_id(
                FencedWorkItem, command.claim.item_id, {"cancel_requested": 1}
            )

    stub.hook = lose
    with pytest.raises(ManagedError, match="stale_claim"):
        service.evaluate(caller, command)
    rows = reviewed[0].all(
        FoundryRequest, where="operation=?", values=["decisions/claimed/v1"]
    )
    assert len(rows) == 1 and '"status":"pending"' in rows[0].result_json
    assert stub.calls == 1


def test_changed_question_or_policy_cannot_approve_old_decision(claimed):
    service, stub, caller, command, _, _ = claimed
    result = service.evaluate(caller, command)
    altered = command.model_copy(update={"policy_revision": "sha256:" + "e" * 64})
    with pytest.raises(ManagedError, match="changed_input"):
        service.resolve(ManagedCaller(actor=caller.actor), result, altered, "approve")
    questions = (
        command.questions[0].model_copy(
            update={"instructions": "different policy question"}
        ),
    )
    with pytest.raises(ManagedError, match="changed_input"):
        service.resolve(
            ManagedCaller(actor=caller.actor),
            result,
            command.model_copy(update={"questions": questions}),
            "approve",
        )
    assert stub.calls == 1


def test_real_robot_task_uses_claim_without_resolving_it(claimed, tmp_path):
    from pathlib import Path

    from robot.api import TestSuite

    service, stub, caller, command, _, reviewed = claimed
    task = (
        Path(__file__).resolve().parents[3]
        / "examples/decisions_robot/tasks-managed.robot"
    )
    suite = TestSuite.from_file_system(task)
    suite.resource.imports[0].args = (service, caller, command)
    result = suite.run(outputdir=str(tmp_path / "robot"), log=None, report=None)
    assert result.return_code == 0
    assert stub.calls == 1
    rows = reviewed[0].all(
        FoundryRequest, where="operation=?", values=["decisions/claimed/v1"]
    )
    assert len(rows) == 1
    assert (
        reviewed[0].all(
            FoundryRequest,
            where="operation=?",
            values=["decisions/claimed-resolution/v1"],
        )
        == []
    )


def test_default_off_authenticated_receipt_and_resolution_transport(claimed):
    import asyncio

    import httpx2
    from fastapi import FastAPI

    from actions.server.decisions.api import create_router

    service, stub, caller, command, _, _ = claimed

    async def identity(request):
        return (
            caller if request.headers.get("Authorization") == "Bearer fixture" else None
        )

    async def scenario():
        unconfigured = FastAPI()
        unconfigured.include_router(create_router(None, None))
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=unconfigured), base_url="http://test"
        ) as client:
            assert (
                await client.post(
                    "/api/managed-work-items/v1/decisions/evaluate", json={}
                )
            ).status_code == 503
        app = FastAPI()
        app.include_router(create_router(service, identity))
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            base = "/api/managed-work-items/v1/decisions"
            assert (
                await client.post(
                    base + "/evaluate", json=command.model_dump(mode="json")
                )
            ).status_code == 401
            response = await client.post(
                base + "/evaluate",
                json=command.model_dump(mode="json"),
                headers={"Authorization": "Bearer fixture"},
            )
            assert response.status_code == 200, response.text
            value = response.json()
            read = await client.get(
                base + "/" + value["receipt_id"],
                headers={"Authorization": "Bearer fixture"},
            )
            assert read.status_code == 200 and read.json()["receipt"] == value
            resolved = await client.post(
                base + "/resolve",
                json={
                    "receipt": value,
                    "evaluation": command.model_dump(mode="json"),
                    "decision": "reject",
                },
                headers={"Authorization": "Bearer fixture"},
            )
            assert (
                resolved.status_code == 200
                and resolved.json()["execution_authorized"] is False
            )
            status = await client.get(
                base + "/" + value["receipt_id"],
                headers={"Authorization": "Bearer fixture"},
            )
            assert status.json()["resolution"]["decision"] == "reject"

    asyncio.run(scenario())
    assert stub.calls == 1


def test_payload_change_and_expired_claim_reject_old_receipt(claimed):
    service, stub, caller, command, _, reviewed = claimed
    result = service.evaluate(caller, command)
    from actions.server.data_queries.review_models import FencedWorkItem

    with reviewed[0].transaction():
        reviewed[0].update_by_id(
            FencedWorkItem, command.claim.item_id, {"claim_deadline_ms": "0"}
        )
    with pytest.raises(ManagedError, match="stale_claim"):
        service.evaluate(caller, command)
    with pytest.raises(ManagedError, match="stale_claim"):
        service.resolve(ManagedCaller(actor=caller.actor), result, command, "approve")
    assert stub.calls == 1


def test_other_actor_and_revoked_review_cannot_resolve(claimed):
    service, stub, caller, command, policy, _ = claimed
    result = service.evaluate(caller, command)
    with pytest.raises(ManagedError, match="forbidden"):
        service.read(
            ManagedCaller(actor=Actor(principal_id=str(uuid4()))), result.receipt_id
        )
    policy.grant(caller.actor, Permission.READ, Permission.CLAIM)
    with pytest.raises(ManagedError, match="forbidden"):
        service.resolve(ManagedCaller(actor=caller.actor), result, command, "approve")
    assert stub.calls == 1


def test_duplicate_delivery_during_provider_call_never_infers_twice(claimed):
    service, stub, caller, command, _, _ = claimed
    from actions.server.decisions.openai import ProviderFailure

    def duplicate():
        with pytest.raises(ProviderFailure, match="evaluation_uncertain"):
            service.evaluate(
                caller, command.model_copy(update={"delivery_key": "concurrent"})
            )

    stub.hook = duplicate
    service.evaluate(caller, command)
    assert stub.calls == 1


def test_receipt_survives_fresh_runtime_process_without_new_inference(
    claimed, tmp_path
):
    import json
    import os
    import subprocess
    import sys

    service, stub, caller, command, _, reviewed = claimed
    receipt = service.evaluate(caller, command)
    db, _, _, reviews, _, _, _, _ = reviewed
    if db.backend_name != "sqlite":
        pytest.skip(
            "fresh-process proof is SQLite; PostgreSQL service tests are separate"
        )
    values = {
        "database": str(db.db_path),
        "objects": str(tmp_path / "objects"),
        "provider_key": next(iter(reviews.outputs.providers)),
        "caller": caller.model_dump(mode="json"),
        "command": command.model_dump(mode="json"),
        "provider_revision": stub.identity,
        "model": stub.model,
    }
    script = """
import json, os, sys
from actions.server._models import load_db
from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.decisions.service import Binding, DecisionService
from actions.server.decisions.work_items import ClaimedDecisionService, ClaimedEvaluation
from actions.server.managed_work_items.contracts import ManagedCaller, Permission
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import AccessDenied, RunOutputService
from actions.server.run_outputs.types import CanvasResultScope
values=json.load(sys.stdin)
caller=ManagedCaller.model_validate_json(json.dumps(values['caller']))
command=ClaimedEvaluation.model_validate_json(json.dumps(values['command']))
class Policy:
    def require_workspace(self, current, workspace, permission):
        if current != caller or workspace != command.claim.queue.workspace_id:
            raise AccessDenied('fixture grant denied')
    def require_queue(self,current,queue,permission):
        self.require_workspace(current,queue.workspace_id,permission)
        if queue != command.claim.queue: raise AccessDenied('fixture queue denied')
class NoInference:
    identity=values['provider_revision']
    def evaluate(self,request): raise AssertionError('restart inferred again')
fd=os.open(values['objects'],os.O_RDONLY|os.O_DIRECTORY)
try:
    with load_db(values['database']) as db, FilesystemOutputProvider(fd) as objects:
        reviews=InvoiceReviewService(InvoiceQueryService(RunOutputService(db,{values['provider_key']:objects}),{}))
        scope=CanvasResultScope.model_validate_json(json.dumps(values['scope']))
        managed=SQLManagedWorkItemsService(reviews,Policy())
        binding=Binding(policy_revision=command.policy_revision,provider_revision=NoInference.identity,model=values['model'])
        service=ClaimedDecisionService(managed,{DecisionService.scope_key(scope):(binding,NoInference())})
        print(service.evaluate(caller,command).model_dump_json())
finally: os.close(fd)
"""
    values["scope"] = reviewed[5].model_dump(mode="json")
    values["handle"] = reviewed[6]
    result = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(values),
        capture_output=True,
        text=True,
        timeout=20,
        env=os.environ.copy(),
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == receipt.model_dump(mode="json")
    assert stub.calls == 1


def test_authorized_renewal_preserves_decision_identity_but_expiry_does_not(claimed):
    from actions.work_items._fencing import WorkItemClaim

    service, stub, caller, command, _, reviewed = claimed
    receipt = service.evaluate(caller, command)
    claim = command.claim
    reviewed[3].queue(reviewed[5]).renew_fenced(
        WorkItemClaim(claim.item_id, claim.owner_id, claim.epoch), lease_seconds=300
    )
    assert service.evaluate(caller, command) == receipt
    assert stub.calls == 1
    resolution = service.resolve(
        ManagedCaller(actor=caller.actor), receipt, command, "approve"
    )
    assert resolution.execution_authorized is False


def test_revoked_runtime_execute_grant_prevents_inference(claimed):
    service, stub, caller, command, _, reviewed = claimed
    reviewed[1].grant(caller.actor, reviewed[7].deployment, {"read", "review"})
    from actions.server.run_outputs.service import AccessDenied

    with pytest.raises(AccessDenied):
        service.evaluate(caller, command)
    assert stub.calls == 0


def test_unsupported_declared_model_rejected_before_provider_call(claimed):
    service, stub, caller, command, _, _ = claimed
    from actions.server.decisions.openai import ProviderFailure

    key = next(iter(service.bindings))
    binding, provider = service.bindings[key]
    service.bindings[key] = (
        binding.model_copy(update={"model": "unsupported-revision"}),
        provider,
    )
    with pytest.raises(ProviderFailure, match="model_revision_changed"):
        service.evaluate(caller, command)
    assert stub.calls == 0


@pytest.mark.parametrize("damage", ["expired", "tampered"])
def test_unreadable_sealed_source_never_reaches_model(claimed, damage):
    service, stub, caller, command, _, reviewed = claimed
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.service import OutputExpired

    rows = reviewed[0].all(RunOutput)
    assert len(rows) == 1
    changes = (
        {"expires_ms": "0"} if damage == "expired" else {"digest": "sha256:" + "0" * 64}
    )
    with reviewed[0].transaction():
        reviewed[0].update_by_id(RunOutput, rows[0].id, changes)
    expected = OutputExpired if damage == "expired" else ManagedError
    with pytest.raises(expected):
        service.evaluate(caller, command)
    assert stub.calls == 0
    assert (
        reviewed[0].all(
            FoundryRequest, where="operation=?", values=["decisions/claimed/v1"]
        )
        == []
    )


def test_expiry_after_post_inference_source_read_cannot_publish(claimed, monkeypatch):
    service, stub, caller, command, _, reviewed = claimed
    from actions.server.data_queries.review_models import FencedWorkItem

    original = service._prepared
    reads = []

    def expire_after_read(*args):
        value = original(*args)
        reads.append(1)
        if len(reads) == 2:
            reviewed[0].update_by_id(
                FencedWorkItem, command.claim.item_id, {"claim_deadline_ms": "0"}
            )
        return value

    monkeypatch.setattr(service, "_prepared", expire_after_read)
    with pytest.raises(ManagedError, match="stale_claim"):
        service.evaluate(caller, command)
    assert stub.calls == 1 and len(reads) == 2


def test_postgres_sdk_cancel_serializes_with_receipt_publication(claimed, monkeypatch):
    import concurrent.futures
    import threading

    service, stub, caller, command, _, reviewed = claimed
    if reviewed[0].backend_name != "postgresql":
        pytest.skip("two-connection MVCC proof uses owned PostgreSQL")
    entered, release, cancelling = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    original = service._store_current

    def paused_write(claim, row, *, insert=False):
        if not insert and row.operation == "decisions/claimed/v1":
            entered.set()
            assert release.wait(10)
        return original(claim, row, insert=insert)

    monkeypatch.setattr(service, "_store_current", paused_write)

    def cancel():
        with reviewed[0].connect():
            cancelling.set()
            return reviewed[3].queue(reviewed[5]).cancel(command.claim.item_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        evaluated = executor.submit(service.evaluate, caller, command)
        assert entered.wait(10)
        cancelled = executor.submit(cancel)
        assert cancelling.wait(10)
        try:
            with pytest.raises(concurrent.futures.TimeoutError):
                cancelled.result(timeout=0.1)
        finally:
            release.set()
        assert evaluated.result(timeout=10).recommendation == "NEEDS_REVIEW"
        assert cancelled.result(timeout=10) is True
    assert stub.calls == 1
    with pytest.raises(ManagedError, match="stale_claim"):
        service.evaluate(caller, command)


def test_unfinished_receipt_checks_workspace_before_revealing_state(claimed):
    from actions.server.decisions.openai import ProviderFailure

    service, stub, caller, command, _, reviewed = claimed

    def fail():
        raise RuntimeError("synthetic provider loss")

    stub.hook = fail
    with pytest.raises(ProviderFailure, match="provider_unavailable"):
        service.evaluate(caller, command)
    row = reviewed[0].all(
        FoundryRequest, where="operation=?", values=["decisions/claimed/v1"]
    )[0]
    with pytest.raises(ManagedError, match="forbidden"):
        service.read(ManagedCaller(actor=Actor(principal_id=str(uuid4()))), row.id)
    with pytest.raises(ProviderFailure, match="evaluation_uncertain"):
        service.read(caller, row.id)
    assert stub.calls == 1
