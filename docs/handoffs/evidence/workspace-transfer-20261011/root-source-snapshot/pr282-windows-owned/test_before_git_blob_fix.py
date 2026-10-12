"""Execute generated published-Canvas admission without starting a service."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

ROOT = Path("/workspace/engineering/pr282")
WORKFLOW = ROOT / ".github/workflows/actions_runtime_tests.yml"
FIXTURE = ROOT / "developer/tests/fixtures/canvas-published-71f60-receipt.json"
TEST_NAME = "test_canvas_template_runs_through_runtime_and_real_browser"
TEST_CLASS = "tests.action_server_tests.mcp.test_canvas_query_template"
ADMISSION_INPUTS = (
    "action_server/src/actions/server/__init__.py",
    "action_server/src/actions/server/templates/zips/canvas-query.zip",
    "action_server/frontend/package-lock.json",
    "templates/canvas-query/package.yaml",
)


def _steps() -> list[dict]:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["build"]["steps"]


def _validator() -> str:
    step = next(
        step
        for step in _steps()
        if step["name"] == "Verify Canvas published-Core Runtime and browser acceptance"
    )
    return step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


def _relocate(value, replacements):
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, str(new))
        return value
    if isinstance(value, list):
        return [_relocate(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _relocate(item, replacements) for key, item in value.items()}
    return value


def _validate(
    tmp_path: Path,
    mutation: str | None = None,
    *,
    input_repository: Path = ROOT,
    changed_input: str | None = None,
):
    checkout = input_repository
    if changed_input:
        path = checkout / changed_input
        path.write_bytes(path.read_bytes() + b"\n")
    measured = json.loads(FIXTURE.read_text())
    receipt = _relocate(
        deepcopy(measured),
        {
            "<checkout>": checkout,
            "<actions-home>": tmp_path / "actions-home",
            "<runner-temp>": tmp_path,
            "<browser>": tmp_path / "prepared-browser",
            "<removed-browser-temp>": tmp_path / "removed-browser-temp",
        },
    )
    suites = ET.Element("testsuites")
    suite = ET.SubElement(
        suites,
        "testsuite",
        {
            "tests": "1",
            "skipped": "0",
            "failures": "0",
            "errors": "0",
        },
    )
    case = ET.SubElement(
        suite,
        "testcase",
        {
            "classname": TEST_CLASS,
            "name": TEST_NAME,
        },
    )
    status = "0"
    if mutation == "skip":
        ET.SubElement(case, "skipped", {"message": "private failure detail"})
        suite.set("skipped", "1")
    elif mutation == "count":
        suite.set("tests", "2")
    elif mutation == "name":
        case.set("name", "another_test")
    elif mutation == "class":
        case.set("classname", "another_module")
    elif mutation == "pytest_failure":
        status = "1"
    elif mutation:
        path, value = POISONS[mutation]
        target = receipt
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
    raw_junit = tmp_path / "junit.xml"
    safe_junit = tmp_path / "junit.sanitized.xml"
    raw_receipt = tmp_path / "receipt.json"
    safe_receipt = tmp_path / "receipt.sanitized.json"
    ET.ElementTree(suites).write(raw_junit, encoding="utf-8")
    raw_receipt.write_text(json.dumps(receipt))
    env = os.environ.copy()
    env.update(
        {
            "CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH": str(
                tmp_path / "prepared-browser"
            ),
            "GITHUB_WORKSPACE": str(checkout),
            "RUNNER_TEMP": str(tmp_path),
        }
    )
    # Independent preflight identities remain the measured values. Relocating
    # paths makes this admission test portable, not a new consumer execution.
    command = [
        sys.executable,
        "-c",
        _validator(),
        str(raw_junit),
        str(safe_junit),
        status,
        str(raw_receipt),
        str(safe_receipt),
        measured["source"]["commit"],
        measured["source"]["tree"],
        " ".join(measured["source"]["parents"]),
        measured["browser"]["sha256"],
        measured["browser"]["version"],
    ]
    result = subprocess.run(
        command,
        cwd=checkout / "action_server",
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result, safe_junit, safe_receipt


POISONS = {
    "source_commit": (("source", "commit"), "0" * 40),
    "resource_sha": (("built_resource_sha256",), "0" * 64),
    "template_sha": (("template_zip_sha256",), "0" * 64),
    "manifest_sha": (("production_package_manifest_sha256",), "0" * 64),
    "source_tree": (("source", "tree"), "0" * 40),
    "source_parents": (("source", "parents"), []),
    "core_floor": (("published_core", "declared_version"), "1.0.2"),
    "core_wheel": (
        ("published_core", "independently_verified_registry_wheel_sha256"),
        "0" * 64,
    ),
    "worker_version": (("published_core", "measured_worker", "version"), "1.0.2"),
    "worker_hashes": (("published_core", "measured_worker", "module_hashes"), {}),
    "worker_modules": (("published_core", "measured_worker", "modules"), {}),
    "browser_selection": (("browser", "selection"), "PATH fallback"),
    "browser_sha": (("browser", "sha256"), "0" * 64),
    "browser_path": (("browser", "path"), "/foreign/browser"),
    "browser_version": (("browser", "version"), "other Chromium"),
    "browser_status": (("browser", "status"), "failed"),
    "browser_temp": (("browser", "temporary_root_removed"), False),
    "playwright_version": (("browser", "playwright_version"), "0.0.0"),
    "wrapper_reaped": (("runtime", "wrapper_reaped"), False),
    "snapshot_false": (("runtime", "descendant_snapshot_complete"), False),
    "reap_false": (("runtime", "descendant_reap_complete"), False),
    "snapshot_integer": (("runtime", "descendant_snapshot_complete"), 1),
    "reap_integer": (("runtime", "descendant_reap_complete"), 1),
    "cleanup_errors": (("runtime", "cleanup_errors"), ["cleanup failed"]),
    "live_children": (("runtime", "live_descendant_pids"), [123]),
    "zombie_children": (("runtime", "zombie_descendant_pids"), [123]),
    "readers": (("runtime", "active_readers"), ["reader"]),
}


def test_measured_published_consumer_receipt_admitted(tmp_path: Path):
    result, junit, receipt = _validate(tmp_path)
    assert result.returncode == 0, result.stderr
    admitted = json.loads(receipt.read_text())
    assert admitted["source"]["commit"] == "71f60ee8b931cb968866db5a8f45ba2056d18ed8"
    assert (
        admitted["browser"]["sha256"]
        == "0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71"
    )
    assert str(ROOT) not in receipt.read_text()
    assert str(tmp_path) not in receipt.read_text()
    assert ET.parse(junit).getroot().get("failures") == "0"


@pytest.mark.parametrize(
    "crlf_input",
    [relative for relative in ADMISSION_INPUTS if not relative.endswith(".zip")],
)
def test_measured_admission_uses_git_bytes_from_crlf_checkout(
    tmp_path: Path, crlf_input: str
):
    repository = tmp_path / "crlf-checkout"
    repository.mkdir()
    for relative in ADMISSION_INPUTS:
        content = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=ROOT)
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", "add", "."], cwd=repository, check=True
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "Canonical admission inputs",
        ],
        cwd=repository,
        check=True,
    )
    path = repository / crlf_input
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert b"\r\n" in path.read_bytes()
    result, _, receipt = _validate(tmp_path, input_repository=repository)
    assert result.returncode == 0, result.stderr
    assert (
        json.loads(receipt.read_text())["source"]
        == json.loads(FIXTURE.read_text())["source"]
    )


@pytest.fixture(scope="module")
def admitted_baseline(tmp_path_factory):
    result, _, _ = _validate(tmp_path_factory.mktemp("admitted-baseline"))
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("changed_input", ADMISSION_INPUTS)
def test_changed_admission_input_rejected(
    tmp_path: Path, changed_input: str, admitted_baseline
):
    result, junit, receipt = _validate(tmp_path, changed_input=changed_input)
    assert result.returncode != 0, f"admitted changed {changed_input} bytes"
    assert not receipt.exists()
    assert ET.parse(junit).getroot().get("failures") == "1"


@pytest.mark.parametrize(
    "mutation", ["skip", "count", "name", "class", "pytest_failure", *POISONS]
)
def test_poisoned_published_consumer_receipt_rejected(
    tmp_path: Path, mutation: str, admitted_baseline
):
    result, junit, receipt = _validate(tmp_path, mutation)
    assert result.returncode != 0, f"admitted poisoned {mutation} receipt"
    assert not receipt.exists()
    assert ET.parse(junit).getroot().get("failures") == "1"
    assert "private failure detail" not in junit.read_text()


def test_generated_published_gate_matches_generator(tmp_path: Path):
    spec = importlib.util.spec_from_file_location(
        "canvas_workflow_generator", ROOT / ".github/workflows/_gen_workflows.py"
    )
    assert spec and spec.loader
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    target = next(t for t in generator.TARGETS if t.target == WORKFLOW.name)
    generator.CURDIR = tmp_path
    target.generate()
    assert (tmp_path / WORKFLOW.name).read_bytes() == WORKFLOW.read_bytes()
    steps = _steps()
    gate = next(
        s for s in steps if s["name"].startswith("Verify Canvas published-Core")
    )
    upload = next(
        s for s in steps if s["name"].startswith("Upload Canvas published-Core")
    )
    setup = next(
        s
        for s in steps
        if s["name"] == "Install Playwright Chromium for Runtime browser acceptance"
    )
    assert steps.index(setup) < steps.index(gate) < steps.index(upload)
    assert gate["if"] == "matrix.os == 'ubuntu-22.04'"
    assert upload["if"] == "always() && matrix.os == 'ubuntu-22.04'"
    assert "receipt.sanitized.json" in upload["with"]["path"]
