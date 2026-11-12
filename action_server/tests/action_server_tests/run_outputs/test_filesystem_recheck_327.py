"""Public read-boundary regressions for sealed output content after open."""

import os
import sys

import pytest

from actions.server.run_outputs.filesystem import CHUNK_BYTES, FilesystemOutputProvider

pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or not hasattr(os, "O_PATH"),
    reason="Linux descriptor provider",
)


@pytest.fixture
def provider(tmp_path):
    root = tmp_path / "objects"
    root.mkdir()
    fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        with FilesystemOutputProvider(fd) as storage:
            yield storage, root, fd
        os.fstat(fd)
    finally:
        os.close(fd)


def _mask_timestamp_observations(monkeypatch):
    """Simulate a filesystem whose identity tuple has coarse timestamps."""
    from actions.server.run_outputs import filesystem

    original_identity = filesystem._identity

    def stable_timestamps(info):
        return (*original_identity(info)[:-2], 0, 0)

    monkeypatch.setattr(filesystem, "_identity", stable_timestamps)


def _stage_payload(storage, payload):
    chunks = [
        payload[index : index + CHUNK_BYTES]
        for index in range(0, len(payload), CHUNK_BYTES)
    ]
    return storage.stage(chunks).receipt


def _overwrite_equal_size(path, original, offset, replacement):
    assert len(replacement) == 1
    assert 0 <= offset < len(original)
    changed = original[:offset] + replacement + original[offset + 1 :]
    assert len(changed) == len(original) and changed != original
    before = path.stat()
    path.chmod(0o600)
    path.write_bytes(changed)
    path.chmod(0o400)
    after = path.stat()
    assert (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_size,
    ) == (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_size,
    )
    return changed


def test_unchanged_content_supports_partial_cross_block_and_eof_reads(provider):
    storage, _, _ = provider
    payload = bytes(index % 251 for index in range(CHUNK_BYTES + 5))
    seal = _stage_payload(storage, payload)

    with storage.open(seal.object_ref, seal.digest, seal.size) as reader:
        parts = [
            reader.read(1),
            reader.read(17),
            reader.read(CHUNK_BYTES - 18),
            reader.read(1),
            reader.read(),
            reader.read(),
        ]

    assert b"".join(parts) == payload
    assert parts[-1] == b""


def test_same_size_same_identity_tamper_fails_before_first_partial_byte(
    provider, monkeypatch
):
    storage, root, _ = provider
    payload = b"hello"
    seal = _stage_payload(storage, payload)
    path = root / seal.object_ref
    _mask_timestamp_observations(monkeypatch)

    with storage.open(seal.object_ref, seal.digest, seal.size) as reader:
        changed = _overwrite_equal_size(path, payload, 0, b"X")
        assert changed == b"Xello"
        with pytest.raises(ValueError, match="changed"):
            reader.read(1)


def test_tamper_in_unread_block_preserves_prefix_then_rejects_changed_block(
    provider, monkeypatch
):
    storage, root, _ = provider
    payload = b"a" * CHUNK_BYTES + b"b" * CHUNK_BYTES
    seal = _stage_payload(storage, payload)
    path = root / seal.object_ref
    _mask_timestamp_observations(monkeypatch)

    with storage.open(seal.object_ref, seal.digest, seal.size) as reader:
        changed = _overwrite_equal_size(path, payload, CHUNK_BYTES, b"X")
        assert changed[:CHUNK_BYTES] == payload[:CHUNK_BYTES]
        assert changed[CHUNK_BYTES] == ord("X")
        assert reader.read(1) == b"a"
        assert reader.read(CHUNK_BYTES - 1) == b"a" * (CHUNK_BYTES - 1)
        with pytest.raises(ValueError, match="changed"):
            reader.read(1)


def test_same_block_tamper_after_partial_read_is_rechecked_fresh(provider, monkeypatch):
    storage, root, _ = provider
    payload = b"abcdef"
    seal = _stage_payload(storage, payload)
    path = root / seal.object_ref
    _mask_timestamp_observations(monkeypatch)

    with storage.open(seal.object_ref, seal.digest, seal.size) as reader:
        assert reader.read(1) == b"a"
        changed = _overwrite_equal_size(path, payload, 1, b"X")
        assert changed == b"aXcdef"
        with pytest.raises(ValueError, match="changed"):
            reader.read(1)


def test_failed_spanning_read_does_not_consume_its_unreturned_prefix(
    provider, monkeypatch
):
    storage, root, _ = provider
    payload = b"a" * CHUNK_BYTES + b"b" * CHUNK_BYTES
    seal = _stage_payload(storage, payload)
    path = root / seal.object_ref
    _mask_timestamp_observations(monkeypatch)
    with storage.open(seal.object_ref, seal.digest, seal.size) as reader:
        changed = _overwrite_equal_size(path, payload, CHUNK_BYTES, b"X")
        with pytest.raises(ValueError, match="changed"):
            reader.read(CHUNK_BYTES + 1)
        assert _overwrite_equal_size(path, changed, CHUNK_BYTES, b"b") == payload
        assert reader.read() == payload


def test_short_positioned_reads_preserve_verified_partial_results(
    provider, monkeypatch
):
    storage, _, _ = provider
    actual = storage._read_at

    def short_read(fd, size, offset):
        return actual(fd, min(size, 2), offset)

    monkeypatch.setattr(storage, "_read_at", short_read)
    seal = _stage_payload(storage, b"hello")
    with storage.open(seal.object_ref, seal.digest, seal.size) as reader:
        assert reader.read(1) == b"h"
        assert reader.read() == b"ello"
        assert reader.read() == b""


@pytest.mark.parametrize("missing", [False, True])
def test_positioned_read_capability_is_checked_before_fd_allocation(
    provider, monkeypatch, missing
):
    from actions.server.run_outputs import filesystem

    _, _, caller = provider
    if missing:
        monkeypatch.delattr(filesystem.os, "pread")
    else:
        monkeypatch.setattr(filesystem.os, "pread", None)
    before = len(os.listdir("/proc/self/fd"))
    with pytest.raises(RuntimeError, match="requires pread"):
        FilesystemOutputProvider(caller)
    assert len(os.listdir("/proc/self/fd")) == before
    os.fstat(caller)
