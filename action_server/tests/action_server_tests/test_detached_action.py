"""Detached ordinary Action authority; no RCC is executed by this module."""
from uuid import uuid4

import pytest
from action_server_tests import test_generic_canvas_view as app_tests

from actions.server._models import Run, RunStatus
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import RunPin
from actions.server.run_outputs.service import FenceRejected, _one

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = app_tests.provider
postgresql_database = app_tests.postgresql_database
reviewed = app_tests.reviewed
case = app_tests.case
pytestmark = app_tests.pytestmark


def setup(c):
    service, caller = c.port._selected(c.app, "run")
    owner = DetachedActions(c.deployments, c.outputs)
    return owner, service, caller


def test_admission_is_durable_unclaimed_and_replayable(case):
    c = case
    owner, service, caller = setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "detached")
    assert run.status == RunStatus.NOT_RUN
    assert not _one(c.db, RunPin, run.id).current_attempt_id
    assert (
        owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "detached").id
        == run.id
    )
    with pytest.raises(ValueError):
        owner.admit(caller.actor, service.snapshot, {"value": "changed"}, "detached")
    assert owner.pending(
        caller.actor, service.snapshot.workspace_id, service.snapshot.worker
    ).run_ids == (run.id,)
    ticket = owner.claim(caller, run.id, service.snapshot.worker)
    assert _one(c.db, Run, run.id).status == RunStatus.RUNNING
    assert owner.claim(caller, run.id, service.snapshot.worker) == ticket
    other = ManagedCaller(actor=caller.actor, worker_id=str(uuid4()))
    with pytest.raises(FenceRejected):
        owner.claim(other, run.id, service.snapshot.worker)


def test_queued_cancel_is_terminal_without_attempt(case):
    c = case
    owner, service, caller = setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "cancel")
    assert owner.cancel(caller.actor, run.id)
    assert _one(c.db, Run, run.id).status == RunStatus.CANCELLED
    assert not _one(c.db, RunPin, run.id).current_attempt_id
    assert (
        owner.pending(
            caller.actor, service.snapshot.workspace_id, service.snapshot.worker
        ).run_ids
        == ()
    )
    with pytest.raises(FenceRejected):
        owner.claim(caller, run.id, service.snapshot.worker)


def test_worker_guard_reads_durable_cancel_and_expiry(case):
    from actions.server.run_outputs.detached import DetachedActionWorker
    from actions.server.run_outputs.models import RunAttempt
    from actions.server.run_outputs.service import _update

    c = case
    owner, service, caller = setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "guard")
    worker = DetachedActionWorker(
        owner, caller.actor, caller.worker_id, service.snapshot.worker
    )
    ticket = worker.claim(run.id)
    assert not worker.cancelled(ticket)
    with c.db.transaction():
        _update(c.db, RunAttempt, ticket.fence.attempt_id, {"lease_deadline_ms": "0"})
    with pytest.raises(FenceRejected):
        worker.cancelled(ticket)
    assert owner.cancel(caller.actor, run.id)
    assert worker.cancelled(ticket)
    assert _one(c.db, Run, run.id).status == RunStatus.RUNNING


def test_loss_requires_explicit_recovery_and_preserves_run(case):
    from actions.server.run_outputs.models import RunAttempt
    from actions.server.run_outputs.service import RunOutputControlPlane, _update

    c = case
    owner, service, caller = setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "loss")
    first = owner.claim(caller, run.id, service.snapshot.worker)
    with c.db.transaction():
        _update(c.db, RunAttempt, first.fence.attempt_id, {"lease_deadline_ms": "0"})
    other = ManagedCaller(actor=caller.actor, worker_id=str(uuid4()))
    with pytest.raises(FenceRejected):
        owner.claim(other, run.id, service.snapshot.worker)
    assert (
        owner.pending(
            caller.actor, service.snapshot.workspace_id, service.snapshot.worker
        ).run_ids
        == ()
    )
    RunOutputControlPlane(c.db).authorize_recovery(
        run.id, first.fence.epoch, receipt="test-operator-verified-no-effects"
    )
    second = owner.claim(other, run.id, service.snapshot.worker)
    assert second.fence.run_id == run.id and second.fence.epoch == first.fence.epoch + 1
    assert first.input_digest == second.input_digest
    assert _one(c.db, RunAttempt, first.fence.attempt_id).state == "lost"
    with pytest.raises(FenceRejected):
        service.outputs(caller, first).heartbeat(first.fence, lease_seconds=60)


@pytest.mark.parametrize(
    "which", ["actor", "run-grant", "workspace-grant", "metadata", "worker"]
)
def test_live_authority_and_immutable_metadata(case, which):
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.run_outputs.models import RunExecutionIntent
    from actions.server.run_outputs.service import RunOutputControlPlane, _update
    from actions.server.run_outputs.types import Actor

    c = case
    owner, service, caller = setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "negative")
    profile = service.snapshot.worker
    if which == "actor":
        caller = ManagedCaller(
            actor=Actor(principal_id=str(uuid4())), worker_id=caller.worker_id
        )
    elif which == "run-grant":
        RunOutputControlPlane(c.db).revoke(caller.actor, service.snapshot.deployment)
    elif which == "workspace-grant":
        with c.db.transaction():
            for grant in c.db.all(FoundryAccessGrant):
                if grant.subject_kind == "workspace":
                    _update(
                        c.db, FoundryAccessGrant, grant.id, {"operations_json": "[]"}
                    )
    elif which == "metadata":
        with c.db.transaction():
            _update(c.db, RunExecutionIntent, run.id, {"envelope_json": "{}"})
    else:
        profile = profile.model_copy(update={"revision_id": "sha256:" + "0" * 64})
    with pytest.raises((PermissionError, FenceRejected)):
        owner.claim(caller, run.id, profile)
    assert not _one(c.db, RunPin, run.id).current_attempt_id


def test_bounded_scan_and_unsupported_mode(case):
    from action_server_tests.test_generic_output_canvas_view import configure

    from actions.server.run_outputs.service import AccessDenied

    c = case
    owner, service, caller = setup(c)
    for i in range(3):
        owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "scan" + str(i))
    first = owner.pending(
        caller.actor, service.snapshot.workspace_id, service.snapshot.worker, limit=2
    )
    second = owner.pending(
        caller.actor,
        service.snapshot.workspace_id,
        service.snapshot.worker,
        limit=2,
        after=first.next_cursor,
    )
    assert len(first.run_ids) == 2 and len(second.run_ids) == 1
    assert not set(first.run_ids) & set(second.run_ids)
    with pytest.raises(ValueError):
        owner.pending(
            caller.actor,
            service.snapshot.workspace_id,
            service.snapshot.worker,
            limit=101,
        )
    configure(c, "consumer")
    consumer, managed = c.port._selected(c.app, "run")
    with pytest.raises(AccessDenied):
        owner.admit(managed.actor, consumer.snapshot, {"value": "hello"}, "unsupported")
    # Explicit old activated revision remains pinned despite new active binding.
    ticket = owner.claim(caller, first.run_ids[0], service.snapshot.worker)
    assert service.ticket(caller, _one(c.db, Run, ticket.fence.run_id)) == ticket


def test_synchronous_and_detached_admissions_do_not_adopt_each_other(case):
    c = case
    owner, service, caller = setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "detached")
    with pytest.raises(FenceRejected):
        service.dispatch_standalone(caller, {"value": "hello"}, "detached")
    assert not _one(c.db, RunPin, run.id).current_attempt_id
    service.dispatch_standalone(caller, {"value": "hello"}, "sync")
    with pytest.raises(FenceRejected):
        owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "sync")


def test_competing_worker_connections_have_one_owner(case):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    c = case
    owner, service, caller = setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "race")
    barrier = Barrier(2)

    def claim():
        worker = ManagedCaller(actor=caller.actor, worker_id=str(uuid4()))
        with c.db.connect():
            barrier.wait(timeout=10)
            try:
                return owner.claim(worker, run.id, service.snapshot.worker)
            except FenceRejected:
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(claim) for _ in range(2)]
        results = [future.result(timeout=30) for future in futures]
    assert sum(result is not None for result in results) == 1


def test_execution_receives_sql_guard_before_preparation_and_during_work(
    case, monkeypatch, tmp_path
):
    from actions.server.run_outputs import detached

    c = case
    owner, service, caller = setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "guard-seam")
    worker = detached.DetachedActionWorker(
        owner, caller.actor, caller.worker_id, service.snapshot.worker
    )
    ticket = worker.claim(run.id)
    calls = []

    class BoundaryExecutor:
        def __init__(self, registry, outputs, prepared, rcc, execution_root):
            self.outputs = outputs

        def execute(self, actor, fence, *, cancelled):
            assert not cancelled()
            self.outputs.heartbeat(fence, lease_seconds=60)
            calls.append("prepared")
            assert owner.cancel(actor, run.id)
            assert cancelled()
            with pytest.raises(FenceRejected):
                self.outputs.heartbeat(fence, lease_seconds=60)
            raise FenceRejected("SQL cancellation observed")

    monkeypatch.setattr(detached, "GeneratedRccExecution", BoundaryExecutor)
    with pytest.raises(FenceRejected):
        worker.execute(
            ticket, prepared=None, rcc=tmp_path / "never", execution_root=tmp_path
        )
    assert calls == ["prepared"]
    assert _one(c.db, Run, run.id).status == RunStatus.RUNNING


def test_recovery_receipt_does_not_erase_uncertain_launch(case):
    import json

    from actions.server.run_outputs.models import RunAttempt
    from actions.server.run_outputs.service import (
        RunOutputControlPlane,
        _canonical,
        _update,
    )

    c = case
    owner, service, caller = setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "uncertain")
    ticket = owner.claim(caller, run.id, service.snapshot.worker)
    record = json.loads(_one(c.db, Run, run.id).result)
    record["launch"] = {"uncertain": True}
    original = _canonical(record, 65536)
    with c.db.transaction():
        _update(c.db, Run, run.id, {"result": original})
        _update(c.db, RunAttempt, ticket.fence.attempt_id, {"lease_deadline_ms": "0"})
    RunOutputControlPlane(c.db).authorize_recovery(
        run.id, ticket.fence.epoch, receipt="explicit-receipt-is-not-reconciliation"
    )
    other = ManagedCaller(actor=caller.actor, worker_id=str(uuid4()))
    with pytest.raises(FenceRejected, match="reconciliation"):
        owner.claim(other, run.id, service.snapshot.worker)
    assert _one(c.db, Run, run.id).result == original
    assert _one(c.db, RunPin, run.id).epoch == ticket.fence.epoch


@pytest.mark.parametrize("claimed", [False, True])
def test_cancel_remains_authorized_after_execute_revocation(case, claimed):
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.run_outputs.models import RunAccessGrant
    from actions.server.run_outputs.service import _update

    c = case
    owner, service, caller = setup(c)
    run = owner.admit(
        caller.actor, service.snapshot, {"value": "hello"}, "cancel-without-execute"
    )
    from actions.server.run_outputs.types import Actor

    with pytest.raises(PermissionError):
        owner.cancel(Actor(principal_id=str(uuid4())), run.id)
    assert not _one(c.db, RunPin, run.id).cancel_requested
    if claimed:
        owner.claim(caller, run.id, service.snapshot.worker)
    with c.db.transaction():
        for grant in c.db.all(FoundryAccessGrant):
            _update(
                c.db,
                FoundryAccessGrant,
                grant.id,
                {"operations_json": '["cancel_execution"]'},
            )
        for grant in c.db.all(RunAccessGrant):
            _update(c.db, RunAccessGrant, grant.id, {"operations_json": '["cancel"]'})
    assert owner.cancel(caller.actor, run.id)
    assert _one(c.db, RunPin, run.id).cancel_requested
    assert _one(c.db, Run, run.id).status == (
        RunStatus.RUNNING if claimed else RunStatus.CANCELLED
    )
    with c.db.transaction():
        for grant in c.db.all(RunAccessGrant):
            _update(c.db, RunAccessGrant, grant.id, {"operations_json": "[]"})
    with pytest.raises(PermissionError):
        owner.cancel(caller.actor, run.id)


def test_scan_skips_revoked_without_disclosing_run_cursor(case, monkeypatch):
    from actions.server.run_outputs.service import AccessDenied

    c = case
    owner, service, caller = setup(c)
    first = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "denied")
    second = owner.admit(caller.actor, service.snapshot, {"value": "hello"}, "allowed")
    original = owner._service

    # Test a single retained revision becoming ineligible; a separate test
    # below revokes actual SQL references. Do not swallow integrity errors.
    calls = 0

    def selective(actor, snapshot):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise AccessDenied("revoked")
        return original(actor, snapshot)

    monkeypatch.setattr(owner, "_service", selective)
    page = owner.pending(
        caller.actor, service.snapshot.workspace_id, service.snapshot.worker, limit=1
    )
    assert page.run_ids == () and page.next_cursor not in (first.id, second.id)
    next_page = owner.pending(
        caller.actor,
        service.snapshot.workspace_id,
        service.snapshot.worker,
        limit=1,
        after=page.next_cursor,
    )
    assert next_page.run_ids == (second.id,)


@pytest.mark.parametrize("corruption", ["metadata", "queued-launch"])
def test_scan_actual_revoked_revision_preserves_valid_candidate_and_cursor(
    case, corruption
):
    import json

    from actions.server.foundry.authoring_values import CanvasBinding
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.foundry.sql_authorization import reference_grant_subject
    from actions.server.run_outputs.models import RunExecutionIntent
    from actions.server.run_outputs.service import _update

    c = case
    owner, service, caller = setup(c)
    denied = owner.admit(
        caller.actor, service.snapshot, {"value": "hello"}, "old-revision"
    )
    revised = c.authority.apply(
        c.actor,
        c.staged.ref.workspace_id,
        c.staged.application_id,
        c.staged.ref,
        json.dumps(dict(c.spec, title="New eligible revision")).encode(),
        (CanvasBinding("run", service.snapshot.capability),),
        c.staged.package_revisions,
        c.selection,
        c.staged.compilation,
        app_tests.fixtures.fingerprint("scan-revision"),
        idempotency_key="scan-revision",
    )
    c.authority.release(
        c.actor,
        c.staged.ref.workspace_id,
        c.staged.application_id,
        revised.ref,
        c.staged.ref,
        app_tests.fixtures.fingerprint("scan-release"),
        idempotency_key="scan-release",
    )
    app_tests.grant(
        c.db,
        c.actor,
        revised.ref.workspace_id,
        "reference",
        reference_grant_subject(revised.ref),
        ["execute"],
    )
    snapshot = c.deployments.resolve(
        caller.actor,
        revised.ref.workspace_id,
        revised.ref.deployment_id,
        service.snapshot.capability,
        revision=revised.ref,
        runtime_plan=service.snapshot.runtime_plan,
    ).snapshot
    valid = owner.admit(caller.actor, snapshot, {"value": "hello"}, "new-revision")
    with c.db.transaction():
        for grant in c.db.all(FoundryAccessGrant):
            if (
                grant.subject_kind == "reference"
                and grant.subject_id
                == reference_grant_subject(service.snapshot.deployment)
            ):
                _update(c.db, FoundryAccessGrant, grant.id, {"operations_json": "[]"})
    page = owner.pending(caller.actor, snapshot.workspace_id, snapshot.worker, limit=2)
    assert page.run_ids == (valid.id,) and denied.id not in page.next_cursor
    assert page.next_cursor == str(_one(c.db, Run, valid.id).numbered_id)
    with c.db.transaction():
        if corruption == "metadata":
            _update(c.db, RunExecutionIntent, denied.id, {"envelope_json": "{}"})
        else:
            _update(c.db, Run, denied.id, {"result": '{"launch":"uncertain"}'})
    with pytest.raises(FenceRejected):
        owner.pending(caller.actor, snapshot.workspace_id, snapshot.worker, limit=2)
    with pytest.raises(ValueError):
        owner.pending(
            caller.actor, snapshot.workspace_id, snapshot.worker, after=denied.id
        )


def test_run_once_cursor_does_not_skip_unconsumed_page_candidates(
    case, monkeypatch, tmp_path
):
    from actions.server.run_outputs.detached import DetachedActionWorker

    c = case
    owner, service, caller = setup(c)
    runs = [
        owner.admit(caller.actor, service.snapshot, {"value": "hello"}, f"page-{i}")
        for i in range(3)
    ]
    pending = owner.pending
    monkeypatch.setattr(
        owner,
        "pending",
        lambda *args, **kwargs: pending(*args, **dict(kwargs, limit=2)),
    )
    worker = DetachedActionWorker(
        owner, caller.actor, caller.worker_id, service.snapshot.worker
    )
    monkeypatch.setattr(
        worker, "execute", lambda ticket, **kwargs: _one(c.db, Run, ticket.fence.run_id)
    )
    first, cursor = worker.run_once(
        prepared=None, rcc=tmp_path / "unused", execution_root=tmp_path
    )
    second, _ = worker.run_once(
        prepared=None, rcc=tmp_path / "unused", execution_root=tmp_path, after=cursor
    )
    assert first.id == runs[0].id
    assert second.id == runs[1].id
