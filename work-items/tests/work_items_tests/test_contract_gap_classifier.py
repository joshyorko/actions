"""Meta-tests for the expected-red call-phase classifier."""

from pathlib import Path

pytest_plugins = ("pytester",)


def _install_classifier(pytester):
    pytester.syspathinsert(Path(__file__).resolve().parents[1])
    pytester.makeconftest(
        """
pytest_plugins = ("work_items_tests.contract_ports.conftest",)
"""
    )


def test_owned_call_failure_is_xfailed(pytester):
    _install_classifier(pytester)
    pytester.makepyfile(
        """
import pytest

@pytest.mark.contract_gap(exception="builtins.ValueError", match="owned detail")
def test_gap():
    raise ValueError("the owned detail is present")
"""
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(xfailed=1)


def test_wrong_exception_class_fails_normally(pytester):
    _install_classifier(pytester)
    pytester.makepyfile(
        """
import pytest

@pytest.mark.contract_gap(exception="builtins.ValueError", match="owned detail")
def test_gap():
    raise TypeError("the owned detail is present")
"""
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(failed=1)


def test_wrong_exception_message_fails_normally(pytester):
    _install_classifier(pytester)
    pytester.makepyfile(
        """
import pytest

@pytest.mark.contract_gap(exception="builtins.ValueError", match="owned detail")
def test_gap():
    raise ValueError("an unrelated failure")
"""
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(failed=1)


def test_missing_fixture_errors_normally(pytester):
    _install_classifier(pytester)
    pytester.makepyfile(
        """
import pytest

@pytest.mark.contract_gap(exception="builtins.ValueError", match="owned detail")
def test_gap(missing_fixture):
    raise ValueError("the owned detail is present")
"""
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(errors=1)


def test_setup_failure_errors_normally(pytester):
    _install_classifier(pytester)
    pytester.makepyfile(
        """
import pytest

@pytest.fixture
def dependency():
    raise ValueError("the owned detail is present")

@pytest.mark.contract_gap(exception="builtins.ValueError", match="owned detail")
def test_gap(dependency):
    pass
"""
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(errors=1)


def test_unexpected_pass_fails_strictly(pytester):
    _install_classifier(pytester)
    pytester.makepyfile(
        """
import pytest

@pytest.mark.contract_gap(exception="builtins.ValueError", match="owned detail")
def test_gap():
    pass
"""
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*XPASS(strict)*manifest update required*"])
