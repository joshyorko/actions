import threading
from uuid import uuid4

import pytest

from actions.server.data_queries.knowledge_normalization import normalize_knowledge
from actions.server.data_queries.knowledge_values import KnowledgeRevisionSpec
from actions.server.data_queries.knowledge_versions import DuckDBKnowledgeVersions
from actions.server.data_queries.sealed_sources import ReadBudget
from actions.server.deployments.ids import WorkspaceId
from actions.server.deployments.provider_registry import SourceManifest, SourceObject

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def test_normalized_version_is_retained(tmp_path, foundry_package_store):
    blobs = foundry_package_store
    seal = blobs.stage([b"First document"]).receipt
    source = SourceManifest(
        kind="knowledge",
        objects=(SourceObject(name="first", digest=seal.digest, size=seal.size),),
    )
    spec = KnowledgeRevisionSpec(
        workspace_id=WorkspaceId(root=str(uuid4())),
        collection_id=str(uuid4()),
        source_revision=source.revision_id,
    )
    corpus = normalize_knowledge(
        spec, source, blobs, {seal.digest: seal}, ReadBudget(30000, threading.Event())
    )
    import duckdb

    store = DuckDBKnowledgeVersions(
        lambda: duckdb.connect(str(tmp_path / "versions.duckdb"))
    )
    store.provision()
    store.put(
        corpus,
        operation_id="operation-one",
        budget=ReadBudget(30000, threading.Event()),
    )
    assert (
        store.read(spec.reference, budget=ReadBudget(30000, threading.Event()))
        == corpus
    )


def build(blobs, raw, *, csv=False, changes=None):
    from actions.server.data_queries.knowledge_values import KnowledgeDocumentField

    seal = blobs.stage([raw]).receipt
    source = SourceManifest(
        kind="knowledge",
        objects=(SourceObject(name="source", digest=seal.digest, size=seal.size),),
    )
    spec = KnowledgeRevisionSpec(
        workspace_id=WorkspaceId(root=str(uuid4())),
        collection_id=str(uuid4()),
        source_revision=source.revision_id,
        source_format="typed-csv/v1" if csv else "utf8-documents/v1",
        document_fields=(
            KnowledgeDocumentField(name="name", kind="string"),
            KnowledgeDocumentField(name="number", kind="integer"),
        )
        if csv
        else (),
    )
    if changes:
        spec = KnowledgeRevisionSpec.model_validate_json(
            spec.model_copy(update=changes).model_dump_json()
        )
    return spec, source, {seal.digest: seal}


def normalize(blobs, inputs):
    return normalize_knowledge(
        inputs[0], inputs[1], blobs, inputs[2], ReadBudget(30000, threading.Event())
    )


@pytest.mark.parametrize("raw", [b"\xff", b"\xef\xbb\xbfbom", b"a\0b", b""])
def test_documents_invalid_bytes(foundry_package_store, raw):
    with pytest.raises(ValueError):
        normalize(foundry_package_store, build(foundry_package_store, raw))


@pytest.mark.parametrize(
    "raw",
    [
        b"name,name\na,1\n",
        b"number,name\n1,a\n",
        b"name,number,extra\na,1,x\n",
        b"name,number\na,1,x\n",
        b"name,number\na\n",
        b"name,number\n\\N,1\n",
        b"name,number\na,\\N\n",
        b"name,number\na,true\n",
        b"name,number\na,01\n",
        b"name,number\na,9007199254740992\n",
        b'name,number\n"unterminated,1\n',
        b'name,number\n"a"junk,1\n',
        b"name,number\na\0,1\n",
        b"\xef\xbb\xbfname,number\na,1\n",
    ],
)
def test_csv_closed_schema_and_values(foundry_package_store, raw):
    with pytest.raises(ValueError):
        normalize(foundry_package_store, build(foundry_package_store, raw, csv=True))


def test_csv_deterministic_typed_corpus(foundry_package_store):
    from actions.server.data_queries.knowledge_normalization import validate_corpus

    inputs = build(
        foundry_package_store, b'name,number\n"line\nvalue",1\n,2\n', csv=True
    )
    first = normalize(foundry_package_store, inputs)
    assert first == normalize(foundry_package_store, inputs)
    spec, documents = validate_corpus(first)
    assert spec == inputs[0]
    assert documents[0]["values"] == {"name": "line\nvalue", "number": 1}
    assert documents[1]["values"] == {"name": "", "number": 2}


def test_bounds_before_open_and_total_rows(foundry_package_store, monkeypatch):
    blobs = foundry_package_store
    inputs = build(blobs, b"abcd", changes={"max_document_bytes": 3})

    def forbidden(*args):
        raise AssertionError("oversized source was opened")

    monkeypatch.setattr(blobs, "open", forbidden)
    with pytest.raises(ValueError, match="byte bound"):
        normalize(blobs, inputs)


def test_row_overflow_rejects_whole_corpus(foundry_package_store):
    inputs = build(
        foundry_package_store,
        b"name,number\na,1\nb,2\n",
        csv=True,
        changes={"max_documents": 1},
    )
    with pytest.raises(ValueError, match="count"):
        normalize(foundry_package_store, inputs)


def test_cancel_before_source_open(foundry_package_store):
    inputs = build(foundry_package_store, b"document")
    event = threading.Event()
    event.set()
    with pytest.raises(ValueError, match="cancelled"):
        normalize_knowledge(
            inputs[0],
            inputs[1],
            foundry_package_store,
            inputs[2],
            ReadBudget(30000, event),
        )


def test_missing_seal_and_traversal_refused(foundry_package_store):
    spec, source, seals = build(foundry_package_store, b"document")
    with pytest.raises(ValueError):
        normalize_knowledge(
            spec,
            source,
            foundry_package_store,
            {},
            ReadBudget(30000, threading.Event()),
        )
    forged = source.model_copy(
        update={
            "objects": (source.objects[0].model_copy(update={"name": "../secret"}),)
        }
    )
    with pytest.raises(ValueError):
        normalize_knowledge(
            spec,
            forged,
            foundry_package_store,
            seals,
            ReadBudget(30000, threading.Event()),
        )


def test_retains_old_version_and_replay_conflict(tmp_path, foundry_package_store):
    import duckdb

    blobs = foundry_package_store
    inputs = build(blobs, b"original")
    first = normalize(blobs, inputs)
    changed = inputs[0].model_copy(update={"max_results": 2})
    second = normalize(blobs, (changed, inputs[1], inputs[2]))
    store = DuckDBKnowledgeVersions(
        lambda: duckdb.connect(str(tmp_path / "retained.duckdb"))
    )
    store.provision()

    def budget():
        return ReadBudget(30000, threading.Event())

    store.put(first, operation_id="one", budget=budget())
    store.put(first, operation_id="one", budget=budget())
    with pytest.raises(ValueError, match="conflicts"):
        store.put(second, operation_id="one", budget=budget())
    store.put(second, operation_id="two", budget=budget())
    assert store.read(inputs[0].reference, budget=budget()) == first
    assert store.read(changed.reference, budget=budget()) == second
    with pytest.raises(ValueError):
        store.read(
            changed.reference.model_copy(update={"collection_id": str(uuid4())}),
            budget=budget(),
        )


def test_no_implicit_provision_and_corruption_refused(tmp_path, foundry_package_store):
    import duckdb

    inputs = build(foundry_package_store, b"original")
    corpus = normalize(foundry_package_store, inputs)
    path = str(tmp_path / "corrupt.duckdb")
    store = DuckDBKnowledgeVersions(lambda: duckdb.connect(path))

    def budget():
        return ReadBudget(30000, threading.Event())

    with pytest.raises(ValueError):
        store.put(corpus, operation_id="one", budget=budget())
    store.provision()
    store.put(corpus, operation_id="one", budget=budget())
    c = duckdb.connect(path)
    c.execute("UPDATE actions_knowledge_documents SET document_json='{}'")
    c.close()
    with pytest.raises(ValueError):
        store.read(inputs[0].reference, budget=budget())
    with pytest.raises(ValueError):
        store.put(corpus, operation_id="one", budget=budget())


def test_failed_document_write_rolls_back_whole_version(
    tmp_path, foundry_package_store, monkeypatch
):
    import duckdb

    inputs = build(foundry_package_store, b"original")
    corpus = normalize(foundry_package_store, inputs)
    path = str(tmp_path / "rollback.duckdb")
    store = DuckDBKnowledgeVersions(lambda: duckdb.connect(path))
    store.provision()
    execute = store._execute

    def fail(connection, sql, parameters=()):
        if sql.startswith("INSERT INTO actions_knowledge_documents"):
            raise RuntimeError("synthetic interrupted write")
        return execute(connection, sql, parameters)

    monkeypatch.setattr(store, "_execute", fail)
    with pytest.raises(ValueError, match="unavailable"):
        store.put(
            corpus, operation_id="first", budget=ReadBudget(30000, threading.Event())
        )
    connection = duckdb.connect(path)
    for table in (
        "actions_knowledge_versions",
        "actions_knowledge_documents",
        "actions_knowledge_operations",
    ):
        assert connection.execute("SELECT count(*) FROM " + table).fetchone() == (0,)
    connection.close()
    monkeypatch.setattr(store, "_execute", execute)
    store.put(corpus, operation_id="first", budget=ReadBudget(30000, threading.Event()))


def test_corpus_validation_does_not_accept_claimed_digest(foundry_package_store):
    import json

    from actions.server.data_queries.knowledge_normalization import (
        NormalizedKnowledge,
        _digest,
        validate_corpus,
    )
    from actions.server.data_queries.sealed_sources import json_bytes

    corpus = normalize(foundry_package_store, build(foundry_package_store, b"original"))
    value = json.loads(corpus.raw)
    value["documents"][0]["ordinal"] = True
    raw = json_bytes(value)
    with pytest.raises(ValueError):
        validate_corpus(NormalizedKnowledge(raw, _digest(raw)))
    with pytest.raises(ValueError):
        validate_corpus(
            NormalizedKnowledge(corpus.raw + b" ", _digest(corpus.raw + b" "))
        )
    value = json.loads(corpus.raw)
    value["documents"].append(value["documents"][0])
    raw = json_bytes(value)
    with pytest.raises(ValueError):
        validate_corpus(NormalizedKnowledge(raw, _digest(raw)))


def test_expired_total_budget_refuses_before_connection(foundry_package_store):
    corpus = normalize(foundry_package_store, build(foundry_package_store, b"original"))

    def forbidden():
        raise AssertionError("expired operation connected")

    store = DuckDBKnowledgeVersions(forbidden)
    budget = ReadBudget(30000, threading.Event())
    budget.deadline = 0
    with pytest.raises(ValueError, match="deadline"):
        store.put(corpus, operation_id="first", budget=budget)


def test_retained_version_reopens_in_fresh_process(tmp_path, foundry_package_store):
    import subprocess
    import sys

    import duckdb

    inputs = build(foundry_package_store, b"persisted document")
    corpus = normalize(foundry_package_store, inputs)
    path = str(tmp_path / "reopened.duckdb")
    store = DuckDBKnowledgeVersions(lambda: duckdb.connect(path))
    store.provision()
    store.put(
        corpus, operation_id="original", budget=ReadBudget(30000, threading.Event())
    )
    script = """
import sys, threading, duckdb
from actions.server.data_queries.knowledge_versions import DuckDBKnowledgeVersions
from actions.server.data_queries.knowledge_values import KnowledgeRevisionRef
from actions.server.data_queries.sealed_sources import ReadBudget
store= DuckDBKnowledgeVersions(lambda: duckdb.connect(sys.argv[1]))
print(store.read(KnowledgeRevisionRef.model_validate_json(sys.argv[2]), budget=ReadBudget(30000,threading.Event())).digest)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, path, inputs[0].reference.model_dump_json()],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stdout.strip() == corpus.digest
