"""Synthetic compiler, real common SQL and sealed engines; no RCC claim."""
import json
import os
import threading
import time
from dataclasses import replace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_package_registry import _registry
from action_server_tests.test_generic_work_item_execution import grant
from action_server_tests.test_local_authorization import local as _local
from action_server_tests.test_local_provider_setup import call
from action_server_tests.test_local_provider_setup import grant as provider_grant
from action_server_tests.test_local_provider_setup import prepare as prepare_provider
from action_server_tests.test_local_provider_setup import provider as _provider
from action_server_tests.test_local_provider_setup import request as provider_request
from action_server_tests.test_sealed_postgres import tls_postgres as _tls_postgres
from contract_tests.test_package_revision_compiler import _generated_action_entries

from actions.server._models import load_db
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.ids import DeploymentId
from actions.server.deployments.logical_bindings import (
    BindingField,
    BindingOperation,
    LogicalBindingRequirement,
)
from actions.server.foundry.authoring_bindings import DataBindingChoice
from actions.server.foundry.authoring_values import CanvasBinding
from actions.server.foundry.logical_execution import (
    LogicalExecution,
    LogicalReadRejected,
)
from actions.server.foundry.provider_catalog import PrivateProviderStore
from actions.server.foundry.provider_execution import ConfiguredProviderExecution
from actions.server.foundry.runtime_profile import RuntimeDeploymentSelection
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputControlPlane, RunOutputService

tls_postgres = _tls_postgres
local = _local
provider = _provider
pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.fixture
def logical(provider, request):
    g = provider
    operation = BindingOperation(
        name="records.scan/v1",
        effect="read",
        parameters=(),
        result=(BindingField(name="record_id", kind="string"),),
        max_rows=100,
        max_bytes=getattr(request, "param", 65536),
        timeout_ms=1000,
    )
    g.descriptor = g.descriptor.model_copy(update={"operations": (operation,)})
    g.config = g.config.model_copy(update={"provider": g.descriptor.reference})
    prepare_provider(g)
    provider_grant(
        g,
        ["provider.manage", "provider.inspect", "data.read", "execute", "deploy"],
        g.descriptor.reference,
    )
    call(g, provider_request(g, "configure-host", config=g.config))
    fd = os.open(g.root / "blobs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        with FilesystemOutputProvider(fd) as blobs, load_db(g.root / "server.db") as db:
            registry = _registry(db, blobs)
            app = DeploymentId(str(uuid4()))
            grant(
                db,
                g.actor,
                g.workspace,
                "workspace",
                str(g.workspace.root),
                ["deploy", "execute", "generate_backend", "apply_revision"],
            )
            outcome = registry.compile_trusted_source(
                _generated_action_entries(),
                logical_package_key="scan-context",
                logical_name="Scan context",
                trusted_actor=g.actor,
                workspace_id=g.workspace,
                application_id=app,
                logical_requirements=(
                    LogicalBindingRequirement(
                        id="records", kind="data", operations=(operation,)
                    ),
                ),
            )
            assert outcome.evidence.ready
            package = registry.admit_compiled(
                g.actor, g.workspace, outcome.compiled_package
            )
            cap = registry.capability_refs(package)[0]
            for ref in (g.profile.worker, g.profile.policy, g.profile.output_provider):
                grant(
                    db,
                    g.actor,
                    g.workspace,
                    "reference",
                    reference_grant_subject(ref),
                    ["execute", "deploy"],
                )
            factory = ConfiguredProviderExecution(db, g.root, blobs)
            selection = RuntimeDeploymentSelection(
                registry, SqlFoundryAuthorization(db), g.profile, factory.registry
            )
            spec = selection.select_specification_with_bindings(
                g.actor,
                g.workspace,
                app,
                (package,),
                (CanvasBinding(binding_id="query", capability=cap),),
                (
                    DataBindingChoice(
                        bindingId="query",
                        requirementId="records",
                        provider=g.descriptor.reference,
                    ),
                ),
            )
            deployments = FoundryDeploymentService(
                FoundryRepository(db), registry, SqlFoundryAuthorization(db), registry
            )
            revision = deployments.create(
                g.actor, g.workspace, app, spec, idempotency_key="scan-deploy"
            )
            grant(
                db,
                g.actor,
                g.workspace,
                "reference",
                reference_grant_subject(revision.ref),
                ["execute", "deploy"],
            )
            snapshot = deployments.resolve(g.actor, g.workspace, app, cap).snapshot
            control = RunOutputControlPlane(db, capabilities=registry)
            control.register(snapshot)
            control.grant(g.actor, revision.ref, {"execute", "read", "cancel"})
            outputs = RunOutputService(
                db, {snapshot.provider_key: blobs}, capabilities=registry
            )
            run = outputs.admit(g.actor, snapshot, {"value": "fixture"}, "read-context")
            fence = outputs.claim(run.id, g.profile.worker_id, lease_seconds=60)
            g.db, g.blobs, g.factory, g.registry, g.outputs, g.fence = (
                db,
                blobs,
                factory,
                registry,
                outputs,
                fence,
            )
            g.execution = LogicalExecution(deployments, registry, outputs, factory)
            yield g
    finally:
        os.close(fd)


def prepare(g, **kwargs):
    return g.execution.prepare(
        g.actor,
        g.fence,
        cancelled=kwargs.get("cancelled", threading.Event()),
        deadline=kwargs.get("deadline", time.monotonic() + 5),
    )


def test_real_preparation_context_and_sql_only_recheck(logical, monkeypatch):
    g = logical
    prepared = prepare(g)
    assert json.loads(prepared.context) == {
        "version": "actions.logical-read-context/v1",
        "lookups": [
            {
                "requirementId": "records",
                "operation": "records.scan/v1",
                "rows": [{"record_id": "synthetic"}],
            }
        ],
    }
    for forbidden in (
        g.actor.principal_id,
        g.descriptor.reference.revision_id.root,
        str(g.root),
        "password",
        "host",
    ):
        assert forbidden not in prepared.context.decode()

    def forbidden(*args, **kwargs):
        raise AssertionError("publication performed non-SQL I/O")

    monkeypatch.setattr(g.factory, "check_current", forbidden)
    monkeypatch.setattr(g.factory.registry, "_read", forbidden)
    monkeypatch.setattr(g.registry, "load", forbidden)
    monkeypatch.setattr(PrivateProviderStore, "resolve_secret", forbidden)
    with g.db.transaction():
        g.execution.recheck(g.actor, g.fence, prepared)
    g.execution.release(prepared)
    with pytest.raises(LogicalReadRejected):
        g.execution.recheck(g.actor, g.fence, prepared)


def test_forged_context_or_fence_refused(logical):
    g = logical
    prepared = prepare(g)
    with pytest.raises(LogicalReadRejected):
        g.execution.recheck(g.actor, g.fence, replace(prepared, context=b"{}"))
    with pytest.raises(LogicalReadRejected):
        g.execution.recheck(
            g.actor, g.fence.model_copy(update={"epoch": g.fence.epoch + 1}), prepared
        )


def test_total_deadline_and_cancellation_before_engine(logical, monkeypatch):
    g = logical

    def forbidden(*args, **kwargs):
        raise AssertionError("engine opened")

    monkeypatch.setattr(g.factory, "open_provider", forbidden)
    with pytest.raises(LogicalReadRejected):
        prepare(g, deadline=time.monotonic() - 1)
    event = threading.Event()
    event.set()
    with pytest.raises(LogicalReadRejected):
        prepare(g, cancelled=event)


def test_current_change_refused(logical):
    g = logical
    path = g.root / "provider-state" / "CURRENT"
    raw = path.read_bytes()
    path.chmod(0o600)
    path.write_bytes(b"{}")
    try:
        with pytest.raises(LogicalReadRejected):
            prepare(g)
    finally:
        path.write_bytes(raw)
        path.chmod(0o400)


@pytest.mark.parametrize("logical", [300000], indirect=True)
def test_declared_aggregate_rejected_before_engine(logical, monkeypatch):
    g = logical
    reached = []

    def forbidden(*args, **kwargs):
        reached.append(True)
        raise AssertionError("engine should not be reached")

    monkeypatch.setattr(g.factory, "open_provider", forbidden)
    with pytest.raises(LogicalReadRejected, match="declared aggregate"):
        prepare(g)
    assert not reached


@pytest.mark.parametrize(
    "target", ["grant", "availability", "package", "provenance", "source"]
)
def test_sql_only_recheck_refuses_changed_authority(logical, target):
    from actions.server.foundry.models import (
        FoundryAccessGrant,
        FoundryPackageRevision,
        FoundryRequest,
    )
    from actions.server.foundry.provider_models import (
        FoundryProviderAvailability,
        FoundrySourceRevision,
    )

    g = logical
    prepared = prepare(g)
    with g.db.transaction():
        if target == "grant":
            rows = g.db.all(
                FoundryAccessGrant,
                where="subject_id=?",
                values=[reference_grant_subject(g.descriptor.reference)],
            )
            for row in rows:
                g.db.update_by_id(FoundryAccessGrant, row.id, {"operations_json": "[]"})
        elif target == "availability":
            row = g.db.all(FoundryProviderAvailability)[0]
            g.db.update_by_id(
                FoundryProviderAvailability,
                row.id,
                {"enabled": False, "generation": row.generation + 1},
            )
        elif target == "package":
            row = g.db.all(FoundryPackageRevision)[0]
            g.db.update_by_id(
                FoundryPackageRevision, row.id, {"build_evidence_json": "{}"}
            )
        elif target == "source":
            row = g.db.all(FoundrySourceRevision)[0]
            g.db.update_by_id(FoundrySourceRevision, row.id, {"manifest_json": "{}"})
        else:
            g.db.update_by_id(
                FoundryRequest, g.factory.pointer.generation, {"result_json": "{}"}
            )
    with pytest.raises(LogicalReadRejected):
        g.execution.recheck(g.actor, g.fence, prepared)


def test_total_deadline_during_engine(logical, monkeypatch):
    from contextlib import contextmanager

    g = logical
    observed = []

    @contextmanager
    def slow(*args):
        class Engine:
            def execute(self, actor, operation, parameters, event):
                while not event.is_set():
                    time.sleep(0.002)
                observed.append(True)
                raise ValueError("deadline")

        yield Engine()

    monkeypatch.setattr(g.factory, "open_provider", slow)
    with pytest.raises(LogicalReadRejected):
        prepare(g, deadline=time.monotonic() + 1.0)
    assert observed == [True]


def test_factory_construction_does_not_resolve_secrets(logical, monkeypatch):
    g = logical

    def forbidden(*args, **kwargs):
        raise AssertionError("secret resolved at construction")

    monkeypatch.setattr(PrivateProviderStore, "resolve_secret", forbidden)
    other = ConfiguredProviderExecution(g.db, g.root, g.blobs)
    assert other.pointer == g.factory.pointer


def test_real_tls_engine_through_catalog_factory(logical, tls_postgres):
    from actions.server._local_provider_setup import SecretImport
    from actions.server.foundry.provider_config import PostgreSQLHost, SecretVersion

    g = logical
    expected = prepare(g).context
    refs = [SecretVersion(slot=str(uuid4()), version=str(uuid4())) for _ in range(2)]
    paths = [g.root / "synthetic-password", g.root / "synthetic-ca"]
    for path, data in zip(paths, [tls_postgres.password.encode(), tls_postgres.ca]):
        path.write_bytes(data)
        path.chmod(0o600)
    config = g.config.model_copy(
        update={
            "host": PostgreSQLHost(
                host="127.0.0.1",
                port=tls_postgres.port,
                database="postgres",
                username="scan_reader",
                password=refs[0],
                ca_bundle=refs[1],
            )
        }
    )
    call(
        g,
        provider_request(
            g,
            "configure-host",
            config=config,
            expected_catalog=g.factory.pointer,
            secrets=tuple(
                SecretImport(reference=ref, path=str(path))
                for ref, path in zip(refs, paths)
            ),
        ),
    )
    with pytest.raises(ValueError, match="catalog changed"):
        g.factory.check_current()
    factory = ConfiguredProviderExecution(g.db, g.root, g.blobs)
    execution = LogicalExecution(
        g.execution.deployments, g.registry, g.outputs, factory
    )
    prepared = execution.prepare(
        g.actor, g.fence, cancelled=threading.Event(), deadline=time.monotonic() + 5
    )
    assert prepared.context == expected
    execution.recheck(g.actor, g.fence, prepared)
    execution.release(prepared)


def test_common_postgresql_authority_with_real_duckdb(
    logical, tls_postgres, monkeypatch
):
    from urllib.parse import quote, urlencode

    import psycopg
    from action_server_tests.test_database_shared import _postgresql_schema_url

    from actions.server._database import Database
    from actions.server._models import get_all_model_classes, get_model_db_rules
    from actions.server.run_outputs.models import Workspace

    g = logical
    schema = "logical_" + uuid4().hex
    admin = psycopg.connect(**tls_postgres.admin)
    admin.execute("CREATE SCHEMA " + schema)
    base = (
        "postgresql://postgres:"
        + quote(tls_postgres.admin["password"], safe="")
        + "@127.0.0.1:"
        + str(tls_postgres.port)
        + "/postgres?"
        + urlencode(
            {"sslmode": "verify-full", "sslrootcert": tls_postgres.admin["sslrootcert"]}
        )
    )
    pg = Database(_postgresql_schema_url(base, schema))
    models = get_all_model_classes()
    try:
        with pg.connect():
            pg.initialize(models)
            with pg.transaction():
                pg.create_tables(get_model_db_rules())
                for model in [Workspace] + [
                    model for model in models if model is not Workspace
                ]:
                    for row in g.db.all(model):
                        pg.insert(row)
            registry = _registry(pg, g.blobs)
            factory = ConfiguredProviderExecution(pg, g.root, g.blobs)
            deployments = FoundryDeploymentService(
                FoundryRepository(pg), registry, SqlFoundryAuthorization(pg), registry
            )
            outputs = RunOutputService(
                pg,
                {
                    g.outputs.execution_context(g.actor, g.fence)[
                        0
                    ].provider_key: g.blobs
                },
                capabilities=registry,
            )
            execution = LogicalExecution(deployments, registry, outputs, factory)
            prepared = execution.prepare(
                g.actor,
                g.fence,
                cancelled=threading.Event(),
                deadline=time.monotonic() + 5,
            )
            assert json.loads(prepared.context)["lookups"][0]["rows"] == [
                {"record_id": "synthetic"}
            ]

            def forbidden(*args, **kwargs):
                raise AssertionError("non-SQL publication work")

            monkeypatch.setattr(registry, "load", forbidden)
            monkeypatch.setattr(factory, "check_current", forbidden)
            contender = psycopg.connect(**tls_postgres.admin)
            try:
                contender.execute("SET lock_timeout = '50ms'")
                with pg.transaction():
                    execution.recheck(g.actor, g.fence, prepared)
                    for table, column in (
                        ("foundry_provider_availability", "enabled"),
                        ("foundry_access_grant", "operations_json"),
                    ):
                        with pytest.raises(psycopg.errors.LockNotAvailable):
                            contender.execute(
                                "UPDATE "
                                + schema
                                + "."
                                + table
                                + " SET "
                                + column
                                + "="
                                + column
                            )
                contender.execute(
                    "UPDATE "
                    + schema
                    + ".foundry_provider_availability SET enabled=enabled"
                )
            finally:
                contender.close()
            outputs.cancel(g.actor, g.fence.run_id)
            with pytest.raises(LogicalReadRejected):
                execution.recheck(g.actor, g.fence, prepared)
    finally:
        admin.execute("DROP SCHEMA " + schema + " CASCADE")
        admin.close()


def test_operation_count_bound_before_engine(logical, monkeypatch):
    from actions.server.foundry import logical_execution as module

    g = logical
    assert module.MAX_OPERATIONS == 32
    monkeypatch.setattr(module, "MAX_OPERATIONS", 0)
    with pytest.raises(LogicalReadRejected, match="bounded unambiguous"):
        prepare(g)


def test_changed_result_receipt_rejected(logical, monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace

    g = logical
    original = g.factory.open_provider

    @contextmanager
    def changed(*args):
        with original(*args) as engine:

            class Changed:
                def execute(self, *args):
                    result = engine.execute(*args)
                    return SimpleNamespace(
                        operation=result.operation,
                        contract_digest=result.contract_digest,
                        source_revision=result.source_revision,
                        payload=result.payload,
                        row_count=result.row_count + 1,
                    )

            yield Changed()

    monkeypatch.setattr(g.factory, "open_provider", changed)
    with pytest.raises(LogicalReadRejected, match="result bounds"):
        prepare(g)
