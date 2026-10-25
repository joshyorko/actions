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


@pytest.mark.parametrize("fault", ["none", "before-spawn", "stage"])
def test_bound_runner_synthetic_completion_and_release(
    domain, tmp_path, monkeypatch, fault
):
    from actions.server.foundry import rcc_execution as module

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
    monkeypatch.setattr(
        module,
        "RccProcessHandle",
        lambda process, receipt: SimpleNamespace(process=process),
    )
    monkeypatch.setattr(
        module, "read_receipt", lambda *args: {"status": "completed", "exitCode": 0}
    )

    def capture(*args):
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

    def prepare(*args, deadline, **kwargs):
        observed.append(deadline)
        return original(*args, deadline=deadline, **kwargs)

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
            with pytest.raises(RuntimeError, match="synthetic"):
                runner.execute(
                    g.actor, g.fence, cancelled=threading.Event(), timeout_seconds=30
                )
            assert _one(g.db, Run, g.fence.run_id).status == RunStatus.RUNNING
        assert len(spawned) == (0 if fault == "before-spawn" else 1)
        if fault != "none":
            from actions.server.run_outputs.service import FenceRejected

            with pytest.raises(FenceRejected, match="reconciliation"):
                runner.execute(
                    g.actor, g.fence, cancelled=threading.Event(), timeout_seconds=30
                )
            assert len(observed) == 1
            assert len(spawned) == (0 if fault == "before-spawn" else 1)
        assert not g.execution._issued
        assert g.execution.close(0)
    finally:
        assert g.execution.close(2)
