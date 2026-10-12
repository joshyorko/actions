"""Current bytes cannot be admitted with predecessor or coordinated false labels."""
import copy
import importlib.util
import json
import os
from pathlib import Path

import pytest

BASE = Path(__file__).parent
PATH = Path(
    os.environ.get(
        "ADMISSION_PROVENANCE_GATE", str(BASE / "current-input-admission-v4.py")
    )
)
SPEC = importlib.util.spec_from_file_location("current_provenance_guard", PATH)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def manifest():
    return json.loads((BASE / "input-and-source-admission-v5.json").read_text())


def admit(value):
    return gate.admit(
        Path(value["original_archive"]["path_private"]),
        Path(value["original_selected_wheel"]["private_path"]),
        value,
        Path("/workspace/engineering/pr282"),
    )


def test_independently_qualified_current_bytes_and_labels_pass():
    value = manifest()
    result = admit(value)
    assert (
        result["python_member_count"] == 202
        and result["tracked_payload_source_matches"] == 215
    )
    assert value["original_archive"]["id"] == 11697353355
    assert value["original_archive"]["run"] == 38126987514
    assert value["original_archive"]["job"] == 114433293243


@pytest.mark.parametrize(
    "field,producer_field,stale",
    [
        ("id", "artifact_id", 11693813383),
        ("run", "run_id", 38118859475),
        ("job", "job_id", 114409246244),
    ],
)
@pytest.mark.parametrize("coordinated", [False, True])
def test_correct_current_archive_bytes_reject_false_provenance(
    field, producer_field, stale, coordinated
):
    value = manifest()
    # Valid baseline prevents an unrelated input gate failure from qualifying a poison.
    admit(value)
    original_body_identity = copy.deepcopy(value["original_archive"])
    value["original_archive"][field] = stale
    if coordinated:
        value["producer_tuple"][producer_field] = stale
    for name in ("path_private", "bytes", "sha256"):
        assert value["original_archive"][name] == original_body_identity[name]
    with pytest.raises(AssertionError):
        admit(value)


def test_independent_qualification_cannot_be_relabelled(monkeypatch, tmp_path):
    value = manifest()
    admit(value)
    body = json.loads(gate.TRUSTED_QUALIFICATION.read_text())
    body["producer"]["run_id"] = 38118859475
    replacement = tmp_path / "untrusted-qualification.json"
    replacement.write_text(json.dumps(body))
    monkeypatch.setattr(gate, "TRUSTED_QUALIFICATION", replacement)
    with pytest.raises(AssertionError):
        admit(value)
