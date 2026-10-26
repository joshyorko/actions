"""Public local command with synthetic owned state; no provider network or RCC."""
import hashlib
import io
import json
import logging
import os
import subprocess
import sys
from uuid import uuid4

import pytest
from action_server_tests.test_local_authorization import local as owner_fixture
from action_server_tests.test_local_authorization import private_write
from action_server_tests.test_logical_binding_checkpoint import requirement
from action_server_tests.test_provider_catalog import codec

from actions.server._local_provider_setup import (
    LocalProviderRequest,
    SourceImport,
    run_local_provider_setup,
)
from actions.server._models import load_db
from actions.server.deployments.ids import ProviderProfileId
from actions.server.deployments.provider_registry import (
    DecodedSourceObject,
    ProviderDescriptor,
    SourceManifest,
)
from actions.server.foundry.bootstrap import _OWNER_OPERATIONS
from actions.server.foundry.models import FoundryAccessGrant, FoundryRequest
from actions.server.foundry.provider_bootstrap import load_configured_provider_registry
from actions.server.foundry.provider_catalog import PrivateProviderStore
from actions.server.foundry.provider_config import DuckDBHost, ProviderHostConfig
from actions.server.run_outputs.filesystem import FilesystemOutputProvider

local = owner_fixture


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.fixture
def provider(local):
    if sys.platform != "linux":
        pytest.skip("Linux private provider setup proof")
    g = local
    (g.root / "blobs").mkdir(mode=0o700)
    payload = b"record_id\nsynthetic\n"
    path = g.root / "input.csv"
    private_write(path, payload.decode())
    source = SourceManifest(
        schema_version="actions.logical-source/v2",
        kind="data",
        objects=(
            DecodedSourceObject(
                name="records",
                digest="sha256:" + hashlib.sha256(payload).hexdigest(),
                size=len(payload),
                codec=codec(),
            ),
        ),
    )
    descriptor = ProviderDescriptor(
        workspace_id=g.workspace,
        provider_profile_id=ProviderProfileId(str(uuid4())),
        source_revision=source.revision_id,
        kind="data",
        operations=requirement().operations,
    )
    g.source, g.descriptor, g.input = source, descriptor, path
    g.config = ProviderHostConfig(
        provider=descriptor.reference,
        source_revision=source.revision_id,
        host=DuckDBHost(),
    )
    return g


def request(g, operation, **kwargs):
    return LocalProviderRequest(
        operation=operation, request_id=str(uuid4()), workspace_id=g.workspace, **kwargs
    )


def call(g, req, *, dry_run=False):
    private_write(g.request_path, req.model_dump_json())
    return run_local_provider_setup(str(g.root), str(g.request_path), dry_run=dry_run)


def grant(g, permissions, provider=None):
    req = request(g, "grant-owner", provider=provider, permissions=tuple(permissions))
    receipt = call(g, req, dry_run=True)
    return call(
        g,
        req.model_copy(
            update={"expected_grants_digest": receipt["expected_grants_digest"]}
        ),
    )


def prepare(g):
    grant(g, ["provider.register"])
    call(
        g,
        request(
            g,
            "import-source",
            source=g.source,
            files=(SourceImport(name="records", path=str(g.input)),),
        ),
    )
    call(g, request(g, "register-revision", descriptor=g.descriptor))
    grant(g, ["provider.manage", "provider.inspect"], g.descriptor.reference)


def loaded(g, callback):
    fd = os.open(g.root / "blobs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        with FilesystemOutputProvider(fd) as blobs, load_db(g.root / "server.db") as db:
            return callback(db, blobs)
    finally:
        os.close(fd)


def test_explicit_setup_restart_metadata_no_implicit_data_permissions(provider):
    g = provider
    before_operations = _OWNER_OPERATIONS
    assert (
        loaded(
            g, lambda db, blobs: load_configured_provider_registry(db, g.root, blobs)
        )
        is None
    )
    assert not (g.root / "provider-state").exists()
    with pytest.raises(Exception, match="authorized"):
        call(
            g,
            request(
                g,
                "import-source",
                source=g.source,
                files=(SourceImport(name="records", path=str(g.input)),),
            ),
        )
    prepare(g)
    with load_db(g.root / "server.db") as db:
        grants_before = db.all(FoundryAccessGrant)
    configured = request(g, "configure-host", config=g.config)
    result = call(g, configured)
    assert result["readiness"] == "configured-not-probed"
    assert call(g, configured) == result

    def inspect(db, blobs):
        registry = load_configured_provider_registry(db, g.root, blobs)
        assert (
            registry.operations(g.actor, g.descriptor.reference, "data")
            == requirement().operations
        )
        assert db.all(FoundryAccessGrant) == grants_before
        assert not any(
            "data.read" in row.operations_json or "data.manage" in row.operations_json
            for row in grants_before
        )

    loaded(g, inspect)
    assert _OWNER_OPERATIONS == before_operations
    code = """
import os,sys
from pathlib import Path
from actions.server._models import load_db
from actions.server.foundry.provider_bootstrap import load_configured_provider_registry
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
root=Path(sys.argv[1]);fd=os.open(root/'blobs',os.O_RDONLY|os.O_DIRECTORY)
with FilesystemOutputProvider(fd) as blobs,load_db(root/'server.db') as db:
    assert load_configured_provider_registry(db,root,blobs) is not None
    print('configured-not-probed')
os.close(fd)
"""
    process = subprocess.run(
        [sys.executable, "-c", code, str(g.root)],
        capture_output=True,
        text=True,
        timeout=20,
        env=os.environ.copy(),
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == "configured-not-probed"


def test_dry_run_import_does_not_create_provider_state(provider):
    g = provider
    grant(g, ["provider.register"])
    result = call(
        g,
        request(
            g,
            "import-source",
            source=g.source,
            files=(SourceImport(name="records", path=str(g.input)),),
        ),
        dry_run=True,
    )
    assert result["readiness"] == "not-probed"
    assert not (g.root / "provider-state").exists()
    assert list((g.root / "blobs").iterdir()) == []


@pytest.mark.parametrize("point", ["before_sql", "after_sql"])
def test_configuration_crash_requires_explicit_recovery(provider, monkeypatch, point):
    g = provider
    prepare(g)
    req = request(g, "configure-host", config=g.config)
    if point == "before_sql":
        from actions.server import _local_provider_setup as module

        original = module._record

        def fail(*args, **kwargs):
            raise ValueError("synthetic before SQL")

        monkeypatch.setattr(module, "_record", fail)
    else:
        original = PrivateProviderStore.publish
        monkeypatch.setattr(
            PrivateProviderStore,
            "publish",
            lambda *_: (_ for _ in ()).throw(ValueError("synthetic after SQL")),
        )
    with pytest.raises(ValueError, match="synthetic"):
        call(g, req)
    assert (
        loaded(
            g, lambda db, blobs: load_configured_provider_registry(db, g.root, blobs)
        )
        is None
    )
    intent_file = next(
        path
        for path in (g.root / "provider-state/intents").glob("*.json")
        if ".request." not in path.name
    )
    intent_id = json.loads(intent_file.read_text())["operation_id"]
    if point == "before_sql":
        monkeypatch.setattr(module, "_record", original)
        with pytest.raises(ValueError, match="committed"):
            call(g, request(g, "recover-intent", intent_id=intent_id))
        call(g, req)
    else:
        monkeypatch.setattr(PrivateProviderStore, "publish", original)
        call(g, request(g, "recover-intent", intent_id=intent_id))
    assert (
        loaded(
            g, lambda db, blobs: load_configured_provider_registry(db, g.root, blobs)
        )
        is not None
    )


def test_grant_provenance_cas_revoke_preserves_unrelated(provider):
    g = provider
    prepare(g)
    with load_db(g.root / "server.db") as db:
        unrelated = FoundryAccessGrant(
            str(uuid4()),
            str(g.workspace.root),
            g.actor.principal_id,
            "workspace",
            str(g.workspace.root),
            '["unrelated"]',
        )
        with db.transaction():
            db.insert(unrelated)
    req = request(
        g,
        "revoke-owner",
        provider=g.descriptor.reference,
        permissions=("provider.inspect",),
    )
    with pytest.raises(ValueError, match="CAS"):
        call(g, req)
    current = call(g, req, dry_run=True)
    req = req.model_copy(
        update={"expected_grants_digest": current["expected_grants_digest"]}
    )
    call(g, req)
    call(g, req)
    with pytest.raises(Exception, match="authorized"):
        call(g, request(g, "inspect", provider=g.descriptor.reference))
    with load_db(g.root / "server.db") as db:
        assert db.all(FoundryAccessGrant, where="id=?", values=[unrelated.id]) == [
            unrelated
        ]
        owned = next(
            row for row in db.all(FoundryAccessGrant) if row.subject_kind == "reference"
        )
        with db.transaction():
            db.update_by_id(
                FoundryAccessGrant,
                owned.id,
                {"operations_json": '["provider.manage","data.read"]'},
            )
    changed = request(
        g, "revoke-owner", provider=g.descriptor.reference, permissions=("data.read",)
    )
    current = call(g, changed, dry_run=True)
    with pytest.raises(ValueError, match="provenance"):
        call(
            g,
            changed.model_copy(
                update={"expected_grants_digest": current["expected_grants_digest"]}
            ),
        )


def test_stale_configuration_intent_never_rolls_back(provider):
    g = provider
    prepare(g)
    first = request(g, "configure-host", config=g.config)
    receipt = call(g, first)
    with PrivateProviderStore(g.root, g.actor, g.workspace) as store:
        current = store.current()
    second = request(g, "configure-host", config=g.config, expected_catalog=current)
    call(g, second)
    with pytest.raises(ValueError, match="stale"):
        call(g, request(g, "recover-intent", intent_id=receipt["intent_id"]))
    with pytest.raises(ValueError, match="stale"):
        call(g, first)


def test_refuses_external_control_plane_and_wrong_owner(provider, monkeypatch):
    g = provider
    monkeypatch.setenv("ACTION_SERVER_DATABASE_URL", "postgresql://synthetic")
    with pytest.raises(ValueError, match="external"):
        call(g, request(g, "inspect"))
    monkeypatch.delenv("ACTION_SERVER_DATABASE_URL")
    with load_db(g.root / "server.db") as db:
        row = next(
            row
            for row in db.all(FoundryRequest)
            if row.operation == "runtime.bootstrap"
        )
        with db.transaction():
            db.update_by_id(FoundryRequest, row.id, {"request_fingerprint": "invalid"})
    with pytest.raises(ValueError, match="lineage"):
        call(g, request(g, "inspect"))


def test_cli_closed_logging_never_prints_private_rejected_value(
    provider, capsys, caplog
):
    from actions.server import _cli_impl

    g = provider
    raw = request(g, "inspect").model_dump(mode="json")
    raw["secret"] = "synthetic-secret-never-echo"
    private_write(g.request_path, json.dumps(raw))
    stream = io.StringIO()
    stream.close()
    handler = logging.StreamHandler(stream)
    _cli_impl.log.addHandler(handler)
    old = logging.raiseExceptions
    logging.raiseExceptions = True
    try:
        assert (
            _cli_impl._main_retcode(
                [
                    "providers-local",
                    "--datadir",
                    str(g.root),
                    "--request",
                    str(g.request_path),
                ]
            )
            == 1
        )
    finally:
        _cli_impl.log.removeHandler(handler)
        logging.raiseExceptions = old
    captured = capsys.readouterr()
    assert raw["secret"] not in captured.out + captured.err + caplog.text


def test_full_provider_setup_through_public_cli_subprocess(provider):
    g = provider

    def cli(req, dry=False):
        private_write(g.request_path, req.model_dump_json())
        args = [
            sys.executable,
            "-m",
            "actions.server",
            "providers-local",
            "--datadir",
            str(g.root),
            "--request",
            str(g.request_path),
        ]
        if dry:
            args.append("--dry-run")
        completed = subprocess.run(
            args, capture_output=True, text=True, timeout=20, env=os.environ.copy()
        )
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)

    def cli_grant(permissions, ref=None):
        req = request(g, "grant-owner", permissions=permissions, provider=ref)
        plan = cli(req, True)
        cli(
            req.model_copy(
                update={"expected_grants_digest": plan["expected_grants_digest"]}
            )
        )

    cli_grant(("provider.register",))
    cli(
        request(
            g,
            "import-source",
            source=g.source,
            files=(SourceImport(name="records", path=str(g.input)),),
        )
    )
    cli(request(g, "register-revision", descriptor=g.descriptor))
    cli_grant(("provider.manage", "provider.inspect"), g.descriptor.reference)
    result = cli(request(g, "configure-host", config=g.config))
    assert result["readiness"] == "configured-not-probed"
    assert cli(request(g, "inspect", provider=g.descriptor.reference))[
        "availability"
    ] == {"generation": 0, "enabled": True}


def test_secret_rotation_private_only_no_startup_reads(provider, monkeypatch):
    from actions.server._local_provider_setup import SecretImport
    from actions.server.foundry.provider_config import PostgreSQLHost, SecretVersion

    g = provider
    prepare(g)
    password = SecretVersion(slot=str(uuid4()), version=str(uuid4()))
    ca = SecretVersion(slot=str(uuid4()), version=str(uuid4()))
    secret_path, ca_path = g.root / "private-password", g.root / "private-ca"
    private_write(secret_path, "synthetic-operator-secret")
    private_write(ca_path, "synthetic-private-ca")
    config = g.config.model_copy(
        update={
            "host": PostgreSQLHost(
                host="localhost",
                port=5432,
                database="fixture",
                username="fixture",
                password=password,
                ca_bundle=ca,
            )
        }
    )
    result = call(
        g,
        request(
            g,
            "configure-host",
            config=config,
            secrets=(
                SecretImport(reference=password, path=str(secret_path)),
                SecretImport(reference=ca, path=str(ca_path)),
            ),
        ),
    )
    monkeypatch.setattr(
        PrivateProviderStore,
        "resolve_secret",
        lambda *_: pytest.fail("startup secret read"),
    )
    with load_db(g.root / "server.db") as db:
        before = (db.all(FoundryAccessGrant), db.all(FoundryRequest))
    loaded(g, lambda db, blobs: load_configured_provider_registry(db, g.root, blobs))
    with load_db(g.root / "server.db") as db:
        assert (db.all(FoundryAccessGrant), db.all(FoundryRequest)) == before
        persisted = repr(db.all(FoundryRequest)) + repr(db.all(FoundryAccessGrant))
    for secret in (
        "synthetic-operator-secret",
        "synthetic-private-ca",
        str(secret_path),
        str(ca_path),
    ):
        assert secret not in persisted + json.dumps(result)


def test_source_mutation_and_unknown_request_do_not_publish(provider):
    g = provider
    grant(g, ["provider.register"])
    private_write(g.input, "tampered")
    with pytest.raises(ValueError, match="pinned manifest"):
        call(
            g,
            request(
                g,
                "import-source",
                source=g.source,
                files=(SourceImport(name="records", path=str(g.input)),),
            ),
        )
    with PrivateProviderStore(g.root, g.actor, g.workspace) as store:
        assert store.current() is None
    with pytest.raises(ValueError, match="outside selected"):
        request(g, "inspect", config=g.config)


def test_disabled_provider_and_absent_blobs_can_revoke(provider):
    g = provider
    prepare(g)
    call(g, request(g, "configure-host", config=g.config))
    for path in (g.root / "blobs").iterdir():
        path.unlink()
    assert call(
        g,
        request(
            g,
            "set-enabled",
            provider=g.descriptor.reference,
            expected_generation=0,
            enabled=False,
        ),
    ) == {"generation": 1, "enabled": False}
    with pytest.raises(ValueError, match="evidence unavailable"):
        call(
            g,
            request(
                g,
                "set-enabled",
                provider=g.descriptor.reference,
                expected_generation=1,
                enabled=True,
            ),
        )


def test_runtime_mutex_blocks_operator(provider):
    from actions.server._common.app_mutex import obtain_app_mutex

    g = provider
    lock = obtain_app_mutex(
        data_dir=g.root,
        lock_basename="action_server.lock",
        app_name="test Runtime",
        timeout=0,
        kill_lock_holder=False,
    )
    try:
        with pytest.raises(RuntimeError):
            call(g, request(g, "inspect"))
    finally:
        lock.release_mutex()


def test_recovery_rejects_changed_private_target(provider, monkeypatch):
    from actions.server.foundry.provider_catalog import CatalogIntent
    from actions.server.foundry.provider_config import PostgreSQLHost, SecretVersion

    g = provider
    prepare(g)
    req = request(g, "configure-host", config=g.config)
    original = PrivateProviderStore.publish
    monkeypatch.setattr(
        PrivateProviderStore,
        "publish",
        lambda *_: (_ for _ in ()).throw(ValueError("after SQL")),
    )
    with pytest.raises(ValueError, match="after SQL"):
        call(g, req)
    monkeypatch.setattr(PrivateProviderStore, "publish", original)
    path = next(
        path
        for path in (g.root / "provider-state/intents").glob("*.json")
        if ".request." not in path.name
    )
    intent = CatalogIntent.model_validate_json(path.read_bytes())
    with PrivateProviderStore(g.root, g.actor, g.workspace, create=True) as store:
        config = g.config.model_copy(
            update={
                "host": PostgreSQLHost(
                    host="different-host",
                    port=5432,
                    database="fixture",
                    username="fixture",
                    password=SecretVersion(slot=str(uuid4()), version=str(uuid4())),
                )
            }
        )
        key = store.stage_config(config)
        prior = store.catalog(intent.target)
        altered = prior.model_copy(
            update={
                "entries": (
                    prior.entries[0].model_copy(update={"config_digest": key}),
                ),
            }
        )
        from actions.server.foundry.provider_catalog import CatalogPointer

        new_target = CatalogPointer(
            generation=altered.generation, digest=altered.catalog_digest
        )
        catalog_path = (
            g.root / "provider-state/catalogs" / (altered.generation + ".json")
        )
        from actions.server.deployments.canonical import canonicalize_json

        catalog_path.chmod(0o600)
        catalog_path.write_bytes(canonicalize_json(altered.model_dump_json().encode()))
        catalog_path.chmod(0o400)
    path.chmod(0o600)
    from actions.server.deployments.canonical import canonicalize_json

    path.write_bytes(
        canonicalize_json(
            intent.model_copy(update={"target": new_target}).model_dump_json().encode()
        )
    )
    path.chmod(0o400)
    with pytest.raises(ValueError, match="target differs"):
        call(g, request(g, "recover-intent", intent_id=intent.operation_id))
    assert (
        loaded(
            g, lambda db, blobs: load_configured_provider_registry(db, g.root, blobs)
        )
        is None
    )


def test_register_permission_cannot_be_mixed_into_reference_scope(provider):
    with pytest.raises(ValueError, match="workspace register"):
        request(
            provider,
            "grant-owner",
            provider=provider.descriptor.reference,
            permissions=("provider.register", "provider.inspect"),
        )


def test_startup_requires_committed_catalog_audit(provider):
    g = provider
    prepare(g)
    receipt = call(g, request(g, "configure-host", config=g.config))
    with load_db(g.root / "server.db") as db:
        with db.transaction():
            db.execute(
                "DELETE FROM foundry_audit WHERE foundry_request_id=?",
                [receipt["intent_id"]],
            )
    with pytest.raises(ValueError, match="configuration unavailable"):
        loaded(
            g, lambda db, blobs: load_configured_provider_registry(db, g.root, blobs)
        )


def test_startup_does_not_need_manage_grant_after_publication(provider):
    g = provider
    prepare(g)
    call(g, request(g, "configure-host", config=g.config))
    revoke = request(
        g,
        "revoke-owner",
        provider=g.descriptor.reference,
        permissions=("provider.manage",),
    )
    state = call(g, revoke, dry_run=True)
    call(
        g,
        revoke.model_copy(
            update={"expected_grants_digest": state["expected_grants_digest"]}
        ),
    )

    def inspect(db, blobs):
        registry = load_configured_provider_registry(db, g.root, blobs)
        assert (
            registry.operations(g.actor, g.descriptor.reference, "data")
            == requirement().operations
        )

    loaded(g, inspect)


def test_configuration_audit_failure_rolls_back_and_retries(provider, monkeypatch):
    from actions.server._database import Database
    from actions.server.foundry.models import FoundryAudit

    g = provider
    prepare(g)
    req = request(g, "configure-host", config=g.config)
    original = Database.insert

    def fail(db, row):
        if (
            isinstance(row, FoundryAudit)
            and row.operation == "runtime.providers-local.configure-host"
        ):
            raise ValueError("synthetic audit insertion failure")
        return original(db, row)

    monkeypatch.setattr(Database, "insert", fail)
    with pytest.raises(ValueError, match="audit insertion"):
        call(g, req)
    with load_db(g.root / "server.db") as db:
        records = db.all(
            FoundryRequest,
            where="operation=?",
            values=["runtime.providers-local.configure-host"],
        )
        assert records == []
    assert (
        loaded(
            g, lambda db, blobs: load_configured_provider_registry(db, g.root, blobs)
        )
        is None
    )
    monkeypatch.setattr(Database, "insert", original)
    assert call(g, req)["readiness"] == "configured-not-probed"


def test_recovery_reauthorizes_manage(provider, monkeypatch):
    g = provider
    prepare(g)
    original = PrivateProviderStore.publish
    monkeypatch.setattr(
        PrivateProviderStore,
        "publish",
        lambda *_: (_ for _ in ()).throw(ValueError("stop before pointer")),
    )
    with pytest.raises(ValueError, match="stop before"):
        call(g, request(g, "configure-host", config=g.config))
    monkeypatch.setattr(PrivateProviderStore, "publish", original)
    path = next(
        path
        for path in (g.root / "provider-state/intents").glob("*.json")
        if ".request." not in path.name
    )
    intent_id = json.loads(path.read_text())["operation_id"]
    revoke = request(
        g,
        "revoke-owner",
        provider=g.descriptor.reference,
        permissions=("provider.manage",),
    )
    plan = call(g, revoke, dry_run=True)
    call(
        g,
        revoke.model_copy(
            update={"expected_grants_digest": plan["expected_grants_digest"]}
        ),
    )
    with pytest.raises(Exception, match="authorized"):
        call(g, request(g, "recover-intent", intent_id=intent_id))
    assert (
        loaded(
            g, lambda db, blobs: load_configured_provider_registry(db, g.root, blobs)
        )
        is None
    )


def test_staging_cleanup_does_not_delete_replaced_inode(provider, monkeypatch):
    from pathlib import Path

    from actions.server.foundry.provider_config import SecretVersion

    g = provider
    prepare(g)
    original = os.write
    replaced = []

    def replace_then_fail(fd, data):
        path = Path(os.readlink(f"/proc/self/fd/{fd}"))
        if path.parent.name == "secrets" and path.name.startswith(".stage-"):
            path.unlink()
            path.write_bytes(b"replacement-must-survive")
            path.chmod(0o600)
            replaced.append(path)
            raise OSError("synthetic replaced staging")
        return original(fd, data)

    with PrivateProviderStore(g.root, g.actor, g.workspace, create=True) as store:
        monkeypatch.setattr(os, "write", replace_then_fail)
        with pytest.raises(OSError, match="replaced"):
            store.import_secret(
                SecretVersion(slot=str(uuid4()), version=str(uuid4())), b"new-secret"
            )
    monkeypatch.setattr(os, "write", original)
    assert len(replaced) == 1
    assert replaced[0].read_bytes() == b"replacement-must-survive"


@pytest.mark.parametrize("corruption", ["result", "from_revision", "to_revision"])
def test_configure_replay_verifies_committed_publication_receipt(
    provider, monkeypatch, corruption
):
    g = provider
    prepare(g)
    req = request(g, "configure-host", config=g.config)
    original = PrivateProviderStore.publish

    def fail(*args):
        raise ValueError("synthetic after SQL")

    monkeypatch.setattr(PrivateProviderStore, "publish", fail)
    with pytest.raises(ValueError, match="synthetic after SQL"):
        call(g, req)
    with load_db(g.root / "server.db") as db:
        with db.transaction():
            if corruption == "result":
                db.execute(
                    "UPDATE foundry_request SET result_json='{}' WHERE operation=?",
                    ["runtime.providers-local.configure-host"],
                )
            elif corruption == "from_revision":
                db.execute(
                    "UPDATE foundry_audit SET from_revision_id='corrupt' WHERE operation=?",
                    ["runtime.providers-local.configure-host"],
                )
            else:
                db.execute(
                    "UPDATE foundry_audit SET to_revision_id='corrupt' WHERE operation=?",
                    ["runtime.providers-local.configure-host"],
                )
    monkeypatch.setattr(PrivateProviderStore, "publish", original)
    with pytest.raises(ValueError):
        call(g, req)
    assert not (g.root / "provider-state/CURRENT").exists()


def test_recovery_dry_run_never_claims_configuration_or_publishes(
    provider, monkeypatch
):
    g = provider
    prepare(g)
    original = PrivateProviderStore.publish

    def fail(*args):
        raise ValueError("synthetic after SQL")

    monkeypatch.setattr(PrivateProviderStore, "publish", fail)
    with pytest.raises(ValueError, match="synthetic after SQL"):
        call(g, request(g, "configure-host", config=g.config))
    intent_file = next(
        path
        for path in (g.root / "provider-state/intents").glob("*.json")
        if ".request." not in path.name
    )
    intent_id = json.loads(intent_file.read_text())["operation_id"]
    monkeypatch.setattr(PrivateProviderStore, "publish", original)
    result = call(g, request(g, "recover-intent", intent_id=intent_id), dry_run=True)
    assert result["readiness"] == "publication-authorized-dry-run"
    assert not (g.root / "provider-state/CURRENT").exists()
