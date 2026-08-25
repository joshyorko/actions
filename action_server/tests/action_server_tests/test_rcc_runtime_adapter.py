import json
import subprocess
from pathlib import Path

import pytest


def test_artifact_digest_parser_accepts_only_exact_identity():
    from actions.server._rcc_runtime_adapter import RccRuntimeError, parse_artifact_digest

    assert parse_artifact_digest({"artifact": "sha256:" + "a" * 64}) == "sha256:" + "a" * 64
    assert parse_artifact_digest({"artifact": {"digest": "sha256:" + "b" * 64}}) == "sha256:" + "b" * 64
    assert parse_artifact_digest({"artifactDigest": "sha256:" + "c" * 64}) == "sha256:" + "c" * 64
    for payload in ({}, {"artifact": "not-a-digest"}, {"digest": "sha256:" + "a" * 63}):
        with pytest.raises(RccRuntimeError, match="artifact"):
            parse_artifact_digest(payload)


def test_runtime_descriptor_has_no_activation_path_authority():
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor

    descriptor = RccRuntimeDescriptor(
        artifact_digest="sha256:" + "a" * 64,
        source_generation="gen-1",
        source_hash="b" * 64,
    )
    serialized = json.loads(descriptor.to_json())
    assert serialized["runtime"]["kind"] == "rcc"
    assert serialized["runtime"]["artifact_digest"] == "sha256:" + "a" * 64
    for forbidden in ("PYTHON_EXE", "CONDA_PREFIX", "ROBOCORP_HOME", "holotree", "materialization"):
        assert forbidden not in descriptor.to_json()


def test_import_command_uses_artifact_exec_not_python_exe(tmp_path):
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor, build_exec_command

    descriptor = RccRuntimeDescriptor(artifact_digest="sha256:" + "c" * 64)
    command = build_exec_command(
        Path("/opt/rcc"), descriptor, ["python", "-c", "import actions"], receipt_file=None
    )
    assert command[:5] == ["/opt/rcc", "env", "exec", "--artifact", "sha256:" + "c" * 64]
    assert "PYTHON_EXE" not in command
    assert command[-4:] == ["--", "python", "-c", "import actions"]


def test_worker_command_has_inherit_streams_and_receipt(tmp_path):
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor, build_exec_command

    receipt = tmp_path / "receipt.json"
    descriptor = RccRuntimeDescriptor(artifact_digest="sha256:" + "d" * 64)
    command = build_exec_command(Path("/opt/rcc"), descriptor, ["python", "-m", "preload_actions_server_main"], receipt_file=receipt)
    assert "--inherit-streams" in command
    assert "--receipt-file" in command
    assert str(receipt) in command
    assert command[command.index("--") + 1 :] == ["python", "-m", "preload_actions_server_main"]


def test_failed_publish_is_phase_error_without_fallback(tmp_path):
    from actions.server._rcc_runtime_adapter import RccRuntimeError, publish_artifact

    with pytest.raises(RccRuntimeError, match="publish"):
        publish_artifact(Path("/does/not/exist"), Path("/tmp/rcc"), runner=lambda *args: (1, "", "no"))


def test_acquire_rejects_missing_or_conflicting_identity():
    from actions.server._rcc_runtime_adapter import RccRuntimeError, acquire_artifact

    digest = "sha256:" + "e" * 64
    for result in ({}, {"artifactDigest": "sha256:" + "f" * 64}):
        with pytest.raises(RccRuntimeError, match="artifact"):
            acquire_artifact(
                digest,
                Path("/opt/rcc"),
                runner=lambda *args, result=result: (0, json.dumps(result), ""),
            )


def test_rcc_version_mismatch_fails_closed():
    from actions.server._rcc_runtime_adapter import RccRuntimeError, verify_rcc_version

    with pytest.raises(RccRuntimeError, match="unsupported RCC version"):
        verify_rcc_version(
            Path("/opt/rcc"), runner=lambda *args: (0, "v18.19.1\n", "")
        )


def test_source_only_reload_reuses_verified_artifact_without_republishing(tmp_path):
    from actions.server._rcc_runtime_adapter import prepare_runtime

    package_yaml = tmp_path / "package.yaml"
    package_yaml.write_text(
        "spec-version: v2\n"
        "dependencies:\n"
        "  conda-forge:\n"
        "    - python=3.11\n"
    )
    digest = "sha256:" + "a" * 64
    calls = []

    def runner(*args):
        calls.append(args)
        if args[2] == "publish":
            return 0, json.dumps({"artifact": digest}), ""
        return 0, json.dumps({"artifactDigest": digest, "verification": {"valid": True}}), ""

    first = prepare_runtime(
        package_yaml,
        Path("/opt/rcc"),
        source_generation="source-1",
        runner=runner,
    )
    second = prepare_runtime(
        package_yaml,
        Path("/opt/rcc"),
        source_generation="source-2",
        runner=runner,
    )

    assert [call[2] for call in calls] == ["publish", "acquire", "acquire"]
    assert first.artifact_digest == second.artifact_digest == digest
    assert second.source_generation == "source-2"


def test_cached_artifact_is_revalidated_and_rebuilt_when_materialization_disappears(
    tmp_path,
):
    from actions.server._rcc_runtime_adapter import prepare_runtime

    package_yaml = tmp_path / "package.yaml"
    package_yaml.write_text("spec-version: v2\ndependencies: {python: '3.11'}\n")
    first_digest = "sha256:" + "a" * 64
    replacement_digest = "sha256:" + "b" * 64
    calls = []
    missing = False

    def runner(*args):
        nonlocal missing
        calls.append(args)
        if args[2] == "publish":
            return 0, json.dumps({"artifact": replacement_digest if missing else first_digest}), ""
        if missing and args[4] == first_digest:
            return 1, "", "artifact is not materialized"
        digest = replacement_digest if missing else first_digest
        return 0, json.dumps(
            {"artifactDigest": digest, "verification": {"valid": True}}
        ), ""

    prepare_runtime(package_yaml, Path("/opt/rcc"), runner=runner)
    missing = True
    descriptor = prepare_runtime(package_yaml, Path("/opt/rcc"), runner=runner)

    assert descriptor.artifact_digest == replacement_digest
    assert [call[2] for call in calls] == [
        "publish",
        "acquire",
        "acquire",
        "publish",
        "acquire",
    ]


def test_environment_change_does_not_reuse_cached_artifact(tmp_path):
    from actions.server._rcc_runtime_adapter import prepare_runtime

    package_yaml = tmp_path / "package.yaml"
    package_yaml.write_text("spec-version: v2\ndependencies: {python: '3.11'}\n")
    calls = []
    digests = iter(("sha256:" + "a" * 64, "sha256:" + "b" * 64))

    def runner(*args):
        calls.append(args)
        if args[2] == "publish":
            return 0, json.dumps({"artifact": next(digests)}), ""
        digest = args[4]
        return 0, json.dumps({"artifactDigest": digest, "verification": {"valid": True}}), ""

    first = prepare_runtime(package_yaml, Path("/opt/rcc"), runner=runner)
    package_yaml.write_text("spec-version: v2\ndependencies: {python: '3.12'}\n")
    second = prepare_runtime(package_yaml, Path("/opt/rcc"), runner=runner)

    assert len(calls) == 4
    assert first.artifact_digest != second.artifact_digest


def test_environment_fingerprint_classifies_pythonpath_as_source_change(tmp_path):
    from actions.server._rcc_runtime_adapter import classify_environment_change

    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(
        "spec-version: v2\ndependencies: {python: '3.11'}\npythonpath: [src]\n"
    )
    after.write_text(
        "spec-version: v2\ndependencies: {python: '3.11'}\npythonpath: [src, tests]\n"
    )

    assert classify_environment_change(before, after) == "source"


def test_restart_reacquires_existing_artifact_without_republishing(tmp_path):
    from actions.server._rcc_runtime_adapter import (
        RccRuntimeDescriptor,
        environment_spec_fingerprint,
        prepare_runtime,
    )

    package_yaml = tmp_path / "package.yaml"
    package_yaml.write_text("spec-version: v2\ndependencies: {python: '3.11'}\n")
    digest = "sha256:" + "c" * 64
    calls = []

    def runner(*args):
        calls.append(args)
        return 0, json.dumps({"artifactDigest": digest, "verification": {"valid": True}}), ""

    previous = RccRuntimeDescriptor(
        artifact_digest=digest,
        environment_fingerprint=environment_spec_fingerprint(package_yaml),
    )
    prepare_runtime(
        package_yaml,
        Path("/opt/rcc"),
        previous_descriptor=previous,
        runner=runner,
    )

    assert [call[2] for call in calls] == ["acquire"]


def test_missing_persisted_artifact_republishes_and_acquires_new_identity(tmp_path):
    from actions.server._rcc_runtime_adapter import (
        RccRuntimeDescriptor,
        environment_spec_fingerprint,
        prepare_runtime,
    )

    package_yaml = tmp_path / "package.yaml"
    package_yaml.write_text("spec-version: v2\ndependencies: {python: '3.11'}\n")
    old_digest = "sha256:" + "a" * 64
    new_digest = "sha256:" + "b" * 64
    calls = []

    def runner(*args):
        calls.append(args)
        if args[2] == "acquire" and args[4] == old_digest:
            return 1, "", "artifact is not materialized"
        if args[2] == "publish":
            return 0, json.dumps({"artifact": new_digest}), ""
        return 0, json.dumps(
            {"artifactDigest": new_digest, "verification": {"valid": True}}
        ), ""

    previous = RccRuntimeDescriptor(
        artifact_digest=old_digest,
        environment_fingerprint=environment_spec_fingerprint(package_yaml),
    )
    descriptor = prepare_runtime(
        package_yaml,
        Path("/opt/rcc"),
        previous_descriptor=previous,
        runner=runner,
    )

    assert descriptor.artifact_digest == new_digest
    assert [call[2] for call in calls] == ["acquire", "publish", "acquire"]


def test_acquire_rejects_invalid_artifact_verification():
    from actions.server._rcc_runtime_adapter import RccRuntimeError, acquire_artifact

    digest = "sha256:" + "d" * 64
    with pytest.raises(RccRuntimeError, match="verification"):
        acquire_artifact(
            digest,
            Path("/opt/rcc"),
            runner=lambda *args: (
                0,
                json.dumps(
                    {
                        "artifactDigest": digest,
                        "verification": {"valid": False},
                    }
                ),
                "",
            ),
        )


def test_acquire_rejects_missing_artifact_verification():
    from actions.server._rcc_runtime_adapter import RccRuntimeError, acquire_artifact

    digest = "sha256:" + "e" * 64
    with pytest.raises(RccRuntimeError, match="verification"):
        acquire_artifact(
            digest,
            Path("/opt/rcc"),
            runner=lambda *args: (
                0,
                json.dumps({"artifactDigest": digest}),
                "",
            ),
        )


def test_reload_marks_running_generation_non_reusable(monkeypatch):
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules, "termcolor", SimpleNamespace(colored=lambda value, **kwargs: value)
    )
    from actions.server import _actions_process_pool as process_pool

    class OldProcess:
        can_reuse = True

    old_process = OldProcess()
    pool = process_pool.ActionsProcessPool.__new__(process_pool.ActionsProcessPool)
    pool._lock = process_pool.threading.Lock()
    pool._idle_processes = {}
    pool._running_processes = {"old": {old_process}}
    pool._warmup_processes_unlocked = lambda **kwargs: None
    pool.action_package_id_to_action_package = {"old": "old-package"}
    pool.actions = ["old-action"]
    pool._cycle_actions_iterator = iter(pool.actions)
    new_action = type("Action", (), {"enabled": True, "name": "new-action"})()
    pool.on_reload({"new": "new-package"}, [new_action])

    assert old_process.can_reuse is False
    assert pool.action_package_id_to_action_package == {"new": "new-package"}
    assert pool.actions == [new_action]


def test_reload_rolls_back_routing_when_new_generation_warmup_fails(monkeypatch):
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules, "termcolor", SimpleNamespace(colored=lambda value, **kwargs: value)
    )
    from actions.server import _actions_process_pool as process_pool

    class OldProcess:
        can_reuse = True

    old_process = OldProcess()
    old_map = {"old": "old-package"}
    old_action = type("Action", (), {"enabled": True, "name": "old-action"})()
    pool = process_pool.ActionsProcessPool.__new__(process_pool.ActionsProcessPool)
    pool._lock = process_pool.threading.Lock()
    pool._idle_processes = {}
    pool._running_processes = {"old": {old_process}}
    pool.action_package_id_to_action_package = old_map
    pool.actions = [old_action]
    pool._cycle_actions_iterator = iter([old_action])

    def fail_warmup(**kwargs):
        raise RuntimeError("new generation failed")

    pool._warmup_processes_unlocked = fail_warmup
    new_action = type("Action", (), {"enabled": True, "name": "new-action"})()

    with pytest.raises(RuntimeError, match="new generation failed"):
        pool.on_reload({"new": "new-package"}, [new_action])

    assert pool.action_package_id_to_action_package is old_map
    assert pool.actions == [old_action]
    assert old_process.can_reuse is True


def test_route_and_pool_reload_commits_after_inflight_old_call(monkeypatch):
    from threading import Event, Thread
    from types import SimpleNamespace

    from actions.server import _server

    class FakeApp:
        def __init__(self):
            self.router = SimpleNamespace(routes=["old-route"])

    app = FakeApp()
    monkeypatch.setattr("actions.server._app.get_app", lambda: app)
    events = []
    old_call_started = Event()
    release_old_call = Event()

    class FakeRoutes:
        def __init__(self):
            self.action_package_id_to_action_package = {"old": "old-package"}
            self.actions = ["old-action"]
            self.registered_route_names = {"old-route"}
            self.mcp_server_setup_helper = SimpleNamespace(_catalog=["old"])

        def unregister_http_actions(self):
            events.append("routes-unregister")

        def unregister_actions(self):
            events.append("routes-unregister")

        def register_actions(self):
            events.append("routes-register")

    class FakePool:
        def on_reload(self, packages, actions):
            events.append("pool-prepare")

    def old_call():
        old_call_started.set()
        release_old_call.wait(timeout=2)
        events.append("old-call-complete")

    old_call_thread = Thread(target=old_call)
    old_call_thread.start()
    assert old_call_started.wait(timeout=2)

    routes = FakeRoutes()
    _server._reload_action_generation(routes, FakePool(), ["new-action"], {"new": "new"})
    release_old_call.set()
    old_call_thread.join(timeout=2)

    assert events[:3] == ["pool-prepare", "routes-unregister", "routes-register"]
    assert events[-1] == "old-call-complete"
    assert app.router.routes == ["old-route"]


def test_admitted_route_pins_process_lookup_to_old_generation(monkeypatch):
    import asyncio

    asyncio.run(_test_admitted_route_pins_process_lookup_to_old_generation(monkeypatch))


def test_scheduler_admission_pins_pool_and_package_across_reload(monkeypatch, tmp_path):
    """A scheduled run keeps its admitted pool and package during reload."""
    import asyncio
    import threading
    from contextlib import nullcontext
    from types import SimpleNamespace

    from actions.server import _actions_process_pool, _actions_run, _artifact_storage
    from actions.server import _models, _runs_state_cache, _settings
    from actions.server._robo_utils import run_in_thread

    class RuntimeInfo:
        class OnCancel:
            def register(self, _callback):
                return nullcontext()

        on_cancel = OnCancel()

        def is_canceled(self):
            return False

    class Handle:
        pid = 123

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def run_action(
            self, _run, _package, _action, _input, _artifacts, _output,
            result_json, *_args
        ):
            result_json.write_text('{"result": "old-generation"}')
            return 0

    class Pool:
        def __init__(self, generation):
            self.generation = generation
            self.calls = []

        def obtain_process_for_action(
            self, action, runtime_info, *, generation, action_package
        ):
            self.calls.append((action, runtime_info, generation, action_package))
            return Handle()

    class DB:
        def connect(self):
            return nullcontext()

        def first(self, *_args):
            return run

    class ArtifactStorage:
        def run_artifacts_dir(self, _relative):
            return tmp_path

    class RunsState:
        def create_run_runtime_info(self, _run_id):
            return RuntimeInfo()

    old_pool = Pool(4)
    new_pool = Pool(5)
    current_pool = old_pool
    worker_started = threading.Event()
    allow_worker = threading.Event()

    def dispatch(func):
        result = {}

        def worker():
            worker_started.set()
            allow_worker.wait(timeout=5)
            try:
                result["value"] = func()
            except BaseException as exc:  # pragma: no cover - surfaced by result()
                result["error"] = exc

        thread = threading.Thread(target=worker)
        thread.start()

        class Future:
            def result(self):
                thread.join(timeout=5)
                if "error" in result:
                    raise result["error"]
                return result["value"]

        return Future()

    def get_pool():
        return current_pool

    run = SimpleNamespace()
    action = SimpleNamespace(name="scheduled", id="action-id")
    old_package = SimpleNamespace(id="old-package")
    result = {}

    monkeypatch.setattr(
        _settings,
        "get_settings",
        lambda: SimpleNamespace(datadir=tmp_path, reuse_processes=False),
    )
    monkeypatch.setattr(
        _runs_state_cache, "get_global_runs_state", lambda: RunsState()
    )
    monkeypatch.setattr(
        _artifact_storage, "get_artifact_storage", lambda: ArtifactStorage()
    )
    monkeypatch.setattr(_actions_process_pool, "get_actions_process_pool", get_pool)
    monkeypatch.setattr(_models, "get_db", lambda: DB())
    monkeypatch.setattr(_actions_run, "_set_run_as_running", lambda *_args: None)
    monkeypatch.setattr(_actions_run, "_set_run_as_finished_ok", lambda *_args: None)
    monkeypatch.setattr(_actions_run, "_set_run_as_finished_failed", lambda *_args: None)
    monkeypatch.setattr(run_in_thread, "run_in_thread", dispatch)

    async def run_scheduled():
        return await _actions_run.execute_action_for_scheduler(
            action, old_package, "run-id", {}, "artifacts"
        )

    task = threading.Thread(
        target=lambda: result.update(value=asyncio.run(run_scheduled()))
    )
    task.start()
    assert worker_started.wait(timeout=5)
    current_pool = new_pool
    allow_worker.set()
    task.join(timeout=5)

    assert result["value"] == (True, "old-generation")
    assert len(old_pool.calls) == 1
    assert old_pool.calls[0][2:] == (4, old_package)
    assert not new_pool.calls


async def _test_admitted_route_pins_process_lookup_to_old_generation(monkeypatch):
    """A request admitted before reload must retain its route generation."""
    import asyncio
    from threading import Event, Lock, Semaphore
    from types import SimpleNamespace

    from fastapi import Response
    from starlette.requests import Request

    from actions.server import _actions_run
    from actions.server import _actions_process_pool as process_pool

    started = Event()
    release = Event()
    lookups = []

    class FakeProcess:
        def __init__(self, _settings, action_package, _post_run_args):
            self.action_package = action_package
            self.key = action_package.id
            self.can_reuse = True
            self.pid = 123
            self.killed = False

        def is_alive(self):
            return not self.killed

        def kill(self):
            self.killed = True

    monkeypatch.setattr(process_pool, "ProcessHandle", FakeProcess)
    monkeypatch.setattr(
        process_pool, "_get_process_handle_key", lambda _settings, package: package.id
    )
    pool = process_pool.ActionsProcessPool.__new__(process_pool.ActionsProcessPool)
    pool._settings = SimpleNamespace(max_processes=1, min_processes=0, reuse_processes=True)
    pool._generation = 2
    pool._lock = Lock()
    pool._processes_running_semaphore = Semaphore(1)
    pool._running_processes = {}
    pool._idle_processes = {}
    pool._post_run_cmd_args = None
    pool.action_package_id_to_action_package = {
        "new-package": SimpleNamespace(id="new-package")
    }
    pool.actions = []
    pool._cycle_actions_iterator = iter(())
    monkeypatch.setattr(
        process_pool, "get_actions_process_pool", lambda: pool
    )

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            self.action_package = args[0]
            self.action = args[1]
            self.process_pool_generation = kwargs["process_pool_generation"]

        def run_in_thread(self):
            started.set()
            assert release.wait(timeout=2)
            with pool.obtain_process_for_action(
                self.action,
                generation=self.process_pool_generation,
                action_package=self.action_package,
            ) as process:
                lookups.append(
                    (self.process_pool_generation, process.action_package)
                )
                return "old-result"

    monkeypatch.setattr(_actions_run, "_ActionsRunner", FakeRunner)
    package = SimpleNamespace(id="old-package")
    action = SimpleNamespace(
        action_package_id="old-package",
        input_schema=json.dumps({"type": "object"}),
        output_schema=json.dumps({"type": "string"}),
    )
    fast_api, _internal, _ = _actions_run.generate_func_from_action(
        package, action, "Old Action", process_pool_generation=1
    )

    request_messages = iter(
        [{"type": "http.request", "body": b"{}", "more_body": False}]
    )

    async def receive():
        return next(request_messages)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/old",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("127.0.0.1", 80),
            "client": ("127.0.0.1", 1),
        },
        receive=receive,
    )
    task = asyncio.create_task(fast_api(Response(), request))
    await asyncio.to_thread(started.wait, 2)
    # The pool has already advanced, but this admitted request still carries
    # generation 1 and its old package into the process lookup.
    release.set()
    assert await task == "old-result"
    assert lookups == [(1, package)]


def test_route_registration_failure_restores_routes_and_pool_generation(monkeypatch):
    from types import SimpleNamespace

    from actions.server import _server

    class FakeApp:
        def __init__(self):
            self.router = SimpleNamespace(routes=["old-route"])

    app = FakeApp()
    monkeypatch.setattr("actions.server._app.get_app", lambda: app)

    class FakeRoutes:
        def __init__(self):
            self.action_package_id_to_action_package = {"old": "old-package"}
            self.actions = ["old-action"]
            self.registered_route_names = {"old-route"}
            self.mcp_server_setup_helper = SimpleNamespace(_catalog=["old"])

        def unregister_actions(self):
            app.router.routes[:] = []

        def unregister_http_actions(self):
            app.router.routes[:] = []

        def register_actions(self):
            app.router.routes.append("new-route")
            raise RuntimeError("route preparation failed")

    class FakePool:
        def __init__(self):
            self.reloads = []
            self.generation = 4

        def on_reload(self, packages, actions):
            self.reloads.append((packages, actions))
            self.generation += 1

        def restore_generation(self, generation):
            self.generation = generation

    routes = FakeRoutes()
    pool = FakePool()
    with pytest.raises(RuntimeError, match="route preparation failed"):
        _server._reload_action_generation(
            routes, pool, ["new-action"], {"new": "new-package"}
        )

    assert app.router.routes == ["old-route"]
    assert pool.reloads == [
        ({"new": "new-package"}, ["new-action"]),
        ({"old": "old-package"}, ["old-action"]),
    ]
    assert pool.generation == 4


def test_receipt_requires_identity_verification_and_lease(tmp_path):
    from actions.server._rcc_runtime_adapter import RccRuntimeError, read_receipt

    digest = "sha256:" + "1" * 64
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "artifactDigest": digest,
                "verification": {"valid": True},
                "leaseId": "lease-1",
            }
        )
    )
    assert read_receipt(receipt, digest)["leaseId"] == "lease-1"
    receipt.write_text(
        json.dumps(
            {
                "artifactDigest": digest,
                "verification": {"valid": False},
                "leaseId": "lease-1",
            }
        )
    )
    with pytest.raises(RccRuntimeError, match="verification"):
        read_receipt(receipt, digest)


def test_spec_v2_without_provider_preserves_legacy_bootstrap(monkeypatch, tmp_path):
    from actions.server._action_package_handler import ActionPackageHandler
    from actions.server._protocols import ActionResult
    from actions.server._rcc import EnvInfo

    monkeypatch.delenv("ACTIONS_RUNTIME_RCC_PROVIDER", raising=False)
    monkeypatch.delenv("ACTIONS_REAL_RCC_ARTIFACT_TEST", raising=False)
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "package.yaml").write_text(
        "version: 0.1\nspec-version: v2\ndependencies: {}\n"
    )

    class LegacyRcc:
        def get_package_yaml_hash(self, package_yaml, devenv):
            return "legacy-hash"

        def create_env_and_get_vars(self, datadir, package_yaml, package_hash, devenv):
            return ActionResult(True, None, EnvInfo({"PYTHON_EXE": "/legacy/python"}))

    monkeypatch.setattr(
        "actions.server._rcc.get_rcc", lambda: LegacyRcc()
    )
    monkeypatch.setattr(
        "actions.server._rcc_runtime_adapter.prepare_runtime",
        lambda *args, **kwargs: pytest.fail("RCC artifact mode was selected without an opt-in"),
    )
    assert ActionPackageHandler(str(package_dir), tmp_path / "data").bootstrap_environment() == (
        "legacy-hash",
        {
            "PYTHON_EXE": "/legacy/python",
            "PYTHONPATH": str(package_dir),
        },
    )


def test_process_handle_kill_waits_for_wrapper(tmp_path):
    from actions.server._rcc_runtime_adapter import RccProcessHandle

    process = subprocess.Popen(["sh", "-c", "sleep 30"])
    handle = RccProcessHandle(process, tmp_path / "receipt.json")
    handle.kill()
    assert process.poll() is not None


def test_process_startup_failure_closes_listener_and_accept_future(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from actions.server import _actions_process_pool as process_pool

    class FakeSocket:
        def __init__(self):
            self.closed = False

        def getsockname(self):
            return ("127.0.0.1", 12345)

        def close(self):
            self.closed = True

    class FakeFuture:
        def __init__(self):
            self.cancel_called = False
            self.result_timeouts = []

        def cancel(self):
            self.cancel_called = True
            return True

        def result(self, timeout=None):
            self.result_timeouts.append(timeout)
            raise RuntimeError("accept worker stopped")

    fake_socket = FakeSocket()
    fake_future = FakeFuture()
    monkeypatch.setattr(process_pool, "_create_server_socket", lambda *args: fake_socket)
    monkeypatch.setattr(
        "actions.server._robo_utils.run_in_thread.run_in_thread",
        lambda *args, **kwargs: fake_future,
    )
    monkeypatch.setattr(process_pool.subprocess, "Popen", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("forced Popen failure")))
    monkeypatch.setattr(process_pool, "_get_process_handle_key", lambda *args: "key")
    monkeypatch.setattr(
        "actions.server._actions_run_helpers.get_action_package_cwd",
        lambda *args: tmp_path,
    )
    monkeypatch.setattr(
        "actions.server._robo_utils.process.build_subprocess_kwargs",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        "actions.server._robo_utils.process.build_python_launch_env",
        lambda env: env,
    )
    monkeypatch.setattr(
        "actions.server._actions_run_helpers._add_preload_actions_dir_to_env_pythonpath",
        lambda env: None,
    )
    monkeypatch.setattr(
        "actions.server._rcc_runtime_adapter.load_descriptor",
        lambda env_json: object(),
    )
    monkeypatch.setattr(
        "actions.server._rcc_runtime_adapter.get_rcc_location",
        lambda: Path("/opt/rcc"),
    )
    monkeypatch.setattr(
        "actions.server._rcc_runtime_adapter.build_exec_command",
        lambda *args, **kwargs: ["/opt/rcc"],
    )
    monkeypatch.setattr(
        "actions.server._rcc_runtime_adapter.new_receipt_path",
        lambda datadir: tmp_path / "receipt.json",
    )

    settings = SimpleNamespace(datadir=tmp_path, reuse_processes=False)
    package = SimpleNamespace(id="package", env_json=json.dumps({"runtime": {}}), directory=str(tmp_path))
    with pytest.raises(OSError, match="forced Popen failure"):
        process_pool.ProcessHandle(settings, package, None)

    assert fake_socket.closed is True
    assert fake_future.cancel_called is True
    assert fake_future.result_timeouts


def test_process_pool_releases_capacity_when_warmup_fails(monkeypatch):
    from types import SimpleNamespace

    from actions.server import _actions_process_pool as process_pool

    class FakeProcess:
        can_reuse = True
        pid = 123
        key = "key"

        def __init__(self):
            self.killed = False
            self.reaped = False

        def is_alive(self):
            return True

        def kill(self):
            self.killed = True
            self.reaped = True

    class TrackingSemaphore:
        def __init__(self):
            self.acquired = False
            self.release_count = 0

        def acquire(self, timeout=None):
            assert not self.acquired
            self.acquired = True
            return True

        def release(self):
            assert fake_process.reaped
            self.acquired = False
            self.release_count += 1

    fake_process = FakeProcess()
    pool = process_pool.ActionsProcessPool.__new__(process_pool.ActionsProcessPool)
    pool._settings = SimpleNamespace(reuse_processes=False)
    pool._lock = process_pool.threading.Lock()
    pool._running_processes = {}
    pool._idle_processes = {"key": {fake_process}}
    semaphore = TrackingSemaphore()
    pool._processes_running_semaphore = semaphore
    pool.action_package_id_to_action_package = {"package": SimpleNamespace(id="package")}
    pool._remove_from_running_processes = lambda process: None
    pool._warmup_processes = lambda: (_ for _ in ()).throw(RuntimeError("forced warmup failure"))
    monkeypatch.setattr(process_pool, "_get_process_handle_key", lambda *args: "key")
    action = SimpleNamespace(action_package_id="package", name="action")

    with pytest.raises(RuntimeError, match="forced warmup failure"), pool.obtain_process_for_action(action):
        pass

    assert fake_process.killed is True
    assert semaphore.release_count == 1


@pytest.mark.real_rcc
def test_real_rcc_artifact_action_vertical(tmp_path):
    import os

    if not os.environ.get("ACTIONS_REAL_RCC_ARTIFACT_TEST"):
        pytest.skip("set ACTIONS_REAL_RCC_ARTIFACT_TEST=1")
    provider = os.environ.get("ACTIONS_RUNTIME_RCC_PROVIDER")
    if not provider:
        pytest.fail("ACTIONS_RUNTIME_RCC_PROVIDER must name the cache provider for real proof")

    from actions.server._actions_import import import_action_package
    from actions.server._actions_process_pool import ActionsProcessPool
    from actions.server._database import Database
    from actions.server._models import Action, ActionPackage, Run, RunStatus, get_model_db_rules
    from actions.server._rcc_runtime_adapter import read_receipt
    import actions.server._models as models
    from actions.server._settings import Settings

    package_dir = tmp_path / "package"
    package_dir.mkdir()
    package_yaml = package_dir / "package.yaml"
    package_yaml.write_text(
        """version: 0.1
spec-version: v2
dependencies:
  conda-forge:
    - python=3.11.11
  pypi:
    - actions-core=1.0.0
"""
    )
    action_file = package_dir / "action.py"
    action_file.write_text(
        "from actions import action\n\n@action\ndef answer() -> str:\n    return 'rcc-v18.19.2'\n"
    )
    db = Database(tmp_path / "server.db")
    with db.connect():
        db.initialize([ActionPackage, Action])
        db.create_tables(get_model_db_rules())
        models._global_db = db
        try:
            import_action_package(
                datadir=tmp_path / "data",
                action_package_dir=str(package_dir),
                disable_not_imported=False,
                skip_lint=True,
                whitelist="",
            )
            package = db.all(ActionPackage)[0]
            action = db.all(Action)[0]
            descriptor = json.loads(package.env_json)["runtime"]
            expected_artifact_digest = "sha256:81fa0aea1b1efe5232cf787725e1bad1258831cb90458469b2f7581f0e11cd01"
            assert descriptor["artifact_digest"] == expected_artifact_digest
            assert descriptor["kind"] == "rcc"
            assert descriptor["rcc_version"] == "v18.19.2"
            for forbidden in (
                "PYTHON_EXE",
                "CONDA_PREFIX",
                "ROBOCORP_HOME",
                "holotree",
                "materialization",
            ):
                assert forbidden not in package.env_json
            settings = Settings(datadir=tmp_path / "data", artifacts_dir=tmp_path / "artifacts")
            settings.reuse_processes = False
            settings.min_processes = 0
            settings.max_processes = 1
            pool = ActionsProcessPool(settings, {package.id: package}, [action])
            try:
                run_dir = tmp_path / "run"
                run_dir.mkdir()
                input_json = run_dir / "input.json"
                result_json = run_dir / "result.json"
                output_file = run_dir / "output.txt"
                input_json.write_text("{}")
                run = Run(
                    id="rcc-real-run", status=RunStatus.NOT_RUN, action_id=action.id,
                    start_time="", run_time=None, inputs="{}", result=None,
                    error_message=None, relative_artifacts_dir="", numbered_id=1,
                )
                with pool.obtain_process_for_action(action) as handle:
                    assert handle.run_action(
                        run, package, action, input_json, run_dir, output_file, result_json,
                        {}, {}, False
                    ) == 0
                    assert json.loads(result_json.read_text())["result"] == "rcc-v18.19.2"
                    receipt = handle._rcc_wrapper.receipt_file
                assert receipt.exists()
                parsed_receipt = read_receipt(receipt, expected_artifact_digest)
                assert parsed_receipt["status"] == "failed"
                assert parsed_receipt["exitCode"] == -1
                assert parsed_receipt["reason"] == "child exited non-zero"
            finally:
                pool.dispose()
        finally:
            models._global_db = None
