"""Acceptance contracts for durable Action Run ownership."""

import subprocess
import sys
from pathlib import Path


def test_remote_runtime_can_query_and_request_cancel(tmp_path: Path) -> None:
    from actions.server.run_ownership import RunOwnershipStore

    db_path = tmp_path / "runs.db"
    owner = RunOwnershipStore(db_path, owner_id="runtime-a")
    observer = RunOwnershipStore(db_path, owner_id="runtime-b")

    owner.create_run("run-1")
    lease = owner.claim("run-1")

    assert observer.get("run-1").owner_id == "runtime-a"
    assert observer.request_cancel("run-1") is True
    assert owner.control_requested("run-1", lease.epoch) == "cancel"


def test_expired_owner_can_be_reconciled_without_stale_fence(tmp_path: Path) -> None:
    from actions.server.run_ownership import RunOwnershipStore

    db_path = tmp_path / "runs.db"
    first = RunOwnershipStore(db_path, owner_id="runtime-a", lease_seconds=0)
    second = RunOwnershipStore(db_path, owner_id="runtime-b", lease_seconds=30)

    first.create_run("run-1")
    first_lease = first.claim("run-1")
    second_lease = second.claim("run-1")

    assert second_lease.epoch > first_lease.epoch
    assert first.release("run-1", first_lease.epoch) is False
    assert second.reconcile("run-1", second_lease.epoch, "running") == "reconciled"


def test_two_independent_processes_observe_same_run(tmp_path: Path) -> None:
    db_path = tmp_path / "runs.db"
    script = """
from actions.server.run_ownership import RunOwnershipStore
import sys
store = RunOwnershipStore(sys.argv[1], owner_id=sys.argv[2])
if sys.argv[3] == 'create':
    store.create_run('run-1')
    store.claim('run-1')
else:
    print(store.get('run-1').owner_id)
"""
    subprocess.run(
        [sys.executable, "-c", script, str(db_path), "runtime-a", "create"],
        check=True,
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(db_path), "runtime-b", "read"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "runtime-a"
