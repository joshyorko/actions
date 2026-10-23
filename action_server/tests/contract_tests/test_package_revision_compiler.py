"""Contract tests for immutable package-revision compiler inputs."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

from actions.server.deployments import source_manifest
from actions.server.deployments.package_revision_compiler import (
    snapshot_source_entries,
    stage_source_snapshot,
)


def _entry(path: str, content: bytes) -> source_manifest.SuppliedSourceEntry:
    return source_manifest.SuppliedSourceEntry(path, "file", content, 0o644)


def test_source_snapshot_digest_is_order_independent_and_idempotent() -> None:
    entries = [
        _entry("action.py", b"def generated_action():\n    return 'synthetic'\n"),
        _entry("package.yaml", b"spec-version: v2\n"),
    ]

    first = snapshot_source_entries(
        entries, protected_input_names=["package.yaml"]
    )
    replay = snapshot_source_entries(
        reversed(entries), protected_input_names=["package.yaml"]
    )

    assert first.inventory.canonical_json == replay.inventory.canonical_json
    assert first.digest == replay.digest
    assert first.digest == (
        "sha256:" + hashlib.sha256(first.inventory.canonical_json).hexdigest()
    )
    assert [
        (file.path, file.mode, file.content) for file in first.files
    ] == [
        ("action.py", 0o644, b"def generated_action():\n    return 'synthetic'\n"),
        ("package.yaml", 0o644, b"spec-version: v2\n"),
    ]


def test_source_snapshot_digest_changes_when_selected_bytes_change() -> None:
    first = snapshot_source_entries(
        [_entry("action.py", b"def generated_action(): return 'one'\n")],
        protected_input_names=[],
    )
    changed = snapshot_source_entries(
        [_entry("action.py", b"def generated_action(): return 'two'\n")],
        protected_input_names=[],
    )

    assert first.digest != changed.digest


@pytest.mark.parametrize("path", ["../action.py", "/action.py", "nested\\action.py", "a//action.py"])
def test_source_snapshot_rejects_traversal_and_invalid_paths(path: str) -> None:
    with pytest.raises(ValueError):
        snapshot_source_entries(
            [_entry(path, b"def generated_action(): pass\n")],
            protected_input_names=[],
        )


def test_source_snapshot_requires_protected_inputs_to_be_selected() -> None:
    with pytest.raises(ValueError, match="protected input"):
        snapshot_source_entries(
            [_entry("action.py", b"def generated_action(): pass\n")],
            protected_input_names=["package.yaml"],
        )


def test_source_snapshot_bounds_protected_input_names() -> None:
    with pytest.raises(ValueError, match="protected input names exceed the entry limit"):
        snapshot_source_entries(
            [_entry("action.py", b"def generated_action(): pass\n")],
            protected_input_names=["action.py"] * 33,
        )


@pytest.mark.skipif(sys.platform != "linux", reason="confined staging requires Linux")
def test_staged_source_snapshot_preserves_exact_selected_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    action_bytes = b"def generated_action():\n    return 'synthetic'\n"
    package_bytes = b"spec-version: v2\n"
    (source / "action.py").write_bytes(action_bytes)
    (source / "package.yaml").write_bytes(package_bytes)

    destination = tmp_path / "staged"
    destination.mkdir(mode=0o700)
    destination.chmod(0o700)
    source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    destination_fd = os.open(destination, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        snapshot = stage_source_snapshot(
            source_fd,
            destination_fd,
            [_entry("action.py", action_bytes), _entry("package.yaml", package_bytes)],
            selected_file_names=["action.py", "package.yaml"],
            protected_input_names=["package.yaml"],
        )
    finally:
        os.close(source_fd)
        os.close(destination_fd)

    assert snapshot.digest.startswith("sha256:")
    assert (destination / "action.py").read_bytes() == action_bytes
    assert (destination / "package.yaml").read_bytes() == package_bytes


@pytest.mark.skipif(sys.platform != "linux", reason="confined staging requires Linux")
def test_staged_source_snapshot_rejects_bytes_that_differ_from_the_input(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "action.py").write_bytes(b"def generated_action(): return 'actual'\n")
    destination = tmp_path / "staged"
    destination.mkdir(mode=0o700)
    destination.chmod(0o700)
    source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    destination_fd = os.open(destination, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        with pytest.raises(ValueError, match="staged source"):
            stage_source_snapshot(
                source_fd,
                destination_fd,
                [_entry("action.py", b"def generated_action(): return 'expected'\n")],
                selected_file_names=["action.py"],
                protected_input_names=[],
            )
    finally:
        os.close(source_fd)
        os.close(destination_fd)
