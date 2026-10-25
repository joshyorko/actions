# Imported pytest fixture names are injected as parameters.
# ruff: noqa: F811
"""Synthetic adapter, real Package/Deployment/Run authority and provider barriers."""
import hashlib
import os
import json
from dataclasses import replace
from threading import Event, Thread
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_robot_package_admission import admitted as admitted
from action_server_tests.test_robot_package_admission import (
    disable_feedback as disable_feedback,
)

from actions.server._common.process import ProcessTreeCleanupResult
from actions.server._models import Run, RunStatus
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import AccessDenied as RegistryDenied
from actions.server.deployments.foundry_values import (
    CapabilityPlanPolicy,
    DeploymentSpecification,
)
from actions.server.foundry.generic_work_item_execution import GenericTicket, _digest
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.robot_execution import (
    RobotExecutionResult,
    RobotLaunchIntent,
    RobotStagedOutput,
)
from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
    _one,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(not hasattr(os, "O_PATH"), reason="Linux descriptor provider")


class SyntheticAdapter:
    calls = 0
    launches = 0
    stdout = b"owned"

    def __init__(self, *args):
        pass

    def execute(
        self,
        actor,
        fence,
        *,
        selection,
        source_archive,
        lifecycle,
        cancelled,
        timeout_seconds,
    ):
        type(self).calls += 1
        assert (
            hashlib.sha256(source_archive).hexdigest()
            == selection.source_digest.split(":")[1]
        )
        intent = RobotLaunchIntent(selection, fence, str(uuid4()))
        lifecycle.record_launch_intent(actor, fence, intent)
        SyntheticAdapter.launches += 1
        values = []
        for name, media, raw in [
            ("robot-stdout.log", "application/octet-stream", self.stdout),
            ("robot-stderr.log", "application/octet-stream", b""),
            ("robot-output.xml", "application/xml", b"<robot/>"),
        ]:
            lifecycle.check_live(actor, fence, selection)
            ref = lifecycle.stage_output(
                actor, fence, name=name, media_type=media, content=raw
            )
            values.append(
                RobotStagedOutput(
                    ref,
                    name,
                    media,
                    "sha256:" + hashlib.sha256(raw).hexdigest(),
                    len(raw),
                    len(raw),
                    False,
                )
            )
        lifecycle.check_live(actor, fence, selection)
        return RobotExecutionResult(
            intent, "PASS", 0, tuple(values), ProcessTreeCleanupResult(True, (), (), ())
        )


@pytest.fixture
def case(admitted, tmp_path):
    db, refs, actor, registry, evidence, provider = admitted
    package = registry.admit_robot(actor, refs.workspace, evidence)
    cap = registry.capability_refs(package)[0]
    plan = registry.get_capability(cap).runtime_plans[0]
    with db.transaction():
        for ref in (refs.worker, refs.policy, refs.output_provider):
            db.insert(
                FoundryAccessGrant(
                    str(uuid4()),
                    str(refs.workspace.root),
                    actor.principal_id,
                    "reference",
                    reference_grant_subject(ref),
                    '["deploy","execute"]',
                )
            )
    auth = SqlFoundryAuthorization(db)
    deployments = FoundryDeploymentService(
        FoundryRepository(db), registry, auth, registry
    )
    spec = DeploymentSpecification(
        package_revisions=(package,),
        capability_plans=(
            CapabilityPlanPolicy(
                capability=cap, mode="locked", allowed_plans=(plan,), default_plan=plan
            ),
        ),
        bindings=(),
        worker=refs.worker,
        policy=refs.policy,
        output_provider=refs.output_provider,
    )
    revision = deployments.create(
        actor, refs.workspace, refs.deployment_id, spec, idempotency_key="robot-deploy"
    )
    with db.transaction():
        db.insert(
            FoundryAccessGrant(
                str(uuid4()),
                str(refs.workspace.root),
                actor.principal_id,
                "reference",
                reference_grant_subject(revision.ref),
                '["deploy","execute"]',
            )
        )
    snapshot = deployments.resolve(
        actor, refs.workspace, refs.deployment_id, cap
    ).snapshot
    control = RunOutputControlPlane(db, capabilities=registry)
    control.register(snapshot)
    control.grant(actor, revision.ref, {"read", "execute", "cancel"})
    outputs = RunOutputService(
        db, {snapshot.provider_key: provider}, capabilities=registry
    )
    caller = ManagedCaller(actor=actor, worker_id=str(uuid4()))
    run = outputs.admit(actor, snapshot, {"value": "owned"}, "robot-run")
    fence = outputs.claim(run.id, caller.worker_id, lease_seconds=60)
    with db.transaction():
        db.update_by_id(
            Run,
            run.id,
            {
                "result": json.dumps(
                    {
                        "version": "actions.robot-dispatch/v1",
                        "mode": "standalone",
                        "claim": None,
                        "fence": fence.model_dump(mode="json"),
                        "launch": None,
                    }
                )
            },
        )
    ticket = GenericTicket(
        claim=None, fence=fence, input_digest=_digest({"value": "owned"})
    )
    service = StandaloneActionExecution(deployments, outputs, snapshot)
    runner = PinnedRobotRunner(
        registry._robot_pending[id(evidence)][4],
        tmp_path / "execution",
        adapter_factory=SyntheticAdapter,
    )
    yield SimpleNamespace(
        db=db,
        refs=refs,
        actor=actor,
        registry=registry,
        provider=provider,
        caller=caller,
        ticket=ticket,
        service=service,
        runner=runner,
        control=control,
    )


def test_canonical_standalone_publication(case):
    c = case
    run = c.runner.execute(c.caller, c.ticket, c.service)
    assert run.status == RunStatus.PASSED
    receipt = json.loads(run.result)["result"]
    assert receipt["version"] == "actions.robot-execution/v1"
    assert receipt["publicationFence"] == c.ticket.fence.model_dump(mode="json")
    assert receipt["actionResult"] == {
        "suite": "Task",
        "task": "Owned",
        "status": "PASS",
    }
    assert _one(c.db, RunAttempt, c.ticket.fence.attempt_id).state == "succeeded"
    assert all(row.state == "final" for row in c.db.all(RunOutput))


@pytest.mark.parametrize("change", ["grant", "cancel", "epoch", "input", "deployment"])
def test_changed_authority_denies_before_adapter(case, change):
    c = case
    before = SyntheticAdapter.calls
    with c.db.transaction():
        if change == "grant":
            c.db.execute(
                "DELETE FROM foundry_access_grant WHERE subject_id=?",
                [reference_grant_subject(c.service.snapshot.capability)],
            )
        elif change == "cancel":
            c.db.update_by_id(RunPin, c.ticket.fence.run_id, {"cancel_requested": 1})
        elif change == "epoch":
            c.ticket = c.ticket.model_copy(
                update={"fence": c.ticket.fence.model_copy(update={"epoch": 99})}
            )
        elif change == "input":
            c.ticket = c.ticket.model_copy(
                update={"input_digest": "sha256:" + "f" * 64}
            )
        else:
            c.db.execute(
                "DELETE FROM foundry_deployment_head WHERE deployment_id=?",
                [str(c.refs.deployment_id.root)],
            )
    with pytest.raises((AccessDenied, RegistryDenied, FenceRejected, ValueError)):
        c.runner.execute(c.caller, c.ticket, c.service)
    assert SyntheticAdapter.calls == before


def test_revocation_during_actual_provider_stage_denies_publication(case, monkeypatch):
    c = case
    entered = Event()
    resume = Event()
    original = c.provider.stage
    outcome = []

    def barrier(chunks):
        staged = original(chunks)
        entered.set()
        assert resume.wait(10)
        return staged

    monkeypatch.setattr(c.provider, "stage", barrier)

    def execute():
        with c.db.connect():
            try:
                c.runner.execute(c.caller, c.ticket, c.service)
            except Exception as e:
                outcome.append(e)

    worker = Thread(target=execute)
    worker.start()
    assert entered.wait(10)
    try:
        with c.db.transaction():
            c.db.execute(
                "DELETE FROM foundry_access_grant WHERE subject_id=?",
                [reference_grant_subject(c.service.snapshot.capability)],
            )
    finally:
        resume.set()
        worker.join(15)
    assert not worker.is_alive() and outcome
    assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.RUNNING
    assert all(row.state != "final" for row in c.db.all(RunOutput))


def test_restart_existing_intent_never_relaunches(case):
    c = case

    class Interrupted(SyntheticAdapter):
        def execute(self, actor, fence, **kwargs):
            kwargs["lifecycle"].record_launch_intent(
                actor,
                fence,
                RobotLaunchIntent(kwargs["selection"], fence, str(uuid4())),
            )
            raise RuntimeError("synthetic process loss after durable intent")

    with pytest.raises(RuntimeError):
        replace(c.runner, adapter_factory=Interrupted).execute(
            c.caller, c.ticket, c.service
        )
    before = SyntheticAdapter.calls
    with pytest.raises(FenceRejected, match="reconciliation"):
        c.runner.execute(c.caller, c.ticket, c.service)
    assert SyntheticAdapter.calls == before


def test_same_attempt_competing_launch_has_one_winner(case):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    c = case
    barrier = Barrier(2)
    before = SyntheticAdapter.launches

    class Competing(SyntheticAdapter):
        def execute(self, *args, **kwargs):
            barrier.wait(timeout=10)
            return super().execute(*args, **kwargs)

    runner = replace(c.runner, adapter_factory=Competing)

    def invoke():
        with c.db.connect():
            try:
                return runner.execute(c.caller, c.ticket, c.service)
            except (FenceRejected, AccessDenied, RegistryDenied) as error:
                return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: invoke(), range(2)))
    assert sum(isinstance(value, Run) for value in results) == 1
    assert SyntheticAdapter.launches - before == 1
    assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.PASSED


def test_fresh_authorities_refuse_retained_intent(case):
    from action_server_tests.test_foundry_package_registry import _registry

    from actions.server._database import Database
    from actions.server._models import get_all_model_classes

    c = case

    class Interrupted(SyntheticAdapter):
        def execute(self, actor, fence, **kwargs):
            kwargs["lifecycle"].record_launch_intent(
                actor,
                fence,
                RobotLaunchIntent(kwargs["selection"], fence, str(uuid4())),
            )
            raise RuntimeError("synthetic lost worker")

    with pytest.raises(RuntimeError):
        replace(c.runner, adapter_factory=Interrupted).execute(
            c.caller, c.ticket, c.service
        )
    db = Database(c.db.db_path)
    with db.connect():
        db.initialize(get_all_model_classes())
        registry = _registry(db, c.provider)
        deployments = FoundryDeploymentService(
            FoundryRepository(db), registry, SqlFoundryAuthorization(db), registry
        )
        base = RunOutputService(
            db, {c.service.snapshot.provider_key: c.provider}, capabilities=registry
        )
        fresh = StandaloneActionExecution(deployments, base, c.service.snapshot)
        before = SyntheticAdapter.launches
        with pytest.raises(FenceRejected, match="reconciliation"):
            c.runner.execute(c.caller, c.ticket, fresh)
        assert SyntheticAdapter.launches == before


def test_final_adapter_return_cannot_bypass_live_authority(case):
    c = case

    class Revoked(SyntheticAdapter):
        def execute(self, *args, **kwargs):
            result = super().execute(*args, **kwargs)
            with c.db.transaction():
                c.db.execute(
                    "DELETE FROM foundry_access_grant WHERE subject_id=?",
                    [reference_grant_subject(c.service.snapshot.capability)],
                )
            return result

    with pytest.raises((AccessDenied, RegistryDenied, FenceRejected)):
        replace(c.runner, adapter_factory=Revoked).execute(
            c.caller, c.ticket, c.service
        )
    assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.RUNNING
    assert all(row.state != "final" for row in c.db.all(RunOutput))


def test_post_bind_lifecycle_and_publish_do_not_reopen_sources(case, monkeypatch):
    c = case

    class Trapped(SyntheticAdapter):
        def execute(self, *args, **kwargs):
            def forbidden(*args, **kwargs):
                raise AssertionError("artifact/schema IO in bound SQL callback")

            with monkeypatch.context() as patch:
                patch.setattr(c.registry, "load_verified", forbidden)
                patch.setattr(c.registry, "schema_for", forbidden)
                patch.setattr(c.provider, "open", forbidden)
                return super().execute(*args, **kwargs)

    assert (
        replace(c.runner, adapter_factory=Trapped)
        .execute(c.caller, c.ticket, c.service)
        .status
        == RunStatus.PASSED
    )


@pytest.mark.parametrize("mutation", ["cleanup", "output", "failure"])
def test_terminal_status_and_receipt_bounds(case, mutation):
    c = case

    class Modified(SyntheticAdapter):
        def execute(self, *args, **kwargs):
            result = super().execute(*args, **kwargs)
            if mutation == "cleanup":
                return replace(
                    result, cleanup=ProcessTreeCleanupResult(False, (), (), ())
                )
            if mutation == "output":
                return replace(
                    result,
                    outputs=(
                        replace(result.outputs[0], digest="sha256:" + "f" * 64),
                        *result.outputs[1:],
                    ),
                )
            return replace(result, status="FAIL", return_code=1)

    runner = replace(c.runner, adapter_factory=Modified)
    if mutation == "failure":
        result = runner.execute(c.caller, c.ticket, c.service)
        assert result.status == RunStatus.FAILED
        assert _one(c.db, RunAttempt, c.ticket.fence.attempt_id).state == "failed"
    else:
        with pytest.raises(FenceRejected):
            runner.execute(c.caller, c.ticket, c.service)
        assert _one(c.db, Run, c.ticket.fence.run_id).status == RunStatus.RUNNING


def test_claimed_ticket_is_explicitly_unsupported(case):
    from actions.server.foundry.work_item_execution import ClaimValue

    c = case
    claim = ClaimValue(item_id=str(uuid4()), owner_id=c.ticket.fence.owner_id, epoch=1)
    with pytest.raises(AccessDenied, match="claimed Robot unsupported"):
        c.runner.execute(
            c.caller, c.ticket.model_copy(update={"claim": claim}), c.service
        )


def test_lifecycle_payload_above_provider_chunk_bound(case):
    c = case

    class Large(SyntheticAdapter):
        stdout = b"x" * (65536 + 1)

    result = replace(c.runner, adapter_factory=Large).execute(
        c.caller, c.ticket, c.service
    )
    assert result.status == RunStatus.PASSED
    assert (
        next(row for row in c.db.all(RunOutput) if row.name == "robot-stdout.log").size
        == 65537
    )
