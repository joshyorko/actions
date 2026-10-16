import json
import logging
import os
import socket
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def artifact_case(tmp_path):
    from actions.server._artifact_storage import create_artifact_storage

    package = tmp_path / "robot"
    package.mkdir()
    config = package / "robot.yaml"
    config.write_text("tasks: {}\n", encoding="utf-8")
    root = tmp_path / "artifacts"
    root.mkdir()
    storage = create_artifact_storage("local", root)
    key = "runs/run-current"
    storage.create_run_artifacts_dir(key)
    return package, config, storage, key


def _collector():
    from actions.server import _robot_artifacts

    return _robot_artifacts


def _put(root, name, content=b"payload"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _collect(case):
    package, config, storage, key = case
    _collector().collect_robot_artifacts(package, config, storage, key)


def _assert_rejected(case):
    module = _collector()
    with pytest.raises(module.RobotArtifactError):
        _collect(case)


def test_collects_default_output_recursively_without_changing_workload_names(
    artifact_case,
):
    package, _config, storage, key = artifact_case
    expected = {
        "report.json": b'{"status":"passed"}\n',
        "results.csv": b"name,value\nexample,42\n",
        "nested/image.png": b"\x89PNG\r\n\x1a\n\x00\xff",
        "nested/empty.bin": b"",
        "log.html": b"<html>robot log</html>",
        "output.xml": b"<robot/>",
        "report.html": b"<html>report</html>",
        "output.robolog": b"V 0.0.2\n",
        "output_1.robolog": b"continuation\n",
    }
    for name, content in expected.items():
        _put(package / "output", name, content)

    _collect(artifact_case)

    assert storage.list_files(key) == sorted(
        (name, len(content)) for name, content in expected.items()
    )
    for name, content in expected.items():
        assert storage.read_bytes(key, name) == content


@pytest.mark.parametrize("config_name", ["robot.yaml", "package.yaml"])
def test_collects_configured_artifacts_directory(artifact_case, config_name):
    package, old_config, storage, key = artifact_case
    config = package / config_name
    if config != old_config:
        old_config.unlink()
    config.write_text("tasks: {}\nartifactsDir: results/custom\n", encoding="utf-8")
    _put(package / "results/custom", "report.json", b"configured")
    _put(package / "output", "stale.txt", b"wrong directory")

    _collect((package, config, storage, key))

    assert storage.list_files(key) == [("report.json", 10)]
    assert storage.read_bytes(key, "report.json") == b"configured"


def test_missing_output_is_an_empty_snapshot(artifact_case):
    _collect(artifact_case)
    assert artifact_case[2].list_files(artifact_case[3]) == []


def test_rejects_output_root_that_is_a_regular_file(artifact_case):
    _put(artifact_case[0], "output")
    _assert_rejected(artifact_case)


@pytest.mark.parametrize("status", ["passed", "failed"])
def test_collects_success_and_failure_payloads_unchanged(artifact_case, status):
    package, _config, storage, key = artifact_case
    payload = json.dumps({"status": status, "message": "task result"}).encode()
    _put(package / "output", "report.json", payload)

    _collect(artifact_case)

    assert storage.read_bytes(key, "report.json") == payload


def test_completed_snapshot_survives_source_changes_and_removal(artifact_case):
    package, config, storage, first_key = artifact_case
    report = _put(package / "output", "report.json", b"first run")
    _collect(artifact_case)
    report.write_bytes(b"second run")
    second_key = "runs/run-second"
    storage.create_run_artifacts_dir(second_key)
    _collect((package, config, storage, second_key))
    report.unlink()

    assert storage.read_bytes(first_key, "report.json") == b"first run"
    assert storage.read_bytes(second_key, "report.json") == b"second run"


def test_collects_through_trusted_symlink_ancestor_spelling(artifact_case, tmp_path):
    package, config, storage, key = artifact_case
    _put(package / "output", "report.json", b"trusted ancestor")
    real = tmp_path / "real"
    real.mkdir()
    package.rename(real / package.name)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires platform permission")
    alias_package = alias / package.name

    _collect((alias_package, alias_package / config.name, storage, key))

    assert storage.read_bytes(key, "report.json") == b"trusted ancestor"


def test_rejects_symlink_as_final_package_directory(artifact_case, tmp_path):
    package, config, storage, key = artifact_case
    _put(package / "output", "report.json", b"linked package")
    alias = tmp_path / "linked-robot"
    try:
        alias.symlink_to(package, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires platform permission")

    _assert_rejected((alias, alias / config.name, storage, key))

    assert storage.list_files(key) == []


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "../outside",
        "output/../results",
        "output/.",
        "output//x",
        "/tmp/output",
        "C:/output",
        "C:output",
        "\\\\server\\share",
        "out\\nested",
        None,
        42,
        True,
        ["output"],
        {"name": "output"},
    ],
)
def test_rejects_noncanonical_or_unsafe_artifact_roots(artifact_case, value):
    _package, config, storage, key = artifact_case
    config.write_text(
        json.dumps({"tasks": {}, "artifactsDir": value}), encoding="utf-8"
    )

    _assert_rejected(artifact_case)

    assert storage.list_files(key) == []


@pytest.mark.parametrize("contents", ["[unterminated", "- output\n", "null\n"])
def test_rejects_malformed_or_nonmapping_config(artifact_case, contents):
    artifact_case[1].write_text(contents, encoding="utf-8")
    _assert_rejected(artifact_case)


@pytest.mark.parametrize("source", ["yaml", "oserror"])
def test_logged_collection_errors_exclude_private_source_details(
    artifact_case, monkeypatch, caplog, source
):
    module = _collector()
    config = artifact_case[1]
    sentinel = "ROBOT_ARTIFACT_PRIVATE_SENTINEL"
    if source == "yaml":
        config.write_text(f'tasks: {{}}\nsecret: "{sentinel}\n', encoding="utf-8")
    else:
        open_file = Path.open

        def private_open_error(path, *args, **kwargs):
            if path == config:
                raise OSError(sentinel)
            return open_file(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", private_open_error)
    logger = logging.getLogger("actions.server.robot_artifact_diagnostic_test")

    with caplog.at_level(logging.ERROR, logger=logger.name):
        try:
            _collect(artifact_case)
        except module.RobotArtifactError as error:
            assert sentinel not in str(error)
            logger.exception("Robot artifact collection failed")
        else:
            pytest.fail("Invalid configuration was accepted")

    assert "RobotArtifactError" in caplog.text
    assert "Robot artifact collection failed" in caplog.text
    assert sentinel not in caplog.text


@pytest.mark.parametrize("over_limit", [False, True])
def test_bounds_actual_configuration_bytes(artifact_case, monkeypatch, over_limit):
    content = b"tasks: {}\n" + b" " * 32
    artifact_case[1].write_bytes(content)
    monkeypatch.setattr(
        _collector(), "MAX_CONFIG_BYTES", len(content) - int(over_limit)
    )

    if over_limit:
        _assert_rejected(artifact_case)
    else:
        _collect(artifact_case)

    assert artifact_case[2].list_files(artifact_case[3]) == []


@pytest.mark.parametrize(
    "name",
    [
        "env.json",
        "ENV.JSON",
        "__action_server_output.txt",
        "__ACTION_SERVER_OUTPUT.TXT",
        "__action_server_custom.json",
        ".action-server-run-bindings.json",
        ".artifact-temporary",
        "nested/env.json",
        "nested/__action_server_output.txt",
    ],
)
def test_rejects_reserved_names_and_preserves_server_files(artifact_case, name):
    package, _config, storage, key = artifact_case
    storage.write_bytes(key, "env.json", b"server environment")
    storage.write_bytes(key, "__action_server_output.txt", b"server console")
    _put(package / "output", name, b"robot replacement")

    _assert_rejected(artifact_case)

    assert storage.read_bytes(key, "env.json") == b"server environment"
    assert storage.read_bytes(key, "__action_server_output.txt") == b"server console"


@pytest.mark.parametrize(
    "name", ["CON.txt", "trailing.", "trailing ", "name:stream", "back\\slash"]
)
def test_rejects_nonportable_output_names(artifact_case, name):
    package = artifact_case[0]
    try:
        _put(package / "output", name)
    except OSError:
        pytest.skip("Filesystem does not permit this unsafe fixture name")

    _assert_rejected(artifact_case)


@pytest.mark.parametrize(
    "names", [("Report.json", "report.json"), ("caf\u00e9.txt", "cafe\u0301.txt")]
)
def test_rejects_portable_name_collisions(artifact_case, names):
    package = artifact_case[0]
    output = package / "output"
    for name in names:
        _put(output, name)
    if len(list(output.iterdir())) != 2:
        pytest.skip("Filesystem aliases the colliding fixture names")

    _assert_rejected(artifact_case)


def test_rejects_case_colliding_directory_prefixes(artifact_case):
    output = artifact_case[0] / "output"
    _put(output, "Results/first.csv")
    _put(output, "results/second.csv")
    if len(list(output.iterdir())) != 2:
        pytest.skip("Filesystem aliases the colliding fixture directories")
    _assert_rejected(artifact_case)


@pytest.mark.parametrize("kind", ["root", "directory", "file", "dangling"])
def test_rejects_symbolic_links_without_reading_the_target(
    artifact_case, tmp_path, kind
):
    package, _config, storage, key = artifact_case
    outside = tmp_path / "outside"
    outside.mkdir()
    _put(outside, "secret.txt", b"private outside bytes")
    output = package / "output"
    try:
        if kind == "root":
            output.symlink_to(outside, target_is_directory=True)
        else:
            output.mkdir()
            target = outside if kind == "directory" else outside / "secret.txt"
            if kind == "dangling":
                target = outside / "missing"
            (output / "linked").symlink_to(
                target, target_is_directory=kind == "directory"
            )
    except OSError:
        pytest.skip("Creating symlinks requires platform permission")

    _assert_rejected(artifact_case)

    assert storage.list_files(key) == []
    assert (outside / "secret.txt").read_bytes() == b"private outside bytes"


def test_rejects_hardlinked_files(artifact_case, tmp_path):
    package, _config, storage, key = artifact_case
    outside = _put(tmp_path, "private.txt", b"private outside bytes")
    output = package / "output"
    output.mkdir()
    try:
        os.link(outside, output / "linked.txt")
    except OSError:
        pytest.skip("Filesystem does not support hardlink fixture")

    _assert_rejected(artifact_case)

    assert storage.list_files(key) == []


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO fixture requires POSIX")
def test_rejects_fifo_without_opening_it(artifact_case):
    output = artifact_case[0] / "output"
    output.mkdir()
    os.mkfifo(output / "pipe")
    _assert_rejected(artifact_case)


@pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"), reason="Unix socket fixture unavailable"
)
def test_rejects_socket_entries(artifact_case):
    output = artifact_case[0] / "output"
    output.mkdir()
    with socket.socket(socket.AF_UNIX) as server:
        try:
            server.bind(str(output / "socket"))
        except OSError:
            pytest.skip("Filesystem cannot create this Unix socket fixture")
        _assert_rejected(artifact_case)


def test_rejects_reparse_attributes(artifact_case, monkeypatch):
    source = _put(artifact_case[0] / "output", "junction.txt")
    original = Path.lstat

    def reparse_lstat(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path == source:
            fields = {
                name: getattr(result, name)
                for name in dir(result)
                if name.startswith("st_")
            }
            fields["st_file_attributes"] = getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024
            )
            return SimpleNamespace(**fields)
        return result

    monkeypatch.setattr(Path, "lstat", reparse_lstat)
    _assert_rejected(artifact_case)


def test_accepts_exact_file_and_total_byte_limits(artifact_case, monkeypatch):
    module = _collector()
    monkeypatch.setattr(module, "MAX_FILE_BYTES", 3)
    monkeypatch.setattr(module, "MAX_TOTAL_BYTES", 6)
    _put(artifact_case[0] / "output", "a.bin", b"abc")
    _put(artifact_case[0] / "output", "b.bin", b"def")

    _collect(artifact_case)

    assert artifact_case[2].list_files(artifact_case[3]) == [("a.bin", 3), ("b.bin", 3)]


@pytest.mark.parametrize("limit", ["file", "total"])
def test_rejects_bytes_above_file_or_total_limit(artifact_case, monkeypatch, limit):
    module = _collector()
    monkeypatch.setattr(module, "MAX_FILE_BYTES", 3 if limit == "file" else 10)
    monkeypatch.setattr(module, "MAX_TOTAL_BYTES", 3 if limit == "total" else 10)
    _put(artifact_case[0] / "output", "oversized.bin", b"abcd")

    _assert_rejected(artifact_case)

    assert artifact_case[2].list_files(artifact_case[3]) == []


def test_enforces_aggregate_limit_across_files(artifact_case, monkeypatch):
    module = _collector()
    monkeypatch.setattr(module, "MAX_FILE_BYTES", 3)
    monkeypatch.setattr(module, "MAX_TOTAL_BYTES", 5)
    _put(artifact_case[0] / "output", "a.bin", b"abc")
    _put(artifact_case[0] / "output", "b.bin", b"def")

    _assert_rejected(artifact_case)

    assert (
        sum(size for _name, size in artifact_case[2].list_files(artifact_case[3])) <= 5
    )


def test_bounds_zero_byte_entry_count(artifact_case, monkeypatch):
    monkeypatch.setattr(_collector(), "MAX_ENTRIES", 2)
    for name in ("a", "b", "c"):
        _put(artifact_case[0] / "output", name, b"")

    _assert_rejected(artifact_case)


def test_bounds_nested_directory_depth(artifact_case, monkeypatch):
    monkeypatch.setattr(_collector(), "MAX_DEPTH", 2)
    _put(artifact_case[0] / "output", "one/two/three/data.bin")
    _assert_rejected(artifact_case)


def test_reads_in_bounded_chunks(artifact_case, monkeypatch):
    module = _collector()
    monkeypatch.setattr(module, "CHUNK_BYTES", 3)
    source = _put(artifact_case[0] / "output", "payload.bin", b"0123456789")
    identity = source.stat()
    read = os.read
    sizes = []

    def observe_read(fd, size):
        current = os.fstat(fd)
        if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
            sizes.append(size)
        return read(fd, size)

    monkeypatch.setattr(module.os, "read", observe_read)
    _collect(artifact_case)

    assert sizes and all(0 < size <= 3 for size in sizes)
    assert artifact_case[2].read_bytes(artifact_case[3], "payload.bin") == b"0123456789"


@pytest.mark.parametrize("mutation", ["grow", "same-size"])
def test_rejects_source_mutation_during_read(artifact_case, monkeypatch, mutation):
    module = _collector()
    monkeypatch.setattr(module, "CHUNK_BYTES", 2)
    monkeypatch.setattr(module, "MAX_FILE_BYTES", 6)
    source = _put(artifact_case[0] / "output", "payload.bin", b"abcdef")
    identity = source.stat()
    read = os.read
    changed = False
    bytes_read = 0

    def mutate_after_read(fd, size):
        nonlocal changed, bytes_read
        content = read(fd, size)
        current = os.fstat(fd)
        if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
            bytes_read += len(content)
        if not changed and (current.st_dev, current.st_ino) == (
            identity.st_dev,
            identity.st_ino,
        ):
            changed = True
            source.write_bytes(b"abcdefghi" if mutation == "grow" else b"ABCDEF")
            os.utime(
                source, ns=(identity.st_atime_ns, identity.st_mtime_ns + 1_000_000_000)
            )
        return content

    monkeypatch.setattr(module.os, "read", mutate_after_read)

    _assert_rejected(artifact_case)

    assert changed
    assert bytes_read <= module.MAX_FILE_BYTES + 1
    assert artifact_case[2].list_files(artifact_case[3]) == []


def test_read_failure_retains_previously_published_files(artifact_case, monkeypatch):
    module = _collector()
    expected = {"a.bin": b"first payload", "b.bin": b"second payload"}
    identities = set()
    for name, content in expected.items():
        info = _put(artifact_case[0] / "output", name, content).stat()
        identities.add((info.st_dev, info.st_ino))
    seen = set()
    read = os.read

    def fail_second_file(fd, size):
        info = os.fstat(fd)
        identity = (info.st_dev, info.st_ino)
        if identity in identities:
            seen.add(identity)
            if len(seen) > 1:
                raise OSError("source read failed")
        return read(fd, size)

    monkeypatch.setattr(module.os, "read", fail_second_file)

    _assert_rejected(artifact_case)

    files = artifact_case[2].list_files(artifact_case[3])
    assert len(files) == 1
    name, size = files[0]
    assert size == len(expected[name])
    assert artifact_case[2].read_bytes(artifact_case[3], name) == expected[name]


def test_rejects_parent_replacement_before_source_open(artifact_case, monkeypatch):
    module = _collector()
    source = _put(artifact_case[0] / "output", "nested/payload.bin", b"original")
    open_file = os.open
    replaced = False

    def replace_parent(path, flags, *args, **kwargs):
        nonlocal replaced
        if Path(path) == source and not replaced:
            replaced = True
            source.parent.rename(source.parent.with_name("replaced-parent"))
            source.parent.mkdir()
            source.write_bytes(b"replacement bytes")
        return open_file(path, flags, *args, **kwargs)

    monkeypatch.setattr(module.os, "open", replace_parent)

    _assert_rejected(artifact_case)

    assert replaced
    assert artifact_case[2].list_files(artifact_case[3]) == []
