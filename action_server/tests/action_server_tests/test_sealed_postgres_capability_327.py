"""Regression coverage for the owned TLS fixture's Docker Engine preflight."""

import re
import subprocess

import pytest
from action_server_tests import test_sealed_postgres as sealed_postgres


def _docker_cli(monkeypatch, *, stdout="linux\n", returncode=0):
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, returncode, stdout, "")

    monkeypatch.setattr(sealed_postgres.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(sealed_postgres.subprocess, "run", run)
    return calls


class _NoFixtureFiles:
    def mktemp(self, *_args, **_kwargs):
        raise AssertionError("refused fixture created a private-material directory")


def test_linux_engine_is_admitted_with_bounded_read_only_preflight(monkeypatch):
    calls = _docker_cli(monkeypatch)

    assert sealed_postgres._docker_engine_ostype() == ("linux", None)
    sealed_postgres._require_linux_docker()
    expected_call = (
        ["docker", "info", "--format", "{{.OSType}}"],
        {
            "check": False,
            "capture_output": True,
            "text": True,
            "timeout": 10,
        },
    )
    assert calls == [expected_call, expected_call]


@pytest.mark.parametrize(
    "stdout,returncode,diagnostic",
    [
        ("windows\n", 0, "Linux Docker Engine required (server OS type: windows)"),
        ("", 1, "Docker Engine returned an unavailable or malformed OS type"),
        ("mystery\n", 0, "Docker Engine returned an unavailable or malformed OS type"),
    ],
)
def test_unqualified_engine_skips_before_any_fixture_side_effects(
    monkeypatch, stdout, returncode, diagnostic
):
    calls = _docker_cli(monkeypatch, stdout=stdout, returncode=returncode)
    monkeypatch.delenv("ACTIONS_REQUIRE_INVOICE_PROVIDERS", raising=False)
    with pytest.raises(pytest.skip.Exception, match=re.escape(diagnostic)):
        next(sealed_postgres.tls_postgres.__wrapped__(_NoFixtureFiles()))

    # The preflight is the sole command: no openssl, private file creation, or
    # container launch can happen after the capability refusal.
    assert len(calls) == 1
    assert calls[0][0] == ["docker", "info", "--format", "{{.OSType}}"]


def test_unqualified_engine_fails_when_provider_is_required(monkeypatch):
    _docker_cli(monkeypatch, stdout="windows\n")
    monkeypatch.setenv("ACTIONS_REQUIRE_INVOICE_PROVIDERS", "1")

    with pytest.raises(pytest.fail.Exception, match="server OS type: windows"):
        next(sealed_postgres.tls_postgres.__wrapped__(_NoFixtureFiles()))


@pytest.mark.parametrize("strict", [False, True])
def test_unavailable_engine_uses_normal_or_strict_policy(monkeypatch, strict):
    calls = _docker_cli(monkeypatch, stdout="", returncode=1)
    if strict:
        monkeypatch.setenv("ACTIONS_REQUIRE_INVOICE_PROVIDERS", "1")
        expected = pytest.fail.Exception
    else:
        monkeypatch.delenv("ACTIONS_REQUIRE_INVOICE_PROVIDERS", raising=False)
        expected = pytest.skip.Exception

    with pytest.raises(expected, match="unavailable or malformed OS type"):
        next(sealed_postgres.tls_postgres.__wrapped__(_NoFixtureFiles()))
    assert len(calls) == 1


def test_timeout_and_os_error_are_unavailable_capabilities(monkeypatch):
    monkeypatch.setattr(sealed_postgres.shutil, "which", lambda _: "/usr/bin/docker")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(sealed_postgres.subprocess, "run", timeout)
    assert sealed_postgres._docker_engine_ostype() == (
        None,
        "Docker Engine OS type is unavailable (TimeoutExpired)",
    )

    def missing(*args, **kwargs):
        raise FileNotFoundError("docker vanished")

    monkeypatch.setattr(sealed_postgres.subprocess, "run", missing)
    assert sealed_postgres._docker_engine_ostype() == (
        None,
        "Docker Engine OS type is unavailable (FileNotFoundError)",
    )


def test_missing_cli_is_unavailable_and_strict_mode_fails(monkeypatch):
    calls = []
    monkeypatch.setattr(sealed_postgres.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        sealed_postgres.subprocess, "run", lambda *a, **kw: calls.append(a)
    )
    monkeypatch.setenv("ACTIONS_REQUIRE_INVOICE_PROVIDERS", "1")

    with pytest.raises(pytest.fail.Exception, match="Docker CLI is unavailable"):
        next(sealed_postgres.tls_postgres.__wrapped__(_NoFixtureFiles()))
    assert calls == []
