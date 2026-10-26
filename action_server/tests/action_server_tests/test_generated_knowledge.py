"""Generated host preparation with synthetic compiler; no actual RCC claim."""
import json
import os
import threading
import time
from dataclasses import replace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_package_registry import _registry
from action_server_tests.test_generic_work_item_execution import grant
from action_server_tests.test_knowledge_host import configured, provision
from action_server_tests.test_local_knowledge_setup import (
    knowledge as knowledge_fixture,
)
from action_server_tests.test_local_knowledge_setup import local as local_fixture
from action_server_tests.test_local_knowledge_setup import provider as provider_fixture
from action_server_tests.test_local_provider_setup import call
from action_server_tests.test_local_provider_setup import grant as provider_grant
from action_server_tests.test_local_provider_setup import request as provider_request
from contract_tests.test_package_revision_compiler import _generated_action_entries

from actions.server._models import Run, RunStatus, load_db
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.ids import DeploymentId
from actions.server.deployments.logical_bindings import (
    BindingField,
    BindingOperation,
    LogicalBindingRequirement,
    LogicalInvocation,
)
from actions.server.foundry.authoring_bindings import DataBindingChoice
from actions.server.foundry.authoring_values import CanvasBinding
from actions.server.foundry.logical_execution import (
    LogicalExecution,
    LogicalReadRejected,
)
from actions.server.foundry.logical_receipts import (
    _projected_summary,
    _retained_projection,
    derive_summary,
)
from actions.server.foundry.provider_execution import ConfiguredProviderExecution
from actions.server.foundry.runtime_profile import RuntimeDeploymentSelection
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import (
    RunOutputControlPlane,
    RunOutputService,
    _one,
)

local, provider, knowledge = local_fixture, provider_fixture, knowledge_fixture
pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def entries():
    source = _generated_action_entries()
    source[0] = replace(
        source[0],
        content=source[0].content.replace(
            b"actions-core=1.0.2", b"actions-core=1.1.0a4"
        ),
    )
    return source


@pytest.fixture
def generated_knowledge(knowledge, request):
    g = knowledge
    operation = BindingOperation(
        name="documents.ingest/v1",
        effect="write",
        parameters=(),
        result=(BindingField(name="result_json", kind="string"),),
        max_rows=100,
        max_bytes=65536,
        timeout_ms=1000,
    )
    g.descriptor = g.descriptor.model_copy(
        update={"operations": (operation, search_operation())}
    )
    call(g, provider_request(g, "register-revision", descriptor=g.descriptor))
    provider_grant(
        g,
        ["provider.manage", "provider.inspect", "knowledge.read", "execute", "deploy"],
        g.descriptor.reference,
    )
    configured(g)
    provision(g)
    names = (
        ("documents_one", "documents_two")
        if getattr(request, "param", None) == "multiple"
        else ("documents",)
    )
    requirements = tuple(
        LogicalBindingRequirement(
            id=name,
            kind="knowledge",
            operations=(operation,),
            invocations=(LogicalInvocation(operation=operation.name, inputs=()),),
        )
        for name in names
    )
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
                entries(),
                logical_package_key="knowledge-context",
                logical_name="Scan context",
                trusted_actor=g.actor,
                workspace_id=g.workspace,
                application_id=app,
                logical_requirements=requirements,
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
                tuple(
                    DataBindingChoice(
                        bindingId="query",
                        requirementId=name,
                        provider=g.descriptor.reference,
                    )
                    for name in names
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


def test_generated_ingestion_stays_provisional_and_has_closed_context(
    generated_knowledge, monkeypatch
):
    g = generated_knowledge
    prepared = g.execution.prepare(
        g.actor, g.fence, cancelled=threading.Event(), deadline=time.monotonic() + 20
    )
    context = json.loads(prepared.context)
    assert context["version"] == "actions.logical-context/v2"
    (lookup,) = context["lookups"]
    assert lookup["kind"] == "knowledge" and lookup["parameters"] == {}
    result = json.loads(lookup["result"]["result_json"])
    assert result["status"] == "staged"
    assert _one(g.db, Run, g.fence.run_id).status != RunStatus.PASSED
    summary = derive_summary(prepared)
    assert summary.version == "actions.logical-receipt/v2"
    assert (
        _projected_summary(
            _retained_projection(g.db, g.registry, prepared.snapshot),
            summary.model_dump(mode="json"),
        )
        == summary
    )
    with pytest.raises(Exception):
        with g.outputs.resolve(
            g.actor, prepared.snapshot.workspace_id, result["corpusHandle"]
        ):
            pass

    def forbidden(*a, **kw):
        raise AssertionError("publication performed I/O")

    monkeypatch.setattr(g.factory, "check_current", forbidden)
    monkeypatch.setattr(g.factory.registry, "_read", forbidden)
    monkeypatch.setattr(g.registry, "load", forbidden)
    with g.db.transaction():
        g.execution.recheck(g.actor, g.fence, prepared)
    g.execution.release(prepared)
    with pytest.raises(LogicalReadRejected):
        g.execution.recheck(g.actor, g.fence, prepared)


def publish_generated(g, prepared):
    from action_server_tests.test_logical_domain import measured

    from actions.server.foundry.standalone_execution import StandaloneActionExecution
    from actions.server.managed_work_items.contracts import ManagedCaller
    from actions.server.run_outputs.service import _canonical, _transaction, _update

    owner = StandaloneActionExecution(
        g.execution.deployments, g.outputs, prepared.snapshot
    )
    caller = ManagedCaller(actor=g.actor, worker_id=g.fence.owner_id)
    seed = dict(
        version="actions.generated-rcc-dispatch/v3",
        mode="standalone",
        claim=None,
        fence=g.fence.model_dump(),
        launch=None,
    )
    with _transaction(g.db):
        _update(g.db, Run, g.fence.run_id, {"result": _canonical(seed, 65536)})
    ticket = owner.ticket(caller, _one(g.db, Run, g.fence.run_id))
    wrapper = owner.outputs(caller, ticket)
    refs, result = measured(g, wrapper, seed, prepared)
    result["version"] = "actions.generated-rcc-execution/v3"
    for item in prepared.knowledge:
        pending = item.ingestion
        if pending is not None:
            refs.append(pending.output)
            result["outputs"].append(
                dict(
                    name=pending.output_name,
                    ref=pending.output.model_dump(mode="json"),
                    digest=pending.corpus_digest,
                    size=pending.corpus_size,
                )
            )
    return owner, caller, wrapper, refs, result


def test_generated_publication_and_retained_source_join(generated_knowledge):
    import copy

    from actions.server.foundry.generated_knowledge import _ingestion_source
    from actions.server.foundry.logical_receipts import validate_bound_record
    from actions.server.run_outputs.detached import DetachedActions
    from actions.server.run_outputs.task_service import TaskPolicy, TaskService

    g = generated_knowledge
    prepared = g.execution.prepare(
        g.actor, g.fence, cancelled=threading.Event(), deadline=time.monotonic() + 20
    )
    owner, caller, wrapper, refs, result = publish_generated(g, prepared)
    for mutation in (
        "missing-corpus",
        "wrong-handle",
        "wrong-fence",
        "wrong-parameters",
    ):
        bad = copy.deepcopy(result)
        chosen = bad["logicalReads"]["operations"][0]
        if mutation == "missing-corpus":
            bad["outputs"].pop()
        elif mutation == "wrong-handle":
            chosen["knowledge"]["corpusHandle"] = "art_" + "a" * 22
        elif mutation == "wrong-fence":
            chosen["knowledge"]["sourceFence"]["epoch"] += 1
        else:
            chosen["parametersDigest"] = "sha256:" + "f" * 64
        with pytest.raises(ValueError):
            validate_bound_record(
                g.db,
                g.registry,
                prepared.snapshot,
                _one(g.db, Run, g.fence.run_id),
                g.fence,
                bad,
                claim=None,
                terminal=True,
                outputs=refs,
            )
    with wrapper.bind_logical_execution(g.execution, prepared):
        wrapper.publish(g.actor, g.fence, refs, result)
    run = _one(g.db, Run, g.fence.run_id)
    assert run.status == RunStatus.PASSED
    assert owner.ticket(caller, run) == wrapper.ticket
    outer = json.loads(run.result)

    class ReadOnlyReadiness:
        def require_ready(self, actor, snapshot):
            raise AssertionError("Retained-result fixture must not dispatch work")

    task_service = TaskService(
        DetachedActions(owner.deployments, g.outputs),
        readiness=ReadOnlyReadiness(),
        policy=TaskPolicy(
            "retained-result-fixture", ttl_ms=60000, poll_interval_ms=1000
        ),
    )
    task_service._result(
        g.actor,
        owner.snapshot,
        run,
        g.fence,
        outer,
        outer["result"],
    )
    evidence, snapshot, pins = _ingestion_source(
        g.outputs,
        g.actor,
        prepared.knowledge[0].evidence.corpus_handle,
        g.spec.reference,
        g.descriptor.reference,
    )
    assert evidence == prepared.knowledge[0].evidence and len(pins) == 4
    g.execution.release(prepared)


def search_operation():
    return BindingOperation(
        name="documents.search/v1",
        effect="read",
        parameters=tuple(
            BindingField(name=name, kind=kind)
            for name, kind in [
                ("ingestion_handle", "string"),
                ("query", "string"),
                ("offset", "integer"),
                ("limit", "integer"),
            ]
        ),
        result=(BindingField(name="result_json", kind="string"),),
        max_rows=20,
        max_bytes=65536,
        timeout_ms=1000,
    )


def admit_search(g, handle):
    from contract_tests.test_package_revision_compiler import _FakeCompilerExecutor

    from actions.server.deployments.logical_bindings import LogicalInputMapping

    class SearchCompiler(_FakeCompilerExecutor):
        def import_action(self, *args):
            value = super().import_action(*args)
            schema = value["actions"][0]["input_schema"]
            for field in search_operation().parameters:
                schema["properties"][field.name] = {"type": field.kind}
                schema["required"].append(field.name)
            return value

    g.registry._executor = SearchCompiler()
    source = entries()
    source[1] = replace(
        source[1],
        content=b"from actions import action\n@action\ndef generated_echo(value: str, ingestion_handle: str, query: str, offset: int, limit: int) -> str:\n    return value\n",
    )
    operation = search_operation()
    requirement = LogicalBindingRequirement(
        id="documents_search",
        kind="knowledge",
        operations=(operation,),
        invocations=(
            LogicalInvocation(
                operation=operation.name,
                inputs=tuple(
                    LogicalInputMapping(parameter=f.name, input=f.name)
                    for f in operation.parameters
                ),
            ),
        ),
    )
    app = DeploymentId(str(uuid4()))
    compiled = g.registry.compile_trusted_source(
        source,
        logical_package_key="knowledge-search",
        logical_name="Knowledge search",
        trusted_actor=g.actor,
        workspace_id=g.workspace,
        application_id=app,
        logical_requirements=(requirement,),
    )
    assert compiled.evidence.ready, compiled.evidence
    package = g.registry.admit_compiled(g.actor, g.workspace, compiled.compiled_package)
    cap = g.registry.capability_refs(package)[0]
    selection = RuntimeDeploymentSelection(
        g.registry, SqlFoundryAuthorization(g.db), g.profile, g.factory.registry
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
                requirementId=requirement.id,
                provider=g.descriptor.reference,
            ),
        ),
    )
    revision = g.execution.deployments.create(
        g.actor, g.workspace, app, spec, idempotency_key="search-deploy"
    )
    grant(
        g.db,
        g.actor,
        g.workspace,
        "reference",
        reference_grant_subject(revision.ref),
        ["execute", "deploy"],
    )
    snapshot = g.execution.deployments.resolve(g.actor, g.workspace, app, cap).snapshot
    control = RunOutputControlPlane(g.db, capabilities=g.registry)
    control.register(snapshot)
    control.grant(g.actor, revision.ref, {"execute", "read", "cancel"})
    inputs = dict(
        value="fixture", ingestion_handle=handle, query="synthetic", offset=0, limit=20
    )
    run = g.outputs.admit(g.actor, snapshot, inputs, "search-context")
    g.fence = g.outputs.claim(run.id, g.profile.worker_id, lease_seconds=60)


def test_search_joins_successful_generated_ingestion_and_rechecks_provenance(
    generated_knowledge,
):
    from actions.server.run_outputs.service import _canonical, _transaction, _update

    g = generated_knowledge
    prepared = g.execution.prepare(
        g.actor, g.fence, cancelled=threading.Event(), deadline=time.monotonic() + 20
    )
    owner, caller, wrapper, refs, result = publish_generated(g, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        wrapper.publish(g.actor, g.fence, refs, result)
    handle = prepared.knowledge[0].evidence.corpus_handle
    g.execution.release(prepared)
    admit_search(g, handle)
    search = g.execution.prepare(
        g.actor, g.fence, cancelled=threading.Event(), deadline=time.monotonic() + 20
    )
    inner = json.loads(
        json.loads(search.context)["lookups"][0]["result"]["result_json"]
    )
    assert (
        inner["total"] == 1
        and inner["hits"][0]["text"] == "Retained synthetic document"
    )
    # Operation timeout applies to preparation, not subsequent generated work.
    search.knowledge[0].budget.deadline = 0
    g.execution.recheck(g.actor, g.fence, search)
    owner, caller, wrapper, refs, result = publish_generated(g, search)
    with wrapper.bind_logical_execution(g.execution, search):
        wrapper.publish(g.actor, g.fence, refs, result)
    run = _one(g.db, Run, g.fence.run_id)
    assert owner.ticket(caller, run) == wrapper.ticket
    original = run.result
    for mutation in ("sourceFence", "corpusDigest", "corpusOutput"):
        outer = json.loads(original)
        for summary in (
            outer["result"]["logicalReads"],
            outer["result"]["launch"]["logicalReads"],
        ):
            evidence = summary["operations"][0]["knowledge"]
            if mutation == "sourceFence":
                evidence[mutation]["epoch"] += 1
            elif mutation == "corpusDigest":
                evidence[mutation] = "sha256:" + "f" * 64
            else:
                evidence[mutation] = "knowledge-" + "f" * 64 + ".json"
        with _transaction(g.db):
            _update(g.db, Run, run.id, {"result": _canonical(outer, 2 * 1024 * 1024)})
        with pytest.raises(ValueError):
            owner.ticket(caller, _one(g.db, Run, run.id))
    with _transaction(g.db):
        _update(g.db, Run, run.id, {"result": original})
    g.execution.release(search)


@pytest.mark.parametrize("generated_knowledge", ["multiple"], indirect=True)
def test_multiple_ingestions_have_distinct_canonical_outputs(generated_knowledge):
    g = generated_knowledge
    prepared = g.execution.prepare(
        g.actor, g.fence, cancelled=threading.Event(), deadline=time.monotonic() + 20
    )
    assert len(prepared.knowledge) == 2
    assert len({item.ingestion.operation_id for item in prepared.knowledge}) == 2
    assert len({item.ingestion.output_name for item in prepared.knowledge}) == 2
    # Finished provider operation timeouts do not cap later RCC execution.
    for item in prepared.knowledge:
        item.budget.deadline = 0
        item.ingestion.budget.deadline = 0
    owner, caller, wrapper, refs, result = publish_generated(g, prepared)
    assert len(refs) == 6
    with wrapper.bind_logical_execution(g.execution, prepared):
        wrapper.publish(g.actor, g.fence, refs, result)
    assert owner.ticket(caller, _one(g.db, Run, g.fence.run_id)) == wrapper.ticket
    g.execution.release(prepared)


@pytest.mark.parametrize(
    "change", ["cancel", "stale-fence", "expired-output", "revoke-manage", "disabled"]
)
def test_generated_ingestion_cannot_publish_after_authority_change(
    generated_knowledge, change
):
    from actions.server.data_queries.knowledge_values import knowledge_grant_subject
    from actions.server.foundry.provider_registry import _ref_id
    from actions.server.run_outputs.service import FenceRejected

    g = generated_knowledge
    event = threading.Event()
    prepared = g.execution.prepare(
        g.actor, g.fence, cancelled=event, deadline=time.monotonic() + 20
    )
    owner, caller, wrapper, refs, result = publish_generated(g, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        with g.db.transaction():
            if change == "cancel":
                event.set()
            elif change == "stale-fence":
                g.db.execute(
                    "UPDATE run_pin SET epoch=epoch+1 WHERE id=?", [g.fence.run_id]
                )
            elif change == "expired-output":
                g.db.execute(
                    "UPDATE run_output SET expires_ms=? WHERE id=?",
                    ["1", prepared.knowledge[0].ingestion.output.output_id],
                )
            elif change == "disabled":
                g.db.execute(
                    "UPDATE foundry_provider_availability SET enabled=? WHERE id=?",
                    [False, _ref_id(g.descriptor.reference)],
                )
            else:
                g.db.execute(
                    "UPDATE foundry_access_grant SET operations_json=? WHERE subject_id=?",
                    [
                        json.dumps(["knowledge.read"]),
                        knowledge_grant_subject(g.collection),
                    ],
                )
        with pytest.raises((ValueError, PermissionError, FenceRejected)):
            wrapper.publish(g.actor, g.fence, refs, result)
    assert _one(g.db, Run, g.fence.run_id).status != RunStatus.PASSED
    g.execution.release(prepared)
