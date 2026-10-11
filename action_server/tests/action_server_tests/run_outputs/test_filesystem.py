"""Actual filesystem boundaries; no HTTP/path serving claims."""

import hashlib
import os

import pytest

from actions.server.run_outputs.filesystem import FilesystemOutputProvider

pytestmark = pytest.mark.skipif(
    not hasattr(os, "O_PATH"), reason="Linux descriptor provider"
)


@pytest.fixture
def provider(tmp_path):
    root = tmp_path / "objects"
    root.mkdir()
    fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        with FilesystemOutputProvider(fd) as storage:
            yield storage, root, fd
        os.fstat(fd)  # caller's borrowed descriptor still belongs to caller
    finally:
        os.close(fd)


def test_actual_bytes_seal_read_and_descriptor_ownership(provider):
    storage, root, caller = provider
    seal = storage.stage([b"hello", b" world"]).receipt
    obj, digest, size = seal.object_ref, seal.digest, seal.size
    assert digest == "sha256:" + hashlib.sha256(b"hello world").hexdigest()
    assert size == 11
    assert (root / obj).stat().st_mode & 0o7777 == 0o400
    with storage.open(obj, digest, size) as reader:
        assert reader.read(5) == b"hello"
        assert reader.read() == b" world"
        assert reader.read() == b""
    os.fstat(caller)


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "corrupt", "mode"])
def test_unsealed_or_replaced_objects_fail_closed(provider, kind):
    storage, root, caller = provider
    seal = storage.stage([b"hello"]).receipt
    obj, digest, size = seal.object_ref, seal.digest, seal.size
    path = root / obj
    if kind == "symlink":
        path.unlink()
        path.symlink_to("/dev/null")
    elif kind == "hardlink":
        os.link(path, root / "alias")
    elif kind == "fifo":
        path.unlink()
        os.mkfifo(path)
    elif kind == "corrupt":
        path.chmod(0o600)
        path.write_bytes(b"other")
        path.chmod(0o400)
    else:
        path.chmod(0o600)
    before = len(os.listdir("/proc/self/fd"))
    with pytest.raises(ValueError):
        with storage.open(obj, digest, size):
            pytest.fail("invalid object returned a reader")
    assert len(os.listdir("/proc/self/fd")) == before


def test_changed_bytes_during_open_stream_are_rejected(provider):
    storage, root, caller = provider
    seal = storage.stage([b"hello"]).receipt
    obj, digest, size = seal.object_ref, seal.digest, seal.size
    with storage.open(obj, digest, size) as reader:
        (root / obj).chmod(0o600)
        (root / obj).write_bytes(b"other")
        (root / obj).chmod(0o400)
        with pytest.raises(ValueError, match="changed"):
            reader.read()


def test_chunk_bound_write_failure_and_missing_procfs_cleanup(provider, monkeypatch):
    from actions.server.run_outputs import filesystem

    storage, root, caller = provider
    monkeypatch.setattr(filesystem, "CHUNK_BYTES", 3)
    with pytest.raises(ValueError):
        storage.stage([b"four"])
    assert not list(root.iterdir())
    before = len(os.listdir("/proc/self/fd"))
    original = os.open

    def missing(path, *args, **kwargs):
        if path == "/proc/self/fd":
            raise FileNotFoundError("procfd absent")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", missing)
    # supports_dir_fd describes the real syscall, retain it for this seam.
    monkeypatch.setattr(os, "supports_dir_fd", os.supports_dir_fd | {missing})
    with pytest.raises(FileNotFoundError):
        FilesystemOutputProvider(caller)
    assert len(os.listdir("/proc/self/fd")) == before
    os.fstat(caller)


def test_stage_measures_actual_written_bytes(provider, monkeypatch):
    storage, root, caller = provider
    original = os.write

    def corrupt(fd, value):
        return original(fd, b"x" * len(value))

    monkeypatch.setattr(os, "write", corrupt)
    with pytest.raises(ValueError, match="bytes changed"):
        storage.stage([b"hello"])
    assert not list(root.iterdir())


@pytest.mark.parametrize("missing", [True, False])
def test_required_fchmod_is_missing_or_noncallable_before_descriptor_allocation(
    provider, monkeypatch, missing
):
    storage, root, caller = provider
    before = len(os.listdir("/proc/self/fd"))
    if missing:
        monkeypatch.delattr(os, "fchmod")
    else:
        monkeypatch.setattr(os, "fchmod", None)
    with pytest.raises(RuntimeError, match="requires fchmod"):
        FilesystemOutputProvider(caller)
    assert len(os.listdir("/proc/self/fd")) == before
    os.fstat(caller)


def test_device_substitution_is_pinned_without_read_capable_device_open(
    provider, monkeypatch
):
    storage, root, caller = provider
    seal = storage.stage([b"hello"]).receipt
    obj, digest, size = seal.object_ref, seal.digest, seal.size
    original = os.open
    device_flags = []

    def substitute(path, flags, *args, **kwargs):
        if path == obj:
            device_flags.append(flags)
            return original("/dev/null", flags)
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", substitute)
    before = len(os.listdir("/proc/self/fd"))
    with pytest.raises(ValueError, match="sealed regular"):
        with storage.open(obj, digest, size):
            pytest.fail("device returned a reader")
    assert len(device_flags) == 1
    assert device_flags[0] & getattr(os, "O_PATH")
    assert len(os.listdir("/proc/self/fd")) == before


def test_discard_measured_owned_seal_is_idempotent_and_closes_descriptors(provider):
    storage, root, caller = provider
    staged = storage.stage([b"body"])
    before = len(os.listdir("/proc/self/fd"))
    storage.discard(staged)
    storage.discard(staged)
    assert not list(root.iterdir())
    assert len(os.listdir("/proc/self/fd")) == before
    os.fstat(caller)


@pytest.mark.parametrize("kind", ["unowned", "replacement", "corrupt"])
def test_discard_never_deletes_unowned_replaced_or_corrupt_seal(provider, kind):
    storage, root, caller = provider
    staged = storage.stage([b"body"])
    path = root / staged.receipt.object_ref
    before = len(os.listdir("/proc/self/fd"))
    if kind == "unowned":
        with FilesystemOutputProvider(caller) as other:
            with pytest.raises(ValueError, match="belong"):
                other.discard(staged)
    else:
        if kind == "replacement":
            replacement = root / "replacement"
            replacement.write_bytes(b"body")
            replacement.chmod(0o400)
            os.replace(replacement, path)
        else:
            path.chmod(0o600)
            path.write_bytes(b"other")
            path.chmod(0o400)
        with pytest.raises(ValueError):
            storage.discard(staged)
    assert path.exists()
    assert len(os.listdir("/proc/self/fd")) == before
    os.fstat(caller)
