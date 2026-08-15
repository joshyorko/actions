import multiprocessing

import pytest

from actions.server._artifact_storage import (
    ArtifactStorageConfigurationError,
    ArtifactStorageNotFoundError,
    create_artifact_storage,
)


def test_local_storage_creates_and_reads_run_artifacts(tmp_path):
    storage = create_artifact_storage("local", tmp_path)

    storage.create_run_artifacts_dir("run-a")
    storage.write_bytes("run-a", "nested/data.bin", b"binary")

    assert storage.list_files("run-a") == [("nested/data.bin", 6)]
    assert storage.read_bytes("run-a", "nested/data.bin") == b"binary"


def test_shared_storage_requires_a_root_and_is_selected_explicitly(tmp_path):
    with pytest.raises(ArtifactStorageConfigurationError):
        create_artifact_storage("shared-filesystem", None)

    storage = create_artifact_storage("shared-filesystem", tmp_path)
    storage.create_run_artifacts_dir("run-a")

    assert storage.root == tmp_path


def test_missing_reads_have_a_stable_not_found_error(tmp_path):
    storage = create_artifact_storage("local", tmp_path)
    storage.create_run_artifacts_dir("run-a")

    with pytest.raises(ArtifactStorageNotFoundError):
        storage.read_text("run-a", "missing.txt")


def test_run_storage_keys_are_isolated(tmp_path):
    storage = create_artifact_storage("local", tmp_path)
    storage.create_run_artifacts_dir("run-a")
    storage.create_run_artifacts_dir("run-b")
    storage.write_text("run-a", "result.txt", "a")

    with pytest.raises(ArtifactStorageNotFoundError):
        storage.read_text("run-b", "result.txt")


def _write_from_process(root, relative_key):
    storage = create_artifact_storage("shared-filesystem", root)
    storage.create_run_artifacts_dir(relative_key)
    storage.write_text(relative_key, "process.txt", "written by A")


def test_shared_filesystem_process_a_write_process_b_read(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    process = ctx.Process(target=_write_from_process, args=(tmp_path, "run-a"))
    process.start()
    process.join()
    assert process.exitcode == 0

    storage = create_artifact_storage("shared-filesystem", tmp_path)
    assert storage.read_text("run-a", "process.txt") == "written by A"
