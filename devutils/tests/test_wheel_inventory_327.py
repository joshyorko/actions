"""Mutation controls for the independent wheel inventory qualification gate."""

import base64
import csv
import hashlib
import importlib.util
import io
import zipfile
from pathlib import Path

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


def wheel_fixture(tmp_path, mutation=None):
    prefix = "actions_runtime-1.1.0a38.dist-info/"
    members = {
        prefix
        + "METADATA": b"Name: actions-runtime\nVersion: 1.1.0a38\nRequires-Dist: sample>=1\n",
        "actions/server/example.py": b"VALUE = 1\n",
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
