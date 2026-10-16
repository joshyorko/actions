"""Exercise request rejection before dependency parsing or filesystem lookup."""

import asyncio
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from actions.server._api_robots import robots_api_router
from actions.server._server import _mount_artifact_static_files


@pytest.mark.parametrize("api_key", [None, "secret"])
@pytest.mark.parametrize(
    "name",
    [
        r"\\example.invalid\share\file",
        r"nested/\\example.invalid\share\file",
        r"C:\file",
        r"C:file",
        r"\\?\UNC\example.invalid\share\file",
        r"\\.\pipe\file",
    ],
)
def test_artifact_rejects_windows_names_before_lookup(
    tmp_path, monkeypatch, api_key, name
):
    from actions.server._artifact_storage import create_artifact_storage

    storage = create_artifact_storage("local", tmp_path)
    storage.create_run_artifacts_dir("runs/run-a")
    storage.bind_run("run-a", "runs/run-a", {"id": "run-a"})
    app = FastAPI()
    _mount_artifact_static_files(app, "local", tmp_path, api_key=api_key)

    def forbidden_lookup(*args, **kwargs):
        pytest.fail("untrusted Windows name reached filesystem lookup")

    monkeypatch.setattr(StaticFiles, "lookup_path", forbidden_lookup)
    response = TestClient(app).get(
        "/artifacts/run-a/" + quote(name, safe="/"),
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code == 404


@pytest.mark.parametrize("declared_length", [None, "1", "16385"])
def test_urlencoded_body_is_bounded_before_parser(monkeypatch, declared_length):
    app = FastAPI()
    app.include_router(robots_api_router)

    async def forbidden_parser(*args, **kwargs):
        pytest.fail("oversized URL-encoded body reached form parser")

    monkeypatch.setattr(Request, "_get_form", forbidden_parser)
    chunks = [b"url=" + b"x" * 8188, b"x" * 8192, b"x", b"not consumed"]
    received = 0
    messages = []

    async def receive():
        nonlocal received
        chunk = chunks[received]
        received += 1
        return {"type": "http.request", "body": chunk, "more_body": True}

    async def send(message):
        messages.append(message)

    headers = [(b"content-type", b"application/x-www-form-urlencoded; charset=UTF-8")]
    if declared_length is not None:
        headers.append((b"content-length", declared_length.encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/robots/import",
        "root_path": "",
        "query_string": b"",
        "headers": headers,
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
    }
    asyncio.run(app(scope, receive, send))
    assert messages[0]["status"] == 413
    assert received == (0 if declared_length == "16385" else 3)


def test_bounded_urlencoded_form_reaches_importer(monkeypatch):
    from actions.server import _api_robots

    seen = []

    async def download(url):
        seen.append(url)
        return False, "controlled download", None

    monkeypatch.setattr(_api_robots, "_download_from_url", download)
    app = FastAPI()
    app.include_router(robots_api_router)
    response = TestClient(app).post(
        "/api/robots/import", data={"url": "https://example.invalid/a.zip?q=a+b"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "controlled download"
    assert seen == ["https://example.invalid/a.zip?q=a+b"]


def test_multipart_zip_still_reaches_upload_boundary(monkeypatch):
    from actions.server import _api_robots

    seen = []

    async def save(file):
        seen.append((file.filename, await file.read()))
        raise _api_robots._RobotImportLimitError("controlled upload")

    monkeypatch.setattr(_api_robots, "_save_uploaded_robot", save)
    app = FastAPI()
    app.include_router(robots_api_router)
    response = TestClient(app).post(
        "/api/robots/import",
        files={"file": ("robot.zip", b"zip-control", "application/zip")},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "controlled upload"
    assert seen == [("robot.zip", b"zip-control")]
