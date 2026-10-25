"""Synthetic RCC result, real eager reads/SQL publication. Not RCC acceptance."""
import hashlib
import json
import threading
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from action_server_tests import test_logical_domain as domain_fixture

from actions.server._models import Run, RunStatus
from actions.server.deployments.package_revision_compiler import (
    PreparedRccEnvironment,
    RccBuildIdentity,
)
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.run_outputs.service import _one

local = domain_fixture.local
provider = domain_fixture.provider
logical = domain_fixture.logical
domain = domain_fixture.domain
tls_postgres = domain_fixture.tls_postgres
pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.mark.parametrize("fault", ["none", "before-spawn", "stage", "cleanup"])
def test_bound_runner_synthetic_completion_and_release(
    domain, tmp_path, monkeypatch, fault
):
    from actions.server.foundry import rcc_execution as module

    if fault == "cleanup" and module.os.name != "posix":
        pytest.skip("synthetic owned process-session cleanup is POSIX-only")

    g = domain
    service, caller, wrapper, seed = domain_fixture.setup(g)
    compiled = g.registry.load(service.snapshot.capability.package_revision)
    with zipfile.ZipFile(BytesIO(compiled.source_archive)) as archive:
        package_yaml = archive.read("package.yaml")
    home = tmp_path / "prepared"
    home.mkdir()
    prepared = PreparedRccEnvironment(
        home,
        "sha256:" + hashlib.sha256(package_yaml).hexdigest(),
        RccBuildIdentity(
            compiled.rcc_specification_digest, compiled.rcc_artifact_digest
        ),
    )
    runner = GeneratedRccExecution(
        g.registry,
        wrapper,
        prepared,
        Path("/usr/bin/true"),
        tmp_path / "execution",
        logical_execution=g.execution,
    )
    monkeypatch.setattr(module, "verify_rcc_version", lambda rcc: None)
    files = {}
    spawned = []
    deadlines = []

    def command(rcc, descriptor, argv, *, receipt_file, **kwargs):
        files["receipt"] = receipt_file
        files["result"] = Path(argv[-3])
        files["context"] = Path(argv[-2])
        files["digest"] = argv[-1]
        if fault == "before-spawn":
            raise RuntimeError("synthetic command failure")
        return list(argv)

    monkeypatch.setattr(module, "build_exec_command", command)

    class Process:
        returncode = 0

        def poll(self):
            return 0

        def wait(self, timeout):
            return 0

    def popen(*args, **kwargs):
        spawned.append(args)
        assert "lookups" in json.loads(files["context"].read_bytes())
        files["result"].write_bytes(b'"fixture"')
        files["receipt"].write_bytes(b"{}")
        return Process()

    monkeypatch.setattr(module.subprocess, "Popen", popen)
    ownership_events = []
    ownership_handles = []

    class Ownership:
        def __init__(self, process, *, owns_session):
            self.process = process
            self.termination_confirmed = fault != "cleanup"
            ownership_handles.append(self)
            self.owns_session = owns_session
            assert owns_session is (module.os.name == "posix")
            ownership_events.append("created")

        def capture(self):
            ownership_events.append("capture")

        def cleanup(self):
            ownership_events.append("cleanup")
            return SimpleNamespace(execution_stopped=self.termination_confirmed)

    # Synthetic Popen has no real PID/group. Replace its ownership boundary,
    # not the removed adapter handle, and verify cleanup gates publication.
    monkeypatch.setattr(module, "_OwnedProcessCapture", Ownership)
    monkeypatch.setattr(
        module, "read_receipt", lambda *args: {"status": "completed", "exitCode": 0}
    )

    def capture(*args):
        args[0]._actions_capture_owned()
        deadlines.append(args[-1])
        measured = dict(
            observedBytes=0,
            retainedBytes=0,
            discardedObservedBytes=0,
            streamComplete=True,
            truncated=False,
        )
        return b"", b"", measured, measured.copy()

    monkeypatch.setattr(runner, "_capture_process", capture)
    original = g.execution.prepare
    observed = []
    preparations = []
    owners = []
    original_begin = g.execution.begin_preparation

    def begin(*args, **kwargs):
        owner = original_begin(*args, **kwargs)
        owners.append(owner)
        return owner

    monkeypatch.setattr(g.execution, "begin_preparation", begin)

    def prepare(*args, deadline, **kwargs):
        observed.append(deadline)
        prepared = original(*args, deadline=deadline, **kwargs)
        preparations.append(prepared)
        return prepared

    monkeypatch.setattr(g.execution, "prepare", prepare)
    if fault == "stage":
        monkeypatch.setattr(
            wrapper,
            "stage",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("synthetic stage failure")
            ),
        )
    try:
        if fault == "none":
            run = runner.execute(
                g.actor, g.fence, cancelled=threading.Event(), timeout_seconds=30
            )
            assert run.status == RunStatus.PASSED
            outer = json.loads(run.result)
            result = outer["result"]
            assert result["version"] == "actions.generated-rcc-execution/v2"
            assert result["logicalReads"] == result["launch"]["logicalReads"]
            assert len(outer["outputs"]) == 4
            assert deadlines == observed
        else:
            expected = "cleanup incomplete" if fault == "cleanup" else "synthetic"
            with pytest.raises(RuntimeError, match=expected):
                runner.execute(
                    g.actor, g.fence, cancelled=threading.Event(), timeout_seconds=30
                )
            assert _one(g.db, Run, g.fence.run_id).status == RunStatus.RUNNING
        assert len(spawned) == (0 if fault == "before-spawn" else 1)
        if fault == "before-spawn":
            assert ownership_events == []
        else:
            expected_events = ["created", "capture"]
            if module.os.name == "posix":
                expected_events.append("cleanup")
            assert ownership_events == expected_events
        if fault != "none":
            from actions.server.run_outputs.service import FenceRejected

            with pytest.raises(FenceRejected, match="reconciliation"):
                runner.execute(
                    g.actor, g.fence, cancelled=threading.Event(), timeout_seconds=30
                )
            assert len(observed) == 1
            assert len(spawned) == (0 if fault == "before-spawn" else 1)
        if fault == "cleanup":
            assert len(owners) == len(preparations) == 1
            assert g.execution._issued == {id(preparations[0]): preparations[0]}
            assert not owners[0].thread.is_alive()
            assert not g.execution.close(0)
            assert g.execution._issued == {id(preparations[0]): preparations[0]}
        else:
            assert not g.execution._issued
            assert g.execution.close(0)
    finally:
        if fault == "cleanup" and preparations:
            # Only this synthetic process owner can resolve its simulated hold.
            # No real process was launched; require the fake's terminal state,
            # then exercise the exact owner/result release API (not dict edits).
            assert len(ownership_handles) == len(owners) == len(preparations) == 1
            handle = ownership_handles[0]
            assert handle.process.wait(timeout=0) == 0
            handle.termination_confirmed = True
            assert handle.cleanup().execution_stopped
            g.execution.release_preparation(owners[0], preparations[0])
            assert not g.execution._issued
        assert g.execution.close(2)
