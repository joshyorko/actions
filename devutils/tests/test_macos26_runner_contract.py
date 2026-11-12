"""Changing a build host must not change architecture or delivery compatibility."""

import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github/workflows"


def generator():
    spec = importlib.util.spec_from_file_location(
        "macos_generator", WORKFLOWS / "_gen_workflows.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("source", ["generator", "native"])
def test_runner_guard_runs_before_checkout_with_package_defaults(tmp_path, source):
    workflow = yaml.safe_load(
        (WORKFLOWS / "frontend-build-unauthenticated.yml").read_text()
    )
    step = (
        generator().macos_arm64_guard()
        if source == "generator"
        else workflow["jobs"]["build-external"]["steps"][0]
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    for name, value in [("uname", "arm64"), ("sw_vers", "26.1")]:
        path = runner_temp / name
        path.write_text(f"#!/bin/sh\nprintf '%s\\n' '{value}'\n")
        path.chmod(0o755)
    directory = step.get(
        "working-directory", workflow["defaults"]["run"]["working-directory"]
    ).replace("${{ runner.temp }}", str(runner_temp))
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=workspace / directory,
        env=dict(
            os.environ,
            PATH=str(runner_temp) + os.pathsep + os.environ["PATH"],
            RUNNER_ARCH="ARM64",
        ),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "26.1" in result.stdout
    assert not (workspace / "action_server").exists()


@pytest.mark.parametrize(
    "frozen_arch,wrapper_arch,accepted",
    [("arm64", "arm64", True), ("arm64", "x86_64", False), ("x86_64", "arm64", False)],
)
def test_native_architecture_receipt_with_real_macho_tools(
    tmp_path, frozen_arch, wrapper_arch, accepted
):
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ["lipo", "otool"]:
        executable = shutil.which(name) or shutil.which(f"llvm-{name}")
        if executable is None:
            pytest.skip(f"native or LLVM {name} unavailable")
        (tools / name).symlink_to(executable)
    for relative, architecture in [
        ("dist/action-server/action-server", frozen_arch),
        ("dist/final/action-server", wrapper_arch),
    ]:
        binary = tmp_path / relative
        binary.parent.mkdir(parents=True)
        binary.write_bytes(
            struct.pack(
                "<8I",
                0xFEEDFACF,
                {"arm64": 0x0100000C, "x86_64": 0x01000007}[architecture],
                0,
                2,
                0,
                0,
                0,
                0,
            )
        )
    (tmp_path / "output").mkdir()
    workflow = yaml.safe_load(
        (WORKFLOWS / "frontend-build-unauthenticated.yml").read_text()
    )
    step = next(
        step
        for step in workflow["jobs"]["build-external"]["steps"]
        if step.get("name") == "Record macOS native deployment load commands"
    )
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=tmp_path,
        env=dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"]),
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == accepted, result.stderr
    if accepted:
        receipt = (tmp_path / "output/native-macos-load-commands.txt").read_text()
        assert "dist/action-server/action-server" in receipt
        assert "dist/final/action-server" in receipt


@pytest.mark.parametrize(
    "architecture,version,accepted",
    [("arm64", "26.1", True), ("x86_64", "26.1", False), ("arm64", "15.7", False)],
)
def test_guard_measures_actual_architecture_and_os(
    tmp_path, architecture, version, accepted
):
    step = generator().macos_arm64_guard()
    for name, value in [("uname", architecture), ("sw_vers", version)]:
        path = tmp_path / name
        path.write_text(f"#!/bin/sh\nprintf '%s\\n' '{value}'\n")
        path.chmod(0o755)
    env = dict(
        os.environ,
        PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
        RUNNER_ARCH="ARM64",
    )
    result = subprocess.run(
        ["bash", "-c", step["run"]], env=env, capture_output=True, text=True
    )
    assert (result.returncode == 0) == accepted
    if accepted:
        assert version in result.stdout


def test_native_manual_mode_is_mac_only_without_changing_default_coverage():
    workflow = yaml.safe_load(
        (WORKFLOWS / "frontend-build-unauthenticated.yml").read_text()
    )
    assert (
        workflow[True]["workflow_dispatch"]["inputs"]["runner_scope"]["default"]
        == "all"
    )
    assert workflow["jobs"]["build-external"]["name"] == (
        "Build Action Server binary without credentials (${{ matrix.os }})"
    )
    expression = workflow["jobs"]["build-external"]["strategy"]["matrix"]["include"]
    choices = [
        json.loads(value) for value in re.findall(r"fromJSON\('([^']+)'\)", expression)
    ]
    assert [[row["os"] for row in choice] for choice in choices] == [
        ["macos-26"],
        ["ubuntu-22.04", "windows-2022", "macos-26"],
    ]
    assert "inputs.runner_scope == 'macos-arm64'" in expression


def test_generated_native_signing_and_download_slots_move_together():
    text = (WORKFLOWS / "actions_runtime_binary_release.yml").read_text()
    workflow = yaml.safe_load(text)
    signing = next(
        step
        for step in workflow["jobs"]["build"]["steps"]
        if step.get("name") == "Check signing availability"
    )
    assert "macos-26) keys=" in signing["run"]
    assert "name: action-server-macos-26" in text
    assert "asset_name: ${{ github.ref_name }}-macos-arm64" in text
    pypi = (WORKFLOWS / "actions_runtime_pypi_release.yml").read_text()
    assert "MACOSX_DEPLOYMENT_TARGET=12.0" in pypi
    assert "cp312-*macos*arm64 cp313-*macos*arm64" in pypi
    assert "macos-15" not in pypi
