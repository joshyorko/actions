"""Nonterminal ingestion staging and SQL-only canonical publication recheck."""
import dataclasses
import json
import threading

import pytest
from action_server_tests.test_knowledge_execution import case as case_fixture
from action_server_tests.test_knowledge_execution import (
    foundation as foundation_fixture,
)
from action_server_tests.test_knowledge_execution import search, start
from action_server_tests.test_knowledge_execution import versions as versions_fixture

from actions.server._models import Run, RunStatus
from actions.server.data_queries.knowledge_execution import KnowledgeSearch
from actions.server.foundry.provider_registry import _ref_id
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.service import FenceRejected, _one, _transaction

pytest_plugins = ["action_server_tests.foundry_fixtures"]
case = case_fixture
foundation = foundation_fixture
versions = versions_fixture


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def test_preparation_stages_without_completion_or_search_authority(case):
    c = case
    run, fence = start(c)
    prepared = c.service.prepare_ingestion(c.g.actor, fence, threading.Event())
    assert prepared.fence == fence and prepared.binding == c.bindings[0]
    assert prepared.corpus_digest == prepared.receipt["corpusDigest"]
    assert prepared.receipt == c.service._receipt(
        c.bindings[0], fence, prepared.output.handle, prepared.corpus_digest
    )
    assert _one(c.g.db, Run, run.id).status == RunStatus.RUNNING
    assert _one(c.g.db, RunOutput, prepared.output.output_id).state == "provisional"
    _, query_fence, inputs = search(c, prepared.output.handle)
    with pytest.raises(PermissionError):
        c.service.search_for_execution(
            c.g.actor,
            query_fence,
            KnowledgeSearch.model_validate(inputs),
            threading.Event(),
        )
    receipt = prepared.receipt
    receipt["revision"]["collection_id"] = "changed"
    assert prepared.receipt["revision"]["collection_id"] == c.g.spec.collection_id
    with pytest.raises(dataclasses.FrozenInstanceError):
        prepared.corpus_digest = "changed"


def test_recheck_has_no_provider_or_blob_io_and_does_not_publish(case, monkeypatch):
    c = case
    run, fence = start(c)
    prepared = c.service.prepare_ingestion(c.g.actor, fence, threading.Event())

    def no_io(*args, **kwargs):
        raise AssertionError("provider/blob access during recheck")

    monkeypatch.setattr(c.g.providers, "describe", no_io)
    monkeypatch.setattr(c.g.providers, "_read", no_io)
    monkeypatch.setattr(c.versions, "put", no_io)
    monkeypatch.setattr(c.versions, "read", no_io)
    monkeypatch.setattr(c.g.blobs, "stage", no_io)
    monkeypatch.setattr(c.g.blobs, "open", no_io)
    monkeypatch.setattr(c.g.providers, "_verify", no_io)
    with _transaction(c.g.db):
        c.service.recheck_prepared_ingestion(c.g.actor, fence, prepared)
    assert _one(c.g.db, Run, run.id).status == RunStatus.RUNNING
    forged = dataclasses.replace(prepared)
    with pytest.raises(ValueError):
        c.service.recheck_prepared_ingestion(c.g.actor, fence, forged)


@pytest.mark.parametrize(
    "change",
    [
        "cancel",
        "deadline",
        "manage",
        "inspect",
        "disabled",
        "output",
        "expired",
        "durable-cancel",
    ],
)
def test_live_authority_and_fence_changes_reject_prepared_ingestion(case, change):
    c = case
    _, fence = start(c)
    cancelled = threading.Event()
    prepared = c.service.prepare_ingestion(c.g.actor, fence, cancelled)
    if change == "cancel":
        cancelled.set()
    elif change == "deadline":
        prepared.budget.deadline = 0
    elif change in ("manage", "inspect"):
        grant = c.g.collection_grant if change == "manage" else c.g.source_grant
        operations = ["knowledge.read"]
        with c.g.db.transaction():
            c.g.db.execute(
                "UPDATE foundry_access_grant SET operations_json=? WHERE id=?",
                [json.dumps(operations), grant.id],
            )
    elif change == "disabled":
        with c.g.db.transaction():
            c.g.db.execute(
                "UPDATE foundry_provider_availability SET enabled=? WHERE id=?",
                [False, _ref_id(c.g.descriptor.reference)],
            )
    elif change == "expired":
        with c.g.db.transaction():
            c.g.db.execute(
                "UPDATE run_output SET expires_ms=? WHERE id=?",
                ["1", prepared.output.output_id],
            )
    elif change == "durable-cancel":
        c.outputs.cancel(c.g.actor, fence.run_id)
    else:
        with c.g.db.transaction():
            c.g.db.execute(
                "UPDATE run_output SET digest=? WHERE id=?",
                ["sha256:" + "0" * 64, prepared.output.output_id],
            )
    with pytest.raises((ValueError, PermissionError, FenceRejected)):
        c.service.recheck_prepared_ingestion(c.g.actor, fence, prepared)


def test_generated_operation_ids_and_names_are_distinct_and_bounded(case, monkeypatch):
    c = case
    run, fence = start(c)
    operation_ids = []
    original = c.versions.put

    def put(*args, **kwargs):
        operation_ids.append(kwargs["operation_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(c.versions, "put", put)
    first = c.service.prepare_ingestion(
        c.g.actor,
        fence,
        threading.Event(),
        operation_id="generated_first",
        output_name="knowledge-first.json",
    )
    second = c.service.prepare_ingestion(
        c.g.actor,
        fence,
        threading.Event(),
        operation_id="generated_second",
        output_name="knowledge-second.json",
    )
    assert operation_ids == ["generated_first", "generated_second"]
    assert first.output != second.output
    assert (
        _one(c.g.db, RunOutput, first.output.output_id).name == "knowledge-first.json"
    )
    assert (
        _one(c.g.db, RunOutput, second.output.output_id).name == "knowledge-second.json"
    )
    before = len(operation_ids)
    for kwargs in (
        {"operation_id": "bad/id"},
        {"operation_id": "x" * 129},
        {"output_name": "../corpus"},
        {"output_name": "x" * 256},
    ):
        with pytest.raises(ValueError):
            c.service.prepare_ingestion(c.g.actor, fence, threading.Event(), **kwargs)
    assert len(operation_ids) == before
    assert _one(c.g.db, Run, run.id).status == RunStatus.RUNNING


def test_default_preparation_can_publish_exact_standalone_receipt(case, monkeypatch):
    c = case
    run, fence = start(c)
    calls = []
    original = c.versions.put

    def put(*args, **kwargs):
        calls.append(kwargs["operation_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(c.versions, "put", put)
    prepared = c.service.prepare_ingestion(c.g.actor, fence, threading.Event())
    assert calls == [run.id]
    assert prepared.output_name == "knowledge-corpus.json"
    with _transaction(c.g.db):
        c.service.recheck_prepared_ingestion(c.g.actor, fence, prepared)
        c.outputs.publish(c.g.actor, fence, [prepared.output], prepared.receipt)
    assert json.loads(_one(c.g.db, Run, run.id).result)["result"] == prepared.receipt
    _, query_fence, inputs = search(c, prepared.output.handle)
    assert (
        c.service.search_for_execution(
            c.g.actor,
            query_fence,
            KnowledgeSearch.model_validate(inputs),
            threading.Event(),
        )["total"]
        == 1
    )
    with pytest.raises((ValueError, PermissionError, FenceRejected)):
        c.service.recheck_prepared_ingestion(c.g.actor, fence, prepared)


def test_wrong_actor_fence_and_admitted_inputs_cannot_reuse_preparation(case):
    from uuid import uuid4

    from actions.server.run_outputs.types import Actor

    c = case
    _, fence = start(c)
    prepared = c.service.prepare_ingestion(c.g.actor, fence, threading.Event())
    for actor, attempt in (
        (Actor(principal_id=str(uuid4())), fence),
        (c.g.actor, fence.model_copy(update={"epoch": fence.epoch + 1})),
    ):
        with pytest.raises(ValueError):
            c.service.recheck_prepared_ingestion(actor, attempt, prepared)
    _, other = start(c, inputs={"source": "not-authority"})
    with pytest.raises(ValueError, match="caller source inputs"):
        c.service.prepare_ingestion(c.g.actor, other, threading.Event())


def test_verified_empty_host_projection_preserves_actual_admission(case):
    c = case
    run, fence = start(c, inputs={"label": "unrelated declared Action input"})
    with pytest.raises(ValueError, match="caller source inputs"):
        c.service.prepare_ingestion(c.g.actor, fence, threading.Event())

    class Empty(dict):
        pass

    for value in ({"source": "forbidden"}, Empty(), [], ""):
        with pytest.raises(ValueError, match="exact empty mapped"):
            c.service.prepare_ingestion(
                c.g.actor, fence, threading.Event(), mapped_inputs=value
            )
    prepared = c.service.prepare_ingestion(
        c.g.actor, fence, threading.Event(), mapped_inputs={}
    )
    assert prepared.input_mapping_applied
    assert prepared.binding.snapshot == c.ingest
    c.service.recheck_prepared_ingestion(c.g.actor, fence, prepared)
    assert _one(c.g.db, Run, run.id).status == RunStatus.RUNNING
    with c.g.db.transaction():
        c.g.db.execute("UPDATE run SET inputs=? WHERE id=?", ["{}", run.id])
    with pytest.raises(PermissionError):
        c.service.recheck_prepared_ingestion(c.g.actor, fence, prepared)
