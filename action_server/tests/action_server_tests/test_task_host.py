"""Worker lifecycle/policy boundary tests; synthetic execution is labelled."""
import hashlib
import json
import threading
import time
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from action_server_tests import test_task_service as tasks_fixture

from actions.server._models import Run
from actions.server.deployments.package_revision_compiler import (
    PreparedRccEnvironment,
    RccBuildIdentity,
)
from actions.server.run_outputs.detached import DetachedActionWorker
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import _one
from actions.server.run_outputs.task_host import DetachedTaskHost, load_task_policy
from actions.server.run_outputs.task_service import (
    TaskHostUnavailable,
    TaskPolicy,
    TaskService,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = tasks_fixture.provider
postgresql_database = tasks_fixture.postgresql_database
reviewed = tasks_fixture.reviewed
case = tasks_fixture.case
pytestmark = tasks_fixture.pytestmark


def policy_file(tmp_path, raw=None):
    path = tmp_path / "task-policy.json"
    path.write_bytes(
        raw
        or json.dumps(
            {
                "schema_version": "actions.runtime-task-policy/v1",
                "policy_id": "host/v1",
                "ttl_ms": 60000,
                "poll_interval_ms": 10,
            }
        ).encode()
    )
    path.chmod(0o600)
    return path


def test_private_policy_exact_schema(tmp_path):
    path = policy_file(tmp_path)
    assert load_task_policy(path) == TaskPolicy("host/v1", 60000, 10)
    with pytest.raises(ValueError):
        load_task_policy(Path("relative.json"))
    path.chmod(0o640)
    with pytest.raises(ValueError):
        load_task_policy(path)
    path.chmod(0o600)
    linked = tmp_path / "linked.json"
    linked.symlink_to(path)
    with pytest.raises(ValueError):
        load_task_policy(linked)
    import os

    os.link(path, tmp_path / "hardlink")
    with pytest.raises(ValueError):
        load_task_policy(path)


@pytest.mark.parametrize(
    "raw",
    [
        b"{}",
        b"[]",
        b"null",
        b"\xff",
        b" " * 17000,
        b'{"schema_version":"actions.runtime-task-policy/v1","policy_id":"a","policy_id":"b","ttl_ms":100,"poll_interval_ms":1}',
        b'{"schema_version":"actions.runtime-task-policy/v1","policy_id":"secret-value","ttl_ms":NaN,"poll_interval_ms":1}',
        b'{"schema_version":"actions.runtime-task-policy/v1","policy_id":"a","ttl_ms":true,"poll_interval_ms":1}',
        b'{"schema_version":"actions.runtime-task-policy/v1","policy_id":"a","ttl_ms":100,"poll_interval_ms":1,"worker_id":"secret-value"}',
    ],
)
def test_invalid_private_policy_is_bounded(tmp_path, raw):
    with pytest.raises(
        ValueError, match="^Private Task policy unavailable or invalid$"
    ):
        load_task_policy(policy_file(tmp_path, raw))


def make_host(c, tmp_path, monkeypatch):
    from actions.server._download_rcc import get_default_rcc_location
    from actions.server.run_outputs import task_host as module

    _, authority, service, caller = tasks_fixture.setup(c)
    compiled = service.registry.load(service.snapshot.capability.package_revision)
    with zipfile.ZipFile(BytesIO(compiled.source_archive)) as archive:
        package_yaml = archive.read("package.yaml")
    home = tmp_path / "prepared"
    home.mkdir()
    root = tmp_path / "execution"
    root.mkdir()
    prepared = PreparedRccEnvironment(
        home,
        "sha256:" + hashlib.sha256(package_yaml).hexdigest(),
        RccBuildIdentity(
            compiled.rcc_specification_digest, compiled.rcc_artifact_digest
        ),
    )
    monkeypatch.setattr(module, "verify_rcc_version", lambda path: None)
    host = DetachedTaskHost(
        authority,
        actor=caller.actor,
        worker_id=caller.worker_id,
        profile=service.snapshot.worker,
        prepared=prepared,
        rcc=Path(get_default_rcc_location()),
        execution_root=root,
        policy=TaskPolicy("host/v1", 60000, 10),
    )
    tasks = TaskService(authority, readiness=host, policy=host.policy)
    return host, tasks, authority, service, caller


def wait_for(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    assert predicate(), "bounded worker observation timed out"


def test_readiness_waits_for_thread_connection_probe(case, tmp_path, monkeypatch):
    c = case
    host, tasks, authority, service, caller = make_host(c, tmp_path, monkeypatch)
    before = c.db.all(RunPin)
    entered, released = threading.Event(), threading.Event()
    original = authority.pending

    def pending(*args, **kwargs):
        entered.set()
        released.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(authority, "pending", pending)
    try:
        with pytest.raises(TaskHostUnavailable):
            host.start(0.02)
        assert entered.wait(1)
        assert host.close(0.01) is False
        with pytest.raises(TaskHostUnavailable):
            tasks_fixture.create(c, tasks, service, caller)
        assert c.db.all(RunPin) == before
        # A false close retains resources; the host never owns their disposal.
        provider = c.outputs.providers[service.snapshot.provider_key]
        staged = provider.stage([b"retained"])
        provider.discard(staged)
    finally:
        released.set()
        assert host.close(5)


def test_thread_consumes_two_canonical_claims_and_stops(case, tmp_path, monkeypatch):
    c = case
    host, tasks, authority, service, caller = make_host(c, tmp_path, monkeypatch)
    consumed = []

    def synthetic_execute(worker, ticket, **kwargs):
        consumed.append(ticket.fence.run_id)
        return _one(c.db, Run, ticket.fence.run_id)

    monkeypatch.setattr(DetachedActionWorker, "execute", synthetic_execute)
    host.start()
    try:
        first = tasks_fixture.create(c, tasks, service, caller, "first")
        second = tasks_fixture.create(c, tasks, service, caller, "second")
        wait_for(lambda: len(consumed) == 2)
        assert consumed == [first.task_id, second.task_id]
        assert sum(row.run_id in consumed for row in c.db.all(RunAttempt)) == 2
        for task in (first, second):
            assert _one(c.db, RunPin, task.task_id).epoch == 1
            assert (
                tasks.get(
                    caller.actor, service.snapshot.workspace_id, task.task_id
                ).status
                == "working"
            )
    finally:
        assert host.close(5)
    assert not host.failed
    with pytest.raises(TaskHostUnavailable):
        host.start()


def test_fatal_execution_refuses_create_but_retains_get_cancel(
    case, tmp_path, monkeypatch
):
    c = case
    host, tasks, authority, service, caller = make_host(c, tmp_path, monkeypatch)

    def failed(*args, **kwargs):
        raise RuntimeError("private execution path")

    monkeypatch.setattr(DetachedActionWorker, "execute", failed)
    host.start()
    try:
        task = tasks_fixture.create(c, tasks, service, caller)
        wait_for(lambda: host.failed)
        assert (
            tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id).status
            == "working"
        )
        tasks.cancel(caller.actor, service.snapshot.workspace_id, task.task_id)
        with pytest.raises(TaskHostUnavailable):
            tasks_fixture.create(c, tasks, service, caller, "next")
        assert len(c.db.all(RunAttempt, where="run_id=?", values=[task.task_id])) == 1
    finally:
        assert host.close(5)


def test_scope_mismatch_and_no_grant_mint(case, tmp_path, monkeypatch):
    from uuid import uuid4

    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.run_outputs.models import RunAccessGrant
    from actions.server.run_outputs.types import Actor

    c = case
    host, tasks, authority, service, caller = make_host(c, tmp_path, monkeypatch)
    before = c.db.all(RunAccessGrant), c.db.all(FoundryAccessGrant)
    host.start()
    try:
        host.require_ready(caller.actor, service.snapshot)
        with pytest.raises(TaskHostUnavailable):
            host.require_ready(Actor(principal_id=str(uuid4())), service.snapshot)
        changed = service.snapshot.model_copy(
            update={
                "worker": service.snapshot.worker.model_copy(
                    update={"worker_profile_id": str(uuid4())}
                )
            }
        )
        with pytest.raises(TaskHostUnavailable):
            host.require_ready(caller.actor, changed)
        assert (c.db.all(RunAccessGrant), c.db.all(FoundryAccessGrant)) == before
    finally:
        assert host.close(5)


def test_local_stop_reaches_executor_callback_without_terminal_fabrication(
    case, tmp_path, monkeypatch
):
    from actions.server._models import RunStatus
    from actions.server.foundry.rcc_execution import GeneratedRccExecution

    c = case
    host, tasks, authority, service, caller = make_host(c, tmp_path, monkeypatch)
    entered = threading.Event()

    def synthetic_execution(executor, actor, fence, *, cancelled, **kwargs):
        entered.set()
        wait_for(cancelled)
        executor._check_cancel(cancelled, actor, fence)
        raise AssertionError("cancellation must stop execution")

    monkeypatch.setattr(GeneratedRccExecution, "execute", synthetic_execution)
    host.start()
    try:
        task = tasks_fixture.create(c, tasks, service, caller)
        assert entered.wait(10)
        assert host.close(5)
        assert not host.failed
        assert _one(c.db, Run, task.task_id).status == RunStatus.RUNNING
        assert _one(c.db, RunPin, task.task_id).cancel_requested == 1
        assert (
            tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id).status
            == "working"
        )
    finally:
        assert host.close(5)


def test_competing_consumers_never_create_second_attempt(case, tmp_path, monkeypatch):
    from uuid import uuid4

    c = case
    first, tasks, authority, service, caller = make_host(c, tmp_path, monkeypatch)
    second = DetachedTaskHost(
        authority,
        actor=caller.actor,
        worker_id=str(uuid4()),
        profile=first.profile,
        prepared=first.prepared,
        rcc=first.rcc,
        execution_root=first.execution_root,
        policy=first.policy,
    )
    barrier = threading.Barrier(2)
    original = authority.pending
    arrived = set()
    guard = threading.Lock()

    def pending(*args, **kwargs):
        page = original(*args, **kwargs)
        current = threading.get_ident()
        with guard:
            should_wait = bool(page.run_ids) and current not in arrived
            if should_wait:
                arrived.add(current)
        if should_wait:
            barrier.wait(timeout=10)
        return page

    released = threading.Event()
    executed = []

    def synthetic_execute(worker, ticket, **kwargs):
        executed.append(ticket.fence)
        released.wait(10)
        return _one(c.db, Run, ticket.fence.run_id)

    monkeypatch.setattr(authority, "pending", pending)
    monkeypatch.setattr(DetachedActionWorker, "execute", synthetic_execute)
    first.start()
    second.start()
    try:
        task = tasks_fixture.create(c, tasks, service, caller)
        wait_for(lambda: first.failed or second.failed)
        assert first.failed != second.failed
        assert len(executed) == 1
        assert len(c.db.all(RunAttempt, where="run_id=?", values=[task.task_id])) == 1
    finally:
        released.set()
        assert first.close(5) and second.close(5)


def test_active_worker_close_timeout_retains_resources(case, tmp_path, monkeypatch):
    c = case
    host, tasks, authority, service, caller = make_host(c, tmp_path, monkeypatch)
    entered, released = threading.Event(), threading.Event()

    def synthetic_execute(worker, ticket, **kwargs):
        entered.set()
        released.wait(10)
        return _one(c.db, Run, ticket.fence.run_id)

    monkeypatch.setattr(DetachedActionWorker, "execute", synthetic_execute)
    host.start()
    try:
        tasks_fixture.create(c, tasks, service, caller)
        assert entered.wait(10)
        assert host.close(0.01) is False
        provider = c.outputs.providers[service.snapshot.provider_key]
        staged = provider.stage([b"still owned"])
        provider.discard(staged)
        with pytest.raises(TaskHostUnavailable):
            tasks_fixture.create(c, tasks, service, caller, "next")
    finally:
        released.set()
        assert host.close(5)


def test_failed_thread_database_probe_never_becomes_ready(case, tmp_path, monkeypatch):
    c = case
    host, tasks, authority, service, caller = make_host(c, tmp_path, monkeypatch)
    before = c.db.all(RunPin)

    def failed(*args, **kwargs):
        raise RuntimeError("private database path")

    monkeypatch.setattr(authority, "pending", failed)
    with pytest.raises(TaskHostUnavailable):
        host.start()
    assert host.failed and host.close(5)
    with pytest.raises(TaskHostUnavailable):
        tasks_fixture.create(c, tasks, service, caller)
    assert c.db.all(RunPin) == before


def test_unconfirmed_child_cleanup_retains_resources_after_thread_exit(
    case, tmp_path, monkeypatch
):
    from actions.server.foundry.rcc_execution import RccCleanupIncomplete

    c = case
    host, tasks, authority, service, caller = make_host(c, tmp_path, monkeypatch)

    def uncertain(*args, **kwargs):
        raise RccCleanupIncomplete("owned cleanup unconfirmed")

    monkeypatch.setattr(DetachedActionWorker, "execute", uncertain)
    host.start()
    try:
        task = tasks_fixture.create(c, tasks, service, caller)
        wait_for(lambda: host.failed)
        host._thread.join(5)
        assert not host._thread.is_alive()
        assert host.close(0.01) is False
        provider = c.outputs.providers[service.snapshot.provider_key]
        staged = provider.stage([b"retained after unconfirmed cleanup"])
        provider.discard(staged)
        assert (
            tasks.get(caller.actor, service.snapshot.workspace_id, task.task_id).status
            == "working"
        )
    finally:
        # This boundary fixture spawned no child. The production latch remains
        # false until operator recovery outside this host, even after join.
        host._thread.join(5)
        assert not host._thread.is_alive()
