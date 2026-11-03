"""The release train PR must reach the existing owned PostgreSQL test gate."""

import importlib.util
from pathlib import Path

import yaml


def test_release_branch_pr_uses_generated_runtime_workflow_and_owned_postgres():
    root = Path(__file__).resolve().parents[3]
    path = root / ".github/workflows/_gen_workflows.py"
    spec = importlib.util.spec_from_file_location("runtime_ci_generator_340", path)
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generated = generator.ActionServerTests().full
    committed = yaml.safe_load(
        (root / ".github/workflows/actions_runtime_tests.yml").read_text()
    )
    assert committed == generated
    assert "release/**" in generated["on"]["pull_request"]["branches"]
    steps = generated["jobs"]["build"]["steps"]
    names = [step.get("name") for step in steps]
    start = steps[names.index("Start owned PostgreSQL for portable Runtime tests")]
    test = steps[names.index("Test (not integration)")]
    cleanup = steps[names.index("Remove owned portable-test PostgreSQL")]
    assert names.index(start["name"]) < names.index(test["name"]) < names.index(cleanup["name"])
    assert start["if"] == "runner.os == 'Linux'"
    assert "postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81" in start["run"]
    assert 'ACTIONS_REQUIRE_INVOICE_PROVIDERS=1' in start["run"]
    assert 'poetry run inv test-not-integration' in test["run"]
    assert cleanup["if"] == "always() && runner.os == 'Linux'"
    assert 'docker rm' in cleanup["run"] and 'docker ps' in cleanup["run"]


def test_owned_postgres_cleanup_removes_task_container(tmp_path):
    """Exercise the real generated cleanup shell with a task-local Docker double."""
    import os
    import subprocess

    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "runtime_ci_cleanup_generator_340", root / ".github/workflows/_gen_workflows.py"
    )
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    cleanup = generator.ActionServerTests().stop_owned_postgres()["run"]
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    state = tmp_path / "container"
    docker = binary_dir / "docker"
    docker.write_text(
        "#!/usr/bin/env python3\n"
        "import os, pathlib, sys\n"
        "state=pathlib.Path(os.environ['TEST_CONTAINER_STATE'])\n"
        "if sys.argv[1] == 'rm':\n"
        "    if not state.exists(): sys.exit(1)\n"
        "    state.unlink()\n"
        "elif sys.argv[1] == 'ps':\n"
        "    if state.exists(): print('a' * 64)\n"
        "else: sys.exit(2)\n"
    )
    docker.chmod(0o700)
    env = os.environ.copy()
    env.update(
        PATH=str(binary_dir) + os.pathsep + os.defpath,
        ACTIONS_RUNTIME_TEST_POSTGRES_CID="a" * 64,
        TEST_CONTAINER_STATE=str(state),
        GITHUB_ENV=str(tmp_path / "github_env"),
    )
    state.write_text("owned")
    subprocess.run(["bash", "-c", cleanup], env=env, check=True)
    assert not state.exists()
    assert "ACTIONS_INVOICE_TEST_POSTGRES=" in (tmp_path / "github_env").read_text()


def test_owned_postgres_start_success_and_readiness_failure_cleanup(tmp_path):
    """Exercise generated shell with a local Docker double, never a real daemon."""
    import os
    import subprocess

    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "runtime_ci_start_generator_340", root / ".github/workflows/_gen_workflows.py"
    )
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    workflow = generator.ActionServerTests()
    start = workflow.start_owned_postgres()["run"]
    cleanup = workflow.stop_owned_postgres()["run"]
    binaries = tmp_path / "bin"
    binaries.mkdir()
    state = tmp_path / "container"
    docker = binaries / "docker"
    docker.write_text(
        "#!/usr/bin/env python3\n"
        "import os, pathlib, sys\n"
        "state=pathlib.Path(os.environ['TEST_CONTAINER_STATE'])\n"
        "cmd=sys.argv[1]\n"
        "if cmd == 'pull': pass\n"
        "elif cmd == 'run': state.write_text('owned'); print('a' * 64)\n"
        "elif cmd == 'exec': sys.exit(0 if os.environ['TEST_READY'] == '1' else 1)\n"
        "elif cmd == 'port': print('127.0.0.1:54321')\n"
        "elif cmd == 'rm':\n"
        "    if not state.exists(): sys.exit(1)\n"
        "    state.unlink()\n"
        "elif cmd == 'ps':\n"
        "    if state.exists(): print('a' * 64)\n"
        "else: sys.exit(2)\n"
    )
    docker.chmod(0o700)
    sleep = binaries / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o700)
    env = os.environ.copy()
    env.update(
        PATH=str(binaries) + os.pathsep + os.defpath,
        TEST_CONTAINER_STATE=str(state),
        GITHUB_RUN_ID="123",
        GITHUB_RUN_ATTEMPT="1",
        GITHUB_ENV=str(tmp_path / "github_env"),
    )
    for ready in ("1", "0"):
        env["TEST_READY"] = ready
        result = subprocess.run(["bash", "-c", start], env=env, capture_output=True)
        assert (result.returncode == 0) == (ready == "1")
        assert state.exists() == (ready == "1")
        env["ACTIONS_RUNTIME_TEST_POSTGRES_CID"] = "a" * 64
        subprocess.run(["bash", "-c", cleanup], env=env, check=True)
        assert not state.exists()
