from threading import Thread

import pytest


def test_malformed_command_arguments_return_argparse_error_code(capsys):
    from actions._args_dispatcher import _ActionsArgDispatcher

    dispatcher = _ActionsArgDispatcher()

    assert dispatcher.process_args(["run", "--max-log-files", "many"]) == 2
    assert "invalid int value" in capsys.readouterr().err


def test_registered_command_handler_errors_propagate(monkeypatch):
    from actions import _commands
    from actions._args_dispatcher import _ActionsArgDispatcher

    def fail_handler(**kwargs):
        raise RuntimeError("handler failed")

    monkeypatch.setattr(_commands, "list_actions", fail_handler)
    dispatcher = _ActionsArgDispatcher()
    parsed = dispatcher.parse_args(["list", "--skip-lint"])

    with pytest.raises(RuntimeError, match="handler failed"):
        dispatcher._dispatch(parsed)


def test_run_handler_reports_missing_selected_action(tmp_path, monkeypatch):
    from actions._commands import run

    monkeypatch.setenv("RC_DUMP_THREADS_AFTER_RUN", "0")
    monkeypatch.setenv("ROBOT_ROOT", "temporary test value")
    (tmp_path / "example_action.py").write_text(
        "from actions import action\n"
        "@action\n"
        "def available():\n"
        "    return 'available'\n"
    )

    result = run(
        output_dir=str(tmp_path / "output"),
        path=str(tmp_path),
        action_name="missing",
    )

    assert result == 1
    from robocorp.log._log_formatting import pretty_format_logs_from_log_html

    log = pretty_format_logs_from_log_html(tmp_path / "output" / "log.html")
    assert "Did not find any actions in:" in log


def test_variable_scope_is_missing_outside_context_and_restored_afterward():
    from actions._variables_scope import (
        create_validate_and_convert_kwargs_scope,
        get_validate_and_convert_kwargs_scope,
    )

    assert get_validate_and_convert_kwargs_scope() is None
    with create_validate_and_convert_kwargs_scope("count", int) as scope:
        assert scope.param_name == "count"
        assert scope.param_type is int
        assert get_validate_and_convert_kwargs_scope() is scope
    assert get_validate_and_convert_kwargs_scope() is None


def test_overlapping_variable_scope_is_rejected_without_losing_outer_scope():
    from actions._variables_scope import (
        create_validate_and_convert_kwargs_scope,
        get_validate_and_convert_kwargs_scope,
    )

    with create_validate_and_convert_kwargs_scope("outer", str) as outer_scope:
        with pytest.raises(AssertionError, match="A scope is already active!"):
            with create_validate_and_convert_kwargs_scope("inner", int):
                pytest.fail("The overlapping scope must not be entered.")
        assert get_validate_and_convert_kwargs_scope() is outer_scope
    assert get_validate_and_convert_kwargs_scope() is None


def test_variable_scope_is_cleared_when_context_body_raises():
    from actions._variables_scope import (
        create_validate_and_convert_kwargs_scope,
        get_validate_and_convert_kwargs_scope,
    )

    with pytest.raises(RuntimeError, match="conversion failed"):
        with create_validate_and_convert_kwargs_scope("amount", float):
            raise RuntimeError("conversion failed")

    assert get_validate_and_convert_kwargs_scope() is None


def test_variable_scope_is_isolated_per_thread():
    from actions._variables_scope import (
        create_validate_and_convert_kwargs_scope,
        get_validate_and_convert_kwargs_scope,
    )

    worker_results = {}
    worker_errors = []

    def observe_worker_scope():
        try:
            worker_results["before"] = get_validate_and_convert_kwargs_scope()
            with create_validate_and_convert_kwargs_scope("worker", bool) as scope:
                worker_results["during"] = (
                    get_validate_and_convert_kwargs_scope() is scope
                )
            worker_results["after"] = get_validate_and_convert_kwargs_scope()
        except BaseException as error:
            worker_errors.append(error)

    with create_validate_and_convert_kwargs_scope("main", str) as main_scope:
        thread = Thread(target=observe_worker_scope)
        thread.start()
        thread.join(timeout=5)

        assert not thread.is_alive(), "Scope worker thread did not finish."
        assert worker_errors == []
        assert worker_results == {"before": None, "during": True, "after": None}
        assert get_validate_and_convert_kwargs_scope() is main_scope

    assert get_validate_and_convert_kwargs_scope() is None
