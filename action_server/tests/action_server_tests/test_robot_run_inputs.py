import asyncio
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import fastapi
import pytest
import yaml
from starlette.requests import Request


def _robot(tmp_path: Path, declaration=None, *, config_name="robot.yaml") -> Path:
    package = tmp_path / "robot"
    package.mkdir(exist_ok=True)
    task = {"shell": "python task.py"}
    if declaration is not None:
        task["inputEnvironment"] = declaration
    (package / config_name).write_text(
        yaml.safe_dump(
            {
                "tasks": {"Consume": task, "Other": {"shell": "true"}},
                "condaConfigFile": "conda.yaml",
                "artifactsDir": "output",
            }
        ),
        encoding="utf-8",
    )
    (package / "conda.yaml").write_text("dependencies: []\n", encoding="utf-8")
    return package


def _request(queue="") -> Request:
    headers = [(b"x-workitem-queue", queue.encode())] if queue else []
    return Request({"type": "http", "headers": headers})


class _ConsumingRcc:
    def __init__(self):
        self.environments: list[dict[str, str]] = []
        self.environment_files: list[Path] = []

    def get_package_yaml_hash(self, *args, **kwargs):
        return "fixture-hash"

    def create_env_and_get_vars(self, *args, **kwargs):
        return SimpleNamespace(success=True, result=SimpleNamespace(env={}))

    def _run_rcc(self, args, *, cwd, **kwargs):
        from actions.server._protocols import RCCActionResult
        from actions.server._rcc import Rcc

        environment_file = Path(args[args.index("-e") + 1])
        environment = json.loads(environment_file.read_text(encoding="utf-8"))
        self.environment_files.append(environment_file)
        self.environments.append(environment)
        process_environment = Rcc(Path("unused-rcc"), None)._compute_env()
        assert "INVOICE_INPUT" not in process_environment
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json,os; print(json.dumps({'consumed': os.environ.get('INVOICE_INPUT', 'default')}))",
            ],
            cwd=cwd,
            env={**process_environment, **environment},
            capture_output=True,
            text=True,
            check=True,
        )
        return RCCActionResult("fixture-rcc", success=True, result=completed.stdout)


def test_robot_run_delivers_declared_literal_inputs_and_keeps_runtime_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from actions.server import _api_robots, _artifact_storage
    from actions.server._models import Run, RunStatus, create_db
    from actions.server._runs_state_cache import use_runs_state_ctx

    package = _robot(tmp_path, ["INVOICE_INPUT"])
    rcc = _ConsumingRcc()
    (tmp_path / "artifacts").mkdir()
    storage = _artifact_storage.create_artifact_storage("local", tmp_path / "artifacts")
    monkeypatch.setattr(_artifact_storage, "get_artifact_storage", lambda: storage)
    monkeypatch.setattr(_api_robots, "get_rcc_robots", lambda: rcc)
    monkeypatch.setattr(
        _api_robots, "get_settings", lambda: SimpleNamespace(datadir=tmp_path)
    )
    value = 'alternate \\ path="quoted"\n雪 $(echo literal); = value'
    background = fastapi.BackgroundTasks()
    with create_db(tmp_path / "runs.db") as db, use_runs_state_ctx(db):
        response = asyncio.run(
            _api_robots.run_robot_task(
                _api_robots.RobotRunRequestAPI(
                    robot_package_path=str(package),
                    task_name="Consume",
                    inputs={"INVOICE_INPUT": value},
                ),
                background,
                _request("fixture-queue"),
            )
        )
        asyncio.run(background())
        run = db.first(Run, "SELECT * FROM run WHERE id = ?", [response.run_id])
        assert run.status == RunStatus.PASSED
        assert json.loads(run.inputs) == {"INVOICE_INPUT": value}
        assert run.result is not None
        assert json.loads(json.loads(run.result)["output"]) == {"consumed": value}
        assert rcc.environments == [
            {
                "INVOICE_INPUT": value,
                "RC_WORKITEM_DB_PATH": str(tmp_path / "workitems.db"),
                "RC_WORKITEM_QUEUE_NAME": "fixture-queue",
            }
        ]
        assert "INVOICE_INPUT" not in os.environ
        assert all(not path.exists() for path in rcc.environment_files)
        assert not list((tmp_path / "artifacts").rglob("env.json"))


@pytest.mark.parametrize(
    "declaration,inputs,task_name",
    [
        (None, {"INVOICE_INPUT": "alternate"}, "Consume"),
        (["INVOICE_INPUT"], {"UNKNOWN": "alternate"}, "Consume"),
        (
            ["INVOICE_INPUT"],
            {"INVOICE_INPUT": "first", "invoice_input": "second"},
            "Consume",
        ),
        (["INVOICE_INPUT"], {"INVOICE_INPUT": "alternate"}, "Other"),
        ("INVOICE_INPUT", {"INVOICE_INPUT": "alternate"}, "Consume"),
        (["INVOICE_INPUT", "invoice_input"], {"INVOICE_INPUT": "alternate"}, "Consume"),
        (["INVOICE_INPUT"], {"INVOICE_INPUT": "nul\x00value"}, "Consume"),
        (["INVOICE_INPUT"], {"INVOICE_INPUT": "x" * 4097}, "Consume"),
        (
            [f"INPUT_{n}" for n in range(33)],
            {f"INPUT_{n}": "x" for n in range(33)},
            "Consume",
        ),
        (
            [f"INPUT_{n}" for n in range(4)],
            {f"INPUT_{n}": "x" * 4096 for n in range(4)},
            "Consume",
        ),
        (["invalid-name"], {"invalid-name": "x"}, "Consume"),
    ],
)
def test_robot_input_rejection_precedes_run_and_artifact_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, declaration, inputs, task_name
):
    from actions.server import _api_robots, _artifact_storage, _models

    package = _robot(tmp_path, declaration)

    def forbidden(*args, **kwargs):
        pytest.fail("invalid robot inputs reached Runtime state")

    monkeypatch.setattr(_api_robots, "get_settings", forbidden)
    monkeypatch.setattr(_api_robots, "get_rcc_robots", forbidden)
    monkeypatch.setattr(_models, "get_db", forbidden)
    monkeypatch.setattr(_artifact_storage, "get_artifact_storage", forbidden)
    background = fastapi.BackgroundTasks()
    with pytest.raises(fastapi.HTTPException) as error:
        asyncio.run(
            _api_robots.run_robot_task(
                _api_robots.RobotRunRequestAPI(
                    robot_package_path=str(package), task_name=task_name, inputs=inputs
                ),
                background,
                _request(),
            )
        )
    assert error.value.status_code == 422
    assert not background.tasks


@pytest.mark.parametrize(
    "name",
    [
        "PATH",
        "Path",
        "PYTHONPATH",
        "LD_PRELOAD",
        "DYLD_INSERT_LIBRARIES",
        "RCC_HOME",
        "RC_WORKITEM_DB_PATH",
        "RC_WORKITEM_QUEUE_NAME",
        "ROBOT_ROOT",
        "ROBOT_ARTIFACTS",
        "HTTP_PROXY",
        "AWS_ACCESS_KEY_ID",
        "API_TOKEN",
        "_JAVA_OPTIONS",
        "BASHOPTS",
        "SHELLOPTS",
        "GLIBC_TUNABLES",
        "GCONV_PATH",
        "OPENSSL_CONF",
        "SSLKEYLOGFILE",
    ],
)
def test_robot_inputs_cannot_declare_process_runtime_or_secret_controls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str
):
    test_robot_input_rejection_precedes_run_and_artifact_state(
        monkeypatch, tmp_path, [name], {name: "refused"}, "Consume"
    )


def test_standalone_robot_helper_forwards_only_declared_inputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog
):
    from actions.server import _rcc_robot_utils

    package = _robot(tmp_path, ["INVOICE_INPUT"])
    captured = []
    environment_files = []

    def run(args):
        assert "-e" in args
        path = Path(args[args.index("-e") + 1])
        environment_files.append(path)
        captured.append(json.loads(path.read_text(encoding="utf-8")))
        return "consumed", "", 0

    monkeypatch.setattr(_rcc_robot_utils, "_run_rcc_command", run)
    assert _rcc_robot_utils.run_robot_task(
        package, "Consume", {"INVOICE_INPUT": "private-input-value"}
    ) == ("consumed", "", 0)
    assert captured == [{"INVOICE_INPUT": "private-input-value"}]
    assert all(not path.exists() for path in environment_files)
    assert "private-input-value" not in caplog.text
    assert (
        _rcc_robot_utils.run_robot_task(
            package, "Other", {"INVOICE_INPUT": "private-input-value"}
        )[2]
        == -1
    )
    assert len(captured) == 1


@pytest.mark.parametrize("inputs", [None, {}])
def test_standalone_robot_helper_preserves_legacy_archive_launch_without_inputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inputs
):
    from actions.server import _rcc_robot_utils

    archive = tmp_path / "legacy.zip"
    archive.write_bytes(b"legacy RCC target")
    calls = []

    def run(args):
        calls.append(args)
        return "legacy", "", 0

    monkeypatch.setattr(_rcc_robot_utils, "_run_rcc_command", run)
    assert _rcc_robot_utils.run_robot_task(archive, "Legacy", inputs) == (
        "legacy",
        "",
        0,
    )
    assert calls == [["task", "run", "--robot", str(archive), "--task", "Legacy"]]


def test_standalone_robot_helper_rejects_archive_inputs_explicitly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from actions.server import _rcc_robot_utils

    archive = tmp_path / "legacy.zip"
    archive.write_bytes(b"legacy RCC target")

    def forbidden(*args, **kwargs):
        pytest.fail("nonempty archive inputs reached RCC")

    monkeypatch.setattr(_rcc_robot_utils, "_run_rcc_command", forbidden)
    stdout, stderr, code = _rcc_robot_utils.run_robot_task(
        archive, "Legacy", {"INVOICE_INPUT": "value"}
    )
    assert (stdout, code) == ("", -1)
    assert stderr == "Nonempty Robot inputs require an unpacked package directory"


@pytest.mark.parametrize("inputs", [None, {}])
def test_empty_robot_inputs_do_not_require_new_metadata(tmp_path: Path, inputs):
    from actions.server._robot_inputs import validate_robot_inputs

    assert validate_robot_inputs(tmp_path / "legacy-package", "Legacy", inputs) == {}


@pytest.mark.parametrize("config_name", ["robot.yaml", "package.yaml"])
def test_robot_input_declarations_use_selected_package_configuration(
    tmp_path: Path, config_name: str
):
    from actions.server._robot_inputs import validate_robot_inputs

    package = _robot(tmp_path, ["INVOICE_INPUT"], config_name=config_name)
    assert validate_robot_inputs(package, "Consume", {"INVOICE_INPUT": ""}) == {
        "INVOICE_INPUT": ""
    }


def test_robot_task_environment_is_private_and_removed_on_failure(tmp_path: Path):
    from actions.server._robot_inputs import robot_task_environment

    previous_umask = os.umask(0o022) if os.name == "posix" else None
    try:
        with pytest.raises(RuntimeError, match="launch failed"):
            with robot_task_environment({"INPUT": "value"}) as path:
                assert json.loads(path.read_text(encoding="utf-8")) == {
                    "INPUT": "value"
                }
                if os.name == "posix":
                    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
                    assert stat.S_IMODE(path.stat().st_mode) == 0o600
                raise RuntimeError("launch failed")
    finally:
        if previous_umask is not None:
            os.umask(previous_umask)
    assert not path.exists()
    assert not path.parent.exists()


@pytest.mark.real_rcc
@pytest.mark.skipif(
    not os.environ.get("ACTIONS_ROBOT_INPUT_RCC"),
    reason="set ACTIONS_ROBOT_INPUT_RCC to pinned RCC18.19.3 for actual task-input acceptance",
)
def test_pinned_rcc_executes_selected_task_with_declared_inputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from actions.server import _api_robots, _artifact_storage
    from actions.server._models import Run, RunStatus, create_db
    from actions.server._rcc import Rcc
    from actions.server._runs_state_cache import use_runs_state_ctx

    rcc_path = Path(os.environ["ACTIONS_ROBOT_INPUT_RCC"]).resolve()
    version = subprocess.run(
        [str(rcc_path), "version"], capture_output=True, text=True, check=True
    )
    assert version.stdout.strip() == "v18.19.3"
    package = _robot(tmp_path, ["INVOICE_INPUT"])
    toolkit_config = Path(__file__).parents[3] / "developer/setup.yaml"
    (package / "conda.yaml").write_bytes(toolkit_config.read_bytes())
    (package / "task.py").write_text(
        "import json,os\nfrom pathlib import Path\n"
        "value = os.environ.get('INVOICE_INPUT', 'default')\n"
        "Path('consumed.json').write_text(json.dumps({'consumed': value}), encoding='utf-8')\n",
        encoding="utf-8",
    )
    rcc = Rcc(rcc_path, tmp_path / "rcc-home")
    (tmp_path / "artifacts").mkdir()
    storage = _artifact_storage.create_artifact_storage("local", tmp_path / "artifacts")
    monkeypatch.setattr(_artifact_storage, "get_artifact_storage", lambda: storage)
    monkeypatch.setattr(_api_robots, "get_rcc_robots", lambda: rcc)
    monkeypatch.setattr(
        _api_robots, "get_settings", lambda: SimpleNamespace(datadir=tmp_path)
    )
    with create_db(tmp_path / "runs.db") as db, use_runs_state_ctx(db):
        for inputs, expected in [
            ({"INVOICE_INPUT": "first"}, "first"),
            (
                {"INVOICE_INPUT": 'second 雪 \\ " $(literal)\nvalue'},
                'second 雪 \\ " $(literal)\nvalue',
            ),
            (None, "default"),
        ]:
            background = fastapi.BackgroundTasks()
            response = asyncio.run(
                _api_robots.run_robot_task(
                    _api_robots.RobotRunRequestAPI(
                        robot_package_path=str(package),
                        task_name="Consume",
                        inputs=inputs,
                    ),
                    background,
                    _request(),
                )
            )
            asyncio.run(background())
            run = db.first(Run, "SELECT * FROM run WHERE id = ?", [response.run_id])
            assert run.status == RunStatus.PASSED, run.error_message
            assert json.loads(run.inputs) == (inputs or {})
            assert json.loads(
                (package / "consumed.json").read_text(encoding="utf-8")
            ) == {"consumed": expected}
    assert "INVOICE_INPUT" not in os.environ
    assert not list((tmp_path / "artifacts").rglob("env.json"))
