"""Generic domain contracts; synthetic completion is not actual RCC evidence."""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant, _registry
from actions.work_items._fencing import ClaimRejected
from contract_tests.test_package_revision_compiler import (
    _FakeCompilerExecutor,
    _generated_action_entries,
)

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
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.managed_work_items.authorization import SqlQueueAuthorization
from actions.server.managed_work_items.contracts import ManagedCaller, Permission
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
    _canonical,
    _one,
    _update,
)
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def test_generic_adapter_requires_explicit_authorities():
    import pytest

    with pytest.raises(TypeError):
        GenericWorkItemExecution(None, None, None, None, None)


class OutputExecutor(_FakeCompilerExecutor):
    def import_action(self, *args):
        value = super().import_action(*args)
        value["actions"][0]["output_schema"] = {
            "type": "object",
            "required": ["result", "workItems"],
            "additionalProperties": False,
            "properties": {
                "result": {"type": "string"},
                "workItems": {"type": "array", "items": {"type": "object"}},
            },
        }
        return value


def grant(db, actor, workspace, kind, subject, permissions):
    row = FoundryAccessGrant(
        str(uuid4()),
        str(workspace.root),
        actor.principal_id,
        kind,
        subject,
        json.dumps(permissions),
    )
    with db.transaction():
        db.insert(row)
    return row


@pytest.fixture
def generic(database_location, foundry_package_store):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)

        def setup(mode="consumer", outputs=False, real=False):
            executor = OutputExecutor() if outputs else None
            entries = _generated_action_entries()
            if real:
                import os
                from pathlib import Path

                from actions.server.deployments.package_revision_compiler import (
                    PinnedRccPackageBuildExecutor,
                    load_prepared_rcc_environment,
                )

                prepared = load_prepared_rcc_environment(
                    Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
                )
                executor = PinnedRccPackageBuildExecutor(prepared)
                if outputs:
                    from contract_tests.test_package_revision_compiler import _entry

                    entries = _generated_action_entries(
                        b"from actions import action\n@action\ndef generated_echo(value: str) -> dict:\n    return {'result': value, 'workItems': [{'value': value + ' child'}]}\n"
                    )
                    entries[-1] = _entry(
                        "tests/test_generated_action.py",
                        b"import unittest\nfrom generated_actions import generated_echo\nclass GenericTest(unittest.TestCase):\n    def test_echo(self):\n        self.assertEqual(generated_echo('synthetic')['result'], 'synthetic')\n",
                    )
            registry = _registry(db, foundry_package_store, executor)
            compiled = registry.compile_trusted_source(
                entries,
                logical_package_key="generic-" + mode,
                logical_name="Generic " + mode,
                trusted_actor=actor,
                workspace_id=refs.workspace,
                application_id=refs.deployment_id,
                work_items=WorkItemDeclaration(mode=mode, allow_outputs=outputs),
            )
            assert compiled.evidence.ready, compiled.evidence
            package = registry.admit_compiled(
                actor, refs.workspace, compiled.compiled_package
            )
            capability = registry.capability_refs(package)[0]
            declaration = registry.get_capability(capability)
            input_mode = {
                "consumer": "claim",
                "optional": "optional",
                "producer": "none",
            }[mode]
            policy = CapabilityWorkItemPolicy(
                capability=capability,
                input_mode=input_mode,
                input_queue=None if mode == "producer" else "generic-input",
                output_queue=(
                    "produced" if mode == "producer" else "generic-input_output"
                )
                if outputs
                else None,
                max_output_items=4 if outputs else 0,
                max_output_bytes=4096 if outputs else 0,
            )
            for reference in (refs.worker, refs.policy, refs.output_provider):
                grant(
                    db,
                    actor,
                    refs.workspace,
                    "reference",
                    reference_grant_subject(reference),
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
                    "cancel_execution",
                    "read_application",
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
                        capability=capability,
                        mode="locked",
                        allowed_plans=declaration.runtime_plans,
                        default_plan=declaration.runtime_plans[0],
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
                idempotency_key="generic-" + mode,
            )
            queue_grant = grant(
                db,
                actor,
                refs.workspace,
                "reference",
                reference_grant_subject(revision.ref),
                [
                    "execute",
                    "cancel_execution",
                    "read_application",
                    *[p.value for p in Permission],
                ],
            )
            snapshot = deployments.resolve(
                actor, refs.workspace, refs.deployment_id, capability
            ).snapshot
            control = RunOutputControlPlane(db, capabilities=registry)
            control.register(snapshot)
            control.grant(actor, snapshot.deployment, {"execute", "read", "cancel"})
            base = RunOutputService(
                db,
                {snapshot.provider_key: foundry_package_store},
                capabilities=registry,
            )
            owner = GenericWorkItemExecution(
                deployments, base, snapshot, policy, SqlQueueAuthorization(db)
            )
            caller = ManagedCaller(actor=actor, worker_id=str(uuid4()))
            return SimpleNamespace(owner=owner, caller=caller, db=db, grant=queue_grant)

        yield setup


def test_enqueue_is_generic_atomic_idempotent_and_reauthorized(generic):
    g = generic()
    item = g.owner.enqueue(g.caller, {"value": "hello"}, "first")
    assert g.owner.enqueue(g.caller, {"value": "hello"}, "first") == item
    assert len(g.db.all(FencedWorkItem)) == 1
    assert not g.db.all(Run)
    assert (
        json.loads(g.db.all(FencedWorkItem)[0].payload)["schema"]
        == "actions.generic-work-item/v1"
    )
    with pytest.raises(FenceRejected):
        g.owner.enqueue(g.caller, {"value": "changed"}, "first")
    with g.db.transaction():
        _update(
            g.db,
            FoundryAccessGrant,
            g.grant.id,
            {"operations_json": '["execute","work_items.read"]'},
        )
    with pytest.raises(AccessDenied):
        g.owner.enqueue(g.caller, {"value": "hello"}, "first")


def test_enqueue_audit_failure_rolls_back(generic, monkeypatch):
    g = generic()
    original = g.db.insert

    def fail(row):
        if (
            isinstance(row, FoundryAudit)
            and row.operation == "generic-work-items.enqueue"
        ):
            raise RuntimeError("injected audit failure")
        original(row)

    monkeypatch.setattr(g.db, "insert", fail)
    with pytest.raises(RuntimeError):
        g.owner.enqueue(g.caller, {"value": "hello"}, "first")
    assert not g.db.all(FencedWorkItem)
    requests = [
        row
        for row in g.db.all(FoundryRequest)
        if row.operation == "generic-work-items.enqueue"
    ]
    assert requests == []


def dispatch(g):
    item = g.owner.enqueue(g.caller, {"value": "hello"}, "first")
    claim = g.owner.queue(g.owner.policy.input_queue).reserve_item_fenced(
        item, g.caller.worker_id, lease_seconds=60
    )
    return g.owner.dispatch(g.caller, claim, lease_seconds=60), claim


def test_consumer_pins_input_and_independent_epochs(generic):
    g = generic()
    item = g.owner.enqueue(g.caller, {"value": "hello"}, "first")
    queue = g.owner.queue(g.owner.policy.input_queue)
    first = queue.reserve_item_fenced(item, g.caller.worker_id, lease_seconds=60)
    with g.db.transaction():
        _update(g.db, FencedWorkItem, item, {"claim_deadline_ms": "0"})
    claim = queue.reserve_item_fenced(item, g.caller.worker_id, lease_seconds=60)
    ticket = g.owner.dispatch(g.caller, claim, lease_seconds=60)
    assert ticket.claim.epoch == 2 and ticket.fence.epoch == 1
    assert json.loads(_one(g.db, Run, ticket.fence.run_id).inputs) == {"value": "hello"}
    assert g.owner.dispatch(g.caller, claim, lease_seconds=60) == ticket
    with pytest.raises((FenceRejected, ClaimRejected)):
        g.owner.dispatch(g.caller, first, lease_seconds=60)
    guarded = g.owner.outputs(g.caller, ticket)
    guarded.heartbeat(ticket.fence, lease_seconds=60)
    with g.db.transaction():
        _update(g.db, FencedWorkItem, item, {"claim_epoch": 3})
    with pytest.raises((FenceRejected, ClaimRejected)):
        guarded.heartbeat(ticket.fence, lease_seconds=60)


@pytest.mark.parametrize("mode", ["optional", "producer"])
def test_standalone_does_not_create_synthetic_input(generic, mode):
    g = generic(mode, outputs=mode == "producer")
    ticket = g.owner.dispatch_standalone(
        g.caller, {"value": "hello"}, "standalone", lease_seconds=60
    )
    assert ticket.claim is None
    assert not g.db.all(FencedWorkItem)
    assert (
        g.owner.dispatch_standalone(
            g.caller, {"value": "hello"}, "standalone", lease_seconds=60
        )
        == ticket
    )
    g.owner.outputs(g.caller, ticket).heartbeat(ticket.fence, lease_seconds=60)


def test_optional_accepts_exact_item_context(generic):
    g = generic("optional")
    ticket, claim = dispatch(g)
    assert ticket.claim.item_id == claim.item_id


def synthetic_completion(g, ticket, action_result):
    """Owned source-contract fixture only; never represents real RCC proof."""
    guarded = g.owner.outputs(g.caller, ticket)
    output = guarded.stage(
        ticket.fence,
        [b"owned"],
        name="result.json",
        media_type="application/json",
        retention_seconds=60,
    )
    run = _one(g.db, Run, ticket.fence.run_id)
    journal = json.loads(run.result)
    journal.update(launch={"id": "synthetic"}, execution={"status": "completed"})
    with g.db.transaction():
        _update(g.db, Run, run.id, {"result": _canonical(journal, 65536)})
    result = {
        "version": "actions.generated-rcc-execution/v1",
        "claim": ticket.claim.model_dump() if ticket.claim else None,
        "publicationFence": ticket.fence.model_dump(),
        "launch": journal["launch"],
        "execution": journal["execution"],
        "actionResult": action_result,
    }
    return guarded, output, result


@pytest.mark.parametrize("mode", ["consumer", "producer"])
def test_atomic_output_lineage_and_replay(generic, mode):
    g = generic(mode, outputs=True)
    ticket = (
        dispatch(g)[0]
        if mode == "consumer"
        else g.owner.dispatch_standalone(
            g.caller, {"value": "hello"}, "standalone", lease_seconds=60
        )
    )
    guarded, output, result = synthetic_completion(
        g, ticket, {"result": "ok", "workItems": [{"value": "child"}]}
    )
    run = guarded.publish(g.caller.actor, ticket.fence, [output], result)
    assert run.status == RunStatus.PASSED
    children = [
        row
        for row in g.db.all(FencedWorkItem)
        if row.queue_name == g.owner.policy.output_queue
    ]
    assert len(children) == 1
    child = json.loads(children[0].payload)
    assert child["produced_by"]["fence"] == ticket.fence.model_dump()
    assert children[0].parent_id == (ticket.claim.item_id if ticket.claim else "")
    assert guarded.publish(g.caller.actor, ticket.fence, [output], result) == run
    assert (
        len(
            [
                row
                for row in g.db.all(FencedWorkItem)
                if row.queue_name == g.owner.policy.output_queue
            ]
        )
        == 1
    )


def test_unknown_output_mapping_never_completes(generic):
    g = generic("producer", outputs=True)
    ticket = g.owner.dispatch_standalone(
        g.caller, {"value": "hello"}, "standalone", lease_seconds=60
    )
    guarded, output, result = synthetic_completion(
        g, ticket, {"workItems": [{"value": "child"}]}
    )
    with pytest.raises(Exception):
        guarded.publish(g.caller.actor, ticket.fence, [output], result)
    assert not g.db.all(FencedWorkItem)
    assert _one(g.db, Run, ticket.fence.run_id).status == RunStatus.RUNNING


def test_schema_wrong_actor_and_changed_input_fail_closed(generic):
    from jsonschema.exceptions import ValidationError

    g = generic()
    with pytest.raises(ValidationError):
        g.owner.enqueue(g.caller, {"value": 3}, "bad-input")
    foreign = ManagedCaller(
        actor=Actor(principal_id=str(uuid4())), worker_id=str(uuid4())
    )
    with pytest.raises(PermissionError):
        g.owner.enqueue(foreign, {"value": "hello"}, "foreign")
    ticket, claim = dispatch(g)
    row = _one(g.db, FencedWorkItem, claim.item_id)
    payload = json.loads(row.payload)
    payload["inputs"] = {"value": "tampered"}
    with g.db.transaction():
        _update(g.db, FencedWorkItem, row.id, {"payload": json.dumps(payload)})
    with pytest.raises(FenceRejected):
        g.owner.outputs(g.caller, ticket).heartbeat(ticket.fence, lease_seconds=60)


def test_attempt_epoch_is_independently_fenced(generic):
    from actions.server.run_outputs.models import RunAttempt

    g = generic()
    ticket, claim = dispatch(g)
    with g.db.transaction():
        _update(
            g.db, RunAttempt, ticket.fence.attempt_id, {"epoch": ticket.fence.epoch + 1}
        )
    with pytest.raises(FenceRejected):
        g.owner.outputs(g.caller, ticket).heartbeat(ticket.fence, lease_seconds=60)
    assert _one(g.db, FencedWorkItem, claim.item_id).claim_epoch == claim.epoch


def test_cancel_fences_item_and_run(generic):
    g = generic()
    ticket, claim = dispatch(g)
    guarded = g.owner.outputs(g.caller, ticket)
    assert guarded.cancel(g.caller.actor, ticket.fence.run_id)
    assert _one(g.db, FencedWorkItem, claim.item_id).cancel_requested
    with pytest.raises((FenceRejected, ClaimRejected)):
        guarded.heartbeat(ticket.fence, lease_seconds=60)


def test_output_write_failure_rolls_back_run_completion(generic, monkeypatch):
    from actions.work_items._adapters._sql_review import SQLReviewQueue

    g = generic("producer", outputs=True)
    ticket = g.owner.dispatch_standalone(
        g.caller, {"value": "hello"}, "producer", lease_seconds=60
    )
    guarded, output, result = synthetic_completion(
        g, ticket, {"result": "ok", "workItems": [{"value": "child"}]}
    )

    def fail(*args, **kwargs):
        raise RuntimeError("injected child write failure")

    monkeypatch.setattr(SQLReviewQueue, "seed_input", fail)
    with pytest.raises(RuntimeError):
        guarded.publish(g.caller.actor, ticket.fence, [output], result)
    assert _one(g.db, Run, ticket.fence.run_id).status == RunStatus.RUNNING
    assert not g.db.all(FencedWorkItem)


@pytest.mark.parametrize("mode", ["consumer", "producer", "optional"])
def test_real_generic_rcc(generic, mode, tmp_path):
    import os
    from pathlib import Path

    from actions.server.deployments.package_revision_compiler import (
        load_prepared_rcc_environment,
    )
    from actions.server.foundry.rcc_execution import GeneratedRccExecution

    if not os.environ.get("ACTIONS_GENERIC_REAL_RCC"):
        pytest.skip("explicit owned prepared RCC gate required")
    g = generic(mode, outputs=mode != "optional", real=True)
    if mode == "consumer":
        ticket, claim = dispatch(g)
    else:
        ticket = g.owner.dispatch_standalone(
            g.caller, {"value": "hello"}, "real-rcc", lease_seconds=60
        )
        assert not g.db.all(FencedWorkItem)
    runner = GeneratedRccExecution(
        g.owner.registry,
        g.owner.outputs(g.caller, ticket),
        load_prepared_rcc_environment(
            Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
        ),
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]),
        tmp_path / "execution",
    )
    run = runner.execute(g.caller.actor, ticket.fence, cancelled=lambda: False)
    assert run.status == RunStatus.PASSED
    children = [
        row
        for row in g.db.all(FencedWorkItem)
        if row.parent_id == (ticket.claim.item_id if ticket.claim else "")
        and row.queue_name == g.owner.policy.output_queue
    ]
    if mode != "optional":
        assert len(children) == 1
        payload = json.loads(children[0].payload)
        assert payload["payload"] == {"value": "hello child"}
        assert payload["produced_by"]["fence"] == ticket.fence.model_dump(mode="json")
    if ticket.claim:
        assert (
            g.owner.dispatch(g.caller, ticket.claim.as_claim(), lease_seconds=60)
            == ticket
        )
    else:
        assert (
            g.owner.dispatch_standalone(
                g.caller, {"value": "hello"}, "real-rcc", lease_seconds=60
            )
            == ticket
        )
    # Terminal replay returns retained admission; the runner must not relaunch it.
    with pytest.raises((FenceRejected, ClaimRejected)):
        runner.execute(g.caller.actor, ticket.fence, cancelled=lambda: False)


def test_enqueue_replay_rejects_audit_scope_change(generic):
    g = generic()
    g.owner.enqueue(g.caller, {"value": "hello"}, "first")
    audit = next(
        row
        for row in g.db.all(FoundryAudit)
        if row.operation == "generic-work-items.enqueue"
    )
    with g.db.transaction():
        _update(g.db, FoundryAudit, audit.id, {"to_revision_id": "sha256:" + "0" * 64})
    with pytest.raises(FenceRejected, match="audit"):
        g.owner.enqueue(g.caller, {"value": "hello"}, "first")


def test_public_read_seam_reauthorizes(generic):
    g = generic()
    item = g.owner.enqueue(g.caller, {"value": "hello"}, "first")
    g.owner.authorize(g.caller, Permission.READ)
    assert g.owner.read_input(g.caller, item).inputs == {"value": "hello"}
    with g.db.transaction():
        _update(g.db, FoundryAccessGrant, g.grant.id, {"operations_json": "[]"})
    with pytest.raises(Exception):
        g.owner.read_input(g.caller, item)


def test_retained_execution_seams_never_admit(generic):
    g = generic()
    item = g.owner.enqueue(g.caller, {"value": "hello"}, "first")
    observer = ManagedCaller(actor=g.caller.actor)
    with pytest.raises(FenceRejected, match="unavailable"):
        g.owner.read_execution(observer, item)
    assert not g.db.all(Run)
    claim = g.owner.queue(g.owner.policy.input_queue).reserve_item_fenced(
        item, g.caller.worker_id, lease_seconds=60
    )
    ticket = g.owner.dispatch(g.caller, claim, lease_seconds=60)
    assert g.owner.retained_ticket(g.caller, claim) == ticket
    run, attempt, retained = g.owner.read_execution(observer, item)
    assert run.id == ticket.fence.run_id and attempt.id == ticket.fence.attempt_id
    assert retained == ticket
    with pytest.raises(FenceRejected):
        g.owner.outputs(observer, retained).heartbeat(retained.fence, lease_seconds=60)
    guarded, output, result = synthetic_completion(g, ticket, "hello")
    guarded.publish(g.caller.actor, ticket.fence, [output], result)
    assert g.owner.read_execution(observer, item)[0].status == RunStatus.PASSED
    assert g.owner.retained_ticket(g.caller, claim) == ticket


def test_failed_publication_requires_reconciliation(generic):
    g = generic()
    ticket, claim = dispatch(g)
    guarded, output, result = synthetic_completion(g, ticket, None)
    with pytest.raises(FenceRejected, match="reconciliation"):
        guarded.publish(
            g.caller.actor,
            ticket.fence,
            [output],
            result,
            terminal_status=RunStatus.FAILED,
        )
    assert _one(g.db, Run, ticket.fence.run_id).status == RunStatus.RUNNING
    assert _one(g.db, FencedWorkItem, claim.item_id).state == "IN_PROGRESS"


def test_read_only_observer_needs_no_execute_grant(generic):
    g = generic()
    ticket, claim = dispatch(g)
    actor = Actor(principal_id=str(uuid4()))
    observer = ManagedCaller(actor=actor)
    workspace = g.owner.snapshot.deployment.workspace_id
    grant(
        g.db,
        actor,
        workspace,
        "workspace",
        str(workspace.root),
        ["read_application", Permission.READ.value],
    )
    queue_grant = grant(
        g.db,
        actor,
        workspace,
        "reference",
        reference_grant_subject(g.owner.snapshot.deployment),
        [Permission.READ.value],
    )
    RunOutputControlPlane(g.db, capabilities=g.owner.registry).grant(
        actor, g.owner.snapshot.deployment, {"read"}
    )
    assert g.owner.read_input(observer, claim.item_id).inputs == {"value": "hello"}
    assert g.owner.read_execution(observer, claim.item_id)[2] == ticket
    with pytest.raises(Exception):
        g.owner.retained_ticket(observer, claim)
    with g.db.transaction():
        _update(g.db, FoundryAccessGrant, queue_grant.id, {"operations_json": "[]"})
    with pytest.raises(Exception):
        g.owner.read_execution(observer, claim.item_id)
