"""Canvas Robot source admission; never a compilation or execution receipt.

The caller supplies portable source and selects an explicitly configured runtime
kind. Only the host supplies preparation, and the existing registry remains the
admission authority. Source admission deliberately cannot authorize release.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

from actions.server.deployments.ids import (
    DeploymentId,
    PackageRevisionId,
    PackageRevisionRef,
    WorkspaceId,
)
from actions.server.foundry.robot_execution import (
    DirectRobotPreparation,
    RccRobotPreparation,
)
from actions.server.foundry.robot_package_admission import RobotAdmissionEvidence
from actions.server.foundry.robot_package_builder import RobotPackageRequest
from actions.server.foundry.robot_validation import (
    RobotValidationResult,
    verify_robot_validation,
)
from actions.server.run_outputs.types import Actor
from pydantic import JsonValue, ValidationError

if TYPE_CHECKING:
    from actions.server.foundry.authoring_values import AuthoringAuthorizationPort
    from actions.server.foundry.mcp import CanvasCaller


@dataclass(frozen=True)
class RobotAuthoringEvidence:
    """Path-free admission/dry-run evidence; genuine execution remains unqualified."""

    package_revision_id: PackageRevisionId
    runtime_kind: Literal["direct", "rcc"]
    verification: Literal["source-and-plan-verified"] = "source-and-plan-verified"
    execution: Literal["not-qualified"] = "not-qualified"
    validation_kind: Literal["robot-dryrun"] | None = None
    validation: Literal["not-run", "passed", "failed"] = "not-run"
    receipt_json: bytes = b""

    @property
    def admission_ready(self) -> bool:
        return (
            self.verification == "source-and-plan-verified"
            and self.execution == "not-qualified"
            and self.runtime_kind in ("direct", "rcc")
            and isinstance(self.package_revision_id, PackageRevisionId)
        )

    @property
    def ready(self) -> bool:
        """Release requires retained dry-run validation, never source admission alone."""
        return (
            self.admission_ready
            and self.validation_kind == "robot-dryrun"
            and self.validation == "passed"
            and bool(self.receipt_json)
        )

    def public_result(self) -> dict[str, JsonValue]:
        return {
            "backendKind": "robot",
            "runtimeKind": self.runtime_kind,
            "admissionVerification": self.verification,
            "executionQualification": self.execution,
            "validationKind": self.validation_kind,
            "backendValidationStatus": self.validation,
        }


def project_robot_evidence(
    evidence: RobotAdmissionEvidence,
    ref: PackageRevisionRef,
    validation: RobotValidationResult | None = None,
) -> RobotAuthoringEvidence:
    """Project a registry-verified retained value, never a caller-supplied receipt."""
    from actions.server.foundry.authoring_values import AuthoringError

    if (
        type(evidence) is not RobotAdmissionEvidence
        or evidence.package.package_revision_id != ref.revision_id
        or evidence.verification != "source-and-plan-verified"
        or evidence.execution != "not-qualified"
    ):
        raise AuthoringError("Robot admission evidence and Package identity disagree")
    result = RobotAuthoringEvidence(
        ref.revision_id, evidence.package.robot.plan.runtime_kind
    )
    if not result.admission_ready:
        raise AuthoringError("Robot admission evidence is invalid")
    if validation is not None:
        from dataclasses import replace

        verify_robot_validation(evidence.package, validation)
        result = replace(
            result,
            validation_kind=validation.validation_kind,
            validation=validation.validation,
            receipt_json=validation.receipt_json,
        )
    return result


def parse_robot_backend(value: object) -> RobotPackageRequest:
    """Parse the closed public request without accepting host paths or digests."""
    from actions.server.foundry.authoring_values import AuthoringValidationError

    try:
        return RobotPackageRequest.model_validate_json(
            json.dumps(value, allow_nan=False)
        )
    except (ValidationError, TypeError, ValueError):
        raise AuthoringValidationError("Invalid Robot backend request") from None


def robot_backend_schema() -> dict[str, JsonValue]:
    """Use nesting-safe definitions shared by the public schema helper."""
    from actions.server.foundry.authoring_bindings import public_schema

    return public_schema(RobotPackageRequest)


class RobotAuthoringRegistry(Protocol):
    def prepare_trusted_robot(
        self,
        request: RobotPackageRequest,
        *,
        logical_package_key: str,
        trusted_actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        preparation: DirectRobotPreparation | RccRobotPreparation,
    ) -> RobotAdmissionEvidence:
        ...

    def admit_robot(
        self, actor: Actor, workspace_id: WorkspaceId, evidence: RobotAdmissionEvidence
    ) -> PackageRevisionRef:
        ...

    def robot_validation_evidence(
        self, ref: PackageRevisionRef
    ) -> RobotValidationResult | None:
        ...

    def robot_admission_evidence(
        self, ref: PackageRevisionRef
    ) -> RobotAdmissionEvidence:
        ...


@dataclass(frozen=True)
class RobotAuthoringResult:
    package_revision: PackageRevisionRef
    evidence: RobotAuthoringEvidence


class RobotAuthoringAdapter:
    """Host-injected bridge to the sole registry, with no worker or process launch."""

    def __init__(
        self,
        registry: RobotAuthoringRegistry,
        authorization: AuthoringAuthorizationPort,
        *,
        direct: DirectRobotPreparation | None = None,
        rcc: RccRobotPreparation | None = None,
    ) -> None:
        if direct is not None and type(direct) is not DirectRobotPreparation:
            raise ValueError("direct host preparation required")
        if rcc is not None and type(rcc) is not RccRobotPreparation:
            raise ValueError("RCC host preparation required")
        self._registry = registry
        self._authorization = authorization
        self._direct, self._rcc = direct, rcc

    def prepare_and_admit(
        self,
        request: RobotPackageRequest,
        *,
        caller: CanvasCaller,
        application_id: DeploymentId,
    ) -> RobotAuthoringResult:
        from actions.server.foundry.authoring_values import (
            AuthoringAccessDenied,
            AuthoringError,
            caller_scope,
        )

        if caller.audience != "model":
            raise AuthoringAccessDenied("Robot authoring requires the model audience")
        actor, workspace = caller_scope(caller)
        application = DeploymentId.model_validate(application_id)
        for operation in ("apply_revision", "execute_generated_source"):
            self._authorization.require(caller, operation, application_id=application)
        request = parse_robot_backend(request.model_dump(mode="json", by_alias=True))
        preparation = self._direct if request.runtime_kind == "direct" else self._rcc
        if preparation is None:
            raise AuthoringAccessDenied(
                "Requested Robot host runtime is not configured"
            )
        evidence = self._registry.prepare_trusted_robot(
            request,
            logical_package_key="canvas-" + str(application.root),
            trusted_actor=actor,
            workspace_id=workspace,
            application_id=application,
            preparation=preparation,
        )
        ref = self._registry.admit_robot(actor, workspace, evidence)
        if not isinstance(ref, PackageRevisionRef) or ref.workspace_id != workspace:
            raise AuthoringError("Robot admission returned a different Workspace")
        projected = project_robot_evidence(evidence, ref)
        retained = self._registry.robot_admission_evidence(ref)
        if retained != evidence:
            raise AuthoringError(
                "Retained Robot admission differs from issued evidence"
            )
        validation = self._registry.robot_validation_evidence(ref)
        projected = project_robot_evidence(retained, ref, validation)
        return RobotAuthoringResult(ref, projected)
