"""Real pinned RCC business execution over reviewed SQL Work Items and Run fences."""
import json
import os
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from action_server_tests import test_generated_work_item_execution as fixtures
from actions.work_items import State
from actions.work_items._fencing import ClaimRejected

from actions.server._models import RunStatus
from actions.server.deployments.package_revision_compiler import (
    load_prepared_rcc_environment,
)
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.run_outputs.service import FenceRejected
from actions.server.run_outputs.types import OutputRef

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = fixtures.pytestmark


@pytest.mark.integration_test
@pytest.mark.skipif(
    not os.environ.get("ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"),
    reason="exact task-owned pinned RCC preparation required",
)
def test_reviewed_generated_summary_executes_with_real_dual_fences(
    reviewed, foundry_package_store, tmp_path
):
    service, actor, proposal = fixtures.setup_generated(
        reviewed, foundry_package_store, real=True
    )
    approved = service.reviews.decide(actor, service.scope, proposal, "approve")
    claim = service.reviews.queue(service.scope).reserve_fenced(
        str(uuid4()), lease_seconds=30
    )
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=30)
    outputs = service.outputs(actor, ticket)
    prepared = load_prepared_rcc_environment(
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
    )
    execute = GeneratedRccExecution(
        service.base.capabilities,
        outputs,
        prepared,
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]),
        tmp_path / "execution",
    )
    complete = execute.execute(actor, ticket.fence, cancelled=Event())
    assert complete.status == RunStatus.PASSED
    assert (
        service.reviews.queue(service.scope).list_items()[0]["state"]
        == State.DONE.value
    )
    assert approved.work_item_id == ticket.claim.item_id
    envelope = json.loads(complete.result)
    assert json.loads(envelope["result"]["actionResult"]) == {
        "invoice_count": 2,
        "total_cents": 12900,
    }
    output = OutputRef.model_validate(envelope["outputs"][0])
    with service.base.resolve(
        actor,
        service.scope.application.workspace_id,
        output.handle,
        canvas_scope=service.scope,
    ) as result:
        assert json.loads(json.loads(result.read())) == {
            "invoice_count": 2,
            "total_cents": 12900,
        }
    from actions.server.foundry.work_item_execution import ReviewedGeneratedRun

    restarted = ReviewedGeneratedRun(
        service.reviews, service.scope, service.snapshot, service.base
    )
    assert restarted.dispatch(actor, proposal, claim, lease_seconds=30) == ticket
    with pytest.raises((ClaimRejected, FenceRejected)):
        execute.execute(actor, ticket.fence, cancelled=Event())
