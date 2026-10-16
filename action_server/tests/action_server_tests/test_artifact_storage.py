import multiprocessing
import sys
from pathlib import Path, PureWindowsPath

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from actions.server._artifact_storage import (
    ArtifactStorageConfigurationError,
    ArtifactStorageNotFoundError,
    create_artifact_storage,
)
from actions.server._server import _mount_artifact_static_files


def _static_client(root: Path, backend: str = "local") -> TestClient:
    app = FastAPI()
    _mount_artifact_static_files(app, backend, root)
    return TestClient(app)


def test_static_artifacts_preserve_file_and_range_responses(tmp_path):
    (tmp_path / "run-a").mkdir()
    (tmp_path / "run-a" / "payload.bin").write_bytes(b"0123456789")

    client = _static_client(tmp_path)

    response = client.get("/artifacts/run-a/payload.bin")
    assert response.status_code == 200
    assert response.content == b"0123456789"

    response = client.get(
        "/artifacts/run-a/payload.bin", headers={"range": "bytes=2-5"}
    )
    assert response.status_code == 206
    assert response.content == b"2345"
    assert response.headers["content-range"] == "bytes 2-5/10"


def test_configured_static_artifacts_require_auth_and_are_run_scoped(tmp_path):
    storage = create_artifact_storage("local", tmp_path)
    storage.create_run_artifacts_dir("runs/run-a")
    storage.write_text("runs/run-a", "payload.txt", "authorized artifact")
    (tmp_path / "unrelated.txt").write_text("outside run", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside root", encoding="utf-8")
    (tmp_path / "runs" / "run-a" / "linked.txt").symlink_to(outside)
    storage.bind_run(
        "run-a",
        "runs/run-a",
        {"id": "run-a", "relative_artifacts_dir": "runs/run-a"},
    )

    app = FastAPI()
    _mount_artifact_static_files(app, "local", tmp_path, api_key="secret")
    client = TestClient(app)

    response = client.get("/artifacts/run-a/payload.txt")
    assert response.status_code == 403

    response = client.get(
        "/artifacts/run-a/payload.txt",
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code == 200
    assert response.text == "authorized artifact"

    for headers in (
        [("Authorization", "Bearer secret"), ("Authorization", "Bearer wrong")],
        [("Authorization", "Bearer wrong"), ("Authorization", "Bearer secret")],
    ):
        assert (
            client.get("/artifacts/run-a/payload.txt", headers=headers).status_code
            == 403
        )

    assert client.head("/artifacts/run-a/payload.txt").status_code == 403
    assert (
        client.head(
            "/artifacts/run-a/payload.txt",
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 403
    )
    assert (
        client.head(
            "/artifacts/run-a/payload.txt",
            headers={"Authorization": "Bearer secret"},
        ).status_code
        == 200
    )

    assert (
        client.get(
            "/artifacts/run-a/payload.txt",
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 403
    )
    for path in (
        "/artifacts/unrelated.txt",
        "/artifacts/run-a/../unrelated.txt",
        "/artifacts/run-a/linked.txt",
    ):
        assert (
            client.get(path, headers={"Authorization": "Bearer secret"}).status_code
            == 404
        )

    response = client.get(
        "/artifacts/.action-server-run-bindings.json",
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code == 404


def test_shared_static_artifacts_are_unavailable(tmp_path):
    (tmp_path / "run-a").mkdir()
    (tmp_path / "run-a" / "payload.bin").write_bytes(b"shared artifact")

    response = _static_client(tmp_path, backend="shared-filesystem").get(
        "/artifacts/run-a/payload.bin"
    )

    assert response.status_code == 404


def test_local_storage_creates_and_reads_run_artifacts(tmp_path):
    storage = create_artifact_storage("local", tmp_path)

    storage.create_run_artifacts_dir("run-a")
    storage.write_bytes("run-a", "nested/data.bin", b"binary")

    assert storage.list_files("run-a") == [("nested/data.bin", 6)]
    assert storage.read_bytes("run-a", "nested/data.bin") == b"binary"


def test_default_local_storage_creates_missing_artifacts_root(tmp_path, monkeypatch):
    from actions.server import _artifact_storage, _settings
    from actions.server._settings import Settings

    settings = Settings(datadir=tmp_path, artifacts_dir=tmp_path / "artifacts")
    monkeypatch.setattr(_settings, "_global_settings", settings)

    storage = _artifact_storage.get_artifact_storage()

    assert storage.root == tmp_path / "artifacts"
    assert storage.root.is_dir()


def test_shared_storage_requires_a_root_and_is_selected_explicitly(tmp_path):
    with pytest.raises(ArtifactStorageConfigurationError):
        create_artifact_storage("shared-filesystem", None)

    storage = create_artifact_storage("shared-filesystem", tmp_path)
    storage.create_run_artifacts_dir("run-a")

    assert storage.root == tmp_path


def test_missing_reads_have_a_stable_not_found_error(tmp_path):
    storage = create_artifact_storage("local", tmp_path)
    storage.create_run_artifacts_dir("run-a")

    with pytest.raises(ArtifactStorageNotFoundError):
        storage.read_text("run-a", "missing.txt")


def test_run_storage_keys_are_isolated(tmp_path):
    storage = create_artifact_storage("local", tmp_path)
    storage.create_run_artifacts_dir("run-a")
    storage.create_run_artifacts_dir("run-b")
    storage.write_text("run-a", "result.txt", "a")

    with pytest.raises(ArtifactStorageNotFoundError):
        storage.read_text("run-b", "result.txt")


def _write_from_process(root, relative_key):
    storage = create_artifact_storage("shared-filesystem", root)
    storage.create_run_artifacts_dir(relative_key)
    storage.write_text(relative_key, "process.txt", "written by A")


def _bind_from_process(root, run_id):
    storage = create_artifact_storage("shared-filesystem", root)
    storage.create_run_artifacts_dir(f"runs/{run_id}")
    storage.bind_run(
        run_id,
        f"runs/{run_id}",
        {"id": run_id, "relative_artifacts_dir": f"runs/{run_id}"},
    )


def test_shared_filesystem_process_a_write_process_b_read(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    process = ctx.Process(target=_write_from_process, args=(tmp_path, "run-a"))
    process.start()
    process.join()
    assert process.exitcode == 0

    storage = create_artifact_storage("shared-filesystem", tmp_path)
    assert storage.read_text("run-a", "process.txt") == "written by A"


def test_concurrent_manifest_publication_is_complete_and_recoverable(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    processes = [
        ctx.Process(target=_bind_from_process, args=(tmp_path, f"run-{i}"))
        for i in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
    assert [process.exitcode for process in processes] == [0, 0]

    storage = create_artifact_storage("shared-filesystem", tmp_path)
    assert storage.run_storage_key("run-0") == "runs/run-0"
    assert storage.run_storage_key("run-1") == "runs/run-1"


def test_corrupt_manifest_fails_closed(tmp_path):
    storage = create_artifact_storage("shared-filesystem", tmp_path)
    (tmp_path / ".action-server-run-bindings.json").write_text("{")

    with pytest.raises(ArtifactStorageConfigurationError):
        storage.run_storage_key("run-a")


@pytest.mark.parametrize("key", ["", ".", "run/../run", "run/.", "../run"])
def test_storage_rejects_noncanonical_run_keys(tmp_path, key):
    storage = create_artifact_storage("local", tmp_path)

    with pytest.raises(ArtifactStorageConfigurationError):
        storage.create_run_artifacts_dir(key)


def test_storage_rejects_symlinked_run_and_artifact_paths(tmp_path):
    storage = create_artifact_storage("local", tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "run-link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ArtifactStorageConfigurationError):
        storage.create_run_artifacts_dir("run-link")

    storage.create_run_artifacts_dir("run-a")
    (tmp_path / "run-a" / "escape").symlink_to(outside, target_is_directory=True)
    (outside / "secret.txt").write_text("secret")

    with pytest.raises(ArtifactStorageConfigurationError):
        storage.read_text("run-a", "escape/secret.txt")


@pytest.mark.parametrize(
    "root_factory", [lambda p: p / "missing", lambda p: p / "file"]
)
def test_storage_rejects_invalid_roots(tmp_path, root_factory):
    root = root_factory(tmp_path)
    if root.name == "file":
        root.write_text("not a directory")

    with pytest.raises(ArtifactStorageConfigurationError):
        create_artifact_storage("shared-filesystem", root)


def test_storage_rejects_symlinked_root(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(ArtifactStorageConfigurationError):
        create_artifact_storage("shared-filesystem", link)


def test_storage_rejects_inaccessible_root(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "actions.server._artifact_storage.os.access", lambda *args: False
    )

    with pytest.raises(ArtifactStorageConfigurationError):
        create_artifact_storage("shared-filesystem", tmp_path)


def test_storage_manifest_is_durable_and_collision_safe(tmp_path):
    storage = create_artifact_storage("shared-filesystem", tmp_path)
    storage.create_run_artifacts_dir("runs/run-a")
    storage.bind_run("run-a", "runs/run-a")

    restarted = create_artifact_storage("shared-filesystem", tmp_path)
    assert restarted.run_storage_key("run-a") == "runs/run-a"
    with pytest.raises(ArtifactStorageConfigurationError):
        restarted.bind_run("run-a", "runs/run-b")


def test_independent_storage_api_reads_durable_run_binding_and_range_file(
    tmp_path, monkeypatch
):
    import asyncio

    from actions.server import _api_run, _artifact_storage, _runs_state_cache
    from actions.server._models import Run, RunStatus

    run = Run(
        id="run-a",
        status=RunStatus.PASSED,
        action_id="action-a",
        start_time="2026-01-01T00:00:00+00:00",
        run_time=1.0,
        inputs="{}",
        result="{}",
        error_message=None,
        relative_artifacts_dir="runs/run-a",
        numbered_id=1,
    )
    writer = create_artifact_storage("shared-filesystem", tmp_path)
    writer.create_run_artifacts_dir(run.relative_artifacts_dir)
    writer.write_bytes(run.relative_artifacts_dir, "payload.bin", b"0123456789")
    writer.bind_run(run.id, run.relative_artifacts_dir, run.__dict__)

    reader = create_artifact_storage("shared-filesystem", tmp_path)
    monkeypatch.setattr(_artifact_storage, "get_artifact_storage", lambda: reader)

    class MissingRunState:
        """Legacy-only cache stub: its fixture Run has no durable scoped pin."""

        semaphore = type(
            "Semaphore",
            (),
            {"__enter__": lambda self: self, "__exit__": lambda *args: None},
        )()

        def is_scoped_run(self, run_id):
            # This fixture models only the legacy manifest path for run-a.
            assert run_id == run.id
            return False

        def get_run_from_id(self, run_id):
            raise KeyError(run_id)

    monkeypatch.setattr(
        _runs_state_cache, "get_global_runs_state", lambda: MissingRunState()
    )
    assert _api_run.get_run_by_id(run.id).relative_artifacts_dir == "runs/run-a"
    assert _api_run.get_run_artifacts(run.id) == [
        _api_run.ArtifactInfo(name="payload.bin", size_in_bytes=10)
    ]
    assert _api_run.get_run_artifact_text(run.id, ["payload.bin"], None) == {
        "payload.bin": "0123456789"
    }
    response = _api_run.get_run_artifact_binary("run-a", "payload.bin")
    assert response.path == tmp_path / "runs" / "run-a" / "payload.bin"
    assert response.media_type == "application/octet-stream"

    events = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        events.append(message)

    asyncio.run(
        response(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [(b"range", b"bytes=2-5")],
                "asgi": {"spec_version": "2.4"},
            },
            receive,
            send,
        )
    )
    assert events[0]["status"] == 206
    assert b"".join(event["body"] for event in events[1:]) == b"2345"
    assert dict(events[0]["headers"])[b"content-range"] == b"bytes 2-5/10"


def test_storage_normalizes_equivalent_root_spelling_without_following_links(tmp_path):
    (tmp_path / "intermediate").mkdir()
    root = tmp_path / "artifacts"
    root.mkdir()
    storage = create_artifact_storage(
        "local", tmp_path / "intermediate" / ".." / "artifacts"
    )
    assert storage.root == root.resolve()
    assert storage.create_run_artifacts_dir("run-a") == root.resolve() / "run-a"


def test_storage_rejects_symlink_in_root_ancestor(tmp_path):
    target = tmp_path / "target"
    (target / "artifacts").mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ArtifactStorageConfigurationError):
        create_artifact_storage("local", link / "artifacts")


def test_storage_rejects_dangling_link_inside_root(tmp_path):
    storage = create_artifact_storage("local", tmp_path)
    (tmp_path / "dangling").symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(ArtifactStorageConfigurationError):
        storage.create_run_artifacts_dir("dangling/run-a")


def test_storage_checks_reparse_attributes_without_following_target(
    tmp_path, monkeypatch
):
    import stat
    from types import SimpleNamespace

    from actions.server._artifact_storage import _is_link_or_reparse_point

    dangling = tmp_path / "junction"
    assert not dangling.exists()
    original = Path.lstat
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda path: SimpleNamespace(
            st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
        if path == dangling
        else original(path),
    )
    assert _is_link_or_reparse_point(dangling)
    storage = create_artifact_storage("local", tmp_path)
    with pytest.raises(ArtifactStorageConfigurationError):
        storage.create_run_artifacts_dir("junction/run-a")


@pytest.mark.parametrize(
    "path, root",
    [
        (r"\\?\C:\storage\runs\run-a", r"C:\storage"),
        (r"C:\storage\runs\run-a", r"\\?\C:\storage"),
        (r"\\?\c:\STORAGE\runs\run-a", r"C:\storage"),
        # Identical namespaces keep their literal names; no alias conversion.
        (r"\\?\C:\storage.\runs\run-a", r"\\?\C:\storage."),
    ],
)
def test_containment_compares_equivalent_local_drive_prefixes(path, root):
    from actions.server._artifact_storage import _relative_parts

    assert _relative_parts(PureWindowsPath(path), PureWindowsPath(root)) == (
        "runs",
        "run-a",
    )
    assert _relative_parts(PureWindowsPath(root), PureWindowsPath(root)) == ()
    assert (
        _relative_parts(PureWindowsPath(path).parents[1], PureWindowsPath(root)) == ()
    )


@pytest.mark.parametrize(
    "path, root",
    [
        (r"\\?\D:\storage\run-a", r"C:\storage"),
        (r"\\?\C:\storage-other\run-a", r"C:\storage"),
        (r"\\?\C:\storage.\run-a", r"C:\storage"),
        ("\\\\?\\C:\\storage \\run-a", r"C:\storage"),
        (r"\\?\C:\storage\run-a", r"C:\storage."),
        (r"\\.\C:\storage\run-a", r"C:\storage"),
        (r"\\.\NUL", r"C:\storage"),
        (r"\\?\GLOBALROOT\Device\HarddiskVolume1\storage\run-a", r"C:\storage"),
        (r"\\?\UNC\server\share\run-a", r"\\server\share"),
        (r"\\?\Volume{12345678-1234-1234-1234-123456789abc}\run-a", r"C:\storage"),
        (r"\\?\C:storage\run-a", r"C:\storage"),
        (r"\\?\C:\storage\run-a", r"C:storage"),
        (r"\\?\C:\storage.\run-a", r"C:\storage."),
        (r"C:\storage.\run-a", r"\\?\C:\storage."),
        (r"\\?\C:\storage\run.\result.txt", r"C:\storage"),
        ("\\\\?\\C:\\storage\\run \\result.txt", r"C:\storage"),
        (r"\\?\C:\storage\NUL\result.txt", r"C:\storage"),
        (r"\\?\C:\storage\CON.txt", r"C:\storage"),
        (r"\\?\C:\storage\run-a\result.txt:stream", r"C:\storage"),
        (r"\\?\C:\storage\run-a\..\result.txt", r"C:\storage"),
    ],
)
def test_drive_prefix_comparison_preserves_namespace_and_directory_boundaries(
    path, root
):
    from actions.server._artifact_storage import _relative_parts

    with pytest.raises(ValueError):
        _relative_parts(PureWindowsPath(path), PureWindowsPath(root))


def test_containment_checks_reparse_entries_in_the_io_namespace(monkeypatch):
    from actions.server import _artifact_storage

    class CandidatePath(PureWindowsPath):
        def absolute(self):
            return self

        def resolve(self, *, strict=False):
            # An inside-root target must still be rejected if reached by a link.
            return PureWindowsPath(r"\\?\C:\storage\safe\result.txt")

    storage = object.__new__(_artifact_storage.FilesystemArtifactStorage)
    storage.root = PureWindowsPath(r"C:\storage")
    linked_directory = PureWindowsPath(r"\\?\C:\storage\run-a")
    checked = []

    def is_reparse(path):
        checked.append(path)
        return path == linked_directory

    monkeypatch.setattr(_artifact_storage, "_is_link_or_reparse_point", is_reparse)
    with pytest.raises(ArtifactStorageConfigurationError, match="symlink"):
        storage._contained(
            CandidatePath(linked_directory / "result.txt"),
            "Artifact path",
            require_exists=True,
        )
    assert checked == [linked_directory]


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows path resolution")
def test_storage_handles_mixed_resolved_drive_prefixes(tmp_path, monkeypatch):
    storage = create_artifact_storage("shared-filesystem", tmp_path)
    root = storage.root
    if len(root.drive) != 2 or root.root != "\\":
        pytest.skip("requires an ordinary fully qualified local drive root")
    original_resolve = Path.resolve
    prefixed_results = []

    def mixed_resolve(path, *args, **kwargs):
        resolved = original_resolve(path, *args, **kwargs)
        # Simulate the documented non-strict resolver result for these owned,
        # ordinary fixture names; do not change the root or outside paths.
        spelling = str(resolved)
        ordinary = Path(spelling[4:]) if spelling.startswith("\\\\?\\") else resolved
        try:
            ordinary.relative_to(root)
        except ValueError:
            return resolved
        if ordinary == root or ordinary.suffix == ".txt":
            return ordinary
        extended = Path("\\\\?\\" + str(ordinary))
        prefixed_results.append(extended)
        return extended

    monkeypatch.setattr(Path, "resolve", mixed_resolve)
    run_dir = storage.create_run_artifacts_dir("runs/run-a")
    assert str(run_dir).startswith("\\\\?\\")
    storage.write_text("runs/run-a", "nested/result.txt", "retained I/O path")
    storage.bind_run("run-a", "runs/run-a")
    restarted = create_artifact_storage("shared-filesystem", root)
    assert restarted.run_storage_key("run-a") == "runs/run-a"
    assert restarted.read_text("runs/run-a", "nested/result.txt") == "retained I/O path"
    assert restarted.list_files("runs/run-a") == [("nested/result.txt", 17)]
    assert prefixed_results
    with pytest.raises(ArtifactStorageConfigurationError, match="storage root"):
        restarted._contained(
            Path("\\\\?\\" + str(root)), "Artifact path", require_exists=True
        )
