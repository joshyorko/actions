"""Failed generated children retain diagnostics without logical publication."""
import json
import time

import pytest
from action_server_tests import test_logical_full_publication as fixtures
from contract_tests.test_generated_failure import prepare as failed

from actions.server._models import Run, RunStatus
from actions.server.foundry.logical_receipts import derive_summary
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.service import _canonical, _one

local, provider, logical = fixtures.local, fixtures.provider, fixtures.logical
knowledge, generated_knowledge = fixtures.knowledge, fixtures.generated_knowledge
domain, tls_postgres = fixtures.domain, fixtures.tls_postgres
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def publish_failure(g, prepared, owner, caller, wrapper, monkeypatch):
    f = failed(
        owner,
        caller,
        wrapper.ticket,
        logical_summary=derive_summary(prepared).model_dump(mode="json"),
    )
    f.record["launch"]["logicalReads"] = derive_summary(prepared).model_dump(
        mode="json"
    )
    journal = json.loads(_one(g.db, Run, g.fence.run_id).result)
    journal["launch"] = f.record["launch"]
    journal.pop("execution", None)
    with g.db.transaction():
        g.db.update_by_id(Run, g.fence.run_id, {"result": _canonical(journal, 65536)})
    with f.outputs.bind_logical_execution(g.execution, prepared):
        with f.outputs.bind_generated_failure(f.record):
            fixtures.forbid_io(g, monkeypatch)
            result = f.outputs.publish(
                g.actor, g.fence, f.refs, f.record, terminal_status=RunStatus.FAILED
            )
    assert result.status == RunStatus.FAILED
    assert {x["name"] for x in f.record["outputs"]} == {
        "rcc-receipt.json",
        "rcc-stdout.log",
        "rcc-stderr.log",
    }
    for item in prepared.knowledge:
        if item.ingestion is not None:
            assert (
                _one(g.db, RunOutput, str(item.ingestion.output.output_id)).state
                == "provisional"
            )


def test_data_failed_publication_sql_only(domain, monkeypatch):
    g = domain
    owner, caller, wrapper, _ = fixtures.setup(g)
    prepared = fixtures.prepare(g, deadline=time.monotonic() + 60)
    try:
        publish_failure(g, prepared, owner, caller, wrapper, monkeypatch)
    finally:
        g.execution.release(prepared)


def test_knowledge_failed_publication_sql_only(generated_knowledge, monkeypatch):
    g = generated_knowledge
    prepared = fixtures.prepare(g, deadline=time.monotonic() + 60)
    try:
        owner, caller, wrapper, _, _ = fixtures.publish_generated(g, prepared)
        publish_failure(g, prepared, owner, caller, wrapper, monkeypatch)
    finally:
        g.execution.release(prepared)


def test_knowledge_failure_publication_rejects_expired_budget(
    generated_knowledge, monkeypatch
):
    from actions.server.foundry.logical_execution import LogicalReadRejected

    g = generated_knowledge
    deadline = time.monotonic() + 60
    prepared = fixtures.prepare(g, deadline=deadline)
    try:
        owner, caller, wrapper, _, _ = fixtures.publish_generated(g, prepared)
        with monkeypatch.context() as clock:
            clock.setattr(time, "monotonic", lambda: deadline + 1)
            with pytest.raises(LogicalReadRejected):
                publish_failure(g, prepared, owner, caller, wrapper, clock)
        assert _one(g.db, Run, g.fence.run_id).status == RunStatus.RUNNING
        assert all(row.state == "provisional" for row in g.db.all(RunOutput))
    finally:
        g.execution.release(prepared)
