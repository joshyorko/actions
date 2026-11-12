"""Read-only installed-Runtime child observation; never signals or authorizes work.

Call with the installed candidate interpreter. Returned records contain no argv,
credentials, source paths, or raw database payloads. No process is spawned here.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from uuid import UUID

import psutil


class ObservationUnavailable(RuntimeError):
    pass


def _hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value):
    value = value.removeprefix("sha256:")
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("exact SHA256 required")
    return value


def _live(pid, birth):
    process = psutil.Process(pid)
    if process.create_time() != birth or process.status() == psutil.STATUS_ZOMBIE:
        raise ObservationUnavailable("original live process identity unavailable")
    return process


def _under(path, root):
    return Path(path).resolve().is_relative_to(root)


def _ancestor(process, ancestor_pid, ancestor_birth):
    for parent in process.parents():
        if parent.pid == ancestor_pid:
            return parent.create_time() == ancestor_birth
    return False


def _read_launch(database_path, run_id, artifact_digest):
    from actions.server.foundry.robot_execution import DISCRIMINATOR, RobotLaunchIntent
    from actions.server.foundry.robot_journal import _decode, _launch
    from actions.server.run_outputs.claimed_intent import claimed_intent
    from actions.server.run_outputs.types import AttemptFence
    from actions.server.run_outputs.service import _canonical

    with sqlite3.connect(Path(database_path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        def one(table):
            rows = db.execute("SELECT * FROM " + table + " WHERE id=?", (run_id,)).fetchall()
            if len(rows) != 1:
                raise ObservationUnavailable("exact Task SQL identity unavailable")
            return dict(rows[0])
        run, pin, receipt, raw = (one(name) for name in (
            "run", "run_pin", "run_task_receipt", "run_execution_intent"
        ))
        if not run["result"]:
            return None
        record = json.loads(run["result"])
        if record.get("launch") is None:
            return None
        intent = claimed_intent(raw["envelope_json"])
        launch = record["launch"]
        fence = AttemptFence.model_validate(launch["fence"])
        selection = _decode(launch["selection"])
        expected = _launch(RobotLaunchIntent(selection, fence, launch["launch_id"]))
        attempts = db.execute("SELECT * FROM run_attempt WHERE id=?", (fence.attempt_id,)).fetchall()
        if len(attempts) != 1:
            raise ObservationUnavailable("exact Attempt unavailable")
        attempt = dict(attempts[0])
        if (
            set(record) != {"version", "mode", "claim", "fence", "launch"}
            or record["version"] != DISCRIMINATOR or record["mode"] != "work-items"
            or launch != expected or record["fence"] != fence.model_dump(mode="json")
            or intent is None or selection.snapshot != intent.snapshot
            or record["claim"] != {"item_id": intent.claim.item_id,
                                   "owner_id": intent.claim.owner_id, "epoch": intent.claim.epoch}
            or fence.run_id != run_id or pin["run_id"] != run_id
            or receipt["run_id"] != run_id or raw["id"] != run_id
            or receipt["receipt_version"] != "actions.run-task-receipt/claimed-v1"
            or receipt["original_method"] != "tools/call"
            or receipt["original_tool_name"] != "capability_invoke"
            or receipt["result_contract_version"] != "actions.detached-invocation-result/v1"
            or raw["actor_id"] != receipt["admission_principal_id"]
            or raw["actor_id"] != pin["admission_principal_id"]
            or any(row["workspace_id"] != selection.snapshot.workspace_id
                   for row in (pin, receipt, raw, attempt))
            or run["status"] != 1 or pin["cancel_requested"] != 0
            or pin["current_attempt_id"] != fence.attempt_id or pin["epoch"] != fence.epoch
            or attempt["run_id"] != run_id or attempt["epoch"] != fence.epoch
            or attempt["owner_id"] != fence.owner_id or fence.owner_id != intent.claim.owner_id
            or attempt["state"] != "running" or selection.plan_kind != "rcc"
            or selection.rcc_artifact_digest != artifact_digest
            or json.loads(run["inputs"]) != json.loads(selection.inputs)
            or "sha256:" + hashlib.sha256(_canonical(json.loads(selection.inputs), 262144).encode()).hexdigest() != intent.input_digest
        ):
            raise ObservationUnavailable("retained Task launch identity differs")
        return launch, selection, fence


def observe(runtime_pid, runtime_birth, database_path, run_id, rcc_sha256,
            artifact_digest, prepared_home, python_sha256, timeout_seconds=30):
    """Observe one exact live RCC wrapper/Python pair; fail closed on ambiguity."""
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor, build_exec_command
    from actions.server.foundry.robot_execution import _CHILD

    if str(UUID(run_id)) != run_id or not 0 < timeout_seconds <= 30:
        raise ValueError("canonical Run and bounded observation required")
    rcc_sha256, python_sha256 = _digest(rcc_sha256), _digest(python_sha256)
    artifact_digest = "sha256:" + _digest(artifact_digest)
    home = Path(prepared_home).resolve(strict=True)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        runtime = _live(runtime_pid, runtime_birth)
        retained = _read_launch(database_path, run_id, artifact_digest)
        if retained is None:
            time.sleep(0.1)
            continue
        launch, selection, fence = retained
        matches = []
        children = runtime.children(recursive=True)
        if len(children) > 4096:
            raise ObservationUnavailable("bounded process inventory exceeded")
        for wrapper in children:
            try:
                birth = wrapper.create_time()
                exe = wrapper.exe()
                if _hash(exe) != rcc_sha256:
                    continue
                source = Path(wrapper.cwd()).resolve(strict=True)
                directory = source.parent
                if source.name != "source" or directory.name != launch["launch_id"]:
                    continue
                args = ["-I", "-B", "-c", _CHILD, str(source), selection.suite_path,
                        selection.suite_name, selection.task_name,
                        str(directory / "input.json"), str(directory / "output.xml")]
                expected = build_exec_command(
                    Path(exe), RccRuntimeDescriptor(artifact_digest=artifact_digest, provider_reference="local"),
                    ["python", *args], receipt_file=directory / "rcc-receipt.json",
                    local_trust_carrier=home / "artifacts/v1/trust")
                expected.insert(1, "--no-build")
                command = wrapper.cmdline()
                # argv[0] may name a symlink; executable bytes are independently pinned.
                if command[1:] != expected[1:] or Path(command[0]).resolve() != Path(exe).resolve():
                    continue
                if (directory / "input.json").read_bytes() != selection.inputs:
                    continue
                if "sha256:" + _hash(source / "package.yaml") != selection.package_yaml_digest:
                    continue
                group = os.getpgid(wrapper.pid)
                if group != wrapper.pid or not _ancestor(wrapper, runtime_pid, runtime_birth):
                    continue
                for child in wrapper.children(recursive=True):
                    child_birth = child.create_time()
                    child_exe = child.exe()
                    child_cwd = child.cwd()
                    if (_hash(child_exe) != python_sha256
                        or not _under(child_exe, home) or not _under(child_cwd, home)
                        or child.cmdline()[1:] != args
                        or os.getpgid(child.pid) != group
                        or not _ancestor(child, wrapper.pid, birth)):
                        continue
                    _live(wrapper.pid, birth)
                    _live(child.pid, child_birth)
                    _live(runtime_pid, runtime_birth)
                    records = []
                    for role, process, created, digest, cwd in (
                        ("rcc", wrapper, birth, rcc_sha256, str(source)),
                        ("python", child, child_birth, python_sha256, child_cwd),
                    ):
                        records.append({"role": role, "pid": process.pid, "birth": created,
                            "pgid": group, "executable_sha256": digest,
                            "cwd_sha256": hashlib.sha256(cwd.encode()).hexdigest(),
                            "run_id": run_id, "attempt_id": fence.attempt_id,
                            "launch_id": launch["launch_id"]})
                    matches.append(records)
            except (psutil.NoSuchProcess, FileNotFoundError, ProcessLookupError):
                continue
        if len(matches) > 1:
            raise ObservationUnavailable("ambiguous exact launch process pairs")
        if matches:
            if _read_launch(database_path, run_id, artifact_digest) != retained:
                raise ObservationUnavailable("launch changed during observation")
            for record in matches[0]:
                _live(record["pid"], record["birth"])
            return matches[0]
        time.sleep(0.1)
    raise ObservationUnavailable("exact live Robot child not observed before deadline")


def assert_absent(records):
    """Require both original process identities absent; zombies do not pass."""
    if len(records) != 2 or {r["role"] for r in records} != {"rcc", "python"}:
        raise ValueError("exact observed wrapper and Python records required")
    for record in records:
        try:
            current = psutil.Process(record["pid"])
            if current.create_time() == record["birth"]:
                raise ObservationUnavailable("original observed process still present")
        except psutil.NoSuchProcess:
            pass
