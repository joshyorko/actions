import os
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[2] / "scripts" / "verify_dakota_rcc_acceptance.py"


def _harness():
    spec = importlib.util.spec_from_file_location("dakota_rcc_acceptance", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dakota_acceptance_harness_describes_candidate_wheel_proof():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "candidate-wheel" in result.stdout
    assert "RCC Environment Artifact" in result.stdout


@pytest.mark.integration_test
@pytest.mark.real_rcc
def test_dakota_local_rcc_action_over_authenticated_http(tmp_path):
    if os.environ.get("ACTIONS_REAL_RCC_ACCEPTANCE") != "1":
        pytest.skip("set ACTIONS_REAL_RCC_ACCEPTANCE=1 for the live local proof")

    harness = _harness()
    receipt_path = Path(
        os.environ.get(
            "ACTIONS_ACCEPTANCE_RECEIPT",
            str(tmp_path / "candidate-wheel-receipt.json"),
        )
    )
    result = harness.run_owned_process(
        [
            sys.executable,
            str(SCRIPT),
            "--mode",
            "candidate-wheel",
            "--receipt",
            str(receipt_path),
        ],
        timeout_seconds=(
            harness.PROOF_TIMEOUT_SECONDS + 2 * harness.CLEANUP_GRACE_SECONDS + 5
        ),
        env=harness.child_environment(
            os.environ,
            task_root=receipt_path.parent / "process-root",
            extra={
                "ACTIONS_RUNTIME_RCC_BINARY": os.environ["ACTIONS_RUNTIME_RCC_BINARY"],
                "ACTIONS_ACCEPTANCE_POETRY": os.environ["ACTIONS_ACCEPTANCE_POETRY"],
                "ACTIONS_ACCEPTANCE_ROBOCORP_HOME": os.environ[
                    "ACTIONS_ACCEPTANCE_ROBOCORP_HOME"
                ],
            },
        ),
        cleanup_grace_seconds=harness.CLEANUP_GRACE_SECONDS,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    live_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert live_receipt["runtime_mode"] == "candidate-wheel"
    assert len(live_receipt["source_sha"]) == 40
    assert len(live_receipt["candidate_wheels"]["actions-core"]["sha256"]) == 64
    assert len(live_receipt["candidate_wheels"]["actions-http-helper"]["sha256"]) == 64
    assert live_receipt["rcc_receipt"]["verification"]["valid"] is True


def test_child_environment_keeps_ca_and_proxy_settings_without_credentials(tmp_path):
    harness = _harness()
    source = {
        "PATH": "/usr/bin:/bin",
        "HTTPS_PROXY": "http://proxy.example:3128",
        "NO_PROXY": "example.test",
        "SSL_CERT_FILE": "/etc/ssl/cert.pem",
        "GITHUB_TOKEN": "must-not-cross-the-boundary",
        "AWS_SECRET_ACCESS_KEY": "must-not-cross-the-boundary",
        "ACTIONS_API_KEY": "must-not-cross-the-boundary",
    }

    result = harness.child_environment(source, task_root=tmp_path / "isolated")

    assert result["HTTPS_PROXY"] == source["HTTPS_PROXY"]
    assert result["NO_PROXY"].startswith("example.test")
    assert result["SSL_CERT_FILE"] == source["SSL_CERT_FILE"]
    assert result["HOME"] == str(tmp_path / "isolated" / "home")
    assert not {"GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY", "ACTIONS_API_KEY"} & set(
        result
    )


def test_child_environment_rejects_proxy_credentials(tmp_path):
    with pytest.raises(ValueError, match="proxy settings"):
        _harness().child_environment(
            {"HTTPS_PROXY": "http://user:secret@proxy.example:3128"},
            task_root=tmp_path / "isolated",
        )


def test_candidate_poetry_requires_explicit_pinned_rcc_toolchain(monkeypatch, tmp_path):
    monkeypatch.delenv("ACTIONS_ACCEPTANCE_POETRY", raising=False)
    monkeypatch.delenv("ACTIONS_ACCEPTANCE_ROBOCORP_HOME", raising=False)

    with pytest.raises(RuntimeError, match="ACTIONS_ACCEPTANCE_POETRY"):
        _harness().resolve_poetry(
            os.environ,
            task_root=tmp_path / "tool-root",
            deadline=_harness().Deadline.after(2),
        )


def test_candidate_poetry_rejects_path_outside_rcc_home(tmp_path):
    tool_home = tmp_path / "rcc-home"
    poetry = tmp_path / "host-bin" / "poetry"
    poetry.parent.mkdir()
    poetry.touch()
    poetry.chmod(0o700)

    with pytest.raises(RuntimeError, match="pinned RCC holotree"):
        _harness().resolve_poetry(
            {
                "ACTIONS_ACCEPTANCE_POETRY": str(poetry),
                "ACTIONS_ACCEPTANCE_ROBOCORP_HOME": str(tool_home),
            },
            task_root=tmp_path / "version-check",
            deadline=_harness().Deadline.after(2),
        )


def test_candidate_poetry_must_resolve_under_toolchain_and_report_2_1_1(
    tmp_path, monkeypatch
):
    harness = _harness()
    tool_home = tmp_path / "rcc-home"
    poetry = tool_home / "holotree" / "toolchain" / "bin" / "poetry"
    poetry.parent.mkdir(parents=True)
    poetry.touch()
    poetry.chmod(0o700)
    env = {
        "ACTIONS_ACCEPTANCE_POETRY": str(poetry),
        "ACTIONS_ACCEPTANCE_ROBOCORP_HOME": str(tool_home),
    }
    monkeypatch.setattr(
        harness,
        "run_owned_process",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "Poetry (version 2.1.2)\n", ""
        ),
    )

    with pytest.raises(RuntimeError, match="Poetry 2.1.1"):
        harness.resolve_poetry(
            env,
            task_root=tmp_path / "version-check",
            deadline=harness.Deadline.after(2),
        )


def test_candidate_poetry_resolves_pinned_executable_under_rcc_home(
    tmp_path, monkeypatch
):
    harness = _harness()
    tool_home = tmp_path / "rcc-home"
    poetry = tool_home / "holotree" / "toolchain" / "bin" / "poetry"
    poetry.parent.mkdir(parents=True)
    poetry.touch()
    poetry.chmod(0o700)
    env = {
        "ACTIONS_ACCEPTANCE_POETRY": str(poetry),
        "ACTIONS_ACCEPTANCE_ROBOCORP_HOME": str(tool_home),
    }
    monkeypatch.setattr(
        harness,
        "run_owned_process",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "Poetry (version 2.1.1)\n", ""
        ),
    )

    assert (
        harness.resolve_poetry(
            env,
            task_root=tmp_path / "version-check",
            deadline=harness.Deadline.after(2),
        )
        == poetry.resolve()
    )


def test_evidence_is_retained_outside_run_temp_with_private_mode(tmp_path):
    harness = _harness()
    temp_root = tmp_path / "disposable"
    temp_root.mkdir()
    receipt = tmp_path / "evidence.json"
    evidence = {"source_sha": "a" * 40, "candidate_wheel_sha256": "b" * 64}

    harness.write_evidence(receipt, evidence, temp_root=temp_root)

    assert json.loads(receipt.read_text(encoding="utf-8")) == evidence
    assert receipt.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        harness.write_evidence(receipt, evidence, temp_root=temp_root)
    with pytest.raises(ValueError, match="outside"):
        harness.write_evidence(temp_root / "inside.json", evidence, temp_root=temp_root)


def test_total_timeout_terminates_owned_descendant_processes(tmp_path):
    harness = _harness()
    pid_file = tmp_path / "child.pid"
    child_code = (
        "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "time.sleep(60)"
    )
    parent_code = (
        "import subprocess,sys,time; from pathlib import Path; "
        f"child=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
        f"Path({str(pid_file)!r}).write_text(str(child.pid)); "
        "time.sleep(60)"
    )
    env = harness.child_environment(os.environ, task_root=tmp_path / "process-root")

    with pytest.raises(subprocess.TimeoutExpired):
        harness.run_owned_process(
            [sys.executable, "-c", parent_code],
            timeout_seconds=0.5,
            env=env,
            cleanup_grace_seconds=0.2,
        )

    import psutil

    child_pid = int(pid_file.read_text())
    deadline = time.monotonic() + 3
    while psutil.pid_exists(child_pid) and time.monotonic() < deadline:
        try:
            if psutil.Process(child_pid).status() == psutil.STATUS_ZOMBIE:
                break
        except psutil.NoSuchProcess:
            break
        time.sleep(0.05)
    try:
        child_stopped = (
            not psutil.Process(child_pid).is_running()
            or psutil.Process(child_pid).status() == psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        child_stopped = True
    assert child_stopped


def test_provider_startup_failure_uses_bounded_kill_fallback(tmp_path, monkeypatch):
    harness = _harness()
    pid_file = tmp_path / "provider.pid"
    fake_server = (
        "import os,signal,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"Path({str(pid_file)!r}).write_text(str(os.getpid())); "
        "print('not-json', flush=True); time.sleep(60)"
    )
    monkeypatch.setattr(
        harness,
        "_provider_command",
        lambda _rcc, _root: [sys.executable, "-c", fake_server],
    )

    with pytest.raises(RuntimeError, match="startup JSON"):
        harness.start_provider(
            "/unused/rcc",
            tmp_path / "provider-root",
            harness.child_environment(os.environ, task_root=tmp_path / "runtime"),
            deadline=harness.Deadline.after(3),
            cleanup_grace_seconds=0.2,
        )

    import psutil

    provider_pid = int(pid_file.read_text())
    try:
        provider_stopped = (
            not psutil.Process(provider_pid).is_running()
            or psutil.Process(provider_pid).status() == psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        provider_stopped = True
    assert provider_stopped
