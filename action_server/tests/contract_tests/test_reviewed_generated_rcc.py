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
    assert envelope["result"]["launch"]["id"]
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
    verify_fresh_process(service, actor, ticket, output, tmp_path)
    from actions.server.foundry.work_item_execution import ReviewedGeneratedRun

    restarted = ReviewedGeneratedRun(
        service.reviews, service.scope, service.snapshot, service.base
    )
    assert restarted.dispatch(actor, proposal, claim, lease_seconds=30) == ticket
    with pytest.raises((ClaimRejected, FenceRejected)):
        execute.execute(actor, ticket.fence, cancelled=Event())


def verify_fresh_process(service, actor, ticket, output, tmp_path):
    import subprocess
    import sys

    environment = {
        key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ
    }
    environment.update(
        OWNED_DB=str(service.db.db_path),
        OWNED_ROOT=str(tmp_path),
        OWNED_ACTOR=actor.model_dump_json(),
        OWNED_SNAPSHOT=service.snapshot.model_dump_json(),
        OWNED_SCOPE=service.scope.model_dump_json(),
        OWNED_TICKET=ticket.model_dump_json(),
        OWNED_HANDLE=output.handle,
    )
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            r"""
import json,os
from pathlib import Path
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.foundry.work_item_execution import ReviewedGeneratedRun,GeneratedWorkItemTicket
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import Actor,CanvasResultScope,ExecutionSnapshot
root=Path(os.environ['OWNED_ROOT']);db=Database(os.environ['OWNED_DB'])
a=Actor.model_validate_json(os.environ['OWNED_ACTOR'])
snapshot=ExecutionSnapshot.model_validate_json(os.environ['OWNED_SNAPSHOT'])
scope=CanvasResultScope.model_validate_json(os.environ['OWNED_SCOPE'])
ticket=GeneratedWorkItemTicket.model_validate_json(os.environ['OWNED_TICKET'])
fds=[os.open(root/name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW) for name in ('objects','package-objects')]
try:
 with db.connect(),FilesystemOutputProvider(fds[0]) as objects,FilesystemOutputProvider(fds[1]) as packages:
  db.initialize(get_all_model_classes())
  registry=FoundryPackageRegistry(db,packages,SqlFoundryAuthorization(db),executor=object())
  outputs=RunOutputService(db,{snapshot.provider_key:objects},capabilities=registry)
  reviews=InvoiceReviewService(InvoiceQueryService(outputs,{}))
  restored=ReviewedGeneratedRun(reviews,scope,snapshot,outputs)
  assert restored.dispatch(a,ticket.proposal,ticket.claim.as_claim(),lease_seconds=30)==ticket
  with outputs.resolve(a,scope.application.workspace_id,os.environ['OWNED_HANDLE'],canvas_scope=scope) as found:
   summary=json.loads(json.loads(found.read()))
  assert summary=={'invoice_count':2,'total_cents':12900}
  print(json.dumps({'run':ticket.fence.run_id,'summary':summary}))
finally:
 for fd in fds:os.close(fd)
""",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "run": ticket.fence.run_id,
        "summary": {"invoice_count": 2, "total_cents": 12900},
    }
