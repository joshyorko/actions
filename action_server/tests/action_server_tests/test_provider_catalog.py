"""Durable private state/declaration tests, without data engines or RCC."""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs
from action_server_tests.test_logical_binding_checkpoint import requirement

from actions.server.deployments.provider_registry import (
    CsvSourceCodec,
    DecodedSourceObject,
    ParquetSourceCodec,
    ProviderDescriptor,
    SourceColumn,
    SourceManifest,
    SourceObject,
    require_executable_source,
)
from actions.server.foundry.provider_catalog import (
    CatalogEntry,
    CatalogIntent,
    CatalogSeal,
    PrivateProviderStore,
    ProviderCatalog,
    SourceSealRecord,
)
from actions.server.foundry.provider_config import (
    DuckDBHost,
    PostgreSQLHost,
    ProviderHostConfig,
    SecretVersion,
)
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import Actor


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def codec():
    return CsvSourceCodec(
        columns=(SourceColumn(name="record_id", kind="string"),),
        max_rows=100,
        max_decoded_bytes=65536,
        max_field_bytes=1024,
    )


@pytest.fixture
def local(tmp_path):
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    (root / "blobs").mkdir(mode=0o700)
    fd = os.open(root / "blobs", os.O_RDONLY | os.O_DIRECTORY)
    blobs = FilesystemOutputProvider(fd)
    os.close(fd)
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    seal = blobs.stage([b"record_id\nexample\n"]).receipt
    source = SourceManifest(
        schema_version="actions.logical-source/v2",
        kind="data",
        objects=(
            DecodedSourceObject(
                name="records", digest=seal.digest, size=seal.size, codec=codec()
            ),
        ),
    )
    descriptor = ProviderDescriptor(
        workspace_id=refs.workspace,
        provider_profile_id=refs.provider.provider_profile_id,
        source_revision=source.revision_id,
        kind="data",
        operations=requirement().operations,
    )
    config = ProviderHostConfig(
        provider=descriptor.reference,
        source_revision=source.revision_id,
        host=DuckDBHost(),
    )
    with PrivateProviderStore(root, actor, refs.workspace, create=True) as store:
        key = store.stage_config(config)
        catalog = ProviderCatalog(
            owner=actor,
            workspace=refs.workspace,
            generation=str(uuid4()),
            entries=(
                CatalogEntry(
                    descriptor=descriptor,
                    source=source,
                    seals=(CatalogSeal(name="records", seal=seal),),
                    config_digest=key,
                ),
            ),
        )
        target = store.stage_catalog(catalog)
        intent = CatalogIntent(
            operation_id=str(uuid4()),
            owner=actor,
            workspace=refs.workspace,
            request_key="setup",
            request_fingerprint="sha256:" + "a" * 64,
            expected=None,
            target=target,
        )
        store.stage_intent(intent)
        yield SimpleNamespace(
            root=root,
            store=store,
            blobs=blobs,
            source=source,
            refs=refs,
            actor=actor,
            config=config,
            catalog=catalog,
            intent=intent,
            seal=seal,
        )
    blobs.close()


def test_v1_bytes_and_actual_old_reader_rejection(local):
    legacy = SourceManifest(
        kind="data",
        objects=(
            SourceObject(
                name="records", digest=local.seal.digest, size=local.seal.size
            ),
        ),
    )
    path = Path(__file__).with_name("provider_source_v1.py.txt")
    loader = importlib.machinery.SourceFileLoader("archived_source_v1", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    try:
        loader.exec_module(module)
        old = module.SourceManifest.model_validate_json(legacy.model_dump_json())
        assert old.model_dump_json() == legacy.model_dump_json()
        assert old.revision_id == legacy.revision_id
        with pytest.raises(ValueError):
            module.SourceManifest.model_validate_json(local.source.model_dump_json())
    finally:
        sys.modules.pop(loader.name)
    with pytest.raises(ValueError, match="decoder"):
        require_executable_source(legacy)
    assert require_executable_source(local.source) == local.source


def test_codec_identity_and_invariants(local):
    altered = codec().model_copy(update={"max_rows": 99})
    obj = local.source.objects[0].model_copy(update={"codec": altered})
    changed = local.source.model_copy(update={"objects": (obj,)})
    assert (
        SourceManifest.model_validate(changed).revision_id != local.source.revision_id
    )
    for change in (
        {"delimiter": ";"},
        {"encoding": "latin1"},
        {"null_value": ""},
        {"columns": []},
        {"max_rows": 100001},
    ):
        with pytest.raises(ValueError):
            CsvSourceCodec.model_validate_json(
                json.dumps(dict(codec().model_dump(mode="json"), **change))
            )
    with pytest.raises(ValueError):
        SourceManifest.model_validate(
            local.source.model_copy(
                update={"schema_version": "actions.logical-source/v1"}
            )
        )
    parquet = ParquetSourceCodec(
        columns=codec().columns,
        max_rows=100,
        max_decoded_bytes=65536,
        max_field_bytes=1024,
        max_row_groups=1,
    )
    with pytest.raises(ValueError):
        ParquetSourceCodec.model_validate(
            parquet.model_copy(update={"external_metadata": "allow"})
        )


def test_fresh_subprocess_reconstructs_catalog_without_secrets(local):
    g = local
    g.store.publish(g.intent)
    # Deliberately absent secret value: startup reconstruction must not read it.
    code = """
import os,sys
from pathlib import Path
from actions.server.foundry.provider_catalog import PrivateProviderStore
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import Actor
from actions.server.deployments.ids import WorkspaceId
root=Path(sys.argv[1]); fd=os.open(root/'blobs',os.O_RDONLY|os.O_DIRECTORY)
with FilesystemOutputProvider(fd) as blobs, PrivateProviderStore(root,Actor(principal_id=sys.argv[2]),WorkspaceId(sys.argv[3])) as store:
    store.resolve_secret=lambda *_: (_ for _ in ()).throw(AssertionError('secret read'))
    catalog,evidence=store.reconstruct(store.current(),blobs)
    print(catalog.catalog_digest)
os.close(fd)
"""
    process = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(g.root),
            g.actor.principal_id,
            str(g.refs.workspace.root),
        ],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=20,
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == g.catalog.catalog_digest


def test_no_current_until_explicit_publish_and_stale_retry(local):
    g = local
    assert g.store.current() is None
    assert g.store.intent(g.intent.operation_id) == g.intent
    g.store.publish(g.intent)
    g.store.publish(g.intent)
    next_catalog = g.catalog.model_copy(
        update={"generation": str(uuid4()), "parent_digest": g.catalog.catalog_digest}
    )
    target = g.store.stage_catalog(next_catalog)
    new = g.intent.model_copy(
        update={
            "operation_id": str(uuid4()),
            "expected": g.intent.target,
            "target": target,
        }
    )
    g.store.stage_intent(new)
    g.store.publish(new)
    with pytest.raises(ValueError, match="stale"):
        g.store.publish(g.intent)
    assert g.store.current() == target


@pytest.mark.parametrize("point", ["replace", "fsync"])
def test_pointer_crash_is_old_or_complete_never_partial(local, monkeypatch, point):
    g = local
    original = getattr(os, point)

    def fail(*args, **kwargs):
        if point == "replace" or (args and args[0] == g.store._root):
            raise OSError("synthetic crash")
        return original(*args, **kwargs)

    monkeypatch.setattr(os, point, fail)
    with pytest.raises(OSError, match="synthetic"):
        g.store.publish(g.intent)
    monkeypatch.setattr(os, point, original)
    current = g.store.current()
    assert current is None or current == g.intent.target
    g.store.publish(g.intent)
    assert g.store.current() == g.intent.target


@pytest.mark.parametrize(
    "kind", ["symlink", "hardlink", "oversize", "tamper", "permission"]
)
def test_private_config_integrity(local, kind, tmp_path):
    g = local
    target = g.root / "provider-state/configs" / (g.config.config_digest[7:] + ".json")
    if kind == "symlink":
        target.unlink()
        target.symlink_to(tmp_path / "outside")
    elif kind == "hardlink":
        os.link(target, tmp_path / "linked")
    elif kind == "permission":
        target.chmod(0o644)
    else:
        target.chmod(0o600)
        target.write_text("x" * (128 * 1024 + 1) if kind == "oversize" else "{}")
    with pytest.raises((ValueError, OSError)):
        g.store.reconstruct(g.intent.target, g.blobs)


def test_wrong_owner_and_missing_store_no_creation(local, tmp_path):
    with PrivateProviderStore(
        local.root, Actor(principal_id=str(uuid4())), local.refs.workspace
    ) as wrong:
        with pytest.raises(ValueError, match="lineage"):
            wrong.catalog(local.intent.target)
    empty = tmp_path / "empty"
    empty.mkdir(mode=0o700)
    with pytest.raises(FileNotFoundError):
        PrivateProviderStore(empty, local.actor, local.refs.workspace)
    assert list(empty.iterdir()) == []


def test_secret_import_explicit_and_reconstruction_never_resolves(local, monkeypatch):
    g = local
    secret = SecretVersion(slot=str(uuid4()), version=str(uuid4()))
    g.store.import_secret(secret, b"synthetic-secret")
    assert g.store.resolve_secret(secret) == b"synthetic-secret"
    host = PostgreSQLHost(
        host="localhost", port=5432, database="test", username="test", password=secret
    )
    config = g.config.model_copy(update={"host": host})
    key = g.store.stage_config(config)
    entry = g.catalog.entries[0].model_copy(update={"config_digest": key})
    catalog = g.catalog.model_copy(
        update={"generation": str(uuid4()), "entries": (entry,)}
    )
    pointer = g.store.stage_catalog(catalog)
    monkeypatch.setattr(
        g.store, "resolve_secret", lambda *_: pytest.fail("startup secret read")
    )
    assert g.store.reconstruct(pointer, g.blobs)[0] == catalog
    assert (
        b"synthetic-secret"
        not in (
            g.root / "provider-state/catalogs" / (catalog.generation + ".json")
        ).read_bytes()
    )
    with pytest.raises(ValueError, match="conflict"):
        g.store.import_secret(secret, b"replacement")


def test_catalog_exact_config_and_evidence(local):
    g = local
    bad = g.catalog.entries[0].model_copy(update={"seals": ()})
    with pytest.raises(ValueError):
        g.store.stage_catalog(g.catalog.model_copy(update={"entries": (bad,)}))
    (g.root / "blobs" / g.seal.object_ref).unlink()
    with pytest.raises(ValueError, match="evidence unavailable"):
        g.store.reconstruct(g.intent.target, g.blobs)


def test_source_seals_reload_before_configuration(local):
    g = local
    record = SourceSealRecord(
        owner=g.actor,
        workspace=g.refs.workspace,
        source=g.source,
        seals=g.catalog.entries[0].seals,
    )
    g.store.stage_source(record)
    with PrivateProviderStore(g.root, g.actor, g.refs.workspace) as reopened:
        assert reopened.source(g.source.revision_id) == record
        assert reopened.current() is None
    g.store.stage_source(record)
    forged = record.model_copy(update={"owner": Actor(principal_id=str(uuid4()))})
    with pytest.raises(ValueError, match="lineage"):
        g.store.stage_source(forged)


@pytest.mark.parametrize("point", ["write", "fsync"])
def test_immutable_staging_fault_can_retry_without_poison(local, monkeypatch, point):
    g = local
    g.store.publish(g.intent)
    ref = SecretVersion(slot=str(uuid4()), version=str(uuid4()))
    original = getattr(os, point)
    calls = 0

    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            if point == "write":
                original(args[0], bytes(args[1][:2]))
            raise OSError("interrupted staging")
        return original(*args, **kwargs)

    monkeypatch.setattr(os, point, fail)
    with pytest.raises(OSError, match="interrupted"):
        g.store.import_secret(ref, b"synthetic-new-value")
    monkeypatch.setattr(os, point, original)
    assert g.store.current() == g.intent.target
    g.store.import_secret(ref, b"synthetic-new-value")
    assert g.store.resolve_secret(ref) == b"synthetic-new-value"
    with pytest.raises(ValueError, match="conflict"):
        g.store.import_secret(ref, b"different")
    assert g.store.resolve_secret(ref) == b"synthetic-new-value"
    assert not list((g.root / "provider-state/secrets").glob(".stage-*"))


def test_ca_reference_does_not_resolve_on_config_load(local, monkeypatch):
    g = local
    host = PostgreSQLHost(
        host="localhost",
        port=5432,
        database="fixture",
        username="fixture",
        password=SecretVersion(slot=str(uuid4()), version=str(uuid4())),
        ca_bundle=SecretVersion(slot=str(uuid4()), version=str(uuid4())),
    )
    config = g.config.model_copy(update={"host": host})
    digest_value = g.store.stage_config(config)
    monkeypatch.setattr(
        g.store, "resolve_secret", lambda *_: pytest.fail("implicit secret/CA read")
    )
    assert g.store.config(digest_value) == config
