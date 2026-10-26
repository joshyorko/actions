"""Compiler workspace bytes and archived modes across platform boundaries."""

import os
import stat
import zipfile
from io import BytesIO

import pytest

from actions.server.deployments import package_revision_compiler as compiler
from actions.server.deployments import source_manifest


def _snapshot():
    return compiler.snapshot_source_entries(
        [
            source_manifest.SuppliedSourceEntry("action.py", "file", b"pass\n", 0o755),
            source_manifest.SuppliedSourceEntry(
                "data.txt", "file", b"exact\x00bytes", 0o644
            ),
        ],
        protected_input_names=[],
    )


class _PlatformOS:
    """Change only compiler OS capabilities, never pathlib's global platform."""

    def __init__(self, name, fchmod=None, open_file=None):
        self.name = name
        self._fchmod = fchmod
        self._open_file = open_file or os.open

    def __getattr__(self, name):
        if name == "fchmod":
            if self.name == "nt":
                raise AttributeError(name)
            return self._fchmod
        if self.name == "nt" and name == "O_NOFOLLOW":
            raise AttributeError(name)
        if name == "open":
            return self._open_file
        return getattr(os, name)


def test_windows_materialization_preserves_exact_bytes_and_archive_modes(
    tmp_path, monkeypatch
):
    snapshot = _snapshot()
    expected_archive = compiler._deterministic_source_archive(snapshot)
    monkeypatch.setattr(compiler, "os", _PlatformOS("nt"))

    compiler._write_source_snapshot(snapshot, tmp_path)

    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == {
        item.path: item.content for item in snapshot.files
    }
    assert compiler._deterministic_source_archive(snapshot) == expected_archive
    with zipfile.ZipFile(BytesIO(expected_archive)) as archive:
        assert {
            info.filename: stat.S_IMODE(info.external_attr >> 16)
            for info in archive.infolist()
        } == {item.path: item.mode for item in snapshot.files}


@pytest.mark.parametrize("capability", [None, False])
def test_posix_materialization_requires_callable_chmod_before_creating_files(
    tmp_path, monkeypatch, capability
):
    monkeypatch.setattr(compiler, "os", _PlatformOS("posix", capability))
    with pytest.raises(RuntimeError, match="requires fchmod"):
        compiler._write_source_snapshot(_snapshot(), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_posix_chmod_error_propagates_and_owned_descriptor_closes(
    tmp_path, monkeypatch
):
    descriptors = []

    def tracked_open(*args, **kwargs):
        fd = os.open(*args, **kwargs)
        descriptors.append(fd)
        return fd

    def reject(_fd, _mode):
        raise PermissionError("synthetic permission application failure")

    monkeypatch.setattr(compiler, "os", _PlatformOS("posix", reject, tracked_open))
    with pytest.raises(PermissionError, match="synthetic permission"):
        compiler._write_source_snapshot(_snapshot(), tmp_path)
    assert len(descriptors) == 1
    with pytest.raises(OSError):
        os.fstat(descriptors[0])


@pytest.mark.skipif(os.name == "nt", reason="POSIX workspace mode contract")
def test_posix_workspace_modes_remain_exact(tmp_path):
    snapshot = _snapshot()
    compiler._write_source_snapshot(snapshot, tmp_path)
    for item in snapshot.files:
        assert stat.S_IMODE((tmp_path / item.path).stat().st_mode) == item.mode
