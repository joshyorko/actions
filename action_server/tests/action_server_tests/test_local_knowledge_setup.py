"""Saved-owner Knowledge metadata setup; no worker or implicit execution readiness."""
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from action_server_tests.test_local_provider_setup import call, grant, loaded
from action_server_tests.test_local_provider_setup import local as local_fixture
from action_server_tests.test_local_provider_setup import private_write
from action_server_tests.test_local_provider_setup import provider as provider_fixture
from action_server_tests.test_local_provider_setup import request

from actions.server import _local_provider_setup as setup
from actions.server.data_queries.knowledge_values import (
    KnowledgeCollectionRef,
    KnowledgeRevisionSpec,
)
from actions.server.deployments.logical_bindings import BindingField, BindingOperation
from actions.server.deployments.provider_registry import (
    ProviderDescriptor,
    SourceManifest,
    SourceObject,
)
from actions.server.foundry.knowledge_models import KnowledgeCollectionRevision
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)

local = local_fixture
provider = provider_fixture


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.fixture
def knowledge(provider):
    g = provider
    payload = b"Retained synthetic document"
    private_write(g.input, payload.decode())
    g.source = SourceManifest(
        kind="knowledge",
        objects=(
            SourceObject(
                name="document",
                digest="sha256:" + hashlib.sha256(payload).hexdigest(),
                size=len(payload),
            ),
        ),
    )
    g.descriptor = ProviderDescriptor(
        workspace_id=g.workspace,
        provider_profile_id=g.descriptor.provider_profile_id,
        source_revision=g.source.revision_id,
        kind="knowledge",
        operations=(
            BindingOperation(
                name="documents.search/v1",
                effect="read",
                parameters=(BindingField(name="query", kind="string"),),
                result=(BindingField(name="text", kind="string"),),
                max_rows=20,
                max_bytes=65536,
                timeout_ms=1000,
            ),
        ),
    )
    g.collection = KnowledgeCollectionRef(
        workspace_id=g.workspace, collection_id=str(uuid4())
    )
    g.spec = KnowledgeRevisionSpec(
        workspace_id=g.workspace,
        collection_id=g.collection.collection_id,
        source_revision=g.source.revision_id,
    )
    grant(g, ["provider.register"])
    call(
        g,
        request(
            g,
            "import-source",
            source=g.source,
            files=(setup.SourceImport(name="document", path=str(g.input)),),
        ),
    )
    call(g, request(g, "register-revision", descriptor=g.descriptor))
    grant(g, ["provider.inspect", "knowledge.read"], g.descriptor.reference)
    return g


def collection_change(
    g, operation="grant-owner", permissions=("knowledge.read", "knowledge.manage")
):
    req = request(
        g, operation, knowledge_collection=g.collection, permissions=permissions
    )
    preview = call(g, req, dry_run=True)
    req = req.model_copy(
        update={"expected_grants_digest": preview["expected_grants_digest"]}
    )
    return req, call(g, req)


def definition(g):
    return request(
        g,
        "register-knowledge-definition",
        provider=g.descriptor.reference,
        knowledge_definition=g.spec,
    )


def snapshot(g):
    return loaded(
        g,
        lambda db, blobs: {
            cls.__name__: db.all(cls)
            for cls in (
                KnowledgeCollectionRevision,
                FoundryAccessGrant,
                FoundryRequest,
                FoundryAudit,
            )
        },
    )


def test_definition_dryrun_reopen_replay_metadata_only(knowledge):
    g = knowledge
    collection_change(g)
    before = snapshot(g)
    req = definition(g)
    preview = call(g, req, dry_run=True)
    assert preview["readiness"] == "metadata-only"
    assert snapshot(g) == before
    result = call(g, req)
    after = snapshot(g)
    assert result == preview == call(g, req)
    assert snapshot(g) == after
    assert len(after["KnowledgeCollectionRevision"]) == 1
    assert after["FoundryAccessGrant"] == before["FoundryAccessGrant"]
    assert len(after["FoundryRequest"]) == len(before["FoundryRequest"]) + 2
    assert len(after["FoundryAudit"]) == len(before["FoundryAudit"]) + 2
    assert not (g.root / "provider-state" / "CURRENT").exists()


@pytest.mark.parametrize(
    "permissions", [(), ("knowledge.read",), ("knowledge.manage",)]
)
def test_registration_needs_independent_collection_grants(knowledge, permissions):
    g = knowledge
    if permissions:
        collection_change(g, permissions=permissions)
    before = snapshot(g)
    for dry_run in (True, False):
        with pytest.raises(PermissionError):
            call(g, definition(g), dry_run=dry_run)
    assert snapshot(g) == before


def test_revoke_and_old_grant_replay_do_not_restore_authority(knowledge):
    g = knowledge
    grant_request, receipt = collection_change(g)
    req = definition(g)
    call(g, req)
    collection_change(g, "revoke-owner", ("knowledge.read",))
    before = snapshot(g)
    assert call(g, grant_request) == receipt
    assert snapshot(g) == before
    with pytest.raises(PermissionError):
        call(g, req)
    state = call(g, request(g, "inspect", knowledge_collection=g.collection))
    assert state["knowledge_collection"] == g.collection.model_dump(mode="json")


def test_collection_cas_and_changed_definition_id_fail(knowledge):
    g = knowledge
    req = request(
        g,
        "grant-owner",
        knowledge_collection=g.collection,
        permissions=("knowledge.read",),
    )
    preview = call(g, req, dry_run=True)
    collection_change(g)
    with pytest.raises(ValueError, match="changed|CAS|stale"):
        call(
            g,
            req.model_copy(
                update={"expected_grants_digest": preview["expected_grants_digest"]}
            ),
        )
    req = definition(g)
    call(g, req)
    before = snapshot(g)
    with pytest.raises(ValueError, match="reuse|differ|conflict"):
        call(
            g,
            req.model_copy(
                update={
                    "knowledge_definition": g.spec.model_copy(update={"max_results": 1})
                }
            ),
        )
    assert snapshot(g) == before


def test_local_audit_failure_rolls_back_definition_and_replay_is_safe(
    knowledge, monkeypatch
):
    g = knowledge
    collection_change(g)
    before = snapshot(g)
    original = setup._record

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic local audit failure")

    monkeypatch.setattr(setup, "_record", fail)
    req = definition(g)
    with pytest.raises(RuntimeError, match="synthetic"):
        call(g, req)
    assert snapshot(g) == before
    monkeypatch.setattr(setup, "_record", original)
    assert call(g, req) == call(g, req)
    assert len(snapshot(g)["KnowledgeCollectionRevision"]) == 1


def test_closed_collection_target_and_workspace(knowledge):
    g = knowledge
    for kwargs in (
        {
            "provider": g.descriptor.reference,
            "knowledge_collection": g.collection,
            "permissions": ("knowledge.read",),
        },
        {"knowledge_collection": g.collection, "permissions": ("data.read",)},
        {"knowledge_collection": g.collection, "permissions": ("provider.register",)},
    ):
        with pytest.raises(ValueError):
            request(g, "grant-owner", **kwargs)
    req = request(
        g,
        "inspect",
        knowledge_collection=g.collection.model_copy(
            update={"workspace_id": type(g.workspace)(str(uuid4()))}
        ),
    )
    with pytest.raises(ValueError, match="Workspace"):
        call(g, req)


def test_registration_rechecks_source_permission(knowledge):
    g = knowledge
    collection_change(g)
    req = definition(g)
    call(g, req)
    revoke = request(
        g,
        "revoke-owner",
        provider=g.descriptor.reference,
        permissions=("knowledge.read",),
    )
    preview = call(g, revoke, dry_run=True)
    call(
        g,
        revoke.model_copy(
            update={"expected_grants_digest": preview["expected_grants_digest"]}
        ),
    )
    with pytest.raises(PermissionError):
        call(g, req)


def test_old_request_serialization_and_fingerprints_stay_exact(provider):
    g = provider
    namespace = dict(vars(setup))
    # Pinned pre-extension DTO preserves old defaults and field order, not just
    # hand-picked digest strings that could miss an added default-null field.
    exec(
        compile(
            base64.b64decode(
                Path(__file__)
                .with_name("local_provider_request_v1.txt.b64")
                .read_bytes()
            ).decode(),
            "local_provider_request_v1.txt",
            "exec",
        ),
        namespace,
    )
    old = namespace["LocalProviderRequest"]
    cases = [
        ("inspect", {}),
        ("grant-owner", {"permissions": ("provider.register",)}),
        (
            "revoke-owner",
            {"permissions": ("data.read",), "provider": g.descriptor.reference},
        ),
        (
            "import-source",
            {
                "source": g.source,
                "files": (setup.SourceImport(name="records", path=str(g.input)),),
            },
        ),
        ("register-revision", {"descriptor": g.descriptor}),
        ("configure-host", {"config": g.config}),
        ("recover-intent", {"intent_id": "a" * 64}),
        (
            "set-enabled",
            {
                "provider": g.descriptor.reference,
                "expected_generation": 1,
                "enabled": False,
            },
        ),
    ]
    for operation, kwargs in cases:
        value = dict(
            operation=operation,
            request_id="old-receipt",
            workspace_id=g.workspace,
            **kwargs,
        )
        previous, current = old(**value), setup.LocalProviderRequest(**value)
        assert previous.model_dump_json() == current.model_dump_json()
        assert setup._fingerprint(previous) == setup._fingerprint(current)
        for options in (
            {"exclude_none": True},
            {"include": {"operation"}},
            {"exclude_unset": True},
        ):
            assert previous.model_dump(**options) == current.model_dump(**options)


def test_definition_through_fresh_public_cli(knowledge):
    g = knowledge
    root = Path(setup.__file__).resolve().parents[3]
    env = dict(
        os.environ, PYTHONPATH=str(root) + os.pathsep + os.environ.get("PYTHONPATH", "")
    )
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import actions.server._local_provider_setup as m; print(m.__file__)",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
        check=True,
    )
    assert Path(probe.stdout.strip()).resolve() == Path(setup.__file__).resolve()

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
        proc = subprocess.run(args, capture_output=True, text=True, env=env, timeout=20)
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    req = request(
        g,
        "grant-owner",
        knowledge_collection=g.collection,
        permissions=("knowledge.read", "knowledge.manage"),
    )
    preview = cli(req, True)
    grant_request = req.model_copy(
        update={"expected_grants_digest": preview["expected_grants_digest"]}
    )
    cli(grant_request)
    req = definition(g)
    preview = cli(req, True)
    assert preview["readiness"] == "metadata-only"
    assert cli(req) == preview == cli(req)
    assert len(snapshot(g)["KnowledgeCollectionRevision"]) == 1


def test_raw_knowledge_is_retained_metadata_not_executable_catalog(knowledge):
    from actions.server.deployments.provider_registry import require_executable_source
    from actions.server.foundry.provider_catalog import (
        CatalogEntry,
        PrivateProviderStore,
        require_retained_source,
    )

    g = knowledge
    assert require_retained_source(g.source) == g.source
    with pytest.raises(ValueError, match="decoder"):
        require_executable_source(g.source)
    with PrivateProviderStore(g.root, g.actor, g.workspace) as store:
        seals = store.source(g.source.revision_id).seals
    with pytest.raises(ValueError, match="decoder"):
        CatalogEntry(
            descriptor=g.descriptor,
            source=g.source,
            seals=seals,
            config_digest="sha256:" + "0" * 64,
        )
    for kind, schema in (
        ("data", "actions.logical-source/v1"),
        ("knowledge", "actions.logical-source/v2"),
    ):
        raw = g.source.model_dump(mode="json")
        raw.update(kind=kind, schema_version=schema)
        with pytest.raises(ValueError):
            require_retained_source(SourceManifest.model_validate_json(json.dumps(raw)))


def test_definition_source_corruption_fails_on_replay(knowledge):
    g = knowledge
    collection_change(g)
    req = definition(g)
    call(g, req)
    before = snapshot(g)
    objects = [p for p in (g.root / "blobs").iterdir() if p.is_file()]
    assert objects
    for path in objects:
        path.chmod(0o600)
        path.write_bytes(b"corrupted")
        path.chmod(0o400)
    with pytest.raises(ValueError):
        call(g, req)
    assert snapshot(g) == before


def test_definition_refuses_shared_control_plane_and_running_runtime(
    knowledge, monkeypatch
):
    from actions.server._common.app_mutex import obtain_app_mutex

    g = knowledge
    collection_change(g)
    before = snapshot(g)
    monkeypatch.setenv("ACTION_SERVER_DATABASE_URL", "synthetic-not-a-credential")
    with pytest.raises(ValueError):
        call(g, definition(g))
    monkeypatch.delenv("ACTION_SERVER_DATABASE_URL")
    lock = obtain_app_mutex(
        data_dir=g.root,
        lock_basename="action_server.lock",
        app_name="test Runtime",
        timeout=0,
        kill_lock_holder=False,
    )
    try:
        with pytest.raises(RuntimeError):
            call(g, definition(g))
    finally:
        lock.release_mutex()
    assert snapshot(g) == before
