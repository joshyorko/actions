"""SQL-backed internal child admission controls (no runtime qualification).

The Action package uses the repository's checked-in-source fixture and a
synthetic compiler executor. The Robot uses typed synthetic RCC preparation
measurements. Neither generated Action execution nor Robot execution is tested.
"""

from __future__ import annotations

import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant, _registry
from action_server_tests.test_generic_work_item_execution import (
    grant as grant_authority,
)
from action_server_tests.test_robot_package_admission import request_for
from contract_tests.test_package_revision_compiler import (
    _FakeCompilerExecutor,
    _generated_action_entries,
)

from actions.server._database import Database
from actions.server._models import Run, get_all_model_classes
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    BindingAssignment,
    CapabilityPlanPolicy,
    DeploymentSpecification,
    InternalRobotBinding,
    InternalRobotDelegationPolicy,
)
from actions.server.deployments.ids import DeploymentId
from actions.server.deployments.package_revision_compiler import (
    PreparedRccEnvironment,
    RccBuildIdentity,
    TrustedDeveloperExecutionAdmission,
)
from actions.server.foundry.internal_child_admission import InternalChildAdmission
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.robot_execution import RccRobotPreparation
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import (
    RunAdmission,
    RunAttempt,
    RunChildLineage,
    RunExecutionIntent,
    RunOutput,
    RunPin,
    RunTaskReceipt,
)
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="private filesystem Package storage is Linux-only"
)


def _grant_refs(db, workspace_id, actor, refs):
    """Issue fresh synthetic reference grants; no prior fixture grants copied."""
    unique = {reference_grant_subject(ref) for ref in refs}
    with db.transaction():
        for subject in unique:
            db.insert(
                FoundryAccessGrant(
                    str(uuid4()),
                    str(workspace_id.root),
                    actor.principal_id,
                    "reference",
                    subject,
                    '["deploy","execute"]',
                )
            )


def _reference_grants_for_package(registry, package_ref):
    refs = [package_ref]
    for cap in registry.capability_refs(package_ref):
        refs.append(cap)
        declaration = registry.get_capability(cap)
        refs.extend(declaration.runtime_plans)
        refs.extend(declaration.binding_requirements)
    return refs


def _add_profile_refs(refs):
    # Profiles are references only in this admission fixture; the generated
    # Action and Robot source do not require provider bindings.
    return [
        refs.provider,
        refs.second_provider,
        refs.worker,
        refs.policy,
        refs.output_provider,
    ]


def _grant_deployment_ref(db, workspace, actor, deployment_ref):
    _grant_refs(db, workspace, actor, [deployment_ref])


@pytest.fixture
def admitted(database_location, foundry_package_store, tmp_path, request):
    refs = _refs()
    workspace = refs.workspace
    actor = Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, workspace, ()) as db:
        _grant(db, refs, actor)
        # The FakeCompilerExecutor supplies synthetic build/import receipts
        # for a checked-in-source fixture. This is admission coverage only; it
        # is not evidence that generated code built or executed successfully.
        registry = FoundryPackageRegistry(
            db,
            foundry_package_store,
            SqlFoundryAuthorization(db),
            executor=_FakeCompilerExecutor(),
            admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        )
        compilation = registry.compile_trusted_source(
            _generated_action_entries(),
            logical_package_key="internal-child-parent",
            logical_name="Synthetic internal child parent",
            trusted_actor=actor,
            workspace_id=workspace,
            application_id=refs.deployment_id,
        )
        action_ref = registry.admit_compiled(
            actor, workspace, compilation.compiled_package
        )
        # Real SQL/blob reload validates the immutable package identity and
        # proves the provider staged the source under a fresh object reference.
        assert registry.load_verified(action_ref) == compilation.compiled_package
        action_cap = registry.capability_refs(action_ref)[0]
        action_declaration = registry.get_capability(action_cap)
        action_plan = action_declaration.runtime_plans[0]
        _grant_refs(
            db,
            workspace,
            actor,
            _add_profile_refs(refs),
        )

        robot_registry = registry
        robot_request = request_for("rcc")
        package_yaml = next(
            file.content.encode("utf-8")
            for file in robot_request.files
            if file.path == "package.yaml"
        )
        # Host measurements are typed, but this test deliberately does not run
        # the prepared environment or qualify Robot execution.
        environment = PreparedRccEnvironment(
            robocorp_home=tmp_path,
            package_yaml_digest="sha256:" + hashlib.sha256(package_yaml).hexdigest(),
            build_identity=RccBuildIdentity(
                specification_digest="sha256:" + "c" * 64,
                artifact_digest="sha256:" + "d" * 64,
            ),
            rcc_version="v18.19.3",
        )
        robot_evidence = robot_registry.prepare_trusted_robot(
            robot_request,
            logical_package_key="actions340-synthetic-internal-robot",
            trusted_actor=actor,
            workspace_id=workspace,
            application_id=refs.deployment_id,
            preparation=RccRobotPreparation(Path(sys.executable), environment),
        )
        robot_ref = robot_registry.admit_robot(actor, workspace, robot_evidence)
        assert robot_registry.load_verified(robot_ref) == robot_evidence.package
        robot_cap = robot_registry.capability_refs(robot_ref)[0]
        robot_plan = robot_registry.get_capability(robot_cap).runtime_plans[0]
        _grant_refs(
            db,
            workspace,
            actor,
            _reference_grants_for_package(robot_registry, robot_ref),
        )

        robot_deployment_id = DeploymentId(str(uuid4()))
        deployments = FoundryDeploymentService(
            FoundryRepository(db),
            robot_registry,
            SqlFoundryAuthorization(db),
            robot_registry,
        )

        def specification(package_ref, capability, plan, extra=()):
            declarations = robot_registry.get_capability(capability)
            bindings = tuple(
                BindingAssignment(requirement=requirement, provider=provider)
                for requirement, provider in zip(
                    declarations.binding_requirements,
                    (refs.provider, refs.second_provider),
                    strict=False,
                )
            )
            return DeploymentSpecification(
                package_revisions=(package_ref,),
                capability_plans=(
                    CapabilityPlanPolicy(
                        capability=capability,
                        mode="locked",
                        allowed_plans=(plan,),
                        default_plan=plan,
                    ),
                ),
                bindings=bindings,
                worker=refs.worker,
                policy=refs.policy,
                output_provider=refs.output_provider,
                internal_robot_delegations=tuple(extra),
            )

        robot_spec = specification(robot_ref, robot_cap, robot_plan)
        robot_revision = deployments.create(
            actor,
            workspace,
            robot_deployment_id,
            robot_spec,
            idempotency_key="synthetic-robot-deployment",
        )
        _grant_deployment_ref(db, workspace, actor, robot_revision.ref)
        control = RunOutputControlPlane(db, capabilities=robot_registry)
        # DetachedActions checks the ordinary RunAccessGrant for the child
        # Deployment. Keep this a fresh test-only grant through the canonical
        # control plane; internal invocation does not bypass Run authorization.
        control.grant(actor, robot_revision.ref, {"execute", "read", "cancel"})
        policy = InternalRobotDelegationPolicy(
            parent_capability=action_cap,
            bindings=(
                InternalRobotBinding(
                    name="scan",
                    target_deployment=robot_revision.ref,
                    target_capability=robot_cap,
                    target_runtime_plan=robot_plan,
                ),
            ),
            max_children=1,
            parent_exit=getattr(request, "param", {}).get(
                "parent_exit", "cancel-children"
            ),
        )
        parent_spec = specification(action_ref, action_cap, action_plan, (policy,))
        parent_revision = deployments.create(
            actor,
            workspace,
            refs.deployment_id,
            parent_spec,
            idempotency_key="synthetic-action-parent",
        )
        _grant_deployment_ref(db, workspace, actor, parent_revision.ref)
        # RunOutputService delegates package Run cancellation to the exact
        # parent Application's cancel_execution authority. Keep the grant
        # scoped to this synthetic parent, using the existing test helper.
        grant_authority(
            db,
            actor,
            workspace,
            "application",
            str(refs.deployment_id.root),
            ["cancel_execution"],
        )
        resolved = deployments.resolve(actor, workspace, refs.deployment_id, action_cap)
        control.register(resolved.snapshot)
        control.grant(
            actor, resolved.snapshot.deployment, {"execute", "read", "cancel"}
        )
        outputs = RunOutputService(db, {}, capabilities=robot_registry)
        parent_run = outputs.admit(
            actor, resolved.snapshot, {"value": "parent"}, "synchronous-parent"
        )
        assert not db.all(RunExecutionIntent, where="id=?", values=[parent_run.id])
        fence = outputs.claim(parent_run.id, str(uuid4()), lease_seconds=300)
        detached = DetachedActions(deployments, outputs)
        admission = InternalChildAdmission(detached)
        yield SimpleNamespace(
            db=db,
            database_location=database_location,
            store=foundry_package_store,
            workspace=workspace,
            actor=actor,
            registry=robot_registry,
            deployments=deployments,
            outputs=outputs,
            detached=detached,
            admission=admission,
            parent_run=parent_run,
            fence=fence,
            parent_revision=parent_revision,
            parent_spec=parent_spec,
            parent_capability=action_cap,
            robot_ref=robot_ref,
            robot_revision=robot_revision,
        )


def _child_rows(db, parent_id):
    return db.all(RunChildLineage, where="parent_run_id=?", values=[parent_id])


def _durable_ids(db):
    models = (
        Run,
        RunPin,
        RunAdmission,
        RunExecutionIntent,
        RunChildLineage,
        RunTaskReceipt,
        RunAttempt,
        RunOutput,
    )
    return {model.__name__: {row.id for row in db.all(model)} for model in models}


def _independent_invoker(admitted, barrier, key, payload):
    """Create a second SQL Database and connection, as a separate worker uses."""
    db = Database(admitted.database_location)
    with db.connect():
        db.initialize(get_all_model_classes())
        registry = _registry(db, admitted.store)
        deployments = FoundryDeploymentService(
            FoundryRepository(db),
            registry,
            SqlFoundryAuthorization(db),
            registry,
        )
        outputs = RunOutputService(db, {}, capabilities=registry)
        admission = InternalChildAdmission(DetachedActions(deployments, outputs))
        barrier.wait(timeout=10)
        return admission.invoke(admitted.fence, "scan", key, payload)


def test_internal_child_replay_conflict_count_and_no_task_receipt(admitted):
    child = admitted.admission.invoke(
        admitted.fence, "scan", "logical-1", {"value": "x"}
    )
    assert child.created
    same = admitted.admission.invoke(
        admitted.fence, "scan", "logical-1", {"value": "x"}
    )
    assert not same.created and same.run.id == child.run.id
    assert len(_child_rows(admitted.db, admitted.parent_run.id)) == 1
    assert (
        admitted.db.all(RunTaskReceipt, where="run_id=?", values=[child.run.id]) == []
    )
    before = len(admitted.db.all(Run))
    with pytest.raises(ValueError, match="conflicts"):
        admitted.admission.invoke(
            admitted.fence, "scan", "logical-1", {"value": "changed"}
        )
    assert len(admitted.db.all(Run)) == before
    with pytest.raises(AccessDenied, match="count bound"):
        admitted.admission.invoke(admitted.fence, "scan", "logical-2", {"value": "y"})
    assert len(admitted.db.all(Run)) == before
    assert len(_child_rows(admitted.db, admitted.parent_run.id)) == 1


def test_internal_child_rejects_stale_and_cancelled_parent(admitted):
    stale = admitted.fence.model_copy(update={"epoch": admitted.fence.epoch + 1})
    with pytest.raises(FenceRejected):
        admitted.admission.invoke(stale, "scan", "stale", {"value": "x"})
    assert not _child_rows(admitted.db, admitted.parent_run.id)
    assert admitted.outputs.cancel(admitted.actor, admitted.parent_run.id)
    with pytest.raises(FenceRejected):
        admitted.admission.invoke(admitted.fence, "scan", "cancelled", {"value": "x"})
    assert not _child_rows(admitted.db, admitted.parent_run.id)


def test_internal_child_rechecks_current_parent_policy(admitted):
    from actions.server.deployments.foundry_values import DeploymentSpecification

    without_policy = DeploymentSpecification.model_validate(
        admitted.parent_spec.model_dump(mode="python")
        | {"internal_robot_delegations": ()}
    )
    admitted.deployments.publish(
        admitted.actor,
        admitted.workspace,
        admitted.parent_revision.ref.deployment_id,
        admitted.parent_revision.ref,
        without_policy,
        idempotency_key="revoke-internal-binding",
    )
    with pytest.raises(AccessDenied, match="Current parent Deployment policy"):
        admitted.admission.invoke(admitted.fence, "scan", "revoked", {"value": "x"})
    assert not _child_rows(admitted.db, admitted.parent_run.id)


def test_internal_child_rolls_back_run_when_parent_fence_fails_after_admission(
    admitted, monkeypatch
):
    original = admitted.outputs._fence
    calls = 0

    def fail_after_child(fence):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise FenceRejected("injected parent fence change")
        return original(fence)

    monkeypatch.setattr(admitted.outputs, "_fence", fail_after_child)
    before = _durable_ids(admitted.db)
    with pytest.raises(FenceRejected, match="injected"):
        admitted.admission.invoke(admitted.fence, "scan", "rollback", {"value": "x"})
    assert _durable_ids(admitted.db) == before
    assert not _child_rows(admitted.db, admitted.parent_run.id)


def test_internal_child_rejects_parent_already_lineaged_as_child(admitted):
    # Synthetic lineage setup marks this Run as a child to exercise the
    # one-level guard; admission must roll back any attempted child Run.
    with admitted.db.transaction():
        admitted.db.insert(
            RunChildLineage(
                id=str(uuid4()),
                workspace_id=str(admitted.workspace.root),
                parent_run_id=admitted.parent_run.id,
                child_run_id=admitted.parent_run.id,
                binding_name="scan",
                logical_key_digest="sha256:" + "a" * 64,
                identity_digest="b" * 64,
            )
        )
    before = len(admitted.db.all(Run))
    with pytest.raises(AccessDenied, match="Nested internal child"):
        admitted.admission.invoke(admitted.fence, "scan", "nested", {"value": "x"})
    assert len(admitted.db.all(Run)) == before


def test_internal_child_concurrent_same_key_replays_one_child(admitted):
    before = _durable_ids(admitted.db)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                lambda _: _independent_invoker(
                    admitted, barrier, "concurrent-same", {"value": "same"}
                ),
                range(2),
            )
        )
    assert len({outcome.run.id for outcome in outcomes}) == 1
    assert sorted(outcome.created for outcome in outcomes) == [False, True]
    lineage = _child_rows(admitted.db, admitted.parent_run.id)
    assert len(lineage) == 1
    child_id = lineage[0].child_run_id
    assert admitted.db.all(RunPin, where="run_id=?", values=[child_id])
    assert admitted.db.all(RunExecutionIntent, where="id=?", values=[child_id])
    assert admitted.db.all(RunTaskReceipt, where="run_id=?", values=[child_id]) == []
    after = _durable_ids(admitted.db)
    for model_name, old_ids in before.items():
        added = after[model_name] - old_ids
        expected = (
            1
            if model_name
            in {
                "Run",
                "RunPin",
                "RunAdmission",
                "RunExecutionIntent",
                "RunChildLineage",
            }
            else 0
        )
        assert len(added) == expected, (model_name, added)


def test_internal_child_concurrent_distinct_keys_quota_leaves_no_orphans(admitted):
    before = _durable_ids(admitted.db)
    barrier = Barrier(2)

    def attempt(key):
        try:
            return _independent_invoker(admitted, barrier, key, {"value": key})
        except AccessDenied:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ("concurrent-a", "concurrent-b")))
    committed = [outcome for outcome in outcomes if outcome is not None]
    assert len(committed) == 1 and committed[0].created
    after = _durable_ids(admitted.db)
    for model_name, old_ids in before.items():
        added = after[model_name] - old_ids
        expected = (
            1
            if model_name
            in {
                "Run",
                "RunPin",
                "RunAdmission",
                "RunExecutionIntent",
                "RunChildLineage",
            }
            else 0
        )
        assert len(added) == expected, (model_name, added)
    lineage = _child_rows(admitted.db, admitted.parent_run.id)
    assert len(lineage) == 1
    assert lineage[0].child_run_id in after["Run"] - before["Run"]
    assert not (after["RunTaskReceipt"] - before["RunTaskReceipt"])
