"""Synthetic generated search publication boundaries; no actual RCC evidence."""
# Imported pytest fixtures are intentionally requested by same-named parameters.
# ruff: noqa: F811
import json
import threading
import time
from types import SimpleNamespace

import pytest
from action_server_tests.test_generated_knowledge import admit_search
from action_server_tests.test_generated_knowledge import (
    generated_knowledge as generated_knowledge,
)
from action_server_tests.test_generated_knowledge import knowledge as knowledge
from action_server_tests.test_generated_knowledge import local as local
from action_server_tests.test_generated_knowledge import provider as provider
from action_server_tests.test_generated_knowledge import publish_generated
from action_server_tests.test_logical_full_publication import forbid_io

from actions.server._models import Run, RunStatus
from actions.server.data_queries.knowledge_values import knowledge_grant_subject
from actions.server.run_outputs.service import (
    FenceRejected,
    RunOutputControlPlane,
    _one,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def prepare(g, event=None):
    return g.execution.prepare(
        g.actor,
        g.fence,
        cancelled=event or threading.Event(),
        deadline=time.monotonic() + 20,
    )


def ingest(g):
    prepared = prepare(g)
    _, _, wrapper, refs, result = publish_generated(g, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        wrapper.publish(g.actor, g.fence, refs, result)
    source = SimpleNamespace(
        fence=g.fence,
        snapshot=prepared.snapshot,
        handle=prepared.knowledge[0].evidence.corpus_handle,
        output_id=prepared.knowledge[0].ingestion.output.output_id,
    )
    g.execution.release(prepared)
    return source


def expire_logs(g, source):
    with g.db.transaction():
        g.db.execute(
            "UPDATE run_output SET expires_ms=? WHERE run_id=? AND id<>?",
            ["1", source.fence.run_id, source.output_id],
        )


@pytest.mark.parametrize(
    "change",
    [
        "corpus-expiry",
        "source-run",
        "source-attempt",
        "source-read",
        "collection-read",
        "cancel",
        "deadline",
    ],
)
def test_search_final_authority_changes_reject(
    generated_knowledge, monkeypatch, change
):
    g = generated_knowledge
    source = ingest(g)
    admit_search(g, source.handle)
    event = threading.Event()
    prepared = prepare(g, event)
    _, _, wrapper, refs, result = publish_generated(g, prepared)
    try:
        with wrapper.bind_logical_execution(g.execution, prepared):
            with g.db.transaction():
                if change == "corpus-expiry":
                    g.db.execute(
                        "UPDATE run_output SET expires_ms=? WHERE id=?",
                        ["1", source.output_id],
                    )
                elif change == "source-run":
                    g.db.execute(
                        "UPDATE run SET result=? WHERE id=?",
                        ["{}", source.fence.run_id],
                    )
                elif change == "source-attempt":
                    g.db.execute(
                        "UPDATE run_attempt SET state=? WHERE id=?",
                        ["failed", source.fence.attempt_id],
                    )
                elif change == "source-read":
                    RunOutputControlPlane(g.db, capabilities=g.registry).grant(
                        g.actor, source.snapshot.deployment, {"execute", "cancel"}
                    )
                elif change == "collection-read":
                    g.db.execute(
                        "UPDATE foundry_access_grant SET operations_json=? WHERE subject_id=?",
                        [
                            json.dumps(["knowledge.manage"]),
                            knowledge_grant_subject(g.collection),
                        ],
                    )
                elif change == "cancel":
                    event.set()
                else:
                    prepared.knowledge[0].budget.cancelled.deadline = 0
            forbid_io(g, monkeypatch)
            with pytest.raises((ValueError, PermissionError, FenceRejected)):
                with g.db.transaction():
                    wrapper.publish(g.actor, g.fence, refs, result)
        assert _one(g.db, Run, g.fence.run_id).status != RunStatus.PASSED
    finally:
        g.execution.release(prepared)


@pytest.mark.parametrize("expired_logs", ["never", "before-prepare", "after-prepare"])
def test_search_full_publish_sql_only_with_independent_corpus_lifetime(
    generated_knowledge, monkeypatch, expired_logs
):
    g = generated_knowledge
    source = ingest(g)
    if expired_logs == "before-prepare":
        expire_logs(g, source)
    admit_search(g, source.handle)
    prepared = prepare(g)
    _, _, wrapper, refs, result = publish_generated(g, prepared)
    try:
        with wrapper.bind_logical_execution(g.execution, prepared):
            if expired_logs == "after-prepare":
                expire_logs(g, source)
            forbid_io(g, monkeypatch)
            with g.db.transaction():
                published = wrapper.publish(g.actor, g.fence, refs, result)
            assert published.status == RunStatus.PASSED
    finally:
        g.execution.release(prepared)


def test_expired_source_logs_still_require_sealed_metadata(generated_knowledge):
    g = generated_knowledge
    source = ingest(g)
    expire_logs(g, source)
    with g.db.transaction():
        g.db.execute(
            "UPDATE run_output SET digest=? WHERE run_id=? AND id<>?",
            ["sha256:" + "f" * 64, source.fence.run_id, source.output_id],
        )
    admit_search(g, source.handle)
    with pytest.raises((ValueError, PermissionError, FenceRejected)):
        prepare(g)
