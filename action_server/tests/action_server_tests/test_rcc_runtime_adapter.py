import json
import subprocess
from pathlib import Path

import pytest


def test_artifact_digest_parser_accepts_only_exact_identity():
    from actions.server._rcc_runtime_adapter import RccRuntimeError, parse_artifact_digest

    assert parse_artifact_digest({"artifact": "sha256:" + "a" * 64}) == "sha256:" + "a" * 64
    assert parse_artifact_digest({"artifact": {"digest": "sha256:" + "b" * 64}}) == "sha256:" + "b" * 64
    assert parse_artifact_digest({"artifactDigest": "sha256:" + "c" * 64}) == "sha256:" + "c" * 64
    for payload in ({}, {"artifact": "not-a-digest"}, {"digest": "sha256:" + "a" * 63}):
        with pytest.raises(RccRuntimeError, match="artifact"):
            parse_artifact_digest(payload)


def test_runtime_descriptor_has_no_activation_path_authority():
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor

    descriptor = RccRuntimeDescriptor(
        artifact_digest="sha256:" + "a" * 64,
        source_generation="gen-1",
        source_hash="b" * 64,
    )
    serialized = json.loads(descriptor.to_json())
    assert serialized["runtime"]["kind"] == "rcc"
    assert serialized["runtime"]["artifact_digest"] == "sha256:" + "a" * 64
    for forbidden in ("PYTHON_EXE", "CONDA_PREFIX", "ROBOCORP_HOME", "holotree", "materialization"):
        assert forbidden not in descriptor.to_json()


def test_import_command_uses_artifact_exec_not_python_exe(tmp_path):
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor, build_exec_command

    descriptor = RccRuntimeDescriptor(artifact_digest="sha256:" + "c" * 64)
    command = build_exec_command(
        Path("/opt/rcc"), descriptor, ["python", "-c", "import actions"], receipt_file=None
    )
    assert command[:5] == ["/opt/rcc", "env", "exec", "--artifact", "sha256:" + "c" * 64]
    assert "PYTHON_EXE" not in command
    assert command[-4:] == ["--", "python", "-c", "import actions"]


def test_worker_command_has_inherit_streams_and_receipt(tmp_path):
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor, build_exec_command

    receipt = tmp_path / "receipt.json"
    descriptor = RccRuntimeDescriptor(artifact_digest="sha256:" + "d" * 64)
    command = build_exec_command(Path("/opt/rcc"), descriptor, ["python", "-m", "preload_actions_server_main"], receipt_file=receipt)
    assert "--inherit-streams" in command
    assert "--receipt-file" in command
    assert str(receipt) in command
    assert command[command.index("--") + 1 :] == ["python", "-m", "preload_actions_server_main"]


def test_failed_publish_is_phase_error_without_fallback(tmp_path):
    from actions.server._rcc_runtime_adapter import RccRuntimeError, publish_artifact

    with pytest.raises(RccRuntimeError, match="publish"):
        publish_artifact(Path("/does/not/exist"), Path("/tmp/rcc"), runner=lambda *args: (1, "", "no"))


def test_process_handle_kill_waits_for_wrapper(tmp_path):
    from actions.server._rcc_runtime_adapter import RccProcessHandle

    process = subprocess.Popen(["sh", "-c", "sleep 30"])
    handle = RccProcessHandle(process, tmp_path / "receipt.json")
    handle.kill()
    assert process.poll() is not None


@pytest.mark.real_rcc
def test_real_rcc_artifact_action_vertical(tmp_path):
    import os

    if not os.environ.get("ACTIONS_REAL_RCC_ARTIFACT_TEST"):
        pytest.skip("set ACTIONS_REAL_RCC_ARTIFACT_TEST=1")
    provider = os.environ.get("ACTIONS_RUNTIME_RCC_PROVIDER")
    if not provider:
        pytest.fail("ACTIONS_RUNTIME_RCC_PROVIDER must name the cache provider for real proof")

    from actions.server._actions_process_pool import ActionsProcessPool
    from actions.server._models import Action, ActionPackage, Run, RunStatus
    from actions.server._rcc_runtime_adapter import get_rcc_location, prepare_runtime
    from actions.server._settings import Settings

    package_dir = tmp_path / "package"
    package_dir.mkdir()
    package_yaml = package_dir / "package.yaml"
    package_yaml.write_text(
        """version: 0.1
spec-version: v2
dependencies:
  conda-forge:
    - python=3.11.11
  pypi:
    - actions-core=1.0.0
"""
    )
    action_file = package_dir / "action.py"
    action_file.write_text(
        "from actions import action\n\n@action\ndef answer() -> str:\n    return 'rcc-v18.19.2'\n"
    )
    descriptor = prepare_runtime(
        package_yaml, get_rcc_location(), provider=provider, source_generation="real-test"
    )
    persisted = descriptor.to_dict()
    persisted["PYTHONPATH"] = str(package_dir)
    package = ActionPackage(
        id="rcc-real-package", name="rcc-real-package", directory=str(package_dir),
        conda_hash=descriptor.artifact_digest, env_json=json.dumps(persisted),
    )
    action = Action(
        id="rcc-real-action", action_package_id=package.id, name="answer", docs="",
        file=str(action_file), lineno=0, input_schema="{}", output_schema="{}",
    )
    settings = Settings(datadir=tmp_path / "data", artifacts_dir=tmp_path / "artifacts")
    settings.reuse_processes = False
    settings.min_processes = 0
    settings.max_processes = 1
    pool = ActionsProcessPool(settings, {package.id: package}, [action])
    try:
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        input_json = run_dir / "input.json"
        result_json = run_dir / "result.json"
        output_file = run_dir / "output.txt"
        input_json.write_text("{}")
        run = Run(
            id="rcc-real-run", status=RunStatus.NOT_RUN, action_id=action.id,
            start_time="", run_time=None, inputs="{}", result=None,
            error_message=None, relative_artifacts_dir="", numbered_id=1,
        )
        with pool.obtain_process_for_action(action) as handle:
            assert handle.run_action(
                run, package, action, input_json, run_dir, output_file, result_json,
                {}, {}, False
            ) == 0
            assert json.loads(result_json.read_text())["result"] == "rcc-v18.19.2"
            receipt = handle._rcc_wrapper.receipt_file
        assert receipt.exists()
        assert descriptor.artifact_digest.startswith("sha256:")
    finally:
        pool.dispose()
