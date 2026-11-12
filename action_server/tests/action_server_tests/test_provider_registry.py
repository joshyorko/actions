"""Metadata prerequisite only; synthetic sealed bytes, no data operation or RCC."""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests import test_logical_binding_checkpoint as logical_fixture
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_generic_work_item_execution import grant
from action_server_tests.test_logical_binding_checkpoint import requirement, select

from actions.server.deployments.provider_registry import (
    ProviderDescriptor,
    SourceManifest,
    SourceObject,
)
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.foundry.provider_models import (
    FoundryProviderRevision,
    FoundrySourceRevision,
)
from actions.server.foundry.provider_registry import (
    RetainedSourceEvidence,
    SqlProviderRegistry,
    _ref_id,
)
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.types import Actor

bound = logical_fixture.bound

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def setup_registry(db, refs, actor, blobs):
    seal = blobs.stage([b'{"record_id":"synthetic"}']).receipt
    source = SourceManifest(
        kind="data",
        objects=(SourceObject(name="records", digest=seal.digest, size=seal.size),),
    )
    descriptor = ProviderDescriptor(
        workspace_id=refs.workspace,
        provider_profile_id=refs.provider.provider_profile_id,
        source_revision=source.revision_id,
        kind="data",
        operations=requirement().operations,
    )
    evidence = RetainedSourceEvidence(
        blobs, {(str(refs.workspace.root), seal.digest): seal}
    )
    registry = SqlProviderRegistry(db, SqlFoundryAuthorization(db), evidence)
    register_grant = grant(
        db,
        actor,
        refs.workspace,
        "workspace",
        str(refs.workspace.root),
        ["provider.register"],
    )
    access_grant = grant(
        db,
        actor,
        refs.workspace,
        "reference",
        reference_grant_subject(descriptor.reference),
        ["provider.inspect", "provider.manage", "deploy", "execute"],
    )
    return SimpleNamespace(
        db=db,
        refs=refs,
        actor=actor,
        registry=registry,
        descriptor=descriptor,
        source=source,
        seal=seal,
        register_grant=register_grant,
        access_grant=access_grant,
    )


@pytest.fixture
def registry(database_location, foundry_package_store):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        yield setup_registry(db, refs, actor, foundry_package_store)


def register(g):
    return g.registry.register(
        g.actor, g.descriptor, g.source, idempotency_key="registration"
    )


def test_register_reopen_no_grants_or_private_metadata(registry):
    g = registry
    before = g.db.all(FoundryAccessGrant)
    ref = register(g)
    assert register(g) == ref
    assert g.registry.operations(g.actor, ref, "data") == requirement().operations
    assert g.db.all(FoundryAccessGrant) == before
    assert len(g.db.all(FoundryRequest)) == len(g.db.all(FoundryAudit)) == 1
    assert g.db.all(FoundryAudit)[0].deployment_id == ""
    reopened = SqlProviderRegistry(
        g.db, SqlFoundryAuthorization(g.db), g.registry._evidence
    )
    assert reopened.describe(g.actor, ref) == g.descriptor
    wire = g.db.all(FoundryProviderRevision)[0].descriptor_json
    for forbidden in (
        g.seal.object_ref,
        "dsn",
        "endpoint",
        "credential",
        "path",
        "engine",
    ):
        assert forbidden not in wire
    with pytest.raises(ValueError, match="not configured"):
        SqlProviderRegistry(g.db, SqlFoundryAuthorization(g.db)).describe(g.actor, ref)


@pytest.mark.parametrize(
    "permission", ["provider.register", "provider.inspect", "provider.manage"]
)
def test_revoked_authority_rechecked(registry, permission):
    g = registry
    ref = register(g)
    row = g.register_grant if permission == "provider.register" else g.access_grant
    with g.db.transaction():
        g.db.update_by_id(FoundryAccessGrant, row.id, {"operations_json": "[]"})
    with pytest.raises(Exception, match="authorized"):
        if permission == "provider.register":
            register(g)
        elif permission == "provider.inspect":
            g.registry.describe(g.actor, ref)
        else:
            g.registry.set_enabled(
                g.actor,
                ref,
                expected_generation=0,
                enabled=False,
                idempotency_key="disable",
            )


def test_disable_cas_and_historical_replay(registry):
    g = registry
    ref = register(g)
    assert (
        g.registry.set_enabled(
            g.actor,
            ref,
            expected_generation=0,
            enabled=False,
            idempotency_key="disable",
        )
        == 1
    )
    receipt = next(
        row
        for row in g.db.all(FoundryRequest)
        if row.operation == "provider.availability"
    )
    assert json.loads(receipt.result_json) == {
        "provider": ref.model_dump(mode="json"),
        "generation": 1,
    }
    register(g)  # does not re-enable
    with pytest.raises(ValueError, match="disabled"):
        g.registry.describe(g.actor, ref)
    with pytest.raises(ValueError, match="generation conflict"):
        g.registry.set_enabled(
            g.actor, ref, expected_generation=0, enabled=True, idempotency_key="stale"
        )
    assert (
        g.registry.set_enabled(
            g.actor, ref, expected_generation=1, enabled=True, idempotency_key="enable"
        )
        == 2
    )
    assert (
        g.registry.set_enabled(
            g.actor,
            ref,
            expected_generation=0,
            enabled=False,
            idempotency_key="disable",
        )
        == 1
    )
    assert g.registry.describe(g.actor, ref) == g.descriptor


@pytest.mark.parametrize("target", ["source", "provider", "blob", "catalog"])
def test_retained_evidence_tamper_fails_closed(
    registry, target, foundry_package_store, tmp_path
):
    g = registry
    ref = register(g)
    with g.db.transaction():
        if target == "source":
            row = g.db.all(FoundrySourceRevision)[0]
            g.db.update_by_id(FoundrySourceRevision, row.id, {"manifest_json": "{}"})
        elif target == "provider":
            g.db.update_by_id(
                FoundryProviderRevision, _ref_id(ref), {"descriptor_json": "{}"}
            )
        elif target == "blob":
            (tmp_path / "package-objects" / g.seal.object_ref).unlink()
        else:
            g.registry = SqlProviderRegistry(
                g.db,
                SqlFoundryAuthorization(g.db),
                RetainedSourceEvidence(foundry_package_store, {}),
            )
    with pytest.raises(ValueError) as error:
        g.registry.operations(g.actor, ref, "data")
    assert g.seal.object_ref not in str(error.value)


def test_audit_failure_rolls_back(registry, monkeypatch):
    g = registry
    original = g.db.insert

    def fail(row):
        if isinstance(row, FoundryAudit):
            raise ValueError("synthetic audit failure")
        return original(row)

    monkeypatch.setattr(g.db, "insert", fail)
    with pytest.raises(ValueError, match="audit failure"):
        register(g)
    assert not g.db.all(FoundrySourceRevision)
    assert not g.db.all(FoundryProviderRevision)
    assert not g.db.all(FoundryRequest)


def test_unavailable_source_cannot_register_or_enable_but_can_disable(registry):
    g = registry
    g.registry._evidence = None
    with pytest.raises(ValueError, match="not configured"):
        register(g)
    assert not g.db.all(FoundrySourceRevision)


def test_registry_port_joins_real_native_selection(bound, foundry_package_store):
    g = bound
    providers = setup_registry(g.db, g.refs, g.actor, foundry_package_store)
    first = register(providers)
    second_descriptor = providers.descriptor.model_copy(
        update={"provider_profile_id": g.refs.second_provider.provider_profile_id}
    )
    second = providers.registry.register(
        g.actor, second_descriptor, providers.source, idempotency_key="second"
    )
    grant(
        g.db,
        g.actor,
        g.refs.workspace,
        "reference",
        reference_grant_subject(second),
        ["deploy", "execute", "provider.inspect"],
    )
    g.selector.provider_compatibility = providers.registry
    a = select(g, (g.choice.model_copy(update={"provider": first}),))
    b = select(g, (g.choice.model_copy(update={"provider": second}),))
    assert a.package_revisions == b.package_revisions
    assert a != b
    assert providers.registry.operations(
        g.actor, first, "data"
    ) == providers.registry.operations(g.actor, second, "data")


@pytest.mark.parametrize("field", ["dsn", "engine", "endpoint", "credential", "path"])
def test_private_config_rejected(registry, field):
    raw = registry.descriptor.model_dump(mode="json")
    raw[field] = "synthetic-secret"
    with pytest.raises(ValueError):
        ProviderDescriptor.model_validate_json(json.dumps(raw))


def test_missing_evidence_after_registration_allows_disable_only(registry):
    g = registry
    ref = register(g)
    g.registry._evidence = None
    assert (
        g.registry.set_enabled(
            g.actor,
            ref,
            expected_generation=0,
            enabled=False,
            idempotency_key="disable",
        )
        == 1
    )
    with pytest.raises(ValueError, match="not configured"):
        g.registry.set_enabled(
            g.actor, ref, expected_generation=1, enabled=True, idempotency_key="enable"
        )


def test_wrong_actor_kind_workspace_and_replay_conflict(registry):
    g = registry
    ref = register(g)
    with pytest.raises(Exception, match="authorized"):
        g.registry.describe(Actor(principal_id=str(uuid4())), ref)
    with pytest.raises(ValueError, match="kind mismatch"):
        g.registry.operations(g.actor, ref, "knowledge")
    other = _refs().workspace
    with pytest.raises(Exception, match="authorized"):
        g.registry.register(
            g.actor,
            g.descriptor.model_copy(update={"workspace_id": other}),
            g.source,
            idempotency_key="other-workspace",
        )
    altered = g.descriptor.model_copy(
        update={"provider_profile_id": g.refs.second_provider.provider_profile_id}
    )
    with pytest.raises(ValueError, match="replay conflict"):
        g.registry.register(g.actor, altered, g.source, idempotency_key="registration")
    assert len(g.db.all(FoundryProviderRevision)) == 1


@pytest.mark.parametrize("change", ["bounds", "effect", "missing", "extra", "grant"])
def test_real_registry_selection_negatives(bound, foundry_package_store, change):
    g = bound
    p = setup_registry(g.db, g.refs, g.actor, foundry_package_store)
    if change in ("bounds", "effect"):
        op = p.descriptor.operations[0].model_copy(
            update={"max_rows": 99} if change == "bounds" else {"effect": "write"}
        )
        p.descriptor = p.descriptor.model_copy(update={"operations": (op,)})
        grant(
            g.db,
            g.actor,
            g.refs.workspace,
            "reference",
            reference_grant_subject(p.descriptor.reference),
            ["provider.inspect", "deploy"],
        )
    ref = register(p)
    g.selector.provider_compatibility = p.registry
    choice = g.choice.model_copy(update={"provider": ref})
    choices = (choice,)
    if change == "missing":
        choices = ()
    elif change == "extra":
        choices = (choice, choice.model_copy(update={"requirement_id": "unowned"}))
    elif change == "grant":
        with g.db.transaction():
            g.db.update_by_id(
                FoundryAccessGrant, p.access_grant.id, {"operations_json": '["deploy"]'}
            )
    with pytest.raises(Exception):
        select(g, choices)


def test_mutable_source_mode_and_unknown_version_refused(registry):
    raw = registry.source.model_dump(mode="json")
    for changes in (
        {"mode": "live-database"},
        {"schema_version": "future"},
        {"source_version": "operator-label"},
    ):
        with pytest.raises(ValueError):
            SourceManifest.model_validate_json(json.dumps(dict(raw, **changes)))


def test_availability_audit_rollback(registry, monkeypatch):
    g = registry
    ref = register(g)
    original = g.db.insert

    def fail(row):
        if isinstance(row, FoundryAudit):
            raise ValueError("synthetic audit failure")
        return original(row)

    monkeypatch.setattr(g.db, "insert", fail)
    with pytest.raises(ValueError, match="audit failure"):
        g.registry.set_enabled(
            g.actor,
            ref,
            expected_generation=0,
            enabled=False,
            idempotency_key="disable",
        )
    assert g.registry.describe(g.actor, ref) == g.descriptor


def test_source_order_identity_and_scope(registry, foundry_package_store):
    g = registry
    first = g.source.objects[0]
    second = first.model_copy(update={"name": "other"})
    a = SourceManifest(kind="data", objects=(first, second))
    b = SourceManifest(kind="data", objects=(second, first))
    assert a.revision_id == b.revision_id
    with pytest.raises(ValueError, match="duplicate"):
        SourceManifest(kind="data", objects=(first, first))
    with pytest.raises(ValueError, match="identity mismatch"):
        g.registry.register(g.actor, g.descriptor, a, idempotency_key="wrong-source")
    g.registry._evidence = RetainedSourceEvidence(
        foundry_package_store, {(str(_refs().workspace.root), g.seal.digest): g.seal}
    )
    with pytest.raises(ValueError, match="evidence unavailable"):
        register(g)
    assert not g.db.all(FoundryProviderRevision)


def test_noncanonical_retained_provider_rejected(registry):
    g = registry
    ref = register(g)
    row = g.db.all(FoundryProviderRevision)[0]
    with g.db.transaction():
        g.db.update_by_id(
            FoundryProviderRevision,
            row.id,
            {"descriptor_json": " " + row.descriptor_json},
        )
    with pytest.raises(ValueError, match="identity mismatch"):
        g.registry.describe(g.actor, ref)
    with pytest.raises(ValueError, match="canonical"):
        g.registry.set_enabled(
            g.actor,
            ref,
            expected_generation=0,
            enabled=False,
            idempotency_key="disable",
        )
