# ruff: noqa: F811 - imported pytest fixture is injected by name
"""Trusted worker selection for the invocation-scoped child IPC host."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests import test_generic_canvas_view as app_tests
from action_server_tests.test_internal_child_admission import (  # noqa: F811
    admitted as admitted,
)

from actions.server.run_outputs.detached import DetachedActionWorker
from actions.server.run_outputs.models import RunPin
from actions.server.run_outputs.service import FenceRejected, _one

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="private filesystem Package storage is Linux-only"
)
case = app_tests.case
provider = app_tests.provider
postgresql_database = app_tests.postgresql_database
reviewed = app_tests.reviewed


def _worker(admitted, snapshot):
    worker_id = str(uuid4())
    run = admitted.detached.admit(
        admitted.actor, snapshot, {"value": "host wiring"}, "child-ipc-worker"
    )
    worker = DetachedActionWorker(
        admitted.detached,
        admitted.actor,
        worker_id,
        snapshot.worker,
    )
    return worker, worker.claim(run.id)


def test_detached_worker_passes_host_factory_for_pinned_delegated_action(
    admitted, monkeypatch
):
    snapshot = admitted.outputs._pinned(
        _one(admitted.db, RunPin, admitted.parent_run.id)
    )
    worker, ticket = _worker(admitted, snapshot)
    captured = {}

    class Runtime:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

        def execute(self, *args, **kwargs):
            return "synthetic host wiring capture"

    monkeypatch.setattr(
        "actions.server.run_outputs.detached.GeneratedRccExecution", Runtime
    )

    assert (
        worker.execute(
            ticket,
            prepared=None,
            rcc=Path("unused-rcc"),
            execution_root=Path("unused-root"),
        )
        == "synthetic host wiring capture"
    )
    factory = captured["internal_child_ipc_factory"]
    assert callable(factory)

    from actions.server.foundry.internal_child_ipc_server import (
        InternalChildIPCServerHost,
    )

    host = factory(ticket.fence)
    assert type(host) is InternalChildIPCServerHost
    assert host._server._fence == ticket.fence
    assert host.stop(timeout_seconds=0)


def test_detached_worker_keeps_child_api_disabled_without_policy(admitted):
    robot_capability = admitted.registry.capability_refs(admitted.robot_ref)[0]
    robot = admitted.deployments.resolve(
        admitted.actor,
        admitted.workspace,
        admitted.robot_revision.ref.deployment_id,
        robot_capability,
        revision=admitted.robot_revision.ref,
    ).snapshot
    worker = DetachedActionWorker(
        admitted.detached,
        admitted.actor,
        str(uuid4()),
        robot.worker,
    )

    assert worker._internal_child_ipc_factory(robot) is None


def test_non_delegated_action_keeps_generated_runtime_api_unavailable(
    case, monkeypatch
):
    service, caller = case.port._selected(case.app, "run")
    from actions.server.run_outputs.detached import DetachedActions

    authority = DetachedActions(case.deployments, case.outputs)
    run = authority.admit(
        caller.actor, service.snapshot, {"value": "no delegation"}, "no-child-api"
    )
    worker = DetachedActionWorker(
        authority,
        caller.actor,
        caller.worker_id,
        service.snapshot.worker,
    )
    ticket = worker.claim(run.id)
    captured = {}

    class Runtime:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

        def execute(self, *args, **kwargs):
            return None

    monkeypatch.setattr(
        "actions.server.run_outputs.detached.GeneratedRccExecution", Runtime
    )
    worker.execute(
        ticket,
        prepared=None,
        rcc=Path("unused-rcc"),
        execution_root=Path("unused-root"),
    )

    assert "internal_child_ipc_factory" not in captured


def test_detached_worker_fails_closed_for_missing_or_ambiguous_pinned_policy(
    admitted, monkeypatch
):
    snapshot = admitted.outputs._pinned(
        _one(admitted.db, RunPin, admitted.parent_run.id)
    )
    worker = DetachedActionWorker(
        admitted.detached,
        admitted.actor,
        str(uuid4()),
        snapshot.worker,
    )
    repository = admitted.deployments._repository
    original = repository.get_revision(snapshot.deployment)
    monkeypatch.setattr(repository, "get_revision", lambda _ref: None)
    with pytest.raises(FenceRejected):
        worker._internal_child_ipc_factory(snapshot)

    duplicate = SimpleNamespace(
        revision=SimpleNamespace(
            ref=snapshot.deployment,
            specification=SimpleNamespace(
                internal_robot_delegations=(
                    admitted.parent_spec.internal_robot_delegations[0],
                    admitted.parent_spec.internal_robot_delegations[0],
                )
            ),
        )
    )
    assert original is not None
    monkeypatch.setattr(repository, "get_revision", lambda _ref: duplicate)
    with pytest.raises(FenceRejected):
        worker._internal_child_ipc_factory(snapshot)
