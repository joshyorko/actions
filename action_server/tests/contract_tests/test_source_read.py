"""Linux filesystem proofs for selected-file descriptor measurement."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from actions.server.deployments import source_manifest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux descriptor proof"
)


@pytest.fixture
def root_fd(tmp_path: Path):
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        yield fd
    finally:
        os.close(fd)


def _reader():
    from actions.server.deployments import source_read

    return source_read


def test_measured_files_match_supplied_policy_and_borrow_root_fd(tmp_path, root_fd):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_bytes(b"print('ok')")
    (tmp_path / "src" / "main.py").chmod(0o711)
    (tmp_path / "package.yaml").write_bytes(b"name: sample")
    (tmp_path / "package.yaml").chmod(0o640)

    measured = _reader().read_selected_files(
        root_fd, ["src/main.py", "package.yaml"], protected_input_names=["package.yaml"]
    )
    supplied = source_manifest.validate_proposed_inventory(
        [
            source_manifest.SuppliedSourceEntry(
                "package.yaml", "file", b"name: sample", 0o640
            ),
            source_manifest.SuppliedSourceEntry(
                "src/main.py", "file", b"print('ok')", 0o711
            ),
        ],
        protected_input_names=["package.yaml"],
    )
    assert measured.inventory == supplied
    assert {item.path for item in measured.files} == {"src/main.py", "package.yaml"}
    assert os.fstat(root_fd).st_ino == measured.root.inode


@pytest.mark.parametrize(
    "paths,protected",
    [
        (["CON.txt"], []),
        (["e\u0301"], []),
        (["../outside"], []),
        (["a", "A"], []),
        (["a"], ["missing"]),
    ],
)
def test_policy_rejection_precedes_any_content_read(
    tmp_path, root_fd, monkeypatch, paths, protected
):
    reader = _reader()
    (tmp_path / "a").write_bytes(b"ok")

    def forbidden_read(*args):
        raise AssertionError("content was read before policy rejection")

    monkeypatch.setattr(reader.os, "read", forbidden_read)
    with pytest.raises(ValueError):
        reader.read_selected_files(root_fd, paths, protected_input_names=protected)


@pytest.mark.parametrize(
    "kind", ["leaf_link", "parent_link", "hardlink", "fifo", "directory", "privileged"]
)
def test_unsafe_objects_are_not_read(tmp_path, root_fd, monkeypatch, kind):
    reader = _reader()
    outside = tmp_path.parent / f"outside-{tmp_path.name}"
    outside.mkdir()
    target = outside / "secret"
    target.write_bytes(b"must not read")
    selected = tmp_path / "selected"
    path = "selected"
    if kind == "leaf_link":
        selected.symlink_to(target)
    elif kind == "parent_link":
        selected.symlink_to(outside, target_is_directory=True)
        path = "selected/secret"
    elif kind == "hardlink":
        os.link(target, selected)
    elif kind == "fifo":
        os.mkfifo(selected)
    elif kind == "directory":
        selected.mkdir()
    else:
        selected.write_bytes(b"ok")
        selected.chmod(0o4755)

    def forbidden_read(*args):
        raise AssertionError("unsafe object reached content read")

    monkeypatch.setattr(reader.os, "read", forbidden_read)
    with pytest.raises((ValueError, OSError)):
        reader.read_selected_files(root_fd, [path], protected_input_names=[])
    assert target.read_bytes() == b"must not read"


@pytest.mark.parametrize(
    "mutation", ["bytes", "mode", "leaf_replace", "parent_replace", "hardlink_added"]
)
def test_changes_during_read_are_rejected(tmp_path, root_fd, monkeypatch, mutation):
    reader = _reader()
    parent = tmp_path / "src"
    parent.mkdir()
    leaf = parent / "input"
    leaf.write_bytes(b"original")
    real_read = os.read
    changed = False

    def mutate_read(fd, size):
        nonlocal changed
        chunk = real_read(fd, size)
        if not changed:
            changed = True
            if mutation == "bytes":
                leaf.write_bytes(b"modified")
            elif mutation == "mode":
                leaf.chmod(0o755)
            elif mutation == "leaf_replace":
                leaf.rename(parent / "old")
                leaf.write_bytes(b"original")
            elif mutation == "parent_replace":
                parent.rename(tmp_path / "old-src")
                parent.mkdir()
                leaf.write_bytes(b"original")
            else:
                os.link(leaf, parent / "alias")
        return chunk

    monkeypatch.setattr(reader.os, "read", mutate_read)
    with pytest.raises(ValueError, match="changed|binding"):
        reader.read_selected_files(root_fd, ["src/input"], protected_input_names=[])


def test_earlier_file_change_during_later_read_is_rejected(
    tmp_path, root_fd, monkeypatch
):
    reader = _reader()
    (tmp_path / "one").write_bytes(b"one")
    (tmp_path / "two").write_bytes(b"two")
    second_inode = (tmp_path / "two").stat().st_ino
    real_read = os.read
    changed = False

    def mutate_previous(fd, size):
        nonlocal changed
        chunk = real_read(fd, size)
        if not changed and os.fstat(fd).st_ino == second_inode:
            changed = True
            (tmp_path / "one").write_bytes(b"ONE")
        return chunk

    monkeypatch.setattr(reader.os, "read", mutate_previous)
    with pytest.raises(ValueError, match="changed|binding"):
        reader.read_selected_files(root_fd, ["one", "two"], protected_input_names=[])


@pytest.mark.parametrize("replacement", ["leaf", "parent"])
def test_replacement_during_open_is_rejected_before_content_read(
    tmp_path, root_fd, monkeypatch, replacement
):
    reader = _reader()
    parent = tmp_path / "src"
    parent.mkdir()
    leaf = parent / "input"
    leaf.write_bytes(b"original")
    real_open = os.open
    changed = False

    def replace_after_open(path, flags, *args, **kwargs):
        nonlocal changed
        fd = real_open(path, flags, *args, **kwargs)
        if not changed and path == ("input" if replacement == "leaf" else "src"):
            changed = True
            if replacement == "leaf":
                leaf.rename(parent / "old")
                leaf.write_bytes(b"replacement")
            else:
                parent.rename(tmp_path / "old-src")
                parent.mkdir()
                leaf.write_bytes(b"replacement")
        return fd

    def forbidden_read(*args):
        raise AssertionError("replacement reached content read")

    monkeypatch.setattr(reader.os, "open", replace_after_open)
    monkeypatch.setattr(
        reader.os, "supports_dir_fd", reader.os.supports_dir_fd | {replace_after_open}
    )
    monkeypatch.setattr(reader.os, "read", forbidden_read)
    with pytest.raises(ValueError, match="changed|binding"):
        reader.read_selected_files(root_fd, ["src/input"], protected_input_names=[])


def test_borrowed_root_object_is_authority_after_original_name_replacement(
    tmp_path, root_fd
):
    reader = _reader()
    (tmp_path / "input").write_bytes(b"selected")
    original_name = tmp_path
    tmp_path.rename(tmp_path.parent / f"moved-{tmp_path.name}")
    original_name.mkdir()
    (original_name / "input").write_bytes(b"replacement")

    measured = reader.read_selected_files(root_fd, ["input"], protected_input_names=[])
    expected = source_manifest.validate_proposed_inventory(
        [source_manifest.SuppliedSourceEntry("input", "file", b"selected", 0o644)],
        protected_input_names=[],
    )
    assert measured.inventory == expected
    assert measured.root.inode != original_name.stat().st_ino


def test_inventory_is_independent_of_verified_root_location(tmp_path, root_fd):
    reader = _reader()
    (tmp_path / "input").write_bytes(b"same")
    (tmp_path / "input").chmod(0o755)
    other = tmp_path / "other"
    other.mkdir()
    (other / "input").write_bytes(b"same")
    (other / "input").chmod(0o711)
    other_fd = os.open(other, os.O_RDONLY | os.O_DIRECTORY)
    try:
        first = reader.read_selected_files(
            root_fd, ["input"], protected_input_names=["input"]
        )
        second = reader.read_selected_files(
            other_fd, ["input"], protected_input_names=["input"]
        )
    finally:
        os.close(other_fd)
    assert first.inventory == second.inventory
    assert first.root != second.root


def test_read_calls_are_bounded_and_total_growth_is_rejected(
    tmp_path, root_fd, monkeypatch
):
    reader = _reader()
    (tmp_path / "one").write_bytes(b"12")
    (tmp_path / "two").write_bytes(b"3")
    second_inode = (tmp_path / "two").stat().st_ino
    monkeypatch.setattr(source_manifest, "MAX_TOTAL_BYTES", 3)
    monkeypatch.setattr(reader, "_READ_CHUNK_BYTES", 1)
    real_read = os.read
    requested = []
    changed = False

    def grow_second(fd, size):
        nonlocal changed
        requested.append(size)
        if not changed and os.fstat(fd).st_ino == second_inode:
            changed = True
            with (tmp_path / "two").open("ab") as stream:
                stream.write(b"4")
        return real_read(fd, size)

    monkeypatch.setattr(reader.os, "read", grow_second)
    with pytest.raises(ValueError, match="total byte"):
        reader.read_selected_files(root_fd, ["one", "two"], protected_input_names=[])
    assert max(requested) <= 2


@pytest.mark.parametrize(
    "failure", ["missing", "parent_link", "read_error", "bounds", "success"]
)
def test_owned_descriptors_close_on_all_exits(tmp_path, root_fd, monkeypatch, failure):
    reader = _reader()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "input").write_bytes(b"data")
    path = "src/input"
    if failure == "missing":
        path = "src/missing"
    elif failure == "parent_link":
        (tmp_path / "link").symlink_to(tmp_path / "src", target_is_directory=True)
        path = "link/input"
    elif failure == "read_error":

        def broken_read(*args):
            raise OSError("read failure")

        monkeypatch.setattr(reader.os, "read", broken_read)
    elif failure == "bounds":
        monkeypatch.setattr(source_manifest, "MAX_FILE_BYTES", 1)

    before = set(os.listdir("/proc/self/fd"))
    if failure == "success":
        reader.read_selected_files(root_fd, [path], protected_input_names=[])
    else:
        with pytest.raises((ValueError, OSError)):
            reader.read_selected_files(root_fd, [path], protected_input_names=[])
    assert set(os.listdir("/proc/self/fd")) == before
    os.fstat(root_fd)


def test_actual_read_budget_and_declared_size_bounds(tmp_path, root_fd, monkeypatch):
    reader = _reader()
    (tmp_path / "one").write_bytes(b"12")
    (tmp_path / "two").write_bytes(b"34")
    monkeypatch.setattr(source_manifest, "MAX_FILE_BYTES", 2)
    monkeypatch.setattr(source_manifest, "MAX_TOTAL_BYTES", 3)
    with pytest.raises(ValueError, match="total byte"):
        reader.read_selected_files(root_fd, ["one", "two"], protected_input_names=[])

    monkeypatch.setattr(source_manifest, "MAX_TOTAL_BYTES", 10)
    (tmp_path / "one").write_bytes(b"123")
    with pytest.raises(ValueError, match="file.*byte"):
        reader.read_selected_files(root_fd, ["one"], protected_input_names=[])


def test_actual_bytes_enforced_when_opened_file_grows(tmp_path, root_fd, monkeypatch):
    reader = _reader()
    (tmp_path / "one").write_bytes(b"12")
    monkeypatch.setattr(source_manifest, "MAX_FILE_BYTES", 2)
    real_read = os.read
    sizes = []

    def grow_read(fd, size):
        sizes.append(size)
        if len(sizes) == 1:
            with (tmp_path / "one").open("ab") as stream:
                stream.write(b"3")
        return real_read(fd, size)

    monkeypatch.setattr(reader.os, "read", grow_read)
    with pytest.raises(ValueError, match="file.*byte"):
        reader.read_selected_files(root_fd, ["one"], protected_input_names=[])
    assert sizes == [3]


def test_selected_count_bound_precedes_file_read(root_fd, monkeypatch):
    reader = _reader()
    monkeypatch.setattr(source_manifest, "MAX_ENTRIES", 1)
    with pytest.raises(ValueError, match="entry limit"):
        reader.read_selected_files(root_fd, ["one", "two"], protected_input_names=[])


def test_rejects_non_directory_root_descriptor(tmp_path):
    reader = _reader()
    (tmp_path / "input").write_bytes(b"x")
    fd = os.open(tmp_path / "input", os.O_RDONLY)
    try:
        with pytest.raises(ValueError, match="root.*directory"):
            reader.read_selected_files(fd, [], protected_input_names=[])
        os.fstat(fd)
    finally:
        os.close(fd)


@pytest.mark.parametrize(
    "feature", ["platform", "nofollow", "open_dir_fd", "stat_nofollow"]
)
def test_unsupported_features_fail_without_fallback(root_fd, monkeypatch, feature):
    reader = _reader()
    if feature == "platform":
        monkeypatch.setattr(reader.sys, "platform", "win32")
    elif feature == "nofollow":
        monkeypatch.delattr(reader.os, "O_NOFOLLOW")
    elif feature == "open_dir_fd":
        monkeypatch.setattr(
            reader.os, "supports_dir_fd", reader.os.supports_dir_fd - {reader.os.open}
        )
    else:
        monkeypatch.setattr(
            reader.os,
            "supports_follow_symlinks",
            reader.os.supports_follow_symlinks - {reader.os.stat},
        )
    with pytest.raises(NotImplementedError, match="Linux|no.follow|descriptor"):
        reader.read_selected_files(root_fd, [], protected_input_names=[])


@pytest.mark.parametrize("acquisition", ["existing_device", "replacement_device"])
def test_device_is_classified_before_any_readable_open(
    tmp_path, root_fd, monkeypatch, acquisition
):
    reader = _reader()
    (tmp_path / "input").write_bytes(b"regular")
    real_open = os.open
    device_root = real_open("/dev", os.O_RDONLY | os.O_DIRECTORY)
    requested = []

    def guard_device_open(path, flags, *args, **kwargs):
        if path in {"null", "input"}:
            requested.append(flags)
            assert flags & os.O_PATH, "device acquisition attempted a read-capable open"
            if acquisition == "replacement_device":
                # Model the leaf changing to an actual device at the open syscall.
                # The returned descriptor really pins /dev/null without driver open.
                return real_open("null", flags, dir_fd=device_root)
        return real_open(path, flags, *args, **kwargs)

    def forbidden_read(*args):
        raise AssertionError("device reached content read")

    monkeypatch.setattr(reader.os, "open", guard_device_open)
    monkeypatch.setattr(
        reader.os, "supports_dir_fd", reader.os.supports_dir_fd | {guard_device_open}
    )
    monkeypatch.setattr(reader.os, "read", forbidden_read)
    try:
        with pytest.raises(ValueError, match="regular file"):
            reader.read_selected_files(
                device_root if acquisition == "existing_device" else root_fd,
                ["null" if acquisition == "existing_device" else "input"],
                protected_input_names=[],
            )
    finally:
        os.close(device_root)
    assert len(requested) == 1


@pytest.mark.parametrize("failure", ["proc_directory", "proc_reopen", "wrong_object"])
def test_procfd_failures_do_not_read_or_leak_descriptors(
    tmp_path, root_fd, monkeypatch, failure
):
    reader = _reader()
    (tmp_path / "input").write_bytes(b"selected")
    (tmp_path / "other").write_bytes(b"other")
    real_open = os.open

    def fail_proc_open(path, flags, *args, **kwargs):
        if failure == "proc_directory" and path == "/proc/self/fd":
            raise FileNotFoundError("procfd unavailable")
        if isinstance(path, str) and path.isdecimal() and "dir_fd" in kwargs:
            if failure == "proc_reopen":
                raise FileNotFoundError("procfd reopening unavailable")
            if failure == "wrong_object":
                return real_open(tmp_path / "other", flags)
        return real_open(path, flags, *args, **kwargs)

    def forbidden_read(*args):
        raise AssertionError("failed procfd acquisition reached content read")

    monkeypatch.setattr(reader.os, "open", fail_proc_open)
    monkeypatch.setattr(
        reader.os, "supports_dir_fd", reader.os.supports_dir_fd | {fail_proc_open}
    )
    monkeypatch.setattr(reader.os, "read", forbidden_read)
    before = set(os.listdir("/proc/self/fd"))
    with pytest.raises(
        ValueError if failure == "wrong_object" else NotImplementedError
    ):
        reader.read_selected_files(root_fd, ["input"], protected_input_names=[])
    assert set(os.listdir("/proc/self/fd")) == before
    os.fstat(root_fd)


def test_missing_o_path_fails_without_fallback(root_fd, monkeypatch):
    reader = _reader()
    monkeypatch.delattr(reader.os, "O_PATH")
    with pytest.raises(NotImplementedError, match="Linux|descriptor"):
        reader.read_selected_files(root_fd, [], protected_input_names=[])


@pytest.mark.parametrize("replacement", ["regular", "device_link"])
def test_procfd_reopen_pins_original_leaf_and_rejects_replacement(
    tmp_path, root_fd, monkeypatch, replacement
):
    reader = _reader()
    leaf = tmp_path / "input"
    leaf.write_bytes(b"original")
    real_open = os.open
    changed = False

    def replace_before_proc_reopen(path, flags, *args, **kwargs):
        nonlocal changed
        if path == "input":
            assert flags & os.O_PATH
        if (
            not changed
            and isinstance(path, str)
            and path.isdecimal()
            and "dir_fd" in kwargs
        ):
            changed = True
            leaf.rename(tmp_path / "old")
            if replacement == "regular":
                leaf.write_bytes(b"replacement")
            else:
                leaf.symlink_to("/dev/null")
            fd = real_open(path, flags, *args, **kwargs)
            assert os.fstat(fd).st_ino == (tmp_path / "old").stat().st_ino
            return fd
        return real_open(path, flags, *args, **kwargs)

    def forbidden_read(*args):
        raise AssertionError("replaced source reached content read")

    monkeypatch.setattr(reader.os, "open", replace_before_proc_reopen)
    monkeypatch.setattr(
        reader.os,
        "supports_dir_fd",
        reader.os.supports_dir_fd | {replace_before_proc_reopen},
    )
    monkeypatch.setattr(reader.os, "read", forbidden_read)
    before = set(os.listdir("/proc/self/fd"))
    with pytest.raises(ValueError, match="changed|binding"):
        reader.read_selected_files(root_fd, ["input"], protected_input_names=[])
    assert changed
    assert set(os.listdir("/proc/self/fd")) == before
