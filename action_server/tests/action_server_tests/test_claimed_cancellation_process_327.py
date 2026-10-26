# ruff: noqa: F811
"""Real direct Robot child and SQLite Task transition; not installed/RCC proof."""
import json
from pathlib import Path

import psutil
from action_server_tests import test_robot_claimed_work_items_327 as fixture
from action_server_tests.test_claimed_task_service import create, setup
from action_server_tests.test_robot_package_admission import request_for

from actions.server._models import RunStatus
from actions.server.foundry.robot_package_builder import RobotPackageRequest
from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner

claimed = fixture.claimed
disable_feedback = fixture.disable_feedback
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def test_live_direct_child_cancel_is_terminal_and_absent(
    claimed, monkeypatch, tmp_path
):
    def sleeping_request():
        raw = request_for().model_dump(mode="json", by_alias=True)
        raw["files"][0]["content"] = "*** Tasks ***\nOwned\n    Sleep    30s\n"
        return RobotPackageRequest.model_validate_json(json.dumps(raw))

    monkeypatch.setattr(fixture, "request_for", sleeping_request)
    c = claimed()
    t = setup(c)
    first = create(c, t)
    ticket = t.worker.claim(first.task_id)
    execution = tmp_path / "real-child"
    runner = PinnedRobotRunner(c.runner.preparation, execution)
    observed = []

    def cancelled():
        if observed:
            return True
        for child in psutil.Process().children(recursive=True):
            try:
                if (
                    any(arg.startswith(str(execution) + "/") for arg in child.cmdline())
                    and Path(child.exe()).resolve()
                    == c.runner.preparation.python.resolve()
                ):
                    observed.append((child.pid, child.create_time()))
                    t.tasks.cancel(
                        c.caller.actor, t.snapshot.workspace_id, first.task_id
                    )
                    return True
            except psutil.NoSuchProcess:
                continue
        return False

    result = runner.execute(c.caller, ticket, c.owner, cancelled=cancelled)
    assert observed, "must observe the actual admitted direct child before cancellation"
    assert result.status == RunStatus.CANCELLED
    assert (
        t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id).status
        == "cancelled"
    )
    assert create(c, t).status == "cancelled"
    for pid, birth in observed:
        try:
            assert (
                psutil.Process(pid).create_time() != birth
            ), "original child still present"
        except psutil.NoSuchProcess:
            pass
