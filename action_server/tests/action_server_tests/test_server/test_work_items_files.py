"""API tests for work-item attachment boundaries."""

import subprocess
import sys
from pathlib import Path

import pytest
from actions.work_items import SQLiteAdapter
from fastapi import FastAPI
from fastapi.testclient import TestClient

from actions.server import _api_work_items


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    adapter = SQLiteAdapter(
        db_path=str(tmp_path / "workitems.db"), files_dir=str(tmp_path / "files")
    )
    monkeypatch.setattr(_api_work_items, "_adapter", adapter)
    app = FastAPI()
    app.include_router(_api_work_items.work_items_api_router)
    return TestClient(app)


def test_work_item_file_api_maps_attachment_errors_and_round_trips(
    client: TestClient,
) -> None:
    """Expose stable attachment error mapping and round trips."""
    item_id = client.post("/api/work-items", json={"payload": {}}).json()["id"]

    unsafe = client.post(
        f"/api/work-items/{item_id}/files",
        files={"file": ("../outside.txt", b"blocked")},
    )
    assert unsafe.status_code == 400

    quoted_name = 'quoted".txt'
    assert (
        client.get(f"/api/work-items/{item_id}/files/{quoted_name}").status_code == 400
    )
    assert (
        client.delete(f"/api/work-items/{item_id}/files/{quoted_name}").status_code
        == 400
    )

    missing = client.get(f"/api/work-items/{item_id}/files/missing.txt")
    assert missing.status_code == 404
    assert client.get("/api/work-items/missing/files/missing.txt").status_code == 404

    upload = client.post(
        f"/api/work-items/{item_id}/files", files={"file": ("report.txt", b"report")}
    )
    assert upload.status_code == 200
    assert (
        client.post(
            f"/api/work-items/{item_id}/files",
            files={"file": ("report.txt", b"report")},
        ).status_code
        == 409
    )

    download = client.get(f"/api/work-items/{item_id}/files/report.txt")
    assert download.status_code == 200
    assert download.content == b"report"
    assert (
        download.headers["content-disposition"] == 'attachment; filename="report.txt"'
    )
    delete = client.delete(f"/api/work-items/{item_id}/files/report.txt")
    assert delete.status_code == 200


def test_work_items_import_ignores_project_actions_module(tmp_path: Path) -> None:
    """A conventional project actions.py must not shadow the REST adapter path."""
    (tmp_path / "actions.py").write_text("PROJECT_ACTIONS = True\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-P",
            "-c",
            (
                "from pathlib import Path; from types import SimpleNamespace; "
                "from fastapi import FastAPI; from fastapi.testclient import TestClient; "
                "from actions.server import _api_work_items as api; "
                "api.get_settings=lambda: SimpleNamespace(datadir=Path.cwd()); "
                "app=FastAPI(); app.include_router(api.work_items_api_router); "
                "response=TestClient(app).post('/api/work-items',json={'payload':{}}); "
                "assert response.status_code == 200, response.text; print(response.json()['state'])"
            ),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "PENDING"


def test_rest_projects_non_object_library_payload_to_null(client: TestClient) -> None:
    """Library scalar payloads cannot violate the REST object-or-null schema."""
    assert _api_work_items._adapter is not None
    item_id = _api_work_items._adapter.seed_input(payload="scalar")

    detail = client.get(f"/api/work-items/{item_id}")
    assert detail.status_code == 200
    assert detail.json()["payload"] is None

    listed = client.get("/api/work-items")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["payload"] is None
