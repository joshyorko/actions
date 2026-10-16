import json
import multiprocessing
import sys
import time
from contextlib import contextmanager

import pytest

from actions.server import _artifact_storage
from actions.server._artifact_storage import (
    ArtifactStorageConfigurationError,
    create_artifact_storage,
)


def _binding_worker(root, run_id, key, started, read, paused, release, results):
    storage = create_artifact_storage("shared-filesystem", root)
    loads = json.loads
    dump = json.dump

    def observe_read(*args, **kwargs):
        read.set()
        return loads(*args, **kwargs)

    def pause_publication(*args, **kwargs):
        if paused is not None:
            paused.set()
            # A crash test must not terminate a process inside Event.wait():
            # that can strand the test's shared condition lock during cleanup.
            if release is None:
                while True:
                    time.sleep(0.05)
            assert release.wait(15), "Parent did not release manifest publisher"
        return dump(*args, **kwargs)

    _artifact_storage.json.loads = observe_read
    _artifact_storage.json.dump = pause_publication
    started.set()
    try:
        storage.bind_run(run_id, key)
    except ArtifactStorageConfigurationError:
        results.put("conflict")
    else:
        results.put("bound")


@contextmanager
def _writers(root, first_key, second_key, run_ids, *, terminate_first=False):
    ctx = multiprocessing.get_context("spawn")
    started = [ctx.Event(), ctx.Event()]
    read = [ctx.Event(), ctx.Event()]
    paused, release = ctx.Event(), ctx.Event()
    results = ctx.Queue()
    processes = [
        ctx.Process(
            target=_binding_worker,
            args=(
                root,
                run_ids[i],
                key,
                started[i],
                read[i],
                paused if i == 0 else None,
                None if i == 0 and terminate_first else release,
                results,
            ),
        )
        for i, key in enumerate((first_key, second_key))
    ]
    try:
        processes[0].start()
        assert paused.wait(15), "First writer never reached publication"
        processes[1].start()
        assert started[1].wait(15), "Second writer never attempted binding"
        yield processes, read[1], release, results
        for i, process in enumerate(processes):
            process.join(15)
            if i == 0 and terminate_first:
                assert process.exitcode is not None and process.exitcode != 0
            else:
                assert process.exitcode == 0
    finally:
        release.set()
        for process in processes:
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(15)
                process.close()
        results.close()
        results.join_thread()


def _seed_storage(root):
    storage = create_artifact_storage("shared-filesystem", root)
    for key in ("seed", "first", "second"):
        storage.create_run_artifacts_dir(key)
    storage.bind_run("seed", "seed")
    return storage


@pytest.mark.parametrize("collision", [False, True])
def test_manifest_transaction_serializes_processes(tmp_path, collision):
    storage = _seed_storage(tmp_path)
    run_ids = ("same", "same") if collision else ("one", "two")
    with _writers(tmp_path, "first", "second", run_ids) as (
        processes,
        second_read,
        release,
        results,
    ):
        # The second process must not read the old manifest during publication.
        assert not second_read.wait(0.5)
        release.set()
        outcomes = sorted(results.get(timeout=15) for _ in processes)
    assert storage.run_storage_key("seed") == "seed"
    assert storage.run_storage_key(run_ids[0]) == "first"
    if collision:
        assert outcomes == ["bound", "conflict"]
    else:
        assert outcomes == ["bound", "bound"]
        assert storage.run_storage_key("two") == "second"
    assert not list(tmp_path.glob(".bindings-*"))


def test_process_exit_releases_manifest_lock(tmp_path):
    storage = _seed_storage(tmp_path)
    original = (tmp_path / storage._MANIFEST).read_bytes()
    with _writers(
        tmp_path, "first", "second", ("one", "two"), terminate_first=True
    ) as (
        processes,
        second_read,
        release,
        results,
    ):
        assert not second_read.wait(0.5)
        processes[0].terminate()
        processes[0].join(15)
        assert processes[0].exitcode is not None
        # Validate the surviving writer after the kernel closes the dead owner.
        assert results.get(timeout=15) == "bound"
        processes[1].join(15)
        assert processes[1].exitcode == 0
    bindings = json.loads((tmp_path / storage._MANIFEST).read_text())
    assert bindings == {
        **json.loads(original),
        "two": {"key": "second", "metadata": {}},
    }


@pytest.mark.parametrize("failure", ["serialize", "replace"])
def test_failed_publication_preserves_manifest_and_releases_lock(
    tmp_path, monkeypatch, failure
):
    storage = _seed_storage(tmp_path)
    manifest = tmp_path / storage._MANIFEST
    original = manifest.read_bytes()
    with monkeypatch.context() as patch:
        if failure == "replace":

            def fail_replace(*args):
                raise OSError("publication failed")

            patch.setattr(_artifact_storage.os, "replace", fail_replace)
            metadata = {}
        else:
            metadata = {"unserializable": object()}
        with pytest.raises((OSError, TypeError)):
            storage.bind_run("failed", "first", metadata)
    assert manifest.read_bytes() == original
    assert not list(tmp_path.glob(".bindings-*"))
    with _writers(tmp_path, "first", "second", ("one", "two")) as (
        processes,
        second_read,
        release,
        results,
    ):
        release.set()
        assert [results.get(timeout=15) for _ in processes] == ["bound", "bound"]
    assert storage.run_storage_key("two") == "second"


def test_manifest_lock_rejects_symlink(tmp_path):
    storage = _seed_storage(tmp_path)
    lock = tmp_path / f"{storage._MANIFEST}.lock"
    lock.unlink(missing_ok=True)
    target = tmp_path / "unrelated"
    target.write_text("preserve me")
    try:
        lock.symlink_to(target)
    except OSError:
        pytest.skip("Creating symlinks requires platform permission")
    with pytest.raises(ArtifactStorageConfigurationError, match="symlink"):
        storage.bind_run("one", "first")
    assert target.read_text() == "preserve me"


def test_lock_open_failure_never_publishes_without_lock(tmp_path):
    storage = _seed_storage(tmp_path)
    manifest = tmp_path / storage._MANIFEST
    original = manifest.read_bytes()
    lock = tmp_path / f"{storage._MANIFEST}.lock"
    lock.unlink()
    lock.mkdir()
    with pytest.raises(OSError):
        storage.bind_run("one", "first")
    assert manifest.read_bytes() == original
    assert not list(tmp_path.glob(".bindings-*"))
    lock.rmdir()
    storage.bind_run("one", "first")
    assert storage.run_storage_key("one") == "first"


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows locking")
def test_windows_binding_does_not_import_fcntl(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "fcntl", None)
    storage = _seed_storage(tmp_path)
    assert storage.run_storage_key("seed") == "seed"
