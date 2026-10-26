"""Genuine Robot processes and retained artifacts, not Foundry plan acceptance.

Direct cases use the locked development runner. RCC cases exercise the legacy
Robot API with an actual pinned RCC binary; only host settings are substituted.
Neither route establishes the common Package/Deployment/Attempt contract.
"""

import asyncio
import os
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from xml.etree import ElementTree

import pytest
import yaml


def _package(root: Path, output: str) -> Path:
    root.mkdir()
    (root / "tasks.robot").write_text(
        "*** Settings ***\nLibrary    OperatingSystem\nLibrary    String\n"
        "*** Tasks ***\nAccept\n"
        "    ${value}=    Get Environment Variable    SAMPLE_INPUT\n"
        "    ${bytes}=    Encode String To Bytes    ${value}    UTF-8\n"
        "    Create Binary File    ${OUTPUT DIR}/result.txt    ${bytes}\n"
        "    Log To Console    accepted literal input\n"
        "Reject\n"
        "    Create File    ${OUTPUT DIR}/failure.txt    diagnostic retained\n"
        "    Fail    deliberate acceptance failure\n",
        encoding="utf-8",
    )
    (root / "robot.yaml").write_text(
        yaml.safe_dump(
            {
                "tasks": {
                    name: {
                        "shell": (
                            "python -m robot --log NONE --report NONE "
                            f"--outputdir {output} --task {name} tasks.robot"
                        ),
                        "inputEnvironment": ["SAMPLE_INPUT"],
                    }
                    for name in ("Accept", "Reject")
                },
                "environmentConfigs": ["conda.yaml"],
                "artifactsDir": output,
            }
        ),
        encoding="utf-8",
    )
    (root / "conda.yaml").write_text(
        "channels:\n  - conda-forge\ndependencies:\n"
        "  - python=3.12.15\n  - pip=25.0\n"
        "  - pip:\n      - robotframework==7.4.2\n",
        encoding="utf-8",
    )
    return root


def _assert_xml(content: bytes, task: str):
    document = ElementTree.fromstring(content)
    assert document.attrib["generator"].startswith("Robot 7.4.2 ")
    tests = document.findall(".//test")
    assert len(tests) == 1
    assert tests[0].attrib["name"] == task
    status = tests[0].find("status")
    assert status is not None
    assert status.attrib["status"] == ("PASS" if task == "Accept" else "FAIL")


@pytest.mark.parametrize("task", ["Accept", "Reject"])
@pytest.mark.parametrize("output", ["output", "custom/nested"])
def test_direct_robot_retains_real_xml_and_payload_after_source_removal(
    tmp_path: Path, task: str, output: str
):
    from actions.server._artifact_storage import create_artifact_storage
    from actions.server._robot_artifacts import collect_robot_artifacts
    from actions.server._robot_inputs import validate_robot_inputs

    assert version("robotframework") == "7.4.2"
    package = _package(tmp_path / "package", output)
    literal = 'snow 雪 \\ "quoted"\n$(touch must-not-exist); = literal'
    inputs = validate_robot_inputs(package, task, {"SAMPLE_INPUT": literal})
    command = [
        sys.executable,
        "-m",
        "robot",
        "--log",
        "NONE",
        "--report",
        "NONE",
        "--outputdir",
        output,
        "--task",
        task,
        "tasks.robot",
    ]
    # Stream diagnostics to disk so TimeoutExpired also leaves a receipt.
    with (tmp_path / "direct.stdout.txt").open("wb") as stdout:
        completed = subprocess.run(
            command,
            cwd=package,
            env={**os.environ, **inputs},
            stdout=stdout,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )
    assert completed.returncode == (0 if task == "Accept" else 1)
    assert not (package / "must-not-exist").exists()
    xml = (package / output / "output.xml").read_bytes()
    _assert_xml(xml, task)
    name = "result.txt" if task == "Accept" else "failure.txt"
    payload = (literal if task == "Accept" else "diagnostic retained").encode()
    assert (package / output / name).read_bytes() == payload
    root = tmp_path / "retained"
    root.mkdir()
    storage = create_artifact_storage("local", root)
    key = "runs/robot-real"
    storage.create_run_artifacts_dir(key)
    collect_robot_artifacts(package, package / "robot.yaml", storage, key)
    shutil.rmtree(package)
    reopened = create_artifact_storage("local", root)
    assert reopened.read_bytes(key, "output.xml") == xml
    assert reopened.read_bytes(key, name) == payload


@pytest.mark.real_rcc
@pytest.mark.parametrize("task", ["Accept", "Reject"])
def test_legacy_robot_api_real_rcc_retains_outputs_after_database_reopen(
    tmp_path: Path, monkeypatch, task: str
):
    if os.environ.get("ACTIONS_ROBOT_REAL_RCC") != "1":
        pytest.skip("set ACTIONS_ROBOT_REAL_RCC=1 with pinned binary and owned home")
    binary = Path(os.environ["ACTIONS_RUNTIME_RCC_BINARY"])
    home = Path(os.environ["ROBOTS_HOME"])
    assert binary.is_absolute() and binary.is_file()
    assert home.is_absolute() and home.is_dir()
    checked = subprocess.run(
        [str(binary), "version"],
        env={**os.environ, "ROBOCORP_HOME": str(home)},
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert checked.stdout.strip() == "v18.19.3"

    from fastapi import BackgroundTasks, Request

    from actions.server import _api_robots, _runs_state_cache, _settings
    from actions.server._artifact_storage import get_artifact_storage
    from actions.server._models import Run, RunStatus, create_db, load_db
    from actions.server._rcc import initialize_rcc_robots
    from actions.server._settings import Settings

    package = _package(tmp_path / "package", "output")
    settings = Settings(datadir=tmp_path, artifacts_dir=tmp_path / "artifacts")
    monkeypatch.setattr(_settings, "get_settings", lambda: settings)
    monkeypatch.setattr(_api_robots, "get_settings", lambda: settings)
    database = tmp_path / "server.db"
    with create_db(database) as db, initialize_rcc_robots(binary, home):
        monkeypatch.setattr(
            _runs_state_cache, "_runs_state", _runs_state_cache.RunsState(db)
        )
        background = BackgroundTasks()
        response = asyncio.run(
            _api_robots.run_robot_task(
                _api_robots.RobotRunRequestAPI(
                    robot_package_path=str(package),
                    task_name=task,
                    inputs={"SAMPLE_INPUT": "genuine RCC input 雪"},
                ),
                background,
                Request({"type": "http", "headers": []}),
            )
        )
        asyncio.run(background())
        run = db.first(Run, "SELECT * FROM run WHERE id=?", [response.run_id])
        assert run.status == (
            RunStatus.PASSED if task == "Accept" else RunStatus.FAILED
        )
        storage = get_artifact_storage()
        key = storage.run_storage_key(run.id)
        xml = storage.read_bytes(key, "output.xml")
        _assert_xml(xml, task)
        name = "result.txt" if task == "Accept" else "failure.txt"
        payload = (
            "genuine RCC input 雪" if task == "Accept" else "diagnostic retained"
        ).encode()
        assert storage.read_bytes(key, name) == payload
        assert storage.read_bytes(key, "__action_server_output.txt")
        run_id = run.id

    shutil.rmtree(package)
    with load_db(database) as db:
        retained = db.first(Run, "SELECT * FROM run WHERE id=?", [run_id])
        assert retained.status == (
            RunStatus.PASSED if task == "Accept" else RunStatus.FAILED
        )
        reopened = get_artifact_storage()
        assert reopened.read_bytes(key, "output.xml") == xml
        assert reopened.read_bytes(key, name) == payload
