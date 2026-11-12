"""Adapter-only cancellation evidence; no durable terminal authority is granted."""
import io
from types import SimpleNamespace

import pytest
from actions.work_items._fencing import ClaimRejected
from contract_tests.test_robot_execution import case as case_fixture

from actions.server._common.process import ProcessTreeCleanupResult
from actions.server.foundry import robot_execution as module
from actions.server.run_outputs.service import FenceRejected

case = case_fixture


@pytest.mark.parametrize("phase", ["running", "after_cleanup"])
def test_explicit_cancel_retains_exact_launch_and_cleanup(case, monkeypatch, phase):
    outcome, host, cleanup = exercise(case, monkeypatch, phase)
    assert isinstance(outcome, module.RobotCancellationStopped)
    assert outcome.launch is host.intent
    assert outcome.launch.fence == case[4]
    assert outcome.launch.selection == case[1]
    assert outcome.cleanup is cleanup
    assert outcome.directory.name == host.intent.launch_id
    assert not host.staged


@pytest.mark.parametrize(
    "phase",
    [
        "before_launch",
        "after_intent",
        "generic",
        "callback_error",
        "incomplete",
        "same_message",
    ],
)
def test_other_failures_never_issue_cancellation_evidence(case, monkeypatch, phase):
    outcome, host, _ = exercise(case, monkeypatch, phase)
    assert not isinstance(outcome, module.RobotCancellationStopped)
    if phase == "before_launch":
        assert host.intent is None
    elif phase == "after_intent":
        assert host.intent is not None
        assert str(outcome) == "Robot execution cancelled"
    elif phase == "incomplete":
        assert isinstance(outcome, module.RobotCleanupIncomplete)
    elif phase == "same_message":
        assert str(outcome) == "Robot execution cancelled"
    else:
        assert isinstance(outcome, RuntimeError)
        assert str(outcome) == "original failure"
    assert not host.staged


@pytest.mark.parametrize("failure", [FenceRejected, ClaimRejected])
@pytest.mark.parametrize("recheck", ["true", "false", "error", "incomplete"])
def test_cancellation_race_requires_cleanup_and_explicit_recheck(
    case, monkeypatch, failure, recheck
):
    original = failure("original fence failure")
    outcome, host, cleanup = exercise(
        case, monkeypatch, "race", race_error=original, recheck=recheck
    )
    if recheck == "true":
        assert isinstance(outcome, module.RobotCancellationStopped)
        assert outcome.__cause__ is original
        assert outcome.launch is host.intent and outcome.cleanup is cleanup
    elif recheck == "false":
        assert outcome is original
    elif recheck == "error":
        assert not isinstance(outcome, module.RobotCancellationStopped)
        assert str(outcome) == "recheck failed"
        assert outcome.__cause__ is original
    else:
        assert isinstance(outcome, module.RobotCleanupIncomplete)
        assert outcome.__cause__ is original
    assert not host.staged


def test_generic_failure_never_rechecks_cancellation(case, monkeypatch):
    original = RuntimeError("generic failure")
    outcome, _, _ = exercise(
        case, monkeypatch, "race", race_error=original, recheck="forbidden"
    )
    assert outcome is original


@pytest.mark.parametrize("phase", ["cleanup_lifecycle", "staging"])
@pytest.mark.parametrize("failure", [FenceRejected, ClaimRejected, RuntimeError])
@pytest.mark.parametrize("recheck", ["true", "false", "error"])
def test_post_cleanup_authority_race(case, monkeypatch, phase, failure, recheck):
    original = failure("post-cleanup failure")
    outcome, host, cleanup = exercise(
        case, monkeypatch, phase, race_error=original, recheck=recheck
    )
    if failure is RuntimeError or recheck == "false":
        assert outcome is original
    elif recheck == "error":
        assert str(outcome) == "recheck failed"
        assert outcome.__cause__ is original
    else:
        assert isinstance(outcome, module.RobotCancellationStopped)
        assert outcome.__cause__ is original
        assert outcome.launch is host.intent and outcome.cleanup is cleanup
    assert not host.staged


def exercise(case, monkeypatch, phase, *, race_error=None, recheck=None):
    runner, selection, archive, actor, fence, host = case
    state = {"spawned": False, "cleaned": False, "rejected": False}
    cleanup = ProcessTreeCleanupResult(
        True, (123,) if phase == "incomplete" or recheck == "incomplete" else (), (), ()
    )

    def spawn(*args, **kwargs):
        state["spawned"] = True
        if phase == "staging":
            (kwargs["cwd"].parent / "output.xml").write_text(
                '<robot generator="Robot 7.4.2 test"><suite name="Tasks">'
                '<test name="Selected"><status status="PASS"/></test></suite></robot>'
            )
        return SimpleNamespace(
            stdout=io.BytesIO(), stderr=io.BytesIO(), poll=lambda: 0, returncode=0
        )

    def clean(*args, **kwargs):
        state["cleaned"] = True
        return cleanup

    class Selector:
        def register(self, *args):
            pass

        def get_map(self):
            return phase not in ("after_cleanup", "cleanup_lifecycle", "staging")

        def close(self):
            pass

    def cancelled():
        if (
            state["cleaned"]
            and recheck is not None
            and (phase == "race" or state["rejected"])
        ):
            if recheck in ("forbidden", "incomplete"):
                pytest.fail("cancellation callback must not be rechecked")
            if recheck == "error":
                raise RuntimeError("recheck failed")
            return recheck == "true"
        if phase == "before_launch":
            return True
        if phase == "after_intent":
            return host.intent is not None
        if state["spawned"] and phase == "callback_error":
            raise RuntimeError("original failure")
        return (
            state["spawned"]
            and phase in ("running", "incomplete")
            or (state["cleaned"] and phase == "after_cleanup")
        )

    original_check = host.check_live

    def check(*args):
        if race_error is not None and (
            (state["spawned"] and phase == "race")
            or (state["cleaned"] and phase == "cleanup_lifecycle")
        ):
            state["rejected"] = True
            raise race_error
        if state["spawned"] and phase == "same_message":
            raise module.RobotExecutionError("Robot execution cancelled")
        if state["spawned"] and phase == "generic":
            raise RuntimeError("original failure")
        return original_check(*args)

    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    monkeypatch.setattr(module.selectors, "DefaultSelector", Selector)
    monkeypatch.setattr(runner, "_cleanup", clean)
    monkeypatch.setattr(host, "check_live", check)
    if phase == "staging":

        def stage(*args, **kwargs):
            state["rejected"] = True
            raise race_error

        monkeypatch.setattr(host, "stage_output", stage)
    with pytest.raises(Exception) as caught:
        runner.execute(
            actor,
            fence,
            selection=selection,
            source_archive=archive,
            lifecycle=host,
            cancelled=cancelled,
            timeout_seconds=10,
        )
    if phase in ("before_launch", "after_intent"):
        assert not state["spawned"] and not state["cleaned"]
    else:
        assert state["spawned"] and state["cleaned"]
    return caught.value, host, cleanup
