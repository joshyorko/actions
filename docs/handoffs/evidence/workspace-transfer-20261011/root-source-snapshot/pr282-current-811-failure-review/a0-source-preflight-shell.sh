set -Eeuo pipefail
unset SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE ACTIONS_RUNTIME_RCC_PROVIDER VIRTUAL_ENV PYTHONPATH PYTHONHOME CONDA_PREFIX POETRY_ACTIVE
mkdir -p "$ACTIONS_HOME" "$TMPDIR" "$UV_CACHE_DIR" "$(dirname "$CANVAS_TEMPLATE_PUBLISHED_RECEIPT_PATH")"
poetry_cmd() {
  uv run --no-project --python "${{ matrix.python }}" env -u VIRTUAL_ENV poetry "$@"
}
test "$(poetry_cmd --version)" = "Poetry (version 2.1.1)"
test -x "$(command -v node)"
test -x "$(command -v uv)"
test -f frontend/node_modules/@playwright/test/cli.js
export CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="$(node -p 'require("./frontend/node_modules/@playwright/test").chromium.executablePath()')"
test -x "$CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"
browser_sha256="$(poetry_cmd run python -c 'import hashlib, os; from pathlib import Path; print(hashlib.sha256(Path(os.environ["CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]).read_bytes()).hexdigest())')"
browser_version="$(poetry_cmd run python -c 'import os, subprocess; browser_version = subprocess.run([os.environ["CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"], "--version"], check=True, capture_output=True, text=True, timeout=10).stdout.strip(); assert browser_version, "Browser version is empty"; print(browser_version)')"
poetry_cmd run python -c "import actions.server, pytest"
junit_raw="$TMPDIR/canvas-query-published-core-junit.xml"
junit_safe="$(dirname "$CANVAS_TEMPLATE_PUBLISHED_RECEIPT_PATH")/junit.xml"
receipt_safe="$(dirname "$CANVAS_TEMPLATE_PUBLISHED_RECEIPT_PATH")/published-core-receipt.sanitized.json"
set +e
poetry_cmd run python -m pytest \
  tests/action_server_tests/mcp/test_canvas_query_template.py::test_canvas_template_runs_through_runtime_and_real_browser \
  -q -n 0 \
  --basetemp "$TMPDIR/pytest" \
  --junitxml "$junit_raw" >"$TMPDIR/pytest.log" 2>&1
pytest_status=$?
set -e
source_sha="$(git rev-parse HEAD)"
source_tree="$(git rev-parse 'HEAD^{tree}')"
source_parents="$(git show -s --format=%P HEAD)"
poetry_cmd run python - "$junit_raw" "$junit_safe" "$pytest_status" \
  "$CANVAS_TEMPLATE_PUBLISHED_RECEIPT_PATH" "$receipt_safe" \
  "$source_sha" "$source_tree" "$source_parents" "$browser_sha256" "$browser_version" <<'PY'
import copy
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
import os
from pathlib import Path

raw_path, safe_path, status_text, receipt_path, receipt_safe, source_sha, source_tree, source_parents, browser_sha256, browser_version = sys.argv[1:]
pytest_status = int(status_text)
if not Path(raw_path).is_file():
    raise SystemExit("pytest did not produce JUnit XML")
raw_root = ET.parse(raw_path).getroot()
cases = list(raw_root.iter("testcase"))
expected = "test_canvas_template_runs_through_runtime_and_real_browser"
expected_class = "tests.action_server_tests.mcp.test_canvas_query_template"
suites = list(raw_root.iter("testsuite"))
skipped = sum(len(case.findall("skipped")) for case in cases)
failures = sum(len(case.findall("failure")) for case in cases)
errors = sum(len(case.findall("error")) for case in cases)
expected_counts = {
    "tests": str(len(cases)),
    "skipped": str(skipped),
    "failures": str(failures),
    "errors": str(errors),
}
reported_counts = (
    suites[0].get("tests"),
    suites[0].get("skipped"),
    suites[0].get("failures"),
    suites[0].get("errors"),
) if len(suites) == 1 else ()
counter_nodes = [raw_root, *suites]
counters_match = all(
    node.get(key) == value
    for node in counter_nodes
    for key, value in expected_counts.items()
    if key in node.attrib
) and reported_counts == tuple(expected_counts[key] for key in (
    "tests",
    "skipped",
    "failures",
    "errors",
))
safe_root = ET.Element(
    "testsuite",
    {
        "name": "canvas-template-published-core",
        "tests": str(len(cases)),
        "skipped": str(skipped),
        "failures": str(failures),
        "errors": str(errors),
        "time": raw_root.get("time", "0"),
    },
)
for case in cases:
    case_class = case.get("classname", "")
    case_name = case.get("name", "")
    safe_case = ET.SubElement(
        safe_root,
        "testcase",
        {
            "classname": case_class,
            "name": case_name,
            "time": case.get("time", "0"),
        },
    )
    for tag in ("skipped", "failure", "error"):
        for _ in case.findall(tag):
            ET.SubElement(
                safe_case,
                tag,
                {"message": "Details withheld; inspect the workflow run."},
            )
ET.indent(safe_root)
ET.ElementTree(safe_root).write(
    safe_path, encoding="utf-8", xml_declaration=True
)
junit_ok = (
    len(suites) == 1
    and len(cases) == 1
    and cases[0].get("classname") == expected_class
    and cases[0].get("name") == expected
    and not skipped
    and not failures
    and not errors
    and counters_match
    and reported_counts == ("1", "0", "0", "0")
)
is_sha256 = lambda value: isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
is_git_blob = lambda value: isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None
expected_hashes = {
    "actions": "790b5e45f1a570f4d209879a47007ce94b73aab76c522bd6400867168726b0d2",
    "actions.mcp": "c944de3b044a232143e66edd85ebd342b81b49cd100221689e22908d0dd5f365",
    "actions.mcp._metadata": "c5750e654cb3c1e057705d80e65c4f6a935a3d81e46450d6dbf68d37f45cb48c",
}
expected_parents = source_parents.split()
with zipfile.ZipFile("src/actions/server/templates/zips/canvas-query.zip") as templates:
    expected_resource_sha256 = hashlib.sha256(templates.read("canvas.html")).hexdigest()
def failure_class(error):
    if isinstance(error, UnicodeError):
        return "TEXT_ERROR"
    if isinstance(error, json.JSONDecodeError):
        return "JSON_ERROR"
    for error_type, code in (
        (OSError, "IO_ERROR"), (TypeError, "TYPE_ERROR"),
        (ValueError, "VALUE_ERROR"), (AttributeError, "ATTRIBUTE_ERROR"),
        (KeyError, "KEY_ERROR"),
    ):
        if isinstance(error, error_type):
            return code
    return "OTHER_ERROR"

def write_failure_diagnostics():
    # Reobserve each unchanged predicate independently; never serialize inputs.
    def optional(read):
        try:
            return read()
        except Exception:
            return None

    core = optional(lambda: receipt.get("published_core", {}))
    worker = optional(lambda: core.get("measured_worker", {}))
    runtime = optional(lambda: receipt.get("runtime", {}))
    browser = optional(lambda: receipt.get("browser", {}))
    prefix = optional(lambda: Path(worker.get("worker_prefix", "")))
    modules = optional(lambda: worker.get("modules", {}))
    runtime_args = optional(lambda: runtime.get("process_args", []))
    checks = (
        ('scope', lambda: receipt.get('scope') == 'published-core Runtime/browser acceptance only'),
        ('source_identity', lambda: receipt.get('source') == {'commit': source_sha, 'tree': source_tree, 'parents': expected_parents}),
        ('declared_core_version', lambda: core.get('declared_version') == '1.0.3'),
        ('registry_wheel_digest', lambda: core.get('independently_verified_registry_wheel_sha256') == '8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265'),
        ('worker_core_version', lambda: worker.get('version') == '1.0.3'),
        ('worker_module_hashes', lambda: worker.get('module_hashes') == expected_hashes),
        ('worker_prefix_absolute', lambda: prefix.is_absolute()),
        ('worker_module_inventory', lambda: set(modules) == set(expected_hashes)),
        ('worker_modules_contained', lambda: all((Path(path).is_absolute() and Path(path).is_relative_to(prefix) for path in modules.values()))),
        ('runtime_origin', lambda: Path(runtime.get('module_origin', '')).resolve() == Path('src/actions/server/__init__.py').resolve()),
        ('runtime_module_digest', lambda: runtime.get('module_sha256') == hashlib.sha256(Path('src/actions/server/__init__.py').read_bytes()).hexdigest()),
        ('runtime_args_list', lambda: isinstance(runtime_args, list)),
        ('runtime_args_count', lambda: len(runtime_args) >= 3),
        ('runtime_interpreter_absolute', lambda: Path(runtime_args[0]).is_absolute()),
        ('runtime_module_entry', lambda: runtime_args[1:3] == ['-m', 'actions.server']),
        ('runtime_wrapper_reaped', lambda: runtime.get('wrapper_reaped') is True),
        ('runtime_live_descendants_empty', lambda: runtime.get('live_descendant_pids') == []),
        ('runtime_readers_empty', lambda: runtime.get('active_readers') == []),
        ('runtime_zombies_empty', lambda: runtime.get('zombie_descendant_pids') == []),
        ('runtime_snapshot_complete', lambda: runtime.get('descendant_snapshot_complete') is True),
        ('runtime_reap_complete', lambda: runtime.get('descendant_reap_complete') is True),
        ('runtime_cleanup_errors_empty', lambda: runtime.get('cleanup_errors') == []),
        ('runtime_calls', lambda: receipt.get('runtime_calls') == ['published_core_identity', 'canvas_fixture_search:alpha', 'canvas_fixture_search:unmatched-query']),
        ('template_digest', lambda: receipt.get('template_zip_sha256') == hashlib.sha256(Path('src/actions/server/templates/zips/canvas-query.zip').read_bytes()).hexdigest()),
        ('package_manifest_digest', lambda: receipt.get('production_package_manifest_sha256') == hashlib.sha256(Path('../templates/canvas-query/package.yaml').read_bytes()).hexdigest()),
        ('resource_digest', lambda: receipt.get('built_resource_sha256') == expected_resource_sha256),
        ('browser_status', lambda: browser.get('status') == 'passed'),
        ('browser_explicit_selection', lambda: browser.get('selection') == 'explicit'),
        ('browser_version', lambda: browser.get('version') == browser_version),
        ('browser_preflight_digest_valid', lambda: is_sha256(browser_sha256)),
        ('browser_digest', lambda: browser.get('sha256') == browser_sha256),
        ('browser_selected_path', lambda: Path(browser.get('path', '')).resolve() == Path(os.environ['CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']).resolve()),
        ('browser_temp_removed', lambda: browser.get('temporary_root_removed') is True),
        ('browser_temp_absolute', lambda: Path(browser.get('temporary_root', '')).is_absolute()),
        ('browser_temp_absent', lambda: not Path(browser['temporary_root']).exists()),
        ('browser_playwright_version', lambda: browser.get('playwright_version') == json.loads(Path('frontend/package-lock.json').read_text())['packages']['node_modules/@playwright/test']['version']),
        ('browser_lock_digest', lambda: browser.get('frontend_lock_sha256') == hashlib.sha256(Path('frontend/package-lock.json').read_bytes()).hexdigest()),
        ('limits_list', lambda: isinstance(receipt.get('limits'), list)),
        ('limits_count', lambda: len(receipt['limits']) == 4),
    )
    observations = []
    for code, check in checks:
        try:
            passed = bool(check())
        except Exception as error:
            observations.append({"code": code, "status": "UNAVAILABLE", "failure_class": failure_class(error)})
        else:
            observations.append({"code": code, "status": "PASS" if passed else "FAIL", "failure_class": "NONE"})
    diagnostics = {
        "status": "FAIL",
        "admission": {"pytest": "FAIL" if pytest_status else "PASS", "junit": "PASS" if junit_ok else "FAIL", "receipt": "PASS" if receipt_ok else "FAIL"},
        "receipt_read": {"status": receipt_read_status, "code": receipt_failure_class},
        "counts": {"tests": len(cases), "skipped": skipped, "failures": failures, "errors": errors},
        "checks": observations,
    }
    try:
        Path(receipt_safe).with_name("published-core-failure-diagnostics.json").write_text(
            json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError:
        # Diagnostic retention must not replace the original admission failure.
        print("Canvas failure diagnostics unavailable: IO_ERROR", file=sys.stderr)

receipt_ok = False
receipt = None
receipt_read_status = "MISSING_OR_NON_FILE"
receipt_failure_class = "NONE"
if Path(receipt_path).is_file():
    try:
        receipt_read_status = "READ_ERROR"
        receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
        receipt_read_status = "PARSED"
        core = receipt.get("published_core", {})
        worker = core.get("measured_worker", {})
        runtime = receipt.get("runtime", {})
        browser = receipt.get("browser", {})
        prefix = Path(worker.get("worker_prefix", ""))
        modules = worker.get("modules", {})
        runtime_args = runtime.get("process_args", [])
        receipt_ok = (
            receipt.get("scope") == "published-core Runtime/browser acceptance only"
            and receipt.get("source") == {"commit": source_sha, "tree": source_tree, "parents": expected_parents}
            and core.get("declared_version") == "1.0.3"
            and core.get("independently_verified_registry_wheel_sha256") == "8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265"
            and worker.get("version") == "1.0.3"
            and worker.get("module_hashes") == expected_hashes
            and prefix.is_absolute()
            and set(modules) == set(expected_hashes)
            and all(Path(path).is_absolute() and Path(path).is_relative_to(prefix) for path in modules.values())
            and Path(runtime.get("module_origin", "")).resolve() == Path("src/actions/server/__init__.py").resolve()
            and runtime.get("module_sha256") == hashlib.sha256(Path("src/actions/server/__init__.py").read_bytes()).hexdigest()
            and isinstance(runtime_args, list) and len(runtime_args) >= 3
            and Path(runtime_args[0]).is_absolute() and runtime_args[1:3] == ["-m", "actions.server"]
            and runtime.get("wrapper_reaped") is True
            and runtime.get("live_descendant_pids") == []
            and runtime.get("active_readers") == []
            and runtime.get("zombie_descendant_pids") == []
            and runtime.get("descendant_snapshot_complete") is True
            and runtime.get("descendant_reap_complete") is True
            and runtime.get("cleanup_errors") == []
            and receipt.get("runtime_calls") == ["published_core_identity", "canvas_fixture_search:alpha", "canvas_fixture_search:unmatched-query"]
            and receipt.get("template_zip_sha256") == hashlib.sha256(Path("src/actions/server/templates/zips/canvas-query.zip").read_bytes()).hexdigest()
            and receipt.get("production_package_manifest_sha256") == hashlib.sha256(Path("../templates/canvas-query/package.yaml").read_bytes()).hexdigest()
            and receipt.get("built_resource_sha256") == expected_resource_sha256
            and browser.get("status") == "passed" and browser.get("selection") == "explicit"
            and browser.get("version") == browser_version
            and is_sha256(browser_sha256) and browser.get("sha256") == browser_sha256
            and Path(browser.get("path", "")).resolve() == Path(os.environ["CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]).resolve()
            and browser.get("temporary_root_removed") is True
            and Path(browser.get("temporary_root", "")).is_absolute()
            and not Path(browser["temporary_root"]).exists()
            and browser.get("playwright_version") == json.loads(Path("frontend/package-lock.json").read_text())["packages"]["node_modules/@playwright/test"]["version"]
            and browser.get("frontend_lock_sha256") == hashlib.sha256(Path("frontend/package-lock.json").read_bytes()).hexdigest()
            and isinstance(receipt.get("limits"), list) and len(receipt["limits"]) == 4
        )
    except (OSError, TypeError, ValueError, AttributeError, KeyError) as error:
        receipt_ok = False
        receipt_failure_class = failure_class(error)
if not junit_ok or pytest_status or not receipt_ok:
    write_failure_diagnostics()
    failure_root = ET.Element(
        "testsuite",
        {
            "name": "canvas-template-published-core",
            "tests": "1",
            "skipped": "0",
            "failures": "1",
            "errors": "0",
        },
    )
    failure_case = ET.SubElement(
        failure_root,
        "testcase",
        {"classname": expected_class, "name": expected},
    )
    ET.SubElement(
        failure_case,
        "failure",
        {"message": "Published Core/browser acceptance failed verification."},
    )
    ET.indent(failure_root)
    ET.ElementTree(failure_root).write(
        safe_path, encoding="utf-8", xml_declaration=True
    )
    raise SystemExit(
        f"Published Core acceptance did not produce one verified pass "
        f"(pytest={pytest_status}, tests={len(cases)}, skipped={skipped}, "
        f"failures={failures}, errors={errors}, receipt_valid={receipt_ok})"
    )

redactions = [
    (os.environ.get("GITHUB_WORKSPACE"), "<checkout>"),
    (os.environ.get("RUNNER_TEMP"), "<runner-temp>"),
    (os.environ.get("ACTIONS_HOME"), "<actions-home>"),
    (os.environ.get("TMPDIR"), "<task-tmp>"),
    (os.environ.get("UV_CACHE_DIR"), "<uv-cache>"),
    (str(Path.home()), "<runner-home>"),
]
redactions = sorted(
    ((prefix, replacement) for prefix, replacement in redactions if prefix),
    key=lambda item: len(item[0]),
    reverse=True,
)

def redact(value):
    if isinstance(value, str):
        for prefix, replacement in redactions:
            value = value.replace(prefix, replacement)
        return value
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value

Path(receipt_safe).write_text(
    json.dumps(redact(copy.deepcopy(receipt)), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
