"""Immutable declaration/selection prerequisite; not provider execution proof."""
import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant, _registry
from action_server_tests.test_generic_work_item_execution import grant
from contract_tests.test_package_revision_compiler import (
    _compilation_policy,
    _FakeCompilerExecutor,
    _generated_action_entries,
)

from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.logical_bindings import (
    BindingField,
    BindingOperation,
    LogicalBindingRequirement,
)
from actions.server.deployments.package_revision_compiler import (
    TrustedDeveloperExecutionAdmission,
    compile_generated_python_action,
    verify_compilation_outcome,
)
from actions.server.foundry.authoring_bindings import (
    DataBindingChoice,
    parse_data_bindings,
)
from actions.server.foundry.authoring_values import CanvasBinding, GeneratedBackend
from actions.server.foundry.models import FoundryPackageRevision
from actions.server.foundry.runtime_profile import (
    RuntimeDeploymentSelection,
    RuntimeExecutionProfile,
)
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    """Synthetic compiler only; no RCC command or cache use."""
    yield


def requirement():
    return LogicalBindingRequirement(
        id="records",
        kind="data",
        operations=(
            BindingOperation(
                name="records.select/v1",
                effect="read",
                parameters=(BindingField(name="minimum", kind="integer"),),
                result=(BindingField(name="record_id", kind="string"),),
                max_rows=100,
                max_bytes=65536,
                timeout_ms=1000,
            ),
        ),
    )


def compile_fixture(requirements=()):
    return compile_generated_python_action(
        _generated_action_entries(),
        replace(_compilation_policy(), logical_requirements=requirements),
        protected_input_names=["package.yaml"],
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=_FakeCompilerExecutor(),
    )


def test_requirement_changes_identity_deterministically_without_provider_config():
    first, second = compile_fixture((requirement(),)), compile_fixture((requirement(),))
    assert first.compiled_package is not None, first.receipt
    assert first.compiled_package.manifest_json == second.compiled_package.manifest_json
    assert first.receipt.to_bytes() == second.receipt.to_bytes()
    verify_compilation_outcome(first)
    old = compile_fixture()
    assert (
        first.compiled_package.package_revision_id
        != old.compiled_package.package_revision_id
    )
    manifest = json.loads(first.compiled_package.manifest_json)
    assert manifest["logicalBindingRequirements"] == [
        requirement().model_dump(mode="json")
    ]
    assert manifest["capabilities"][0]["bindingRequirementIds"] == ["records"]
    assert first.compiled_package.source_archive == old.compiled_package.source_archive
    for key in ("provider", "dsn", "endpoint", "credential", "path"):
        with pytest.raises(ValueError):
            LogicalBindingRequirement.model_validate_json(
                json.dumps(
                    dict(requirement().model_dump(mode="json"), **{key: "forbidden"})
                )
            )


def test_zero_requirement_legacy_serialization_and_identity():
    first, second = compile_fixture(), compile_fixture(())
    assert first.compiled_package == second.compiled_package
    backend = GeneratedBackend.model_validate_json(
        json.dumps(
            {
                "logicalName": "Example",
                "files": [{"path": "action.py", "content": "print('example')"}],
            }
        )
    )
    assert "logicalRequirements" not in backend.model_dump(mode="json", by_alias=True)
    assert (
        json.loads(first.compiled_package.manifest_json)["logicalBindingRequirements"]
        == []
    )


class Compatibility:
    def __init__(self, operations):
        self.supported = operations
        self.calls = 0

    def operations(self, actor, provider, kind):
        self.calls += 1
        return self.supported


@pytest.fixture
def bound(database_location, foundry_package_store):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        registry = _registry(db, foundry_package_store)
        outcome = registry.compile_trusted_source(
            _generated_action_entries(),
            logical_package_key="logical-fixture",
            logical_name="Logical fixture",
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
            logical_requirements=(requirement(),),
        )
        assert outcome.evidence.ready, outcome.evidence
        package = registry.admit_compiled(
            actor, refs.workspace, outcome.compiled_package
        )
        capability = registry.capability_refs(package)[0]
        for ref in (
            refs.worker,
            refs.policy,
            refs.output_provider,
            refs.provider,
            refs.second_provider,
        ):
            grant(
                db,
                actor,
                refs.workspace,
                "reference",
                reference_grant_subject(ref),
                ["deploy", "execute"],
            )
        profile = RuntimeExecutionProfile(
            schema_version="actions.runtime-rcc-profile/v1",
            admission="trusted-developer-execution",
            prepared_receipt="/tmp/not-read",
            worker_id=str(uuid4()),
            worker=refs.worker,
            policy=refs.policy,
            output_provider=refs.output_provider,
        )
        compat = Compatibility(requirement().operations)
        selector = RuntimeDeploymentSelection(
            registry, SqlFoundryAuthorization(db), profile, compat
        )
        bindings = (CanvasBinding(binding_id="query", capability=capability),)
        choice = DataBindingChoice(
            bindingId="query", requirementId="records", provider=refs.provider
        )
        yield SimpleNamespace(
            db=db,
            refs=refs,
            actor=actor,
            registry=registry,
            package=package,
            capability=capability,
            selector=selector,
            compat=compat,
            bindings=bindings,
            choice=choice,
        )


def select(g, choices=None):
    return g.selector.select_specification_with_bindings(
        g.actor,
        g.refs.workspace,
        g.refs.deployment_id,
        (g.package,),
        g.bindings,
        (g.choice,) if choices is None else choices,
    )


def test_real_registry_projection_and_binding_A_B_preserve_package(bound):
    g = bound
    declaration = g.registry.get_capability(g.capability)
    assert len(declaration.binding_requirements) == 1
    projected = g.registry.get_binding_requirement(declaration.binding_requirements[0])
    assert projected.contract == requirement()
    original = g.registry.load(g.package).manifest_json
    service = FoundryDeploymentService(
        FoundryRepository(g.db), g.registry, SqlFoundryAuthorization(g.db), g.registry
    )
    a = service.create(
        g.actor, g.refs.workspace, g.refs.deployment_id, select(g), idempotency_key="A"
    )
    grant(
        g.db,
        g.actor,
        g.refs.workspace,
        "reference",
        reference_grant_subject(a.ref),
        ["deploy", "execute"],
    )
    first = service.resolve(
        g.actor, g.refs.workspace, g.refs.deployment_id, g.capability
    )
    b = service.publish(
        g.actor,
        g.refs.workspace,
        g.refs.deployment_id,
        a.ref,
        select(g, (g.choice.model_copy(update={"provider": g.refs.second_provider}),)),
        idempotency_key="B",
    )
    grant(
        g.db,
        g.actor,
        g.refs.workspace,
        "reference",
        reference_grant_subject(b.ref),
        ["execute"],
    )
    assert (
        service.resolve(g.actor, g.refs.workspace, g.refs.deployment_id, g.capability)
        .bindings[0]
        .provider
        == g.refs.second_provider
    )
    assert (
        service.resolve(
            g.actor,
            g.refs.workspace,
            g.refs.deployment_id,
            g.capability,
            revision=a.ref,
        )
        == first
    )
    assert g.registry.load(g.package).manifest_json == original
    assert len(g.db.all(FoundryPackageRevision)) == 1


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "extra",
        "duplicate",
        "wrong-binding",
        "mismatch",
        "unconfigured",
        "revoked-provider",
        "revoked-requirement",
        "cross-workspace",
    ],
)
def test_selection_fails_closed(bound, kind):
    g = bound
    choices = (g.choice,)
    if kind == "missing":
        choices = ()
    elif kind == "extra":
        choices = (g.choice.model_copy(update={"requirement_id": "other"}),)
    elif kind == "duplicate":
        choices = (g.choice, g.choice)
    elif kind == "wrong-binding":
        choices = (g.choice.model_copy(update={"binding_id": "other"}),)
    elif kind == "mismatch":
        g.compat.supported = (
            requirement().operations[0].model_copy(update={"effect": "write"}),
        )
    elif kind == "unconfigured":
        g.selector.provider_compatibility = None
    elif kind == "cross-workspace":
        choices = (g.choice.model_copy(update={"provider": _refs().provider}),)
    else:
        target = (
            g.refs.provider
            if kind == "revoked-provider"
            else g.registry.get_capability(g.capability).binding_requirements[0]
        )
        with g.db.transaction():
            g.db.execute(
                "DELETE FROM foundry_access_grant WHERE subject_id=?",
                [reference_grant_subject(target)],
            )
    with pytest.raises((ValueError, PermissionError)):
        select(g, choices)


def test_public_wire_selection_and_schema_are_strict(bound):
    import jsonschema

    from actions.server.foundry.authoring import SCHEMAS

    g = bound
    raw = [g.choice.model_dump(mode="json", by_alias=True)]
    assert parse_data_bindings(raw, ("query",)) == (g.choice,)
    schema = SCHEMAS["canvas_apply"]["properties"]["dataBindings"]
    jsonschema.validate(raw, schema)
    assert "$ref" not in json.dumps(schema)
    with pytest.raises(ValueError):
        parse_data_bindings(raw + raw, ("query",))
    raw[0]["dsn"] = "forbidden"
    with pytest.raises(ValueError):
        parse_data_bindings(raw, ("query",))


def test_stored_requirement_tamper_is_not_projected(bound):
    g = bound
    with g.db.transaction():
        row = g.db.all(FoundryPackageRevision)[0]
        manifest = json.loads(row.manifest_json)
        manifest["logicalBindingRequirements"][0]["operations"][0]["effect"] = "write"
        g.db.execute(
            "UPDATE foundry_package_revision SET manifest_json=? WHERE id=?",
            [json.dumps(manifest), row.id],
        )
    with pytest.raises(PermissionError):
        g.registry.get_capability(g.capability)


def test_zero_requirement_bytes_match_precheckpoint_compiler():
    import hashlib

    compiled = compile_fixture().compiled_package
    assert (
        hashlib.sha256(compiled.manifest_json).hexdigest()
        == "b69feea6cdb57315b9ea490bd7610371ceeeb05ec9096f101e1b50d08b3215bd"
    )
    assert (
        hashlib.sha256(compiled.runtime_plan_payload).hexdigest()
        == "c87ec3f327ec0b7ef844caccb8652d0e84fe2b657b78e10104c60fb8f2df0bfd"
    )
    assert (
        hashlib.sha256(compiled.source_archive).hexdigest()
        == "5f3ce35a3a2b2095932da6681e686d8ce911d415f4f2f45469a6f9c8aa82b6ff"
    )


def test_normalized_order_and_duplicate_contracts():
    first = requirement()
    second = first.model_copy(update={"id": "other"})
    assert (
        compile_fixture((first, second)).compiled_package
        == compile_fixture((second, first)).compiled_package
    )
    with pytest.raises(ValueError):
        compile_fixture((first, first))
    with pytest.raises(ValueError):
        BindingOperation.model_validate_json(
            json.dumps(
                dict(
                    first.operations[0].model_dump(mode="json"),
                    parameters=[
                        {"name": "token", "kind": "string", "default": "secret"}
                    ],
                )
            )
        )


@pytest.mark.parametrize("change", ["effect", "schema", "bounds"])
def test_provider_compatibility_is_exact_not_a_fallback(bound, change):
    g = bound
    operation = requirement().operations[0]
    update = (
        {"effect": "write"}
        if change == "effect"
        else {"max_bytes": operation.max_bytes - 1}
        if change == "bounds"
        else {"result": (BindingField(name="other", kind="boolean"),)}
    )
    g.compat.supported = (operation.model_copy(update=update),)
    with pytest.raises(ValueError, match="schema/effect/bounds"):
        select(g)


def test_two_canvas_aliases_cannot_collide_on_one_requirement(bound):
    g = bound
    g.bindings = (
        *g.bindings,
        CanvasBinding(binding_id="alias", capability=g.capability),
    )
    choices = (g.choice, g.choice.model_copy(update={"binding_id": "alias"}))
    with pytest.raises(ValueError, match="colliding"):
        select(g, choices)


def test_authoring_forwards_declaration_selection_and_replay_fingerprint():
    from action_server_tests.test_foundry_authoring import (
        _call,
        _caller,
        _service,
        _spec,
    )

    from actions.server.foundry.authoring_values import AuthoringConflict

    service, authority, auth, compiler, packages, selector = _service()
    calls = []

    def explicit(*args):
        calls.append(args)
        return object()

    selector.select_specification_with_bindings = explicit
    caller = _caller()
    created = _call(
        service, caller, "canvas_create", {"idempotencyKey": "binding-create"}
    )
    from actions.server.deployments.ids import WorkspaceId

    provider = _refs().provider.model_copy(
        update={"workspace_id": WorkspaceId.model_validate(caller.workspace_id)}
    )
    args = {
        "appId": created.model_result["applicationId"],
        "expectedBase": created.model_result["revisionId"],
        "spec": _spec(binding_ids=("query",)),
        "bindings": [{"bindingId": "query", "capabilityId": "generated"}],
        "backend": {
            "logicalName": "Logical",
            "files": [
                {"path": "package.yaml", "content": "spec: v2"},
                {"path": "main.py", "content": "pass"},
            ],
            "logicalRequirements": [requirement().model_dump(mode="json")],
        },
        "dataBindings": [
            {
                "bindingId": "query",
                "requirementId": "records",
                "provider": provider.model_dump(mode="json"),
            }
        ],
        "idempotencyKey": "binding-apply",
    }
    result = _call(service, caller, "canvas_apply", args)
    assert compiler.calls[0][1]["logical_requirements"] == (requirement(),)
    assert calls[0][-1][0].provider == provider
    assert (
        _call(service, caller, "canvas_apply", args).model_result == result.model_result
    )
    changed = dict(
        args,
        dataBindings=[
            dict(
                args["dataBindings"][0],
                provider=_refs()
                .provider.model_copy(
                    update={
                        "workspace_id": WorkspaceId.model_validate(caller.workspace_id)
                    }
                )
                .model_dump(mode="json"),
            )
        ],
    )
    with pytest.raises(AuthoringConflict):
        _call(service, caller, "canvas_apply", changed)
    assert len(compiler.calls) == 1 and len(calls) == 1


def test_actual_archived_old_verifier_accepts_legacy_and_rejects_binding_schema():
    import hashlib
    from pathlib import Path

    from actions.server.deployments import package_revision_compiler as compiler

    path = Path(__file__).with_suffix("") / "legacy_package_verifier_c97e.py.txt"
    source = path.read_text()
    core = source[source.index("def _verify_compiled_package_revision") :]
    assert (
        hashlib.sha256(core.encode()).hexdigest()
        == "61435130e9821cb511aff4e4d94af520ea809b1774f31ad05427f9b1a971b5a4"
    )
    namespace = dict(vars(compiler))
    exec(compile(source, str(path), "exec"), namespace)
    old_verify = namespace["_verify_compiled_package_revision"]
    legacy = compile_fixture().compiled_package
    new = compile_fixture((requirement(),)).compiled_package
    old_verify(legacy)
    assert (
        json.loads(new.manifest_json)["schemaVersion"]
        == compiler.PACKAGE_BINDINGS_SCHEMA_VERSION
    )
    with pytest.raises(ValueError, match="manifest shape"):
        old_verify(new)
    compiler.verify_compiled_package_revision(legacy)
    compiler.verify_compiled_package_revision(new)


@pytest.mark.parametrize(
    "required, schema",
    [
        (True, "actions.package-revision/v1-draft"),
        (False, "actions.package-revision/v2-bindings-draft"),
        (True, "actions.package-revision/unknown"),
    ],
)
def test_package_schema_requirement_invariant_rejects_even_rehashed_manifest(
    required, schema
):
    from actions.server.deployments import package_revision_compiler as compiler
    from actions.server.deployments.ids import PackageRevisionId

    compiled = compile_fixture((requirement(),) if required else ()).compiled_package
    manifest = json.loads(compiled.manifest_json)
    manifest["schemaVersion"] = schema
    manifest["identity"].pop("revisionDigest")
    digest = compiler._canonical_digest([schema, manifest])
    manifest["identity"]["revisionDigest"] = digest
    changed = replace(
        compiled,
        manifest_json=compiler._canonical_json(manifest),
        package_revision_id=PackageRevisionId(digest),
    )
    with pytest.raises(ValueError, match="integrity"):
        compiler.verify_compiled_package_revision(changed)


def test_choice_cannot_select_a_requirement_through_unknown_capability(bound):
    from actions.server.deployments.ids import CapabilityId

    g = bound
    g.bindings = (
        CanvasBinding(
            binding_id="query",
            capability=g.capability.model_copy(
                update={"capability_id": CapabilityId("action.other")}
            ),
        ),
    )
    with pytest.raises(ValueError, match="logical binding"):
        select(g)
    assert g.compat.calls == 0


def test_live_provider_execute_revocation_blocks_retained_resolution(bound):
    g = bound
    service = FoundryDeploymentService(
        FoundryRepository(g.db), g.registry, SqlFoundryAuthorization(g.db), g.registry
    )
    revision = service.create(
        g.actor,
        g.refs.workspace,
        g.refs.deployment_id,
        select(g),
        idempotency_key="live-binding",
    )
    grant(
        g.db,
        g.actor,
        g.refs.workspace,
        "reference",
        reference_grant_subject(revision.ref),
        ["execute"],
    )
    assert (
        service.resolve(g.actor, g.refs.workspace, g.refs.deployment_id, g.capability)
        .bindings[0]
        .provider
        == g.refs.provider
    )
    with g.db.transaction():
        g.db.execute(
            "UPDATE foundry_access_grant SET operations_json=? WHERE subject_id=?",
            ['["deploy"]', reference_grant_subject(g.refs.provider)],
        )
    with pytest.raises(PermissionError):
        service.resolve(
            g.actor,
            g.refs.workspace,
            g.refs.deployment_id,
            g.capability,
            revision=revision.ref,
        )


def test_requirement_bearing_package_cannot_enter_unconfigured_rcc_dispatch():
    from actions.server.foundry.rcc_execution import GeneratedRccExecution
    from actions.server.run_outputs.service import AccessDenied

    compiled = compile_fixture((requirement(),)).compiled_package
    manifest = json.loads(compiled.manifest_json)
    runner = object.__new__(GeneratedRccExecution)
    runner.registry = SimpleNamespace(
        load=lambda ref: compiled,
        evidence=lambda ref: SimpleNamespace(ready=True),
    )
    snapshot = SimpleNamespace(
        capability_authority="package-revision",
        capability=SimpleNamespace(
            package_revision=object(),
            capability_id=SimpleNamespace(root=manifest["capabilities"][0]["id"]),
        ),
    )
    with pytest.raises(AccessDenied, match="logical execution runtime"):
        runner._verified_selection(snapshot)
