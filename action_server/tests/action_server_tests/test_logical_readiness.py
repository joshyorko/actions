"""Selected optional adapter readiness; no RCC/network/container probes."""
import importlib
from types import SimpleNamespace

import pytest
from action_server_tests.test_logical_execution import local as _local
from action_server_tests.test_logical_execution import logical as _logical
from action_server_tests.test_logical_execution import provider as _provider

from actions.server._models import Run
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import RunAttempt
from actions.server.run_outputs.task_service import (
    TaskHostUnavailable,
    TaskPolicy,
    TaskService,
)

local, logical, provider = _local, _logical, _provider
pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def runtime(g):
    value = object.__new__(GeneratedRccExecution)
    value.registry, value.outputs, value.logical_execution = (
        g.registry,
        g.outputs,
        g.execution,
    )
    return value


def task_host(g, snapshot):
    import hashlib
    import zipfile
    from io import BytesIO

    from actions.server.run_outputs.task_host import DetachedTaskHost

    host = object.__new__(DetachedTaskHost)
    host.actor, host.profile = g.actor, snapshot.worker
    host.authority = DetachedActions(g.execution.deployments, g.outputs)
    # Only background-thread state is synthetic; real require_ready, selected
    # immutable Package verification and TaskService admission are exercised.
    host._check_running = lambda: None
    host._runtime = lambda: runtime(g)
    compiled = g.registry.load(snapshot.capability.package_revision)
    with zipfile.ZipFile(BytesIO(compiled.source_archive)) as archive:
        package_yaml = archive.read("package.yaml")
    host.prepared = SimpleNamespace(
        build_identity=SimpleNamespace(
            specification_digest=compiled.rcc_specification_digest,
            artifact_digest=compiled.rcc_artifact_digest,
        ),
        package_yaml_digest="sha256:" + hashlib.sha256(package_yaml).hexdigest(),
    )
    return host


def test_missing_selected_dependency_blocks_task_admission(logical, monkeypatch):
    g = logical
    snapshot = g.outputs.execution_context(g.actor, g.fence)[0]
    tasks = TaskService(
        DetachedActions(g.execution.deployments, g.outputs),
        readiness=task_host(g, snapshot),
        policy=TaskPolicy("readiness", 60000, 100),
    )
    before = (len(g.db.all(Run)), len(g.db.all(RunAttempt)))
    original = importlib.import_module

    def missing(name, *args, **kwargs):
        if name == "duckdb":
            raise ImportError("synthetic private dependency detail")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", missing)
    with pytest.raises(TaskHostUnavailable) as error:
        tasks.create(
            g.actor,
            snapshot.workspace_id,
            snapshot,
            {"value": "fixture"},
            "dependency-absent",
        )
    assert "synthetic private" not in str(error.value)
    assert before == (len(g.db.all(Run)), len(g.db.all(RunAttempt)))


def test_selected_installed_dependency_and_no_engine_probe(logical, monkeypatch):
    g = logical
    snapshot = g.outputs.execution_context(g.actor, g.fence)[0]

    def forbidden(*args, **kwargs):
        raise AssertionError("readiness performed engine/secret/catalog I/O")

    monkeypatch.setattr(g.factory, "open_provider", forbidden)
    monkeypatch.setattr(g.factory, "check_current", forbidden)
    runtime(g)._verified_selection(snapshot)


def test_selected_postgres_csv_does_not_require_unused_duckdb(logical, monkeypatch):
    from uuid import uuid4

    from actions.server.foundry.provider_config import PostgreSQLHost, SecretVersion

    g = logical
    ref = g.descriptor.reference
    config = g.factory.configs[ref]
    host = PostgreSQLHost(
        host="localhost",
        port=1,
        database="synthetic",
        username="synthetic",
        password=SecretVersion(slot=str(uuid4()), version=str(uuid4())),
    )
    g.factory.configs[ref] = config.model_copy(update={"host": host})
    seen = []

    def modules(name):
        seen.append(name)
        if name == "duckdb":
            raise ImportError("unused adapter")
        return SimpleNamespace()

    monkeypatch.setattr(importlib, "import_module", modules)
    g.factory.require_adapter_available(ref, ("records.scan/v1",))
    assert seen == ["psycopg"]


def test_present_dependency_keeps_task_admission_unchanged(logical):
    g = logical
    snapshot = g.outputs.execution_context(g.actor, g.fence)[0]
    tasks = TaskService(
        DetachedActions(g.execution.deployments, g.outputs),
        readiness=task_host(g, snapshot),
        policy=TaskPolicy("readiness", 60000, 100),
    )
    before = (len(g.db.all(Run)), len(g.db.all(RunAttempt)))
    receipt = tasks.create(
        g.actor,
        snapshot.workspace_id,
        snapshot,
        {"value": "fixture"},
        "dependency-present",
    )
    assert receipt.status == "working"
    assert (len(g.db.all(Run)), len(g.db.all(RunAttempt))) == (before[0] + 1, before[1])


def test_postgres_selected_parquet_requires_shared_decoder(logical, monkeypatch):
    from uuid import uuid4

    from actions.server.deployments.provider_registry import ParquetSourceCodec
    from actions.server.foundry.provider_config import PostgreSQLHost, SecretVersion

    g = logical
    original = g.factory.entry(g.descriptor.reference)
    obj = original.source.objects[0]
    codec = ParquetSourceCodec(
        columns=obj.codec.columns,
        max_rows=obj.codec.max_rows,
        max_decoded_bytes=obj.codec.max_decoded_bytes,
        max_field_bytes=obj.codec.max_field_bytes,
        max_row_groups=1,
    )
    source = original.source.model_copy(
        update={"objects": (obj.model_copy(update={"codec": codec}),)}
    )
    descriptor = original.descriptor.model_copy(
        update={"source_revision": source.revision_id}
    )
    ref = descriptor.reference
    host = PostgreSQLHost(
        host="localhost",
        port=1,
        database="synthetic",
        username="synthetic",
        password=SecretVersion(slot=str(uuid4()), version=str(uuid4())),
    )
    config = g.factory.configs[g.descriptor.reference].model_copy(
        update={"provider": ref, "source_revision": source.revision_id, "host": host}
    )
    entry = original.model_copy(
        update={
            "source": source,
            "descriptor": descriptor,
            "config_digest": config.config_digest,
        }
    )
    g.factory.catalog = g.factory.catalog.model_copy(update={"entries": (entry,)})
    g.factory.configs = {ref: config}
    seen = []

    def modules(name):
        seen.append(name)
        if name == "duckdb":
            raise ModuleNotFoundError("decoder unavailable")
        return SimpleNamespace()

    monkeypatch.setattr(importlib, "import_module", modules)
    with pytest.raises(
        ValueError, match="selected logical adapter dependency unavailable"
    ):
        g.factory.require_adapter_available(ref, ("records.scan/v1",))
    assert seen == ["duckdb"]
