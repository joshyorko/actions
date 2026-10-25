"""Canvas authoring adapter over the one common Deployment SQL authority."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from actions.canvas_contract import parse_canvas_spec

from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    CanvasCapabilityBinding,
    DeploymentRevision,
    DeploymentSpecification,
    IdempotencyConflict,
    StaleDeploymentRevision,
    canvas_revision_digest,
)
from actions.server.deployments.ids import (
    DeploymentId,
    DeploymentRevisionRef,
    PackageRevisionRef,
    WorkspaceId,
)
from actions.server.foundry.authoring_values import (
    AuthoringAccessDenied,
    AuthoringAppSummary,
    AuthoringAuthorizationPort,
    AuthoringConflict,
    AuthoringError,
    AuthoringInspection,
    AuthoringRevision,
    CanvasBinding,
    CompilationEvidence,
    public_spec_document,
)
from actions.server.foundry.mcp import CanvasCaller
from actions.server.foundry.robot_authoring import RobotAuthoringEvidence
from actions.server.run_outputs.types import Actor, CanvasApplicationRef


class SqlAuthoringAuthority:
    """Stage and explicitly activate immutable edits; no independent state store.

    Compiler evidence is supplied by the admitted common Package registry. Its
    absence disables backend staging rather than admitting a caller receipt.
    """

    def __init__(
        self,
        repository: FoundryRepository,
        deployments: FoundryDeploymentService,
        authorization: AuthoringAuthorizationPort,
        *,
        package_evidence: Callable[
            [PackageRevisionRef], CompilationEvidence | RobotAuthoringEvidence
        ]
        | None = None,
    ):
        self.repository, self.deployments, self.authorization = (
            repository,
            deployments,
            authorization,
        )
        self.package_evidence = package_evidence

    def _require(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        operation: str,
        application_id: DeploymentId | None = None,
    ) -> None:
        caller = CanvasCaller(
            Actor.model_validate(actor),
            str(WorkspaceId.model_validate(workspace_id).root),
            "model",
        )
        self.authorization.require(caller, operation, application_id=application_id)

    @staticmethod
    def _owner(
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        ref: DeploymentRevisionRef,
    ) -> None:
        if ref.workspace_id != workspace_id or ref.deployment_id != application_id:
            raise AuthoringAccessDenied("Canvas revision is outside the application")

    def _compilation(
        self, specification: DeploymentSpecification, *, require_ready: bool = False
    ) -> CompilationEvidence | RobotAuthoringEvidence | None:
        evidence = None
        for package in specification.package_revisions:
            if self.package_evidence is None:
                raise AuthoringError(
                    "common Package build evidence adapter is not configured"
                )
            value = self.package_evidence(package)
            if (
                not isinstance(value, (CompilationEvidence, RobotAuthoringEvidence))
                or not (
                    value.admission_ready
                    if isinstance(value, RobotAuthoringEvidence)
                    else value.ready
                )
                or value.package_revision_id != package.revision_id
            ):
                raise AuthoringError("common Package evidence is not admitted")
            if require_ready and not value.ready:
                raise AuthoringError(
                    "Robot backend requires retained dry-run validation before activation"
                )
            # An unqualified Package cannot be hidden by a later qualified one.
            if evidence is None or evidence.ready or not value.ready:
                evidence = value
        return evidence

    def _project(self, revision: DeploymentRevision) -> AuthoringRevision:
        specification = revision.specification
        if (
            specification.canvas_spec is None
            or specification.canvas_application is None
        ):
            raise AuthoringAccessDenied("Deployment has no Canvas view")
        current = self.repository.current(
            revision.ref.workspace_id, revision.ref.deployment_id
        )
        return AuthoringRevision(
            ref=revision.ref,
            application_id=revision.ref.deployment_id,
            spec_json=specification.canvas_spec.to_json().encode("utf-8"),
            bindings=tuple(
                CanvasBinding(binding.binding_id, binding.capability)
                for binding in specification.canvas_bindings
            ),
            package_revisions=specification.package_revisions,
            validation_status="passed",
            compilation=self._compilation(specification),
            active=current is not None and current.revision.ref == revision.ref,
        )

    def open(
        self, actor: Actor, workspace_id: WorkspaceId
    ) -> tuple[AuthoringAppSummary, ...]:
        self._require(actor, workspace_id, "inspect_library")
        db = self.repository._db
        with db.connect():
            with db.cursor() as cursor:
                db.execute_query(
                    cursor,
                    "SELECT DISTINCT deployment_id FROM foundry_deployment_revision WHERE workspace_id=? ORDER BY deployment_id LIMIT 201",
                    [str(workspace_id.root)],
                )
                rows = cursor.fetchall()
        if len(rows) > 200:
            raise AuthoringError("Canvas library exceeds the bounded application limit")
        result = []
        for row in rows:
            application_id = DeploymentId.model_validate(row[0])
            try:
                self._require(actor, workspace_id, "read_application", application_id)
            except AuthoringAccessDenied:
                continue
            revision = self.latest(actor, workspace_id, application_id)
            if revision is not None:
                spec = public_spec_document(revision.spec_json)
                current = self.current(actor, workspace_id, application_id)
                title = spec["title"]
                assert isinstance(title, str)
                result.append(
                    AuthoringAppSummary(
                        application_id, title, current.ref if current else None
                    )
                )
        return tuple(result)

    def lookup_request(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> AuthoringRevision | None:
        permission = {
            "create": "create_application",
            "apply": "apply_revision",
            "release": "release_application",
            "rollback": "release_application",
        }.get(operation)
        if permission is None:
            raise AuthoringError("unknown authoring request operation")
        Actor.model_validate(actor)
        WorkspaceId.model_validate(workspace_id)
        if operation == "create":
            self._require(actor, workspace_id, permission)
        try:
            revision = self.repository.lookup_authoring_request(
                workspace_id,
                actor.principal_id,
                "canvas." + operation,
                idempotency_key,
                request_fingerprint,
            )
        except IdempotencyConflict as exc:
            raise AuthoringConflict("idempotency request input changed") from exc
        if revision is None:
            return None
        self._require(
            actor,
            workspace_id,
            permission,
            revision.ref.deployment_id if operation != "create" else None,
        )
        return self._project(revision)

    def create(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        spec_json: bytes,
        *,
        selection: DeploymentSpecification | None = None,
        request_fingerprint: str,
        idempotency_key: str,
    ) -> AuthoringRevision:
        if selection is not None:
            raise AuthoringError("blank Canvas creation does not admit a backend")
        application_id = DeploymentId.model_validate(str(uuid4()))
        return self._stage(
            actor,
            workspace_id,
            application_id,
            None,
            spec_json,
            (),
            (),
            None,
            None,
            "create",
            request_fingerprint,
            idempotency_key,
        )

    def get(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        revision: DeploymentRevisionRef | None = None,
    ) -> AuthoringRevision:
        self._require(actor, workspace_id, "read_application", application_id)
        if revision is None:
            result = self.latest(actor, workspace_id, application_id)
            if result is None:
                raise AuthoringAccessDenied("Canvas application unavailable")
            return result
        self._owner(workspace_id, application_id, revision)
        stored = self.repository.get_revision(revision)
        if stored is None:
            raise AuthoringAccessDenied("Canvas revision unavailable")
        return self._project(stored.revision)

    def current(
        self, actor: Actor, workspace_id: WorkspaceId, application_id: DeploymentId
    ) -> AuthoringRevision | None:
        self._require(actor, workspace_id, "read_application", application_id)
        stored = self.repository.current(workspace_id, application_id)
        return self._project(stored.revision) if stored else None

    def latest(
        self, actor: Actor, workspace_id: WorkspaceId, application_id: DeploymentId
    ) -> AuthoringRevision | None:
        self._require(actor, workspace_id, "read_application", application_id)
        history = self.repository.history(workspace_id, application_id)
        return self._project(history[-1].revision) if history else None

    def apply(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        expected_base: DeploymentRevisionRef | None,
        spec_json: bytes,
        bindings: tuple[CanvasBinding, ...],
        package_revisions: tuple[PackageRevisionRef, ...],
        selection: DeploymentSpecification | None,
        compilation: CompilationEvidence | RobotAuthoringEvidence | None,
        request_fingerprint: str,
        *,
        idempotency_key: str,
    ) -> AuthoringRevision:
        return self._stage(
            actor,
            workspace_id,
            application_id,
            expected_base,
            spec_json,
            bindings,
            package_revisions,
            selection,
            compilation,
            "apply",
            request_fingerprint,
            idempotency_key,
        )

    def _stage(
        self,
        actor,
        workspace_id,
        application_id,
        expected_base,
        spec_json,
        bindings,
        packages,
        selection,
        compilation,
        operation,
        fingerprint,
        key,
    ) -> AuthoringRevision:
        permission = "create_application" if operation == "create" else "apply_revision"
        if expected_base is not None:
            self._owner(workspace_id, application_id, expected_base)
        spec = parse_canvas_spec(spec_json)
        selected_bindings = tuple(
            CanvasCapabilityBinding(
                binding_id=binding.binding_id, capability=binding.capability
            )
            for binding in bindings
        )
        if bool(packages) != (selection is not None):
            raise AuthoringError("backend selection and Package references disagree")
        if selection is not None and set(selection.package_revisions) != set(packages):
            raise AuthoringError("backend selected different Package revisions")
        app = CanvasApplicationRef(
            workspace_id=str(workspace_id.root),
            app_id=str(application_id.root),
            revision_id=canvas_revision_digest(spec, selected_bindings, packages),
        )
        values = selection.model_dump(mode="json", by_alias=True) if selection else {}
        values.update(
            canvas_spec=spec.model_dump(mode="json", by_alias=True),
            canvas_application=app.model_dump(mode="json"),
            canvas_bindings=[
                binding.model_dump(mode="json") for binding in selected_bindings
            ],
        )
        import json

        specification = DeploymentSpecification.model_validate_json(json.dumps(values))

        def preflight():
            self._require(
                actor,
                workspace_id,
                permission,
                None if operation == "create" else application_id,
            )
            self.deployments._authorize_specification(
                actor, workspace_id, specification, "deploy"
            )
            self.deployments._validate_package_contracts(specification)
            evidence = self._compilation(specification)
            if compilation is not None and evidence != compilation:
                raise AuthoringError("compiler evidence differs from admitted Package")

        try:
            revision = self.repository.stage(
                workspace_id,
                application_id,
                expected_base,
                specification,
                principal_id=actor.principal_id,
                operation="canvas." + operation,
                idempotency_key=key,
                input_digest=fingerprint,
                preflight=preflight,
                snapshot_builder=self.deployments._execution_snapshots,
            )
        except (StaleDeploymentRevision, IdempotencyConflict) as exc:
            raise AuthoringConflict(
                "authoring edit or idempotency input changed"
            ) from exc
        return self._project(revision)

    def inspect(
        self, actor: Actor, workspace_id: WorkspaceId, application_id: DeploymentId
    ) -> AuthoringInspection:
        self._require(actor, workspace_id, "inspect_application", application_id)
        revisions = tuple(
            self._project(stored.revision)
            for stored in self.repository.history(workspace_id, application_id)
        )
        current = self.current(actor, workspace_id, application_id)
        return AuthoringInspection(
            application_id, current.ref if current else None, revisions
        )

    def release(
        self,
        actor,
        workspace_id,
        application_id,
        candidate,
        expected_active,
        request_fingerprint,
        *,
        idempotency_key,
    ) -> AuthoringRevision:
        return self._activate(
            actor,
            workspace_id,
            application_id,
            candidate,
            expected_active,
            "release",
            request_fingerprint,
            idempotency_key,
        )

    def rollback(
        self,
        actor,
        workspace_id,
        application_id,
        target,
        expected_active,
        request_fingerprint,
        *,
        idempotency_key,
    ) -> AuthoringRevision:
        return self._activate(
            actor,
            workspace_id,
            application_id,
            target,
            expected_active,
            "rollback",
            request_fingerprint,
            idempotency_key,
        )

    def _activate(
        self,
        actor,
        workspace_id,
        application_id,
        target,
        expected_active,
        operation,
        fingerprint,
        key,
    ) -> AuthoringRevision:
        self._owner(workspace_id, application_id, target)

        def preflight(revision):
            self._require(actor, workspace_id, "release_application", application_id)
            self.deployments._require_workspace(actor, workspace_id, "deploy")
            self.deployments._authorization.require_deployment(
                actor, workspace_id, application_id, "deploy"
            )
            self.deployments._authorize_specification(
                actor, workspace_id, revision.specification, "deploy"
            )
            self.deployments._validate_package_contracts(revision.specification)
            self._compilation(revision.specification, require_ready=True)

        try:
            revision = self.repository.activate_existing(
                target,
                expected_active,
                principal_id=actor.principal_id,
                operation="canvas." + operation,
                idempotency_key=key,
                input_digest=fingerprint,
                preflight=preflight,
                snapshot_builder=self.deployments._execution_snapshots,
            )
        except (StaleDeploymentRevision, IdempotencyConflict) as exc:
            raise AuthoringConflict(
                "activation target or idempotency input changed"
            ) from exc
        return self._project(revision)
