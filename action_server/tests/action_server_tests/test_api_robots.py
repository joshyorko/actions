import asyncio
import io
import os
import shutil
import socket
import stat
import sys
import types
import zipfile
from pathlib import Path
from typing import Any, ClassVar, Self

import pytest


def _zip_bytes(members: dict[str, bytes | str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return output.getvalue()


def _write_zip(path: Path, members: dict[str, bytes | str]) -> None:
    path.write_bytes(_zip_bytes(members))


def _valid_robot_files(root: str = "robot") -> dict[str, str]:
    return {
        f"{root}/robot.yaml": "name: imported\ntasks:\n  run:\n    shell: echo ok\n",
        f"{root}/task.py": "print('ok')\n",
    }


class _FixedTemporaryDirectory:
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self) -> str:
        self.path.mkdir()
        return str(self.path)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        shutil.rmtree(self.path)


class _ChunkedUpload:
    def __init__(self, payload: bytes, chunk_size: int = 3) -> None:
        self.filename = "robot.zip"
        self._payload = payload
        self._chunk_size = chunk_size
        self._offset = 0
        self.read_sizes: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if self._offset >= len(self._payload):
            return b""
        if size < 0:
            end = len(self._payload)
        else:
            end = min(self._offset + min(size, self._chunk_size), len(self._payload))
        chunk = self._payload[self._offset : end]
        self._offset = end
        return chunk


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        *,
        headers: dict[str, str] | None = None,
        chunks: tuple[bytes, ...] = (),
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    async def aiter_bytes(self, chunk_size: int | None = None):
        for chunk in self._chunks:
            yield chunk


class _FakeHTTPXClient:
    instances: ClassVar[list["_FakeHTTPXClient"]] = []
    responses: ClassVar[dict[str, _FakeResponse]] = {}

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.urls: list[str] = []
        self.__class__.instances.append(self)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def stream(self, method: str, url: str) -> _FakeResponse:
        assert method == "GET"
        self.urls.append(url)
        return self.__class__.responses[url]


def _fake_httpx2(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeHTTPXClient.instances.clear()
    _FakeHTTPXClient.responses = {}
    module = types.SimpleNamespace(
        AsyncClient=_FakeHTTPXClient,
        HTTPStatusError=RuntimeError,
        RequestError=RuntimeError,
    )
    monkeypatch.setitem(sys.modules, "httpx2", module)


def _allow_test_download_host(monkeypatch: pytest.MonkeyPatch) -> None:
    def getaddrinfo(host, *args, **kwargs):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", 443),
            )
        ]

    monkeypatch.setattr(
        "actions.server._api_robots.socket",
        types.SimpleNamespace(
            SOCK_STREAM=socket.SOCK_STREAM,
            getaddrinfo=getaddrinfo,
        ),
        raising=False,
    )


def test_robot_zip_rejects_raw_parent_root_without_copying_parent_sentinel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    staging_parent = tmp_path / "staging-parent"
    staging = staging_parent / "staging"
    staging_parent.mkdir()
    robots_dir = tmp_path / "robots"
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots_dir)
    monkeypatch.setattr(
        _api_robots.tempfile,
        "TemporaryDirectory",
        lambda: _FixedTemporaryDirectory(staging),
    )

    (staging_parent / "robot.yaml").write_text(
        "name: seeded\ntasks:\n  run:\n    shell: echo seeded\n"
    )
    (staging_parent / "sentinel.txt").write_text("must stay outside staging")
    archive_path = tmp_path / "parent-root.zip"
    _write_zip(
        archive_path,
        {
            "../robot.yaml": "name: archive\ntasks:\n  run:\n    shell: echo archive\n",
            "../task.py": "print('archive')\n",
        },
    )

    success, message, imported_path = _api_robots._extract_zip_to_robots(
        archive_path, robot_name="imported"
    )

    assert success is False
    assert imported_path is None
    assert "root" in message.lower() or "path" in message.lower()
    assert not (robots_dir / "imported").exists()
    assert (staging_parent / "sentinel.txt").read_text() == "must stay outside staging"


@pytest.mark.parametrize(
    "member_name",
    [
        "../robot.yaml",
        "/robot.yaml",
        "C:/robot.yaml",
        r"robot\\robot.yaml",
    ],
)
def test_robot_zip_rejects_ambiguous_member_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, member_name: str
) -> None:
    from actions.server import _api_robots

    robots_dir = tmp_path / "robots"
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots_dir)
    archive_path = tmp_path / "unsafe.zip"
    _write_zip(
        archive_path,
        {
            member_name: "name: unsafe\ntasks:\n  run:\n    shell: echo no\n",
            "task.py": "print('no')\n",
        },
    )

    success, message, imported_path = _api_robots._extract_zip_to_robots(archive_path)

    assert success is False
    assert imported_path is None
    assert any(
        word in message.lower() for word in ("unsafe", "absolute", "separator", "drive")
    )
    assert not robots_dir.exists() or not any(robots_dir.iterdir())


def test_robot_zip_rejects_case_colliding_members_before_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    robots_dir = tmp_path / "robots"
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots_dir)
    archive_path = tmp_path / "duplicate.zip"
    members = _valid_robot_files()
    members["robot/ROBOT.yaml"] = "name: duplicate\ntasks:\n  run: {}\n"
    _write_zip(archive_path, members)

    success, message, imported_path = _api_robots._extract_zip_to_robots(archive_path)

    assert success is False
    assert imported_path is None
    assert "duplicate" in message.lower() or "collid" in message.lower()
    assert not robots_dir.exists() or not any(robots_dir.iterdir())


def test_robot_zip_rejects_case_colliding_directory_prefixes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    robots_dir = tmp_path / "robots"
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots_dir)
    archive_path = tmp_path / "duplicate-root.zip"
    _write_zip(
        archive_path,
        {
            "robot/robot.yaml": "name: first\ntasks:\n  run: {}\n",
            "ROBOT/task.py": "print('second')\n",
        },
    )

    success, message, imported_path = _api_robots._extract_zip_to_robots(archive_path)

    assert success is False
    assert imported_path is None
    assert "duplicate" in message.lower() or "collid" in message.lower()
    assert not robots_dir.exists() or not any(robots_dir.iterdir())


def test_robot_zip_rejects_link_entries_before_extraction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    robots_dir = tmp_path / "robots"
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots_dir)
    archive_path = tmp_path / "link.zip"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in _valid_robot_files().items():
            archive.writestr(name, content)
        link = zipfile.ZipInfo("robot/link")
        link.create_system = 3
        link.external_attr = stat.S_IFLNK << 16
        archive.writestr(link, "robot.yaml")
    archive_path.write_bytes(output.getvalue())

    success, message, imported_path = _api_robots._extract_zip_to_robots(archive_path)

    assert success is False
    assert imported_path is None
    assert "link" in message.lower() or "special" in message.lower()
    assert not robots_dir.exists() or not any(robots_dir.iterdir())


def test_robot_zip_enforces_actual_archive_input_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    archive_path = tmp_path / "too-large-input.zip"
    _write_zip(archive_path, _valid_robot_files())
    monkeypatch.setattr(
        _api_robots,
        "_MAX_ARCHIVE_INPUT_BYTES",
        archive_path.stat().st_size - 1,
        raising=False,
    )
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", tmp_path / "robots")

    success, message, imported_path = _api_robots._extract_zip_to_robots(archive_path)

    assert success is False
    assert imported_path is None
    assert "limit" in message.lower() or "large" in message.lower()


def test_robot_zip_enforces_entry_and_expansion_limits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    archive_path = tmp_path / "too-many-bytes.zip"
    members = _valid_robot_files()
    members["robot/repeated.txt"] = "A" * 256
    _write_zip(archive_path, members)
    monkeypatch.setattr(_api_robots, "_MAX_ARCHIVE_ENTRIES", 2, raising=False)
    monkeypatch.setattr(_api_robots, "_MAX_ARCHIVE_MEMBER_BYTES", 64, raising=False)
    monkeypatch.setattr(_api_robots, "_MAX_ARCHIVE_EXPANDED_BYTES", 64, raising=False)
    monkeypatch.setattr(_api_robots, "_MAX_ARCHIVE_EXPANSION_RATIO", 2.0, raising=False)
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", tmp_path / "robots")

    success, message, imported_path = _api_robots._extract_zip_to_robots(archive_path)

    assert success is False
    assert imported_path is None
    assert any(
        word in message.lower() for word in ("limit", "large", "expansion", "entries")
    )


@pytest.mark.parametrize(
    "members",
    [
        _valid_robot_files(),
        {
            "robot.yaml": "name: rootless\ntasks:\n  run:\n    shell: echo ok\n",
            "task.py": "print('ok')\n",
        },
    ],
)
def test_robot_zip_accepts_ordinary_and_rootless_valid_packages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, members: dict[str, str]
) -> None:
    from actions.server import _api_robots

    robots_dir = tmp_path / "robots"
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots_dir)
    archive_path = tmp_path / "valid.zip"
    _write_zip(archive_path, members)

    success, message, imported_path = _api_robots._extract_zip_to_robots(
        archive_path, robot_name="valid"
    )

    assert success is True, message
    assert imported_path == robots_dir / "valid"
    assert (imported_path / "robot.yaml").exists()


def test_robot_upload_is_read_in_bounded_chunks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", tmp_path / "robots")
    upload = _ChunkedUpload(_zip_bytes(_valid_robot_files()), chunk_size=5)

    response = asyncio.run(_api_robots.import_robot(file=upload))

    assert response.success is True, response.message
    assert upload.read_sizes
    assert all(0 < size <= 1024 * 1024 for size in upload.read_sizes)
    assert len(upload.read_sizes) > 1


def test_robot_upload_rejects_actual_bytes_above_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", tmp_path / "robots")
    monkeypatch.setattr(_api_robots, "_MAX_UPLOAD_BYTES", 16, raising=False)
    upload = _ChunkedUpload(_zip_bytes(_valid_robot_files()), chunk_size=5)

    response = asyncio.run(_api_robots.import_robot(file=upload))

    assert response.success is False
    assert "limit" in response.message.lower() or "large" in response.message.lower()
    assert not (tmp_path / "robots").exists()


def test_url_download_streams_and_validates_each_redirect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    _allow_test_download_host(monkeypatch)
    start = "https://downloads.example.test/start.zip"
    final = "https://downloads.example.test/final.zip"
    _FakeHTTPXClient.responses = {
        start: _FakeResponse(302, headers={"location": final}),
        final: _FakeResponse(
            200,
            headers={"content-type": "application/zip"},
            chunks=(b"PK", b"\x03\x04payload"),
        ),
    }
    monkeypatch.setattr(_api_robots.tempfile, "gettempdir", lambda: str(tmp_path))

    success, message, downloaded = asyncio.run(_api_robots._download_from_url(start))

    assert success is True, message
    assert downloaded is not None
    assert downloaded.read_bytes() == b"PK\x03\x04payload"
    assert _FakeHTTPXClient.instances[0].kwargs["follow_redirects"] is False
    assert _FakeHTTPXClient.instances[0].urls == [start, final]
    downloaded.unlink()


def test_url_download_rejects_private_destination_before_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    success, message, downloaded = asyncio.run(
        _api_robots._download_from_url("http://127.0.0.1/private.zip")
    )

    assert success is False
    assert downloaded is None
    assert (
        "url" in message.lower()
        or "host" in message.lower()
        or "private" in message.lower()
    )
    assert not _FakeHTTPXClient.instances


def test_url_download_preserves_valid_github_repository_normalization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    _allow_test_download_host(monkeypatch)
    source = "https://github.com/owner/repo"
    normalized = "https://github.com/owner/repo/archive/refs/heads/main.zip"
    _FakeHTTPXClient.responses = {
        normalized: _FakeResponse(
            200,
            headers={"content-type": "application/zip"},
            chunks=(b"PK", b"\x03\x04payload"),
        )
    }
    monkeypatch.setattr(_api_robots.tempfile, "gettempdir", lambda: str(tmp_path))

    success, message, downloaded = asyncio.run(_api_robots._download_from_url(source))

    assert success is True, message
    assert downloaded is not None
    assert _FakeHTTPXClient.instances[0].urls == [normalized]
    downloaded.unlink()


@pytest.mark.parametrize(
    "url",
    [
        "https://user:secret@github.com/owner/repo",
        "https://github.com/owner/repo#fragment",
    ],
)
def test_url_download_rejects_unsafe_original_github_url(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    _allow_test_download_host(monkeypatch)

    success, message, downloaded = asyncio.run(_api_robots._download_from_url(url))

    assert success is False
    assert downloaded is None
    assert not _FakeHTTPXClient.instances
    assert "url" in message.lower() or "credential" in message.lower()


@pytest.mark.parametrize(
    "url",
    [
        "https://user:secret@downloads.example.test/robot.zip",
        "https://downloads.example.test/robot.zip#fragment",
        "https://downloads.example.test:99999/robot.zip",
    ],
)
def test_url_download_rejects_ambiguous_or_credentialed_urls(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    _allow_test_download_host(monkeypatch)

    success, message, downloaded = asyncio.run(_api_robots._download_from_url(url))

    assert success is False
    assert downloaded is None
    assert "url" in message.lower() or "host" in message.lower()
    assert not _FakeHTTPXClient.instances


def test_url_download_rejects_redirect_to_private_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    _allow_test_download_host(monkeypatch)
    start = "https://downloads.example.test/start.zip"
    private = "http://127.0.0.1/private.zip"
    _FakeHTTPXClient.responses = {
        start: _FakeResponse(302, headers={"location": private}),
    }

    success, message, downloaded = asyncio.run(_api_robots._download_from_url(start))

    assert success is False
    assert downloaded is None
    assert (
        "url" in message.lower()
        or "host" in message.lower()
        or "private" in message.lower()
    )
    assert _FakeHTTPXClient.instances[0].urls == [start]


def test_url_download_rejects_non_zip_content_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    _allow_test_download_host(monkeypatch)
    url = "https://downloads.example.test/robot.zip"
    _FakeHTTPXClient.responses = {
        url: _FakeResponse(
            200,
            headers={"content-type": "text/html"},
            chunks=(b"not a zip",),
        )
    }

    success, message, downloaded = asyncio.run(_api_robots._download_from_url(url))

    assert success is False
    assert downloaded is None
    assert "zip" in message.lower()


def test_url_download_rejects_actual_stream_above_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    _allow_test_download_host(monkeypatch)
    url = "https://downloads.example.test/large.zip"
    _FakeHTTPXClient.responses = {
        url: _FakeResponse(
            200,
            headers={"content-type": "application/zip"},
            chunks=(b"1234", b"5678"),
        )
    }
    monkeypatch.setattr(_api_robots, "_MAX_DOWNLOAD_BYTES", 4, raising=False)

    success, message, downloaded = asyncio.run(_api_robots._download_from_url(url))

    assert success is False
    assert downloaded is None
    assert "limit" in message.lower() or "large" in message.lower()


def test_failed_robot_publication_leaves_no_partial_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    robots_dir = tmp_path / "robots"
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots_dir)
    archive_path = tmp_path / "publication.zip"
    _write_zip(archive_path, _valid_robot_files())

    def partial_copy(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *args,
        **kwargs,
    ):
        destination_path = Path(destination)
        destination_path.mkdir(parents=True)
        (destination_path / "partial.txt").write_text("partial")
        raise OSError("publication interrupted")

    monkeypatch.setattr(_api_robots.shutil, "copytree", partial_copy)

    success, message, imported_path = _api_robots._extract_zip_to_robots(
        archive_path, robot_name="atomic"
    )

    assert success is False
    assert imported_path is None
    assert "publication" in message.lower() or "interrupted" in message.lower()
    assert not robots_dir.exists() or not any(robots_dir.iterdir())
