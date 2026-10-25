"""Explicit Knowledge hosts on saved-owner local configuration."""
import pytest
from action_server_tests.test_local_knowledge_setup import collection_change, definition
from action_server_tests.test_local_knowledge_setup import (
    knowledge as knowledge_fixture,
)
from action_server_tests.test_local_knowledge_setup import local as local_fixture
from action_server_tests.test_local_knowledge_setup import provider as provider_fixture
from action_server_tests.test_local_provider_setup import call, grant, loaded, request

from actions.server.foundry.provider_config import (
    KnowledgeDuckDBHost,
    ProviderHostConfig,
)
from actions.server.foundry.provider_execution import ConfiguredProviderExecution

knowledge = knowledge_fixture
local = local_fixture
provider = provider_fixture


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def configured(g, *, host=None, secrets=()):
    collection_change(g)
    call(g, definition(g))
    grant(g, ["provider.manage"], g.descriptor.reference)
    g.config = ProviderHostConfig(
        schema_version="actions.local-provider-config/v2",
        provider=g.descriptor.reference,
        source_revision=g.source.revision_id,
        host=host or KnowledgeDuckDBHost(revision=g.spec.reference),
    )
    return call(g, request(g, "configure-host", config=g.config, secrets=secrets))


def test_explicit_configure_and_provision_are_separate(knowledge):
    g = knowledge
    result = configured(g)
    assert result["readiness"] == "configured-not-probed"
    directory = g.root / "provider-state" / "knowledge-versions"
    assert not directory.exists()

    def inspect(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        execution.require_adapter_available(
            g.descriptor.reference, ("documents.search/v1",)
        )
        assert not directory.exists()
        with execution.open_knowledge(g.actor, g.descriptor.reference) as selection:
            assert selection.revision == g.spec.reference
            assert selection.source == g.source
        assert not directory.exists()

    loaded(g, inspect)
    req = request(g, "provision-knowledge-host", config=g.config)
    assert call(g, req, dry_run=True)["readiness"] == "not-probed"
    assert not directory.exists()
    assert call(g, req)["readiness"] == "provisioned-not-ingested"
    assert list(directory.glob("*.duckdb"))
    assert call(g, req)["readiness"] == "provisioned-not-ingested"


def provision(g):
    return call(g, request(g, "provision-knowledge-host", config=g.config))


def test_real_duckdb_roundtrip_restart_and_read_only_selection(knowledge):
    from threading import Event

    from actions.server.data_queries.knowledge_normalization import normalize_knowledge
    from actions.server.data_queries.sealed_sources import (
        ReadBudget,
        SealedReadRejected,
    )

    g = knowledge
    configured(g)

    def write(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        with execution.open_knowledge(
            g.actor, g.descriptor.reference, manage=True
        ) as selection:
            budget = ReadBudget(2000, Event())
            corpus = normalize_knowledge(
                g.spec, selection.source, blobs, selection.seals, budget
            )
            with pytest.raises(SealedReadRejected):
                selection.versions.put(
                    corpus, operation_id="before_provision", budget=budget
                )
            return corpus

    corpus = loaded(g, write)
    provision(g)

    def write_ready(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        with execution.open_knowledge(
            g.actor, g.descriptor.reference, manage=True
        ) as selection:
            selection.versions.put(
                corpus, operation_id="first", budget=ReadBudget(2000, Event())
            )

    loaded(g, write_ready)

    def read(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        with execution.open_knowledge(g.actor, g.descriptor.reference) as selection:
            assert (
                selection.versions.read(
                    g.spec.reference, budget=ReadBudget(2000, Event())
                )
                == corpus
            )
            with pytest.raises(SealedReadRejected):
                selection.versions.put(
                    corpus,
                    operation_id="unauthorized_write",
                    budget=ReadBudget(2000, Event()),
                )

    loaded(g, read)


@pytest.mark.parametrize("permission", ["knowledge.read", "knowledge.manage"])
def test_provision_requires_live_collection_grants_even_on_replay(
    knowledge, permission
):
    g = knowledge
    configured(g)
    req = request(g, "provision-knowledge-host", config=g.config)
    call(g, req)
    collection_change(g, "revoke-owner", (permission,))
    with pytest.raises(PermissionError):
        call(g, req)


def test_search_does_not_require_manage_but_ingestion_does(knowledge):
    g = knowledge
    configured(g)
    collection_change(g, "revoke-owner", ("knowledge.manage",))

    def check(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        with execution.open_knowledge(g.actor, g.descriptor.reference):
            pass
        with pytest.raises(PermissionError):
            with execution.open_knowledge(g.actor, g.descriptor.reference, manage=True):
                pass

    loaded(g, check)


def test_final_sql_recheck_has_no_blob_catalog_secret_or_engine_io(
    knowledge, monkeypatch
):
    from actions.server.foundry.provider_catalog import PrivateProviderStore

    g = knowledge
    configured(g)

    def check(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        pins = execution.pin_sql(g.actor, g.descriptor.reference, manage=True)

        def forbidden(*args, **kwargs):
            raise AssertionError("I/O inside final SQL publication")

        monkeypatch.setattr(execution.registry, "_read", forbidden)
        monkeypatch.setattr(execution, "check_current", forbidden)
        monkeypatch.setattr(PrivateProviderStore, "config", forbidden)
        monkeypatch.setattr(PrivateProviderStore, "resolve_secret", forbidden)
        monkeypatch.setattr(type(blobs), "open", forbidden)
        with db.transaction():
            execution.recheck_sql(g.actor, g.descriptor.reference, pins, manage=True)
            db.execute(
                "UPDATE knowledge_collection_revision SET specification_json='{}'"
            )
            with pytest.raises(ValueError):
                execution.recheck_sql(
                    g.actor, g.descriptor.reference, pins, manage=True
                )

    loaded(g, check)


def test_sql_pins_recheck_live_collection_revocation(knowledge):
    g = knowledge
    configured(g)

    def check(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        pins = execution.pin_sql(g.actor, g.descriptor.reference, manage=True)
        with db.transaction():
            db.execute(
                "UPDATE foundry_access_grant SET operations_json='[]' WHERE subject_kind='knowledge-collection'"
            )
            with pytest.raises(PermissionError):
                execution.recheck_sql(
                    g.actor, g.descriptor.reference, pins, manage=True
                )

    loaded(g, check)


def test_unknown_definition_and_legacy_schema_refused(knowledge):
    from pydantic import ValidationError

    g = knowledge
    configured(g)
    raw = g.config.model_dump(mode="json")
    raw["schema_version"] = "actions.local-provider-config/v1"
    with pytest.raises(ValidationError):
        ProviderHostConfig.model_validate(raw)
    raw = g.config.model_dump(mode="json")
    raw["host"]["revision"]["revision_id"] = "sha256:" + "a" * 64
    changed = ProviderHostConfig.model_validate(raw)
    with pytest.raises(PermissionError):
        call(g, request(g, "configure-host", config=changed), dry_run=True)
    with pytest.raises(ValueError):
        call(g, request(g, "provision-knowledge-host", config=changed))


def test_private_duckdb_symlink_refused(knowledge, tmp_path):
    g = knowledge
    configured(g)
    directory = g.root / "provider-state" / "knowledge-versions"
    directory.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        provision(g)


def test_missing_dependency_is_refused_without_connecting(knowledge, monkeypatch):
    import importlib

    g = knowledge
    configured(g)

    def check(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        original = importlib.import_module

        def unavailable(name, *args, **kwargs):
            if name == "duckdb":
                raise ImportError("synthetic missing optional dependency")
            return original(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", unavailable)
        with pytest.raises(ValueError, match="dependency unavailable"):
            execution.require_adapter_available(
                g.descriptor.reference, ("documents.search/v1",)
            )
        assert not (g.root / "provider-state" / "knowledge-versions").exists()

    loaded(g, check)


def test_knowledge_catalog_requires_explicit_version_and_data_remains_closed(knowledge):
    from pydantic import ValidationError

    from actions.server.foundry.provider_catalog import (
        CatalogEntry,
        PrivateProviderStore,
        ProviderCatalog,
    )

    g = knowledge
    configured(g)
    with PrivateProviderStore(g.root, g.actor, g.workspace) as store:
        catalog = store.catalog(store.current())
        assert catalog.schema_version == "actions.local-provider-catalog/v2"
        raw = catalog.model_dump(mode="json")
        raw["schema_version"] = "actions.local-provider-catalog/v1"
        with pytest.raises(ValidationError):
            ProviderCatalog.model_validate(raw)
        entry = raw["entries"][0]
        entry.pop("kind")
        with pytest.raises(ValidationError):
            CatalogEntry.model_validate(entry)
