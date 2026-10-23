"""Real SQL/blob admission; fake compiler tests do not qualify generated execution."""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from contract_tests.test_package_revision_compiler import (
    _FakeCompilerExecutor,
    _generated_action_entries,
)

from actions.server.deployments.foundry_values import AccessDenied
from actions.server.deployments.package_revision_compiler import (
    TrustedDeveloperExecutionAdmission,
)
from actions.server.foundry.models import FoundryAccessGrant, FoundryPackageRevision
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="private filesystem Package storage is Linux-only"
)


def _grant(db, refs, actor):
    grant = FoundryAccessGrant(
        str(uuid4()),
        str(refs.workspace.root),
        actor.principal_id,
        "workspace",
        str(refs.workspace.root),
        '["deploy","execute","generate_backend","apply_revision"]',
    )
    with db.transaction():
        db.insert(grant)
    return grant


def _registry(db, provider, executor=None):
    return FoundryPackageRegistry(
        db,
        provider,
        SqlFoundryAuthorization(db),
        executor=executor or _FakeCompilerExecutor(),
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
    )


def _compile(registry, refs, actor):
    result = registry.compile_trusted_source(
        _generated_action_entries(),
        logical_package_key="generated-fixture",
        logical_name="Generated fixture",
        trusted_actor=actor,
        workspace_id=refs.workspace,
        application_id=refs.deployment_id,
    )
    assert result.evidence.ready
    return result.compiled_package


def _admit_native_run(db, registry, package, actor):
    from action_server_tests.run_outputs.test_service import snapshot

    from actions.server._models import Action, Run
    from actions.server.foundry.sql_authorization import reference_grant_subject
    from actions.server.run_outputs.service import (
        RunOutputControlPlane,
        RunOutputService,
    )
    from actions.server.run_outputs.types import ExecutionSnapshot

    capability = registry.capability_refs(package)[0]
    declaration = registry.get_capability(capability)
    raw = snapshot(str(package.workspace_id.root)).model_dump(mode="json")
    raw.update(
        capability_authority="package-revision",
        capability=capability.model_dump(mode="json"),
        runtime_plan=declaration.runtime_plans[0].model_dump(mode="json"),
        action_id=registry.action_id_for(capability),
        capability_schema_digest=declaration.schema_digest,
    )
    admitted = ExecutionSnapshot.model_validate(raw)
    with db.transaction():
        for ref in (
            admitted.deployment,
            admitted.worker,
            admitted.policy,
            admitted.output_provider,
        ):
            db.insert(
                FoundryAccessGrant(
                    str(uuid4()),
                    str(package.workspace_id.root),
                    actor.principal_id,
                    "reference",
                    reference_grant_subject(ref),
                    '["execute"]',
                )
            )
    control = RunOutputControlPlane(db, capabilities=registry)
    control.register(admitted)
    control.grant(actor, admitted.deployment, {"execute", "read", "cancel"})
    service = RunOutputService(db, {}, capabilities=registry)
    run = service.admit(
        actor, admitted, {"value": "synthetic"}, "generated-package-run"
    )
    assert (
        service.admit(
            actor, admitted, {"value": "synthetic"}, "generated-package-run"
        ).id
        == run.id
    )
    assert len(db.all(Run)) == 1 and db.all(Action) == []
    return run


def test_package_admission_replay_restart_and_exact_schemas(
    database_location, foundry_package_store, tmp_path
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        registry = _registry(db, foundry_package_store)
        compiled = _compile(registry, refs, actor)
        ref = registry.admit_compiled(actor, refs.workspace, compiled)
        first = db.all(FoundryPackageRevision)[0]
        assert registry.admit_compiled(actor, refs.workspace, compiled) == ref
        restarted = _registry(db, foundry_package_store)
        assert restarted.evidence(ref).ready
        assert restarted.load(ref) == compiled
        capability = restarted.capability_refs(ref)[0]
        declaration = restarted.get_capability(capability)
        assert declaration.capability_authority == "package-revision"
        assert restarted.get_runtime_plan(
            declaration.runtime_plans[0]
        ).capabilities == (capability,)
        assert (
            restarted.resolve_capability(actor, refs.workspace, capability)
            == capability
        )
        assert db.all(FoundryPackageRevision) == [first]
        _admit_native_run(db, registry, ref, actor)
    # Real fresh interpreter: no in-memory compiler outcome survives this read.
    import json
    import subprocess

    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.update(
        ACTIONS_OWNED_PACKAGE_DB=str(database_location),
        ACTIONS_OWNED_PACKAGE_ROOT=str(tmp_path / "package-objects"),
        ACTIONS_OWNED_PACKAGE_REF=ref.model_dump_json(),
        ACTIONS_OWNED_PACKAGE_ACTOR=actor.model_dump_json(),
    )
    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import json,os
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.deployments.ids import PackageRevisionRef
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.types import Actor
ref=PackageRevisionRef.model_validate_json(os.environ['ACTIONS_OWNED_PACKAGE_REF'])
actor=Actor.model_validate_json(os.environ['ACTIONS_OWNED_PACKAGE_ACTOR'])
db=Database(os.environ['ACTIONS_OWNED_PACKAGE_DB'])
fd=os.open(os.environ['ACTIONS_OWNED_PACKAGE_ROOT'],os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
try:
    with db.connect(), FilesystemOutputProvider(fd) as provider:
        db.initialize(get_all_model_classes())
        registry=FoundryPackageRegistry(db,provider,SqlFoundryAuthorization(db),executor=object())
        cap=registry.capability_refs(ref)[0]
        assert registry.resolve_capability(actor,ref.workspace_id,cap)==cap
        assert registry.evidence(ref).ready
        print(json.dumps({'revision':ref.revision_id.root,'capability':str(cap.capability_id.root)}))
finally:
    os.close(fd)
""",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert json.loads(process.stdout) == {
        "revision": ref.revision_id.root,
        "capability": "action.generated_echo",
    }


def test_package_admission_requires_host_output_actor_workspace_and_live_grants(
    database_location, foundry_package_store
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        grant = _grant(db, refs, actor)
        registry = _registry(db, foundry_package_store)
        compiled = _compile(registry, refs, actor)
        with pytest.raises(AccessDenied):
            registry.admit_compiled(actor, refs.workspace, replace(compiled))
        with pytest.raises(AccessDenied):
            registry.admit_compiled(
                Actor(principal_id=str(uuid4())), refs.workspace, compiled
            )
        with db.transaction():
            db.execute("DELETE FROM foundry_access_grant WHERE id=?", [grant.id])
        with pytest.raises(AccessDenied):
            registry.admit_compiled(actor, refs.workspace, compiled)
        assert db.all(FoundryPackageRevision) == []


def test_duplicate_package_compiles_converge_without_overwriting_or_regranting(
    database_location, foundry_package_store
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        registry = _registry(db, foundry_package_store)
        compiled = [_compile(registry, refs, actor) for _ in range(2)]
        barrier = Barrier(2)

        def admit(value):
            barrier.wait(timeout=10)
            return registry.admit_compiled(actor, refs.workspace, value)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(admit, compiled))
        assert results[0] == results[1]
        assert len(db.all(FoundryPackageRevision)) == 1
        with db.transaction():
            db.execute(
                "DELETE FROM foundry_access_grant WHERE subject_kind='reference'", []
            )
        with pytest.raises(AccessDenied):
            registry.admit_compiled(actor, refs.workspace, compiled[0])
        with pytest.raises(AccessDenied):
            registry.resolve_capability(
                actor, refs.workspace, registry.capability_refs(results[0])[0]
            )


def test_failed_compiler_never_admits_and_tampered_storage_fails_closed(
    database_location, foundry_package_store
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        failed = _registry(db, foundry_package_store, _FakeCompilerExecutor("test"))
        result = failed.compile_trusted_source(
            _generated_action_entries(),
            logical_package_key="generated-fixture",
            logical_name="Generated fixture",
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
        )
        assert not result.evidence.ready and result.compiled_package is None
        assert db.all(FoundryPackageRevision) == []
        registry = _registry(db, foundry_package_store)
        compiled = _compile(registry, refs, actor)
        ref = registry.admit_compiled(actor, refs.workspace, compiled)
        with db.transaction():
            db.execute(
                "UPDATE foundry_package_revision SET manifest_json='{}' WHERE revision_id=?",
                [ref.revision_id.root],
            )
        with pytest.raises(AccessDenied):
            registry.require_revision(ref)


def test_compilation_requires_explicit_host_execution_admission(
    database_location, foundry_package_store
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        executor = _FakeCompilerExecutor()
        registry = FoundryPackageRegistry(
            db, foundry_package_store, SqlFoundryAuthorization(db), executor=executor
        )
        result = registry.compile_trusted_source(
            _generated_action_entries(),
            logical_package_key="generated-fixture",
            logical_name="Generated fixture",
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
        )
        assert not result.evidence.ready
        assert executor.calls == []
        assert db.all(FoundryPackageRevision) == []


def test_package_request_audit_and_grants_rollback_together(
    database_location, foundry_package_store, monkeypatch
):
    from actions.server.foundry.models import FoundryAudit, FoundryRequest

    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        registry = _registry(db, foundry_package_store)
        compiled = _compile(registry, refs, actor)
        original = db.insert

        def fail_audit(value):
            if isinstance(value, FoundryAudit):
                raise RuntimeError("owned synthetic transaction failure")
            return original(value)

        with monkeypatch.context() as patch:
            patch.setattr(db, "insert", fail_audit)
            with pytest.raises(RuntimeError, match="synthetic transaction"):
                registry.admit_compiled(actor, refs.workspace, compiled)
        assert db.all(FoundryPackageRevision) == []
        assert db.all(FoundryRequest) == []
        assert db.all(FoundryAudit) == []
        assert len(db.all(FoundryAccessGrant)) == 1
        ref = registry.admit_compiled(actor, refs.workspace, compiled)
        assert registry.load(ref) == compiled
        assert len(db.all(FoundryRequest)) == len(db.all(FoundryAudit)) == 1
