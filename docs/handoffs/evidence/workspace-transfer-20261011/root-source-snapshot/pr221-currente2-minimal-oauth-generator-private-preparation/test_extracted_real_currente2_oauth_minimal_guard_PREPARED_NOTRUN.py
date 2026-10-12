"""PRIVATE PREPARED controls; no product import, remote call, or real gh launch.

RCC_OAUTH_PRIVATE_SOURCE_KIND=original selects retained original for meaningful
RED; proposed selects the two-check/nonblank function. No invocation authorized
by this file. Run only in an explicitly released isolated absent basetemp.
"""
import ast
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

HERE = Path(__file__).resolve().parent
SENTINEL = b"previous-generated-module\n"
BODIES = (b"actions-config: synthetic-public-test\n", b"default-config: synthetic-public-test\n")


def real_function(root):
    kind = os.environ.get("RCC_OAUTH_PRIVATE_SOURCE_KIND", "proposed")
    assert kind in ("original", "proposed")
    source = HERE / ("original-currente2-real-build_oauth2_config.py" if kind == "original" else "proposed-currente2-real-build_oauth2_config.py")
    module = ast.parse(source.read_text(encoding="utf-8"))
    assert len(module.body) == 1 and isinstance(module.body[0], ast.FunctionDef)
    function = module.body[0]
    function.decorator_list = []
    namespace = {"CURDIR": root, "Context": object}
    exec(compile(module, str(source), "exec"), namespace)
    return namespace["build_oauth2_config"]


class SyntheticGh:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def __call__(self, argv, **kwargs):
        index = len(self.calls)
        assert index < len(self.results)
        expected_name = ("actions-oauth-config.yaml", "oauth-config.yaml")[index]
        assert argv == ["gh", "api", "-H", "Accept: application/vnd.github.raw", f"repos/Sema4AI/oauth-public-configs/contents/{expected_name}"]
        assert kwargs.get("stdout") is subprocess.PIPE
        self.calls.append((argv, kwargs))
        returncode, body = self.results[index]
        if returncode and kwargs.get("check") is True:
            raise subprocess.CalledProcessError(returncode, argv, output=body)
        return subprocess.CompletedProcess(argv, returncode, stdout=body)


def invoke(function, results):
    gh = SyntheticGh(results)
    with patch("subprocess.run", gh):
        function(None)
    return gh


@pytest.fixture
def valid_baseline(tmp_path):
    destination = tmp_path / "src/actions/server/_oauth2_config.py"
    destination.parent.mkdir(parents=True)
    function = real_function(tmp_path)
    gh = invoke(function, [(0, body) for body in BODIES])
    assert len(gh.calls) == 2
    module = ast.parse(destination.read_text(encoding="utf-8"))
    assignment = next(node for node in module.body if isinstance(node, ast.Assign))
    assert ast.literal_eval(assignment.value) == {"actions_config": BODIES[0].decode("utf-8"), "default_user_config": BODIES[1].decode("utf-8")}
    baseline = destination.read_bytes()
    assert baseline.endswith(b"\n") and b"\r\n" not in baseline
    destination.write_bytes(SENTINEL)
    return function, destination, baseline


def test_success_retains_exact_original_generated_format(valid_baseline):
    function, destination, baseline = valid_baseline
    invoke(function, [(0, body) for body in BODIES])
    assert destination.read_bytes() == baseline


@pytest.mark.parametrize("index", [0, 1])
def test_nonzero_even_with_valid_body_refused_before_previous_destination_write(valid_baseline, index):
    function, destination, _ = valid_baseline
    results = [(0, body) for body in BODIES]
    results[index] = (17, BODIES[index])
    gh = SyntheticGh(results)
    with patch("subprocess.run", gh), pytest.raises(subprocess.CalledProcessError) as caught:
        function(None)
    assert caught.value.returncode == 17
    assert len(gh.calls) == index + 1
    assert destination.read_bytes() == SENTINEL


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("body", [b"", b" \t\r\n"])
def test_zero_exit_empty_or_blank_refused_before_previous_destination_write(valid_baseline, index, body):
    function, destination, _ = valid_baseline
    results = [(0, good) for good in BODIES]
    results[index] = (0, body)
    with pytest.raises(RuntimeError, match="configuration is empty"):
        invoke(function, results)
    assert destination.read_bytes() == SENTINEL


@pytest.mark.parametrize("index", [0, 1])
def test_invalid_UTF8_refused_before_previous_destination_write(valid_baseline, index):
    function, destination, _ = valid_baseline
    results = [(0, body) for body in BODIES]
    results[index] = (0, b"\xff")
    with pytest.raises(UnicodeDecodeError):
        invoke(function, results)
    assert destination.read_bytes() == SENTINEL


def test_second_failure_does_not_create_absent_destination(valid_baseline):
    function, destination, _ = valid_baseline
    destination.unlink()
    with pytest.raises(subprocess.CalledProcessError):
        invoke(function, [(0, BODIES[0]), (17, BODIES[1])])
    assert not destination.exists()
