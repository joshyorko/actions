"""Route immutable generic queue policies and reviewed queues on one SQL authority."""
from __future__ import annotations

import hashlib
import json

from actions.server.deployments.ids import DeploymentRevisionRef, WorkspaceId
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.models import FoundryDeploymentRevision
from actions.server.run_outputs.service import AccessDenied, _now

from .api import ManagedError
from .contracts import (
    Capabilities,
    Command,
    ManagedCaller,
    QueuePage,
    Queues,
    QueueView,
)
from .generic_service import GenericManagedWorkItemsService
from .sql_service import SQLManagedWorkItemsService

_LIMIT = 1024


class CompositeManagedWorkItemsService:
    """A catalog projection, not a queue backend or execution scheduler.

    Every generic entry originates in an activated immutable Deployment and its
    selected default Runtime Plan. Ambiguous same-queue capability policies fail
    closed. Reviewed queue authority stays with the existing reviewed service.
    """

    def __init__(self, reviewed: SQLManagedWorkItemsService, deployments, outputs):
        if (
            reviewed.db is not outputs.db
            or deployments._repository._db is not outputs.db
        ):
            raise ValueError("one common SQL authority required")
        self.reviewed, self.deployments, self.outputs = reviewed, deployments, outputs
        self.db = outputs.db

    def _services(self, caller: ManagedCaller, workspace: WorkspaceId):
        services = {}
        repository = self.deployments._repository
        rows = self.db.select(
            FoundryDeploymentRevision,
            "SELECT * FROM foundry_deployment_revision WHERE workspace_id=? ORDER BY id LIMIT ?",
            [str(workspace.root), _LIMIT + 1],
        )
        if len(rows) > _LIMIT:
            raise ManagedError("storage_unavailable")
        for row in rows:
            ref = DeploymentRevisionRef.model_validate_json(
                json.dumps(
                    {
                        "workspace_id": row.workspace_id,
                        "deployment_id": row.deployment_id,
                        "revision_id": row.revision_id,
                    }
                )
            )
            if not repository.was_activated(ref):
                continue
            stored = repository.get_revision(ref)
            if stored is None:
                raise ManagedError("storage_unavailable")
            spec = stored.revision.specification
            plans = {p.capability: p.default_plan for p in spec.capability_plans}
            for policy in spec.work_item_policies:
                if policy.input_queue is None:
                    continue
                if policy.output_queue not in (None, policy.input_queue + "_output"):
                    # A declared mapping is not evidence this executor supports it.
                    continue
                selected_plan = plans.get(policy.capability)
                if selected_plan is None:
                    # The wire QueueRef cannot select a Runtime Plan. A valid
                    # caller-choice policy is unsupported here, never defaulted.
                    continue
                entries = [
                    e
                    for e in stored.execution_snapshots
                    if e.capability == policy.capability
                    and e.runtime_plan == selected_plan
                ]
                if len(entries) != 1:
                    raise ManagedError("storage_unavailable")
                execution = GenericWorkItemExecution(
                    self.deployments,
                    self.outputs,
                    entries[0].snapshot,
                    policy,
                    self.reviewed.authorization,
                )
                service = GenericManagedWorkItemsService(execution)
                try:
                    service.capabilities(caller, workspace)
                except AccessDenied:
                    continue
                except ManagedError as exc:
                    if exc.code == "forbidden":
                        continue
                    raise
                if service.queue_ref in services:
                    raise ManagedError("storage_unavailable")
                services[service.queue_ref] = service
        reviewed = self.reviewed._known_scopes(workspace)
        if any(
            queue.queue_id == other.queue_id for queue in services for other in reviewed
        ):
            raise ManagedError("storage_unavailable")
        return services

    def capabilities(
        self, caller: ManagedCaller, workspace_id: WorkspaceId
    ) -> Capabilities:
        with self.db.connect():
            base = self.reviewed.capabilities(caller, workspace_id)
            variants = [
                service.capabilities(caller, workspace_id)
                for service in self._services(caller, workspace_id).values()
            ]
            return base.model_copy(
                update={
                    "operations": tuple(
                        dict.fromkeys(
                            [
                                *base.operations,
                                *(v for c in variants for v in c.operations),
                            ]
                        )
                    ),
                    "modes": tuple(
                        dict.fromkeys(
                            [*base.modes, *(v for c in variants for v in c.modes)]
                        )
                    ),
                }
            )

    def call(self, caller: ManagedCaller, command: Command) -> dict:
        with self.db.connect():
            workspace = (
                command.workspace_id
                if isinstance(command, Queues)
                else command.queue.workspace_id
            )
            # Workspace READ is mandatory for discovery; each delegate separately
            # rechecks operation-specific grants and retained admission on replay.
            from .contracts import Permission

            self.reviewed._require_workspace(caller, workspace, Permission.READ)
            services = self._services(caller, workspace)
            if not isinstance(command, Queues):
                service = services.get(command.queue)
                return (service or self.reviewed).call(caller, command)
            queues: list[QueueView] = []
            cursor = None
            for _ in range(_LIMIT // 100 + 1):
                page = self.reviewed.call(
                    caller, command.model_copy(update={"cursor": cursor, "limit": 100})
                )
                parsed = QueuePage.model_validate_json(json.dumps(page))
                queues.extend(parsed.queues)
                cursor = parsed.next_cursor
                if cursor is None:
                    break
            if cursor is not None:
                raise ManagedError("storage_unavailable")
            for service in services.values():
                page = service.call(
                    caller, command.model_copy(update={"cursor": None, "limit": 100})
                )
                queues.extend(QueuePage.model_validate_json(json.dumps(page)).queues)
            queues.sort(
                key=lambda q: json.dumps(
                    q.queue.model_dump(mode="json"), sort_keys=True
                )
            )
            digest = hashlib.sha256(
                json.dumps(
                    [q.queue.model_dump(mode="json") for q in queues], sort_keys=True
                ).encode()
            ).hexdigest()
            offset = 0
            if command.cursor is not None:
                pieces = command.cursor.split(":")
                if (
                    len(pieces) != 3
                    or pieces[0] != "policies"
                    or pieces[1] != digest
                    or not pieces[2].isascii()
                    or not pieces[2].isdigit()
                ):
                    raise ManagedError("changed_input")
                offset = int(pieces[2])
                if offset > len(queues):
                    raise ManagedError("changed_input")
            end = offset + command.limit
            return QueuePage(
                queues=tuple(queues[offset:end]),
                next_cursor=f"policies:{digest}:{end}" if end < len(queues) else None,
                server_time_ms=str(_now(self.db)),
            ).model_dump(mode="json")
