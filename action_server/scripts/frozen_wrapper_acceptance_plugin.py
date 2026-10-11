"""Prove wrapper-to-frozen process identity for the frozen catalog control."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import psutil
import pytest

_records: list[dict[str, Any]] = []
_active_nodeid = ""
_original_start = None
_original_stop = None
_digests: dict[Path, str] = {}
_artifact_verification: dict[str, Any] = {}


def _sha256(path: Path) -> str:
    path = path.resolve(strict=True)
    cached = _digests.get(path)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    _digests[path] = value
    return value


def _start_identity(process) -> dict[str, Any]:
    wrapper_path = Path(
        os.environ["SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE"]
    ).resolve(strict=True)
    wrapper = psutil.Process(process.process.pid)
    actual_wrapper = Path(wrapper.exe()).resolve(strict=True)
    if actual_wrapper != wrapper_path:
        raise AssertionError(
            f"Popen parent is {actual_wrapper}, expected Go wrapper {wrapper_path}"
        )
    wrapper_sha = _sha256(actual_wrapper)
    expected_wrapper_sha = _artifact_verification["binary_sha256"]
    if wrapper_sha != expected_wrapper_sha:
        raise AssertionError(
            "launched Go wrapper digest differs from measured artifact"
        )

    children = wrapper.children(recursive=False)
    if len(children) != 1:
        raise AssertionError(
            f"Go wrapper must own exactly one direct Runtime child; got {len(children)}"
        )
    child = children[0]
    actual_frozen = Path(child.exe()).resolve(strict=True)
    child_home = Path(process.process._env["HOME"]).resolve()
    cached_paths = list(
        child_home.glob(".actions/bin/action-server/internal/*/action-server")
    )
    if len(cached_paths) != 1 or actual_frozen != cached_paths[0].resolve(strict=True):
        raise AssertionError(
            "direct wrapper child is not the single executable cached under its HOME"
        )
    frozen_sha = _sha256(actual_frozen)
    expected_frozen_sha = _artifact_verification["frozen_binary_sha256"]
    if frozen_sha != expected_frozen_sha:
        raise AssertionError(
            "wrapper child digest differs from the measured frozen executable"
        )
    if child.ppid() != wrapper.pid:
        raise AssertionError("measured frozen executable is not the wrapper's child")

    return {
        "test_nodeid": _active_nodeid,
        "identity_verified": True,
        "wrapper_pid": wrapper.pid,
        "wrapper_create_time": wrapper.create_time(),
        "wrapper_path": str(actual_wrapper),
        "wrapper_sha256": wrapper_sha,
        "frozen_child_pid": child.pid,
        "frozen_child_create_time": child.create_time(),
        "frozen_child_path": str(actual_frozen),
        "frozen_child_sha256": frozen_sha,
        "frozen_child_parent_pid": child.ppid(),
        "child_home": str(child_home),
        "natural_exit": False,
        "stop_observed": False,
        "stop_failure": None,
    }


def _has_verified_child_identity(record: dict[str, Any]) -> bool:
    return (
        record.get("identity_verified") is True
        and isinstance(record.get("wrapper_pid"), int)
        and not isinstance(record.get("wrapper_pid"), bool)
        and isinstance(record.get("frozen_child_pid"), int)
        and not isinstance(record.get("frozen_child_pid"), bool)
        and isinstance(record.get("frozen_child_create_time"), (int, float))
        and not isinstance(record.get("frozen_child_create_time"), bool)
        and record.get("frozen_child_parent_pid") == record.get("wrapper_pid")
    )


def _successful_lifecycle(record: dict[str, Any]) -> bool:
    return (
        record.get("natural_exit") is True
        and record.get("stop_observed") is True
        and record.get("stop_failure") is None
        and _has_verified_child_identity(record)
        and record.get("wrapper_returncode") is not None
    )


def _set_stop_failure(record: dict[str, Any], message: str) -> None:
    if record.get("stop_failure") is None:
        record["stop_failure"] = message
    record["natural_exit"] = False


def pytest_configure(config) -> None:
    if os.environ.get("SEMA4AI_INTEGRATION_TEST_GO_WRAPPER") != "1":
        raise pytest.UsageError("wrapper identity plugin requires the wrapper job flag")
    verification_path = Path(os.environ["WRAPPER_ARTIFACT_VERIFICATION"])
    try:
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise pytest.UsageError(
            "verified wrapper artifact receipt is unavailable"
        ) from error
    if verification.get("archive_and_member_verified") is not True:
        raise pytest.UsageError("wrapper artifact was not verified before execution")
    global _artifact_verification
    _artifact_verification = verification
    from actions.server._selftest import ActionServerProcess

    global _original_start, _original_stop
    _original_start = ActionServerProcess.start
    _original_stop = ActionServerProcess.stop

    def observed_start(instance, *args, **kwargs):
        result = _original_start(instance, *args, **kwargs)
        try:
            record = _start_identity(instance)
        except Exception as error:
            _records.append(
                {
                    "test_nodeid": _active_nodeid,
                    "identity_verified": False,
                    "wrapper_pid": instance.process.pid,
                    "natural_exit": False,
                    "stop_observed": False,
                    "stop_failure": f"startup identity check failed: {error}",
                    "process_handle": instance.process,
                }
            )
            raise
        record["process_handle"] = instance.process
        _records.append(record)
        return result

    def observed_stop(instance, *args, **kwargs):
        record = next(
            (
                item
                for item in reversed(_records)
                if item["wrapper_pid"] == instance.process.pid
                and not item["natural_exit"]
                and not item["stop_observed"]
            ),
            None,
        )
        if record is not None:
            record["stop_observed"] = True
            if not _has_verified_child_identity(record):
                _set_stop_failure(
                    record, "frozen child identity was not verified before cleanup"
                )
            else:
                handle = record["process_handle"]
                try:
                    child = psutil.Process(record["frozen_child_pid"])
                    child_alive = (
                        child.create_time() == record["frozen_child_create_time"]
                        and child.is_running()
                    )
                except psutil.NoSuchProcess:
                    child_alive = False
                except Exception as error:
                    child_alive = True
                    _set_stop_failure(
                        record, f"could not verify frozen child exit: {error}"
                    )
                wrapper_returncode = handle.returncode
                if (
                    wrapper_returncode is not None
                    and not child_alive
                    and record.get("stop_failure") is None
                ):
                    record["wrapper_returncode"] = wrapper_returncode
                    record["natural_exit"] = True
                else:
                    _set_stop_failure(
                        record,
                        "launcher or frozen child was still running before cleanup",
                    )
        try:
            return _original_stop(instance, *args, **kwargs)
        except Exception as error:
            if record is not None:
                _set_stop_failure(record, f"normal process cleanup failed: {error}")
            raise

    ActionServerProcess.start = observed_start
    ActionServerProcess.stop = observed_stop


def pytest_runtest_setup(item) -> None:
    global _active_nodeid
    _active_nodeid = item.nodeid


def pytest_runtest_teardown(item, nextitem) -> None:
    del item, nextitem
    global _active_nodeid
    _active_nodeid = ""


def pytest_sessionfinish(session, exitstatus) -> None:
    output = Path(os.environ["WRAPPER_PROCESS_EVIDENCE"])
    completed = [record for record in _records if _successful_lifecycle(record)]
    expected_nodes = {item.nodeid for item in session.items}
    observed_nodes = {record["test_nodeid"] for record in completed}
    missing_nodes = sorted(expected_nodes - observed_nodes)
    failures = []
    node_status = {}
    for nodeid in sorted(expected_nodes):
        attempts = [record for record in _records if record["test_nodeid"] == nodeid]
        natural_exits = sum(_successful_lifecycle(record) for record in attempts)
        node_status[nodeid] = {
            "attempted": len(attempts),
            "natural_wrapper_and_child_exits": natural_exits,
            "failed": sum(not record["natural_exit"] for record in attempts),
            "status": "PASS" if attempts and natural_exits == len(attempts) else "FAIL",
        }
    expected_nodes_without_natural_exit = sorted(
        nodeid for nodeid, result in node_status.items() if result["status"] != "PASS"
    )
    if missing_nodes:
        failures.append(
            f"no wrapper lifecycle proof for selected nodes: {missing_nodes}"
        )
    if expected_nodes_without_natural_exit:
        failures.append(
            "wrapper lifecycle did not exit naturally for nodes: "
            f"{expected_nodes_without_natural_exit}"
        )
    if len(completed) != len(_records):
        failures.append("one or more wrapper children did not exit naturally")
    stop_failures = [
        f"{record['test_nodeid']}: {record['stop_failure']}"
        for record in _records
        if record.get("stop_failure") is not None
    ]
    if stop_failures:
        failures.append(
            f"wrapper process lifecycle verification failed: {stop_failures}"
        )
    receipt = {
        "expected_wrapper_sha256": _artifact_verification["binary_sha256"],
        "expected_frozen_binary_sha256": _artifact_verification["frozen_binary_sha256"],
        "selected_test_nodes": sorted(expected_nodes),
        "process_lifecycles": [
            {key: value for key, value in record.items() if key != "process_handle"}
            for record in _records
        ],
        "per_node": node_status,
        "natural_wrapper_and_child_shutdowns": len(completed),
        "missing_test_nodes": missing_nodes,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if failures:
        session.exitstatus = 1


def pytest_unconfigure(config) -> None:
    if _original_start is not None and _original_stop is not None:
        from actions.server._selftest import ActionServerProcess

        ActionServerProcess.start = _original_start
        ActionServerProcess.stop = _original_stop
