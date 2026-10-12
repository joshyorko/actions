"""Cancellation admission controls with persisted Runs and a held executor."""

from concurrent.futures import Future
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


class HeldExecutor:
    def __init__(self):
        self.target = None
        self.future = Future()

    def submit(self, target):
        assert self.target is None
        self.target = target
        return self.future

    def release(self):
        assert self.target is not None
        try:
            self.future.set_result(self.target())
        except BaseException as error:
            self.future.set_exception(error)


@pytest.fixture
def admitted_runner(tmp_path, monkeypatch):
    from actions.server import (
        _actions_process_pool,
        _actions_run,
        _artifact_storage,
        _settings,
    )
    from actions.server._models import Action, ActionPackage, create_db
    from actions.server._robo_utils import run_in_thread
    from actions.server._runs_state_cache import use_runs_state_ctx
    from actions.server._settings import HEADER_ACTIONS_ASYNC_TIMEOUT

    class Storage:
        def create_run_artifacts_dir(self, relative):
            path = tmp_path / relative
            path.mkdir()
            return path

        def bind_run(self, *_):
            pass

        def run_artifacts_dir(self, relative):
            return tmp_path / relative

    class Pool:
        def __init__(self):
            self.calls = []

        def obtain_process_for_action(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            pytest.fail("cancelled queued Run must not acquire an action process")

    class Response:
        def set_run_id(self, run_id):
            self.run_id = run_id

        def set_async_completion(self):
            self.async_completion = True

    executor = HeldExecutor()
    pool = Pool()
    monkeypatch.setattr(run_in_thread, "run_in_thread", executor.submit)
    monkeypatch.setattr(_actions_process_pool, "get_actions_process_pool", lambda: pool)
    monkeypatch.setattr(_artifact_storage, "get_artifact_storage", lambda: Storage())
    monkeypatch.setattr(
        _settings, "get_settings", lambda: SimpleNamespace(base_url="http://127.0.0.1")
    )
    package = ActionPackage("package", "package", str(tmp_path), "unused", "{}")
    action = Action("action", package.id, "queued", "", "unused.py", 1, "{}", "{}")
    with create_db(tmp_path / "runs.db") as db, use_runs_state_ctx(db) as state:
        with db.transaction():
            db.insert(package)
            db.insert(action)
        runner = _actions_run._ActionsRunner(
            package,
            action,
            {},
            {},
            lambda inputs: None,
            lambda output: None,
            {},
            Response(),
            {HEADER_ACTIONS_ASYNC_TIMEOUT: "0"},
            {},
            process_pool_generation=1,
        )
        yield SimpleNamespace(
            runner=runner, executor=executor, pool=pool, state=state, db=db
        )
        if not executor.future.done():
            executor.future.cancel()


def test_async_zero_admits_cancel_before_held_worker_runs(admitted_runner):
    from actions.server._api_run import cancel_run
    from actions.server._models import Run, RunStatus

    case = admitted_runner
    assert case.runner.run_in_thread() == "async-return"
    run = case.db.first(Run, "SELECT * FROM run WHERE id=?", [case.runner._run_id])
    assert run.status == RunStatus.NOT_RUN
    assert case.executor.target is not None and not case.executor.future.done()
    assert cancel_run(run.id) == "cancelled"
    info = case.state._run_id_to_runtime_info[run.id]
    assert info.is_canceled()
    case.executor.release()
    with pytest.raises(HTTPException) as caught:
        case.executor.future.result()
    assert caught.value.status_code == 500
    assert not case.pool.calls
    run = case.db.first(Run, "SELECT * FROM run WHERE id=?", [run.id])
    assert run.status == RunStatus.CANCELLED
    assert cancel_run(run.id) == "not-running"
    assert run.id not in case.state._run_id_to_runtime_info


@pytest.mark.parametrize("error_type", [RuntimeError, BaseException])
def test_submission_failure_preserves_primary_and_retires_own_state(
    admitted_runner, monkeypatch, error_type
):
    from actions.server._robo_utils import run_in_thread

    case = admitted_runner
    primary = error_type("owned executor refused submission")
    observed = []

    def refuse(target):
        observed.append(case.state._run_id_to_runtime_info[case.runner._run_id])
        raise primary

    monkeypatch.setattr(run_in_thread, "run_in_thread", refuse)
    with pytest.raises(error_type) as caught:
        case.runner.run_in_thread()
    assert caught.value is primary
    assert len(observed) == 1
    assert not case.state._run_id_to_runtime_info
    assert case.runner._future is None


def test_validation_failure_keeps_response_and_persisted_status_without_leak(
    admitted_runner,
):
    from fastapi.exceptions import RequestValidationError

    from actions.server._models import Run, RunStatus

    case = admitted_runner
    primary = ValueError("owned invalid input")

    def reject(inputs):
        raise primary

    case.runner.input_validator = reject
    assert case.runner.run_in_thread() == "async-return"
    case.executor.release()
    with pytest.raises(RequestValidationError) as caught:
        case.executor.future.result()
    assert "owned invalid input" in str(caught.value)
    assert not case.pool.calls and not case.state._run_id_to_runtime_info
    run = case.db.first(Run, "SELECT * FROM run WHERE id=?", [case.runner._run_id])
    assert run.status == RunStatus.NOT_RUN  # Existing validation status policy.


def test_already_completed_future_retires_same_runtime_identity(
    admitted_runner, monkeypatch
):
    from actions.server._robo_utils import run_in_thread

    case = admitted_runner
    seen = []

    def execute(runtime_info):
        assert case.state._run_id_to_runtime_info[case.runner._run_id] is runtime_info
        seen.append(runtime_info)
        return "owned result"

    def immediate(target):
        future = Future()
        future.set_result(target())
        return future

    monkeypatch.setattr(case.runner, "_run_action_impl", execute)
    monkeypatch.setattr(run_in_thread, "run_in_thread", immediate)
    case.runner.timeout = None
    assert case.runner.run_in_thread() == "owned result"
    assert len(seen) == 1 and seen[0]._run_id == case.runner._run_id
    assert not case.state._run_id_to_runtime_info


def test_old_completion_cannot_retire_replacement_runtime_info(admitted_runner):
    case = admitted_runner
    case.runner.input_validator = lambda inputs: (_ for _ in ()).throw(ValueError())
    assert case.runner.run_in_thread() == "async-return"
    run_id = case.runner._run_id
    original = case.state._run_id_to_runtime_info[run_id]
    assert case.state.discard_run_runtime_info(run_id, original)
    replacement = case.state.create_run_runtime_info(run_id)
    case.executor.release()
    assert case.state._run_id_to_runtime_info[run_id] is replacement
    assert not case.state.discard_run_runtime_info(run_id, original)
    assert case.state.discard_run_runtime_info(run_id, replacement)


def test_finished_run_stays_uncancellable(admitted_runner):
    from actions.server import _actions_run
    from actions.server._api_run import cancel_run

    case = admitted_runner
    assert case.runner.run_in_thread() == "async-return"
    _actions_run._set_run_as_finished_ok(case.runner._run, "{}", 0.0)
    assert cancel_run(case.runner._run_id) == "not-running"
    assert not case.state._run_id_to_runtime_info


def test_scoped_run_rejection_does_not_register_or_dispatch(
    admitted_runner, monkeypatch
):
    from actions.server._api_run import cancel_run

    case = admitted_runner
    monkeypatch.setattr(case.state, "is_scoped_run", lambda run_id: True)
    with pytest.raises(PermissionError, match="common authorized lifecycle"):
        case.runner.run_in_thread()
    assert case.executor.target is None
    assert not case.state._run_id_to_runtime_info
    assert cancel_run(case.runner._run_id) == "not-running"
