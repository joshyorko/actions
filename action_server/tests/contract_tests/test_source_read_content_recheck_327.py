"""Content rechecks must catch writes with unchanged observed metadata."""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from actions.server.deployments import source_manifest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux descriptor proof"
)


@pytest.fixture
def root_fd(tmp_path: Path):
    fd = os.open(tmp_path, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        yield fd
    finally:
        os.close(fd)


def _reader():
    from actions.server.deployments import source_read

    return source_read


def _hold_observed_timestamps(monkeypatch, reader):
    """Keep real identity observations while removing clock granularity."""
    observe = reader._observation

    def observe_without_timestamps(value):
        return replace(observe(value), mtime_ns=0, ctime_ns=0)

    monkeypatch.setattr(reader, "_observation", observe_without_timestamps)


def _inventory(*entries):
    return source_manifest.validate_proposed_inventory(
        [
            source_manifest.SuppliedSourceEntry(name, "file", content, 0o644)
            for name, content in entries
        ],
        protected_input_names=[],
    )


def _assert_rejected_or_expose_stale_result(
    call, expected_inventory, changed_path, expected_live_bytes
):
    try:
        call()
    except ValueError as error:
        assert (
            "changed" in str(error)
            or "binding" in str(error)
            or "content" in str(error)
        )
    else:
        measured = call.measured
        assert measured.inventory == expected_inventory
        assert changed_path.read_bytes() == expected_live_bytes
        pytest.fail("reader accepted a changed file and returned its stale inventory")


def test_same_file_same_size_write_is_rejected_with_unchanged_observations(
    tmp_path, root_fd, monkeypatch
):
    reader = _reader()
    _hold_observed_timestamps(monkeypatch, reader)
    parent = tmp_path / "src"
    parent.mkdir()
    leaf = parent / "input"
    leaf.write_bytes(b"original")
    expected = _inventory(("src/input", b"original"))
    real_read = os.read
    changed = False

    def overwrite_after_read(fd, size):
        nonlocal changed
        chunk = real_read(fd, size)
        if not changed:
            changed = True
            leaf.write_bytes(b"modified")
        return chunk

    monkeypatch.setattr(reader.os, "read", overwrite_after_read)

    def measure():
        measure.measured = reader.read_selected_files(
            root_fd, ["src/input"], protected_input_names=[]
        )

    _assert_rejected_or_expose_stale_result(measure, expected, leaf, b"modified")
    assert changed
    assert leaf.read_bytes() == b"modified"


def test_earlier_file_same_size_write_is_rejected_after_later_read(
    tmp_path, root_fd, monkeypatch
):
    reader = _reader()
    _hold_observed_timestamps(monkeypatch, reader)
    first = tmp_path / "one"
    second = tmp_path / "two"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    second_inode = second.stat().st_ino
    expected = _inventory(("one", b"one"), ("two", b"two"))
    real_read = os.read
    changed = False

    def overwrite_first_during_second_read(fd, size):
        nonlocal changed
        chunk = real_read(fd, size)
        if not changed and os.fstat(fd).st_ino == second_inode:
            changed = True
            first.write_bytes(b"ONE")
        return chunk

    monkeypatch.setattr(reader.os, "read", overwrite_first_during_second_read)

    def measure():
        measure.measured = reader.read_selected_files(
            root_fd, ["one", "two"], protected_input_names=[]
        )

    _assert_rejected_or_expose_stale_result(measure, expected, first, b"ONE")
    assert changed
    assert first.read_bytes() == b"ONE"


def test_unchanged_source_passes_content_recheck_with_exact_inventory(
    tmp_path, root_fd, monkeypatch
):
    reader = _reader()
    _hold_observed_timestamps(monkeypatch, reader)
    (tmp_path / "one").write_bytes(b"one")
    (tmp_path / "two").write_bytes(b"two")

    measured = reader.read_selected_files(
        root_fd, ["one", "two"], protected_input_names=[]
    )

    assert measured.inventory == _inventory(("one", b"one"), ("two", b"two"))
    assert [item.path for item in measured.files] == ["one", "two"]
