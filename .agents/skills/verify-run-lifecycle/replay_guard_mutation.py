"""Scratch-only mutation of the retained-launch guard; never launches a process."""
import inspect
import json
import sys
import textwrap
from pathlib import Path
from uuid import uuid4
import pytest
sys.path.insert(0,str((Path(__file__).resolve().parents[3] / "action_server/tests")))
from action_server_tests import test_detached_action as fixtures
from actions.server._models import Run
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import RunOutputControlPlane, FenceRejected, _one, _update, _canonical
provider=fixtures.provider
postgresql_database=fixtures.postgresql_database
reviewed=fixtures.reviewed
case=fixtures.case
pytestmark=fixtures.pytestmark
pytest_plugins=['action_server_tests.foundry_fixtures']

def test_retained_launch_guard_rejects_but_its_mutant_admits(case,monkeypatch):
    c=case
    owner,service,caller=fixtures.setup(c)
    run=owner.admit(caller.actor,service.snapshot,{'value':'hello'},'formal-uncertain')
    first=owner.claim(caller,run.id,service.snapshot.worker)
    record=json.loads(_one(c.db,Run,run.id).result)
    record['launch']={'uncertain':True}
    original_record=_canonical(record,65536)
    with c.db.transaction():
        _update(c.db,Run,run.id,{'result':original_record})
        _update(c.db,RunAttempt,first.fence.attempt_id,{'lease_deadline_ms':'0'})
    RunOutputControlPlane(c.db).authorize_recovery(run.id,first.fence.epoch,receipt='formal-mutation-is-not-reconciliation')
    other=ManagedCaller(actor=caller.actor,worker_id=str(uuid4()))
    with pytest.raises(FenceRejected,match='reconciliation'):
        owner.claim(other,run.id,service.snapshot.worker)
    assert _one(c.db,RunPin,run.id).epoch==first.fence.epoch
    original=DetachedActions.claim
    source=textwrap.dedent(inspect.getsource(original))
    guard='or record.get("launch") is not None'
    assert source.count(guard)==1
    namespace={}
    exec(compile(source.replace(guard,'or False',1),'scratch_retained_launch_mutant.py','exec'),original.__globals__,namespace)
    with monkeypatch.context() as patch:
        patch.setattr(DetachedActions,'claim',namespace['claim'])
        second=owner.claim(other,run.id,service.snapshot.worker)
        assert second.fence.epoch==first.fence.epoch+1
        assert json.loads(_one(c.db,Run,run.id).result)['launch'] is None
        assert _one(c.db,RunAttempt,first.fence.attempt_id).state=='lost'
    assert DetachedActions.claim is original
