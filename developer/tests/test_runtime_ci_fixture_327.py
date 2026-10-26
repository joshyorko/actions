"""Exercise generated owned-PostgreSQL CI helpers without Docker services."""

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux CI Docker lifecycle Bash contract"
)

ROOT = Path(__file__).parents[2]
GENERATOR = ROOT / ".github" / "workflows" / "_gen_workflows.py"
CID = "0" * 63 + "1"


def load_generator():
    spec = importlib.util.spec_from_file_location("runtime_ci_generator", GENERATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shell_step(step):
    assert step["shell"] == "bash"
    return step["run"]


def stub_tools(tmp_path, *, ready=True, listing_fails=False):
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    docker_log = tmp_path / "docker.log"
    docker = binary_dir / "docker"
    docker.write_text(
        """#!/usr/bin/env bash
set -u
printf '%s\\n' "$*" >> "$DOCKER_LOG"
case "$1" in
  pull) exit 0 ;;
  run) printf '%s\\n' "$STUB_CID" ;;
  exec) [[ "$STUB_READY" == 1 ]] ;;
  port) printf '%s\\n' '127.0.0.1:55432' ;;
  rm) [[ "$2" == '--force' && "$3" == "$STUB_CID" ]] ;;
  ps)
    if [[ "$STUB_LISTING_FAIL" == 1 ]]; then exit 42; fi
    [[ "$*" == *"id=$STUB_CID"* ]] || exit 43
    exit 0
    ;;
  *) exit 44 ;;
esac
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    sleep = binary_dir / "sleep"
    sleep.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    sleep.chmod(0o755)
    environment = {
        "PATH": os.pathsep.join((str(binary_dir), os.defpath)),
        "DOCKER_LOG": str(docker_log),
        "STUB_CID": CID,
        "STUB_READY": "1" if ready else "0",
        "STUB_LISTING_FAIL": "1" if listing_fails else "0",
        "GITHUB_RUN_ID": "test-run",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    return environment, docker_log


def run_shell(script, environment):
    return subprocess.run(
        ["bash", "-e", "-u", "-o", "pipefail", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_owned_postgres_shell_helpers_are_valid_bash():
    workflow = load_generator().ActionServerTests()
    for step in (workflow.start_owned_postgres(), workflow.stop_owned_postgres()):
        check = subprocess.run(
            ["bash", "-n"],
            input=shell_step(step),
            check=False,
            capture_output=True,
            text=True,
        )
        assert check.returncode == 0, check.stderr


def test_runtime_and_coverage_workflows_require_same_owned_provider_lifecycle():
    workflow = load_generator().ActionServerTests()
    for filename, job, test_step in (
        ("actions_runtime_tests.yml", "build", "Test (not integration)"),
        ("coverage-gate.yml", "coverage", "Measure portable package suite coverage"),
    ):
        document = yaml.safe_load((GENERATOR.parent / filename).read_text())
        steps = document["jobs"][job]["steps"]
        setup = workflow.start_owned_postgres()
        cleanup = workflow.stop_owned_postgres()
        assert setup in steps
        assert cleanup in steps
        measure_index = next(i for i, step in enumerate(steps) if step.get("name") == test_step)
        assert steps.index(setup) < measure_index < steps.index(cleanup)


def test_owned_postgres_start_exports_strict_urls_and_stop_removes_exact_cid(
    tmp_path,
):
    workflow = load_generator().ActionServerTests()
    env_file = tmp_path / "github-env"
    environment, docker_log = stub_tools(tmp_path)
    environment["GITHUB_ENV"] = str(env_file)

    start = run_shell(shell_step(workflow.start_owned_postgres()), environment)
    assert start.returncode == 0, start.stderr
    assert "::add-mask::postgresql://postgres:synthetic-runtime-ci-only@127.0.0.1:55432/postgres" in start.stdout

    start_env = env_file.read_text(encoding="utf-8").splitlines()
    url = "postgresql://postgres:synthetic-runtime-ci-only@127.0.0.1:55432/postgres"
    assert f"ACTIONS_RUNTIME_TEST_POSTGRES_CID={CID}" in start_env
    assert f"ACTIONS_INVOICE_TEST_POSTGRES={url}" in start_env
    assert f"ACTIONS_TEST_POSTGRES_URL={url}" in start_env
    assert "ACTIONS_REQUIRE_INVOICE_PROVIDERS=1" in start_env
    assert re.fullmatch(r"[0-9a-f]{64}", CID)

    environment["ACTIONS_RUNTIME_TEST_POSTGRES_CID"] = CID
    stop = run_shell(shell_step(workflow.stop_owned_postgres()), environment)
    assert stop.returncode == 0, stop.stderr
    log = docker_log.read_text(encoding="utf-8").splitlines()
    assert f"rm --force {CID}" in log
    assert f"ps --all --no-trunc --quiet --filter id={CID}" in log
    stop_env = env_file.read_text(encoding="utf-8").splitlines()[len(start_env) :]
    assert "ACTIONS_INVOICE_TEST_POSTGRES=" in stop_env
    assert "ACTIONS_TEST_POSTGRES_URL=" in stop_env
    assert "ACTIONS_REQUIRE_INVOICE_PROVIDERS=0" in stop_env


def test_failed_readiness_keeps_cid_for_cleanup_and_listing_error_fails_closed(
    tmp_path,
):
    workflow = load_generator().ActionServerTests()
    env_file = tmp_path / "github-env"
    environment, docker_log = stub_tools(
        tmp_path, ready=False, listing_fails=True
    )
    environment["GITHUB_ENV"] = str(env_file)

    start = run_shell(shell_step(workflow.start_owned_postgres()), environment)
    assert start.returncode != 0
    assert "PASS" not in start.stdout
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        f"ACTIONS_RUNTIME_TEST_POSTGRES_CID={CID}"
    ]
    assert len(
        [line for line in docker_log.read_text(encoding="utf-8").splitlines() if line.startswith("exec ")]
    ) == 60

    environment["ACTIONS_RUNTIME_TEST_POSTGRES_CID"] = CID
    stop = run_shell(shell_step(workflow.stop_owned_postgres()), environment)
    assert stop.returncode != 0
    log = docker_log.read_text(encoding="utf-8").splitlines()
    assert f"rm --force {CID}" in log
    assert f"ps --all --no-trunc --quiet --filter id={CID}" in log
    # Cleanup must not write a success-shaped reset after Docker could not
    # confirm that the exact owned container is gone.
    assert len(env_file.read_text(encoding="utf-8").splitlines()) == 1
    assert "PASS" not in stop.stdout
