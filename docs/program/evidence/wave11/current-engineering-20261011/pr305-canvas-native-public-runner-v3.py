"""One reviewed frozen-only Canvas consumer attempt; default is preflight only."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import types
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path("/workspace/engineering/pr305")
OWNED = Path("/workspace/actions-cloud/receipts/pr305-runner")
HEAD = "14c1c1965314b192c4118c3281f5539d29f0aa6f"
TREE = "b95b352dd20cec016ea5dac204b81eeb331a8b3d"
PRODUCER = "92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e"
NATIVE = Path("/workspace/engineering/pr310-runner-qualification-owned")
BROWSER = Path(
    "/workspace/actions-cloud/cache/playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"
)
BROWSER_SHA = "e11fc9ce65c96313476f7ee9844b6fb6a9220fb048693cfe9eee00acf4170a9f"
NODE = Path(
    "/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/node"
)
PREPARED_NODE_MODULES = Path(
    "/workspace/engineering/pr310/action_server/frontend/node_modules"
)
TEST = "tests/action_server_tests/mcp/test_mcp_apps_authoring.py::test_canvas_view_calls_public_action_through_runtime_bridge"
# The outer controller imports only the committed test harness from this path.
# Public Core imports are measured in the separate Runtime-managed worker.
sys.path.insert(0, str(REPO / "action_server/tests"))
HELPERS = {
    "browser_owner": (
        "test_canvas_query_template.py",
        "edc7ccfb85bd20bc89775f73ee45039bcf4c501fe6dae9a5ebd81a80e16eda4e",
    ),
    "outer_owner": (
        "verify_dakota_rcc_acceptance.py",
        "60acf72569c2dfe5748f45ac6c3bf4cc8621e28955a4afa3dbf2f417d7290659",
    ),
    "startup_observer": (
        "native_startup_diagnostics.py",
        "943d3882e753f5d6ce31330b3783248c050c2c7eb8cf6ab1bedada020799d76c",
    ),
    "native_inventory": (
        "write_native_artifact_manifest.py",
        "aaa6855bc6c0bccc41933703fbdb2e58d9f25a118a651d254a7dce34e5fd113b",
    ),
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_helper(name):
    filename, expected = HELPERS[name]
    path = OWNED / "frozen-helpers" / filename
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    module = types.ModuleType("pr305_" + name)
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def verify_helpers():
    for filename, expected in HELPERS.values():
        assert sha(OWNED / "frozen-helpers" / filename) == expected


class CollectedOwnership:
    """Bind only the permitted ownership hook on the actual collected module."""

    def __init__(self, callback):
        self.callback = callback
        self.installed = []

    def pytest_collection_modifyitems(self, session, config, items):
        assert len(items) == 1, "require exactly one selected Canvas node"
        item = items[0]
        assert item.nodeid == TEST, "unexpected Canvas node"
        module = item.module
        expected = REPO / "action_server" / TEST.split("::")[0]
        assert (
            Path(module.__file__).resolve() == expected.resolve()
        ), "unexpected collected module file"
        assert (
            sha(expected)
            == "0e7d44ebfdfee63dc3e2688a0fa5d677d97bc1138217d4c3e192c72fe63fad08"
        ), "collected source hash changed"
        assert module._canvas_core_mode.__globals__ is module.__dict__
        assert module._canvas_command.__globals__ is module.__dict__
        assert module.CANVAS_OWNED_RUNNER is None, "unexpected existing ownership hook"
        self.installed.append((module, module.CANVAS_OWNED_RUNNER))
        module.CANVAS_OWNED_RUNNER = self.callback

    def restore(self):
        for module, original in self.installed:
            module.CANVAS_OWNED_RUNNER = original


def record_outer_completion(completed, attempt):
    write(
        attempt / "outer-cleanup.json",
        {
            "command": completed.args,
            "command_returncode": completed.returncode,
            "cleanup_disposition": completed.cleanup_disposition,
            "reaped_descendants": completed.reaped_descendants,
            "scope": "outer supervisor observed adopted command descendants only; not Runtime internal cleanup admission",
        },
    )
    (attempt / "worker-stdout.log").write_text(completed.stdout, encoding="utf-8")
    (attempt / "worker-stderr.log").write_text(completed.stderr, encoding="utf-8")
    completed.check_returncode()


def admit_source():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()

    assert git("rev-parse", "HEAD") == HEAD
    assert git("rev-parse", "HEAD^{tree}") == TREE
    assert not git("status", "--porcelain")
    inventory = Path(
        "/workspace/actions-cloud/receipts/pr305-readonly-proposal/simulated-union-producer-and-selected-inventory.json"
    )
    assert (
        sha(inventory)
        == "0ca58af2be51f25d3c76077ce3fa56d170b3f1417a8fce416edb175b3ef6a9f8"
    )
    declared = json.loads(inventory.read_text())
    assert (
        len(declared["strict_entries"]) == 268
        and len(declared["selected_entries"]) == 5
    )
    for entry in declared["strict_entries"] + declared["selected_entries"]:
        expected = " ".join(entry["producer"][k] for k in ("mode", "kind", "blob"))
        current = git("ls-tree", HEAD, "--", entry["path"]).split("\t")[0]
        assert current == expected, entry["path"]
    checkpoint = Path(
        "/workspace/actions-cloud/receipts/pr305-readonly-proposal/frozen-source-checkpoint-receipt.json"
    )
    assert (
        sha(checkpoint)
        == "d68e265a2bbbb28cc54cfed511d2e0bbc3cdaeb71a93ac08ef1d7c74aeaae60e"
    )
    receipt = json.loads(checkpoint.read_text())
    allowed = set(
        receipt["full_inventory"]["changed_original"]
        + receipt["full_inventory"]["added"]
    )
    assert set(git("diff", "--name-only", PRODUCER, HEAD).splitlines()) == allowed
    return {
        "head": HEAD,
        "tree": TREE,
        "native_producer": PRODUCER,
        "producer_entries": 268,
        "selected_entries": 5,
    }


def admit_cleanup(cleanup):
    for key in (
        "wrapper_reaped",
        "descendant_snapshot_complete",
        "descendant_reap_complete",
    ):
        assert cleanup[key] is True, key
    for key in (
        "cleanup_errors",
        "active_readers",
        "observed_live_children",
        "observed_zombie_children",
    ):
        assert cleanup[key] == [], key


def admit_observer(observations):
    assert observations, "missing startup observations"
    markers = {"outcome", "exception", "sampler_cancelled", "sampler_alive"}
    finals = [
        (index, report)
        for index, report in enumerate(observations)
        if markers.intersection(report)
    ]
    assert len(finals) == 1, "require exactly one observer final report"
    index, final = finals[0]
    assert index == len(observations) - 1, "stale observer final report"
    assert set(final) == markers, "malformed observer final report"
    assert final["outcome"] in ("ready", "failed")
    assert (
        final["exception"] is None
        if final["outcome"] == "ready"
        else isinstance(final["exception"], str)
    )
    assert final["sampler_cancelled"] is True, "cancellation not explicitly requested"
    assert final["sampler_alive"] is False, "sampler not explicitly stopped"
    return final


def admit_junit(path):
    suites = ET.parse(path).getroot()
    cases = list(suites.iter("testcase"))
    assert len(cases) == 1 and cases[0].get("name") == TEST.split("::")[1]
    assert not any(list(case) for case in cases)
    for suite in suites.iter("testsuite"):
        assert int(suite.get("tests", 0)) == 1
        assert all(int(suite.get(k, 0)) == 0 for k in ("failures", "errors", "skipped"))
    return {"tests": 1, "passed": 1, "failures": 0, "errors": 0, "skipped": 0}


def admit_bridge(receipt):
    assert receipt["schema_version"] == 3 and receipt["core_mode"] == "published"
    assert "actions_core_wheel" not in receipt
    public = receipt["published_core"]
    assert public["declared_version"] == "1.0.3"
    assert (
        public["independently_verified_registry_wheel_sha256"]
        == "8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265"
    )
    assert (
        public["whole_wheel_authenticated"] is False
        and public["cold_registry_acquisition"] is False
    )
    assert public["mode"] == "published"
    assert set(public) == {
        "mode",
        "declared_version",
        "independently_verified_registry_wheel_sha256",
        "measured_members",
        "whole_wheel_authenticated",
        "cold_registry_acquisition",
    }
    assert receipt["worker"]["version"] == "1.0.3"
    from action_server_tests.mcp import test_mcp_apps_authoring as bridge

    assert receipt["worker"]["module_hashes"] == bridge.PUBLISHED_CORE_MODULE_SHA256
    assert public["measured_members"] == list(bridge.PUBLISHED_CORE_MODULE_SHA256)
    assert set(receipt["worker"]["modules"]) == set(bridge.PUBLISHED_CORE_MODULE_SHA256)
    prefix = Path(receipt["worker"]["worker_prefix"]).resolve()
    assert all(
        Path(p).resolve().is_relative_to(prefix)
        for p in receipt["worker"]["modules"].values()
    )
    browser = receipt["browser"]
    assert browser["selection"] == "explicit" and browser["path"] == str(BROWSER)
    assert (
        browser["sha256"] == BROWSER_SHA and browser["playwright_version"] == "1.62.1"
    )
    assert browser["temporary_root_removed"] is True
    cache = receipt["cache"]
    assert cache["outside_synchronized_package"] is True
    root = Path(cache["source_root"]).resolve()
    assert all(
        not Path(cache[k]).resolve().is_relative_to(root)
        for k in ("build_root", "uv_cache")
    )
    assert receipt["canvas_resource"]["uri"] == bridge.CANVAS_RESOURCE_URI
    assert receipt["canvas_resource"]["mime_type"] == "text/html;profile=mcp-app"
    records = receipt["persisted_run_records"]
    assert len(records) == 5 and len({r["run_id"] for r in records}) == 5
    counts = {
        name: sum(r["action_name"] == name for r in records)
        for name in (
            "canvas_fixture_search",
            "canvas_fixture_artifact_status",
            "canvas_fixture_worker_provenance",
        )
    }
    assert counts == {
        "canvas_fixture_search": 2,
        "canvas_fixture_artifact_status": 2,
        "canvas_fixture_worker_provenance": 1,
    }
    assert all(r["status"] == "passed" and r["status_code"] == 2 for r in records)
    assert receipt["runtime_call_observations"] == [
        {
            "caller": "python-mcp-client",
            "tool": "canvas_fixture_search",
            "result": "passed",
        },
        {
            "caller": "python-mcp-client",
            "tool": "canvas_fixture_artifact_status",
            "result": "passed",
        },
        {
            "caller": "python-mcp-client",
            "tool": "canvas_fixture_worker_provenance",
            "result": "passed",
        },
        {
            "caller": "playwright-browser",
            "tool": "canvas_fixture_search",
            "result": "passed",
        },
        {
            "caller": "playwright-browser",
            "tool": "canvas_fixture_artifact_status",
            "result": "passed",
        },
    ]


def preflight():
    assert sys.platform == "linux"
    source = admit_source()
    verify_helpers()
    assert sha(BROWSER) == BROWSER_SHA and NODE.is_file()
    assert Path(shutil.which("node")).resolve() == NODE.resolve()
    assert (
        sha("/workspace/actions-cloud/bin/rcc")
        == "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428"
    )
    assert (
        sha(PREPARED_NODE_MODULES / "playwright-core/lib/coreBundle.js")
        == "9393fa79e1c67c74edc26b610d65a4f7ed73d345a762465cc88340a33a2454ac"
    )
    assert (
        sha(PREPARED_NODE_MODULES / "playwright-core/browsers.json")
        == "f306eed529599b1eaf2f8a85db9de2b23e1a3fe36c2b66434b7c9434fb627a99"
    )
    selection_path = NATIVE / "headless-selection.json"
    assert (
        sha(selection_path)
        == "a800c30a70cc5fc3564d5fd243888de646c54dcb42243a138af0c0eafee42152"
    )
    selection = json.loads(selection_path.read_text())
    assert selection["node"] == str(NODE) and selection["nodeVersion"] == "v20.19.3"
    assert (
        selection["playwrightVersion"] == "1.62.1"
        and selection["selectedName"] == "chromium-headless-shell"
    )
    assert (
        selection["executable"] == str(BROWSER)
        and selection["executableSha256"] == BROWSER_SHA
    )
    assert (
        selection["registryRevision"] == "1234"
        and selection["registryBrowserVersion"] == "151.0.7922.34"
    )
    assert selection["browserLaunched"] is False
    lock = json.loads((REPO / "action_server/frontend/package-lock.json").read_text())
    installed = json.loads((PREPARED_NODE_MODULES / ".package-lock.json").read_text())
    for package in ("@playwright/test", "playwright", "playwright-core"):
        key = "node_modules/" + package
        assert (
            installed["packages"][key]["version"]
            == lock["packages"][key]["version"]
            == "1.62.1"
        )
        assert (
            installed["packages"][key]["integrity"]
            == lock["packages"][key]["integrity"]
        )
    manifest = NATIVE / "output/native-artifact-manifest.json"
    assert (
        sha(manifest)
        == "70405e6e831066a37631c7a63045010fcbc8b3c928a6a22ff5130467c3ad9d44"
    )
    assert (
        sha(NATIVE / "output/native-artifact-tree-inventory.json")
        == "154aeb29249db79a32392124a3b71a8ac325c0bdaeda1bbc2e7445e96ffc7fdf"
    )
    measured = load_helper("native_inventory")
    entries = measured.packaged_tree_inventory(NATIVE / "dist/action-server")
    assert entries == json.loads(
        (NATIVE / "output/native-artifact-tree-inventory.json").read_text()
    )
    assert len(entries) == 1192
    assert (
        sha(NATIVE / "dist/action-server/action-server")
        == "067a27c24b55690410beeb1b95e97fb098edf8e02779b36b69bbead2227433fb"
    )
    assert (
        measured.packaged_tree_sha256(NATIVE / "dist/action-server")
        == "739838962d9d29f873932e13d2598d51ebba58b0f97c2c52fff8550004f06ae0"
    )
    assert (
        measured.packaged_files_sha256(NATIVE / "dist/action-server")
        == "576d6cb8e5a8637dcfd82f675384d638736509541a0e10877420151b61c4786b"
    )
    assert (
        sha("/workspace/engineering/pr310/action_server/go-wrapper/assets/assets.zip")
        == "c85862c9b4dba354953c02cbb80e520052f07cb6d506600bf4a07d2f755135e0"
    )
    verify_helpers()
    return {
        "source": source,
        "native_entries": len(entries),
        "actual_consumer_executed": False,
    }


def worker(attempt):
    import pytest
    import psutil
    from actions.server._selftest import ActionServerProcess
    from actions.server._common.process import (
        force_kill_process_tree_until,
        snapshot_process_descendants,
    )

    owner, observer = load_helper("browser_owner"), load_helper("startup_observer")
    runtime_processes, descendants, identities = [], [], set()
    observations, command_receipts, capture_errors = [], [], []
    original_start = ActionServerProcess.start

    def capture():
        for process in runtime_processes:
            if process._proc.poll() is not None:
                continue
            try:
                for child in snapshot_process_descendants(process._proc.pid):
                    identity = (child.pid, child.create_time())
                    if identity not in identities:
                        identities.add(identity)
                        descendants.append(child)
            except psutil.Error as error:
                capture_errors.append(type(error).__name__)

    def publish(report):
        observations.append(report)
        write(attempt / "startup-observations.json", observations)

    def observed_start(server, **kwargs):
        try:
            return observer.observe_start(
                original_start,
                server,
                snapshot=observer.snapshot,
                publish=publish,
                offsets=(20.0, 80.0, 110.0),
                **kwargs,
            )
        finally:
            primary = sys.exc_info()[1]
            try:
                if server._process is not None and server._process._proc is not None:
                    runtime_processes.append(server._process)
                    capture()
                    write(
                        attempt / "runtime-start-final-snapshot.json",
                        observer.snapshot(server),
                    )
            except BaseException as error:
                if primary is not None:
                    primary.add_note("Startup observation also failed: " + repr(error))
                else:
                    raise

    def owned_command(command, *, cwd, env, timeout):
        verify_helpers()
        capture()
        sequence = len(command_receipts) + 1
        record = {
            "argv": command,
            "cwd": str(cwd),
            "timeout_seconds": timeout,
            "browser_selection": env.get("CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"),
            "tmpdir": env.get("TMPDIR"),
            "status": "running",
        }
        command_receipts.append(record)
        try:
            completed = owner._run_owned_process_tree(
                command, cwd=cwd, env=env, timeout=timeout
            )
            record["returncode"] = completed.returncode
            for label, content in [
                ("stdout", completed.stdout),
                ("stderr", completed.stderr),
            ]:
                (attempt / f"command-{sequence}-{label}.log").write_text(
                    content or "", encoding="utf-8"
                )
            if command[:2] == ["npm", "run"]:
                assert command[2] == "build:canvas"
            if "--reporter" in command:
                assert Path(command[0]).resolve() == NODE.resolve()
                assert re.search(
                    r"<launching>\s+" + re.escape(str(BROWSER)) + r"\s",
                    completed.stderr,
                ), "Actual Playwright launch path not observed"
                record["actual_browser_launch_path"] = str(BROWSER)
                record[
                    "live_browser_pid_identity"
                ] = "NOT_OBSERVED; DEBUG path is launch evidence only"
            record["status"] = "completed"
            return completed
        except BaseException as error:
            record["status"] = "failed"
            record["error"] = type(error).__name__
            for label, content in [
                ("stdout", getattr(error, "stdout", getattr(error, "output", ""))),
                ("stderr", getattr(error, "stderr", "")),
            ]:
                if isinstance(content, bytes):
                    content = content.decode("utf-8", "replace")
                (attempt / f"command-{sequence}-{label}.log").write_text(
                    content or "", encoding="utf-8"
                )
            raise
        finally:
            primary = sys.exc_info()[1]
            try:
                capture()
                verify_helpers()
                write(attempt / "command-receipts.json", command_receipts)
            except BaseException as error:
                if primary is not None:
                    primary.add_note(
                        "Command postcondition also failed: " + repr(error)
                    )
                else:
                    raise

    ownership = CollectedOwnership(owned_command)
    ActionServerProcess.start = (
        observed_start  # Observation only; delegates identical kwargs/result/exception.
    )
    argv = [
        TEST,
        "-q",
        "-s",
        "-rs",
        "-n",
        "0",
        "--tb=short",
        "--basetemp",
        str(attempt / "pytest"),
        "--junitxml",
        str(attempt / "junit.xml"),
    ]
    status, cleanup = "failed", None
    try:
        code = pytest.main(argv, plugins=[ownership])
        assert code == 0
        admit_junit(attempt / "junit.xml")
        receipts = list(
            (attempt / "pytest").rglob("canvas-bridge-acceptance-receipt.json")
        )
        assert len(receipts) == 1
        receipt = json.loads(receipts[0].read_text())
        admit_bridge(receipt)
        package = receipts[0].parent
        assert sha(package / "package.yaml") == receipt["package_manifest_sha256"]
        assert sha(package / "canvas_actions.py") == receipt["action_source_sha256"]
        assert sha(package / "canvas.html") == receipt["canvas_resource"]["sha256"]
        assert (
            sha(REPO / "action_server/frontend/dist-canvas/index.html")
            == receipt["canvas_resource"]["sha256"]
        )
        assert (
            sha(REPO / "action_server/frontend/package-lock.json")
            == receipt["browser"]["frontend_lock_sha256"]
        )
        write(attempt / "bridge-receipt.json", receipt)
        assert (
            sum(
                r["argv"][:3] == ["npm", "run", "build:canvas"]
                for r in command_receipts
            )
            == 1
        )
        assert sum("--reporter" in r["argv"] for r in command_receipts) == 1
        status = "passed"
    finally:
        primary = sys.exc_info()[1]
        ActionServerProcess.start = original_start
        ownership.restore()
        deadline = time.monotonic() + 5
        try:
            if not runtime_processes:
                raise RuntimeError(
                    "Runtime ownership unavailable: no startup owner was constructed"
                )
            assert len(runtime_processes) == 1
            process = runtime_processes[0]
            result = force_kill_process_tree_until(
                process._proc,
                descendants,
                max(time.monotonic(), deadline - 1),
                snapshot_complete_before_call=not capture_errors,
            )
            for reader in process._reader_threads:
                if reader.ident is not None:
                    reader.join(timeout=max(0, deadline - time.monotonic()))
            cleanup = {
                "wrapper_reaped": result.wrapper_reaped,
                "descendant_snapshot_complete": result.descendant_snapshot_complete,
                "descendant_reap_complete": result.descendant_reap_complete,
                "cleanup_errors": list(result.errors) + capture_errors,
                "active_readers": [
                    r.name for r in process._reader_threads if r.is_alive()
                ],
                "observed_live_children": list(result.live_descendant_pids),
                "observed_zombie_children": list(result.zombie_descendant_pids),
                "natural_runtime_exit": "NOT_PROVEN; fixture/owned supervisor forced cleanup",
            }
            admit_cleanup(cleanup)
            final_observer = admit_observer(observations)
        except BaseException as error:
            status = "failed"
            print("Owned cleanup failure:", repr(error), file=sys.stderr)
            write(
                attempt / "runtime-cleanup.json",
                {
                    "status": "unavailable" if not runtime_processes else "failed",
                    "cleanup": cleanup,
                    "error": repr(error),
                },
            )
            if primary is not None:
                primary.add_note("Owned cleanup also failed: " + repr(error))
            else:
                raise
        else:
            write(
                attempt / "runtime-cleanup.json",
                {
                    "status": status,
                    "cleanup": cleanup,
                    "finite_observed_descendants": len(descendants),
                    "observer_cancelled_and_joined": True,
                    "observer_final_report": final_observer,
                    "mechanism": "measured Runtime owned cleanup; false internal reap predicate remains failure regardless of outer subreaper",
                },
            )


def execute():
    preflight()
    os.umask(0o077)
    attempt = OWNED / ("actual-" + HEAD + "-2")
    attempt.mkdir(mode=0o700)  # One attempt only; existing root fails closed.
    node_modules = REPO / "action_server/frontend/node_modules"
    if not node_modules.exists():
        node_modules.symlink_to(PREPARED_NODE_MODULES, target_is_directory=True)
    assert node_modules.resolve() == PREPARED_NODE_MODULES
    native = attempt / "frozen-runtime"
    shutil.copytree(NATIVE / "dist/action-server", native, symlinks=True)
    measure = load_helper("native_inventory")
    expected = json.loads(
        (NATIVE / "output/native-artifact-tree-inventory.json").read_text()
    )
    assert measure.packaged_tree_inventory(native) == expected
    env = dict(os.environ)
    env.update(
        {
            "ACTIONS_CANVAS_RUNTIME_ACCEPTANCE": "1",
            "ACTIONS_CANVAS_CORE_MODE": "published",
            "ACTIONS_HOME": str(attempt / "actions-home"),
            "UV_CACHE_DIR": str(attempt / "uv-cache"),
            "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE": str(
                native / "action-server"
            ),
            "CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH": str(BROWSER),
            "DEBUG": "pw:browser",
            "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2",
            "MKL_NUM_THREADS": "2",
            "PYTEST_XDIST_AUTO_NUM_WORKERS": "2",
        }
    )
    env.pop("PYTHONPATH", None)
    env.pop("NODE_OPTIONS", None)
    env.pop("NODE_PATH", None)
    outer = load_helper("outer_owner")
    verify_helpers()
    try:
        completed = outer.run_owned_process(
            [sys.executable, str(Path(__file__).resolve()), "--worker", str(attempt)],
            env=env,
            cwd=REPO / "action_server",
            timeout_seconds=600,
            cleanup_grace_seconds=10,
        )
        record_outer_completion(completed, attempt)
        assert completed.cleanup_disposition in {
            "clean_no_descendants",
            "reaped_exited_descendants",
        }
        junit = admit_junit(attempt / "junit.xml")
        runtime = json.loads((attempt / "runtime-cleanup.json").read_text())
        assert runtime["status"] == "passed"
        admit_cleanup(runtime["cleanup"])
        admit_bridge(json.loads((attempt / "bridge-receipt.json").read_text()))
        assert measure.packaged_tree_inventory(native) == expected
        write(
            attempt / "actual-admission.json",
            {
                "status": "pending_postconditions",
                "source": admit_source(),
                "native_producer": PRODUCER,
                "junit": junit,
                "runtime_cleanup": runtime,
                "outer_cleanup": completed.cleanup_disposition,
                "outer_reaped_descendants": completed.reaped_descendants,
                "native1192_entries_unchanged": True,
                "limits": [
                    "finite observed descendant cleanup, not universal adoption/natural Runtime shutdown",
                    "three-member public-Core sample, not whole wheel/cold registry",
                    "fixture artifact status only; no production host/ChatGPT/OAuth release qualification",
                ],
            },
        )
    except BaseException as error:
        for label, content in [
            ("stdout", getattr(error, "stdout", getattr(error, "output", ""))),
            ("stderr", getattr(error, "stderr", "")),
        ]:
            if isinstance(content, bytes):
                content = content.decode("utf-8", "replace")
            if content:
                (attempt / f"failure-{label}.log").write_text(content, encoding="utf-8")
                print(content, file=sys.stderr)
        write(
            attempt / "actual-admission.json",
            {
                "status": "failed",
                "primary": repr(error),
                "actual_rerun_authorized": False,
            },
        )
        raise
    finally:
        primary = sys.exc_info()[1]
        try:
            verify_helpers()
            assert sha(BROWSER) == BROWSER_SHA
            assert measure.packaged_tree_inventory(native) == expected
        except BaseException as error:
            provisional = attempt / "actual-admission.json"
            if provisional.is_file():
                shutil.copyfile(
                    provisional, attempt / "consumer-provisional-admission.json"
                )
            write(
                provisional,
                {
                    "status": "failed",
                    "postcondition_failure": repr(error),
                    "primary": repr(primary) if primary is not None else None,
                    "prior_admission": "consumer-provisional-admission.json",
                },
            )
            if primary is not None:
                primary.add_note("Postcondition also failed: " + repr(error))
            else:
                raise
        else:
            if primary is None:
                path = attempt / "actual-admission.json"
                admission = json.loads(path.read_text())
                assert admission["status"] == "pending_postconditions"
                admission["status"] = "passed"
                write(path, admission)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-reviewed-proposal", action="store_true")
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker)
    elif args.execute_reviewed_proposal:
        execute()
    else:
        print(json.dumps(preflight(), sort_keys=True))
