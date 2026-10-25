"""Actual host readiness boundary; simulated host state, no worker/RCC launch."""
import threading
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests import test_generic_work_item_execution as generic_fixture
from action_server_tests import test_robot_claimed_work_items_327 as robot_fixture

from actions.server.deployments.package_revision_compiler import (
    PreparedRccEnvironment,
    RccBuildIdentity,
)
from actions.server.managed_work_items.contracts import ClaimRef
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.service import FenceRejected
from actions.server.run_outputs.task_host import DetachedTaskHost
from actions.server.run_outputs.task_service import TaskHostUnavailable, TaskPolicy
from actions.server.run_outputs.types import Actor

claimed = robot_fixture.claimed
generic = generic_fixture.generic
disable_feedback = robot_fixture.disable_feedback
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def host_for(c, tmp_path):
    authority = DetachedActions(
        c.owner.deployments, c.owner.base, queue_authorization=c.owner.authorization
    )
    phases = []

    class Robot:
        def require_claimed_ready(self, service):
            assert not c.db.in_transaction()
            assert service.snapshot == c.owner.snapshot
            phases.append("provider-readiness")

    def select(registry, snapshot):
        assert not c.db.in_transaction()
        phases.append("select")
        return Robot()

    home = tmp_path / "prepared"
    home.mkdir()
    host = DetachedTaskHost(
        authority,
        actor=c.caller.actor,
        worker_id=c.caller.worker_id,
        profile=c.owner.snapshot.worker,
        prepared=PreparedRccEnvironment(
            home,
            "sha256:" + "a" * 64,
            RccBuildIdentity("sha256:" + "b" * 64, "sha256:" + "c" * 64),
        ),
        rcc=tmp_path / "not-executed-rcc",
        execution_root=tmp_path / "execution",
        policy=TaskPolicy("claimed-host-boundary", 60000, 100),
        capability_runner=SimpleNamespace(robot_for=select),
    )
    # Isolate readiness policy from thread startup, tested in test_task_host.
    host._thread = threading.current_thread()
    host._ready.set()
    ref = ClaimRef(
        queue=c.owner.queue_ref(c.owner.policy.input_queue),
        item_id=str(uuid4()),
        owner_id=c.caller.worker_id,
        epoch=1,
    )
    return host, ref, phases


def test_claimed_scope_is_pure_and_full_readiness_is_transaction_free(
    claimed, tmp_path, monkeypatch
):
    c = claimed()
    host, ref, phases = host_for(c, tmp_path)
    with c.db.transaction():
        with monkeypatch.context() as patch:

            def forbidden(*args, **kwargs):
                raise AssertionError("pure scope touched database or provider")

            patch.setattr(host.authority, "claimed_service", forbidden)
            patch.setattr(c.db, "connect", forbidden)
            host.require_claimed_scope(c.caller.actor, c.owner.snapshot, ref)
        with pytest.raises(TaskHostUnavailable, match="transaction-free"):
            host.require_claimed_ready(c.caller.actor, c.owner.snapshot, ref)
    assert phases == []
    host.require_claimed_ready(c.caller.actor, c.owner.snapshot, ref)
    assert phases == ["select", "provider-readiness"]


@pytest.mark.parametrize(
    "damage", ["owner", "actor", "profile", "deployment", "queue", "stopped"]
)
def test_claimed_scope_denials_precede_provider_preparation(claimed, tmp_path, damage):
    c = claimed()
    host, ref, phases = host_for(c, tmp_path)
    actor, snapshot = c.caller.actor, c.owner.snapshot
    if damage == "owner":
        ref = ref.model_copy(update={"owner_id": str(uuid4())})
    elif damage == "actor":
        actor = Actor(principal_id=str(uuid4()))
    elif damage == "profile":
        host.profile = snapshot.worker.model_copy(update={"revision_id": "wrong"})
    elif damage == "deployment":
        deployment = ref.queue.deployment.model_copy(update={"revision_id": "wrong"})
        ref = ref.model_copy(
            update={"queue": ref.queue.model_copy(update={"deployment": deployment})}
        )
    elif damage == "queue":
        ref = ref.model_copy(
            update={"queue": ref.queue.model_copy(update={"queue_id": "wrong-queue"})}
        )
    else:
        host._stop.set()
    with pytest.raises(TaskHostUnavailable):
        host.require_claimed_ready(actor, snapshot, ref)
    assert phases == []


def test_non_robot_rejected_before_provider_preparation(generic, tmp_path):
    c = generic()
    host, ref, phases = host_for(c, tmp_path)
    with pytest.raises(FenceRejected, match="retained Robot Package required"):
        host.require_claimed_ready(c.caller.actor, c.owner.snapshot, ref)
    assert phases == []


def test_claimed_readiness_rechecks_host_after_provider(claimed, tmp_path):
    c = claimed()
    host, ref, phases = host_for(c, tmp_path)

    class Robot:
        def require_claimed_ready(self, service):
            assert not c.db.in_transaction()
            phases.append("provider-readiness")
            host._stop.set()

    host.capability_runner.robot_for = lambda *args: Robot()
    with pytest.raises(TaskHostUnavailable):
        host.require_claimed_ready(c.caller.actor, c.owner.snapshot, ref)
    assert phases == ["provider-readiness"]


def test_real_robot_runner_claimed_readiness_preserves_standalone_guard(
    claimed, tmp_path
):
    from actions.server.run_outputs.service import AccessDenied

    c = claimed()
    host, ref, _ = host_for(c, tmp_path)
    host.capability_runner = SimpleNamespace(
        robot_for=lambda registry, snapshot: c.runner
    )
    # Exercise the actual runner, not the synthetic sequencing probe above.
    with pytest.raises(AccessDenied, match="standalone Robot declaration required"):
        c.runner.require_ready(c.owner)
    host.require_claimed_ready(c.caller.actor, c.owner.snapshot, ref)


@pytest.mark.parametrize(
    "damage", ["none", "optional", "producer", "outputs", "inactive"]
)
def test_real_claimed_runner_readiness_rejects_changed_declaration_or_activation(
    claimed, monkeypatch, damage
):
    from dataclasses import replace

    from actions.server.run_outputs.service import AccessDenied

    c = claimed()
    if damage == "inactive":
        monkeypatch.setattr(
            c.owner.deployments._repository, "was_activated", lambda ref: False
        )
    else:
        declaration = c.owner.registry.get_capability(c.owner.snapshot.capability)
        updates = {"allow_outputs": True} if damage == "outputs" else {"mode": damage}
        changed = replace(
            declaration, work_items=declaration.work_items.model_copy(update=updates)
        )
        monkeypatch.setattr(c.owner.registry, "get_capability", lambda ref: changed)
    with pytest.raises(AccessDenied):
        c.runner.require_claimed_ready(c.owner)
