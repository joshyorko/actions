import os
import uuid

import pytest

from actions.server.data_queries.knowledge import (
    DuckDBKnowledgeProvider,
    KnowledgeCollectionService,
    KnowledgeDenied,
    KnowledgeField,
    KnowledgeRejected,
    KnowledgeSchema,
    LocalCollection,
    LocalFilesKnowledgeProvider,
    PostgreSQLKnowledgeProvider,
    local_source_version,
)
from actions.server.run_outputs.types import Actor


WORKSPACE = str(uuid.UUID("10000000-0000-4000-8000-000000000001"))
OTHER_WORKSPACE = str(uuid.UUID("20000000-0000-4000-8000-000000000002"))
COLLECTION = str(uuid.UUID("30000000-0000-4000-8000-000000000003"))
ACTOR = Actor(principal_id=str(uuid.UUID("40000000-0000-4000-8000-000000000004")))
SCHEMA = KnowledgeSchema(
    fields=(
        KnowledgeField(name="title", kind="text"),
        KnowledgeField(name="year", kind="integer"),
    )
)


class _AllowWorkspace:
    def __init__(self, workspace_id=WORKSPACE, *, can_manage=True):
        self.workspace_id = workspace_id
        self.manage = can_manage

    def can_read(self, actor, workspace_id, collection_id):
        return actor == ACTOR and workspace_id == self.workspace_id

    def can_manage(self, actor, workspace_id, collection_id):
        return self.manage and self.can_read(actor, workspace_id, collection_id)


@pytest.fixture(params=["duckdb", "postgresql"])
def provider(request, tmp_path):
    if request.param == "duckdb":
        pytest.importorskip("duckdb", reason="install Runtime data-duckdb extra")
        yield DuckDBKnowledgeProvider(tmp_path / "knowledge.duckdb")
        return

    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    dsn = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
    if not dsn:
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            pytest.fail("knowledge PostgreSQL fixture is required")
        pytest.skip("isolated PostgreSQL fixture not configured")
    schema = "actions_knowledge_test_" + uuid.uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as owner:
        owner.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            yield PostgreSQLKnowledgeProvider(
                make_conninfo(dsn, options="-csearch_path=" + schema)
            )
        finally:
            owner.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def _binding(root, *, workspace=WORKSPACE, collection=COLLECTION, files=("papers.csv",), fmt="csv", revoked=False):
    return LocalCollection(
        workspace_id=workspace,
        collection_id=collection,
        root=root,
        files=files,
        schema=SCHEMA,
        source_version=local_source_version(root, files),
        format=fmt,
        revoked=revoked,
    )


def _service(provider, binding, *, authorizer=None):
    return KnowledgeCollectionService(
        authorizer or _AllowWorkspace(), provider, (binding,), LocalFilesKnowledgeProvider()
    )


def test_typed_ingestion_and_deterministic_bounded_search(provider, tmp_path):
    (tmp_path / "papers.csv").write_text(
        "title,year\nAlpha knowledge,2024\nKnowledge beta,2023\nKnowledge alpha,2022\n",
        encoding="utf-8",
    )
    binding = _binding(tmp_path)
    service = _service(provider, binding)

    assert service.ingest(ACTOR, WORKSPACE, COLLECTION) == 3
    first = service.search(ACTOR, WORKSPACE, COLLECTION, "knowledge alpha", limit=1)
    second = service.search(
        ACTOR, WORKSPACE, COLLECTION, "knowledge alpha", offset=1, limit=1
    )

    assert first.total == second.total == 3
    assert first.source_version == binding.source_version
    assert first.provider == provider.kind
    assert first.data_schema == SCHEMA
    assert first.hits[0].document.document_id == "papers.csv#2"
    assert second.hits[0].document.document_id == "papers.csv#4"
    assert first.hits[0].document.values == {"title": "Alpha knowledge", "year": 2024}
    assert first.hits[0].document.metadata == {
        "source_file": "papers.csv",
        "source_row": "2",
    }


def test_document_ingestion_and_changed_source_version(provider, tmp_path):
    (tmp_path / "policy.txt").write_text("Refunds require a receipt.", encoding="utf-8")
    docs_schema = KnowledgeSchema(fields=(KnowledgeField(name="body", kind="text"),))
    files = ("policy.txt",)
    binding = LocalCollection(
        WORKSPACE,
        COLLECTION,
        tmp_path,
        files,
        docs_schema,
        local_source_version(tmp_path, files),
        "documents",
    )
    service = _service(provider, binding)
    assert service.ingest(ACTOR, WORKSPACE, COLLECTION) == 1
    assert service.search(ACTOR, WORKSPACE, COLLECTION, "receipt").total == 1
    (tmp_path / "policy.txt").write_text("Changed policy.", encoding="utf-8")
    with pytest.raises(KnowledgeRejected, match="version"):
        service.ingest(ACTOR, WORKSPACE, COLLECTION)
    old_snapshot = service.search(ACTOR, WORKSPACE, COLLECTION, "receipt")
    assert old_snapshot.source_version == binding.source_version
    assert old_snapshot.hits[0].document.text == "Refunds require a receipt."


def test_cross_workspace_denial_precedes_provider_access(tmp_path):
    (tmp_path / "papers.csv").write_text("title,year\nA,2024\n", encoding="utf-8")
    binding = _binding(tmp_path)

    class ExplodingProvider:
        kind = "duckdb/v1"

        def publish(self, binding, documents):
            pytest.fail("provider must not be touched for denied access")

        def documents(self, binding):
            pytest.fail("provider must not be touched for denied access")

        def revoke(self, binding):
            pytest.fail("provider must not be touched for denied access")

    service = _service(
        ExplodingProvider(), binding, authorizer=_AllowWorkspace(OTHER_WORKSPACE)
    )
    with pytest.raises(KnowledgeDenied):
        service.ingest(ACTOR, WORKSPACE, COLLECTION)
    with pytest.raises(KnowledgeDenied):
        service.search(ACTOR, WORKSPACE, COLLECTION, "A")


def test_revocation_is_persisted_and_requires_manage_authority(provider, tmp_path):
    (tmp_path / "papers.csv").write_text("title,year\nPrivate policy,2024\n", encoding="utf-8")
    binding = _binding(tmp_path)
    service = _service(provider, binding)
    service.ingest(ACTOR, WORKSPACE, COLLECTION)

    no_manage = _service(provider, binding, authorizer=_AllowWorkspace(can_manage=False))
    with pytest.raises(KnowledgeDenied):
        no_manage.revoke(ACTOR, WORKSPACE, COLLECTION)

    service.revoke(ACTOR, WORKSPACE, COLLECTION)
    restarted = _service(provider, binding)
    with pytest.raises(KnowledgeDenied):
        restarted.search(ACTOR, WORKSPACE, COLLECTION, "policy")
    with pytest.raises(KnowledgeDenied):
        restarted.ingest(ACTOR, WORKSPACE, COLLECTION)


def test_csv_type_mismatch_and_unbounded_paging_are_rejected(provider, tmp_path):
    (tmp_path / "papers.csv").write_text("title,year\nA,twenty\n", encoding="utf-8")
    service = _service(provider, _binding(tmp_path))
    with pytest.raises(KnowledgeRejected, match="typed schema"):
        service.ingest(ACTOR, WORKSPACE, COLLECTION)

    (tmp_path / "papers.csv").write_text("title,year\nA,2024\n", encoding="utf-8")
    binding = _binding(tmp_path)
    service = _service(provider, binding)
    service.ingest(ACTOR, WORKSPACE, COLLECTION)
    with pytest.raises(KnowledgeRejected, match="bounded"):
        service.search(ACTOR, WORKSPACE, COLLECTION, "A", limit=1000)


def test_path_escape_and_symlink_are_rejected(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside.csv")
    outside.write_text("title,year\nA,2024\n", encoding="utf-8")
    with pytest.raises(KnowledgeRejected, match="escapes"):
        local_source_version(tmp_path, ("../" + outside.name,))

    link = tmp_path / "linked.csv"
    link.symlink_to(outside)
    with pytest.raises(KnowledgeRejected, match="symlinks"):
        local_source_version(tmp_path, ("linked.csv",))


def test_query_requires_terms_and_boolean_bounds_are_not_accepted(provider, tmp_path):
    (tmp_path / "papers.csv").write_text("title,year\nA,2024\n", encoding="utf-8")
    service = _service(provider, _binding(tmp_path))
    service.ingest(ACTOR, WORKSPACE, COLLECTION)
    with pytest.raises(KnowledgeRejected, match="searchable"):
        service.search(ACTOR, WORKSPACE, COLLECTION, "!!!")
    with pytest.raises(KnowledgeRejected, match="bounded"):
        service.search(ACTOR, WORKSPACE, COLLECTION, "A", offset=True)


def test_uningested_and_stale_collection_versions_fail_closed(provider, tmp_path):
    (tmp_path / "papers.csv").write_text("title,year\nA,2024\n", encoding="utf-8")
    binding = _binding(tmp_path)
    service = _service(provider, binding)
    with pytest.raises(KnowledgeRejected, match="not been ingested"):
        service.search(ACTOR, WORKSPACE, COLLECTION, "A")
    service.ingest(ACTOR, WORKSPACE, COLLECTION)
    (tmp_path / "papers.csv").write_text("title,year\nB,2025\n", encoding="utf-8")
    assert service.search(ACTOR, WORKSPACE, COLLECTION, "A").hits[0].document.values[
        "title"
    ] == "A"
    refreshed_binding = _binding(tmp_path)
    stale_service = _service(provider, refreshed_binding)
    with pytest.raises(KnowledgeRejected, match="version"):
        stale_service.search(ACTOR, WORKSPACE, COLLECTION, "A")
