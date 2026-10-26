"""Real SQLite claim/Run authority with synthetic Robot adapter; no RCC proof."""
import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant, _registry
from action_server_tests.test_generic_work_item_execution import grant
from action_server_tests.test_robot_package_admission import request_for
from action_server_tests.test_robot_runtime_runner import SyntheticAdapter
from actions.work_items import State
from actions.work_items._adapters._sql_review import SQLReviewQueue
from actions.work_items._fencing import ClaimRejected

from actions.server._models import Run, RunStatus
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    CapabilityPlanPolicy,
    CapabilityWorkItemPolicy,
    DeploymentSpecification,
    WorkItemDeclaration,
)
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.robot_execution import DirectRobotPreparation
from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.managed_work_items.authorization import SqlQueueAuthorization
from actions.server.managed_work_items.contracts import ManagedCaller, Permission
from actions.server.run_outputs.models import RunAttempt, RunOutput
from actions.server.run_outputs.service import (
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
    _one,
    _update,
)
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.fixture
def claimed(database_location, foundry_package_store, tmp_path):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)

        def setup(mode="consumer", with_claim=True):
            registry = _registry(db, foundry_package_store)
            request = request_for().model_copy(
                update={"work_items": WorkItemDeclaration(mode=mode)}
            )
            preparation = DirectRobotPreparation(Path(sys.executable))
            evidence = registry.prepare_trusted_robot(
                request,
                logical_package_key="claimed-robot",
                trusted_actor=actor,
                workspace_id=refs.workspace,
                application_id=refs.deployment_id,
                preparation=preparation,
            )
            package = registry.admit_robot(actor, refs.workspace, evidence)
            cap = registry.capability_refs(package)[0]
            plan = registry.get_capability(cap).runtime_plans[0]
            policy = CapabilityWorkItemPolicy(
                capability=cap,
                input_mode={
                    "optional": "optional",
                    "required-input": "required",
                    "consumer": "claim",
                }[mode],
                input_queue="robot-input",
                max_output_items=0,
                max_output_bytes=0,
            )
            for ref in (refs.worker, refs.policy, refs.output_provider):
                grant(
                    db,
                    actor,
                    refs.workspace,
                    "reference",
                    reference_grant_subject(ref),
                    ["deploy", "execute"],
                )
            grant(
                db,
                actor,
                refs.workspace,
                "workspace",
                str(refs.workspace.root),
                [
                    "execute",
                    "read_application",
                    "cancel_execution",
                    *[p.value for p in Permission],
                ],
            )
            deployments = FoundryDeploymentService(
                FoundryRepository(db), registry, SqlFoundryAuthorization(db), registry
            )
            spec = DeploymentSpecification(
                package_revisions=(package,),
                capability_plans=(
                    CapabilityPlanPolicy(
                        capability=cap,
                        mode="locked",
                        allowed_plans=(plan,),
                        default_plan=plan,
                    ),
                ),
                worker=refs.worker,
                policy=refs.policy,
                output_provider=refs.output_provider,
                work_item_policies=(policy,),
            )
            revision = deployments.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                spec,
                idempotency_key="claimed-robot",
            )
            grant(
                db,
                actor,
                refs.workspace,
                "reference",
                reference_grant_subject(revision.ref),
                [
                    "execute",
                    "read_application",
                    "cancel_execution",
                    *[p.value for p in Permission],
                ],
            )
            snapshot = deployments.resolve(
                actor, refs.workspace, refs.deployment_id, cap
            ).snapshot
            control = RunOutputControlPlane(db, capabilities=registry)
            control.register(snapshot)
            control.grant(actor, revision.ref, {"execute", "read", "cancel"})
            base = RunOutputService(
                db,
                {snapshot.provider_key: foundry_package_store},
                capabilities=registry,
            )
            owner = GenericWorkItemExecution(
                deployments, base, snapshot, policy, SqlQueueAuthorization(db)
            )
            caller = ManagedCaller(actor=actor, worker_id=str(uuid4()))
            item = claim = None
            if with_claim:
                item = owner.enqueue(caller, {"value": "owned"}, "robot-item")
                queue = owner.queue(policy.input_queue)
                queue.reserve_item_fenced(item, caller.worker_id, lease_seconds=60)
                with db.transaction():
                    _update(db, FencedWorkItem, item, {"claim_deadline_ms": "0"})
                claim = queue.reserve_item_fenced(
                    item, caller.worker_id, lease_seconds=60
                )
                ticket = owner.dispatch(caller, claim, lease_seconds=60)
                assert claim.epoch == 2 and ticket.fence.epoch == 1
            else:
                ticket = owner.dispatch_standalone(
                    caller, {"value": "owned"}, "optional", lease_seconds=60
                )
            runner = PinnedRobotRunner(
                preparation, tmp_path / "execution", adapter_factory=SyntheticAdapter
            )
            return SimpleNamespace(
                owner=owner,
                caller=caller,
                ticket=ticket,
                db=db,
                provider=foundry_package_store,
                runner=runner,
                item=item,
                claim=claim,
            )

        yield setup


@pytest.mark.parametrize(
    "mode,with_claim",
    [
        ("consumer", True),
        ("required-input", True),
        ("optional", True),
        ("optional", False),
    ],
)
@pytest.mark.parametrize("failed", [False, True])
def test_claimed_robot_atomic_terminal_and_renew(
    claimed, monkeypatch, mode, with_claim, failed
):
    c = claimed(mode, with_claim)
    original = type(c.provider).open
    reads = []

    def guarded(self, *args, **kwargs):
        if self is c.provider:
            assert (
                not c.db.in_transaction()
            ), "provider read inside SQL execution lifecycle"
            reads.append(True)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(c.provider), "open", guarded)

    class Adapter(SyntheticAdapter):
        def execute(self, actor, fence, **kwargs):
            # Authority preparation is complete before adapter construction/work.
            before = len(reads)
            if with_claim:
                shortened = int(time.time() * 1000) + 10000
                with c.db.transaction():
                    _update(
                        c.db,
                        FencedWorkItem,
                        c.item,
                        {"claim_deadline_ms": str(shortened)},
                    )
            kwargs["lifecycle"].heartbeat(actor, fence, kwargs["selection"])
            if with_claim:
                assert (
                    int(_one(c.db, FencedWorkItem, c.item).claim_deadline_ms)
                    > shortened
                )
            result = super().execute(actor, fence, **kwargs)
            assert len(reads) == before
            return replace(result, status="FAIL", return_code=1) if failed else result

    run = replace(c.runner, adapter_factory=Adapter).execute(
        c.caller, c.ticket, c.owner
    )
    assert run.status == (RunStatus.FAILED if failed else RunStatus.PASSED)
    record = json.loads(run.result)["result"]
    assert record["claim"] == (
        c.ticket.claim.model_dump(mode="json") if with_claim else None
    )
    assert record["mode"] == ("work-items" if with_claim else "standalone")
    assert _one(c.db, RunAttempt, c.ticket.fence.attempt_id).state == (
        "failed" if failed else "succeeded"
    )
    assert all(o.state == "final" for o in c.db.all(RunOutput))
    if with_claim:
        row = _one(c.db, FencedWorkItem, c.item)
        assert row.state == (State.FAILED.value if failed else State.DONE.value)
        assert row.claim_epoch == 2
    assert len(c.db.all(FencedWorkItem)) == (1 if with_claim else 0)


@pytest.mark.parametrize(
    "failure", ["finish", "stop", "complete", "claim_epoch", "claim_expired"]
)
def test_claimed_robot_failure_keeps_outputs_provisional(claimed, monkeypatch, failure):
    c = claimed()

    class Adapter(SyntheticAdapter):
        def execute(self, actor, fence, **kwargs):
            result = super().execute(actor, fence, **kwargs)
            if failure in ("claim_epoch", "claim_expired"):
                with c.db.transaction():
                    _update(
                        c.db,
                        FencedWorkItem,
                        c.item,
                        {"claim_epoch": 3}
                        if failure == "claim_epoch"
                        else {"claim_deadline_ms": "0"},
                    )
            return result

    if failure == "finish":

        def reject(*args, **kwargs):
            raise FenceRejected("injected queue finish failure")

        monkeypatch.setattr(SQLReviewQueue, "finish_fenced", reject)
    if failure == "complete":
        original = c.owner._permission

        def permission(caller, queue, permission):
            if permission == Permission.COMPLETE:
                raise FenceRejected("injected COMPLETE denial")
            return original(caller, queue, permission)

        monkeypatch.setattr(c.owner, "_permission", permission)
    with pytest.raises((FenceRejected, ClaimRejected)):
        replace(c.runner, adapter_factory=Adapter).execute(
            c.caller, c.ticket, c.owner, publication_cancelled=lambda: failure == "stop"
        )
    assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.RUNNING
    assert _one(c.db, RunAttempt, c.ticket.fence.attempt_id).state == "running"
    outputs = c.db.all(RunOutput)
    assert len(outputs) == 3 and all(o.state == "provisional" for o in outputs)
    assert _one(c.db, FencedWorkItem, c.item).state not in (
        State.DONE.value,
        State.FAILED.value,
    )


@pytest.mark.parametrize("permission", [Permission.READ, Permission.CLAIM])
def test_revoked_queue_authority_prevents_adapter(claimed, monkeypatch, permission):
    c = claimed()
    calls = []
    original = c.owner._permission

    def require(caller, queue, requested):
        if requested == permission:
            raise FenceRejected("revoked queue permission")
        return original(caller, queue, requested)

    monkeypatch.setattr(c.owner, "_permission", require)

    class NeverAdapter(SyntheticAdapter):
        def __init__(self, *args):
            calls.append(True)
            super().__init__(*args)

    with pytest.raises(FenceRejected):
        replace(c.runner, adapter_factory=NeverAdapter).execute(
            c.caller, c.ticket, c.owner
        )
    assert not calls
    assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.RUNNING
    assert c.db.all(RunOutput) == []


@pytest.mark.parametrize("change", ["unissued", "owner", "ticket", "source", "nested"])
def test_robot_claim_authority_binding_is_exact(claimed, change):
    from actions.server.foundry.models import FoundryPackageRevision
    from actions.server.foundry.robot_work_item_authority import (
        prepare_robot_work_item_authority,
    )
    from actions.server.run_outputs.service import AccessDenied

    c = claimed()
    authority = prepare_robot_work_item_authority(c.owner, c.caller, c.ticket)
    domain = c.owner.outputs(c.caller, c.ticket)
    if change == "unissued":
        authority = replace(authority)
    elif change == "owner":
        other = GenericWorkItemExecution(
            c.owner.deployments,
            c.owner.base,
            c.owner.snapshot,
            c.owner.policy,
            c.owner.authorization,
        )
        domain = other.outputs(c.caller, c.ticket)
    elif change == "ticket":
        altered = c.ticket.model_copy(update={"input_digest": "sha256:" + "0" * 64})
        domain = c.owner.outputs(c.caller, altered)
    elif change == "source":
        row = c.db.all(FoundryPackageRevision)[0]
        with c.db.transaction():
            _update(
                c.db,
                FoundryPackageRevision,
                row.id,
                {"build_evidence_json": row.build_evidence_json + " "},
            )
    expected = ValueError if change == "source" else (AccessDenied, FenceRejected)
    with pytest.raises(expected):
        with domain.bind_execution_authority(authority):
            assert change == "nested", "invalid authority unexpectedly bound"
            with domain.bind_execution_authority(authority):
                pytest.fail("nested authority binding admitted")
    assert getattr(domain, "_robot_authority", None) is None
