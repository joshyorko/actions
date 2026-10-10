"""Independent processes share SQLite authority, not Python locks/caches."""

import json
import os
import subprocess
import sys
import time

import pytest
from action_server_tests.run_outputs.test_service import insert_action, snapshot, uid

from actions.server._models import create_db
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputControlPlane, RunOutputService
from actions.server.run_outputs.types import Actor

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux private output-provider proof"
)


def child_env():
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def test_two_process_claims_have_one_current_owner(tmp_path):
    database = tmp_path / "runs.db"
    snap = snapshot()
    actor = Actor(principal_id=uid())
    with create_db(database) as db:
        control = RunOutputControlPlane(db)
        insert_action(db, snap)
        control.register(snap)
        control.grant(actor, snap.deployment, {"execute"})
        run = RunOutputService(db, {}).admit(actor, snap, {}, "key")
    script = """
import json,sys,time
from pathlib import Path
from uuid import uuid4
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.run_outputs.service import RunOutputService,FenceRejected
ready,go=Path(sys.argv[3]),Path(sys.argv[4])
ready.write_text("ready")
deadline=time.monotonic()+10
while not go.exists():
    if time.monotonic()>deadline: raise TimeoutError("start barrier")
    time.sleep(.005)
db=Database(Path(sys.argv[1]))
with db.connect():
    db.initialize(get_all_model_classes())
    try:
        fence=RunOutputService(db,{}).claim(sys.argv[2],str(uuid4()),lease_seconds=30)
        print(json.dumps({"claimed":fence.model_dump()}),flush=True)
    except FenceRejected:
        print(json.dumps({"rejected":True}),flush=True)
"""
    results = _race(tmp_path, script, [str(database), run.id])
    assert sum("claimed" in result for result in results) == 1
    assert sum("rejected" in result for result in results) == 1


def _race(tmp_path, script, args):
    go = tmp_path / "go"
    children = []
    try:
        for index in range(2):
            ready = tmp_path / f"ready-{index}"
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    script,
                    *args,
                    str(ready),
                    str(go),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=child_env(),
            )
            children.append((child, ready))
        deadline = time.monotonic() + 10
        while not all(marker.exists() for child, marker in children):
            for child, marker in children:
                if child.poll() is not None:
                    stdout, stderr = child.communicate(timeout=5)
                    raise AssertionError(
                        f"child exited before readiness: {child.returncode}; {stderr[-4000:]}; {stdout[-1000:]}"
                    )
            assert time.monotonic() < deadline, "bounded readiness timeout"
            time.sleep(0.005)
        go.touch()
        results = []
        for child, marker in children:
            stdout, stderr = child.communicate(timeout=15)
            assert child.returncode == 0, stderr[-4000:]
            results.append(json.loads(stdout))
        return results
    finally:
        for child, marker in children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)


def test_authorized_handle_is_retrieved_after_real_process_restart(tmp_path):
    root = tmp_path / "objects"
    root.mkdir()
    database = tmp_path / "runs.db"
    snap = snapshot()
    actor = Actor(principal_id=uid())
    fd = os.open(root, getattr(os, "O_DIRECTORY") | os.O_RDONLY)
    try:
        with create_db(database) as db, FilesystemOutputProvider(fd) as provider:
            control = RunOutputControlPlane(db)
            insert_action(db, snap)
            control.register(snap)
            control.grant(actor, snap.deployment, {"execute", "read"})
            service = RunOutputService(db, {snap.provider_key: provider})
            run = service.admit(actor, snap, {}, "key")
            fence = service.claim(run.id, uid(), lease_seconds=30)
            output = service.stage(
                fence,
                [b"restart proof"],
                name="result",
                media_type="text/plain",
                retention_seconds=30,
            )
            service.publish(
                actor, fence, [output], {"artifact": {"handle": output.handle}}
            )
    finally:
        os.close(fd)
    script = """
import os,sys,json
from pathlib import Path
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import Actor
fd=os.open(sys.argv[2],os.O_RDONLY|getattr(os,"O_DIRECTORY"))
try:
    db=Database(Path(sys.argv[1]))
    with db.connect(),FilesystemOutputProvider(fd) as provider:
        db.initialize(get_all_model_classes())
        service=RunOutputService(db,{sys.argv[3]:provider})
        with service.resolve(Actor(principal_id=sys.argv[4]),sys.argv[5],sys.argv[6]) as output:
            print(json.dumps({"run_id":output.run_id,"body":output.read().decode()}))
finally: os.close(fd)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(database),
            str(root),
            snap.provider_key,
            actor.principal_id,
            snap.workspace_id,
            output.handle,
        ],
        capture_output=True,
        text=True,
        env=child_env(),
        timeout=15,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    assert json.loads(result.stdout) == {"run_id": run.id, "body": "restart proof"}


def test_two_process_publications_attach_only_the_winning_result(tmp_path):
    from actions.server._database import Database
    from actions.server._models import Run, RunStatus, get_all_model_classes
    from actions.server.run_outputs.models import RunAttempt, RunOutput

    database = tmp_path / "runs.db"
    root = tmp_path / "objects"
    root.mkdir()
    snap = snapshot()
    actor = Actor(principal_id=uid())
    fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        with create_db(database) as db, FilesystemOutputProvider(fd) as provider:
            control = RunOutputControlPlane(db)
            insert_action(db, snap)
            control.register(snap)
            control.grant(actor, snap.deployment, {"execute"})
            service = RunOutputService(db, {snap.provider_key: provider})
            run = service.admit(actor, snap, {}, "key")
            fence = service.claim(run.id, uid(), lease_seconds=30)
            output = service.stage(
                fence,
                [b"body"],
                name="body",
                media_type="text/plain",
                retention_seconds=30,
            )
    finally:
        os.close(fd)
    script = """
import json,sys,time
from pathlib import Path
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.run_outputs.service import RunOutputService,FenceRejected
from actions.server.run_outputs.types import Actor,AttemptFence,OutputRef
payload=json.loads(sys.argv[2])
ready,go=Path(sys.argv[3]),Path(sys.argv[4])
ready.write_text("ready")
deadline=time.monotonic()+10
while not go.exists():
    if time.monotonic()>deadline: raise TimeoutError("start barrier")
    time.sleep(.005)
db=Database(Path(sys.argv[1]))
with db.connect():
    db.initialize(get_all_model_classes())
    try:
        run=RunOutputService(db,{}).publish(Actor.model_validate(payload["actor"]),AttemptFence.model_validate(payload["fence"]),[OutputRef.model_validate(payload["output"])],{"winner":str(ready)})
        print(json.dumps({"published":str(ready),"result":run.result}),flush=True)
    except FenceRejected:
        print(json.dumps({"rejected":True}),flush=True)
"""
    payload = json.dumps(
        {
            "actor": actor.model_dump(),
            "fence": fence.model_dump(),
            "output": output.model_dump(),
        }
    )
    results = _race(tmp_path, script, [str(database), payload])
    winners = [result for result in results if "published" in result]
    assert len(winners) == 1
    assert sum("rejected" in result for result in results) == 1
    db = Database(database)
    with db.connect():
        db.initialize(get_all_model_classes())
        persisted = db.first(Run, "SELECT * FROM run WHERE id=?", [run.id])
        assert persisted.status == RunStatus.PASSED
        assert persisted.result == winners[0]["result"]
        assert json.loads(persisted.result)["result"] == {
            "winner": winners[0]["published"]
        }
        assert (
            db.first(
                RunOutput, "SELECT * FROM run_output WHERE id=?", [output.output_id]
            ).state
            == "final"
        )
        assert (
            db.first(
                RunAttempt, "SELECT * FROM run_attempt WHERE id=?", [fence.attempt_id]
            ).state
            == "succeeded"
        )
