import asyncio
import io
import os
import shutil
import socket
import stat
import sys
import types
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar, Self
from urllib.parse import urlparse

import pytest
from fastapi import UploadFile


def _zip_bytes(members: Mapping[str, bytes | str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return output.getvalue()


def _write_zip(path: Path, members: Mapping[str, bytes | str]) -> None:
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


class _ChunkedUpload(UploadFile):
    def __init__(self, payload: bytes, chunk_size: int = 3) -> None:
        super().__init__(io.BytesIO(payload), filename="robot.zip", size=len(payload))
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
        self.requests: list[tuple[str, dict[str, str], dict[str, str]]] = []
        self.__class__.instances.append(self)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def stream(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        extensions: dict[str, str] | None = None,
    ) -> _FakeResponse:
        assert method == "GET"
        self.requests.append((url, headers or {}, extensions or {}))
        original_url = (
            urlparse(url)
            ._replace(netloc=(headers or {}).get("Host", urlparse(url).netloc))
            .geturl()
        )
        self.urls.append(original_url)
        return self.__class__.responses[original_url]


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
    assert [client.urls for client in _FakeHTTPXClient.instances] == [[start], [final]]
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
        destination_path.mkdir(parents=True, exist_ok=True)
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


@pytest.mark.parametrize(
    "name",
    [
        "robot/task.py:payload",
        "robot/CON",
        "robot/aux.txt",
        "robot/NUL.log",
        "robot/COM1",
        "robot/LPT9.txt",
        "robot/file.",
        "robot/file ",
        "robot/nested./task.py",
    ],
)
def test_zip_rejects_windows_destination_aliases(name: str) -> None:
    from actions.server import _api_robots

    accepted, _, _ = _api_robots._validate_zip_members([zipfile.ZipInfo(name)])
    assert not accepted


def test_download_connection_uses_admitted_ip_and_preserves_tls_hostname(
    monkeypatch, tmp_path
):
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    _allow_test_download_host(monkeypatch)
    url = "https://rebind.example.test/robot.zip"
    _FakeHTTPXClient.responses = {url: _FakeResponse(200, chunks=(b"PKtest",))}
    success, message, path = asyncio.run(_api_robots._download_from_url(url))
    assert success, message
    assert path is not None
    path.unlink()
    client = _FakeHTTPXClient.instances[0]
    assert client.kwargs.get("trust_env") is False
    assert client.requests == [
        (
            "https://93.184.216.34/robot.zip",
            {"Host": "rebind.example.test"},
            {"sni_hostname": "rebind.example.test"},
        )
    ]


def test_redirect_hosts_sharing_ip_do_not_reuse_tls_or_cookies(monkeypatch):
    from actions.server import _api_robots

    _fake_httpx2(monkeypatch)
    _allow_test_download_host(monkeypatch)
    first = "https://first.example.test/robot.zip"
    second = "https://second.example.test/robot.zip"
    _FakeHTTPXClient.responses = {
        first: _FakeResponse(
            302, headers={"location": second, "set-cookie": "private=secret"}
        ),
        second: _FakeResponse(200, chunks=(b"PKtest",)),
    }
    success, message, path = asyncio.run(_api_robots._download_from_url(first))
    assert success, message
    assert path is not None
    path.unlink()
    assert len(_FakeHTTPXClient.instances) == 2
    assert [
        client.requests[0][2]["sni_hostname"] for client in _FakeHTTPXClient.instances
    ] == ["first.example.test", "second.example.test"]
    assert all(len(client.requests) == 1 for client in _FakeHTTPXClient.instances)


def test_real_http_transport_binds_ip_but_verifies_original_tls_identity(monkeypatch):
    """Instrument the real TCP/TLS boundary without sending a network request."""
    import ssl

    import httpcore2
    from httpcore2._backends.anyio import AnyIOBackend

    from actions.server import _api_robots

    admitted_hosts = []
    connection = {}

    def resolve(host, *args, **kwargs):
        admitted_hosts.append(host)
        address = "93.184.216.34" if len(admitted_hosts) <= 3 else "127.0.0.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]

    class TLSProbe:
        async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            connection["tls_hostname"] = server_hostname
            connection["check_hostname"] = ssl_context.check_hostname
            connection["verify_mode"] = ssl_context.verify_mode
            raise httpcore2.ConnectError("stop before real TLS or network traffic")

        async def aclose(self):
            pass

    async def connect(self, host, port, *args, **kwargs):
        connection["tcp_host"] = host
        connection["port"] = port
        return TLSProbe()

    monkeypatch.setattr(_api_robots.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(AnyIOBackend, "connect_tcp", connect)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    success, _, path = asyncio.run(
        _api_robots._download_from_url("https://rebind.example.test/robot.zip")
    )
    assert not success and path is None
    assert admitted_hosts == ["rebind.example.test"] * 3
    assert connection == {
        "tcp_host": "93.184.216.34",
        "port": 443,
        "tls_hostname": "rebind.example.test",
        "check_hostname": True,
        "verify_mode": ssl.CERT_REQUIRED,
    }


def test_pinning_preserves_signed_path_parameters_and_query():
    from actions.server import _api_robots

    url = "https://downloads.example.test:8443/robot.zip;signature=synthetic?version=1&opaque=a%2Fb"
    pinned, headers, extensions = _api_robots._pinned_download_request(
        url, "93.184.216.34"
    )
    assert (
        pinned
        == "https://93.184.216.34:8443/robot.zip;signature=synthetic?version=1&opaque=a%2Fb"
    )
    assert headers == {"Host": "downloads.example.test:8443"}
    assert extensions == {"sni_hostname": "downloads.example.test"}


def test_robot_publication_does_not_clean_unowned_initial_staging_collision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    package = tmp_path / "package"
    package.mkdir()
    (package / "robot.yaml").write_text("tasks:\n  run: {}\n")
    robots = tmp_path / "robots"
    robots.mkdir()
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots)
    mkdir = os.mkdir
    collisions: list[Path] = []

    def competing_mkdir(path, *args, **kwargs):
        path = Path(path)
        if path.parent == robots and ".staging-" in path.name and not collisions:
            mkdir(path)
            (path / "foreign.txt").write_text("synthetic foreign staging entry")
            collisions.append(path)
        return mkdir(path, *args, **kwargs)

    monkeypatch.setattr(os, "mkdir", competing_mkdir)
    with pytest.raises(FileExistsError):
        _api_robots._publish_robot_package(package, "synthetic", None)
    assert len(collisions) == 1
    assert (
        collisions[0] / "foreign.txt"
    ).read_text() == "synthetic foreign staging entry"


def test_robot_publication_revalidates_metadata_after_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    archive_path = tmp_path / "robot.zip"
    _write_zip(archive_path, _valid_robot_files())
    robots = tmp_path / "robots"
    robots.mkdir()
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots)
    copytree = shutil.copytree
    copy2 = shutil.copy2
    changed_during_copy: list[Path] = []

    def change_source_before_file_copy(source, destination, *, follow_symlinks=True):
        source = Path(source)
        if source.name == "robot.yaml":
            source.write_text("name: changed_during_copy\ntasks: {}\n")
            changed_during_copy.append(source)
        return copy2(source, destination, follow_symlinks=follow_symlinks)

    def copy_with_source_change(source, destination, *args, **kwargs):
        kwargs["copy_function"] = change_source_before_file_copy
        return copytree(source, destination, *args, **kwargs)

    monkeypatch.setattr(_api_robots.shutil, "copytree", copy_with_source_change)

    success, message, imported_path = _api_robots._extract_zip_to_robots(archive_path)

    assert changed_during_copy
    assert not success
    assert "No tasks defined" in message
    assert imported_path is None
    assert list(robots.iterdir()) == []


def test_robot_publication_uses_metadata_from_completed_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    archive_path = tmp_path / "robot.zip"
    _write_zip(archive_path, _valid_robot_files())
    robots = tmp_path / "robots"
    robots.mkdir()
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots)
    copytree = shutil.copytree
    copy2 = shutil.copy2
    rewritten_copy_metadata: list[Path] = []

    def copy_file_with_distinct_admitted_name(
        source, destination, *, follow_symlinks=True
    ):
        copied = copy2(source, destination, follow_symlinks=follow_symlinks)
        if Path(source).name == "robot.yaml":
            Path(destination).write_text(
                "name: admitted_copy\ntasks:\n  run:\n    shell: echo copied\n"
            )
            rewritten_copy_metadata.append(Path(destination))
        return copied

    def copy_with_distinct_metadata(source, destination, *args, **kwargs):
        kwargs["copy_function"] = copy_file_with_distinct_admitted_name
        return copytree(source, destination, *args, **kwargs)

    monkeypatch.setattr(_api_robots.shutil, "copytree", copy_with_distinct_metadata)

    success, message, imported_path = _api_robots._extract_zip_to_robots(archive_path)

    assert success
    assert rewritten_copy_metadata
    assert imported_path == robots / "admitted_copy"
    assert message == "Successfully imported robot 'admitted_copy'"
    assert "name: admitted_copy" in (imported_path / "robot.yaml").read_text()
    assert sorted(path.name for path in robots.iterdir()) == ["admitted_copy"]


def test_robot_publication_keeps_copytree_metadata_inside_private_container(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    package = tmp_path / "package"
    package.mkdir()
    (package / "robot.yaml").write_text("tasks:\n  run: {}\n")
    (package / "task.py").write_text("print('ok')\n")
    package.chmod(0o755)
    source_mode = stat.S_IMODE(package.stat().st_mode)
    robots = tmp_path / "robots"
    robots.mkdir()
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots)
    copytree = shutil.copytree
    copy2 = shutil.copy2
    observed_modes: list[tuple[int, int]] = []
    during_copy_modes: list[int] = []

    def inspect_copytree(source, destination, *args, **kwargs):
        destination = Path(destination)
        container = destination.parent
        assert container.parent == robots
        assert ".staging-" in container.name
        observed_modes.append((stat.S_IMODE(container.stat().st_mode), -1))

        def inspect_copy(source_file, destination_file, *, follow_symlinks=True):
            copied = copy2(
                source_file,
                destination_file,
                follow_symlinks=follow_symlinks,
            )
            during_copy_modes.append(stat.S_IMODE(container.stat().st_mode))
            return copied

        kwargs["copy_function"] = inspect_copy
        result = copytree(source, destination, *args, **kwargs)
        observed_modes[-1] = (
            observed_modes[-1][0],
            stat.S_IMODE(container.stat().st_mode),
        )
        if os.name != "nt":
            assert stat.S_IMODE(destination.stat().st_mode) == source_mode
        return result

    monkeypatch.setattr(_api_robots.shutil, "copytree", inspect_copytree)
    name, destination = _api_robots._publish_robot_package(package, "synthetic", None)

    assert name == "synthetic"
    assert destination == robots / name
    assert observed_modes[0][0] == observed_modes[0][1]
    assert during_copy_modes == [observed_modes[0][0], observed_modes[0][0]]
    if os.name != "nt":
        assert observed_modes == [(0o700, 0o700)]
        assert stat.S_IMODE(destination.stat().st_mode) == source_mode
    assert sorted(path.name for path in robots.iterdir()) == [name]


def test_robot_publication_removes_private_container_after_copy_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    package = tmp_path / "package"
    package.mkdir()
    (package / "robot.yaml").write_text("tasks:\n  run: {}\n")
    robots = tmp_path / "robots"
    robots.mkdir()
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots)
    containers: list[Path] = []

    def partial_copy_then_fail(source, destination, *args, **kwargs):
        destination = Path(destination)
        containers.append(destination.parent)
        (destination / "partial.txt").write_text("incomplete package")
        raise OSError("synthetic interrupted copy")

    monkeypatch.setattr(_api_robots.shutil, "copytree", partial_copy_then_fail)
    with pytest.raises(OSError, match="synthetic interrupted copy"):
        _api_robots._publish_robot_package(package, "synthetic", None)

    assert len(containers) == 1
    assert containers[0].parent == robots
    assert not containers[0].exists()
    assert list(robots.iterdir()) == []


def test_robot_publication_preserves_replaced_package_after_copy_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    package = tmp_path / "package"
    package.mkdir()
    (package / "robot.yaml").write_text("tasks:\n  run: {}\n")
    robots = tmp_path / "robots"
    robots.mkdir()
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots)
    replacements: list[tuple[Path, tuple[int, int], tuple[int, int], Path]] = []

    def replace_package_then_fail(source, destination, *args, **kwargs):
        destination = Path(destination)
        previous_stat = destination.lstat()
        previous_identity = (previous_stat.st_dev, previous_stat.st_ino)
        displaced = destination.with_name("displaced-package")
        destination.rename(displaced)
        destination.mkdir()
        replacement_stat = destination.lstat()
        replacement_identity = (replacement_stat.st_dev, replacement_stat.st_ino)
        sentinel = destination / "foreign.txt"
        sentinel.write_text("replacement payload must survive cleanup")
        replacements.append(
            (destination, previous_identity, replacement_identity, sentinel)
        )
        raise OSError("synthetic interrupted copy")

    monkeypatch.setattr(_api_robots.shutil, "copytree", replace_package_then_fail)
    with pytest.raises(OSError, match="synthetic interrupted copy"):
        _api_robots._publish_robot_package(package, "synthetic", None)

    assert len(replacements) == 1
    destination, previous_identity, replacement_identity, sentinel = replacements[0]
    assert previous_identity != replacement_identity
    assert destination.exists()
    assert sentinel.read_text() == "replacement payload must survive cleanup"
    assert (destination.parent / "displaced-package").exists()
    assert destination.parent.exists()
    assert list(robots.iterdir()) == [destination.parent]


def test_robot_publication_preserves_destination_created_after_last_precheck(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    package = tmp_path / "package"
    package.mkdir()
    (package / "robot.yaml").write_text("tasks:\n  run: {}\n")
    robots = tmp_path / "robots"
    robots.mkdir()
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots)
    competing = robots / "synthetic"
    lexists = os.path.lexists
    checks = 0
    identity = []

    def interleaved_lexists(path):
        nonlocal checks
        result = lexists(path)
        if Path(path) == competing:
            checks += 1
            if checks == 2:
                assert not result
                competing.mkdir()
                identity.append(competing.stat().st_ino)
        return result

    monkeypatch.setattr(os.path, "lexists", interleaved_lexists)
    name, destination = _api_robots._publish_robot_package(package, "synthetic", None)
    assert identity
    assert competing.stat().st_ino == identity[0]
    assert list(competing.iterdir()) == []
    assert destination != competing
    assert name.startswith("synthetic_")
    assert (destination / "robot.yaml").read_text() == "tasks:\n  run: {}\n"
    assert sorted(path.name for path in robots.iterdir()) == sorted([name, "synthetic"])


@pytest.mark.parametrize("entry_kind", ["directory", "file", "container"])
def test_robot_publication_relinquishes_cleanup_of_published_staging_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, entry_kind: str
) -> None:
    from actions.server import _api_robots, _directory_publication

    package = tmp_path / "package"
    package.mkdir()
    (package / "robot.yaml").write_text("tasks:\n  run:\n    shell: echo ok\n")
    (package / "payload.txt").write_text("complete package content")
    robots = tmp_path / "robots"
    robots.mkdir()
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots)
    rename = _directory_publication.rename_directory_no_replace
    foreign_entries: list[tuple[Path, int, Path]] = []
    container_replacements: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def publish_then_recreate_source(source: Path, destination: Path) -> None:
        # Another writer can reuse the old name once the real native rename
        # transfers our complete staging directory to the final destination.
        rename(source, destination)
        if entry_kind == "container":
            staging_root = source.parent
            original_stat = staging_root.lstat()
            original_identity = (original_stat.st_dev, original_stat.st_ino)
            staging_root.rename(tmp_path / "displaced-staging-container")
            staging_root.mkdir()
            replacement_stat = staging_root.lstat()
            container_replacements.append(
                (original_identity, (replacement_stat.st_dev, replacement_stat.st_ino))
            )
            source = source.parent
            sentinel = source / "foreign.txt"
        elif entry_kind == "directory":
            source.mkdir()
            sentinel = source / "foreign.txt"
        else:
            sentinel = source
        sentinel.write_text("foreign entry created after publication")
        foreign_entries.append((source, source.stat().st_ino, sentinel))

    monkeypatch.setattr(
        _directory_publication,
        "rename_directory_no_replace",
        publish_then_recreate_source,
    )
    name, destination = _api_robots._publish_robot_package(package, "synthetic", None)

    assert name == "synthetic"
    assert destination == robots / name
    assert (destination / "payload.txt").read_text() == "complete package content"
    assert (destination / "robot.yaml").read_text() == (
        package / "robot.yaml"
    ).read_text()
    assert len(foreign_entries) == 1
    foreign, identity, sentinel = foreign_entries[0]
    assert foreign.exists(), "Publication cleanup deleted a new owner's entry"
    assert foreign.stat().st_ino == identity
    assert sentinel.read_text() == "foreign entry created after publication"
    container = foreign if entry_kind == "container" else foreign.parent
    assert set(robots.iterdir()) == {destination, container}
    if entry_kind == "container":
        assert len(container_replacements) == 1
        assert container_replacements[0][0] != container_replacements[0][1]
