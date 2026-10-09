"""Run a synthetic Work Items consumer through an explicitly selected Runtime."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict

import pytest


class CaseProof(TypedDict):
    schema_version: int
    runtime_kind: str
    executable_sha256: str
    actions_core_wheel_sha256: str
    consumer_actions: list[dict[str, str | int]]
    api_state_readbacks: dict[str, dict[str, object]]


PROCESSOR_ACTION = textwrap.dedent(
    """
    from actions import action


    @action
    def process_work_item(
        db_path: str,
        files_dir: str,
        expected_id: str,
        scenario: str,
    ) -> dict[str, str]:
        from actions.work_items import SQLiteAdapter, State

        adapter = SQLiteAdapter(db_path=db_path, files_dir=files_dir)
        if scenario == "recover":
            recovered = adapter.recover_orphaned_work_items()
            if expected_id not in recovered:
                raise AssertionError("synthetic abandoned reservation was not recovered")

        item_id = adapter.reserve_input()
        if item_id != expected_id:
            raise AssertionError("consumer reserved an unexpected synthetic input")
        payload = adapter.load_payload(item_id)

        if scenario == "fail":
            adapter.release_input(
                item_id,
                State.FAILED,
                exception={
                    "type": "APPLICATION",
                    "code": "SYNTHETIC_PROCESSOR_FAILURE",
                    "message": "synthetic consumer failure",
                },
            )
            raise RuntimeError("synthetic consumer failed after recording Work Item failure")

        output_id = adapter.create_output(
            item_id,
            {"input": payload, "scenario": scenario, "result": "synthetic success"},
        )
        adapter.release_input(item_id, State.DONE)
        return {"item_id": item_id, "output_id": output_id}
    """
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_atomic_proof(proof_dir: Path, runtime_kind: str, proof: object) -> Path:
    if runtime_kind not in {"frozen", "go-wrapper"}:
        raise ValueError("unknown native Runtime kind")
    proof_path = proof_dir / f"{runtime_kind}.json"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=proof_dir, delete=False
        ) as stream:
            json.dump(proof, stream, indent=2)
            stream.write("\n")
            temporary = Path(stream.name)
        temporary.replace(proof_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return proof_path


@pytest.mark.integration_test
@pytest.mark.parametrize(
    ("runtime_kind", "executable_variable"),
    [
        ("frozen", "DAKOTA_WORKITEMS_FROZEN_EXECUTABLE"),
        ("go-wrapper", "DAKOTA_WORKITEMS_GO_WRAPPER_EXECUTABLE"),
    ],
)
def test_packaged_runtime_executes_work_item_consumer_lifecycle(
    runtime_kind: str,
    executable_variable: str,
    action_server_process,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise consumer transitions and persistence through native Runtime HTTP."""
    executable = os.environ.get(executable_variable)
    assert (
        executable and Path(executable).is_file()
    ), f"Run the {runtime_kind} acceptance with its built executable selected explicitly"
    rcc_home = os.environ.get("DAKOTA_WORKITEMS_RCC_HOME")
    assert rcc_home and Path(rcc_home).is_dir(), "Use the task-owned RCC home"
    monkeypatch.setenv("ACTIONS_HOME", rcc_home)
    monkeypatch.setenv("ROBOCORP_HOME", rcc_home)
    monkeypatch.setenv("SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE", executable)
    proof_dir_value = os.environ.get("DAKOTA_WORKITEMS_PROOF_DIR")
    assert (
        proof_dir_value and Path(proof_dir_value).is_dir()
    ), "Use a fresh proof directory"
    proof_dir = Path(proof_dir_value)
    expected_executable_hash = os.environ.get(
        f"DAKOTA_WORKITEMS_{runtime_kind.upper().replace('-', '_')}_SHA256"
    )
    assert expected_executable_hash
    executable_hash = _sha256(Path(executable))
    assert executable_hash == expected_executable_hash
    core_wheel_value = os.environ.get("DAKOTA_WORKITEMS_CORE_WHEEL")
    expected_core_wheel_hash = os.environ.get("DAKOTA_WORKITEMS_CORE_WHEEL_SHA256")
    assert core_wheel_value and expected_core_wheel_hash
    core_wheel_hash = _sha256(Path(core_wheel_value))
    assert core_wheel_hash == expected_core_wheel_hash

    from actions.work_items import State

    from actions.server._selftest import ActionServerClient, ActionServerProcess

    proof: CaseProof = {
        "schema_version": 1,
        "runtime_kind": runtime_kind,
        "executable_sha256": executable_hash,
        "actions_core_wheel_sha256": core_wheel_hash,
        "consumer_actions": [],
        "api_state_readbacks": {},
    }

    def save_proof() -> None:
        _write_atomic_proof(proof_dir, runtime_kind, proof)

    project = tmp_path / "synthetic-consumer-package"
    project.mkdir()
    (project / "package.yaml").write_text(
        f"""version: 1
dependencies:
  conda-forge:
    - python=3.12
    - uv=0.9.26
  local-wheels:
    - {Path(os.environ['DAKOTA_WORKITEMS_CORE_WHEEL']).resolve()}
  pypi:
    - actions-work-items=0.4.4
""",
        encoding="utf-8",
    )
    (project / "dakota_workitems_processor.py").write_text(
        PROCESSOR_ACTION, encoding="utf-8"
    )
    action_server_process.start(
        db_file="server.db",
        cwd=project,
        actions_sync=True,
        timeout=600,
        min_processes=1,
        max_processes=1,
    )
    client = ActionServerClient(action_server_process)
    package_action = "/api/actions/synthetic-consumer-package/process-work-item/run"

    def create(payload: dict[str, str]) -> str:
        response = client.post_get_response("/api/work-items", {"payload": payload})
        return response.json()["id"]

    def execute(item_id: str, scenario: str):
        return client.post_get_response(
            package_action,
            {
                "db_path": str(action_server_process.datadir / "workitems.db"),
                "files_dir": str(action_server_process.datadir / "work_item_files"),
                "expected_id": item_id,
                "scenario": scenario,
            },
        )

    success_id = create({"case": "success"})
    database = action_server_process.datadir / "workitems.db"
    assert database.is_file() and database.parent == action_server_process.datadir
    success_run = execute(success_id, "success")
    assert success_run.status_code == 200
    success = client.get_json(f"/api/work-items/{success_id}")
    assert success["state"] == State.DONE.value
    success_output_id = success_run.json()["output_id"]
    success_output = client.get_json(f"/api/work-items/{success_output_id}")
    assert success_output["parent_id"] == success_id
    assert success_output["queue_name"] == "default_output"
    assert success_output["payload"] == {
        "input": {"case": "success"},
        "scenario": "success",
        "result": "synthetic success",
    }
    proof["consumer_actions"].append({"scenario": "success", "http_status": 200})
    proof["api_state_readbacks"]["after_success"] = {
        "input_state": success["state"],
        "output_state": success_output["state"],
        "output_queue": success_output["queue_name"],
        "parent_link_verified": success_output["parent_id"] == success_id,
    }
    save_proof()

    failure_id = create({"case": "failure"})
    client.post_error(
        package_action,
        500,
        {
            "db_path": str(database),
            "files_dir": str(action_server_process.datadir / "work_item_files"),
            "expected_id": failure_id,
            "scenario": "fail",
        },
    )
    failed = client.get_json(f"/api/work-items/{failure_id}")
    assert failed["state"] == State.FAILED.value
    assert failed["error_code"] == "SYNTHETIC_PROCESSOR_FAILURE"
    assert failed["error_message"] == "synthetic consumer failure"
    proof["consumer_actions"].append({"scenario": "failure", "http_status": 500})
    proof["api_state_readbacks"]["after_failure"] = {
        "input_state": failed["state"],
        "error_code": failed["error_code"],
        "error_message": failed["error_message"],
    }
    save_proof()

    recovery_id = create({"case": "recovery"})
    stale_reservation = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    # Seed a stale row; this does not simulate a process crash. The consumer performs recovery and retry.
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE work_items SET state = ?, reserved_at = ? WHERE id = ?",
            (State.IN_PROGRESS.value, stale_reservation, recovery_id),
        )
    recovery_run = execute(recovery_id, "recover")
    assert recovery_run.status_code == 200
    recovered = client.get_json(f"/api/work-items/{recovery_id}")
    assert recovered["state"] == State.DONE.value
    recovery_output_id = recovery_run.json()["output_id"]
    recovery_output = client.get_json(f"/api/work-items/{recovery_output_id}")
    assert recovery_output["parent_id"] == recovery_id
    assert recovery_output["payload"]["input"] == {"case": "recovery"}
    proof["consumer_actions"].append({"scenario": "recovery", "http_status": 200})
    proof["api_state_readbacks"]["after_recovery"] = {
        "input_state": recovered["state"],
        "output_state": recovery_output["state"],
        "parent_link_verified": recovery_output["parent_id"] == recovery_id,
    }
    save_proof()

    stats = client.get_json("/api/work-items/stats")
    assert stats == {
        "queue_name": "default",
        "pending": 0,
        "in_progress": 0,
        "done": 2,
        "failed": 1,
        "total": 3,
    }

    # Restart the same packaged executable against the Runtime-owned data directory.
    action_server_process.stop()
    restarted = ActionServerProcess(action_server_process.datadir)
    try:
        restarted.start(
            db_file="server.db",
            cwd=project,
            actions_sync=True,
            timeout=600,
            max_processes=1,
        )
        restarted_client = ActionServerClient(restarted)
        assert (
            restarted_client.get_json(f"/api/work-items/{success_id}")["state"]
            == State.DONE.value
        )
        assert (
            restarted_client.get_json(f"/api/work-items/{failure_id}")["state"]
            == State.FAILED.value
        )
        assert (
            restarted_client.get_json(f"/api/work-items/{recovery_id}")["state"]
            == State.DONE.value
        )
        assert (
            restarted_client.get_json(f"/api/work-items/{success_output_id}")[
                "parent_id"
            ]
            == success_id
        )
        assert (
            restarted_client.get_json(f"/api/work-items/{recovery_output_id}")[
                "parent_id"
            ]
            == recovery_id
        )
        assert restarted_client.get_json("/api/work-items/stats") == stats
        proof["api_state_readbacks"]["after_restart"] = {
            "success_state": State.DONE.value,
            "failure_state": State.FAILED.value,
            "recovery_state": State.DONE.value,
            "stats": stats,
            "output_parent_links_verified": True,
        }
        save_proof()
    finally:
        restarted.stop()
