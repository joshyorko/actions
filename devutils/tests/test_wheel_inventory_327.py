"""Mutation controls for the independent wheel inventory qualification gate."""

import base64
import csv
import hashlib
import importlib.util
import io
import zipfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def checker():
    path = (
        Path(__file__).parents[2]
        / "action_server/scripts/qualify_wheel_inventory_327.py"
    )
    spec = importlib.util.spec_from_file_location("wheel_inventory_327", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wheel_fixture(tmp_path, mutation=None, body=b"VALUE = 1\n"):
    prefix = "actions_runtime-1.1.0a38.dist-info/"
    members = {
        prefix
        + "METADATA": b"Name: actions-runtime\nVersion: 1.1.0a38\nRequires-Dist: sample>=1\n",
        "actions/server/example.py": body,
    }
    rows = []
    for name, body in members.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b"=")
        rows.append([name, "sha256=" + digest.decode(), str(len(body))])
    rows.append([prefix + "RECORD", "", ""])
    if mutation == "duplicate-record":
        rows.append(rows[0])
    elif mutation == "size":
        rows[0][2] = "1"
    elif mutation == "hash":
        rows[0][1] = "sha256=invalid"
    elif mutation == "self-hash":
        rows[-1][1] = "sha256=invalid"
    elif mutation == "unrecorded":
        members["extra.txt"] = b"unrecorded"
    elif mutation == "missing":
        del members["actions/server/example.py"]
    elif mutation == "tampered":
        members["actions/server/example.py"] = b"VALUE = 2\n"
    elif mutation == "traversal":
        members["../escape"] = b"rejected"
    stream = io.StringIO()
    csv.writer(stream).writerows(rows)
    members[prefix + "RECORD"] = stream.getvalue().encode()
    wheel = tmp_path / "candidate.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, body in members.items():
            archive.writestr(name, body)
        if mutation == "duplicate-archive":
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr("actions/server/example.py", b"duplicate")
    return wheel, hashlib.sha256(wheel.read_bytes()).hexdigest()


def test_exact_wheel_inventory_and_dependency_declarations(checker, tmp_path):
    wheel, digest = wheel_fixture(tmp_path)
    result = checker.qualify(wheel, digest, "1.1.0a38")
    assert len(result["inventory"]) == 3
    assert result["declared_requires_dist"] == ["sample>=1"]
    with pytest.raises(ValueError, match="digest"):
        checker.qualify(wheel, "0" * 64, "1.1.0a38")
    with pytest.raises(ValueError, match="identity"):
        checker.qualify(wheel, digest, "1.0.4")


@pytest.mark.parametrize("change", ["replace", "in-place"])
def test_path_replacement_cannot_mix_digest_and_inventory(
    checker, tmp_path, monkeypatch, change
):
    wheel, digest = wheel_fixture(tmp_path)
    replacement_dir = tmp_path / "replacement"
    replacement_dir.mkdir()
    replacement, replacement_digest = wheel_fixture(
        replacement_dir, body=b"VALUE = 2\n"
    )
    assert digest != replacement_digest
    replacement_bytes = replacement.read_bytes()
    original_open = Path.open
    swapped = []

    @contextmanager
    def replace_after_read(path, *args, **kwargs):
        with original_open(path, *args, **kwargs) as stream:
            if path != wheel or swapped:
                yield stream
                return

            def read(size):
                assert size == checker.MAX_ARCHIVE_BYTES + 1
                captured = stream.read(size)
                if change == "replace":
                    replacement.replace(wheel)
                else:
                    with original_open(wheel, "wb") as output:
                        output.write(replacement_bytes)
                swapped.append(True)
                return captured

            yield SimpleNamespace(read=read)

    monkeypatch.setattr(Path, "open", replace_after_read)
    result = checker.qualify(wheel, digest, "1.1.0a38")
    assert swapped == [True]
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == replacement_digest
    member = next(
        item
        for item in result["inventory"]
        if item["path"] == "actions/server/example.py"
    )
    assert result["wheel_sha256"] == digest
    assert member["sha256"] == hashlib.sha256(b"VALUE = 1\n").hexdigest()


def test_archive_byte_bound_precedes_zip_parsing(checker, tmp_path, monkeypatch):
    wheel, digest = wheel_fixture(tmp_path)
    monkeypatch.setattr(checker, "MAX_ARCHIVE_BYTES", 32)

    def forbidden_parse(*args, **kwargs):
        pytest.fail("Oversized archives must be rejected before ZIP parsing")

    monkeypatch.setattr(checker.zipfile, "ZipFile", forbidden_parse)
    with pytest.raises(ValueError, match="archive exceeds byte bound"):
        checker.qualify(wheel, digest, "1.1.0a38")


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate-record",
        "duplicate-archive",
        "size",
        "hash",
        "self-hash",
        "unrecorded",
        "missing",
        "tampered",
        "traversal",
    ],
)
def test_invalid_internal_inventory_rejected_with_matching_outer_hash(
    checker, tmp_path, mutation
):
    wheel, digest = wheel_fixture(tmp_path, mutation)
    with pytest.raises(ValueError):
        checker.qualify(wheel, digest, "1.1.0a38")
