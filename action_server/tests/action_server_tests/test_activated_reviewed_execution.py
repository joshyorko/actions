"""Activated common Deployment selection before exact reviewed native admission."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_review as fixture
from action_server_tests.test_generated_work_item_execution import setup_generated

from actions.server._models import Run
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    CapabilityPlanPolicy,
    DeploymentSpecification,
)
from actions.server.foundry.authoring_values import CanvasBinding
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.sql_authoring import SqlAuthoringAuthority
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.service import AccessDenied, RunOutputControlPlane
from actions.server.run_outputs.types import CanvasResultScope

provider = fixture.provider
postgresql_database = fixture.postgresql_database
reviewed = fixture.reviewed
pytestmark = fixture.pytestmark
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def fingerprint(label):
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def setup_activated(
    reviewed,
    foundry_package_store,
    *,
    real=False,
    backend_entries=None,
    logical_key="reviewed-summary",
):
    previous, actor, _ = setup_generated(
        reviewed,
        foundry_package_store,
        real=real,
        backend_entries=backend_entries,
        logical_key=logical_key,
    )
    db, control, queries, reviews, _, _, _, query_snapshot = reviewed
    registry = previous.base.capabilities
    auth = SqlFoundryAuthorization(db)
    repository = FoundryRepository(db)
    deployments = FoundryDeploymentService(repository, registry, auth, registry)
    authority = SqlAuthoringAuthority(
        repository, deployments, auth, package_evidence=registry.evidence
    )
    workspace = previous.snapshot.deployment.workspace_id
    with db.transaction():
        db.insert(
            FoundryAccessGrant(
                str(uuid4()),
                str(workspace.root),
                actor.principal_id,
                "workspace",
                str(workspace.root),
                json.dumps(
                    [
                        "create_application",
                        "apply_revision",
                        "read_application",
                        "inspect_application",
                        "release_application",
                        "deploy",
                        "execute",
                    ]
                ),
            )
        )
        for ref in (
            previous.snapshot.worker,
            previous.snapshot.policy,
            previous.snapshot.output_provider,
        ):
            db.insert(
                FoundryAccessGrant(
                    str(uuid4()),
                    str(workspace.root),
                    actor.principal_id,
                    "reference",
                    reference_grant_subject(ref),
                    '["deploy","execute"]',
                )
            )
    spec = {
        "schemaVersion": "actions.canvas-spec/v1",
        "title": "Owned blank",
        "visibility": ["model", "app"],
        "bindingIds": [],
        "root": {"type": "stack", "id": "main", "children": []},
    }
    first = authority.create(
        actor,
        workspace,
        json.dumps(spec).encode(),
        request_fingerprint=fingerprint("blank"),
        idempotency_key="blank",
    )
    spec.update(
        title="Owned generated job",
        bindingIds=["run"],
        root={
            "type": "form",
            "id": "job",
            "bindingId": "run",
            "submitLabel": "Run approved result",
            "fields": [
                {
                    "name": "value",
                    "label": "Saved result",
                    "type": "text",
                    "required": True,
                }
            ],
        },
    )
    capability = previous.snapshot.capability
    plan = previous.snapshot.runtime_plan
    selection = DeploymentSpecification(
        package_revisions=(capability.package_revision,),
        capability_plans=(
            CapabilityPlanPolicy(
                capability=capability,
                mode="locked",
                allowed_plans=(plan,),
                default_plan=plan,
            ),
        ),
        worker=previous.snapshot.worker,
        policy=previous.snapshot.policy,
        output_provider=previous.snapshot.output_provider,
    )
    staged = authority.apply(
        actor,
        workspace,
        first.application_id,
        first.ref,
        json.dumps(spec).encode(),
        (CanvasBinding("run", capability),),
        (capability.package_revision,),
        selection,
        registry.evidence(capability.package_revision),
        fingerprint("backend"),
        idempotency_key="backend",
    )
    stored = repository.get_revision(staged.ref)
    scope = CanvasResultScope(
        deployment=staged.ref,
        application=stored.revision.specification.canvas_application,
    )
    with db.transaction():
        db.insert(
            FoundryAccessGrant(
                str(uuid4()),
                str(workspace.root),
                actor.principal_id,
                "reference",
                reference_grant_subject(staged.ref),
                '["deploy","execute"]',
            )
        )
    source = query_snapshot.model_copy(
        update={"deployment": staged.ref, "canvas_application": scope.application}
    )
    control.register(source)
    control.grant(actor, staged.ref, {"read", "execute", "review", "cancel"})
    run = reviews.outputs.admit(actor, source, {"min_days": 0}, "activated-source")
    handle = queries.execute(
        actor, reviews.outputs.claim(run.id, str(uuid4()), lease_seconds=30), Event()
    )
    proposal = reviews.offer(actor, scope, handle)
    return SimpleNamespace(
        db=db,
        actor=actor,
        reviews=reviews,
        scope=scope,
        outputs=previous.base,
        repository=repository,
        deployments=deployments,
        authority=authority,
        staged=staged,
        proposal=proposal,
        selection=selection,
        spec=spec,
        first=first,
        source=source,
    )


def adapter(case):
    from actions.server.foundry.activated_execution import ActivatedReviewedExecution

    return ActivatedReviewedExecution(
        case.deployments,
        case.reviews,
        case.outputs,
        worker_id="e530355c-8c66-4ebc-b86d-2d76c85f7169",
    )


def release(case):
    return case.authority.release(
        case.actor,
        case.staged.ref.workspace_id,
        case.staged.application_id,
        case.staged.ref,
        None,
        fingerprint("release"),
        idempotency_key="release",
    )


def test_staged_backend_cannot_claim_or_admit_before_explicit_activation(
    reviewed, foundry_package_store
):
    case = setup_activated(reviewed, foundry_package_store)
    approved = case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    before = len(case.db.all(Run))
    with pytest.raises((AccessDenied, PermissionError)):
        adapter(case).dispatch(case.actor, case.scope, "run", case.proposal)
    assert len(case.db.all(Run)) == before
    item = next(
        row
        for row in case.reviews.queue(case.scope).list_items()
        if row["id"] == approved.work_item_id
    )
    assert item["state"] == "PENDING" and item["claim_epoch"] == 0


def test_active_dispatch_claims_exact_result_and_reuses_one_pinned_run(
    reviewed, foundry_package_store
):
    case = setup_activated(reviewed, foundry_package_store)
    release(case)
    older_run = case.reviews.outputs.admit(
        case.actor, case.source, {"min_days": 10}, "older-result"
    )
    older_handle = case.reviews.queries.execute(
        case.actor,
        case.reviews.outputs.claim(older_run.id, str(uuid4()), lease_seconds=30),
        Event(),
    )
    older = case.reviews.offer(case.actor, case.scope, older_handle)
    older_receipt = case.reviews.decide(case.actor, case.scope, older, "approve")
    approved = case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    before = len(case.db.all(Run))
    grants = len(case.db.all(FoundryAccessGrant))
    selected = adapter(case)
    ticket = selected.dispatch(case.actor, case.scope, "run", case.proposal)
    assert ticket.claim.item_id == approved.work_item_id
    assert ticket.fence.run_id != case.proposal.binding.run_id
    assert selected.dispatch(case.actor, case.scope, "run", case.proposal) == ticket
    assert (
        len(case.db.all(Run)) == before + 1
        and len(case.db.all(FoundryAccessGrant)) == grants
    )
    service = selected.resume(case.actor, ticket)
    snapshot, _ = service.outputs(case.actor, ticket).execution_context(
        case.actor, ticket.fence
    )
    assert (
        snapshot.deployment == case.staged.ref
        and snapshot.canvas_application == case.scope.application
    )
    items = {row["id"]: row for row in case.reviews.queue(case.scope).list_items()}
    assert items[older_receipt.work_item_id]["state"] == "PENDING"
    assert items[older_receipt.work_item_id]["claim_epoch"] == 0


def test_concurrent_exact_dispatch_admits_one_claim_run_and_attempt(
    reviewed, foundry_package_store
):
    from actions.server.run_outputs.models import RunAttempt

    case = setup_activated(reviewed, foundry_package_store)
    release(case)
    case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    before = (len(case.db.all(Run)), len(case.db.all(RunAttempt)))
    barrier = Barrier(2)

    def dispatch(_):
        barrier.wait(timeout=20)
        return adapter(case).dispatch(case.actor, case.scope, "run", case.proposal)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(dispatch, range(2))
    assert first == second
    assert (len(case.db.all(Run)), len(case.db.all(RunAttempt))) == (
        before[0] + 1,
        before[1] + 1,
    )
    assert len(case.reviews.queue(case.scope).list_items()) == 1
    assert case.reviews.queue(case.scope).list_items()[0]["claim_epoch"] == 1


@pytest.mark.parametrize(
    "failure",
    ["unapproved", "unselected-binding", "changed-application", "revoked-source"],
)
def test_active_dispatch_denials_leave_claim_and_run_unchanged(
    reviewed, foundry_package_store, failure
):
    case = setup_activated(reviewed, foundry_package_store)
    release(case)
    if failure != "unapproved":
        case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    proposal = case.proposal
    binding = "run"
    if failure == "unselected-binding":
        binding = "other"
    if failure == "changed-application":
        changed = proposal.binding.scope.model_copy(
            update={
                "application": proposal.binding.scope.application.model_copy(
                    update={"revision_id": "sha256:" + "0" * 64}
                )
            }
        )
        proposal = proposal.model_copy(
            update={"binding": proposal.binding.model_copy(update={"scope": changed})}
        )
    if failure == "revoked-source":
        RunOutputControlPlane(case.db).revoke(case.actor, case.scope.deployment)
    before = len(case.db.all(Run))
    with pytest.raises((AccessDenied, PermissionError, ValueError)):
        adapter(case).dispatch(case.actor, case.scope, binding, proposal)
    assert len(case.db.all(Run)) == before
    assert all(
        row["claim_epoch"] == 0 for row in case.reviews.queue(case.scope).list_items()
    )


def test_new_activation_blocks_stale_dispatch_but_preserves_admitted_pin(
    reviewed, foundry_package_store
):
    case = setup_activated(reviewed, foundry_package_store)
    release(case)
    case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    selected = adapter(case)
    ticket = selected.dispatch(case.actor, case.scope, "run", case.proposal)
    revised = dict(case.spec, title="Revised generated app")
    next_revision = case.authority.apply(
        case.actor,
        case.staged.ref.workspace_id,
        case.staged.application_id,
        case.staged.ref,
        json.dumps(revised).encode(),
        (CanvasBinding("run", case.selection.capability_plans[0].capability),),
        case.staged.package_revisions,
        case.selection,
        case.staged.compilation,
        fingerprint("revised"),
        idempotency_key="revised",
    )
    case.authority.release(
        case.actor,
        case.staged.ref.workspace_id,
        case.staged.application_id,
        next_revision.ref,
        case.staged.ref,
        fingerprint("release-next"),
        idempotency_key="release-next",
    )
    with pytest.raises(AccessDenied):
        selected.dispatch(case.actor, case.scope, "run", case.proposal)
    resumed = selected.resume(case.actor, ticket)
    pinned, _ = resumed.outputs(case.actor, ticket).execution_context(
        case.actor, ticket.fence
    )
    assert pinned.deployment == case.staged.ref
    assert (
        case.repository.current(
            case.staged.ref.workspace_id, case.staged.application_id
        ).revision.ref
        == next_revision.ref
    )
    case.authority.rollback(
        case.actor,
        case.staged.ref.workspace_id,
        case.staged.application_id,
        case.staged.ref,
        next_revision.ref,
        fingerprint("rollback"),
        idempotency_key="rollback",
    )
    assert selected.dispatch(case.actor, case.scope, "run", case.proposal) == ticket


def test_expired_exact_claim_is_not_automatically_reclaimed_or_relaunched(
    reviewed, foundry_package_store
):
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.service import FenceRejected

    case = setup_activated(reviewed, foundry_package_store)
    release(case)
    case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    selected = adapter(case)
    ticket = selected.dispatch(case.actor, case.scope, "run", case.proposal)
    with case.db.transaction():
        case.db.update_by_id(
            FencedWorkItem, ticket.claim.item_id, {"claim_deadline_ms": "0"}
        )
    before = len(case.db.all(Run))
    with pytest.raises(FenceRejected):
        selected.resume(case.actor, ticket)
    with pytest.raises(FenceRejected):
        selected.dispatch(case.actor, case.scope, "run", case.proposal)
    assert len(case.db.all(Run)) == before
    item = next(
        row
        for row in case.reviews.queue(case.scope).list_items()
        if row["id"] == ticket.claim.item_id
    )
    assert item["claim_epoch"] == 1


def test_admission_sql_failure_rolls_back_claim_and_registration(
    reviewed, foundry_package_store
):
    from actions.server._database import DBError
    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.run_outputs.models import RunAdmission

    case = setup_activated(reviewed, foundry_package_store)
    release(case)
    approved = case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    action = case.outputs.capabilities.action_id_for(
        case.selection.capability_plans[0].capability
    )
    assert str(__import__("uuid").UUID(action)) == action
    with case.db.transaction():
        if case.db.backend_name == "sqlite":
            case.db.execute(
                "CREATE TRIGGER owned_admit_fault BEFORE INSERT ON run WHEN NEW.action_id='"
                + action
                + "' BEGIN SELECT RAISE(ABORT,'owned admission fault'); END"
            )
        else:
            case.db.execute(
                "CREATE FUNCTION owned_admit_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action_id='"
                + action
                + "' THEN RAISE EXCEPTION 'owned admission fault'; END IF; RETURN NEW; END $$"
            )
            case.db.execute(
                "CREATE TRIGGER owned_admit_fault BEFORE INSERT ON run FOR EACH ROW EXECUTE FUNCTION owned_admit_fault()"
            )
    before = (len(case.db.all(Run)), len(case.db.all(RunAdmission)))
    with pytest.raises(DBError):
        adapter(case).dispatch(case.actor, case.scope, "run", case.proposal)
    assert (len(case.db.all(Run)), len(case.db.all(RunAdmission))) == before
    item = case.db.first(
        FencedWorkItem,
        "SELECT * FROM fenced_work_item WHERE id=?",
        [approved.work_item_id],
    )
    assert item.state == "PENDING" and item.claim_epoch == 0
