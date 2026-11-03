"""Atomic model-invocation publication checks for existing Run admission.

Call only after the transport has authenticated a model principal. ``admit``
re-resolves and authorizes the exact snapshot, verifies current model
publication, and holds the shared Counter/Workspace admission locks across the
provided admission callback. It creates no Run or other admission by itself.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from actions.server._models import RUN_ID_COUNTER
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    AccessDenied,
    ResolvedDeploymentExecution,
)
from actions.server.run_outputs.service import (
    _lock_workspace,
    _private_diagnostics,
    _returning,
    _transaction,
)
from actions.server.run_outputs.types import Actor, ExecutionSnapshot

T = TypeVar("T")


class ModelInvocationPublicationGuard:
    """Require a currently authorized model publication before Run admission.

    Model publication is satisfied by either the explicit Deployment
    ``model_published_capabilities`` selection (headless model discovery) or a
    binding in a current CanvasSpec whose visibility includes ``model``. App
    only Canvas bindings and unbound/internal-only capabilities do not qualify.
    """

    def __init__(self, deployments: FoundryDeploymentService):
        if not isinstance(deployments, FoundryDeploymentService):
            raise TypeError("canonical Deployment service required")
        self.deployments = deployments
        self.db = deployments._repository._db

    def admit(
        self,
        actor: Actor,
        snapshot: ExecutionSnapshot,
        admission: Callable[[ResolvedDeploymentExecution], T],
    ) -> T:
        """Run one existing admission callback under current publication locks.

        The callback should perform only admission and receipt work. Return from
        this method before execution/RCC begins so Deployment publication does
        not wait for a long-running process.
        """
        if not callable(admission):
            raise TypeError("synchronous Run admission callback required")
        actor = Actor.model_validate(actor)
        snapshot = ExecutionSnapshot.model_validate(snapshot)
        db = self.db
        _private_diagnostics(db)

        with db.connect(), _transaction(db):
            self._lock_admission_workspace(snapshot.deployment.workspace_id)
            resolved = self.deployments.resolve(
                actor,
                snapshot.deployment.workspace_id,
                snapshot.deployment.deployment_id,
                snapshot.capability,
                revision=snapshot.deployment,
                runtime_plan=snapshot.runtime_plan,
            )
            if resolved.snapshot != snapshot:
                raise AccessDenied("exact current model invocation snapshot required")
            current = self.deployments._repository.current(
                snapshot.deployment.workspace_id,
                snapshot.deployment.deployment_id,
            )
            if current is None or current.revision.ref != snapshot.deployment:
                raise AccessDenied("current model invocation publication required")
            if not self._published_to_model(current.revision.specification, snapshot):
                raise AccessDenied("model invocation is not published")
            return admission(resolved)

    def _lock_admission_workspace(self, workspace_id) -> None:
        """Use the common Run counter -> Workspace lock order before reads."""
        db = self.db
        if not db.in_transaction():
            raise RuntimeError("model publication requires an admission transaction")
        if not _returning(
            db,
            "UPDATE counter SET value=value WHERE id=? RETURNING id",
            [RUN_ID_COUNTER],
        ):
            raise RuntimeError("Run counter unavailable")
        workspace_key = str(workspace_id.root)
        _lock_workspace(db, workspace_key)

    @staticmethod
    def _published_to_model(specification, snapshot: ExecutionSnapshot) -> bool:
        if snapshot.capability in specification.model_published_capabilities:
            return True
        canvas_spec = specification.canvas_spec
        if canvas_spec is None or "model" not in canvas_spec.visibility:
            return False
        if specification.canvas_application is None:
            return False
        has_binding = any(
            binding.capability == snapshot.capability
            for binding in specification.canvas_bindings
        )
        if not has_binding:
            return False
        return any(
            policy.capability == snapshot.capability
            and policy.default_plan is not None
            and policy.default_plan == snapshot.runtime_plan
            for policy in specification.capability_plans
        )
