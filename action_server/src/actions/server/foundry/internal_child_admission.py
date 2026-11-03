"""Trusted-host admission for one-level internal child Runs.

This module is not Runtime/IPC wiring. It admits ordinary detached Runs and
records RunChildLineage; it never fabricates MCP Task receipts.
"""

from __future__ import annotations

import hashlib
import uuid

from actions.server._models import RUN_ID_COUNTER, Run, RunStatus
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import (
    RunChildLineage,
    RunPin,
    RunTaskReceipt,
    run_child_identity_digest,
)
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.run_outputs.service import (
    AccessDenied,
    _insert,
    _one,
    _returning,
    _transaction,
)
from actions.server.run_outputs.types import Actor, AttemptFence


class InternalChildAdmission:
    """Host-owned one-level child admission over existing Run authority."""

    def __init__(self, detached: DetachedActions):
        if not isinstance(detached, DetachedActions):
            raise TypeError("DetachedActions authority required")
        self.detached = detached
        self.deployments = detached.deployments
        self.outputs = detached.outputs
        self.db = detached.db

    def invoke(self, fence: AttemptFence, binding_name: str, logical_key: str, inputs):
        """Admit or replay a child using a parent fence and Action logical key.

        Actor, parent identity and target are read from trusted Run state and
        stored Deployment policy. They are not request parameters.
        """
        fence = AttemptFence.model_validate(fence)
        if (
            type(binding_name) is not str  # noqa: E721 - require an exact primitive
            or not 1 <= len(binding_name.encode("utf-8", errors="strict")) <= 64
            or type(logical_key) is not str  # noqa: E721 - require an exact primitive
            or not 1 <= len(logical_key.encode("utf-8", errors="strict")) <= 128
        ):
            raise ValueError("bounded internal binding and logical key required")

        # Workers own distinct Database connections; never rely on a caller's
        # thread-local connection being open.
        with self.db.connect(), _transaction(self.db):
            # Lock counter first, including on SQLite, before any read in a
            # write transaction to prevent deferred read-to-write upgrades.
            if not _returning(
                self.db,
                "UPDATE counter SET value=value WHERE id=? RETURNING id",
                [RUN_ID_COUNTER],
            ):
                raise AccessDenied("Run admission unavailable")
            pin = _one(self.db, RunPin, fence.run_id)
            actor = Actor(principal_id=pin.admission_principal_id)
            if pin.run_id != fence.run_id or pin.id != fence.run_id:
                raise AccessDenied("Parent Run unavailable")
            parent_snapshot = self.outputs._pinned(pin)
            if parent_snapshot.workspace_id != pin.workspace_id:
                raise AccessDenied("Parent Run unavailable")

            # _fence locks Workspace and conditionally updates the Run.
            self.outputs._fence(fence)
            # The Workspace fence serializes Deployment publication. Lock the
            # actor's current grant set as well so a concurrent PostgreSQL
            # revocation cannot commit between live authorization and child
            # admission. SQLite's write transaction already excludes writers.
            if self.db.backend_name == "postgresql":
                self.db.select(
                    FoundryAccessGrant,
                    "SELECT * FROM foundry_access_grant WHERE workspace_id=? AND principal_id=? ORDER BY id LIMIT 129 FOR SHARE",
                    [pin.workspace_id, actor.principal_id],
                )
            self.outputs._authorize(actor, parent_snapshot, "execute")
            current = self.deployments._repository.current(
                parent_snapshot.deployment.workspace_id,
                parent_snapshot.deployment.deployment_id,
            )
            if current is None or current.revision.ref != parent_snapshot.deployment:
                raise AccessDenied("Current parent Deployment policy unavailable")
            specification = current.revision.specification
            policies = [
                policy
                for policy in specification.internal_robot_delegations
                if policy.parent_capability == parent_snapshot.capability
            ]
            if len(policies) != 1:
                raise AccessDenied("Current internal delegation unavailable")
            policy = policies[0]
            binding = next(
                (candidate for candidate in policy.bindings if candidate.name == binding_name),
                None,
            )
            if binding is None:
                raise AccessDenied("Internal binding unavailable")

            # Recheck every persisted target's verified registry provenance,
            # current activated revision, and execute authorization in-lock.
            self.deployments._validate_internal_robot_delegations(actor, specification)
            resolved = self.deployments.resolve(
                actor,
                parent_snapshot.deployment.workspace_id,
                binding.target_deployment.deployment_id,
                binding.target_capability,
                revision=binding.target_deployment,
                runtime_plan=binding.target_runtime_plan,
            )
            child_snapshot = resolved.snapshot
            if child_snapshot.runtime_kind != "rcc":
                raise AccessDenied("Internal child must be an RCC Robot")

            key_digest = "sha256:" + hashlib.sha256(
                logical_key.encode("utf-8")
            ).hexdigest()
            identity = run_child_identity_digest(
                fence.run_id, binding_name, key_digest
            )
            outcome = self.detached.admit_outcome(
                actor,
                child_snapshot,
                inputs,
                "internal-child:" + identity,
            )

            # A fence/cancel change aborts the outer transaction, including the
            # nested ordinary Run admission.
            self.outputs._fence(fence)
            self.outputs._authorize(actor, parent_snapshot, "execute")
            parent_run = _one(self.db, Run, fence.run_id)
            if parent_run.status != RunStatus.RUNNING:
                raise AccessDenied("Parent Run is not active")
            if self.db.all(
                RunChildLineage, where="child_run_id=?", values=[fence.run_id]
            ):
                raise AccessDenied("Nested internal child execution is not allowed")

            prior = self.db.all(
                RunChildLineage, where="identity_digest=?", values=[identity]
            )
            if prior:
                row = prior[0]
                if (
                    len(prior) != 1
                    or row.workspace_id != pin.workspace_id
                    or row.parent_run_id != fence.run_id
                    or row.binding_name != binding_name
                    or row.logical_key_digest != key_digest
                    or row.child_run_id != outcome.run.id
                ):
                    raise AccessDenied("Internal child replay identity conflicts")
            else:
                children = self.db.all(
                    RunChildLineage, where="parent_run_id=?", values=[fence.run_id]
                )
                if len(children) >= policy.max_children:
                    raise AccessDenied("Internal child count bound exceeded")
                if self.db.all(
                    RunChildLineage,
                    where="child_run_id=?",
                    values=[outcome.run.id],
                ):
                    raise AccessDenied("Run already has internal parent lineage")
                _insert(
                    self.db,
                    RunChildLineage(
                        id=str(uuid.uuid4()),
                        workspace_id=pin.workspace_id,
                        parent_run_id=fence.run_id,
                        child_run_id=outcome.run.id,
                        binding_name=binding_name,
                        logical_key_digest=key_digest,
                        identity_digest=identity,
                    ),
                )
            if self.db.all(
                RunTaskReceipt, where="run_id=?", values=[outcome.run.id]
            ):
                raise AccessDenied("Internal child cannot be an MCP Task")
            return outcome
