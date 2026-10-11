"""Synthetic admission controls only; no Runtime, browser or registry acquisition."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

PATH = Path(__file__).with_name("canvas-native-public-runner-v2.py")
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
    monkeypatch.setattr(pytest, "main", lambda argv: 1)
    with pytest.raises(AssertionError) as failure:
        runner.worker(tmp_path)
    assert any("Owned cleanup also failed" in note for note in failure.value.__notes__)
    assert (
        json.loads((tmp_path / "runtime-cleanup.json").read_text())["status"]
        == "failed"
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
