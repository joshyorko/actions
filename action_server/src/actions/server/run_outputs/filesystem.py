"""Linux-only, trusted service-owned output objects opened by owned descriptors.

Requires trusted kernel procfs. No pathname/HTTP serving or hostile-tree snapshot
claim; the configured root is control-plane authority, never a package argument.
"""

from __future__ import annotations

import hashlib
import os
import stat
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Callable, cast
from uuid import uuid4

from actions.server.run_outputs.types import canonical_uuid

MAX_OUTPUT_BYTES = 64 * 1024 * 1024
CHUNK_BYTES = 64 * 1024


def _flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int):
        raise RuntimeError("Linux output provider requires " + name)
    return value


def _fchmod() -> Callable[[int, int], None]:
    value = getattr(os, "fchmod", None)
    if not callable(value):
        raise RuntimeError("Linux output provider requires fchmod")
    return cast(Callable[[int, int], None], value)


def _identity(info: os.stat_result) -> tuple:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _regular(info: os.stat_result, expected_size: int) -> None:
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) != 0o400
        or info.st_size != expected_size
        or not 0 <= info.st_size <= MAX_OUTPUT_BYTES
    ):
        raise ValueError("output object is not a sealed regular bounded file")


class _Reader:
    def __init__(self, fd: int, identity: tuple, size: int):
        self.fd = fd
        self.identity = identity
        self.remaining = size
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if self.closed:
            raise ValueError("closed output reader")
        if not isinstance(size, int) or isinstance(size, bool) or size < -1:
            raise ValueError("invalid read size")
        amount = self.remaining if size == -1 else min(size, self.remaining)
        parts = []
        while amount:
            chunk = os.read(self.fd, min(amount, CHUNK_BYTES))
            if not chunk or _identity(os.fstat(self.fd)) != self.identity:
                raise ValueError("sealed output changed during read")
            parts.append(chunk)
            self.remaining -= len(chunk)
            amount -= len(chunk)
        if _identity(os.fstat(self.fd)) != self.identity:
            raise ValueError("sealed output changed during read")
        return b"".join(parts)


class FilesystemOutputProvider:
    _nofollow: int
    _directory: int
    _cloexec: int
    _path: int
    _nonblock: int
    _root: int
    _proc: int
    _closed: bool
    _chmod: Callable[[int, int], None]

    def __init__(self, verified_root_fd: int):
        if sys.platform != "linux":
            raise RuntimeError("filesystem output provider is Linux-only")
        self._chmod = _fchmod()
        self._nofollow = _flag("O_NOFOLLOW")
        self._directory = _flag("O_DIRECTORY")
        self._cloexec = _flag("O_CLOEXEC")
        self._path = _flag("O_PATH")
        self._nonblock = _flag("O_NONBLOCK")
        if os.open not in os.supports_dir_fd:
            raise RuntimeError("output provider requires open dir_fd support")
        if not stat.S_ISDIR(os.fstat(verified_root_fd).st_mode):
            raise ValueError("verified root descriptor must be a directory")
        self._root = os.dup(verified_root_fd)
        try:
            self._proc = os.open(
                "/proc/self/fd", os.O_RDONLY | self._directory | self._cloexec
            )
        except BaseException:
            os.close(self._root)
            raise
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if not self._closed:
            os.close(self._proc)
            os.close(self._root)
            self._closed = True

    def stage(self, chunks: Iterable[bytes]) -> tuple[str, str, int]:
        if self._closed:
            raise ValueError("closed output provider")
        object_ref = str(uuid4())
        fd = os.open(
            object_ref,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | self._nofollow | self._cloexec,
            0o600,
            dir_fd=self._root,
        )
        digest = hashlib.sha256()
        size = 0
        complete = False
        try:
            for chunk in chunks:
                if (
                    not isinstance(chunk, bytes)
                    or len(chunk) > CHUNK_BYTES
                    or len(chunk) > MAX_OUTPUT_BYTES - size
                ):
                    raise ValueError("output byte/chunk bound exceeded")
                view = memoryview(chunk)
                while view:
                    count = os.write(fd, view)
                    if count <= 0:
                        raise OSError("output write made no progress")
                    view = view[count:]
                digest.update(chunk)
                size += len(chunk)
            os.fsync(fd)
            self._chmod(fd, 0o400)
            os.fsync(fd)
            _regular(os.fstat(fd), size)
            sealed_identity = _identity(os.fstat(fd))
            os.lseek(fd, 0, os.SEEK_SET)
            measured = hashlib.sha256()
            remaining = size
            while remaining:
                actual = os.read(fd, min(remaining, CHUNK_BYTES))
                if not actual:
                    raise ValueError("staged output truncated")
                measured.update(actual)
                remaining -= len(actual)
            if (
                os.read(fd, 1)
                or measured.digest() != digest.digest()
                or _identity(os.fstat(fd)) != sealed_identity
            ):
                raise ValueError("staged output bytes changed before seal")
            observed = os.stat(object_ref, dir_fd=self._root, follow_symlinks=False)
            if _identity(observed) != _identity(os.fstat(fd)):
                raise ValueError("output object name changed during stage")
            os.fsync(self._root)
            complete = True
            return object_ref, "sha256:" + digest.hexdigest(), size
        finally:
            os.close(fd)
            if not complete:
                try:
                    os.unlink(object_ref, dir_fd=self._root)
                except FileNotFoundError:
                    pass

    @contextmanager
    def open(self, object_ref: str, digest: str, size: int) -> Iterator[_Reader]:
        canonical_uuid(object_ref)
        if (
            self._closed
            or not isinstance(size, int)
            or isinstance(size, bool)
            or not 0 <= size <= MAX_OUTPUT_BYTES
        ):
            raise ValueError("invalid bounded output object")
        pinned = os.open(
            object_ref, self._path | self._nofollow | self._cloexec, dir_fd=self._root
        )
        reader_fd = None
        reader = None
        try:
            before = os.fstat(pinned)
            _regular(before, size)
            reader_fd = os.open(
                str(pinned),
                os.O_RDONLY | self._nonblock | self._cloexec,
                dir_fd=self._proc,
            )
            identity = _identity(before)
            if _identity(os.fstat(reader_fd)) != identity:
                raise ValueError("output descriptor binding changed")
            measured = hashlib.sha256()
            remaining = size
            while remaining:
                chunk = os.read(reader_fd, min(remaining, CHUNK_BYTES))
                if not chunk:
                    raise ValueError("truncated sealed output")
                measured.update(chunk)
                remaining -= len(chunk)
            if (
                os.read(reader_fd, 1)
                or "sha256:" + measured.hexdigest() != digest
                or _identity(os.fstat(reader_fd)) != identity
                or _identity(
                    os.stat(object_ref, dir_fd=self._root, follow_symlinks=False)
                )
                != identity
            ):
                raise ValueError("sealed output identity/content changed")
            os.lseek(reader_fd, 0, os.SEEK_SET)
            reader = _Reader(reader_fd, identity, size)
            yield reader
        finally:
            if reader is not None:
                reader.closed = True
            if reader_fd is not None:
                os.close(reader_fd)
            os.close(pinned)
