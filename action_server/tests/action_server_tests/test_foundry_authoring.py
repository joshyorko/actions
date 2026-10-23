"""Fixture proof for the #71 Canvas authoring domain port.

The test authority is deliberately in-memory. Combined Runtime SQL/CAS and
authenticated ChatGPT acceptance require the integration-owned adapter and
remain separate release gates.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from typing import Literal
from uuid import uuid4

import pytest

from actions.server.deployments.ids import (
    DeploymentId,
    DeploymentRevisionId,
    DeploymentRevisionRef,
    PackageId,
    PackageRevisionId,
    PackageRevisionRef,
    WorkspaceId,
)
from actions.server.foundry.authoring import FoundryAuthoring
from actions.server.foundry.authoring_values import (
    AuthoringAccessDenied,
    AuthoringAppSummary,
    AuthoringConflict,
    AuthoringInspection,
    AuthoringRevision,
    AuthoringValidationError,
    CompilationEvidence,
    CompilationResult,
)
from actions.server.foundry.mcp import CanvasCaller
from actions.server.run_outputs.types import Actor


def _uuid() -> str:
    return str(uuid4())


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _spec(*, title: str = "Records", binding_ids: tuple[str, ...] = ()) -> dict:
    children = [{"type": "text", "id": "intro", "text": "Records are ready."}]
    children.extend(
        {
            "type": "status",
            "id": f"status-{binding_id}",
            "bindingId": binding_id,
        }
        for binding_id in binding_ids
    )
    return {
        "schemaVersion": "actions.canvas-spec/v1",
        "title": title,
        "visibility": ["model", "app"],
        "bindingIds": list(binding_ids),
        "root": {
            "type": "stack",
            "id": "main",
            "children": [*children],
        },
    }


def _caller(
    workspace: WorkspaceId | None = None,
    *,
    audience: Literal["model", "app"] = "model",
) -> CanvasCaller:
    return CanvasCaller(
        actor=Actor(principal_id=_uuid()),
        workspace_id=str((workspace or WorkspaceId.model_validate(_uuid())).root),
        audience=audience,
    )


class _Authorization:
    def __init__(self) -> None:
        self.revoked = False
        self.calls: list[str] = []

    def require(
        self,
        caller,
        operation,
        *,
        application_id=None,
        references=(),
    ) -> None:
        self.calls.append(operation)
        if self.revoked:
            raise AuthoringAccessDenied("Foundry access revoked")
        workspace = WorkspaceId(caller.workspace_id)
        for ref in references:
            ref_workspace = getattr(ref, "workspace_id", None)
            if ref_workspace is None and hasattr(ref, "package_revision"):
                ref_workspace = ref.package_revision.workspace_id
            if ref_workspace != workspace:
                raise AuthoringAccessDenied("Reference is outside this Workspace")
        if application_id is not None:
            # Every application is a common Deployment ID in this fixture.
            DeploymentId.model_validate(application_id)


class _Authority:
    """Small state fixture; the production adapter is integration-owned."""

    def __init__(self) -> None:
        self.apps: dict[tuple[str, str], list[AuthoringRevision]] = {}
        self.active: dict[tuple[str, str], DeploymentRevisionRef | None] = {}
        self.requests: dict[tuple[str, str, str, str], tuple[str, object]] = {}
        self.calls: list[str] = []

    def _owner(self, workspace_id, application_id):
        return (str(workspace_id.root), str(application_id.root))

    def _request(self, actor, workspace_id, operation, key, fingerprint):
        identity = (str(workspace_id.root), actor.principal_id, operation, key)
        existing = self.requests.get(identity)
        if existing is not None:
            if existing[0] != fingerprint:
                raise AuthoringConflict("idempotency key was used for changed input")
            return existing[1]
        return None

    def lookup_request(
        self, actor, workspace_id, operation, idempotency_key, request_fingerprint
    ):
        return self._request(
            actor, workspace_id, operation, idempotency_key, request_fingerprint
        )

    def _remember(self, actor, workspace_id, operation, key, fingerprint, value):
        identity = (str(workspace_id.root), actor.principal_id, operation, key)
        self.requests[identity] = (fingerprint, value)

    def _new_revision(
        self,
        actor,
        workspace_id,
        application_id,
        spec_json,
        bindings=(),
        packages=(),
        compilation=None,
        *,
        active=False,
        salt="",
    ):
        owner = self._owner(workspace_id, application_id)
        count = len(self.apps.get(owner, ())) + 1
        ref = DeploymentRevisionRef(
            workspace_id=workspace_id,
            deployment_id=application_id,
            revision_id=DeploymentRevisionId(_digest(f"{owner}:{count}:{salt}")),
        )
        revision = AuthoringRevision(
            ref=ref,
            application_id=application_id,
            spec_json=spec_json,
            bindings=tuple(bindings),
            package_revisions=tuple(packages),
            validation_status="passed",
            compilation=compilation,
            active=active,
        )
        self.apps.setdefault(owner, []).append(revision)
        self.active.setdefault(owner, None)
        return revision

    def open(self, actor, workspace_id):
        self.calls.append("open")
        return tuple(
            AuthoringAppSummary(
                application_id=revision.application_id,
                title=json.loads(revision.spec_json)["title"],
                active_revision=self.active[owner],
            )
            for owner, revisions in self.apps.items()
            if owner[0] == str(workspace_id.root)
            for revision in revisions[-1:]
        )

    def create(
        self,
        actor,
        workspace_id,
        spec_json,
        *,
        selection=None,
        request_fingerprint,
        idempotency_key,
    ):
        self.calls.append("create")
        replay = self._request(
            actor, workspace_id, "create", idempotency_key, request_fingerprint
        )
        if replay is not None:
            return replay
        application_id = DeploymentId(_uuid())
        revision = self._new_revision(
            actor, workspace_id, application_id, spec_json, salt=idempotency_key
        )
        self._remember(
            actor,
            workspace_id,
            "create",
            idempotency_key,
            request_fingerprint,
            revision,
        )
        return revision

    def get(self, actor, workspace_id, application_id, revision=None):
        self.calls.append("get")
        values = self.apps.get(self._owner(workspace_id, application_id), [])
        if revision is None:
            current = self.active.get(self._owner(workspace_id, application_id))
            revision = current or (values[-1].ref if values else None)
        for item in values:
            if item.ref == revision:
                return replace(
                    item,
                    active=item.ref
                    == self.active.get(self._owner(workspace_id, application_id)),
                )
        raise AuthoringAccessDenied("Canvas revision unavailable")

    def current(self, actor, workspace_id, application_id):
        owner = self._owner(workspace_id, application_id)
        current = self.active.get(owner)
        if current is None:
            return None
        return self.get(actor, workspace_id, application_id, current)

    def latest(self, actor, workspace_id, application_id):
        owner = self._owner(workspace_id, application_id)
        values = self.apps.get(owner, [])
        return (
            replace(values[-1], active=values[-1].ref == self.active.get(owner))
            if values
            else None
        )

    def apply(
        self,
        actor,
        workspace_id,
        application_id,
        expected_base,
        spec_json,
        bindings,
        package_revisions,
        selection,
        compilation,
        *,
        request_fingerprint,
        idempotency_key,
    ):
        self.calls.append("apply")
        owner = self._owner(workspace_id, application_id)
        values = self.apps.get(owner, [])
        latest = values[-1].ref if values else None
        if latest != expected_base:
            raise AuthoringConflict("stale Canvas edit")
        replay = self._request(
            actor, workspace_id, "apply", idempotency_key, request_fingerprint
        )
        if replay is not None:
            return replay
        revision = self._new_revision(
            actor,
            workspace_id,
            application_id,
            spec_json,
            bindings,
            package_revisions,
            compilation,
            salt=idempotency_key,
        )
        self._remember(
            actor,
            workspace_id,
            "apply",
            idempotency_key,
            request_fingerprint,
            revision,
        )
        return revision

    def inspect(self, actor, workspace_id, application_id):
        self.calls.append("inspect")
        owner = self._owner(workspace_id, application_id)
        values = self.apps.get(owner, [])
        return AuthoringInspection(
            application_id=application_id,
            active_revision=self.active.get(owner),
            revisions=tuple(
                replace(item, active=item.ref == self.active.get(owner))
                for item in values
            ),
        )

    def release(
        self,
        actor,
        workspace_id,
        application_id,
        candidate,
        expected_active,
        *,
        request_fingerprint,
        idempotency_key,
    ):
        self.calls.append("release")
        owner = self._owner(workspace_id, application_id)
        replay = self._request(
            actor, workspace_id, "release", idempotency_key, request_fingerprint
        )
        if replay is not None:
            return replay
        if self.active.get(owner) != expected_active:
            raise AuthoringConflict("active revision changed")
        target = self.get(actor, workspace_id, application_id, candidate)
        if not target.ready_for_release:
            raise AuthoringValidationError("revision is not ready")
        accepted = replace(target, active=True)
        self.apps[owner] = [
            replace(item, active=item.ref == candidate) for item in self.apps[owner]
        ]
        self.active[owner] = candidate
        self._remember(
            actor,
            workspace_id,
            "release",
            idempotency_key,
            request_fingerprint,
            accepted,
        )
        return accepted

    def rollback(
        self,
        actor,
        workspace_id,
        application_id,
        target,
        expected_active,
        *,
        request_fingerprint,
        idempotency_key,
    ):
        self.calls.append("rollback")
        owner = self._owner(workspace_id, application_id)
        replay = self._request(
            actor, workspace_id, "rollback", idempotency_key, request_fingerprint
        )
        if replay is not None:
            return replay
        if self.active.get(owner) != expected_active:
            raise AuthoringConflict("active revision changed")
        previous = self.get(actor, workspace_id, application_id, target)
        rollback_revision = self._new_revision(
            actor,
            workspace_id,
            application_id,
            previous.spec_json,
            previous.bindings,
            previous.package_revisions,
            previous.compilation,
            active=True,
            salt="rollback:" + idempotency_key,
        )
        self.active[owner] = rollback_revision.ref
        self.apps[owner] = [
            replace(item, active=item.ref == rollback_revision.ref)
            for item in self.apps[owner]
        ]
        self._remember(
            actor,
            workspace_id,
            "rollback",
            idempotency_key,
            request_fingerprint,
            rollback_revision,
        )
        return rollback_revision


class _Compiler:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = []

    def compile_trusted_source(self, entries, **kwargs):
        self.calls.append((tuple(entries), kwargs))
        if self.fail:
            return CompilationResult(
                compiled_package=None,
                evidence=CompilationEvidence(
                    status="failed",
                    build_status="failed",
                    import_status="not-run",
                    test_status="not-run",
                    failure_code="rcc_build_failed",
                ),
            )
        package_revision_id = PackageRevisionId(_digest("compiled-package"))
        return CompilationResult(
            compiled_package=type(
                "FixtureCompiledPackage",
                (),
                {
                    "manifest_json": b"{}",
                    "source_archive": b"fixture source archive",
                    "source_inventory_digest": _digest("inventory"),
                    "source_artifact_digest": _digest("archive"),
                    "package_revision_id": package_revision_id,
                    "runtime_plan_header": object(),
                    "runtime_plan_payload": b"{}",
                    "adapter_specification_payload": b"{}",
                    "input_schema_payload": b"{}",
                    "output_schema_payload": b"{}",
                    "rcc_artifact_digest": _digest("rcc artifact"),
                },
            )(),
            evidence=CompilationEvidence(
                status="succeeded",
                build_status="passed",
                import_status="passed",
                test_status="passed",
                package_revision_id=package_revision_id,
                receipt_json=b"{}",
            ),
        )


class _Packages:
    def __init__(self):
        self.calls = []

    def admit_compiled(self, actor, workspace_id, compiled):
        self.calls.append(compiled)
        return PackageRevisionRef(
            workspace_id=workspace_id,
            package_id=PackageId(_uuid()),
            revision_id=compiled.package_revision_id,
        )

    def resolve_capability(self, actor, workspace_id, capability):
        if capability.package_revision.workspace_id != workspace_id:
            raise AuthoringAccessDenied("Package Revision is outside this Workspace")
        if capability.capability_id.root != "generated":
            raise AuthoringValidationError("Capability is not declared by the Package")
        return capability


class _DeploymentSelection:
    def __init__(self):
        self.calls = []

    def select_specification(
        self, actor, workspace_id, application_id, package_revisions, bindings
    ):
        self.calls.append((package_revisions, bindings))
        return object()


def _service(*, compiler=None):
    auth = _Authorization()
    authority = _Authority()
    compiler = compiler or _Compiler()
    packages = _Packages()
    selection = _DeploymentSelection()
    service = FoundryAuthoring(authority, auth, compiler, packages, selection)
    return service, authority, auth, compiler, packages, selection


def _call(service, caller, name, inputs):
    return asyncio.run(service.call(caller, name, inputs))


def test_empty_library_and_create_compose_a_useful_ui_without_a_package():
    service, authority, _, _, packages, _ = _service()
    caller = _caller()

    empty = _call(service, caller, "canvas_open", {})
    assert empty.model_result == {"applications": []}
    assert "semantic UI" in empty.summary
    assert authority.calls == ["open"]

    created = _call(
        service,
        caller,
        "canvas_create",
        {"title": "Inbox", "idempotencyKey": "create-inbox"},
    )
    spec = created.view_state["spec"]
    assert spec["schemaVersion"] == "actions.canvas-spec/v1"
    assert spec["bindingIds"] == []
    assert len(spec["root"]["children"]) >= 2
    assert not packages.calls


def test_preview_is_effect_free_and_validates_spec_and_binding_map():
    service, authority, auth, compiler, packages, _ = _service()
    caller = _caller()
    valid = _spec(binding_ids=("lookup",))
    with pytest.raises(AuthoringValidationError, match="missing or undeclared"):
        _call(service, caller, "canvas_preview", {"spec": valid, "bindings": []})

    before = tuple(authority.calls), len(compiler.calls), len(packages.calls)
    preview = _call(
        service,
        caller,
        "canvas_preview",
        {
            "spec": _spec(binding_ids=("generated",)),
            "bindings": [{"bindingId": "generated", "capabilityId": "generated"}],
            "backend": {
                "logicalName": "generated-search",
                "files": [
                    {"path": "package.yaml", "content": "spec: v2"},
                    {"path": "search_actions.py", "content": "pass"},
                ],
            },
        },
    )
    assert preview.model_result["effects"] == []
    assert preview.view_state["preview"] is True
    assert (tuple(authority.calls), len(compiler.calls), len(packages.calls)) == before

    with pytest.raises(AuthoringValidationError, match="source inventory is invalid"):
        _call(
            service,
            caller,
            "canvas_preview",
            {
                "spec": _spec(binding_ids=("generated",)),
                "bindings": [{"bindingId": "generated", "capabilityId": "generated"}],
                "backend": {
                    "logicalName": "generated-search",
                    "files": [{"path": "../escape.py", "content": "pass"}],
                },
            },
        )
    assert (tuple(authority.calls), len(compiler.calls), len(packages.calls)) == before

    with pytest.raises(AuthoringValidationError, match="CanvasSpec is invalid"):
        _call(
            service,
            caller,
            "canvas_preview",
            {"spec": {**_spec(), "unexpected": True}},
        )
    assert (tuple(authority.calls), len(compiler.calls), len(packages.calls)) == before

    workspace = WorkspaceId(caller.workspace_id)
    existing_package = PackageRevisionRef(
        workspace_id=workspace,
        package_id=PackageId(_uuid()),
        revision_id=PackageRevisionId(_digest("existing")),
    )
    with pytest.raises(AuthoringValidationError, match="not declared"):
        _call(
            service,
            caller,
            "canvas_preview",
            {
                "spec": _spec(binding_ids=("lookup",)),
                "bindings": [
                    {
                        "bindingId": "lookup",
                        "capabilityId": "missing",
                        "packageRevision": {
                            "workspace_id": str(workspace.root),
                            "package_id": str(existing_package.package_id.root),
                            "revision_id": existing_package.revision_id.root,
                        },
                    }
                ],
            },
        )
    assert (tuple(authority.calls), len(compiler.calls), len(packages.calls)) == before


def test_stale_edits_and_duplicate_requests_are_rejected_or_replayed():
    service, authority, _, _, _, _ = _service()
    caller = _caller()
    created = _call(service, caller, "canvas_create", {"idempotencyKey": "create-one"})
    app_id = created.model_result["applicationId"]
    base = created.model_result["revisionId"]
    applied = _call(
        service,
        caller,
        "canvas_apply",
        {
            "appId": app_id,
            "expectedBase": base,
            "spec": _spec(title="Updated"),
            "bindings": [],
            "idempotencyKey": "apply-one",
        },
    )
    replay = _call(
        service,
        caller,
        "canvas_apply",
        {
            "appId": app_id,
            "expectedBase": base,
            "spec": _spec(title="Updated"),
            "bindings": [],
            "idempotencyKey": "apply-one",
        },
    )
    assert replay.model_result["revisionId"] == applied.model_result["revisionId"]

    with pytest.raises(AuthoringConflict, match="base revision is stale"):
        _call(
            service,
            caller,
            "canvas_apply",
            {
                "appId": app_id,
                "expectedBase": base,
                "spec": _spec(title="Stale"),
                "bindings": [],
                "idempotencyKey": "apply-stale",
            },
        )
    with pytest.raises(AuthoringConflict, match="idempotency key"):
        _call(
            service,
            caller,
            "canvas_create",
            {"title": "Different", "idempotencyKey": "create-one"},
        )

    inspection = _call(service, caller, "canvas_inspect", {"appId": app_id})
    assert len(inspection.model_result["revisions"]) == 2
    assert authority.calls.count("create") == 1
    assert authority.calls.count("apply") == 1
    assert authority.calls.count("inspect") == 1


def test_release_is_explicit_failed_build_does_not_replace_active_and_rollback_reopens():
    compiler = _Compiler()
    service, authority, _, _, packages, selection = _service(compiler=compiler)
    caller = _caller()
    created = _call(
        service, caller, "canvas_create", {"idempotencyKey": "create-release"}
    )
    app_id = created.model_result["applicationId"]
    first = created.model_result["revisionId"]
    released_first = _call(
        service,
        caller,
        "canvas_release",
        {
            "appId": app_id,
            "candidateRevision": first,
            "expectedActive": None,
            "idempotencyKey": "release-first",
        },
    )
    assert released_first.model_result["active"] is True

    binding_spec = _spec(binding_ids=("run",))
    backend_apply = {
        "appId": app_id,
        "expectedBase": first,
        "spec": binding_spec,
        "bindings": [{"bindingId": "run", "capabilityId": "generated"}],
        "backend": {
            "logicalName": "generated-search",
            "files": [
                {"path": "package.yaml", "content": "spec: v2"},
                {"path": "search_actions.py", "content": "pass"},
            ],
        },
        "idempotencyKey": "apply-backend",
    }
    applied = _call(service, caller, "canvas_apply", backend_apply)
    second = applied.model_result["revisionId"]
    assert compiler.calls
    assert len(packages.calls) == 1
    assert applied.model_result["compilationStatus"] == "succeeded"
    assert applied.model_result["buildStatus"] == "passed"
    assert applied.model_result["active"] is False
    compilation_count = len(compiler.calls)
    applied_replay = _call(service, caller, "canvas_apply", backend_apply)
    assert applied_replay.model_result["revisionId"] == second
    assert len(compiler.calls) == compilation_count

    # A new authoring service instance can reopen state retained by the authority.
    reopened_service = FoundryAuthoring(
        authority, _Authorization(), compiler, packages, selection
    )
    reopened = _call(reopened_service, caller, "canvas_get", {"appId": app_id})
    assert reopened.model_result["revisionId"] == second

    with pytest.raises(AuthoringConflict, match="active revision changed"):
        _call(
            service,
            caller,
            "canvas_release",
            {
                "appId": app_id,
                "candidateRevision": second,
                "expectedActive": None,
                "idempotencyKey": "release-stale",
            },
        )
    before_release = _call(service, caller, "canvas_inspect", {"appId": app_id})
    assert before_release.model_result["activeRevisionId"] == first

    released_second = _call(
        service,
        caller,
        "canvas_release",
        {
            "appId": app_id,
            "candidateRevision": second,
            "expectedActive": first,
            "idempotencyKey": "release-second",
        },
    )
    assert released_second.model_result["active"] is True

    # A duplicate request returns its recorded receipt without restoring the
    # old pointer after a later release.
    replayed_first = _call(
        service,
        caller,
        "canvas_release",
        {
            "appId": app_id,
            "candidateRevision": first,
            "expectedActive": None,
            "idempotencyKey": "release-first",
        },
    )
    assert replayed_first.model_result["revisionId"] == first
    inspect_second = _call(service, caller, "canvas_inspect", {"appId": app_id})
    assert inspect_second.model_result["activeRevisionId"] == second

    rolled_back = _call(
        service,
        caller,
        "canvas_release",
        {
            "appId": app_id,
            "rollbackTo": first,
            "expectedActive": second,
            "idempotencyKey": "rollback-first",
        },
    )
    assert rolled_back.model_result["active"] is True
    assert rolled_back.model_result["revisionId"] != first
    assert rolled_back.view_state["spec"]["title"] == "New Canvas"

    failing_compiler = _Compiler(fail=True)
    failing_service = FoundryAuthoring(
        authority,
        _Authorization(),
        failing_compiler,
        packages,
        selection,
    )
    with pytest.raises(AuthoringValidationError, match="did not pass"):
        _call(
            failing_service,
            caller,
            "canvas_apply",
            {
                "appId": app_id,
                "expectedBase": rolled_back.model_result["revisionId"],
                "spec": binding_spec,
                "bindings": [{"bindingId": "run", "capabilityId": "generated"}],
                "backend": {
                    "logicalName": "generated-search",
                    "files": [
                        {"path": "package.yaml", "content": "spec: v2"},
                        {"path": "search_actions.py", "content": "pass"},
                    ],
                },
                "idempotencyKey": "apply-failed-build",
            },
        )
    inspect = _call(service, caller, "canvas_inspect", {"appId": app_id})
    assert (
        inspect.model_result["activeRevisionId"]
        == rolled_back.model_result["revisionId"]
    )


def test_revoked_and_cross_workspace_requests_fail_closed():
    service, _, authorization, _, _, _ = _service()
    caller = _caller()
    foreign = WorkspaceId.model_validate(_uuid())
    package_revision = PackageRevisionRef(
        workspace_id=foreign,
        package_id=PackageId(_uuid()),
        revision_id=PackageRevisionId(_digest("foreign")),
    )
    with pytest.raises(AuthoringAccessDenied, match="outside this Workspace"):
        _call(
            service,
            caller,
            "canvas_apply",
            {
                "appId": _uuid(),
                "expectedBase": None,
                "spec": _spec(binding_ids=("foreign",)),
                "bindings": [
                    {
                        "bindingId": "foreign",
                        "capabilityId": "lookup",
                        "packageRevision": {
                            "workspace_id": str(foreign.root),
                            "package_id": str(package_revision.package_id.root),
                            "revision_id": package_revision.revision_id.root,
                        },
                    }
                ],
                "idempotencyKey": "foreign-app",
            },
        )

    authorization.revoked = True
    with pytest.raises(AuthoringAccessDenied, match="revoked"):
        _call(service, caller, "canvas_open", {})


def test_app_audience_cannot_apply_or_release():
    service, authority, _, _, _, _ = _service()
    caller = _caller(audience="app")
    with pytest.raises(AuthoringAccessDenied, match="model audience"):
        _call(
            service,
            caller,
            "canvas_create",
            {"idempotencyKey": "app-create"},
        )
    assert authority.calls == []
