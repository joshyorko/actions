"""Real common SQL, retained corpora and provider engines; not installed clients."""
import json
import os
import threading
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.run_outputs.test_service import insert_action, snapshot
from action_server_tests.test_knowledge_foundation import foundation as _foundation
from action_server_tests.test_knowledge_foundation import register

from actions.server._models import Run, RunStatus
from actions.server.data_queries.knowledge_execution import (
    KnowledgeExecution,
    KnowledgeExecutionBinding,
    KnowledgeSearch,
)
from actions.server.data_queries.knowledge_versions import (
    DuckDBKnowledgeVersions,
    PostgreSQLKnowledgeVersions,
)
from actions.server.data_queries.sealed_sources import ReadBudget
from actions.server.run_outputs.models import RunAttempt, RunOutput
from actions.server.run_outputs.service import (
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
    _one,
)
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]
foundation = _foundation


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.fixture(params=["duckdb", "postgresql"])
def versions(request, tmp_path):
    if request.param == "duckdb":
        import duckdb

        path = str(tmp_path / "corpus.duckdb")
        store = DuckDBKnowledgeVersions(lambda: duckdb.connect(path))
        store.provision()
        store.test_location = path
        store.test_postgres = False
        yield store
        return
    import psycopg
    from action_server_tests.test_database_shared import _postgresql_schema_url
    from psycopg import sql

    base = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
    if not base:
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            pytest.fail("owned PostgreSQL fixture required")
        pytest.skip("owned PostgreSQL fixture not configured")
    schema = "knowledge_execution_" + uuid4().hex
    with psycopg.connect(base, autocommit=True) as owner:
        owner.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        location = _postgresql_schema_url(base, schema)
        store = PostgreSQLKnowledgeVersions(lambda: psycopg.connect(location))
        store.provision()
        store.test_location = location
        store.test_postgres = True
        try:
            yield store
        finally:
            owner.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )


@pytest.fixture
def case(foundation, versions):
    g = foundation
    register(g)
    snaps = []
    for operation in ["ingest", "search"]:
        raw = snapshot(str(g.refs.workspace.root)).model_dump(mode="json")
        raw["action_id"] = "knowledge-" + operation
        raw["capability"]["capability_id"] = "knowledge-" + operation
        from actions.server.run_outputs.types import ExecutionSnapshot

        snap = ExecutionSnapshot.model_validate(raw)
        insert_action(g.db, snap)
        snaps.append(snap)
    control = RunOutputControlPlane(g.db)
    outputs = RunOutputService(g.db, {s.provider_key: g.blobs for s in snaps})
    for snap in snaps:
        control.register(snap)
        control.grant(g.actor, snap.deployment, {"execute", "read", "cancel"})
    seals = {
        digest: seal
        for (workspace, digest), seal in g.providers._evidence._seals.items()
    }
    bindings = tuple(
        KnowledgeExecutionBinding(
            snap,
            g.spec.reference,
            g.descriptor.reference,
            g.source,
            g.blobs,
            seals,
            versions,
            operation,
        )
        for snap, operation in zip(snaps, ["ingest", "search"])
    )
    service = KnowledgeExecution(outputs, g.authority, bindings)
    yield SimpleNamespace(
        g=g,
        outputs=outputs,
        control=control,
        bindings=bindings,
        service=service,
        versions=versions,
        ingest=snaps[0],
        search=snaps[1],
    )


def start(c, operation="ingest", inputs=None, key=None):
    snap = getattr(c, operation)
    run = c.outputs.admit(c.g.actor, snap, inputs or {}, key or str(uuid4()))
    return run, c.outputs.claim(run.id, str(uuid4()), lease_seconds=60)


def ingest(c):
    run, fence = start(c)
    return run, fence, c.service.execute(c.g.actor, fence, threading.Event())


def search(c, handle, **changes):
    inputs = dict(ingestion_handle=handle, query="knowledge", limit=20, offset=0)
    inputs.update(changes)
    run, fence = start(c, "search", inputs)
    return run, fence, inputs


def test_ingest_search_reconstruct_and_retained_read(case):
    c = case
    run, fence, handle = ingest(c)
    assert _one(c.g.db, Run, run.id).status == RunStatus.PASSED
    assert _one(c.g.db, RunAttempt, fence.attempt_id).state == "succeeded"
    resumed = KnowledgeExecution(c.outputs, c.g.authority, c.bindings)
    query, query_fence, inputs = search(c, handle)
    result = resumed.search_for_execution(
        c.g.actor,
        query_fence,
        KnowledgeSearch.model_validate(inputs),
        threading.Event(),
    )
    assert result["total"] == 1
    assert result["hits"][0]["text"] == "Bounded knowledge source"
    output = resumed.execute(c.g.actor, query_fence, threading.Event())
    with c.outputs.resolve(c.g.actor, c.ingest.workspace_id, output) as stream:
        assert json.loads(stream.read()) == result
    assert len(c.g.db.all(Run)) == 2


def test_provider_write_without_publication_is_not_search_ready(case, monkeypatch):
    c = case
    run, fence = start(c)
    original = c.outputs.publish

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic publication interruption")

    monkeypatch.setattr(c.outputs, "publish", fail)
    with pytest.raises(RuntimeError, match="interruption"):
        c.service.execute(c.g.actor, fence, threading.Event())
    assert c.versions.read(
        c.g.spec.reference, budget=ReadBudget(1000, threading.Event())
    )
    assert _one(c.g.db, Run, run.id).status == RunStatus.RUNNING
    pending = c.g.db.all(RunOutput, where="run_id=?", values=[run.id])
    from actions.server.run_outputs.types import OutputRef

    handle = OutputRef(
        workspace_id=c.ingest.workspace_id, run_id=run.id, output_id=pending[0].id
    ).handle
    _, query_fence, inputs = search(c, handle)
    with pytest.raises(PermissionError):
        c.service.search_for_execution(
            c.g.actor,
            query_fence,
            KnowledgeSearch.model_validate(inputs),
            threading.Event(),
        )
    monkeypatch.setattr(c.outputs, "publish", original)
    final = c.service.execute(c.g.actor, fence, threading.Event())
    assert final != handle
    assert _one(c.g.db, Run, run.id).status == RunStatus.PASSED
    assert len(c.g.db.all(RunAttempt, where="run_id=?", values=[run.id])) == 1
    assert (
        len(
            [
                o
                for o in c.g.db.all(RunOutput, where="run_id=?", values=[run.id])
                if o.state == "final"
            ]
        )
        == 1
    )


@pytest.mark.parametrize("revocation", ["collection", "source", "run"])
def test_live_read_revocation_blocks_search(case, revocation):
    c = case
    _, _, handle = ingest(c)
    _, fence, inputs = search(c, handle)
    if revocation == "run":
        c.control.revoke(c.g.actor, c.ingest.deployment)
    else:
        row = c.g.collection_grant if revocation == "collection" else c.g.source_grant
        with c.g.db.transaction():
            c.g.db.execute("DELETE FROM foundry_access_grant WHERE id=?", [row.id])
    with pytest.raises(PermissionError):
        c.service.search_for_execution(
            c.g.actor, fence, KnowledgeSearch.model_validate(inputs), threading.Event()
        )


def test_manage_revocation_after_provider_write_cannot_publish(case, monkeypatch):
    c = case
    original = c.versions.put

    def put(*args, **kwargs):
        result = original(*args, **kwargs)
        with c.g.db.transaction():
            c.g.db.execute(
                "UPDATE foundry_access_grant SET operations_json=? WHERE id=?",
                [json.dumps(["knowledge.read"]), c.g.collection_grant.id],
            )
        return result

    monkeypatch.setattr(c.versions, "put", put)
    run, fence = start(c)
    with pytest.raises(PermissionError):
        c.service.execute(c.g.actor, fence, threading.Event())
    assert _one(c.g.db, Run, run.id).status == RunStatus.RUNNING


def test_stale_cancelled_wrong_binding_and_cross_actor_refuse(case):
    c = case
    run, fence = start(c)
    with pytest.raises(FenceRejected):
        c.service.execute(
            c.g.actor,
            fence.model_copy(update={"owner_id": str(uuid4())}),
            threading.Event(),
        )
    with pytest.raises(PermissionError):
        c.service.execute(Actor(principal_id=str(uuid4())), fence, threading.Event())
    no_bindings = KnowledgeExecution(c.outputs, c.g.authority, ())
    with pytest.raises(PermissionError):
        no_bindings.execute(c.g.actor, fence, threading.Event())
    c.outputs.cancel(c.g.actor, run.id)
    with pytest.raises(FenceRejected):
        c.service.execute(c.g.actor, fence, threading.Event())
    assert not c.g.db.all(RunOutput, where="run_id=?", values=[run.id])


@pytest.mark.parametrize(
    "change", [{"query": " "}, {"query": "\x00"}, {"offset": 100001}, {"limit": 101}]
)
def test_closed_search_input_limits(case, change):
    c = case
    _, _, handle = ingest(c)
    _, fence, inputs = search(c, handle, **change)
    with pytest.raises(ValueError):
        c.service.search_for_execution(
            c.g.actor, fence, KnowledgeSearch.model_validate(inputs), threading.Event()
        )


@pytest.mark.parametrize("mutation", ["digest", "null", "extra", "fence"])
def test_tampered_publication_is_not_readiness(case, mutation):
    c = case
    run, _, handle = ingest(c)
    record = _one(c.g.db, Run, run.id)
    value = json.loads(record.result)
    if mutation == "digest":
        value["result"]["corpusDigest"] = "sha256:" + "0" * 64
    elif mutation == "null":
        value = None
    elif mutation == "extra":
        value["result"]["unexpected"] = True
    else:
        value["result"]["fence"]["owner_id"] = str(uuid4())
    with c.g.db.transaction():
        c.g.db.execute(
            "UPDATE run SET result=? WHERE id=?", [json.dumps(value), run.id]
        )
    _, fence, inputs = search(c, handle)
    with pytest.raises(PermissionError):
        c.service.search_for_execution(
            c.g.actor, fence, KnowledgeSearch.model_validate(inputs), threading.Event()
        )


def test_search_reopens_in_independent_process(case, tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    c = case
    _, _, handle = ingest(c)
    _, fence, inputs = search(c, handle)
    configuration = {
        "database": str(c.g.db.db_path),
        "blobs": os.readlink("/proc/self/fd/" + str(c.g.blobs._root)),
        "actor": c.g.actor.model_dump(mode="json"),
        "fence": fence.model_dump(mode="json"),
        "inputs": inputs,
        "revision": c.g.spec.reference.model_dump(mode="json"),
        "provider": c.g.descriptor.reference.model_dump(mode="json"),
        "source": c.g.source.model_dump(mode="json"),
        "seals": {k: v.model_dump(mode="json") for k, v in c.bindings[0].seals.items()},
        "snapshots": [b.snapshot.model_dump(mode="json") for b in c.bindings],
        "store_location": c.versions.test_location,
        "postgres": c.versions.test_postgres,
    }
    private = tmp_path / "private-reopen.json"
    private.write_text(json.dumps(configuration))
    private.chmod(0o600)
    helper = Path(__file__).with_name("knowledge_execution_child.py")
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[2] / "src"))
    result = subprocess.run(
        [sys.executable, str(helper), str(private)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, "independent Knowledge consumer failed"
    value = json.loads(result.stdout)
    assert value["result"]["total"] == 1
    assert value["source"] == str(
        Path(__file__).parents[2]
        / "src/actions/server/data_queries/knowledge_execution.py"
    )


def test_provider_bytes_and_retention_do_not_become_implicit_readiness(
    case, monkeypatch
):
    c = case
    _, _, handle = ingest(c)
    _, fence, inputs = search(c, handle)
    original = c.versions.read
    monkeypatch.setattr(c.versions, "read", lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="provider and published"):
        c.service.search_for_execution(
            c.g.actor, fence, KnowledgeSearch.model_validate(inputs), threading.Event()
        )
    monkeypatch.setattr(c.versions, "read", original)
    from actions.server.run_outputs.types import output_id_from_handle

    with c.g.db.transaction():
        c.g.db.execute(
            "UPDATE run_output SET expires_ms=? WHERE id=?",
            ["0", output_id_from_handle(handle)],
        )
    with pytest.raises(PermissionError):
        c.service.search_for_execution(
            c.g.actor, fence, KnowledgeSearch.model_validate(inputs), threading.Event()
        )


def test_ingestion_admission_replay_keeps_same_run_and_publication(case):
    c = case
    run, fence = start(c, key="stable-ingestion")
    handle = c.service.execute(c.g.actor, fence, threading.Event())
    replay = c.outputs.admit(c.g.actor, c.ingest, {}, "stable-ingestion")
    assert replay.id == run.id
    assert replay.status == RunStatus.PASSED
    assert len(c.g.db.all(RunAttempt, where="run_id=?", values=[run.id])) == 1
    _, query_fence, inputs = search(c, handle)
    assert (
        c.service.search_for_execution(
            c.g.actor,
            query_fence,
            KnowledgeSearch.model_validate(inputs),
            threading.Event(),
        )["total"]
        == 1
    )


def test_search_local_cancel_after_staging_refuses_publication(case, monkeypatch):
    c = case
    _, _, handle = ingest(c)
    run, fence, _ = search(c, handle)
    cancelled = threading.Event()
    original = c.outputs.stage

    def stage(*args, **kwargs):
        output = original(*args, **kwargs)
        cancelled.set()
        return output

    monkeypatch.setattr(c.outputs, "stage", stage)
    with pytest.raises(ValueError, match="cancel"):
        c.service.execute(c.g.actor, fence, cancelled)
    assert _one(c.g.db, Run, run.id).status == RunStatus.RUNNING
