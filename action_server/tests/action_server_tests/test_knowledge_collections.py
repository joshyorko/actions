import uuid

import pytest

from actions.server.data_queries.knowledge import (
    KnowledgeDenied,
    KnowledgeField,
    KnowledgeRejected,
    KnowledgeSchema,
    KnowledgeCollectionService,
    LocalCollection,
    LocalFilesKnowledgeProvider,
    local_source_version,
)
from actions.server.run_outputs.types import Actor


WORKSPACE = str(uuid.UUID("10000000-0000-4000-8000-000000000001"))
OTHER_WORKSPACE = str(uuid.UUID("20000000-0000-4000-8000-000000000002"))
COLLECTION = str(uuid.UUID("30000000-0000-4000-8000-000000000003"))
ACTOR = Actor(principal_id=str(uuid.UUID("40000000-0000-4000-8000-000000000004")))
SCHEMA = KnowledgeSchema(
    fields=(KnowledgeField(name="title", kind="text"), KnowledgeField(name="year", kind="integer"))
)


class _AllowWorkspace:
    def __init__(self, workspace_id=WORKSPACE):
        self.workspace_id = workspace_id

    def can_read(self, actor, workspace_id, collection_id):
        return actor == ACTOR and workspace_id == self.workspace_id


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


def test_csv_ingestion_has_typed_schema_provenance_and_deterministic_pages(tmp_path):
    (tmp_path / "papers.csv").write_text(
        "title,year\nAlpha knowledge,2024\nKnowledge beta,2023\nKnowledge alpha,2022\n",
        encoding="utf-8",
    )
    binding = _binding(tmp_path)
    service = KnowledgeCollectionService(
        _AllowWorkspace(), LocalFilesKnowledgeProvider(), (binding,)
    )

    first = service.search(ACTOR, WORKSPACE, COLLECTION, "knowledge alpha", limit=1)
    second = service.search(
        ACTOR, WORKSPACE, COLLECTION, "knowledge alpha", offset=1, limit=1
    )

    assert first.total == second.total == 3
    assert first.source_version == binding.source_version
    assert first.provider == "local-files/v1"
    assert first.schema == SCHEMA
    assert first.hits[0].document.document_id == "papers.csv#2"
    assert second.hits[0].document.document_id == "papers.csv#4"
    assert first.hits[0].document.values == {"title": "Alpha knowledge", "year": 2024}
    assert first.hits[0].document.metadata == {
        "source_file": "papers.csv",
        "source_row": "2",
    }


def test_document_ingestion_and_changed_source_version(tmp_path):
    (tmp_path / "policy.txt").write_text("Refunds require a receipt.", encoding="utf-8")
    docs_schema = KnowledgeSchema(fields=(KnowledgeField(name="body", kind="text"),))
    files = ("policy.txt",)
    binding = LocalCollection(
        WORKSPACE, COLLECTION, tmp_path, files, docs_schema,
        local_source_version(tmp_path, files), "documents"
    )
    provider = LocalFilesKnowledgeProvider()
    assert provider.ingest(binding)[0].text == "Refunds require a receipt."
    (tmp_path / "policy.txt").write_text("Changed policy.", encoding="utf-8")
    with pytest.raises(KnowledgeRejected, match="version"):
        provider.ingest(binding)


def test_cross_workspace_and_revoked_binding_deny_before_provider_access(tmp_path):
    (tmp_path / "papers.csv").write_text("title,year\nA,2024\n", encoding="utf-8")
    binding = _binding(tmp_path)

    class ExplodingProvider:
        def ingest(self, binding):
            pytest.fail("provider must not be touched for denied access")

    service = KnowledgeCollectionService(_AllowWorkspace(OTHER_WORKSPACE), ExplodingProvider(), (binding,))
    with pytest.raises(KnowledgeDenied):
        service.search(ACTOR, WORKSPACE, COLLECTION, "A")

    revoked = _binding(tmp_path, revoked=True)
    revoked_service = KnowledgeCollectionService(_AllowWorkspace(), ExplodingProvider(), (revoked,))
    with pytest.raises(KnowledgeDenied):
        revoked_service.search(ACTOR, WORKSPACE, COLLECTION, "A")


def test_csv_type_mismatch_and_unbounded_paging_are_rejected(tmp_path):
    (tmp_path / "papers.csv").write_text("title,year\nA,twenty\n", encoding="utf-8")
    service = KnowledgeCollectionService(
        _AllowWorkspace(), LocalFilesKnowledgeProvider(), (_binding(tmp_path),)
    )
    with pytest.raises(KnowledgeRejected, match="typed schema"):
        service.search(ACTOR, WORKSPACE, COLLECTION, "A")
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


def test_query_requires_terms_and_boolean_bounds_are_not_accepted(tmp_path):
    (tmp_path / "papers.csv").write_text("title,year\nA,2024\n", encoding="utf-8")
    service = KnowledgeCollectionService(
        _AllowWorkspace(), LocalFilesKnowledgeProvider(), (_binding(tmp_path),)
    )
    with pytest.raises(KnowledgeRejected, match="searchable"):
        service.search(ACTOR, WORKSPACE, COLLECTION, "!!!")
    with pytest.raises(KnowledgeRejected, match="bounded"):
        service.search(ACTOR, WORKSPACE, COLLECTION, "A", offset=True)
