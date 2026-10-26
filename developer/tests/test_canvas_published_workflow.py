"""Execute generated published-Canvas admission without starting a service."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import os
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/actions_runtime_tests.yml"
FIXTURE = Path(__file__).parent / "fixtures/canvas-published-71f60-receipt.json"
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


def _admission_input(relative: str, repository: Path = ROOT) -> bytes:
    if repository == ROOT and relative == ADMISSION_INPUTS[0]:
        # This is a historical measured receipt, not current Runtime evidence.
        # Bundle its exact module bytes for shallow hosted checkouts; do not
        # rewrite its measured hash when the current package version changes.
        content = FIXTURE.with_suffix(".runtime-init.txt").read_bytes()
        measured = json.loads(FIXTURE.read_text())
        assert (
            hashlib.sha256(content).hexdigest() == measured["runtime"]["module_sha256"]
        )
        return content
    return subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=repository)


def _validate(
    tmp_path: Path,
    mutation: str | None = None,
    *,
    input_repository: Path = ROOT,
    changed_input: str | None = None,
    expected_browser_version: str | None = None,
    safe_path: bool = True,
):
    # Git checkout may convert text inputs to CRLF. Preserve the measured
    # fixture's byte contract with canonical inputs, not normalized work files.
    checkout = tmp_path / "admission-checkout"
    for relative in ADMISSION_INPUTS:
        content = _admission_input(relative, input_repository)
        path = checkout / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
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
    # Project only the launcher into the current safe-path contract. The
    # retained historical receipt and its measured module bytes stay unchanged;
    # this owned admission fixture is not new historical execution evidence.
    assert receipt["runtime"]["process_args"][1:3] == ["-m", "actions.server"]
    if safe_path:
        receipt["runtime"]["process_args"].insert(1, "-P")
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
    elif mutation and not mutation.startswith("receipt_"):
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
    if mutation == "receipt_missing":
        raw_receipt.unlink()
    elif mutation == "receipt_invalid_json":
        raw_receipt.write_text("private https://provider.invalid/?token=poison")
    elif mutation == "receipt_invalid_text":
        raw_receipt.write_bytes(b"\xffprivate-provider-token")
    elif mutation == "receipt_not_object":
        raw_receipt.write_text("[]")
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
    validator = _validator()
    if mutation == "receipt_read_denied":
        validator = (
            "import sys\n"
            "def deny_receipt_read(event, args):\n"
            "    if event == 'open' and args[0] == sys.argv[4]:\n"
            "        raise PermissionError('private https://provider.invalid/?token=poison')\n"
            "sys.addaudithook(deny_receipt_read)\n" + validator
        )
    command = [
        sys.executable,
        "-c",
        validator,
        str(raw_junit),
        str(safe_junit),
        status,
        str(raw_receipt),
        str(safe_receipt),
        measured["source"]["commit"],
        measured["source"]["tree"],
        " ".join(measured["source"]["parents"]),
        measured["browser"]["sha256"],
        measured["browser"]["version"]
        if expected_browser_version is None
        else expected_browser_version,
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


def _browser_version_preflight(tmp_path: Path, stdout: bytes, exitcode: int = 0):
    step = next(
        step
        for step in _steps()
        if step["name"] == "Verify Canvas published-Core Runtime and browser acceptance"
    )
    assignment = next(
        line for line in step["run"].splitlines() if line.startswith("browser_version=")
    )
    command = shlex.split(
        assignment.removeprefix('browser_version="$(').removesuffix(')"')
    )
    assert command[:4] == ["poetry_cmd", "run", "python", "-c"]
    browser = str(tmp_path / "synthetic-browser")
    output = io.StringIO()

    def measured(actual, **kwargs):
        assert actual == [browser, "--version"]
        assert kwargs == {
            "check": True,
            "capture_output": True,
            "text": True,
            "timeout": 10,
        }
        if exitcode:
            raise subprocess.CalledProcessError(exitcode, actual, stdout.decode(), "")
        return subprocess.CompletedProcess(actual, 0, stdout.decode(), "")

    # Execute the generated Python measurement, substituting only the binary
    # observation. This keeps developer controls portable and service-free.
    with pytest.MonkeyPatch.context() as patch, redirect_stdout(output):
        patch.setenv("CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", browser)
        patch.setattr(subprocess, "run", measured)
        try:
            exec(command[4], {})
        except subprocess.CalledProcessError as error:
            return subprocess.CompletedProcess(
                command, error.returncode, "", str(error)
            )
        except AssertionError as error:
            return subprocess.CompletedProcess(command, 1, "", str(error))
    # The shell retains the printed value and removes only print's final LF.
    return subprocess.CompletedProcess(
        command, 0, output.getvalue().removesuffix("\n"), ""
    )


@pytest.mark.parametrize("ending", [b" \n", b" \r\n"])
def test_browser_version_preflight_matches_receipt_measurement(tmp_path, ending):
    version = json.loads(FIXTURE.read_text())["browser"]["version"]
    observed = _browser_version_preflight(tmp_path, version.encode() + ending)
    assert observed.returncode == 0, observed.stderr
    result, _, _ = _validate(tmp_path, expected_browser_version=observed.stdout)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("change", ["brand", "version"])
def test_browser_version_preflight_does_not_normalize_identity_changes(
    tmp_path, change
):
    version = json.loads(FIXTURE.read_text())["browser"]["version"]
    brand, number = version.rsplit(" ", 1)
    changed = f"OtherBrowser {number}" if change == "brand" else f"{brand} 0.0.0.0"
    observed = _browser_version_preflight(tmp_path, changed.encode() + b" \r\n")
    assert observed.returncode == 0, observed.stderr
    result, _, _ = _validate(tmp_path, expected_browser_version=observed.stdout)
    assert result.returncode != 0
    diagnostic = json.loads(
        (tmp_path / "published-core-failure-diagnostics.json").read_text()
    )
    assert any(
        row["code"] == "browser_version" and row["status"] == "FAIL"
        for row in diagnostic["checks"]
    )


@pytest.mark.parametrize("stdout,exitcode", [(b" \r\n", 0), (b"Chromium sample\n", 7)])
def test_browser_version_preflight_rejects_empty_or_nonzero(tmp_path, stdout, exitcode):
    observed = _browser_version_preflight(tmp_path, stdout, exitcode)
    assert observed.returncode != 0


def test_browser_version_preflight_uses_checked_bounded_receipt_measurement(
    monkeypatch,
):
    step = next(
        step
        for step in _steps()
        if step["name"] == "Verify Canvas published-Core Runtime and browser acceptance"
    )
    assignment = next(
        line for line in step["run"].splitlines() if line.startswith("browser_version=")
    )
    command = shlex.split(
        assignment.removeprefix('browser_version="$(').removesuffix(')"')
    )
    assert command[:4] == ["poetry_cmd", "run", "python", "-c"]
    monkeypatch.setenv(
        "CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/synthetic/browser"
    )
    calls = []

    def timed_out(actual, **kwargs):
        calls.append((actual, kwargs))
        raise subprocess.TimeoutExpired(actual, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timed_out)
    with pytest.raises(subprocess.TimeoutExpired):
        exec(command[4], {})
    assert calls == [
        (
            ["/synthetic/browser", "--version"],
            {"check": True, "capture_output": True, "text": True, "timeout": 10},
        )
    ]


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
    "cleanup_errors_secret": (
        ("runtime", "cleanup_errors"),
        ["private https://provider.invalid/?token=poison"],
    ),
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
    assert not (receipt.parent / "published-core-failure-diagnostics.json").exists()


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
        content = _admission_input(relative)
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
    diagnostics = _failure_diagnostics(receipt)
    assert diagnostics["admission"]["pytest"] == (
        "FAIL" if mutation == "pytest_failure" else "PASS"
    )
    assert diagnostics["admission"]["junit"] == (
        "FAIL" if mutation in {"skip", "count", "name", "class"} else "PASS"
    )
    assert diagnostics["admission"]["receipt"] == (
        "FAIL" if mutation in POISONS else "PASS"
    )


def _failure_diagnostics(receipt: Path) -> dict:
    diagnostics = json.loads(
        (receipt.parent / "published-core-failure-diagnostics.json").read_text()
    )
    assert set(diagnostics) == {
        "status",
        "admission",
        "receipt_read",
        "counts",
        "checks",
    }
    assert diagnostics["status"] == "FAIL"
    assert set(diagnostics["counts"]) == {"tests", "skipped", "failures", "errors"}
    assert all(type(value) is int for value in diagnostics["counts"].values())
    assert len(diagnostics["checks"]) == 39
    assert len({check["code"] for check in diagnostics["checks"]}) == 39
    for check in diagnostics["checks"]:
        assert set(check) == {"code", "status", "failure_class"}
        assert check["status"] in {"PASS", "FAIL", "UNAVAILABLE"}
        assert check["failure_class"] in {
            "NONE",
            "IO_ERROR",
            "TEXT_ERROR",
            "JSON_ERROR",
            "TYPE_ERROR",
            "VALUE_ERROR",
            "ATTRIBUTE_ERROR",
            "KEY_ERROR",
            "OTHER_ERROR",
        }
    encoded = json.dumps(diagnostics)
    for forbidden in (
        str(receipt.parent),
        "provider.invalid",
        "private",
        "token=",
        "https://",
        "prepared-browser",
        "actions-home",
        "removed-browser-temp",
    ):
        assert forbidden not in encoded
    return diagnostics


@pytest.mark.parametrize("mutation", POISONS)
def test_receipt_poison_preserves_strict_rejection_with_diagnostics(
    tmp_path: Path, mutation: str, admitted_baseline
):
    result, junit, receipt = _validate(tmp_path, mutation)
    assert result.returncode != 0
    assert not receipt.exists()
    assert ET.parse(junit).getroot().get("failures") == "1"
    diagnostics = _failure_diagnostics(receipt)
    assert diagnostics["admission"] == {
        "pytest": "PASS",
        "junit": "PASS",
        "receipt": "FAIL",
    }
    assert any(check["status"] == "FAIL" for check in diagnostics["checks"])


@pytest.mark.parametrize(
    "mutation, status, failure_class",
    [
        ("receipt_missing", "MISSING_OR_NON_FILE", "NONE"),
        ("receipt_invalid_json", "READ_ERROR", "JSON_ERROR"),
        ("receipt_invalid_text", "READ_ERROR", "TEXT_ERROR"),
        ("receipt_read_denied", "READ_ERROR", "IO_ERROR"),
        ("receipt_not_object", "PARSED", "ATTRIBUTE_ERROR"),
    ],
)
def test_receipt_read_and_parse_failures_have_distinct_fixed_diagnostics(
    tmp_path: Path, mutation: str, status: str, failure_class: str, admitted_baseline
):
    result, junit, receipt = _validate(tmp_path, mutation)
    assert result.returncode != 0
    assert not receipt.exists()
    assert ET.parse(junit).getroot().get("failures") == "1"
    diagnostics = _failure_diagnostics(receipt)
    assert diagnostics["receipt_read"] == {"status": status, "code": failure_class}
    assert diagnostics["admission"]["receipt"] == "FAIL"
    assert "provider.invalid" not in result.stderr


def test_failure_diagnostics_cover_each_existing_receipt_predicate():
    validator = ast.parse(_validator())
    admission = next(
        node.value
        for node in ast.walk(validator)
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "receipt_ok"
        and isinstance(node.value, ast.BoolOp)
    )
    diagnostic_function = next(
        node
        for node in validator.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "write_failure_diagnostics"
    )
    checks = next(
        node.value
        for node in diagnostic_function.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "checks"
    )
    assert [ast.dump(check.elts[1].body) for check in checks.elts] == [
        ast.dump(predicate) for predicate in admission.values
    ]


def test_current_safe_path_launcher_admitted_and_unsafe_prefix_rejected(tmp_path):
    accepted = tmp_path / "safe"
    accepted.mkdir()
    result, _, receipt = _validate(accepted)
    assert result.returncode == 0, result.stderr
    assert receipt.is_file()

    rejected = tmp_path / "unsafe"
    rejected.mkdir()
    result, _, receipt = _validate(rejected, safe_path=False)
    assert result.returncode != 0
    assert not receipt.exists()
    diagnostic = _failure_diagnostics(receipt)
    assert any(
        item["code"] == "runtime_module_entry" and item["status"] == "FAIL"
        for item in diagnostic["checks"]
    )


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
    diagnostic = 'scripts/summarize_candidate_failure_327.py "$junit_raw" published'
    assert diagnostic in gate["run"]
    assert gate["run"].index("pytest_status=$?") < gate["run"].index(diagnostic)
    assert upload["if"] == "always() && matrix.os == 'ubuntu-22.04'"
    assert "receipt.sanitized.json" in upload["with"]["path"]
    assert "published-core-failure-diagnostics.json" in upload["with"]["path"]
