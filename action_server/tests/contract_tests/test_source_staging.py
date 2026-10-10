"""Linux contract tests for confined selected-source staging."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

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


@pytest.fixture
def destination(tmp_path: Path):
    path = tmp_path / "staging"
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        yield path, fd
    finally:
        os.close(fd)


def _stager():
    from actions.server.deployments import source_staging

    return source_staging


def test_stages_exact_measured_bytes_with_portable_modes_and_borrowed_fds(
    tmp_path, root_fd, destination
):
    destination_path, destination_fd = destination
    source = tmp_path / "src"
    source.mkdir()
    (source / "main.py").write_bytes(b"print('ready')\n")
    (source / "main.py").chmod(0o751)
    (tmp_path / "package.yaml").write_bytes(b"name: staged\n")
    (tmp_path / "package.yaml").chmod(0o640)
    before_root = os.fstat(root_fd)
    before_destination = os.fstat(destination_fd)

    result = _stager().stage_selected_files(
        root_fd,
        destination_fd,
        ["src/main.py", "package.yaml"],
        protected_input_names=["package.yaml"],
    )

    assert result.inventory.canonical_json
    assert {entry.path: entry.mode for entry in result.inventory.entries} == {
        "package.yaml": 0o644,
        "src/main.py": 0o755,
    }
    assert (destination_path / "package.yaml").read_bytes() == b"name: staged\n"
    assert (destination_path / "package.yaml").stat().st_mode & 0o777 == 0o644
    assert (destination_path / "src" / "main.py").read_bytes() == b"print('ready')\n"
    assert (destination_path / "src" / "main.py").stat().st_mode & 0o777 == 0o755
    assert os.fstat(root_fd).st_ino == before_root.st_ino
    assert os.fstat(destination_fd).st_ino == before_destination.st_ino
    assert set(os.listdir(destination_fd)) == {"src", "package.yaml"}


def test_empty_selection_stages_empty_inventory_without_touching_destination(
    tmp_path, root_fd, destination
):
    destination_path, destination_fd = destination
    result = _stager().stage_selected_files(
        root_fd, destination_fd, [], protected_input_names=[]
    )
    assert result.inventory.entries == ()
    assert os.listdir(destination_fd) == []
    assert list(destination_path.iterdir()) == []


@pytest.mark.parametrize("missing", ["mkdir_dir_fd", "scandir_fd"])
def test_missing_staging_descriptor_feature_fails_closed_before_read(
    tmp_path, root_fd, destination, monkeypatch, missing
):
    stager = _stager()
    (tmp_path / "input").write_bytes(b"content")
    destination_path, destination_fd = destination

    def forbidden_read(*args):
        raise AssertionError("source bytes read before staging feature check")

    monkeypatch.setattr(stager.os, "read", forbidden_read)
    if missing == "mkdir_dir_fd":
        monkeypatch.setattr(
            stager.os,
            "supports_dir_fd",
            stager.os.supports_dir_fd - {stager.os.mkdir},
        )
    else:
        monkeypatch.setattr(
            stager.os,
            "supports_fd",
            stager.os.supports_fd - {stager.os.scandir},
        )
    with pytest.raises(NotImplementedError, match="descriptor-relative"):
        stager.stage_selected_files(
            root_fd, destination_fd, ["input"], protected_input_names=[]
        )
    assert list(destination_path.iterdir()) == []


@pytest.mark.parametrize(
    ("capability", "unavailable"),
    [
        ("geteuid", "missing"),
        ("geteuid", None),
        ("fchmod", "missing"),
        ("fchmod", None),
    ],
)
def test_missing_linux_callable_fails_before_read_or_staging(
    tmp_path, root_fd, destination, monkeypatch, capability, unavailable
):
    stager = _stager()
    destination_path, destination_fd = destination
    (tmp_path / "input").write_bytes(b"content")

    def forbidden_read(*args):
        raise AssertionError("source bytes read before capability validation")

    monkeypatch.setattr(stager.source_read.os, "read", forbidden_read)
    if unavailable == "missing":
        monkeypatch.delattr(stager.os, capability)
    else:
        monkeypatch.setattr(stager.os, capability, None)

    with pytest.raises(NotImplementedError, match="required"):
        stager.stage_selected_files(
            root_fd, destination_fd, ["input"], protected_input_names=[]
        )
    assert list(destination_path.iterdir()) == []


def test_initial_leaf_observation_failure_reports_unresolved_file(
    tmp_path, root_fd, destination, monkeypatch
):
    stager = _stager()
    destination_path, destination_fd = destination
    source = tmp_path / "nested"
    source.mkdir()
    (source / "input").write_bytes(b"content")
    original_error = OSError("injected leaf fstat failure")
    created_fds = []
    real_create_file = stager._create_file
    real_fstat = stager.os.fstat

    def capture_created_file(*args, **kwargs):
        fd = real_create_file(*args, **kwargs)
        created_fds.append(fd)
        return fd

    def fail_leaf_fstat(fd):
        if created_fds and fd == created_fds[0]:
            raise original_error
        return real_fstat(fd)

    monkeypatch.setattr(stager, "_create_file", capture_created_file)
    monkeypatch.setattr(stager.os, "fstat", fail_leaf_fstat)

    with pytest.raises(OSError) as caught:
        stager.stage_selected_files(
            root_fd, destination_fd, ["nested/input"], protected_input_names=[]
        )

    assert caught.value is original_error
    assert "nested/input" in " ".join(caught.value.__notes__)
    assert (destination_path / "nested" / "input").is_file()
    assert os.fstat(root_fd)
    assert os.fstat(destination_fd)
    for fd in created_fds:
        with pytest.raises(OSError):
            real_fstat(fd)


@pytest.mark.parametrize("destination_state", ["nonempty", "public", "not_directory"])
def test_rejects_invalid_destination_before_read_or_modification(
    tmp_path, root_fd, monkeypatch, destination_state
):
    reader = _stager().source_read
    (tmp_path / "input").write_bytes(b"content")
    path = tmp_path / "dest"
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    if destination_state == "nonempty":
        (path / "keep").write_bytes(b"preserve")
    elif destination_state == "public":
        path.chmod(0o755)
    elif destination_state == "not_directory":
        path.rmdir()
        path.write_bytes(b"keep")
    flags = os.O_RDONLY
    if destination_state != "not_directory":
        flags |= getattr(os, "O_DIRECTORY")
    destination_fd = os.open(path, flags)
    try:

        def forbidden_read(*args):
            raise AssertionError("source bytes read before destination admission")

        monkeypatch.setattr(reader.os, "read", forbidden_read)
        with pytest.raises((ValueError, NotADirectoryError)):
            _stager().stage_selected_files(
                root_fd, destination_fd, ["input"], protected_input_names=[]
            )
        assert path.is_file() if destination_state == "not_directory" else True
        if destination_state == "nonempty":
            assert (path / "keep").read_bytes() == b"preserve"
    finally:
        os.close(destination_fd)


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "directory"])
def test_unsafe_source_objects_are_rejected_without_stage_entries(
    tmp_path, root_fd, destination, kind
):
    destination_path, destination_fd = destination
    outside = tmp_path.parent / f"outside-stage-{tmp_path.name}"
    outside.mkdir()
    target = outside / "secret"
    target.write_bytes(b"private")
    selected = tmp_path / "selected"
    path = "selected"
    if kind == "symlink":
        selected.symlink_to(target)
    elif kind == "hardlink":
        os.link(target, selected)
    elif kind == "fifo":
        os.mkfifo(selected)
    else:
        selected.mkdir()

    with pytest.raises((ValueError, OSError)):
        _stager().stage_selected_files(
            root_fd, destination_fd, [path], protected_input_names=[]
        )
    assert os.listdir(destination_fd) == []
    assert target.read_bytes() == b"private"
    assert list(destination_path.iterdir()) == []


def test_source_replacement_after_measurement_is_rejected_and_cleaned(
    tmp_path, root_fd, destination, monkeypatch
):
    source_read = _stager().source_read
    destination_path, destination_fd = destination
    source = tmp_path / "input"
    source.write_bytes(b"original")
    real_opened_path = source_read._opened_path
    calls = 0

    @contextmanager
    def replace_before_stage(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            source.write_bytes(b"replacement")
        with real_opened_path(*args, **kwargs) as opened:
            yield opened

    monkeypatch.setattr(source_read, "_opened_path", replace_before_stage)
    with pytest.raises(ValueError, match="changed|binding"):
        _stager().stage_selected_files(
            root_fd, destination_fd, ["input"], protected_input_names=[]
        )
    assert list(destination_path.iterdir()) == []


def test_copy_failure_removes_only_task_created_entries(
    tmp_path, root_fd, destination, monkeypatch
):
    stager = _stager()
    destination_path, destination_fd = destination
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "input").write_bytes(b"content")
    real_write_all = stager._write_all
    raised = False

    def fail_after_partial_write(fd: int, data: bytes) -> None:
        nonlocal raised
        if not raised:
            raised = True
            os.write(fd, data[:2])
            raise OSError("injected write failure")
        real_write_all(fd, data)

    monkeypatch.setattr(stager, "_write_all", fail_after_partial_write)
    with pytest.raises(OSError, match="injected write failure"):
        stager.stage_selected_files(
            root_fd, destination_fd, ["src/input"], protected_input_names=[]
        )
    assert list(destination_path.iterdir()) == []
    assert os.listdir(destination_fd) == []
    assert os.fstat(root_fd).st_ino
    assert os.fstat(destination_fd).st_ino


def test_cleanup_preserves_unowned_entry_added_during_failure(
    tmp_path, root_fd, destination, monkeypatch
):
    stager = _stager()
    destination_path, destination_fd = destination
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "input").write_bytes(b"content")
    real_write_all = stager._write_all
    inserted = False

    def insert_foreign_then_fail(fd: int, data: bytes) -> None:
        nonlocal inserted
        if not inserted:
            inserted = True
            foreign = destination_path / "foreign"
            foreign.write_bytes(b"leave")
            raise OSError("injected write failure")
        real_write_all(fd, data)

    monkeypatch.setattr(stager, "_write_all", insert_foreign_then_fail)
    with pytest.raises(OSError, match="injected write failure"):
        stager.stage_selected_files(
            root_fd, destination_fd, ["src/input"], protected_input_names=[]
        )
    assert (destination_path / "foreign").read_bytes() == b"leave"
    assert not (destination_path / "src" / "input").exists()
    assert set(os.listdir(destination_fd)) == {"foreign"}


def test_source_growth_during_staging_is_rejected_and_cleaned(
    tmp_path, root_fd, destination, monkeypatch
):
    source_read = _stager().source_read
    destination_path, destination_fd = destination
    source = tmp_path / "input"
    source.write_bytes(b"original")
    real_read = os.read
    nonempty_reads = 0

    def grow_during_copy(fd: int, size: int) -> bytes:
        nonlocal nonempty_reads
        chunk = real_read(fd, size)
        if chunk and os.fstat(fd).st_ino == source.stat().st_ino:
            nonempty_reads += 1
        if nonempty_reads == 2:
            nonempty_reads += 1
            with source.open("ab") as output:
                output.write(b"-growth")
        return chunk

    monkeypatch.setattr(source_read.os, "read", grow_during_copy)
    with pytest.raises(ValueError, match="changed|size"):
        _stager().stage_selected_files(
            root_fd, destination_fd, ["input"], protected_input_names=[]
        )
    assert list(destination_path.iterdir()) == []


@pytest.mark.parametrize("failure_phase", ["identity", "open", "observe"])
def test_nested_directory_setup_failure_cleans_all_created_ancestors(
    tmp_path, root_fd, destination, monkeypatch, failure_phase
):
    stager = _stager()
    destination_path, destination_fd = destination
    source = tmp_path / "a" / "b"
    source.mkdir(parents=True)
    (source / "input").write_bytes(b"content")
    original_error = OSError(f"injected post-mkdir {failure_phase} failure")
    opened_directory_fds = []

    if failure_phase == "identity":
        real_stat = stager.os.stat
        real_open = stager.os.open

        def capture_directory_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            parent_fd = kwargs.get("dir_fd")
            if path in {"a", "b"} and parent_fd is not None:
                parent = os.readlink(f"/proc/self/fd/{parent_fd}")
                if parent == str(destination_path) or parent == str(
                    destination_path / "a"
                ):
                    opened_directory_fds.append(fd)
            return fd

        monkeypatch.setattr(stager.os, "open", capture_directory_open)
        monkeypatch.setattr(
            stager.os,
            "supports_dir_fd",
            stager.os.supports_dir_fd | {capture_directory_open},
        )

        def fail_identity(path, *args, **kwargs):
            parent_fd = kwargs.get("dir_fd")
            if path == "b" and parent_fd is not None:
                parent = os.readlink(f"/proc/self/fd/{parent_fd}")
                if parent == str(destination_path / "a"):
                    raise original_error
            return real_stat(path, *args, **kwargs)

        monkeypatch.setattr(stager.os, "stat", fail_identity)
        monkeypatch.setattr(
            stager.os, "supports_dir_fd", stager.os.supports_dir_fd | {fail_identity}
        )
        monkeypatch.setattr(
            stager.os,
            "supports_follow_symlinks",
            stager.os.supports_follow_symlinks | {fail_identity},
        )
    elif failure_phase == "open":
        real_open = stager.os.open

        def fail_open(path, flags, *args, **kwargs):
            if path == "b" and kwargs.get("dir_fd") is not None:
                parent = os.readlink(f"/proc/self/fd/{kwargs['dir_fd']}")
                if parent == str(destination_path / "a"):
                    raise original_error
            fd = real_open(path, flags, *args, **kwargs)
            if path == "a":
                opened_directory_fds.append(fd)
            return fd

        monkeypatch.setattr(stager.os, "open", fail_open)
        monkeypatch.setattr(
            stager.os, "supports_dir_fd", stager.os.supports_dir_fd | {fail_open}
        )
    else:
        real_fstat = stager.os.fstat
        real_open = stager.os.open

        def capture_directory_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            parent_fd = kwargs.get("dir_fd")
            if path in {"a", "b"} and parent_fd is not None:
                parent = os.readlink(f"/proc/self/fd/{parent_fd}")
                if parent == str(destination_path) or parent == str(
                    destination_path / "a"
                ):
                    opened_directory_fds.append(fd)
            return fd

        monkeypatch.setattr(stager.os, "open", capture_directory_open)
        monkeypatch.setattr(
            stager.os,
            "supports_dir_fd",
            stager.os.supports_dir_fd | {capture_directory_open},
        )

        def fail_fstat(fd):
            try:
                path = os.readlink(f"/proc/self/fd/{fd}")
            except OSError:
                path = ""
            if path == str(destination_path / "a" / "b"):
                raise original_error
            return real_fstat(fd)

        monkeypatch.setattr(stager.os, "fstat", fail_fstat)

    with pytest.raises(OSError) as caught:
        stager.stage_selected_files(
            root_fd, destination_fd, ["a/b/input"], protected_input_names=[]
        )
    assert caught.value is original_error
    assert os.fstat(root_fd)
    assert os.fstat(destination_fd)
    for fd in opened_directory_fds:
        with pytest.raises(OSError):
            os.fstat(fd)
    if failure_phase == "identity":
        assert "a/b" in " ".join(caught.value.__notes__)
        assert (destination_path / "a" / "b").is_dir()
    else:
        assert list(destination_path.iterdir()) == []


def test_staged_bytes_are_rechecked_and_mutation_cleans_owned_tree(
    tmp_path, root_fd, destination, monkeypatch
):
    stager = _stager()
    destination_path, destination_fd = destination
    (tmp_path / "input").write_bytes(b"original")
    real_read = os.read
    mutated = False

    def mutate_staged_read(fd: int, size: int) -> bytes:
        nonlocal mutated
        chunk = real_read(fd, size)
        current = os.fstat(fd)
        staged_path = destination_path / "input"
        if (
            not mutated
            and staged_path.exists()
            and current.st_ino == staged_path.stat().st_ino
        ):
            mutated = True
            staged_path.write_bytes(b"modified")
        return chunk

    monkeypatch.setattr(stager.os, "read", mutate_staged_read)
    with pytest.raises(ValueError, match="staged.*changed"):
        stager.stage_selected_files(
            root_fd, destination_fd, ["input"], protected_input_names=[]
        )
    assert mutated
    assert list(destination_path.iterdir()) == []


def test_actual_copy_bytes_stay_within_policy_bounds(
    tmp_path, root_fd, destination, monkeypatch
):
    stager = _stager()
    source_read = stager.source_read
    destination_path, destination_fd = destination
    source = tmp_path / "input"
    source.write_bytes(b"four")
    real_opened_path = source_read._opened_path
    calls = 0

    @contextmanager
    def grow_after_pinned_open(*args, **kwargs):
        nonlocal calls
        calls += 1
        with real_opened_path(*args, **kwargs) as opened:
            if calls == 2:
                source.write_bytes(b"more-than-four")
            yield opened

    monkeypatch.setattr(source_read, "_opened_path", grow_after_pinned_open)
    monkeypatch.setattr(stager.source_manifest, "MAX_FILE_BYTES", 4)
    monkeypatch.setattr(stager.source_manifest, "MAX_TOTAL_BYTES", 8)
    with pytest.raises(ValueError, match="byte limit|changed|size"):
        stager.stage_selected_files(
            root_fd, destination_fd, ["input"], protected_input_names=[]
        )
    assert list(destination_path.iterdir()) == []
