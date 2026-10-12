"""Synthetic admission controls only; no Runtime, browser or registry acquisition."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

PATH = Path(__file__).with_name("canvas-native-public-runner-v5.py")
spec = importlib.util.spec_from_file_location("pr305_runner_controls", PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def cleanup():
    return dict(
        wrapper_reaped=True,
        descendant_snapshot_complete=True,
        descendant_reap_complete=True,
        cleanup_errors=[],
        active_readers=[],
        observed_live_children=[],
        observed_zombie_children=[],
    )


@pytest.mark.parametrize(
    "field",
    [
        "wrapper_reaped",
        "descendant_snapshot_complete",
        "descendant_reap_complete",
        "cleanup_errors",
        "active_readers",
        "observed_live_children",
        "observed_zombie_children",
    ],
)
def test_actual_final_cleanup_validator_rejects_failed_state(field):
    value = cleanup()
    runner.admit_cleanup(value)
    value[field] = False if isinstance(value[field], bool) else ["poison"]
    with pytest.raises(AssertionError):
        runner.admit_cleanup(value)


@pytest.mark.parametrize("poison", ["skip", "count", "name", "failure"])
def test_actual_junit_validator_rejects_poison(tmp_path, poison):
    path = tmp_path / "junit.xml"
    name = runner.TEST.split("::")[1]

    def report(count=1, name=name, child=""):
        return f'<testsuites><testsuite tests="{count}" failures="0" errors="0" skipped="0"><testcase name="{name}">{child}</testcase></testsuite></testsuites>'

    path.write_text(report())
    assert runner.admit_junit(path)["passed"] == 1
    path.write_text(
        report(count=2)
        if poison == "count"
        else report(name="other")
        if poison == "name"
        else report(child="<skipped/>" if poison == "skip" else "<failure/>")
    )
    with pytest.raises(AssertionError):
        runner.admit_junit(path)


def bridge_record():
    from action_server_tests.mcp import test_mcp_apps_authoring as bridge

    return {
        "schema_version": 3,
        "core_mode": "published",
        "published_core": {
            "mode": "published",
            "declared_version": "1.0.3",
            "independently_verified_registry_wheel_sha256": "8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265",
            "whole_wheel_authenticated": False,
            "cold_registry_acquisition": False,
            "measured_members": list(bridge.PUBLISHED_CORE_MODULE_SHA256),
        },
        "worker": {
            "version": "1.0.3",
            "module_hashes": dict(bridge.PUBLISHED_CORE_MODULE_SHA256),
            "worker_prefix": "/synthetic/unit/prefix",
            "modules": {
                name: "/synthetic/unit/prefix/" + name + ".py"
                for name in bridge.PUBLISHED_CORE_MODULE_SHA256
            },
        },
        "browser": {
            "selection": "explicit",
            "path": str(runner.BROWSER),
            "sha256": runner.BROWSER_SHA,
            "playwright_version": "1.62.1",
            "temporary_root_removed": True,
        },
        "cache": {
            "outside_synchronized_package": True,
            "source_root": "/synthetic/unit/source",
            "build_root": "/synthetic/unit/build",
            "uv_cache": "/synthetic/unit/cache",
        },
        "canvas_resource": {
            "uri": bridge.CANVAS_RESOURCE_URI,
            "mime_type": "text/html;profile=mcp-app",
        },
        "persisted_run_records": [
            {
                "run_id": str(i),
                "status": "passed",
                "status_code": 2,
                "action_name": name,
            }
            for i, name in enumerate(
                ["canvas_fixture_search"] * 2
                + ["canvas_fixture_artifact_status"] * 2
                + ["canvas_fixture_worker_provenance"]
            )
        ],
        "runtime_call_observations": [
            {"caller": "python-mcp-client", "tool": name, "result": "passed"}
            for name in [
                "canvas_fixture_search",
                "canvas_fixture_artifact_status",
                "canvas_fixture_worker_provenance",
            ]
        ]
        + [
            {"caller": "playwright-browser", "tool": name, "result": "passed"}
            for name in ["canvas_fixture_search", "canvas_fixture_artifact_status"]
        ],
    }


@pytest.mark.parametrize(
    "poison",
    [
        "candidate",
        "mode",
        "localwheel",
        "Core",
        "member",
        "modules",
        "calls",
        "browser",
        "selection",
        "cache",
        "Run",
        "resource",
    ],
)
def test_actual_bridge_validator_rejects_poison(poison):
    receipt = bridge_record()
    runner.admit_bridge(receipt)
    if poison == "candidate":
        receipt["actions_core_wheel"] = {"path": "fake"}
    elif poison == "mode":
        receipt["published_core"]["mode"] = "candidate"
    elif poison == "localwheel":
        receipt["published_core"]["path"] = "/fake/candidate.whl"
    elif poison == "modules":
        receipt["worker"]["modules"] = {}
    elif poison == "calls":
        receipt["runtime_call_observations"][0]["caller"] = "fabricated"
    elif poison == "Core":
        receipt["worker"]["version"] = "0.0.0"
    elif poison == "member":
        receipt["worker"]["module_hashes"]["actions"] = "poison"
    elif poison == "browser":
        receipt["browser"]["sha256"] = "poison"
    elif poison == "selection":
        receipt["browser"]["selection"] = "implicit"
    elif poison == "cache":
        receipt["cache"]["uv_cache"] = receipt["cache"]["source_root"] + "/cache"
    elif poison == "Run":
        receipt["persisted_run_records"].pop()
    else:
        receipt["canvas_resource"]["mime_type"] = "text/plain"
    with pytest.raises(AssertionError):
        runner.admit_bridge(receipt)


def test_actual_source_admission_rejects_wrong_commit(monkeypatch):
    assert runner.admit_source()["producer_entries"] == 268
    monkeypatch.setattr(runner, "HEAD", "ba85aac7324ea4463bfba8c5f8586e27706dc2fe")
    with pytest.raises(AssertionError):
        runner.admit_source()


def test_verified_byte_import_rejects_helper_poison_before_execution(
    tmp_path, monkeypatch
):
    copy = tmp_path / "frozen-helpers"
    shutil.copytree(runner.OWNED / "frozen-helpers", copy)
    monkeypatch.setattr(runner, "OWNED", tmp_path)
    helper = runner.load_helper("outer_owner")
    assert Path(helper.__file__).parent == copy
    target = copy / runner.HELPERS["outer_owner"][0]
    target.chmod(0o600)
    target.write_text('raise RuntimeError("must never execute")')
    with pytest.raises(AssertionError):
        runner.load_helper("outer_owner")


def test_actual_outer_helper_self_launch_uses_pinned_snapshot(monkeypatch, tmp_path):
    helper = runner.load_helper("outer_owner")
    observed = []

    class Child:
        returncode = 0

        def communicate(self, payload, timeout):
            observed.append((json.loads(payload), timeout))
            return json.dumps(
                {
                    "returncode": 0,
                    "stdout": "retained stdout",
                    "stderr": "retained stderr",
                    "cleanup_disposition": "clean_no_descendants",
                    "reaped_descendants": 0,
                    "timed_out": False,
                    "unexpected_live_descendants": False,
                }
            ), ""

    def launch(argv, **kwargs):
        assert argv[1] == helper.__file__ and argv[2] == "--_supervisor"
        assert runner.sha(argv[1]) == runner.HELPERS["outer_owner"][1]
        return Child()

    monkeypatch.setattr(helper.subprocess, "Popen", launch)
    command = ["python", "synthetic-child"]
    result = helper.run_owned_process(
        command,
        cwd=tmp_path,
        env={"TEST": "owned"},
        timeout_seconds=600,
        cleanup_grace_seconds=10,
    )
    assert (
        result.args == command
        and result.stdout == "retained stdout"
        and result.stderr == "retained stderr"
    )
    assert observed == [
        (
            {
                "command": command,
                "cwd": str(tmp_path),
                "env": {"TEST": "owned"},
                "timeout_seconds": 600,
                "cleanup_grace_seconds": 10,
            },
            645,
        )
    ]


def test_worker_cleanup_failure_preserves_primary_and_failed_receipt(
    tmp_path, monkeypatch
):
    # pytest.main never enters the Canvas node. This tests the actual worker's
    # primary-error/cleanup-error control flow without starting a consumer.
    monkeypatch.setattr(pytest, "main", lambda argv, **kwargs: 1)
    with pytest.raises(AssertionError) as failure:
        runner.worker(tmp_path)
    assert any("Owned cleanup also failed" in note for note in failure.value.__notes__)
    assert (
        json.loads((tmp_path / "runtime-cleanup.json").read_text())["status"]
        == "unavailable"
    )


def test_actual_owned_callback_preserves_primary_when_helper_posthash_fails(tmp_path):
    import ast
    import subprocess
    from types import SimpleNamespace

    # Compile the actual nested callback from the frozen runner; only its outer
    # owner and receipt I/O bindings are service-free substitutes.
    tree = ast.parse(PATH.read_text())
    worker = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "worker"
    )
    callback = next(
        n
        for n in worker.body
        if isinstance(n, ast.FunctionDef) and n.name == "owned_command"
    )
    primary = subprocess.CalledProcessError(
        7, ["node", "synthetic"], "retained stdout", "retained stderr"
    )

    def owner(*args, **kwargs):
        raise primary

    checks = []

    def verify():
        checks.append(True)
        if len(checks) == 2:
            raise AssertionError("secondary helper hash mismatch")

    namespace = dict(runner.__dict__)
    namespace.update(
        owner=SimpleNamespace(_run_owned_process_tree=owner),
        attempt=tmp_path,
        command_receipts=[],
        capture=lambda: None,
        verify_helpers=verify,
    )
    exec(
        compile(ast.Module(body=[callback], type_ignores=[]), str(PATH), "exec"),
        namespace,
    )
    with pytest.raises(subprocess.CalledProcessError) as failure:
        namespace["owned_command"](
            ["node", "synthetic"], cwd=tmp_path, env={"CONTROL": "only"}, timeout=180
        )
    assert failure.value is primary
    assert any("secondary helper hash mismatch" in note for note in primary.__notes__)
    assert (tmp_path / "command-1-stdout.log").read_text() == "retained stdout"
    assert (tmp_path / "command-1-stderr.log").read_text() == "retained stderr"


@pytest.mark.parametrize(
    "poison",
    [
        "missing_alive",
        "missing_cancel",
        "alive",
        "cancel_false",
        "alive_wrongtype",
        "cancel_wrongtype",
        "duplicate",
        "stale",
        "missing_marker",
        "malformed_marker",
    ],
)
def test_actual_observer_final_validator_requires_explicit_stopped_final(poison):
    final = {
        "outcome": "ready",
        "exception": None,
        "sampler_cancelled": True,
        "sampler_alive": False,
    }
    reports = [
        {"elapsed_seconds": 20, "snapshot": {"owned_process": "synthetic"}},
        dict(final),
    ]
    assert runner.admit_observer(reports) == final
    if poison == "missing_alive":
        reports[-1].pop("sampler_alive")
    elif poison == "missing_cancel":
        reports[-1].pop("sampler_cancelled")
    elif poison == "alive":
        reports[-1]["sampler_alive"] = True
    elif poison == "cancel_false":
        reports[-1]["sampler_cancelled"] = False
    elif poison == "alive_wrongtype":
        reports[-1]["sampler_alive"] = 0
    elif poison == "cancel_wrongtype":
        reports[-1]["sampler_cancelled"] = 1
    elif poison == "duplicate":
        reports.append(dict(final))
    elif poison == "stale":
        reports.append({"elapsed_seconds": 80, "snapshot": {}})
    elif poison == "missing_marker":
        reports[-1] = {"snapshot": {}}
    else:
        reports[-1]["elapsed_seconds"] = 80
    with pytest.raises(AssertionError):
        runner.admit_observer(reports)


@pytest.mark.parametrize(
    "poison", ["missing_alive", "wrongtype_alive", "duplicate", "stale"]
)
def test_retained_predecessor_guard_reproduces_gap_successor_rejects(poison):
    import ast

    predecessor = PATH.with_name("canvas-native-public-runner.py")
    assert (
        runner.sha(predecessor)
        == "0feee8b8c911f94496323d10dc4a92cf93cfe2ce566b54efc29e3b771b8e56d5"
    )
    worker = next(
        n
        for n in ast.parse(predecessor.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == "worker"
    )
    guards = [
        n
        for n in ast.walk(worker)
        if isinstance(n, ast.Assert) and "observations" in ast.unparse(n.test)
    ]
    assert len(guards) == 2
    final = {
        "outcome": "ready",
        "exception": None,
        "sampler_cancelled": True,
        "sampler_alive": False,
    }
    reports = [dict(final)]
    if poison == "missing_alive":
        reports[-1].pop("sampler_alive")
    elif poison == "wrongtype_alive":
        reports[-1]["sampler_alive"] = 0
    elif poison == "duplicate":
        reports.append(dict(final))
    else:
        reports.append({"elapsed_seconds": 80, "snapshot": {}})
    # Execute retained actual worker assertions: each poison was admitted there.
    exec(
        compile(ast.Module(body=guards, type_ignores=[]), str(predecessor), "exec"),
        {"observations": reports},
    )
    with pytest.raises(AssertionError):
        runner.admit_observer(reports)


@pytest.fixture(scope="module")
def collected_canvas_item():
    class Inspection:
        def pytest_collection_finish(self, session):
            self.items = list(session.items)

    inspection = Inspection()
    code = pytest.main(
        [runner.TEST, "--collect-only", "-q", "-n0"], plugins=[inspection]
    )
    assert code == 0 and len(inspection.items) == 1
    return inspection.items[0]


def test_real_collected_public_boundary_red_green_and_restoration(
    collected_canvas_item, monkeypatch, tmp_path
):
    import subprocess
    from action_server_tests.mcp import test_mcp_apps_authoring as preimport

    item = collected_canvas_item
    module = item.module
    assert module is not preimport
    assert module.CANVAS_OWNED_RUNNER is None
    monkeypatch.setenv("ACTIONS_CANVAS_CORE_MODE", "published")
    calls = []

    def callback(command, *, cwd, env, timeout):
        calls.append(dict(command=command, cwd=str(cwd), env=env, timeout=timeout))
        return subprocess.CompletedProcess(command, 0, "unit stdout", "unit stderr")

    monkeypatch.setattr(preimport, "CANVAS_OWNED_RUNNER", callback)
    assert callable(preimport.CANVAS_OWNED_RUNNER)
    with pytest.raises(AssertionError, match="requires an owned runner"):
        module._canvas_core_mode()
    plugin = runner.CollectedOwnership(callback)
    assert (
        pytest.main([runner.TEST, "--collect-only", "-q", "-n0"], plugins=[plugin]) == 0
    )
    assert len(plugin.installed) == 1 and plugin.installed[0][0] is module
    try:
        assert module._canvas_core_mode() == "published"
        env = {"UNIT": "owned"}
        command = ["synthetic", "no-product-execution"]
        completed = module._canvas_command(
            command, cwd=tmp_path, env=env, timeout=180, mode="published"
        )
        assert completed.args == command
        assert completed.stdout == "unit stdout" and completed.stderr == "unit stderr"
        assert calls == [dict(command=command, cwd=str(tmp_path), env=env, timeout=180)]
    finally:
        plugin.restore()
    assert module.CANVAS_OWNED_RUNNER is None
    assert callable(preimport.CANVAS_OWNED_RUNNER)
    with pytest.raises(AssertionError, match="requires an owned runner"):
        module._canvas_core_mode()
    evidence = dict(
        phase="REAL_COLLECTION_ONLY_FAKE_CONTROLLER_NO_CONSUMER",
        nodeid=item.nodeid,
        collected_module=module.__name__,
        preimport_module=preimport.__name__,
        same_module=False,
        source_sha256=runner.sha(module.__file__),
        predecessor_hook_missing_RED=True,
        collected_public_boundary_GREEN=True,
        exact_CompletedProcess_forwarding=True,
        collected_owner_restored=True,
    )
    (runner.OWNED / "v5-real-collection-controls.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )


@pytest.mark.parametrize("poison", ["node", "module", "count", "hash", "existing_hook"])
def test_collected_ownership_binding_poison_refuses_before_mutation(
    collected_canvas_item, monkeypatch, poison
):
    from types import SimpleNamespace

    item = collected_canvas_item
    module = item.module
    selected = [item]
    if poison == "node":
        selected = [SimpleNamespace(nodeid="wrong-node", module=module)]
    elif poison == "module":
        selected = [
            SimpleNamespace(
                nodeid=item.nodeid, module=SimpleNamespace(__file__="/wrong/module.py")
            )
        ]
    elif poison == "count":
        selected.append(item)
    elif poison == "hash":
        monkeypatch.setattr(runner, "sha", lambda path: "poison")
    else:
        monkeypatch.setattr(module, "CANVAS_OWNED_RUNNER", lambda: None)
    before = module.CANVAS_OWNED_RUNNER
    plugin = runner.CollectedOwnership(lambda *args, **kwargs: None)
    with pytest.raises(AssertionError):
        plugin.pytest_collection_modifyitems(None, None, selected)
    assert plugin.installed == []
    assert module.CANVAS_OWNED_RUNNER is before


def test_returned_outer_cleanup_retained_before_primary_nonzero(tmp_path):
    import subprocess

    command = ["synthetic-child"]
    completed = subprocess.CompletedProcess(
        command, 7, "primary stdout", "primary stderr"
    )
    completed.cleanup_disposition = "clean_no_descendants"
    completed.reaped_descendants = 0
    with pytest.raises(subprocess.CalledProcessError) as failure:
        runner.record_outer_completion(completed, tmp_path)
    assert failure.value.cmd == command
    assert failure.value.output == "primary stdout"
    assert failure.value.stderr == "primary stderr"
    receipt = json.loads((tmp_path / "outer-cleanup.json").read_text())
    assert receipt["cleanup_disposition"] == "clean_no_descendants"
    assert receipt["reaped_descendants"] == 0
    assert receipt["command_returncode"] == 7
    assert (tmp_path / "worker-stdout.log").read_text() == "primary stdout"
    assert (tmp_path / "worker-stderr.log").read_text() == "primary stderr"


def test_actual_worker_restores_installed_collected_hook_after_primary_failure(
    collected_canvas_item, monkeypatch, tmp_path
):
    from actions.server._selftest import ActionServerProcess

    item = collected_canvas_item
    module = item.module
    assert module.CANVAS_OWNED_RUNNER is None
    original_start = ActionServerProcess.start
    primary = RuntimeError("synthetic collected-hook primary; no product execution")

    def fail_after_collection(argv, *, plugins):
        assert argv[0] == runner.TEST and len(plugins) == 1
        plugins[0].pytest_collection_modifyitems(None, None, [item])
        assert callable(module.CANVAS_OWNED_RUNNER)
        raise primary

    monkeypatch.setattr(pytest, "main", fail_after_collection)
    with pytest.raises(RuntimeError) as failure:
        runner.worker(tmp_path)
    assert failure.value is primary
    assert any("Runtime ownership unavailable" in note for note in primary.__notes__)
    assert module.CANVAS_OWNED_RUNNER is None
    assert ActionServerProcess.start is original_start
    receipt = json.loads((tmp_path / "runtime-cleanup.json").read_text())
    assert receipt["status"] == "unavailable" and receipt["cleanup"] is None


@pytest.mark.parametrize(
    "selector",
    [
        None,
        "^official bridge renders a real Runtime Action result$",
        ".*",
        r"^\s*host-harness\.spec\.ts official MCP Apps bridge handles fixture calls and host context lifecycle$",
    ],
)
def test_actual_locked_driver_list_discovery_gate(selector, monkeypatch):
    import subprocess
    from types import SimpleNamespace

    original = runner.load_helper("browser_owner")
    completed = []

    def trace(command, **kwargs):
        result = original._run_owned_process_tree(command, **kwargs)
        completed.append(result)
        return result

    monkeypatch.setattr(
        runner,
        "load_helper",
        lambda name: SimpleNamespace(_run_owned_process_tree=trace),
    )
    if selector is None:
        result = runner.discover_canvas_case()
        assert result["specs"] == [
            "official bridge renders a real Runtime Action result"
        ]
        assert result["phase"] == "LIST_ONLY_NO_BROWSER_OR_TESTCASE"
        (runner.OWNED / "v5-driver-discovery-GREEN.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
    elif selector.startswith("^official"):
        with pytest.raises(subprocess.CalledProcessError) as failure:
            runner.discover_canvas_case(selector)
        report = json.loads(failure.value.stdout)
        assert (
            report["suites"] == []
            and report["errors"][0]["message"] == "Error: No tests found"
        )
        (runner.OWNED / "v5-driver-discovery-oldzero.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    else:
        with pytest.raises(
            AssertionError,
            match="Discovery must select exactly the existing Runtime case",
        ):
            runner.discover_canvas_case(selector)
        assert len(completed) == 1
        report = json.loads(completed[0].stdout)
        specs = [s for suite in report["suites"] for s in suite.get("specs", [])]
        if selector == ".*":
            assert len(specs) == 2
            label = "broadtwo"
        else:
            assert [s["title"] for s in specs] == [
                "official MCP Apps bridge handles fixture calls and host context lifecycle"
            ]
            label = "wrongfixture"
        (runner.OWNED / ("v5-driver-discovery-" + label + ".json")).write_text(
            json.dumps(report, indent=2) + "\n"
        )


@pytest.mark.parametrize("poison", ["absent", "wrong"])
def test_actual_frontend_dependency_guard_refuses_unmeasured_tree(
    tmp_path, monkeypatch, poison
):
    prepared = tmp_path / "measured-prepared"
    prepared.mkdir()
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    actual = frontend / "node_modules"
    monkeypatch.setattr(runner, "PREPARED_NODE_MODULES", prepared)
    actual.symlink_to(prepared, target_is_directory=True)
    runner.assert_prepared_frontend(frontend)
    actual.unlink()
    if poison == "wrong":
        wrong = tmp_path / "unmeasured"
        wrong.mkdir()
        actual.symlink_to(wrong, target_is_directory=True)
    with pytest.raises(AssertionError, match="Actual frontend dependencies"):
        runner.assert_prepared_frontend(frontend)


def browser_report(*, launch=None):
    result = {"status": "passed", "retry": 0, "errors": [], "stderr": []}
    if launch:
        result["stderr"] = [{"text": launch}]
    return {
        "errors": [],
        "stats": {"expected": 1, "unexpected": 0, "skipped": 0, "flaky": 0},
        "suites": [
            {
                "title": "host-harness.spec.ts",
                "specs": [
                    {
                        "file": "host-harness.spec.ts",
                        "title": "official bridge renders a real Runtime Action result",
                        "tests": [{"results": [result]}],
                    }
                ],
            }
        ],
    }


def compiled_owned_callback(tmp_path, completed):
    import ast
    from types import SimpleNamespace

    tree = ast.parse(PATH.read_text())
    worker = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "worker"
    )
    callback = next(
        n
        for n in worker.body
        if isinstance(n, ast.FunctionDef) and n.name == "owned_command"
    )
    observed = []

    def owner(command, **kwargs):
        observed.append((command, kwargs))
        return completed

    namespace = dict(runner.__dict__)
    namespace.update(
        owner=SimpleNamespace(_run_owned_process_tree=owner),
        attempt=tmp_path,
        command_receipts=[],
        capture=lambda: None,
        verify_helpers=lambda: None,
    )
    exec(
        compile(ast.Module(body=[callback], type_ignores=[]), str(PATH), "exec"),
        namespace,
    )
    return namespace["owned_command"], observed, namespace["command_receipts"]


def test_postguard_failure_retains_returned_streams(tmp_path):
    import subprocess

    command = [str(runner.NODE), "/synthetic/cli.js", "test", "--reporter", "json"]
    stdout = json.dumps(browser_report())
    stderr = "synthetic CLI diagnostic without a browser launch"
    completed = subprocess.CompletedProcess(command, 0, stdout, stderr)
    callback, observed, records = compiled_owned_callback(tmp_path, completed)
    env = {"DEBUG": "pw:browser", "CONTROL": "no product execution"}
    with pytest.raises(
        AssertionError, match="Actual Playwright launch path not observed"
    ) as failure:
        callback(command, cwd=tmp_path, env=env, timeout=180)
    assert type(failure.value) is AssertionError
    assert records[0]["returncode"] == 0 and records[0]["status"] == "failed"
    assert (tmp_path / "command-1-stdout.log").read_text() == stdout
    assert (tmp_path / "command-1-stderr.log").read_text() == stderr
    assert observed == [(command, {"cwd": tmp_path, "env": env, "timeout": 180})]


def test_json_captured_test_stderr_is_actual_launch_evidence(tmp_path):
    import subprocess

    command = [str(runner.NODE), "/synthetic/cli.js", "test", "--reporter", "json"]
    launch = "pw:browser <launching> " + str(runner.BROWSER) + " --synthetic-flags"
    stdout = json.dumps(browser_report(launch=launch))
    completed = subprocess.CompletedProcess(command, 0, stdout, "")
    callback, observed, records = compiled_owned_callback(tmp_path, completed)
    env = {"DEBUG": "pw:browser", "CONTROL": "no product execution"}
    assert callback(command, cwd=tmp_path, env=env, timeout=180) is completed
    assert observed == [(command, {"cwd": tmp_path, "env": env, "timeout": 180})]
    assert records[0]["actual_browser_launch_path"] == str(runner.BROWSER)
    assert (tmp_path / "command-1-stdout.log").read_text() == stdout


@pytest.mark.parametrize(
    "poison",
    [
        None,
        "outer",
        "buffer",
        "split",
        "wrong_path",
        "missing",
        "skip",
        "count",
        "name",
        "file",
        "retry",
        "errors",
        "result_error",
        "malformed_stderr",
        "malformed_buffer",
        "malformed_json",
    ],
)
def test_actual_launch_parser_requires_original_exact_case_and_path(poison):
    import base64
    import copy
    import subprocess

    report = browser_report(
        launch="pw:browser <launching> " + str(runner.BROWSER) + " --flags"
    )
    result = report["suites"][0]["specs"][0]["tests"][0]["results"][0]
    stderr = ""
    if poison == "outer":
        stderr = result["stderr"][0]["text"]
        result["stderr"] = []
    elif poison == "buffer":
        result["stderr"] = [
            {"buffer": base64.b64encode(result["stderr"][0]["text"].encode()).decode()}
        ]
    elif poison == "split":
        text = result["stderr"][0]["text"]
        result["stderr"] = [{"text": text[:20]}, {"text": text[20:]}]
    elif poison == "wrong_path":
        result["stderr"][0]["text"] = "pw:browser <launching> /wrong/browser --flags"
    elif poison == "missing":
        result["stderr"] = []
    elif poison == "skip":
        report["stats"]["skipped"] = 1
    elif poison == "count":
        report["suites"][0]["specs"].append(
            copy.deepcopy(report["suites"][0]["specs"][0])
        )
    elif poison == "name":
        report["suites"][0]["specs"][0]["title"] = "wrong case"
    elif poison == "file":
        report["suites"][0]["specs"][0]["file"] = "other.spec.ts"
    elif poison == "retry":
        result["retry"] = 1
    elif poison == "errors":
        report["errors"] = [{"message": "report failed"}]
    elif poison == "result_error":
        result["error"] = {"message": "result failed"}
    elif poison == "malformed_stderr":
        result["stderr"] = [{"text": 1}]
    elif poison == "malformed_buffer":
        result["stderr"] = [{"buffer": "not-base64!"}]
    stdout = "not JSON" if poison == "malformed_json" else json.dumps(report)
    completed = subprocess.CompletedProcess(
        [str(runner.NODE), "owned CLI"], 0, stdout, stderr
    )
    if poison in (None, "outer", "buffer", "split"):
        assert runner.admit_browser_launch(completed) == (
            "outer_stderr" if poison == "outer" else "named_case_result_stderr"
        )
    else:
        with pytest.raises((AssertionError, ValueError)):
            runner.admit_browser_launch(completed)


def test_postguard_primary_and_completed_bytes_survive_secondary_hash_failure(tmp_path):
    import subprocess

    command = [str(runner.NODE), "/synthetic/cli.js", "test", "--reporter", "json"]
    stdout = json.dumps(browser_report())
    completed = subprocess.CompletedProcess(command, 0, stdout, "completed stderr")
    callback, _, _ = compiled_owned_callback(tmp_path, completed)
    primary = AssertionError("synthetic postcondition primary; no product execution")
    checks = []

    def reject(completed):
        raise primary

    def verify():
        checks.append(True)
        if len(checks) == 2:
            raise AssertionError("secondary helper mismatch")

    callback.__globals__["admit_browser_launch"] = reject
    callback.__globals__["verify_helpers"] = verify
    with pytest.raises(AssertionError) as failure:
        callback(command, cwd=tmp_path, env={"CONTROL": "only"}, timeout=180)
    assert failure.value is primary
    assert any("secondary helper mismatch" in note for note in primary.__notes__)
    assert (tmp_path / "command-1-stdout.log").read_text() == stdout
    assert (tmp_path / "command-1-stderr.log").read_text() == "completed stderr"
