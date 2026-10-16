"""Exercise installed Runtime request boundaries without importing checkout code."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from actions.server import _api_robots
from actions.server._artifact_storage import create_artifact_storage
from actions.server._server import _mount_artifact_static_files


async def request(app, path, *, method="GET", headers=(), chunks=(b"",)):
    messages = []
    consumed = 0

    async def receive():
        nonlocal consumed
        if consumed >= len(chunks):
            raise AssertionError("request consumed beyond supplied body")
        body = chunks[consumed]
        consumed += 1
        return {
            "type": "http.request",
            "body": body,
            "more_body": consumed < len(chunks),
        }

    async def send(message):
        messages.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "root_path": "",
            "query_string": b"",
            "headers": list(headers),
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 1234),
        },
        receive,
        send,
    )
    return (
        messages[0]["status"],
        b"".join(m.get("body", b"") for m in messages),
        consumed,
    )


def forbidden(*args, **kwargs):
    raise AssertionError("rejected request reached protected boundary")


async def verify():
    checks = 0
    with tempfile.TemporaryDirectory(prefix="runtime-boundaries-") as temp:
        root = Path(temp).resolve(strict=True)
        storage = create_artifact_storage("local", root)
        storage.create_run_artifacts_dir("runs/run-a")
        storage.write_bytes("runs/run-a", "payload.bin", b"0123456789")
        storage.bind_run("run-a", "runs/run-a", {"id": "run-a"})
        for api_key in (None, "secret"):
            app = FastAPI()
            _mount_artifact_static_files(app, "local", root, api_key=api_key)
            prefix = "/artifacts/run-a/" if api_key else "/artifacts/runs/run-a/"
            auth = ((b"authorization", b"Bearer secret"),)
            status, body, _ = await request(app, prefix + "payload.bin", headers=auth)
            assert (status, body) == (200, b"0123456789")
            status, body, _ = await request(
                app, prefix + "payload.bin", headers=auth + ((b"range", b"bytes=2-5"),)
            )
            assert (status, body) == (206, b"2345")
            assert (
                await request(app, prefix + "payload.bin", method="HEAD", headers=auth)
            )[0] == 200
            checks += 3
            with patch.object(StaticFiles, "lookup_path", forbidden):
                for name in (
                    r"\\example.invalid\share\file",
                    r"nested/\\example.invalid\share\file",
                    r"C:\file",
                    r"C:file",
                    r"\\?\UNC\example.invalid\share\file",
                    r"\\.\pipe\file",
                    "nested/C:/file",
                ):
                    assert (await request(app, prefix + name, headers=auth))[0] == 404
                    checks += 1

    app = FastAPI()
    app.include_router(_api_robots.robots_api_router)
    form_headers = ((b"content-type", b"application/x-www-form-urlencoded"),)
    with patch.object(Request, "_get_form", forbidden):
        for length in (None, b"1", b"16385", b"9" * 5000):
            headers = form_headers + (((b"content-length", length),) if length else ())
            status, _, consumed = await request(
                app,
                "/api/robots/import",
                method="POST",
                headers=headers,
                chunks=(b"url=" + b"x" * 8188, b"x" * 8192, b"x", b"unconsumed"),
            )
            assert status == 413
            assert consumed == (0 if length and length != b"1" else 3)
            checks += 1

    seen = []

    async def download(url):
        seen.append(url)
        return False, "controlled download", None

    with patch.object(_api_robots, "_download_from_url", download):
        for body in (
            b"url=https%3A%2F%2Fexample.invalid%2Fa.zip",
            b"url=" + b"x" * 16380,
        ):
            status, response, _ = await request(
                app,
                "/api/robots/import",
                method="POST",
                headers=form_headers,
                chunks=(body,),
            )
            assert (
                status == 200
                and json.loads(response)["message"] == "controlled download"
            )
            checks += 1
    assert seen == ["https://example.invalid/a.zip", "x" * 16380]
    print(
        "RUNTIME_REQUEST_BOUNDARIES=" + json.dumps({"checks": checks, "status": "PASS"})
    )


if __name__ == "__main__":
    asyncio.run(verify())
