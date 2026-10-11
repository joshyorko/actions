"""Durable common Run ownership, grants and output publication."""

import json
import os
import sys
from uuid import uuid4

import pytest

from actions.server._models import Action, ActionPackage, Run, RunStatus, create_db
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor, ExecutionSnapshot

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux private output-provider proof"
)


def uid():
    return str(uuid4())


def snapshot(workspace=None):
    ws = workspace or uid()
    package = {
        "workspace_id": ws,
        "package_id": uid(),
        "revision_id": "sha256:" + "1" * 64,
    }
    return ExecutionSnapshot.model_validate(
        {
            "deployment": {
                "workspace_id": ws,
                "deployment_id": uid(),
                "revision_id": "sha256:" + "2" * 64,
            },
            "capability": {"package_revision": package, "capability_id": "query"},
            "runtime_plan": {
                "package_revision": package,
                "plan_digest": "sha256:" + "3" * 64,
            },
            "worker": {
                "workspace_id": ws,
                "worker_profile_id": uid(),
                "revision_id": "sha256:" + "4" * 64,
            },
            "policy": {
                "workspace_id": ws,
                "policy_id": uid(),
                "revision_id": "sha256:" + "5" * 64,
            },
            "output_provider": {
                "workspace_id": ws,
                "provider_profile_id": uid(),
                "revision_id": "sha256:" + "6" * 64,
            },
            "runtime_kind": "test/no-external-effects",
            "capability_schema_digest": "sha256:" + "7" * 64,
            "action_id": "test-action",
        }
    )


def insert_action(db, snap):
    package_id = str(snap.capability.package_revision.package_id.root)
    with db.transaction():
        db.insert(
            ActionPackage(
                package_id,
                "package-" + package_id,
                "trusted-test-source",
                "unused",
                "{}",
            )
        )
        db.insert(
            Action(
                snap.action_id,
                package_id,
                snap.capability.capability_id.root,
                "trusted test",
                "action.py",
                1,
                '{"type":"object","properties":{"query":{"type":"string"}}}',
                "{}",
            )
        )


@pytest.fixture
def store(tmp_path):
    root = tmp_path / "objects"
    root.mkdir()
    fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        with create_db(tmp_path / "runs.db") as db:
            with FilesystemOutputProvider(fd) as provider:
                control = RunOutputControlPlane(db)
                snap = snapshot()
                actor = Actor(principal_id=uid())
                insert_action(db, snap)
                control.register(snap)
                control.grant(actor, snap.deployment, {"execute", "read", "cancel"})
                service = RunOutputService(db, {snap.provider_key: provider})
                yield db, control, service, snap, actor, provider, root
    finally:
        os.close(fd)


def publish(store, *, key="one", body=b"result"):
    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {"query": "alpha"}, key)
    fence = service.claim(run.id, uid(), lease_seconds=30)
    output = service.stage(
        fence,
        [body],
        name="result.txt",
        media_type="text/plain",
        retention_seconds=3600,
    )
    service.publish(
        actor,
        fence,
        [output],
        {"rows": ["alpha"], "artifact": {"handle": output.handle}},
    )
    return run, fence, output


def test_authorized_handle_round_trip_and_existing_run_authority(store):
    db, control, service, snap, actor, provider, root = store
    run, fence, output = publish(store)
    stored = db.first(Run, "SELECT * FROM run WHERE id=?", [run.id])
    assert stored.status == RunStatus.PASSED
    assert json.loads(stored.result)["result"]["artifact"]["handle"] == output.handle
    assert output.handle.startswith("art_") and len(output.handle) == 26
    with service.resolve(actor, snap.workspace_id, output.handle) as resolved:
        assert resolved.run_id == run.id
        assert resolved.read() == b"result"
    # A fresh service uses only durable rows and the configured provider.
    second = RunOutputService(db, {snap.provider_key: provider})
    with second.resolve(actor, snap.workspace_id, output.handle) as resolved:
        assert resolved.read() == b"result"


def test_revocation_and_other_workspace_deny_before_provider_access(store, monkeypatch):
    db, control, service, snap, actor, provider, root = store
    run, fence, output = publish(store)

    def forbidden(*args, **kwargs):
        pytest.fail("unauthorized resolver reached provider")

    monkeypatch.setattr(provider, "open", forbidden)
    with pytest.raises(AccessDenied):
        with service.resolve(
            Actor(principal_id=uid()), snap.workspace_id, output.handle
        ):
            pass
    with pytest.raises(AccessDenied):
        with service.resolve(actor, uid(), output.handle):
            pass
    control.revoke(actor, snap.deployment)
    with pytest.raises(AccessDenied):
        with service.resolve(actor, snap.workspace_id, output.handle):
            pass


def test_idempotency_reauthorizes_and_rejects_changed_inputs(store):
    db, control, service, snap, actor, provider, root = store
    first = service.admit(actor, snap, {"query": "alpha"}, "key")
    assert service.admit(actor, snap, {"query": "alpha"}, "key").id == first.id
    with pytest.raises(ValueError, match="idempotency"):
        service.admit(actor, snap, {"query": "beta"}, "key")
    control.revoke(actor, snap.deployment)
    with pytest.raises(AccessDenied):
        service.admit(actor, snap, {"query": "alpha"}, "key")


def test_unregistered_snapshot_is_not_authority(store):
    db, control, service, snap, actor, provider, root = store
    altered = snap.model_copy(update={"action_id": "unregistered"})
    with pytest.raises(AccessDenied):
        service.admit(actor, altered, {}, "unknown")


def test_stale_expired_owner_cannot_stage_heartbeat_or_publish(store):
    from actions.server.run_outputs.models import RunAttempt

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    old = service.claim(run.id, uid(), lease_seconds=30)
    output = service.stage(
        old, [b"old"], name="old", media_type="text/plain", retention_seconds=30
    )
    with db.transaction():
        db.update_by_id(RunAttempt, old.attempt_id, {"lease_deadline_ms": "0"})
    with pytest.raises(FenceRejected):
        service.heartbeat(old, lease_seconds=30)
    # No external-effect retry is inferred: reclaim requires explicit safe recovery.
    with pytest.raises(FenceRejected):
        service.claim(run.id, uid(), lease_seconds=30)
    control.authorize_recovery(
        run.id, old.epoch, receipt="trusted fixture: no external effects"
    )
    new = service.claim(run.id, uid(), lease_seconds=30)
    assert new.epoch == old.epoch + 1
    with pytest.raises(FenceRejected):
        service.stage(
            old, [b"bad"], name="old", media_type="text/plain", retention_seconds=30
        )
    with pytest.raises(FenceRejected):
        service.publish(actor, old, [output], {})
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result is None


def test_cancel_wins_before_publish_and_provisional_not_readable(store):
    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    output = service.stage(
        fence, [b"body"], name="body", media_type="text/plain", retention_seconds=30
    )
    with pytest.raises(AccessDenied):
        with service.resolve(actor, snap.workspace_id, output.handle):
            pass
    assert service.cancel(actor, run.id)
    with pytest.raises(FenceRejected):
        service.publish(actor, fence, [output], {})
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result is None


def test_success_wins_cancel_and_replay_must_be_exact(store):
    db, control, service, snap, actor, provider, root = store
    run, fence, output = publish(store)
    result = {"rows": ["alpha"], "artifact": {"handle": output.handle}}
    assert service.publish(actor, fence, [output], result).id == run.id
    with pytest.raises(FenceRejected):
        service.publish(actor, fence, [output], {"changed": True})
    assert not service.cancel(actor, run.id)


def test_finalize_failure_rolls_back_run_and_output(store, monkeypatch):
    from actions.server.run_outputs.models import RunOutput

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    output = service.stage(
        fence, [b"body"], name="body", media_type="text/plain", retention_seconds=30
    )
    original = db.update_by_id

    def injected(cls, *args, **kwargs):
        if cls is RunOutput:
            raise RuntimeError("injected output transition")
        return original(cls, *args, **kwargs)

    monkeypatch.setattr(db, "update_by_id", injected)
    with pytest.raises(RuntimeError, match="injected"):
        service.publish(actor, fence, [output], {})
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result is None
    assert (
        db.first(
            RunOutput, "SELECT * FROM run_output WHERE id=?", [output.output_id]
        ).state
        == "provisional"
    )


def test_expired_output_and_unmapped_provider_fail_closed(store):
    from actions.server.run_outputs.models import RunOutput

    db, control, service, snap, actor, provider, root = store
    run, fence, output = publish(store)
    with pytest.raises(AccessDenied):
        with RunOutputService(db, {}).resolve(actor, snap.workspace_id, output.handle):
            pass
    with db.transaction():
        db.update_by_id(RunOutput, output.output_id, {"expires_ms": "0"})
    with pytest.raises(AccessDenied):
        with service.resolve(actor, snap.workspace_id, output.handle):
            pass


def test_legacy_helper_cannot_change_scoped_run_and_keeps_legacy_behavior(
    store, monkeypatch
):
    import time
    from dataclasses import replace
    from types import SimpleNamespace

    from actions.server import _runs_state_cache, _settings
    from actions.server._actions_run import _update_run

    db, control, service, snap, actor, provider, root = store
    scoped = service.admit(actor, snap, {}, "key")
    events = []
    monkeypatch.setattr(
        _settings, "get_settings", lambda: SimpleNamespace(base_url="http://local")
    )
    monkeypatch.setattr(
        _runs_state_cache,
        "get_global_runs_state",
        lambda: SimpleNamespace(on_run_changed=lambda *args: events.append(args)),
    )
    with pytest.raises(FenceRejected):
        _update_run(
            scoped, time.monotonic(), True, status=RunStatus.PASSED, result="unfenced"
        )
    assert scoped.status == RunStatus.NOT_RUN and scoped.result is None and not events
    legacy = replace(scoped, id=uid(), numbered_id=scoped.numbered_id + 1)
    with db.transaction():
        db.insert(legacy)
    _update_run(
        legacy, time.monotonic(), True, status=RunStatus.PASSED, result="legacy"
    )
    assert legacy.status == RunStatus.PASSED
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [legacy.id]).result == "legacy"
    assert len(events) == 1


def test_provider_mutation_and_oversize_stage_leave_no_final_output(store, monkeypatch):
    from actions.server.run_outputs import filesystem
    from actions.server.run_outputs.models import RunOutput

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    monkeypatch.setattr(filesystem, "MAX_OUTPUT_BYTES", 3)
    with pytest.raises(ValueError, match="bound"):
        service.stage(
            fence,
            [b"four"],
            name="output",
            media_type="text/plain",
            retention_seconds=30,
        )
    assert not list(root.iterdir())
    assert {row.state for row in db.all(RunOutput)} == {"aborted"}
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result is None


def test_all_legacy_read_and_event_seams_isolate_scoped_runs(store, monkeypatch):
    from dataclasses import replace

    from fastapi import HTTPException

    from actions.server import _artifact_storage
    from actions.server._api_run import get_run_by_id
    from actions.server._runs_state_cache import use_runs_state_ctx

    db, control, service, snap, actor, provider, root = store
    scoped, fence, output = publish(store)
    scoped = db.first(Run, "SELECT * FROM run WHERE id=?", [scoped.id])
    legacy = replace(
        scoped,
        id=uid(),
        numbered_id=scoped.numbered_id + 1,
        request_id="legacy-request",
    )
    with db.transaction():
        db.insert(legacy)
        db.update_by_id(Run, scoped.id, {"request_id": "scoped-request"})
    events = []
    with use_runs_state_ctx(db) as state:
        with state.semaphore:
            assert [r.id for r in state.get_current_run_state()] == [legacy.id]
            assert [
                r.id for r in state.get_current_run_summaries(run_type="action")
            ] == [legacy.id]
            assert state.get_run_from_request_id("legacy-request").id == legacy.id
            assert state.get_run_from_id(legacy.id).id == legacy.id
            with pytest.raises(KeyError):
                state.get_run_from_id(scoped.id)
            with pytest.raises(KeyError):
                state.get_run_from_request_id("scoped-request")
            state.register(events.append)
        state.on_run_inserted(scoped)
        state.on_run_changed(scoped, {"result": "secret"})
        assert not events and not state.cancel_run(scoped.id)
        with pytest.raises(PermissionError):
            state.create_run_runtime_info(scoped.id)
        state.on_run_inserted(legacy)
        assert len(events) == 1
        monkeypatch.setattr(
            _artifact_storage,
            "get_artifact_storage",
            lambda: pytest.fail("scoped ID reached legacy provider"),
        )
        with pytest.raises(HTTPException) as failure:
            get_run_by_id(scoped.id)
        assert failure.value.status_code == 404
        assert get_run_by_id(legacy.id).id == legacy.id


def test_registered_snapshot_cannot_be_changed_under_same_revision(store):
    db, control, service, snap, actor, provider, root = store
    changed = snap.model_copy(update={"runtime_kind": "changed"})
    with pytest.raises(ValueError, match="immutable"):
        control.register(changed)


def test_lease_expiry_at_final_statement_rolls_back_attachment(store, monkeypatch):
    from actions.server.run_outputs import service as module
    from actions.server.run_outputs.models import RunAttempt, RunOutput

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    output = service.stage(
        fence, [b"body"], name="body", media_type="text/plain", retention_seconds=30
    )
    original = module._returning

    def expire(db, sql, values):
        if sql.startswith("UPDATE run SET status=?, result=?"):
            db.update_by_id(RunAttempt, fence.attempt_id, {"lease_deadline_ms": "0"})
        return original(db, sql, values)

    monkeypatch.setattr(module, "_returning", expire)
    with pytest.raises(FenceRejected, match="expired"):
        service.publish(actor, fence, [output], {})
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result is None
    assert (
        db.first(
            RunOutput, "SELECT * FROM run_output WHERE id=?", [output.output_id]
        ).state
        == "provisional"
    )


def test_nondurable_sqlite_commit_preserves_authoritative_run_and_outputs(
    store, monkeypatch, caplog
):
    import sqlite3
    import traceback

    from actions.server._database import Database
    from actions.server._models import get_all_model_classes
    from actions.server.run_outputs.models import RunOutput

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    output = service.stage(
        fence, [b"body"], name="body", media_type="text/plain", retention_seconds=30
    )

    class CommitFailure(RuntimeError):
        pass

    class FailedConnection(sqlite3.Connection):
        def commit(self):
            raise CommitFailure("nondurable commit")

    original = sqlite3.connect

    def connect(*args, **kwargs):
        return original(*args, **kwargs, factory=FailedConnection)

    monkeypatch.setattr(sqlite3, "connect", connect)
    failed = Database(db.db_path)
    with failed.connect():
        failed.initialize(get_all_model_classes())
        secret = "private-commit-" + uid()
        with pytest.raises(CommitFailure, match="nondurable") as failure:
            RunOutputService(failed, {snap.provider_key: provider}).publish(
                actor, fence, [output], {"private": secret}
            )
        assert secret not in caplog.text
        assert secret not in "".join(traceback.format_exception(failure.value))
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result is None
    assert (
        db.first(
            RunOutput, "SELECT * FROM run_output WHERE id=?", [output.output_id]
        ).state
        == "provisional"
    )
    assert (
        root
        / db.first(
            RunOutput, "SELECT * FROM run_output WHERE id=?", [output.output_id]
        ).object_ref
    ).exists()


def test_legacy_analytics_excludes_scoped_counts_status_and_action_identity(store):
    from dataclasses import replace

    from actions.server._api_analytics import (
        get_analytics_summary,
        get_runs_by_action,
        get_runs_by_day,
    )

    db, control, service, snap, actor, provider, root = store
    scoped, fence, output = publish(store)
    assert get_analytics_summary().total_runs == 0
    assert get_runs_by_day() == [] and get_runs_by_action() == []
    legacy = replace(scoped, id=uid(), numbered_id=scoped.numbered_id + 1)
    with db.transaction():
        db.insert(legacy)
    assert get_analytics_summary().total_runs == 1
    assert sum(day.total for day in get_runs_by_day()) == 1
    assert sum(action.total for action in get_runs_by_action()) == 1


def test_control_plane_registration_cannot_choose_unknown_or_foreign_action(store):
    db, control, service, snap, actor, provider, root = store
    with pytest.raises(AccessDenied, match="identity|unavailable"):
        control.register(snap.model_copy(update={"action_id": "unknown"}))
    with db.transaction():
        db.update_by_id(Action, snap.action_id, {"name": "other-capability"})
    with pytest.raises(AccessDenied, match="identity"):
        service.admit(actor, snap, {}, "new")


def test_admit_validates_actual_action_input_schema(store):
    from jsonschema import ValidationError

    db, control, service, snap, actor, provider, root = store
    with pytest.raises(ValidationError):
        service.admit(actor, snap, {"query": 99}, "invalid")


def test_stage_rechecks_grant_and_count_bound_before_provider(store, monkeypatch):
    from actions.server.run_outputs import service as module

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    service.stage(
        fence, [b"first"], name="first", media_type="text/plain", retention_seconds=30
    )
    monkeypatch.setattr(
        provider, "stage", lambda *args: pytest.fail("denied stage reached provider")
    )
    monkeypatch.setattr(module, "MAX_OUTPUTS", 1)
    with pytest.raises(ValueError, match="count bound"):
        service.stage(
            fence,
            [b"second"],
            name="second",
            media_type="text/plain",
            retention_seconds=30,
        )
    control.revoke(actor, snap.deployment)
    with pytest.raises(AccessDenied):
        service.stage(
            fence,
            [b"second"],
            name="second",
            media_type="text/plain",
            retention_seconds=30,
        )


def test_idempotency_digest_collision_does_not_merge_different_keys(store, monkeypatch):
    from actions.server.run_outputs import service as module

    db, control, service, snap, actor, provider, root = store
    original = module._key

    def collide(domain, *parts):
        if domain == "actions.workspace-run-idempotency/v1":
            return "0" * 64
        return original(domain, *parts)

    monkeypatch.setattr(module, "_key", collide)
    service.admit(actor, snap, {}, "first")
    with pytest.raises(ValueError, match="idempotency"):
        service.admit(actor, snap, {}, "second")


def test_sql_body_error_is_redacted_before_database_rollback_logging(
    store, monkeypatch, caplog
):
    import traceback

    from actions.server._database import DBError

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    output = service.stage(
        fence, [b"body"], name="body", media_type="text/plain", retention_seconds=30
    )
    secret = "private-" + uid()
    original = db.execute_update_returning

    def injected(cursor, sql, values=None):
        if sql.startswith("UPDATE run SET status=?, result=?"):
            raise DBError("backend failed with bound values " + repr(values))
        return original(cursor, sql, values)

    monkeypatch.setattr(db, "execute_update_returning", injected)
    result = {"private": secret}
    with pytest.raises(DBError, match="redacted") as failure:
        service.publish(actor, fence, [output], result)
    assert secret not in caplog.text
    assert secret not in "".join(traceback.format_exception(failure.value))
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result is None


def test_mutable_verbose_diagnostics_are_rejected_without_disabling_them(store):
    db, control, service, snap, actor, provider, root = store
    db.verbose = True
    try:
        with pytest.raises(ValueError, match="diagnostics"):
            RunOutputService(db, {})
        with pytest.raises(ValueError, match="diagnostics"):
            RunOutputControlPlane(db)
        with pytest.raises(ValueError, match="diagnostics"):
            service.admit(actor, snap, {}, "key")
        assert db.verbose
    finally:
        db.verbose = False


def test_registration_and_numbered_admission_take_installation_lock_before_workspace(
    store, monkeypatch
):
    from actions.server.run_outputs import service as module

    db, control, service, snap, actor, provider, root = store
    observed = []
    original = module._returning

    def record(db, sql, values):
        if sql.startswith("UPDATE counter"):
            observed.append("counter")
        elif sql.startswith("UPDATE workspace"):
            observed.append("workspace")
        return original(db, sql, values)

    monkeypatch.setattr(module, "_returning", record)
    control.register(snap)
    assert observed[:2] == ["counter", "workspace"]
    observed.clear()
    service.admit(actor, snap, {}, "key")
    assert observed[:2] == ["counter", "workspace"]


def test_cancel_during_actual_stage_retains_abort_receipt_and_discards_owned_seal(
    store,
):
    from actions.server.run_outputs.models import RunOutput

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)

    def chunks():
        yield b"cancelled body"
        assert service.cancel(actor, run.id)

    with pytest.raises(FenceRejected):
        service.stage(
            fence, chunks(), name="body", media_type="text/plain", retention_seconds=30
        )
    output = db.first(RunOutput)
    assert output.state == "aborted"
    assert output.object_ref and output.digest and output.size == len(b"cancelled body")
    assert not list(root.iterdir())
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result is None


def test_seal_transaction_failure_retains_abort_receipt_before_discard(
    store, monkeypatch
):
    from actions.server.run_outputs.models import RunOutput

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    original = db.update_by_id

    def fail_seal(cls, key, changes):
        original(cls, key, changes)
        if cls is RunOutput and "object_ref" in changes and "state" not in changes:
            raise RuntimeError("seal transaction failed")

    monkeypatch.setattr(db, "update_by_id", fail_seal)
    with pytest.raises(RuntimeError, match="seal transaction failed"):
        service.stage(
            fence, [b"body"], name="body", media_type="text/plain", retention_seconds=30
        )
    output = db.first(RunOutput)
    assert (
        output.state == "aborted"
        and output.object_ref
        and output.digest
        and output.size == 4
    )
    assert not list(root.iterdir())
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result is None


def test_discard_failure_preserves_original_fence_error_and_durable_receipt(
    store, monkeypatch, caplog
):
    from actions.server.run_outputs.models import RunOutput

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)

    def fail(staged):
        raise OSError("discard unavailable")

    monkeypatch.setattr(provider, "discard", fail)

    def chunks():
        yield b"body"
        service.cancel(actor, run.id)

    with pytest.raises(FenceRejected) as failure:
        service.stage(
            fence, chunks(), name="body", media_type="text/plain", retention_seconds=30
        )
    output = db.first(RunOutput)
    assert (
        output.state == "aborted"
        and output.object_ref
        and output.digest
        and output.size == 4
    )
    assert (root / output.object_ref).exists()
    assert "discard failed" in " ".join(failure.value.__notes__)
    assert "discard failed" in caplog.text
    from actions.server.run_outputs.types import OutputRef

    ref = OutputRef(
        workspace_id=output.workspace_id, run_id=run.id, output_id=output.id
    )
    with pytest.raises(AccessDenied):
        with service.resolve(actor, snap.workspace_id, ref.handle):
            pytest.fail("aborted receipt became a published output")


def test_ambiguous_seal_and_abort_commits_do_not_discard_even_with_durable_abort(
    store, monkeypatch
):
    import sqlite3

    from actions.server._database import Database
    from actions.server._models import get_all_model_classes
    from actions.server.run_outputs.models import RunOutput

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)

    class CommitFailure(RuntimeError):
        pass

    calls = []

    class AmbiguousConnection(sqlite3.Connection):
        def commit(self):
            super().commit()
            calls.append(len(calls) + 1)
            if len(calls) in (2, 3):
                raise CommitFailure(
                    "seal commit ambiguous"
                    if len(calls) == 2
                    else "abort commit ambiguous"
                )

    original = sqlite3.connect
    monkeypatch.setattr(
        sqlite3,
        "connect",
        lambda *args, **kwargs: original(*args, **kwargs, factory=AmbiguousConnection),
    )
    monkeypatch.setattr(
        provider,
        "discard",
        lambda staged: pytest.fail("uncertain commit caused discard"),
    )
    failed = Database(db.db_path)
    with failed.connect():
        failed.initialize(get_all_model_classes())
        with pytest.raises(CommitFailure, match="seal commit ambiguous") as failure:
            RunOutputService(failed, {snap.provider_key: provider}).stage(
                fence,
                [b"body"],
                name="body",
                media_type="text/plain",
                retention_seconds=30,
            )
    output = db.first(RunOutput)
    assert calls == [1, 2, 3]
    assert (
        output.state == "aborted"
        and output.object_ref
        and output.digest
        and output.size == 4
    )
    assert (root / output.object_ref).exists()
    assert "uncertain" in " ".join(failure.value.__notes__)


def test_successfully_published_output_survives_stage_commit_exception_and_replay(
    store, monkeypatch
):
    import sqlite3

    from actions.server._database import Database
    from actions.server._models import get_all_model_classes
    from actions.server.run_outputs.models import RunOutput
    from actions.server.run_outputs.types import OutputRef

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    published = []
    calls = []

    class StageFailure(RuntimeError):
        pass

    class PublishedConnection(sqlite3.Connection):
        def commit(self):
            super().commit()
            calls.append(len(calls) + 1)
            if len(calls) == 2:
                row = db.first(RunOutput)
                ref = OutputRef(
                    workspace_id=row.workspace_id, run_id=row.run_id, output_id=row.id
                )
                service.publish(actor, fence, [ref], {"winner": "durable"})
                published.append(ref)
                raise StageFailure("stage commit observer failed")

    original = sqlite3.connect
    monkeypatch.setattr(
        sqlite3,
        "connect",
        lambda *args, **kwargs: original(*args, **kwargs, factory=PublishedConnection),
    )
    monkeypatch.setattr(
        provider,
        "discard",
        lambda staged: pytest.fail("published output was discarded"),
    )
    failed = Database(db.db_path)
    with failed.connect():
        failed.initialize(get_all_model_classes())
        with pytest.raises(StageFailure, match="observer failed"):
            RunOutputService(failed, {snap.provider_key: provider}).stage(
                fence,
                [b"body"],
                name="body",
                media_type="text/plain",
                retention_seconds=30,
            )
    output = db.first(RunOutput)
    assert output.state == "final" and (root / output.object_ref).exists()
    assert (
        db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).status
        == RunStatus.PASSED
    )
    service.publish(actor, fence, published, {"winner": "durable"})
    with pytest.raises(FenceRejected):
        service.publish(actor, fence, published, {"winner": "changed"})
    with service.resolve(actor, snap.workspace_id, published[0].handle) as resolved:
        assert resolved.read() == b"body"


def test_abort_receipt_does_not_discard_object_referenced_by_another_record(
    store, monkeypatch
):
    from dataclasses import replace

    from actions.server.run_outputs.models import RunOutput

    db, control, service, snap, actor, provider, root = store
    run = service.admit(actor, snap, {}, "key")
    fence = service.claim(run.id, uid(), lease_seconds=30)
    original = provider.stage
    original_ids = []

    def referenced(chunks):
        staged = original(chunks)
        row = db.first(RunOutput)
        original_ids.append(row.id)
        duplicate = replace(row, id=uid(), **staged.receipt.model_dump())
        with db.transaction():
            db.insert(duplicate)
        service.cancel(actor, run.id)
        return staged

    monkeypatch.setattr(provider, "stage", referenced)
    monkeypatch.setattr(
        provider,
        "discard",
        lambda staged: pytest.fail("referenced object was discarded"),
    )
    with pytest.raises(FenceRejected) as failure:
        service.stage(
            fence, [b"body"], name="body", media_type="text/plain", retention_seconds=30
        )
    row = db.first(RunOutput, "SELECT * FROM run_output WHERE id=?", original_ids)
    assert row.state == "aborted" and row.object_ref and row.digest and row.size == 4
    assert (root / row.object_ref).exists()
    assert "not proven safe" in " ".join(failure.value.__notes__)
