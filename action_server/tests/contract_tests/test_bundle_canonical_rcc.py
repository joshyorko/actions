"""Two independently selected Actions execute through real canonical Run authority."""
import json
import os
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant, _registry
from action_server_tests.test_generic_work_item_execution import grant

from actions.server._models import Run, RunStatus
from actions.server.deployments.capability_bundle_compiler import (
    BundleCompilationPolicy,
    PythonCapabilityPolicy,
)
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    CapabilityPlanPolicy,
    DeploymentSpecification,
)
from actions.server.deployments.package_revision_compiler import (
    PackageCompilationPolicy,
    PinnedRccPackageBuildExecutor,
    load_prepared_rcc_environment,
)
from actions.server.deployments.source_manifest import SuppliedSourceEntry
from actions.server.foundry.execution_selection import compiled_for_snapshot
from actions.server.foundry.models import FoundryPackageRevision
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor, OutputRef

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    os.environ.get("ACTIONS_BUNDLE_REAL_RCC") != "1",
    reason="explicit owned prepared two-Action RCC qualification required",
)


def source_entries(manifest):
    source = b'''from actions import action
@action
def normalize_words(text: str) -> str:
    """Normalize whitespace and letter case.

    Args:
        text: Text to normalize.
    Returns:
        Normalized text.
    """
    return " ".join(text.lower().split())
@action
def add_counts(left: int, right: int) -> int:
    """Add two integer counts.

    Args:
        left: First count.
        right: Second count.
    Returns:
        Sum of counts.
    """
    return left + right
'''
    tests = b"""import unittest
from actions_impl import normalize_words, add_counts
class GeneratedTests(unittest.TestCase):
    def test_words(self): self.assertEqual(normalize_words(" A   B "), "a b")
    def test_counts(self): self.assertEqual(add_counts(7, 9), 16)
"""
    return tuple(
        SuppliedSourceEntry(name, "file", content, 0o644)
        for name, content in (
            ("package.yaml", manifest),
            ("actions_impl.py", source),
            ("tests/test_actions.py", tests),
        )
    )


def test_two_actions_pin_outer_package_and_execute_distinct_plans(
    database_location, foundry_package_store, tmp_path
):
    prepared_path = Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
    prepared = load_prepared_rcc_environment(prepared_path)
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        registry = _registry(
            db, foundry_package_store, PinnedRccPackageBuildExecutor(prepared)
        )
        compiled = registry.compile_trusted_bundle(
            source_entries(prepared_path.with_name("package.yaml").read_bytes()),
            policy=BundleCompilationPolicy(
                tuple(
                    PythonCapabilityPolicy(
                        name,
                        PackageCompilationPolicy(
                            "two-actions",
                            "Two generated Actions",
                            ">=1.1.0a38,<2",
                            ">=1.1.0a3,<2",
                        ),
                    )
                    for name in ("normalize_words", "add_counts")
                )
            ),
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
        )
        assert compiled.evidence.ready, compiled.evidence
        package = registry.admit_compiled(
            actor, refs.workspace, compiled.compiled_package
        )
        capabilities = registry.capability_refs(package)
        assert len(capabilities) == 2
        for reference in (refs.worker, refs.policy, refs.output_provider):
            grant(
                db,
                actor,
                refs.workspace,
                "reference",
                reference_grant_subject(reference),
                ["deploy", "execute"],
            )
        deployments = FoundryDeploymentService(
            FoundryRepository(db), registry, SqlFoundryAuthorization(db), registry
        )
        specification = DeploymentSpecification(
            package_revisions=(package,),
            capability_plans=tuple(
                CapabilityPlanPolicy(
                    capability=capability,
                    mode="locked",
                    allowed_plans=registry.get_capability(capability).runtime_plans,
                    default_plan=registry.get_capability(capability).runtime_plans[0],
                )
                for capability in capabilities
            ),
            worker=refs.worker,
            policy=refs.policy,
            output_provider=refs.output_provider,
        )
        revision = deployments.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            specification,
            idempotency_key="two-actions",
        )
        grant(
            db,
            actor,
            refs.workspace,
            "reference",
            reference_grant_subject(revision.ref),
            ["execute", "read_application"],
        )
        caller = ManagedCaller(actor=actor, worker_id=str(uuid4()))
        grant(
            db,
            actor,
            refs.workspace,
            "application",
            str(refs.deployment_id.root),
            ["read_application"],
        )
        snapshots = [
            deployments.resolve(actor, refs.workspace, refs.deployment_id, cap).snapshot
            for cap in capabilities
        ]
        # Provider-key serialization is supplied by the canonical resolved snapshot.
        outputs = RunOutputService(
            db,
            {s.provider_key: foundry_package_store for s in snapshots},
            capabilities=registry,
        )
        control = RunOutputControlPlane(db, capabilities=registry)
        for snapshot in snapshots:
            control.register(snapshot)
            control.grant(actor, snapshot.deployment, {"execute", "read", "cancel"})
        wrong = snapshots[0].model_copy(
            update={"runtime_plan": snapshots[1].runtime_plan}
        )
        with pytest.raises(AccessDenied):
            compiled_for_snapshot(registry, wrong)
        assert not db.all(Run)
        results = {}
        for snapshot in snapshots:
            cap = snapshot.capability.capability_id.root
            inputs, expected = (
                ({"text": " A   B "}, "a b")
                if cap == "action.normalize_words"
                else ({"left": 7, "right": 9}, 16)
            )
            service = StandaloneActionExecution(deployments, outputs, snapshot)
            ticket = service.dispatch_standalone(caller, inputs, cap, lease_seconds=120)
            runner = GeneratedRccExecution(
                registry,
                service.outputs(caller, ticket),
                prepared,
                Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]),
                tmp_path / cap,
            )
            run = runner.execute(actor, ticket.fence, cancelled=Event())
            assert run.status == RunStatus.PASSED
            value = json.loads(run.result)
            assert value["result"]["actionResult"] == expected
            assert len(value["outputs"]) == 4
            assert (
                service.dispatch_standalone(caller, inputs, cap, lease_seconds=120)
                == ticket
            )
            with pytest.raises(FenceRejected):
                runner.execute(actor, ticket.fence, cancelled=Event())
            readback = []
            for item in value["outputs"]:
                with outputs.resolve(
                    actor,
                    str(refs.workspace.root),
                    OutputRef.model_validate(item).handle,
                ) as stream:
                    raw = stream.read(65537)
                    try:
                        readback.append(json.loads(raw))
                    except (ValueError, UnicodeDecodeError):
                        pass
            assert expected in readback
            results[cap] = (run.id, snapshot.runtime_plan.plan_digest.root)
            assert snapshot.capability.package_revision == package
            assert (
                compiled_for_snapshot(registry, snapshot).package_revision_id
                != package.revision_id
            )
        assert len(db.all(FoundryPackageRevision)) == 1
        assert len(db.all(Run)) == len(db.all(RunAttempt)) == len(db.all(RunPin)) == 2
        assert len({plan for _, plan in results.values()}) == 2
