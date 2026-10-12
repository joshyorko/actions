"""Private service-free controls: read bytes/Git only, never install/import Runtime."""
import base64
import csv
import importlib.util
import io
import json
import os
import zipfile
from pathlib import Path

import pytest

BASE = Path(__file__).parent
PATH = Path(
    os.environ.get("ADMISSION_REVIEW_GATE", str(BASE / "current-input-admission-v2.py"))
)
SPEC = importlib.util.spec_from_file_location("current_input_admission_review", PATH)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
ROOT = "actions_runtime-1.0.3.dist-info"


def payload(metadata=None):
    contents = {
        ROOT + "/METADATA": metadata
        or b"Metadata-Version: 2.1\nName: actions-runtime\nVersion: 1.0.3\n\n",
        ROOT
        + "/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: cp312-cp312-manylinux2014_x86_64\n",
        "actions/server/public.py": b"from actions import ActionContext\n",
    }
    output = io.StringIO()
    writer = csv.writer(output)
    for name, body in contents.items():
        encoded = (
            base64.urlsafe_b64encode(__import__("hashlib").sha256(body).digest())
            .decode()
            .rstrip("=")
        )
        writer.writerow([name, "sha256=" + encoded, str(len(body))])
    writer.writerow([ROOT + "/RECORD", "", ""])
    contents[ROOT + "/RECORD"] = output.getvalue().encode()
    return contents


def test_record_and_metadata_positive_runs_actual_validator():
    result = gate.validate_payload(payload())
    assert result["record_entries"] == 4 and result["record_verified_entries"] == 3
    assert result["python_member_count"] == 1


def test_metadata_rejects_non_utf8():
    contents = payload(
        b"Metadata-Version: 2.1\nName: actions-runtime\nVersion: 1.0.3\nSummary: \xff\n\n"
    )
    with pytest.raises((AssertionError, UnicodeDecodeError)):
        gate.validate_payload(contents)


@pytest.mark.parametrize(
    "poison",
    [
        "name",
        "version",
        "duplicate_name",
        "duplicate_version",
        "extra_metadata",
        "purelib",
        "wrong_tag",
    ],
)
def test_metadata_shape_rejection_uses_actual_validator(poison):
    contents = payload()
    if poison == "name":
        contents[ROOT + "/METADATA"] = contents[ROOT + "/METADATA"].replace(
            b"Name: actions-runtime", b"Name: unrelated"
        )
    elif poison == "version":
        contents[ROOT + "/METADATA"] = contents[ROOT + "/METADATA"].replace(
            b"Version: 1.0.3", b"Version: 1.0.2"
        )
    elif poison.startswith("duplicate"):
        field = (
            b"Name: actions-runtime\n"
            if poison == "duplicate_name"
            else b"Version: 1.0.3\n"
        )
        contents[ROOT + "/METADATA"] = field + contents[ROOT + "/METADATA"]
    elif poison == "extra_metadata":
        contents["other.dist-info/METADATA"] = b"Name: unrelated\nVersion: 1\n"
    elif poison == "purelib":
        contents[ROOT + "/WHEEL"] = contents[ROOT + "/WHEEL"].replace(b"false", b"true")
    else:
        contents[ROOT + "/WHEEL"] = contents[ROOT + "/WHEEL"].replace(
            b"cp312-cp312-manylinux2014_x86_64", b"cp313-cp313-manylinux2014_x86_64"
        )
    with pytest.raises(AssertionError):
        gate.validate_payload(contents)


@pytest.mark.parametrize(
    "poison",
    [
        "missing_record",
        "duplicate",
        "omitted_member",
        "extra_member",
        "digest",
        "size",
        "record_self_hash",
        "invalid_utf8",
        "malformed_row",
    ],
)
def test_record_rejection_reads_real_rows_and_payload_bytes(poison):
    contents = payload()
    name = ROOT + "/RECORD"
    rows = list(csv.reader(io.StringIO(contents[name].decode())))
    if poison == "missing_record":
        contents.pop(name)
    elif poison == "duplicate":
        rows.append(rows[0])
    elif poison == "omitted_member":
        rows = rows[1:]
    elif poison == "extra_member":
        rows.append(["extra.py", "sha256=" + "A" * 43, "0"])
    elif poison == "digest":
        rows[0][1] = "sha256=" + "A" * 43
    elif poison == "size":
        rows[0][2] = "999999"
    elif poison == "record_self_hash":
        rows[-1][1] = "sha256=" + "A" * 43
    elif poison == "invalid_utf8":
        contents[name] = b"\xff"
    else:
        rows[0].pop()
    if poison not in ["missing_record", "invalid_utf8"]:
        output = io.StringIO()
        csv.writer(output).writerows(rows)
        contents[name] = output.getvalue().encode()
    with pytest.raises((AssertionError, KeyError, UnicodeDecodeError)):
        gate.validate_payload(contents)


@pytest.mark.parametrize(
    "poison",
    [
        "duplicate",
        "traversal",
        "absolute",
        "backslash",
        "colon",
        "symlink",
        "encrypted",
    ],
)
def test_safe_archive_names_use_original_inspector_function(tmp_path, poison):
    path = tmp_path / "synthetic.zip"
    name = {
        "traversal": "../private.py",
        "absolute": "/private.py",
        "backslash": "a\\private.py",
        "colon": "C:private.py",
    }.get(poison, "public.py")
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo(name)
        if poison == "symlink":
            info.external_attr = (__import__("stat").S_IFLNK | 0o777) << 16
        archive.writestr(info, b"not executable")
        if poison == "duplicate":
            archive.writestr(name, b"different bytes")
    if poison == "encrypted":
        body = bytearray(path.read_bytes())
        local = body.index(b"PK\x03\x04")
        central = body.index(b"PK\x01\x02")
        body[local + 6 : local + 8] = (1).to_bytes(2, "little")
        body[central + 8 : central + 10] = (1).to_bytes(2, "little")
        path.write_bytes(body)
    with zipfile.ZipFile(path) as archive, pytest.raises(AssertionError):
        gate.safe_members(archive)


def test_original_current_input_gate_reads_zip_record_and_current_git_without_install():
    manifest = json.loads((BASE / "input-and-source-admission.json").read_text())
    result = gate.admit(
        Path(manifest["original_archive"]["path_private"]),
        Path(manifest["original_selected_wheel"]["private_path"]),
        manifest,
        Path("/workspace/engineering/pr282"),
    )
    assert result["record_entries"] == 215 and result["record_verified_entries"] == 214
    assert (
        result["python_member_count"] == 196
        and result["tracked_payload_source_matches"] == 209
    )
    assert result["generated_oauth_content"] == "EMPTY_CONTENT_AUTHORITY_HOLD"


@pytest.mark.parametrize(
    "poison",
    [
        "wrong_tree",
        "wrong_source_blob",
        "wrong_member_digest",
        "omitted_source",
        "wrong_archive_digest",
        "wrong_wheel_digest",
    ],
)
def test_current_source_and_archive_binding_mutations_rejected(poison):
    manifest = json.loads((BASE / "input-and-source-admission.json").read_text())
    if poison == "wrong_tree":
        manifest["actual_integration"]["tree"] = "0" * 40
    elif poison == "wrong_source_blob":
        manifest["tracked_member_bindings"][0]["source_blob"] = "0" * 40
    elif poison == "wrong_member_digest":
        manifest["tracked_member_bindings"][0]["member_sha256"] = "0" * 64
    elif poison == "omitted_source":
        manifest["tracked_member_bindings"].pop()
    elif poison == "wrong_archive_digest":
        manifest["original_archive"]["sha256"] = "0" * 64
    else:
        manifest["original_selected_wheel"]["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        gate.admit(
            Path(manifest["original_archive"]["path_private"]),
            Path(manifest["original_selected_wheel"]["private_path"]),
            manifest,
            Path("/workspace/engineering/pr282"),
        )
