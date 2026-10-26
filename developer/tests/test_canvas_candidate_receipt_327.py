"""Execute candidate receipt admission with safe-path and authority controls."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/frontend-build-unauthenticated.yml"
MEASURED = (
    ROOT
    / "docs/program/evidence/actions-next-327/recovery-20261026/a59-platform-checkpoint/browser/candidate-receipt.json"
)
TEST_CLASS = "tests.action_server_tests.mcp.test_canvas_query_template"
TEST_NAME = (
    "test_canvas_template_candidate_source_runs_through_runtime_and_real_browser"
)


def _relocate(value, root):
    if isinstance(value, str) and value.startswith("/"):
        return str(root.joinpath(*value.lstrip("/").split("/")))
    if isinstance(value, list):
        return [_relocate(item, root) for item in value]
    if isinstance(value, dict):
        return {key: _relocate(item, root) for key, item in value.items()}
    return value


def _validate(tmp_path, poison=None):
    # Relocated metadata is an owned admission fixture, never a new service or
    # browser execution claim. Preserve the committed measured receipt bytes.
    measured = json.loads(MEASURED.read_text())
    receipt = _relocate(deepcopy(measured), tmp_path / "absolute")
    if poison == "unsafe_launcher":
        receipt["candidate_core"]["runtime_process_args"].remove("-P")
    elif poison == "source_identity":
        receipt["candidate_core"]["source_revision"] = "0" * 40
    elif poison == "worker_identity":
        receipt["candidate_core"]["worker"]["wheel_sha256"] = "0" * 64
    root = ET.Element("testsuites")
    suite = ET.SubElement(
        root, "testsuite", tests="1", failures="0", skipped="0", errors="0"
    )
    ET.SubElement(suite, "testcase", classname=TEST_CLASS, name=TEST_NAME)
    junit = tmp_path / "raw.xml"
    ET.ElementTree(root).write(junit)
    source = tmp_path / "raw.json"
    source.write_text(json.dumps(receipt))
    safe = tmp_path / "safe.json"
    step = next(
        step
        for job in yaml.safe_load(WORKFLOW.read_text())["jobs"].values()
        for step in job["steps"]
        if step["name"]
        == "Verify Canvas candidate-source Runtime and browser acceptance"
    )
    validator = step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            validator,
            str(junit),
            str(tmp_path / "safe.xml"),
            "0",
            str(source),
            str(safe),
            measured["candidate_core"]["source_revision"],
            measured["candidate_core"]["source_tree"],
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result, safe


def test_actual_candidate_metadata_with_safe_path_is_admitted(tmp_path):
    result, safe = _validate(tmp_path)
    assert result.returncode == 0, result.stderr
    assert safe.is_file()


@pytest.mark.parametrize(
    "poison", ["unsafe_launcher", "source_identity", "worker_identity"]
)
def test_candidate_rejects_unsafe_launcher_or_changed_authority(tmp_path, poison):
    result, safe = _validate(tmp_path, poison)
    assert result.returncode != 0
    assert not safe.exists()
