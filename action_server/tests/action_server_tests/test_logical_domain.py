"""Synthetic generated receipts, real common SQL and issued logical preparation."""
import copy
import hashlib
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from action_server_tests.test_logical_execution import local as _local
from action_server_tests.test_logical_execution import logical as _logical
from action_server_tests.test_logical_execution import prepare
from action_server_tests.test_logical_execution import provider as _provider
from action_server_tests.test_sealed_postgres import tls_postgres as _tls_postgres

from actions.server._models import Run, RunStatus
from actions.server.foundry.logical_receipts import (
    derive_summary,
    retained_summary,
    validate_bound_record,
)
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.service import _canonical, _one, _transaction, _update

local, provider, tls_postgres = _local, _provider, _tls_postgres

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def setup(g):
    snapshot = g.outputs.execution_context(g.actor, g.fence)[0]
    owner = StandaloneActionExecution(g.execution.deployments, g.outputs, snapshot)
    caller = ManagedCaller(actor=g.actor, worker_id=g.fence.owner_id)
    seed = dict(
        version="actions.generated-rcc-dispatch/v2",
        mode="standalone",
        claim=None,
        fence=g.fence.model_dump(),
        launch=None,
    )
    with _transaction(g.db):
        _update(g.db, Run, g.fence.run_id, {"result": _canonical(seed, 65536)})
    ticket = owner.ticket(caller, _one(g.db, Run, g.fence.run_id))
    return owner, caller, owner.outputs(caller, ticket), seed


def measured(g, wrapper, seed, prepared):
    snapshot = prepared.snapshot
    compiled = g.registry.load(snapshot.capability.package_revision)
    run = _one(g.db, Run, g.fence.run_id)
    summary = derive_summary(prepared).model_dump(mode="json")
    fixed = dict(
        sourceArtifactDigest=compiled.source_artifact_digest,
        packageRevision=compiled.package_revision_id.root,
        runtimePlanDigest=snapshot.runtime_plan.plan_digest.root,
        rccSpecificationDigest=compiled.rcc_specification_digest,
        rccArtifactDigest=compiled.rcc_artifact_digest,
    )
    lineage = dict(
        packageRevision=snapshot.capability.package_revision.model_dump(mode="json"),
        runtimePlan=snapshot.runtime_plan.model_dump(mode="json"),
        workItemClaim=seed["claim"],
        runId=run.id,
        attemptFence=g.fence.model_dump(),
    )
    launch = dict(
        id=str(uuid4()),
        workItemClaim=seed["claim"],
        lineage=lineage,
        inputDigest=digest(_canonical(json.loads(run.inputs), 262144).encode()),
        logicalReads=summary,
        **fixed,
    )
    payloads = [
        ("generated-action-result.json", b'"fixture"'),
        ("rcc-receipt.json", b"{}"),
        ("rcc-stdout.log", b""),
        ("rcc-stderr.log", b""),
    ]
    refs, records = [], []
    for name, data in payloads:
        ref = wrapper.stage(
            g.fence,
            [data],
            name=name,
            media_type="application/octet-stream",
            retention_seconds=3600,
        )
        refs.append(ref)
        records.append(
            dict(
                name=name,
                ref=ref.model_dump(mode="json"),
                digest=digest(data),
                size=len(data),
            )
        )
    stream = dict(
        digest=digest(b""),
        observedBytes=0,
        retainedBytes=0,
        discardedObservedBytes=0,
        streamComplete=True,
        truncated=False,
    )
    execution = dict(
        status="completed",
        resultDigest=digest(payloads[0][1]),
        receiptDigest=digest(b"{}"),
        artifactDigest=compiled.rcc_artifact_digest,
        stdout=stream,
        stderr=stream.copy(),
    )
    journal = {**seed, "launch": launch, "execution": execution}
    with _transaction(g.db):
        _update(g.db, Run, run.id, {"result": _canonical(journal, 65536)})
    result = dict(
        version="actions.generated-rcc-execution/v2",
        mode=seed["mode"],
        claim=seed["claim"],
        lineage=lineage,
        launch=launch,
        publicationFence=g.fence.model_dump(),
        execution=execution,
        outputs=records,
        actionResult="fixture",
        logicalReads=summary,
        **fixed,
    )
    return refs, result


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def test_bound_publication_requires_issued_guard_and_cleanup(domain):
    g = domain
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    with pytest.raises(ValueError, match="issued logical"):
        wrapper.publish(g.actor, g.fence, refs, result)
    with _transaction(g.db), pytest.raises(ValueError, match="exact invocation"):
        with wrapper.bind_logical_execution(g.execution, prepared):
            pass
    with wrapper.bind_logical_execution(g.execution, replace(prepared)):
        with pytest.raises(ValueError, match="unissued"):
            wrapper.publish(g.actor, g.fence, refs, result)
    with wrapper.bind_logical_execution(g.execution, prepared):
        with pytest.raises(ValueError, match="exact invocation"):
            with wrapper.bind_logical_execution(g.execution, prepared):
                pass
        wrapper.publish(g.actor, g.fence, refs, result)
    assert wrapper._logical_binding is None
    run = _one(g.db, Run, g.fence.run_id)
    assert run.status == RunStatus.PASSED
    assert owner.ticket(caller, run) == wrapper.ticket
    from types import SimpleNamespace

    from actions.server.run_outputs.task_service import TaskService

    outer = json.loads(run.result)
    readback = TaskService._result(
        SimpleNamespace(db=g.db, outputs=g.outputs),
        g.actor,
        owner.snapshot,
        run,
        g.fence,
        outer,
        outer["result"],
    )
    assert readback["structuredContent"]["runId"] == run.id
    with pytest.raises(ValueError, match="issued logical"):
        wrapper.publish(g.actor, g.fence, refs, result)


@pytest.mark.parametrize(
    "mutation",
    [
        "summary",
        "row-limit",
        "source",
        "contract",
        "launch",
        "fence",
        "inventory",
        "bool-size",
        "extra",
        "result",
        "stream",
    ],
)
def test_bound_receipt_tampering_refused(domain, mutation):
    g = domain
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    bad = copy.deepcopy(result)
    bad["logicalReads"] = copy.deepcopy(bad["logicalReads"])
    if mutation == "summary":
        bad["logicalReads"]["contextDigest"] = "sha256:" + "f" * 64
    elif mutation == "row-limit":
        bad["launch"]["logicalReads"]["operations"][0]["rowCount"] = 101
    elif mutation == "source":
        bad["launch"]["logicalReads"]["operations"][0]["sourceRevision"] = (
            "sha256:" + "f" * 64
        )
    elif mutation == "contract":
        bad["launch"]["logicalReads"]["operations"][0]["contractDigest"] = (
            "sha256:" + "f" * 64
        )
    elif mutation == "launch":
        bad["launch"]["inputDigest"] = "sha256:" + "f" * 64
    elif mutation == "fence":
        bad["publicationFence"]["epoch"] += 1
    elif mutation == "inventory":
        bad["outputs"].pop()
    elif mutation == "bool-size":
        bad["outputs"][0]["size"] = True
    elif mutation == "extra":
        bad["privateConfig"] = "secret"
    elif mutation == "result":
        bad["actionResult"] = "changed"
    elif mutation == "stream":
        bad["execution"]["stdout"]["retainedBytes"] = True
    with pytest.raises(ValueError):
        validate_bound_record(
            g.db,
            g.registry,
            owner.snapshot,
            _one(g.db, Run, g.fence.run_id),
            g.fence,
            bad,
            claim=None,
            terminal=True,
            outputs=refs,
        )
    assert _one(g.db, Run, g.fence.run_id).status == RunStatus.RUNNING


def test_guard_revocation_and_transaction_rollback(domain):
    g = domain
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        with pytest.raises(RuntimeError):
            with _transaction(g.db):
                wrapper.publish(g.actor, g.fence, refs, result)
                raise RuntimeError("rollback")
    assert _one(g.db, Run, g.fence.run_id).status == RunStatus.RUNNING
    g.execution.release(prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        with pytest.raises(ValueError, match="unissued"):
            wrapper.publish(g.actor, g.fence, refs, result)


def test_retained_summary_does_not_read_source_or_secrets(domain, monkeypatch):
    g = domain
    prepared = prepare(g)

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected engine or secret I/O")

    monkeypatch.setattr(g.factory, "open_provider", forbidden)
    monkeypatch.setattr(g.factory, "check_current", forbidden)
    summary = derive_summary(prepared)
    assert (
        retained_summary(
            g.db, g.registry, prepared.snapshot, summary.model_dump(mode="json")
        )
        == summary
    )


@pytest.fixture(params=["sqlite", "postgresql"])
def domain(logical, request):
    if request.param == "sqlite":
        yield logical
        return
    from types import SimpleNamespace
    from urllib.parse import quote, urlencode

    import psycopg
    from action_server_tests.test_database_shared import _postgresql_schema_url
    from action_server_tests.test_foundry_package_registry import _registry

    from actions.server._database import Database
    from actions.server._models import get_all_model_classes, get_model_db_rules
    from actions.server.deployments.foundry_repository import FoundryRepository
    from actions.server.deployments.foundry_service import FoundryDeploymentService
    from actions.server.foundry.logical_execution import LogicalExecution
    from actions.server.foundry.provider_execution import ConfiguredProviderExecution
    from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
    from actions.server.run_outputs.models import Workspace
    from actions.server.run_outputs.service import RunOutputService

    tls = request.getfixturevalue("tls_postgres")
    g = SimpleNamespace(**vars(logical))
    schema = "logical_domain_" + uuid4().hex
    admin = psycopg.connect(**tls.admin)
    admin.execute("CREATE SCHEMA " + schema)
    base = (
        "postgresql://postgres:"
        + quote(tls.admin["password"], safe="")
        + "@127.0.0.1:"
        + str(tls.port)
        + "/postgres?"
        + urlencode({"sslmode": "verify-full", "sslrootcert": tls.admin["sslrootcert"]})
    )
    pg = Database(_postgresql_schema_url(base, schema))
    try:
        with pg.connect():
            models = get_all_model_classes()
            pg.initialize(models)
            with pg.transaction():
                pg.create_tables(get_model_db_rules())
                for model in [Workspace] + [m for m in models if m is not Workspace]:
                    for row in g.db.all(model):
                        pg.insert(row)
            g.db = pg
            g.registry = _registry(pg, g.blobs)
            g.factory = ConfiguredProviderExecution(pg, g.root, g.blobs)
            deployments = FoundryDeploymentService(
                FoundryRepository(pg),
                g.registry,
                SqlFoundryAuthorization(pg),
                g.registry,
            )
            snapshot = logical.outputs.execution_context(g.actor, g.fence)[0]
            g.outputs = RunOutputService(
                pg, {snapshot.provider_key: g.blobs}, capabilities=g.registry
            )
            g.execution = LogicalExecution(
                deployments, g.registry, g.outputs, g.factory
            )
            yield g
    finally:
        admin.execute("DROP SCHEMA " + schema + " CASCADE")
        admin.close()


@pytest.fixture
def logical(provider, request, monkeypatch):
    if "generic_queue" in request.node.name:
        from actions.server.deployments.foundry_service import FoundryDeploymentService
        from actions.server.deployments.foundry_values import (
            CapabilityWorkItemPolicy,
            WorkItemDeclaration,
        )
        from actions.server.foundry.package_registry import FoundryPackageRegistry

        original_compile = FoundryPackageRegistry.compile_trusted_source
        original_create = FoundryDeploymentService.create

        def compile_bound(self, *args, **kwargs):
            kwargs["work_items"] = WorkItemDeclaration(
                mode="consumer", allow_outputs=False
            )
            return original_compile(self, *args, **kwargs)

        def create_bound(self, actor, workspace, app, spec, **kwargs):
            capability = spec.capability_plans[0].capability
            policy = CapabilityWorkItemPolicy(
                capability=capability,
                input_mode="claim",
                input_queue="records-input",
                max_output_items=0,
                max_output_bytes=0,
            )
            spec = spec.model_copy(update={"work_item_policies": (policy,)})
            return original_create(self, actor, workspace, app, spec, **kwargs)

        monkeypatch.setattr(
            FoundryPackageRegistry, "compile_trusted_source", compile_bound
        )
        monkeypatch.setattr(FoundryDeploymentService, "create", create_bound)
    yield from _logical.__wrapped__(provider, request)


def test_generic_queue_publication_and_finish_are_atomic(domain):
    from action_server_tests.test_generic_work_item_execution import grant

    from actions.server.data_queries.review_models import FencedWorkItem
    from actions.server.foundry.generic_work_item_execution import (
        GenericWorkItemExecution,
    )
    from actions.server.foundry.sql_authorization import reference_grant_subject
    from actions.server.managed_work_items.authorization import SqlQueueAuthorization
    from actions.server.managed_work_items.contracts import Permission

    g = domain
    snapshot = g.outputs.execution_context(g.actor, g.fence)[0]
    policy = g.execution.repository.get_revision(
        snapshot.deployment
    ).revision.specification.work_item_policies[0]
    grant(
        g.db,
        g.actor,
        g.workspace,
        "reference",
        reference_grant_subject(snapshot.deployment),
        [p.value for p in Permission],
    )
    owner = GenericWorkItemExecution(
        g.execution.deployments,
        g.outputs,
        snapshot,
        policy,
        SqlQueueAuthorization(g.db),
    )
    caller = ManagedCaller(actor=g.actor, worker_id=g.fence.owner_id)
    grant(
        g.db,
        g.actor,
        g.workspace,
        "workspace",
        str(g.workspace.root),
        [p.value for p in Permission],
    )
    item = owner.enqueue(caller, {"value": "fixture"}, "bound-input")
    claim = owner.queue(policy.input_queue).reserve_item_fenced(
        item, caller.worker_id, lease_seconds=60
    )
    ticket = owner.dispatch(caller, claim, lease_seconds=60)
    g.fence = ticket.fence
    wrapper = owner.outputs(caller, ticket)
    seed = json.loads(_one(g.db, Run, g.fence.run_id).result)
    assert seed["version"] == "actions.generated-rcc-dispatch/v2"
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        with pytest.raises(RuntimeError):
            with _transaction(g.db):
                wrapper.publish(g.actor, g.fence, refs, result)
                raise RuntimeError("rollback queue finish")
    assert _one(g.db, Run, g.fence.run_id).status == RunStatus.RUNNING
    assert _one(g.db, FencedWorkItem, item).state != "COMPLETED"
    with wrapper.bind_logical_execution(g.execution, prepared):
        wrapper.publish(g.actor, g.fence, refs, result)
    retained = owner.read_execution(caller, item)
    assert retained[0].status == RunStatus.PASSED
    assert retained[2] == ticket
    from actions.server.managed_work_items.generic_service import (
        GenericManagedWorkItemsService,
    )

    managed = GenericManagedWorkItemsService(owner)
    assert len(managed._artifacts(caller, retained)) == 4


def test_new_guard_is_sql_only_and_rechecks_live_grants(domain, monkeypatch):
    from actions.server.foundry.models import FoundryAccessGrant

    g = domain
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):

        def forbidden(*args, **kwargs):
            raise AssertionError(
                "artifact/engine/secret I/O inside new publication guard"
            )

        monkeypatch.setattr(g.registry, "load", forbidden)
        monkeypatch.setattr(g.factory, "open_provider", forbidden)
        monkeypatch.setattr(g.factory, "check_current", forbidden)
        with _transaction(g.db):
            wrapper._logical_publication(
                g.actor, g.fence, refs, result, _one(g.db, Run, g.fence.run_id)
            )
        with _transaction(g.db):
            for grant in g.db.all(FoundryAccessGrant):
                if grant.principal_id == g.actor.principal_id:
                    _update(
                        g.db, FoundryAccessGrant, grant.id, {"operations_json": "[]"}
                    )
        with _transaction(g.db), pytest.raises(ValueError):
            wrapper._logical_publication(
                g.actor, g.fence, refs, result, _one(g.db, Run, g.fence.run_id)
            )


@pytest.mark.parametrize(
    "damage", ["duplicate-carrier", "pending-execution", "bool-fence"]
)
def test_retained_v2_carrier_is_closed(domain, damage):
    g = domain
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    run = _one(g.db, Run, g.fence.run_id)
    journal = json.loads(run.result)
    if damage == "duplicate-carrier":
        run.result = run.result.replace("{", '{"mode":"standalone",', 1)
    elif damage == "pending-execution":
        journal["execution"]["stdout"]["observedBytes"] = True
        run.result = _canonical(journal, 65536)
    else:
        journal["fence"]["epoch"] = True
        run.result = _canonical(journal, 65536)
    with pytest.raises(ValueError):
        validate_bound_record(
            g.db,
            g.registry,
            owner.snapshot,
            run,
            g.fence,
            journal,
            claim=None,
            terminal=False,
        )
