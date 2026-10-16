"""API tests for work-item attachment boundaries."""

import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import pytest
from actions.work_items import SQLiteAdapter
from fastapi import FastAPI
from fastapi.testclient import TestClient

from actions.server import _api_work_items, _work_items_import


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    adapter = SQLiteAdapter(
        db_path=str(tmp_path / "workitems.db"), files_dir=str(tmp_path / "files")
    )
    monkeypatch.setattr(_api_work_items, "_adapter", adapter)
    app = FastAPI()
    app.include_router(_api_work_items.work_items_api_router)
    return TestClient(app)


@pytest.fixture
def runtime_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """Exercise Work Items through the Runtime's registered error handler."""
    from actions.server._app import get_app
    from actions.server._cli_impl import _create_parser
    from actions.server._protocols import ArgumentsNamespaceRequiringDatadir
    from actions.server._settings import setup_settings

    args: ArgumentsNamespaceRequiringDatadir = _create_parser().parse_args(
        ["import", "--datadir", str(tmp_path)]
    )
    with setup_settings(args):
        get_app.cache_clear()
        adapter = SQLiteAdapter(
            db_path=str(tmp_path / "workitems.db"),
            files_dir=str(tmp_path / "files"),
        )
        monkeypatch.setattr(_api_work_items, "_adapter", adapter)
        app = get_app()
        app.include_router(_api_work_items.work_items_api_router)
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
        get_app.cache_clear()


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


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (
            _work_items_import.WorkItemsPackageUnavailableError(
                "internal bundle path is not available"
            ),
            "work_items_runtime_unavailable",
        ),
        (
            _work_items_import.WorkItemsPackageLoadError("private import failure"),
            "work_items_load_failed",
        ),
    ],
)
def test_work_items_loader_failure_is_actionable_and_does_not_expose_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    failure: ImportError,
    expected_code: str,
) -> None:
    """Report Runtime loading failures without recommending package.yaml edits."""
    monkeypatch.setattr(_api_work_items, "_adapter", None)
    monkeypatch.setattr(
        _api_work_items,
        "load_work_items_types",
        lambda: (_ for _ in ()).throw(failure),
    )

    response = client.get("/api/work-items/stats")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == expected_code
    assert "Runtime" in detail["message"]
    assert "package.yaml" not in detail["message"]
    assert "internal bundle path" not in response.text
    assert "private import failure" not in response.text


def test_work_items_storage_error_is_bounded_and_actionable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Map SQLite failures to a safe Runtime storage recovery message."""
    adapter = _api_work_items._adapter
    assert adapter is not None

    def fail_stats(*, queue_name: str) -> dict[str, int]:
        raise sqlite3.OperationalError("/private/datadir/workitems.db is corrupt")

    monkeypatch.setattr(adapter, "get_queue_stats", fail_stats)
    response = TestClient(client.app, raise_server_exceptions=False).get(
        "/api/work-items/stats"
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "work_items_storage_unavailable"
    assert "local Runtime storage" in detail["message"]
    assert "/private/datadir" not in response.text


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (
            _work_items_import.WorkItemsPackageUnavailableError("missing source"),
            "work_items_runtime_unavailable",
        ),
        (
            _work_items_import.WorkItemsPackageLoadError("failed import"),
            "work_items_load_failed",
        ),
    ],
)
def test_runtime_http_error_handler_preserves_work_items_recovery_code(
    runtime_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    failure: ImportError,
    expected_code: str,
) -> None:
    """The assembled Runtime response keeps structured Work Items error detail."""
    monkeypatch.setattr(_api_work_items, "_adapter", None)
    monkeypatch.setattr(
        _api_work_items,
        "load_work_items_types",
        lambda: (_ for _ in ()).throw(failure),
    )

    response = runtime_client.get("/api/work-items/stats")

    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "internal-error"
    assert body["detail"]["code"] == expected_code
    assert body["message"] == str(body["detail"])
    assert str(failure) not in response.text


def test_runtime_http_error_handler_keeps_plain_detail_contract(
    runtime_client: TestClient,
) -> None:
    """Plain FastAPI error details retain their existing Runtime response shape."""
    from fastapi import HTTPException

    async def raise_plain_error() -> None:
        raise HTTPException(status_code=400, detail="ordinary error message")

    assert isinstance(runtime_client.app, FastAPI)
    runtime_client.app.add_api_route("/plain-error", raise_plain_error, methods=["GET"])
    response = runtime_client.get("/plain-error")

    assert response.status_code == 400
    assert response.json() == {
        "error_code": "internal-error",
        "message": "ordinary error message",
    }


def test_corrupt_stored_payload_is_storage_failure_for_detail_and_list(
    runtime_client: TestClient,
    tmp_path: Path,
) -> None:
    """Malformed persisted JSON is not reported as a missing item or empty queue."""
    created = runtime_client.post(
        "/api/work-items", json={"payload": {"probe": "valid"}}
    )
    assert created.status_code == 200
    item_id = created.json()["id"]

    with sqlite3.connect(tmp_path / "workitems.db") as connection:
        connection.execute(
            "UPDATE work_items SET payload = ? WHERE id = ?", ("not-json", item_id)
        )

    detail = runtime_client.get(f"/api/work-items/{item_id}")
    listed = runtime_client.get("/api/work-items")

    for response in (detail, listed):
        assert response.status_code == 503
        body = response.json()
        assert body["detail"]["code"] == "work_items_storage_unavailable"
        assert "not found" not in body["message"].lower()
        assert str(tmp_path) not in response.text

    missing = runtime_client.get("/api/work-items/does-not-exist")
    assert missing.status_code == 404
    assert runtime_client.get("/api/work-items?queue_name=empty-queue").json() == {
        "items": [],
        "total": 0,
    }
