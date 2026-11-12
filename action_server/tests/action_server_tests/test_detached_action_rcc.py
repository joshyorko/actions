"""Opt-in real detached ordinary Action; parent owns exclusive prepared cache."""
import os
from pathlib import Path

import pytest
from action_server_tests import test_generic_canvas_view as app_tests
from contract_tests.test_package_revision_compiler import _generated_action_entries

from actions.server._models import Run, RunStatus
from actions.server.deployments.package_revision_compiler import (
    load_prepared_rcc_environment,
)
from actions.server.run_outputs.detached import DetachedActions, DetachedActionWorker
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import FenceRejected, _one

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = app_tests.provider
postgresql_database = app_tests.postgresql_database
reviewed = app_tests.reviewed
pytestmark = app_tests.pytestmark


def test_actual_detached_action(reviewed, foundry_package_store, tmp_path, monkeypatch):
    if os.environ.get("ACTIONS_DETACHED_REAL_RCC") != "1":
        pytest.skip("exclusive prepared detached RCC cache required")
    original = app_tests.fixtures.setup_activated
    monkeypatch.setattr(
        app_tests.fixtures,
        "setup_activated",
        lambda r, store: original(
            r,
            store,
            real=True,
            backend_entries=_generated_action_entries(),
            logical_key="detached-echo",
        ),
    )
    c = app_tests.case.__wrapped__(reviewed, foundry_package_store)
    service, caller = c.port._selected(c.app, "run")
    owner = DetachedActions(c.deployments, c.outputs)
    run = owner.admit(
        caller.actor, service.snapshot, {"value": "hello"}, "real-detached"
    )
    assert (
        run.status == RunStatus.NOT_RUN
        and not _one(c.db, RunPin, run.id).current_attempt_id
    )
    # Rebuild authority objects before consuming the persisted admission. This
    # is service reconstruction, not a process restart or two-replica proof.
    worker = DetachedActionWorker(
        DetachedActions(c.deployments, c.outputs),
        caller.actor,
        caller.worker_id,
        service.snapshot.worker,
    )
    root = tmp_path / "execution"
    root.mkdir()
    done, _ = worker.run_once(
        prepared=load_prepared_rcc_environment(
            Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
        ),
        rcc=Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]),
        execution_root=root,
    )
    assert done.id == run.id and done.status == RunStatus.PASSED
    pin = _one(c.db, RunPin, run.id)
    assert _one(c.db, RunAttempt, pin.current_attempt_id).state == "succeeded"
    assert (
        owner.admit(
            caller.actor, service.snapshot, {"value": "hello"}, "real-detached"
        ).id
        == run.id
    )
    with pytest.raises(FenceRejected):
        worker.claim(run.id)
    assert not owner.pending(
        caller.actor, service.snapshot.workspace_id, service.snapshot.worker
    ).run_ids
    assert _one(c.db, Run, run.id).result
