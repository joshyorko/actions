"""Robot completion copies survive source changes and Runtime restarts."""

import asyncio
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.testclient import TestClient


@pytest.mark.parametrize("success", [True, False])
@pytest.mark.parametrize("output_name", ["output", "custom/nested"])
def test_completed_robot_artifacts_are_retrievable_after_restart(
    tmp_path: Path, monkeypatch, success: bool, output_name: str
):
    from actions.server import _api_robots, _api_run, _runs_state_cache, _settings
    from actions.server._artifact_storage import get_artifact_storage
    from actions.server._models import RunStatus, create_db, load_db
    from actions.server._server import _ConfiguredAPIKeyMiddleware
    from actions.server._settings import Settings

    package = tmp_path / "robot"
    package.mkdir()
    (package / "robot.yaml").write_text(
        f"artifactsDir: {output_name}\ntasks:\n  task:\n    shell: echo ok\n"
    )
    (package / "conda.yaml").write_text("dependencies: []\n")
    settings = Settings(datadir=tmp_path, artifacts_dir=tmp_path / "artifacts")
    monkeypatch.setattr(_settings, "get_settings", lambda: settings)
    monkeypatch.setattr(_api_robots, "get_settings", lambda: settings)
    name = "report.json" if success else "failure.json"
    payload = json.dumps({"success": success}).encode()

    class Rcc:
        def get_package_yaml_hash(self, *args, **kwargs):
            return "owned-environment"

        def create_env_and_get_vars(self, *args, **kwargs):
            return SimpleNamespace(success=True, result=SimpleNamespace(env={}))

        def _run_rcc(self, *args, **kwargs):
            output = package / output_name
            output.mkdir(parents=True, exist_ok=True)
            (output / name).write_bytes(payload)
            (output / "log.html").write_bytes(b"<html>owned robot log</html>")
            return SimpleNamespace(success=success, result="console", message="failure")

    monkeypatch.setattr(_api_robots, "get_rcc_robots", Rcc)
    database = tmp_path / "server.db"
    with create_db(database) as db:
        monkeypatch.setattr(
            _runs_state_cache, "_runs_state", _runs_state_cache.RunsState(db)
        )
        background = BackgroundTasks()
        response = asyncio.run(
            _api_robots.run_robot_task(
                _api_robots.RobotRunRequestAPI(
                    robot_package_path=str(package), task_name="task"
                ),
                background,
                Request({"type": "http", "headers": []}),
            )
        )
        asyncio.run(background())
        run_id = response.run_id
        assert _api_run.get_run_by_id(run_id).status == (
            RunStatus.PASSED if success else RunStatus.FAILED
        )
        assert name in {item.name for item in _api_run.get_run_artifacts(run_id)}
        key = get_artifact_storage().run_storage_key(run_id)
        assert get_artifact_storage().read_bytes(key, name) == payload

    # A subsequent invocation can replace/remove the source without changing
    # the completed Run's captured bytes.
    (package / output_name / name).write_bytes(b"later invocation")
    shutil.rmtree(package)
    with load_db(database) as db:
        monkeypatch.setattr(
            _runs_state_cache, "_runs_state", _runs_state_cache.RunsState(db)
        )
        app = FastAPI()
        app.add_middleware(_ConfiguredAPIKeyMiddleware, api_key="owned-key")
        app.include_router(_api_run.run_api_router)
        client = TestClient(app)
        url = f"/api/runs/{run_id}/artifacts/binary-content"
        for headers in ({}, {"Authorization": "Bearer wrong"}):
            assert (
                client.get(
                    url, params={"artifact_name": name}, headers=headers
                ).status_code
                == 403
            )
        headers = {"Authorization": "Bearer owned-key"}
        listed = client.get(f"/api/runs/{run_id}/artifacts", headers=headers)
        assert listed.status_code == 200
        assert name in {item["name"] for item in listed.json()}
        text = client.get(
            f"/api/runs/{run_id}/artifacts/text-content",
            params={"artifact_names": name},
            headers=headers,
        )
        assert text.status_code == 200
        assert text.json()[name] == payload.decode()
        assert client.get(f"/api/runs/{run_id}", headers=headers).json()["status"] == (
            RunStatus.PASSED if success else RunStatus.FAILED
        )
        result = client.get(url, params={"artifact_name": name}, headers=headers)
        assert result.status_code == 200
        assert result.content == payload
        ranged = client.get(
            url,
            params={"artifact_name": name},
            headers={**headers, "Range": "bytes=0-3"},
        )
        assert ranged.status_code == 206
        assert ranged.content == payload[:4]
        assert get_artifact_storage().run_storage_key(run_id) == key
