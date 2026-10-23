"""Canonical approved Work Item and generated Run fences on real SQL stores."""

from uuid import uuid4

import pytest
from action_server_tests import test_invoice_review as review_fixtures
from actions.work_items import State
from actions.work_items._fencing import ClaimRejected
from contract_tests.test_foundry_rcc_execution import _fake_registry

from actions.server.data_queries.review import ReviewConflict
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.run_outputs.service import FenceRejected

provider = review_fixtures.provider
postgresql_database = review_fixtures.postgresql_database
reviewed = review_fixtures.reviewed
pytestmark = review_fixtures.pytestmark
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def setup_generated(reviewed, foundry_package_store, *, real=False):
    from actions.server.foundry.work_item_execution import ReviewedGeneratedRun

    db, _, _, reviews, actor, scope, handle, query_snapshot = reviewed
    from action_server_tests.test_foundry_deployments import _refs

    refs = _refs()
    refs = refs.__class__(
        **{**vars(refs), "workspace": query_snapshot.deployment.workspace_id}
    )
    if real:
        import os
        from pathlib import Path

        from action_server_tests.test_foundry_package_registry import _grant
        from contract_tests.test_package_revision_compiler import (
            _generated_action_entries,
        )

        from actions.server.deployments.package_revision_compiler import (
            PinnedRccPackageBuildExecutor,
            TrustedDeveloperExecutionAdmission,
            load_prepared_rcc_environment,
        )
        from actions.server.deployments.source_manifest import SuppliedSourceEntry
        from actions.server.foundry.package_registry import FoundryPackageRegistry
        from actions.server.foundry.sql_authorization import SqlFoundryAuthorization

        prepared = load_prepared_rcc_environment(
            Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
        )
        _grant(db, refs, actor)
        registry = FoundryPackageRegistry(
            db,
            foundry_package_store,
            SqlFoundryAuthorization(db),
            executor=PinnedRccPackageBuildExecutor(prepared),
            admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        )
        action = b'from actions import action\nimport json\n@action\ndef generated_echo(value: str) -> str:\n    rows=[json.loads(line) for line in value.splitlines()]\n    return json.dumps({"invoice_count":len(rows),"total_cents":sum(row["amount_cents"] for row in rows)},sort_keys=True)\n'
        entries = _generated_action_entries(action)
        entries[-1] = SuppliedSourceEntry(
            "tests/test_generated_action.py",
            "file",
            b"""import unittest,json
from generated_actions import generated_echo
class GeneratedActionTest(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(json.loads(generated_echo(value='{"amount_cents":200}')), {"invoice_count":1,"total_cents":200})
""",
            0o644,
        )
        outcome = registry.compile_trusted_source(
            entries,
            logical_package_key="reviewed-summary",
            logical_name="Reviewed summary",
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
        )
        assert outcome.evidence.ready, outcome.evidence
        package = registry.admit_compiled(
            actor, refs.workspace, outcome.compiled_package
        )
    else:
        registry, package = _fake_registry(db, foundry_package_store, refs, actor)
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.foundry.sql_authorization import reference_grant_subject
    from actions.server.run_outputs.service import (
        RunOutputControlPlane,
        RunOutputService,
    )
    from actions.server.run_outputs.types import ExecutionSnapshot

    capability = registry.capability_refs(package)[0]
    declared = registry.get_capability(capability)
    payload = query_snapshot.model_dump(mode="json")
    payload.update(
        capability_authority="package-revision",
        capability=capability.model_dump(mode="json"),
        runtime_plan=declared.runtime_plans[0].model_dump(mode="json"),
        runtime_kind="rcc",
        action_id=registry.action_id_for(capability),
        capability_schema_digest=declared.schema_digest,
        data_binding=None,
    )
    snapshot = ExecutionSnapshot.model_validate(payload)
    base = RunOutputService(db, reviews.outputs.providers, capabilities=registry)
    control = RunOutputControlPlane(db, capabilities=registry)
    with db.transaction():
        for ref in (
            snapshot.deployment,
            snapshot.worker,
            snapshot.policy,
            snapshot.output_provider,
        ):
            db.insert(
                FoundryAccessGrant(
                    str(uuid4()),
                    snapshot.workspace_id,
                    actor.principal_id,
                    "reference",
                    reference_grant_subject(ref),
                    '["execute"]',
                )
            )
        db.insert(
            FoundryAccessGrant(
                str(uuid4()),
                snapshot.workspace_id,
                actor.principal_id,
                "workspace",
                snapshot.workspace_id,
                '["read_application","cancel_execution"]',
            )
        )
    control.register(snapshot)
    control.grant(actor, snapshot.deployment, {"execute", "read", "review", "cancel"})
    service = ReviewedGeneratedRun(reviews, scope, snapshot, base)
    return service, actor, reviews.offer(actor, scope, handle)


def test_explicit_approval_and_exact_claim_are_required(
    reviewed, foundry_package_store
):
    service, actor, proposal = setup_generated(reviewed, foundry_package_store)
    from actions.work_items._fencing import WorkItemClaim

    claim = WorkItemClaim(str(uuid4()), str(uuid4()), 1)
    with pytest.raises((ReviewConflict, ClaimRejected)):
        service.dispatch(actor, proposal, claim, lease_seconds=30)
    reviews = reviewed[3]
    approved = reviews.decide(actor, service.scope, proposal, "approve")
    claim = reviews.queue(service.scope).reserve_fenced(str(uuid4()), lease_seconds=30)
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=30)
    assert ticket.claim.item_id == approved.work_item_id
    assert service.dispatch(actor, proposal, claim, lease_seconds=30) == ticket
    assert ticket.fence.run_id != proposal.binding.run_id
    assert service.outputs(actor, ticket).execution_context(actor, ticket.fence)[1][
        "value"
    ]


def test_live_run_fence_cannot_publish_after_work_item_lease_loss(
    reviewed, foundry_package_store
):
    service, actor, proposal = setup_generated(reviewed, foundry_package_store)
    db, _, _, reviews, *_ = reviewed
    reviews.decide(actor, service.scope, proposal, "approve")
    queue = reviews.queue(service.scope)
    claim = queue.reserve_fenced(str(uuid4()), lease_seconds=30)
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=30)
    outputs = service.outputs(actor, ticket)
    output = outputs.stage(
        ticket.fence,
        [b'"owned"'],
        name="result.json",
        media_type="application/json",
        retention_seconds=60,
    )
    with db.transaction():
        db.update_by_id(FencedWorkItem, claim.item_id, {"claim_deadline_ms": "0"})
    replacement = queue.reserve_fenced(claim.owner_id, lease_seconds=30)
    assert replacement.epoch == claim.epoch + 1
    with pytest.raises((ClaimRejected, FenceRejected)):
        outputs.publish(actor, ticket.fence, [output], receipt(ticket))
    assert queue.list_items()[0]["state"] == State.IN_PROGRESS.value


def approved_ticket(reviewed, foundry_package_store):
    service, actor, proposal = setup_generated(reviewed, foundry_package_store)
    reviews = reviewed[3]
    reviews.decide(actor, service.scope, proposal, "approve")
    claim = reviews.queue(service.scope).reserve_fenced(str(uuid4()), lease_seconds=30)
    return service, actor, service.dispatch(actor, proposal, claim, lease_seconds=30)


def receipt(ticket):
    return {
        "version": "actions.generated-rcc-execution/v1",
        "claim": ticket.claim.model_dump(),
        "publicationFence": ticket.fence.model_dump(),
    }


def test_publication_and_work_item_finish_commit_together(
    reviewed, foundry_package_store, monkeypatch
):
    from actions.work_items._adapters._sql_review import SQLReviewQueue

    from actions.server._models import Run, RunStatus
    from actions.server.run_outputs.models import RunOutput

    service, actor, ticket = approved_ticket(reviewed, foundry_package_store)
    db = reviewed[0]
    outputs = service.outputs(actor, ticket)
    output = outputs.stage(
        ticket.fence,
        [b'"owned"'],
        name="result.json",
        media_type="application/json",
        retention_seconds=60,
    )
    original = SQLReviewQueue.finish_fenced

    def fail_after_write(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("synthetic post-finish transaction failure")

    with monkeypatch.context() as patch:
        patch.setattr(SQLReviewQueue, "finish_fenced", fail_after_write)
        with pytest.raises(RuntimeError, match="synthetic post-finish"):
            outputs.publish(actor, ticket.fence, [output], receipt(ticket))
    assert (
        db.first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id]).status
        == RunStatus.RUNNING
    )
    assert (
        db.first(
            RunOutput, "SELECT * FROM run_output WHERE id=?", [output.output_id]
        ).state
        == "provisional"
    )
    assert (
        service.reviews.queue(service.scope).list_items()[0]["state"]
        == State.IN_PROGRESS.value
    )
    finished = outputs.publish(actor, ticket.fence, [output], receipt(ticket))
    assert finished.status == RunStatus.PASSED
    assert (
        service.reviews.queue(service.scope).list_items()[0]["state"]
        == State.DONE.value
    )
    assert outputs.publish(actor, ticket.fence, [output], receipt(ticket)) == finished
    assert (
        service.dispatch(
            actor, ticket.proposal, ticket.claim.as_claim(), lease_seconds=30
        )
        == ticket
    )


def test_expired_dispatch_replay_cannot_present_a_live_ticket(
    reviewed, foundry_package_store
):
    service, actor, ticket = approved_ticket(reviewed, foundry_package_store)
    with reviewed[0].transaction():
        reviewed[0].update_by_id(
            FencedWorkItem, ticket.claim.item_id, {"claim_deadline_ms": "0"}
        )
    with pytest.raises(ClaimRejected):
        service.dispatch(
            actor, ticket.proposal, ticket.claim.as_claim(), lease_seconds=30
        )


def test_work_item_cancellation_and_reviewer_revocation_fence_staging(
    reviewed, foundry_package_store
):
    from actions.server.run_outputs.service import AccessDenied

    service, actor, ticket = approved_ticket(reviewed, foundry_package_store)
    db, control, _, reviews, *_ = reviewed
    outputs = service.outputs(actor, ticket)
    control.grant(actor, service.scope.deployment, {"execute", "read", "cancel"})
    with pytest.raises(AccessDenied):
        outputs.stage(
            ticket.fence,
            [b'"denied"'],
            name="result.json",
            media_type="application/json",
            retention_seconds=60,
        )
    control.grant(
        actor, service.scope.deployment, {"execute", "read", "review", "cancel"}
    )
    assert reviews.queue(service.scope).cancel(ticket.claim.item_id)
    with pytest.raises(ClaimRejected):
        outputs.heartbeat(ticket.fence, lease_seconds=30)


def test_explicit_no_launch_recovery_replaces_expired_dual_owner_and_audits(
    reviewed, foundry_package_store
):
    from actions.server.foundry.models import FoundryAudit
    from actions.server.run_outputs.models import RunAttempt

    service, actor, old = approved_ticket(reviewed, foundry_package_store)
    db = reviewed[0]
    with db.transaction():
        db.update_by_id(FencedWorkItem, old.claim.item_id, {"claim_deadline_ms": "0"})
        db.update_by_id(RunAttempt, old.fence.attempt_id, {"lease_deadline_ms": "0"})
    claim = service.reviews.queue(service.scope).reserve_fenced(
        str(uuid4()), lease_seconds=30
    )
    recovered = service.recover_no_launch(actor, old, claim, lease_seconds=30)
    assert recovered.fence.run_id == old.fence.run_id
    assert recovered.fence.attempt_id != old.fence.attempt_id
    assert recovered.fence.epoch == old.fence.epoch + 1
    assert recovered.claim.epoch == old.claim.epoch + 1
    assert service.recover_no_launch(actor, old, claim, lease_seconds=30) == recovered
    assert (
        len(
            [
                row
                for row in db.all(FoundryAudit)
                if row.operation == "generated.no-launch-recovery"
            ]
        )
        == 1
    )
    import json

    from actions.server.foundry.models import FoundryRequest

    recovery = next(
        row
        for row in db.all(FoundryRequest)
        if row.operation == "generated.no-launch-recovery"
    )
    assert json.loads(recovery.result_json)["from"] == old.model_dump(mode="json")
    with pytest.raises((FenceRejected, ClaimRejected)):
        service.outputs(actor, old).heartbeat(old.fence, lease_seconds=30)


def test_prior_launch_intent_cannot_be_reclassified_as_no_effect(
    reviewed, foundry_package_store
):
    import json

    from actions.server._models import Run
    from actions.server.run_outputs.models import RunAttempt

    service, actor, old = approved_ticket(reviewed, foundry_package_store)
    db = reviewed[0]
    with db.transaction():
        run = db.first(Run, "SELECT * FROM run WHERE id=?", [old.fence.run_id])
        record = json.loads(run.result)
        record["launch"] = {"id": str(uuid4())}
        db.update_by_id(Run, run.id, {"result": json.dumps(record)})
        db.update_by_id(FencedWorkItem, old.claim.item_id, {"claim_deadline_ms": "0"})
        db.update_by_id(RunAttempt, old.fence.attempt_id, {"lease_deadline_ms": "0"})
    claim = service.reviews.queue(service.scope).reserve_fenced(
        str(uuid4()), lease_seconds=30
    )
    with pytest.raises(FenceRejected, match="reconcil"):
        service.recover_no_launch(actor, old, claim, lease_seconds=30)
