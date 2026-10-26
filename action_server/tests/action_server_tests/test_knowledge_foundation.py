"""Immutable metadata and explicit authority; no ingestion/search/RCC readiness."""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_generic_work_item_execution import grant

from actions.server.data_queries.knowledge_values import (
    KnowledgeCollectionRef,
    KnowledgeRevisionSpec,
    knowledge_grant_subject,
)
from actions.server.deployments.logical_bindings import BindingField, BindingOperation
from actions.server.deployments.provider_registry import (
    ProviderDescriptor,
    SourceManifest,
    SourceObject,
)
from actions.server.foundry.knowledge_authority import KnowledgeRevisionAuthority
from actions.server.foundry.knowledge_models import KnowledgeCollectionRevision
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.foundry.provider_registry import (
    RetainedSourceEvidence,
    SqlProviderRegistry,
)
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.service import _transaction, _update
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.fixture
def foundation(database_location, foundry_package_store):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        blobs = foundry_package_store
        seal = blobs.stage([b"Bounded knowledge source"]).receipt
        source = SourceManifest(
            kind="knowledge",
            objects=(
                SourceObject(name="document", digest=seal.digest, size=seal.size),
            ),
        )
        descriptor = ProviderDescriptor(
            workspace_id=refs.workspace,
            provider_profile_id=refs.provider.provider_profile_id,
            source_revision=source.revision_id,
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
        auth = SqlFoundryAuthorization(db)
        providers = SqlProviderRegistry(
            db,
            auth,
            RetainedSourceEvidence(
                blobs, {(str(refs.workspace.root), seal.digest): seal}
            ),
        )
        grant(
            db,
            actor,
            refs.workspace,
            "workspace",
            str(refs.workspace.root),
            ["provider.register"],
        )
        source_grant = grant(
            db,
            actor,
            refs.workspace,
            "reference",
            reference_grant_subject(descriptor.reference),
            ["provider.inspect", "knowledge.read"],
        )
        providers.register(actor, descriptor, source, idempotency_key="source")
        collection = KnowledgeCollectionRef(
            workspace_id=refs.workspace, collection_id=str(uuid4())
        )
        collection_grant = grant(
            db,
            actor,
            refs.workspace,
            "knowledge-collection",
            knowledge_grant_subject(collection),
            ["knowledge.read", "knowledge.manage"],
        )
        spec = KnowledgeRevisionSpec(
            workspace_id=refs.workspace,
            collection_id=collection.collection_id,
            source_revision=source.revision_id,
        )
        yield SimpleNamespace(
            db=db,
            actor=actor,
            refs=refs,
            blobs=blobs,
            source=source,
            descriptor=descriptor,
            providers=providers,
            auth=auth,
            collection=collection,
            collection_grant=collection_grant,
            source_grant=source_grant,
            spec=spec,
            authority=KnowledgeRevisionAuthority(db, providers),
        )


def register(g, key="definition"):
    return g.authority.register_definition(
        g.actor, g.spec, source_provider=g.descriptor.reference, idempotency_key=key
    )


def test_definition_replay_reopen_and_no_grants_or_readiness(foundation):
    g = foundation
    before = g.db.all(FoundryAccessGrant)
    ref = register(g)
    assert ref == g.spec.reference == register(g)
    assert len(g.db.all(KnowledgeCollectionRevision)) == 1
    assert len(g.db.all(FoundryRequest)) == len(g.db.all(FoundryAudit)) == 2
    assert g.db.all(FoundryAccessGrant) == before
    reopened = KnowledgeRevisionAuthority(g.db, g.providers)
    assert reopened.require_revision(g.actor, ref, "knowledge.read") == g.spec
    assert reopened.require_revision(g.actor, ref, "knowledge.manage") == g.spec
    with pytest.raises(ValueError, match="not configured"):
        reopened.require_search_ready(g.actor, ref)


@pytest.mark.parametrize(
    "permissions",
    [[], ["knowledge.read"], ["knowledge.manage"], ["data.read", "data.manage"]],
)
def test_registration_requires_separate_read_manage(foundation, permissions):
    g = foundation
    with _transaction(g.db):
        _update(
            g.db,
            FoundryAccessGrant,
            g.collection_grant.id,
            {"operations_json": json.dumps(permissions)},
        )
    with pytest.raises(PermissionError):
        register(g)
    assert not g.db.all(KnowledgeCollectionRevision)


@pytest.mark.parametrize(
    "permissions",
    [[], ["provider.inspect"], ["knowledge.read"], ["data.read", "provider.inspect"]],
)
def test_source_admission_needs_inspect_and_knowledge_read(foundation, permissions):
    g = foundation
    with _transaction(g.db):
        _update(
            g.db,
            FoundryAccessGrant,
            g.source_grant.id,
            {"operations_json": json.dumps(permissions)},
        )
    with pytest.raises(PermissionError):
        register(g)
    assert not g.db.all(KnowledgeCollectionRevision)


def test_exact_revision_grant_does_not_cover_new_revision(foundation):
    g = foundation
    with _transaction(g.db):
        _update(
            g.db, FoundryAccessGrant, g.collection_grant.id, {"operations_json": "[]"}
        )
    grant(
        g.db,
        g.actor,
        g.refs.workspace,
        "knowledge-revision",
        knowledge_grant_subject(g.spec.reference),
        ["knowledge.read", "knowledge.manage"],
    )
    ref = register(g)
    changed = g.spec.model_copy(update={"max_documents": 2})
    with pytest.raises(PermissionError):
        g.authority.register_definition(
            g.actor,
            changed,
            source_provider=g.descriptor.reference,
            idempotency_key="changed",
        )
    assert g.authority.require_revision(g.actor, ref, "knowledge.read") == g.spec


def test_revocation_blocks_replay_and_does_not_delete_definition(foundation):
    g = foundation
    ref = register(g)
    with _transaction(g.db):
        _update(
            g.db, FoundryAccessGrant, g.collection_grant.id, {"operations_json": "[]"}
        )
    with pytest.raises(PermissionError):
        register(g)
    with pytest.raises(PermissionError):
        g.authority.require_revision(g.actor, ref, "knowledge.read")
    assert len(g.db.all(KnowledgeCollectionRevision)) == 1


def test_changed_idempotency_payload_and_wrong_scope_refused(foundation):
    g = foundation
    register(g)
    changed = g.spec.model_copy(update={"max_documents": 2})
    with pytest.raises(ValueError):
        g.authority.register_definition(
            g.actor,
            changed,
            source_provider=g.descriptor.reference,
            idempotency_key="definition",
        )
    other = g.spec.model_copy(update={"collection_id": str(uuid4())})
    with pytest.raises(PermissionError):
        g.authority.register_definition(
            g.actor,
            other,
            source_provider=g.descriptor.reference,
            idempotency_key="other",
        )
    assert len(g.db.all(KnowledgeCollectionRevision)) == 1


@pytest.mark.parametrize(
    "field,value",
    [("result_json", "{}"), ("request_fingerprint", "sha256:" + "f" * 64)],
)
def test_replay_request_tamper_fails_closed(foundation, field, value):
    g = foundation
    register(g)
    request = next(
        r
        for r in g.db.all(FoundryRequest)
        if r.operation == "knowledge.register-definition"
    )
    with _transaction(g.db):
        _update(g.db, FoundryRequest, request.id, {field: value})
    with pytest.raises(ValueError):
        register(g)


def test_audit_tamper_and_insert_rollback(foundation, monkeypatch):
    g = foundation
    original = g.db.insert

    def fail(row):
        if (
            isinstance(row, FoundryAudit)
            and row.operation == "knowledge.register-definition"
        ):
            raise RuntimeError("injected")
        original(row)

    monkeypatch.setattr(g.db, "insert", fail)
    with pytest.raises(RuntimeError):
        register(g)
    assert not g.db.all(KnowledgeCollectionRevision)
    assert len(g.db.all(FoundryRequest)) == 1
    monkeypatch.setattr(g.db, "insert", original)
    ref = register(g)
    audit = next(
        a
        for a in g.db.all(FoundryAudit)
        if a.operation == "knowledge.register-definition"
    )
    with _transaction(g.db):
        _update(g.db, FoundryAudit, audit.id, {"to_revision_id": "sha256:" + "f" * 64})
    with pytest.raises(ValueError):
        g.authority.require_revision(g.actor, ref, "knowledge.read")


def test_values_reject_private_fields_and_revalidate_copies(foundation):
    g = foundation
    value = json.loads(g.spec.model_dump_json())
    for key in ("dsn", "path", "provider", "credentials", "endpoint"):
        with pytest.raises(ValueError):
            KnowledgeRevisionSpec.model_validate_json(
                json.dumps({**value, key: "private-marker"})
            )
    with pytest.raises(ValueError) as error:
        g.authority.register_definition(
            g.actor,
            g.spec.model_copy(update={"source_revision": "private-marker"}),
            source_provider=g.descriptor.reference,
            idempotency_key="bad",
        )
    assert "private-marker" not in str(error.value)


def test_source_identity_mismatch_and_revocation_on_replay(foundation):
    g = foundation
    changed = g.spec.model_copy(update={"source_revision": "sha256:" + "a" * 64})
    with pytest.raises(PermissionError):
        g.authority.register_definition(
            g.actor,
            changed,
            source_provider=g.descriptor.reference,
            idempotency_key="wrong-source",
        )
    assert not g.db.all(KnowledgeCollectionRevision)
    register(g)
    with _transaction(g.db):
        _update(g.db, FoundryAccessGrant, g.source_grant.id, {"operations_json": "[]"})
    with pytest.raises(PermissionError):
        register(g)


def test_read_and_manage_metadata_are_distinct(foundation):
    g = foundation
    ref = register(g)
    with _transaction(g.db):
        _update(
            g.db,
            FoundryAccessGrant,
            g.collection_grant.id,
            {"operations_json": '["knowledge.read"]'},
        )
    assert g.authority.require_revision(g.actor, ref, "knowledge.read") == g.spec
    with pytest.raises(PermissionError):
        g.authority.require_revision(g.actor, ref, "knowledge.manage")
    with pytest.raises(PermissionError):
        g.authority.require_revision(
            Actor(principal_id=str(uuid4())), ref, "knowledge.read"
        )


def test_same_definition_new_request_preserves_original_provenance(foundation):
    g = foundation
    ref = register(g)
    original = g.db.all(KnowledgeCollectionRevision)
    assert register(g, "second") == ref
    assert g.db.all(KnowledgeCollectionRevision) == original
    assert len(g.db.all(FoundryRequest)) == len(g.db.all(FoundryAudit)) == 3


def test_revision_identity_and_strict_limits(foundation):
    g = foundation
    assert KnowledgeRevisionSpec.model_validate_json(g.spec.model_dump_json()) == g.spec
    assert g.spec.model_copy(update={"max_results": 2}).reference != g.spec.reference
    for field, value in [
        ("max_results", True),
        ("max_documents", 10001),
        ("source_format", "data-csv/v2"),
        ("timeout_ms", 0),
    ]:
        payload = g.spec.model_dump(mode="json")
        payload[field] = value
        with pytest.raises(ValueError):
            KnowledgeRevisionSpec.model_validate_json(json.dumps(payload))


def test_migration22_is_empty_forward_only_and_old_reader_refuses(foundation):
    from actions.server import migrations

    g = foundation
    # Fixture upgrades frozen schema16 through every migration including22.
    assert max(row.id for row in g.db.all(migrations.Migration)) == 22
    assert not g.db.all(KnowledgeCollectionRevision)
    # Execute the exact prior migration-status implementation with its actual
    # version21 map, rather than simulating a hypothetical old-reader predicate.
    import base64
    from pathlib import Path

    baseline = Path(__file__).with_name("knowledge_migration21.txt.b64")
    namespace = {"__name__": "actions.server.migrations.old21"}
    exec(
        compile(base64.b64decode(baseline.read_bytes()), str(baseline), "exec"),
        namespace,
    )
    from actions.server._database import Database

    old_db = Database(g.db.db_path)
    with old_db.connect():
        status = namespace["_db_migration_status"](old_db)
    assert status == namespace["MigrationStatus"].TOO_NEW


def test_fresh_schema22_has_empty_definitions(database_location):
    from actions.server._models import create_db
    from actions.server.migrations import Migration

    with create_db(database_location) as db:
        assert max(row.id for row in db.all(Migration)) == 22
        assert db.all(KnowledgeCollectionRevision) == []
        assert db.all(FoundryAccessGrant) == []


def test_explicit_schema21_upgrade_preserves_workspace(database_location):
    from action_server_tests.foundry_historical import create_historical_schema

    from actions.server._database import Database
    from actions.server._models import get_all_model_classes
    from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration, migrate_db
    from actions.server.run_outputs.models import Workspace

    workspace = Workspace(str(uuid4()), "active", 0)
    db = Database(database_location)
    with db.connect():
        db.initialize(get_all_model_classes())
        with db.transaction():
            create_historical_schema(db, 16)
            db.insert(Migration(16, MIGRATION_ID_TO_NAME[16]))
            db.insert(workspace)
    assert migrate_db(database_location, to_version=21)
    with db.connect():
        assert max(row.id for row in db.all(Migration)) == 21
        assert "knowledge_collection_revision" not in db.list_table_names()
    assert migrate_db(database_location, to_version=22)
    with db.connect():
        assert db.all(Workspace) == [workspace]
        assert max(row.id for row in db.all(Migration)) == 22
        assert db.all(KnowledgeCollectionRevision) == []


def test_real_data_source_cannot_be_admitted_as_knowledge(foundation):
    g = foundation
    source = g.source.model_copy(update={"kind": "data"})
    descriptor = g.descriptor.model_copy(
        update={"kind": "data", "source_revision": source.revision_id}
    )
    grant(
        g.db,
        g.actor,
        g.refs.workspace,
        "reference",
        reference_grant_subject(descriptor.reference),
        ["provider.inspect", "knowledge.read"],
    )
    g.providers.register(g.actor, descriptor, source, idempotency_key="data-source")
    spec = g.spec.model_copy(update={"source_revision": source.revision_id})
    with pytest.raises(ValueError):
        g.authority.register_definition(
            g.actor,
            spec,
            source_provider=descriptor.reference,
            idempotency_key="not-knowledge",
        )
    assert not g.db.all(KnowledgeCollectionRevision)


def test_retained_source_evidence_missing_refuses_definition(foundation):
    g = foundation
    unavailable = SqlProviderRegistry(g.db, g.auth, RetainedSourceEvidence(g.blobs, {}))
    authority = KnowledgeRevisionAuthority(g.db, unavailable)
    with pytest.raises((ValueError, PermissionError)):
        authority.register_definition(
            g.actor,
            g.spec,
            source_provider=g.descriptor.reference,
            idempotency_key="missing-seal",
        )
    assert not g.db.all(KnowledgeCollectionRevision)
