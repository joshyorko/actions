"""Synthetic offline owner authorization; no RCC, network, or production grants."""
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs

from actions.server._local_authorization import (
    LocalAuthorizationRequest,
    apply_local_authorization,
    run_local_authorization,
)
from actions.server._models import create_db, load_db
from actions.server.foundry.bootstrap import _realm
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.foundry.runtime_profile import RuntimeExecutionProfile
from actions.server.run_outputs.models import RunAdmission


def private_write(path, value):
    path.write_text(value)
    path.chmod(0o600)


@pytest.fixture
def local(tmp_path):
    root = tmp_path / "owner"
    root.mkdir(mode=0o700)
    with create_db(root / "server.db") as db:
        actor, workspace = _realm(db)
    (root / "server.db").chmod(0o600)
    refs = _refs()
    profile = RuntimeExecutionProfile(
        schema_version="actions.runtime-rcc-profile/v1",
        admission="trusted-developer-execution",
        prepared_receipt="/tmp/synthetic-not-read.json",
        worker_id=str(uuid4()),
        worker=refs.worker.model_copy(update={"workspace_id": workspace}),
        policy=refs.policy.model_copy(update={"workspace_id": workspace}),
        output_provider=refs.output_provider.model_copy(
            update={"workspace_id": workspace}
        ),
    )
    profile_path = root / "profile.json"
    private_write(profile_path, profile.model_dump_json())
    request = LocalAuthorizationRequest(
        schema_version="actions.local-authorization/v1",
        operation="authorize-generated-source",
        target="generated-source",
        request_id="source-1",
        workspace_id=workspace,
        runtime_profile=str(profile_path),
    )
    request_path = root / "request.json"
    private_write(request_path, request.model_dump_json())
    return SimpleNamespace(
        root=root,
        actor=actor,
        workspace=workspace,
        profile=profile,
        request=request,
        request_path=request_path,
    )


def inspect(case):
    return run_local_authorization(str(case.root), str(case.request_path), dry_run=True)


def apply(case, request=None):
    if request:
        private_write(case.request_path, request.model_dump_json())
    receipt = inspect(case)
    current = LocalAuthorizationRequest.model_validate_json(
        case.request_path.read_bytes()
    )
    private_write(
        case.request_path,
        current.model_copy(
            update={"expected_grants_digest": receipt["expected_grants_digest"]}
        ).model_dump_json(),
    )
    return run_local_authorization(str(case.root), str(case.request_path))


def test_source_dry_run_apply_replay_revoke_preserves_unrelated(local):
    with load_db(local.root / "server.db") as db:
        before = db.all(FoundryAccessGrant)
    preview = inspect(local)
    assert preview["dryRun"] and preview["owner"] == local.actor.principal_id
    with load_db(local.root / "server.db") as db:
        assert db.all(FoundryAccessGrant) == before
        assert not db.all(RunAdmission)
    receipt = apply(local)
    assert not receipt["dryRun"]
    replay = run_local_authorization(str(local.root), str(local.request_path))
    assert replay["replay"]
    with load_db(local.root / "server.db") as db:
        assert len(db.all(FoundryAccessGrant)) == len(before) + 4
        assert (
            len(
                db.all(
                    FoundryRequest,
                    where="operation=?",
                    values=["runtime.local-authorization"],
                )
            )
            == 1
        )
    revoke = local.request.model_copy(
        update={"operation": "revoke", "request_id": "source-revoke"}
    )
    apply(local, revoke)
    with load_db(local.root / "server.db") as db:
        rows = db.all(FoundryAccessGrant)
        assert all(row in rows for row in before)
        assert all(
            json.loads(row.operations_json) == [] for row in rows if row not in before
        )
    # Historical replay never restores revoked permissions.
    private_write(
        local.request_path,
        local.request.model_copy(
            update={"expected_grants_digest": preview["expected_grants_digest"]}
        ).model_dump_json(),
    )
    assert run_local_authorization(str(local.root), str(local.request_path))["replay"]


def test_missing_or_stale_cas_fails_without_mutation(local):
    with pytest.raises(ValueError, match="state changed"):
        run_local_authorization(str(local.root), str(local.request_path))
    digest = inspect(local)["expected_grants_digest"]
    apply(local)
    private_write(
        local.request_path,
        local.request.model_copy(
            update={"request_id": "different", "expected_grants_digest": digest}
        ).model_dump_json(),
    )
    with pytest.raises(ValueError, match="state changed"):
        run_local_authorization(str(local.root), str(local.request_path))


@pytest.mark.parametrize(
    "kind",
    [
        "symlink",
        "permissions",
        "missing",
        "sidecar",
        "external",
        "profile-workspace",
        "owner-audit",
    ],
)
def test_offline_boundary_rejections(local, monkeypatch, kind):
    if kind == "symlink":
        target = local.root / "real.db"
        (local.root / "server.db").rename(target)
        (local.root / "server.db").symlink_to(target)
    elif kind == "permissions":
        local.root.chmod(0o755)
    elif kind == "missing":
        (local.root / "server.db").unlink()
    elif kind == "sidecar":
        private_write(local.root / "server.db-wal", "synthetic")
    elif kind == "external":
        monkeypatch.setenv(
            "ACTION_SERVER_DATABASE_URL", "postgresql://synthetic.invalid/db"
        )
    elif kind == "profile-workspace":
        changed = local.profile.model_copy(update={"worker": _refs().worker})
        private_write(Path(local.request.runtime_profile), changed.model_dump_json())
    else:
        with load_db(local.root / "server.db") as db, db.transaction():
            db.execute("DELETE FROM foundry_audit")
    with pytest.raises((ValueError, OSError)):
        inspect(local)


def test_no_arbitrary_recipient_or_permission(local):
    raw = local.request.model_dump(mode="json")
    raw["principal_id"] = str(uuid4())
    with pytest.raises(ValueError):
        LocalAuthorizationRequest.model_validate_json(json.dumps(raw))
    raw.pop("principal_id")
    raw["queue_permissions"] = ["work_items.retry"]
    with pytest.raises(ValueError):
        LocalAuthorizationRequest.model_validate_json(json.dumps(raw))


def test_canonical_mutex_refuses_running_runtime(local):
    from actions.server._common.app_mutex import obtain_app_mutex

    mutex = obtain_app_mutex(
        data_dir=local.root,
        lock_basename="action_server.lock",
        app_name="synthetic",
        timeout=0,
    )
    try:
        with pytest.raises(ValueError, match="Runtime is running"):
            inspect(local)
    finally:
        mutex.release_mutex()


def test_cli_schema_never_requires_rcc_or_state(capsys):
    from actions.server._cli_impl import _main_retcode

    assert _main_retcode(["authorize-local", "--schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["additionalProperties"] is False
    assert "principal_id" not in schema["properties"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    """This offline-only lane must not initialize or invoke RCC."""
    yield


pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def deployed(tmp_path, foundry_package_store):
    import hashlib

    from action_server_tests import test_generic_work_item_execution as fixtures

    from actions.server.foundry.bootstrap import _OWNER_OPERATIONS, _ROOT_REQUEST

    context = fixtures.generic.__wrapped__(
        tmp_path / "native.db", foundry_package_store
    )
    setup = next(context)
    try:
        g = setup("optional")
        snapshot = g.owner.snapshot
        workspace = snapshot.workspace_id
        actor = g.caller.actor
        with g.db.transaction():
            g.db.insert(
                FoundryRequest(
                    _ROOT_REQUEST,
                    workspace,
                    actor.principal_id,
                    "runtime.bootstrap",
                    "runtime-bootstrap/v1",
                    "sha256:"
                    + hashlib.sha256(
                        json.dumps(_OWNER_OPERATIONS).encode()
                    ).hexdigest(),
                    json.dumps(
                        {"workspace_id": workspace, "principal_id": actor.principal_id}
                    ),
                )
            )
            g.db.insert(
                FoundryAudit(
                    str(uuid4()),
                    workspace,
                    "",
                    actor.principal_id,
                    "runtime.bootstrap",
                    _ROOT_REQUEST,
                    "",
                    "",
                    "1",
                )
            )
            g.db.execute("DELETE FROM run_access_grant")
        g.profile = RuntimeExecutionProfile(
            schema_version="actions.runtime-rcc-profile/v1",
            admission="trusted-developer-execution",
            prepared_receipt="/tmp/not-read.json",
            worker_id=g.caller.worker_id,
            worker=snapshot.worker,
            policy=snapshot.policy,
            output_provider=snapshot.output_provider,
        )
        g.request = LocalAuthorizationRequest(
            schema_version="actions.local-authorization/v1",
            operation="authorize-exact-deployment",
            target="deployment",
            request_id="deployment-one",
            workspace_id=snapshot.deployment.workspace_id,
            runtime_profile="/tmp/synthetic-profile.json",
            deployment=snapshot.deployment,
            run_permissions=("execute", "read"),
            queue_permissions=("work_items.read", "work_items.claim"),
        )
        yield g
    finally:
        try:
            next(context)
        except StopIteration:
            pass


def native_apply(g, request=None):
    request = request or g.request
    preview = apply_local_authorization(
        g.db, request, g.profile, g.owner.registry, dry_run=True
    )
    request = request.model_copy(
        update={"expected_grants_digest": preview["expected_grants_digest"]}
    )
    return apply_local_authorization(
        g.db, request, g.profile, g.owner.registry, dry_run=False
    )


def test_deployment_named_scopes_revoke_preserves_other_grants(deployed):
    from actions.server.run_outputs.models import RunAccessGrant

    g = deployed
    original = g.db.all(FoundryAccessGrant)
    admissions = g.db.all(RunAdmission)
    receipt = native_apply(g)
    assert (
        "application ID" in receipt["runScope"]
        and "all queues" in receipt["queueScope"]
    )
    assert g.db.all(RunAdmission) == admissions
    assert set(json.loads(g.db.all(RunAccessGrant)[0].operations_json)) == {
        "execute",
        "read",
    }
    revoke = g.request.model_copy(
        update={
            "operation": "revoke",
            "request_id": "revoke-read",
            "run_permissions": ("read",),
            "queue_permissions": ("work_items.claim",),
        }
    )
    native_apply(g, revoke)
    assert json.loads(g.db.all(RunAccessGrant)[0].operations_json) == ["execute"]
    assert all(row in g.db.all(FoundryAccessGrant) for row in original)


@pytest.mark.parametrize("change", ["revision", "profile", "package"])
def test_deployment_exact_target_validation(deployed, change):
    g = deployed
    request = g.request
    if change == "revision":
        from actions.server.deployments.ids import DeploymentRevisionId

        request = request.model_copy(
            update={
                "deployment": request.deployment.model_copy(
                    update={"revision_id": DeploymentRevisionId("sha256:" + "e" * 64)}
                )
            }
        )
    elif change == "profile":
        g.profile = g.profile.model_copy(update={"worker": _refs().worker})
    else:
        with g.db.transaction():
            g.db.execute("UPDATE foundry_package_revision SET manifest_json='{}'")
    before = g.db.all(FoundryAccessGrant)
    with pytest.raises((ValueError, PermissionError)):
        native_apply(g, request)
    assert g.db.all(FoundryAccessGrant) == before


def test_audit_failure_rolls_back_grants_and_request(deployed, monkeypatch):
    g = deployed
    grants, requests = g.db.all(FoundryAccessGrant), g.db.all(FoundryRequest)
    original = g.db.insert

    def fail(model):
        if isinstance(model, FoundryAudit):
            raise RuntimeError("synthetic audit failure")
        return original(model)

    monkeypatch.setattr(g.db, "insert", fail)
    with pytest.raises(RuntimeError, match="audit failure"):
        native_apply(g)
    assert (
        g.db.all(FoundryAccessGrant) == grants and g.db.all(FoundryRequest) == requests
    )


def test_command_receipt_audit_tamper_and_request_collision(local):
    apply(local)
    with load_db(local.root / "server.db") as db, db.transaction():
        db.execute(
            "UPDATE foundry_audit SET principal_id=? WHERE operation=?",
            [str(uuid4()), "runtime.local-authorization"],
        )
    with pytest.raises(ValueError, match="audit"):
        run_local_authorization(str(local.root), str(local.request_path))


def test_changed_target_reuses_request_id_is_rejected(local):
    apply(local)
    changed = LocalAuthorizationRequest.model_validate_json(
        local.request_path.read_bytes()
    ).model_copy(update={"operation": "revoke"})
    private_write(local.request_path, changed.model_dump_json())
    with pytest.raises(ValueError, match="conflict"):
        inspect(local)


def test_actual_cli_apply_is_offline_and_uses_owned_state(local, capsys):
    from actions.server._cli_impl import _main_retcode

    digest = inspect(local)["expected_grants_digest"]
    private_write(
        local.request_path,
        local.request.model_copy(
            update={"expected_grants_digest": digest}
        ).model_dump_json(),
    )
    assert (
        _main_retcode(
            [
                "authorize-local",
                "--datadir",
                str(local.root),
                "--request",
                str(local.request_path),
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["owner"] == local.actor.principal_id and not receipt["dryRun"]


def test_other_process_holding_runtime_mutex_is_refused(local):
    import subprocess
    import sys

    script = "from actions.server._common.system_mutex import SystemMutex; import sys; mutex=SystemMutex('action_server.lock', base_dir=sys.argv[1]); print(mutex.get_mutex_aquired(), flush=True); sys.stdin.read()"
    with subprocess.Popen(
        [sys.executable, "-c", script, str(local.root)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        try:
            assert process.stdout.readline().strip() == "True"
            with pytest.raises(ValueError, match="Runtime is running"):
                inspect(local)
        finally:
            process.communicate("", timeout=10)
        assert process.returncode == 0


def test_hardlinked_database_and_oversized_request_refused(local):
    import os

    os.link(local.root / "server.db", local.root / "other.db")
    with pytest.raises(ValueError, match="hardlinked"):
        inspect(local)
    (local.root / "other.db").unlink()
    private_write(local.request_path, " " * 16385)
    with pytest.raises(ValueError, match="bounded"):
        inspect(local)


def test_cli_validation_does_not_echo_rejected_secret(local, capsys, caplog):
    from actions.server._cli_impl import _main_retcode

    raw = local.request.model_dump(mode="json")
    raw["token"] = "synthetic-secret-must-not-print"
    private_write(local.request_path, json.dumps(raw))
    assert (
        _main_retcode(
            [
                "authorize-local",
                "--datadir",
                str(local.root),
                "--request",
                str(local.request_path),
            ]
        )
        == 1
    )
    capture = capsys.readouterr()
    assert raw["token"] not in capture.out + capture.err + caplog.text


def test_historical_revoke_does_not_reactivate_or_require_package_readiness(
    deployed, monkeypatch
):
    from action_server_tests.test_generic_work_item_execution import grant

    from actions.server.foundry.sql_authorization import reference_grant_subject
    from actions.server.run_outputs.models import RunAccessGrant

    g = deployed
    native_apply(g)
    old = g.request.deployment
    grant(
        g.db,
        g.caller.actor,
        old.workspace_id,
        "reference",
        reference_grant_subject(old),
        ["deploy"],
    )
    old_spec = g.owner.deployments._repository.get_revision(old).revision.specification
    changed = old_spec.model_copy(
        update={
            "work_item_policies": (
                old_spec.work_item_policies[0].model_copy(
                    update={
                        "max_input_bytes": old_spec.work_item_policies[
                            0
                        ].max_input_bytes
                        - 1
                    }
                ),
            )
        }
    )
    new = g.owner.deployments.publish(
        g.caller.actor,
        old.workspace_id,
        old.deployment_id,
        old,
        changed,
        idempotency_key="advance-for-revoke",
    )
    with pytest.raises(ValueError, match="active"):
        native_apply(g, g.request.model_copy(update={"request_id": "old-authorize"}))
    baseline = g.db.all(FoundryAccessGrant)
    request = g.request.model_copy(
        update={"operation": "revoke", "request_id": "old-revoke"}
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("revocation must not require compiler/package readiness")

    monkeypatch.setattr(g.owner.registry, "load", forbidden)
    preview = apply_local_authorization(g.db, request, g.profile, None, dry_run=True)
    request = request.model_copy(
        update={"expected_grants_digest": preview["expected_grants_digest"]}
    )
    result = apply_local_authorization(g.db, request, g.profile, None, dry_run=False)
    assert not result["replay"]
    assert apply_local_authorization(g.db, request, g.profile, None, dry_run=False)[
        "replay"
    ]
    assert (
        g.owner.deployments._repository.current(
            old.workspace_id, old.deployment_id
        ).revision.ref
        == new.ref
    )
    assert not g.db.all(RunAccessGrant)
    after = {row.id: row for row in g.db.all(FoundryAccessGrant)}
    for row in baseline:
        if row.id in after and after[row.id].operations_json != row.operations_json:
            assert json.loads(after[row.id].operations_json) == []


def test_owned_grant_revoke_requires_original_audit_provenance(local):
    apply(local)
    with load_db(local.root / "server.db") as db, db.transaction():
        db.execute(
            "DELETE FROM foundry_audit WHERE operation=?",
            ["runtime.local-authorization"],
        )
    private_write(
        local.request_path,
        local.request.model_copy(
            update={"operation": "revoke", "request_id": "revocation"}
        ).model_dump_json(),
    )
    with pytest.raises(ValueError, match="provenance"):
        inspect(local)


def test_symlinked_lock_never_touches_external_target(local, tmp_path):
    outside = tmp_path / "unchanged.txt"
    outside.write_text("must remain unchanged")
    (local.root / "action_server.lock").symlink_to(outside)
    with pytest.raises(ValueError, match="canonical lock"):
        inspect(local)
    assert outside.read_text() == "must remain unchanged"


def test_root_help_snapshot_includes_explicit_offline_command(capsys):
    from actions.server import __version__
    from actions.server._cli_impl import _main_retcode

    with pytest.raises(SystemExit) as stopped:
        _main_retcode(["-h"])
    assert stopped.value.code == 0
    output = (
        capsys.readouterr()
        .out.replace(f"Actions Runtime ({__version__})", "Actions Runtime (<version>)")
        .strip()
    )
    assert (
        output
        == (Path(__file__).parent / "test_cli" / "test_help_-h.txt").read_text().strip()
    )
