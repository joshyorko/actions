import json
import subprocess
from pathlib import Path

import pytest


def test_artifact_digest_parser_accepts_only_exact_identity():
    from actions.server._rcc_runtime_adapter import RccRuntimeError, parse_artifact_digest

    assert parse_artifact_digest({"artifact": "sha256:" + "a" * 64}) == "sha256:" + "a" * 64
    assert parse_artifact_digest({"artifact": {"digest": "sha256:" + "b" * 64}}) == "sha256:" + "b" * 64
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
def test_real_rcc_artifact_action_vertical():
    if not __import__("os").environ.get("ACTIONS_REAL_RCC_ARTIFACT_TEST"):
        pytest.skip("set ACTIONS_REAL_RCC_ARTIFACT_TEST=1")
    pytest.skip("integration body is enabled after the focused adapter contract is wired")
