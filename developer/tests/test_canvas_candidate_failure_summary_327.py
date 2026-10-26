"""Privacy and non-admission contracts for candidate browser diagnostics."""

import importlib.util
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[2]
HELPER = ROOT / "action_server" / "scripts" / "summarize_candidate_failure_327.py"
WORKFLOW = ROOT / ".github" / "workflows" / "frontend-build-unauthenticated.yml"
TEST_CLASS = "tests.action_server_tests.mcp.test_canvas_query_template"
TEST_NAME = (
    "test_canvas_template_candidate_source_runs_through_runtime_and_real_browser"
)
ALLOWED_EXCEPTION_CLASSES = {
    "AssertionError",
    "RuntimeError",
    "CalledProcessError",
    "TimeoutExpired",
    "FileNotFoundError",
    "TypeError",
    "ValueError",
    "StopIteration",
    "Failed",
    "OSError",
    "OTHER",
}


def load_helper():
    """Load lazily so the workflow contract can run before the helper lands."""
    spec = importlib.util.spec_from_file_location(
        "candidate_failure_summary_327", HELPER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def junit_file(
    path: Path,
    *,
    failure: str | None,
    classname: str = TEST_CLASS,
    name: str = TEST_NAME,
):
    root = ET.Element(
        "testsuite",
        {"name": "candidate", "tests": "1", "failures": "1" if failure else "0"},
    )
    case = ET.SubElement(root, "testcase", {"classname": classname, "name": name})
    if failure is not None:
        node = ET.SubElement(case, "failure", {"message": "PRIVATE_ASSERTION_TEXT"})
        node.text = failure
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return path


def availability(summary):
    assert summary["availability"] in {"AVAILABLE", "UNAVAILABLE", "NOT_NEEDED"}
    return summary["availability"]


def test_published_profile_reports_only_its_allowlisted_case(tmp_path):
    helper = load_helper()
    path = junit_file(
        tmp_path / "published.xml",
        failure="/private/test_canvas_query_template.py:1173: AssertionError: secret",
        name="test_canvas_template_runs_through_runtime_and_real_browser",
    )
    summary = helper.summarize(path, profile="published")
    assert summary["locations"] == [{"line": 1173, "exception_class": "AssertionError"}]
    assert "secret" not in json.dumps(summary)
    assert availability(helper.summarize(path)) == "UNAVAILABLE"


def test_published_profile_does_not_report_candidate_case(tmp_path):
    helper = load_helper()
    path = junit_file(
        tmp_path / "candidate.xml",
        failure="test_canvas_query_template.py:688: AssertionError",
    )
    assert availability(helper.summarize(path, profile="published")) == "UNAVAILABLE"


def test_unknown_profile_is_rejected_without_reading_junit(tmp_path):
    helper = load_helper()
    assert helper.summarize(tmp_path / "missing", profile="untrusted") == {
        "availability": "UNAVAILABLE",
        "locations": [],
        "reason": "UNKNOWN_PROFILE",
    }


def assert_private(summary, *canaries):
    encoded = json.dumps(summary, sort_keys=True)
    for canary in canaries:
        assert canary not in encoded
    for item in summary.get("locations", []):
        assert isinstance(item, dict)
        assert set(item) == {"line", "exception_class"}
        assert isinstance(item["line"], int) and 1 <= item["line"] <= 999_999
        assert item["exception_class"] in ALLOWED_EXCEPTION_CLASSES


def test_workflow_runs_advisory_summary_without_changing_candidate_gate():
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = document["jobs"]["build-external"]["steps"]
    candidate = next(
        step
        for step in steps
        if step.get("name")
        == "Verify Canvas candidate-source Runtime and browser acceptance"
    )
    run = candidate["run"]
    summary_call = (
        "poetry_cmd run python scripts/summarize_candidate_failure_327.py "
        '"$junit_raw"'
    )

    assert summary_call in run
    assert run.index("pytest_status=$?") < run.index(summary_call)
    assert run.index(summary_call) < run.index(
        "if not junit_ok or pytest_status or not receipt_ok:"
    )
    # The browser result and receipt remain the actual admission inputs.
    assert "junit_ok = (" in run
    assert "receipt_ok = (" in run
    assert "if not junit_ok or pytest_status or not receipt_ok:" in run
    assert "Candidate acceptance did not produce one verified pass" in run


def test_summary_extracts_only_known_candidate_locations_and_fixed_classes(tmp_path):
    raw = (
        "Traceback (most recent call last):\n"
        '  File "/home/runner/work/actions/action_server/tests/action_server_tests/mcp/'
        'test_canvas_query_template.py", line 42, in run_candidate\n'
        "AssertionError: PRIVATE_ASSERTION_TEXT token=PRIVATE_TOKEN\n"
        "Traceback (most recent call last):\n"
        r'  File "C:\actions\action_server\tests\action_server_tests\mcp\test_canvas_query_template.py", line 77, in run_candidate'
        + "\n"
        "AssertionError: PRIVATE_ASSERTION_TEXT token=PRIVATE_TOKEN\n"
    )
    summary = load_helper().summarize(
        junit_file(tmp_path / "candidate.xml", failure=raw)
    )

    assert availability(summary) == "AVAILABLE"
    locations = summary["locations"]
    assert locations == [
        {"line": 42, "exception_class": "AssertionError"},
        {"line": 77, "exception_class": "AssertionError"},
    ]
    assert_private(
        summary,
        "PRIVATE_ASSERTION_TEXT",
        "PRIVATE_TOKEN",
        "/home/runner/work/actions",
        r"C:\actions",
    )


def test_summary_deduplicates_sorts_and_caps_candidate_locations(tmp_path):
    trace = (
        "\n".join(
            f'  File "/tmp/action_server/tests/action_server_tests/mcp/'
            f'test_canvas_query_template.py", line {line}, in candidate'
            for line in [30, *range(30, 50)]
        )
        + "\nRuntimeError: PRIVATE_DETAIL"
    )
    summary = load_helper().summarize(junit_file(tmp_path / "many.xml", failure=trace))

    assert availability(summary) == "AVAILABLE"
    locations = summary["locations"]
    assert len(locations) <= 16
    lines = [item["line"] for item in locations]
    assert lines == sorted(set(lines))
    assert_private(summary, "PRIVATE_DETAIL", "/tmp/action_server")


@pytest.mark.parametrize("separator", ["/", "\\"])
def test_pytest_short_location_never_exposes_its_assertion(tmp_path, separator):
    trace = (
        separator.join(("private", "tests", "mcp", "test_canvas_query_template.py"))
        + ":644: AssertionError: PRIVATE_TOKEN_327\n"
    )
    summary = load_helper().summarize(junit_file(tmp_path / "short.xml", failure=trace))
    assert availability(summary) == "AVAILABLE"
    assert summary["locations"] == [{"line": 644, "exception_class": "AssertionError"}]
    assert_private(summary, "private", "PRIVATE_TOKEN_327")


@pytest.mark.parametrize(
    "exception_class",
    sorted(ALLOWED_EXCEPTION_CLASSES - {"OTHER"}),
)
def test_allowlisted_exception_classes_remain_fixed_enums(tmp_path, exception_class):
    trace = (
        '  File "/tmp/action_server/tests/action_server_tests/mcp/'
        f'test_canvas_query_template.py", line 92, in candidate\n'
        f"{exception_class}: PRIVATE_DETAIL"
    )
    summary = load_helper().summarize(junit_file(tmp_path / "known.xml", failure=trace))

    assert availability(summary) == "AVAILABLE"
    assert summary["locations"] == [{"line": 92, "exception_class": exception_class}]
    assert_private(summary, "PRIVATE_DETAIL", "/tmp/action_server")


def test_unknown_exception_class_is_reduced_to_other(tmp_path):
    trace = (
        '  File "/tmp/action_server/tests/action_server_tests/mcp/'
        'test_canvas_query_template.py", line 91, in candidate\n'
        "UntrustedError: PRIVATE_DETAIL"
    )
    summary = load_helper().summarize(
        junit_file(tmp_path / "unknown.xml", failure=trace)
    )

    assert availability(summary) == "AVAILABLE"
    assert summary["locations"] == [{"line": 91, "exception_class": "OTHER"}]
    assert_private(summary, "UntrustedError", "PRIVATE_DETAIL", "/tmp/action_server")


def test_nonfailure_candidate_is_not_needed(tmp_path):
    summary = load_helper().summarize(
        junit_file(tmp_path / "passing.xml", failure=None)
    )

    assert availability(summary) == "NOT_NEEDED"
    assert summary.get("locations", []) == []


def test_unavailable_inputs_are_safe_and_do_not_raise(tmp_path):
    helper = load_helper()
    missing = tmp_path / "missing.xml"
    assert availability(helper.summarize(missing)) == "UNAVAILABLE"

    invalid = tmp_path / "invalid.xml"
    invalid.write_text("<testsuite><failure", encoding="utf-8")
    assert availability(helper.summarize(invalid)) == "UNAVAILABLE"

    unrelated = junit_file(
        tmp_path / "unrelated.xml",
        failure="AssertionError: PRIVATE_DETAIL",
        classname="tests.other.test_unrelated",
    )
    assert availability(helper.summarize(unrelated)) == "UNAVAILABLE"

    oversized = tmp_path / "oversized.xml"
    oversized.write_bytes(b" " * (8 * 1024 * 1024 + 1))
    assert availability(helper.summarize(oversized)) == "UNAVAILABLE"


def test_cli_emits_json_only_and_never_echoes_trace_or_path(tmp_path):
    secret = "PRIVATE_TOKEN_327"
    raw = (
        '  File "/private/runner/action_server/tests/action_server_tests/mcp/'
        'test_canvas_query_template.py", line 123, in candidate\n'
        f"ValueError: {secret} PRIVATE_ASSERTION_TEXT"
    )
    source = junit_file(tmp_path / "private-path-candidate.xml", failure=raw)
    original = source.read_bytes()
    completed = subprocess.run(
        [sys.executable, str(HELPER), str(source)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    summary = json.loads(completed.stdout)
    assert availability(summary) == "AVAILABLE"
    assert_private(
        summary,
        secret,
        "PRIVATE_ASSERTION_TEXT",
        "/private/runner",
        str(source),
    )
    assert completed.stderr == ""
    assert source.read_bytes() == original
    assert list(tmp_path.iterdir()) == [source]
