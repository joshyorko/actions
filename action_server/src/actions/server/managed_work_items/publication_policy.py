"""Live model Work Item publication policy over active Deployments and queues."""

from __future__ import annotations

import inspect
import json
from typing import get_args

from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    AccessDenied,
    ModelPublishedWorkItemOperation,
)
from actions.server.deployments.ids import DeploymentId, WorkspaceId
from actions.server.foundry.models import FoundryDeploymentHead
from actions.server.managed_work_items.contracts import (
    OPERATION_PERMISSION,
    ManagedCaller,
    Operation,
    Permission,
    QueuePage,
    QueueRef,
    Queues,
)
from actions.server.run_outputs.types import Actor

MAX_CURRENT_DEPLOYMENTS = 1024
MAX_PUBLICATION_QUEUE_ENTRIES = 2048
MAX_PUBLISHED_QUEUES = 100
MAX_CATALOG_SCAN_ROWS = 1024
MAX_CATALOG_SCAN_PAGES = MAX_CATALOG_SCAN_ROWS // 100 + 1
MAX_CATALOG_SCAN_BYTES = 512 * 1024
MAX_BACKEND_CURSOR_BYTES = 4096
_MODEL_OPERATIONS = frozenset(get_args(ModelPublishedWorkItemOperation))


def _queue_key(queue: QueueRef) -> str:
    return json.dumps(
        queue.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


class DeploymentModelWorkItemPublicationPolicy:
    """Resolve only current, explicitly selected and live-authorized queues.

    The configured actor and Workspace come from trusted host authentication and
    installation scope. This adapter has no cache: callers must still use the
    atomic publication guard before invoking the domain port.
    """

    def __init__(
        self,
        deployments: FoundryDeploymentService,
        port,
        actor: Actor,
        workspace_id: WorkspaceId,
    ) -> None:
        if not isinstance(deployments, FoundryDeploymentService):
            raise TypeError("canonical Deployment service required")
        db = deployments._repository._db
        if getattr(port, "db", None) is not db:
            raise ValueError("publication policy requires one common SQL authority")
        if not callable(getattr(port, "call", None)):
            raise TypeError("canonical managed Work Item port required")
        self.deployments = deployments
        self.port = port
        self.actor = Actor.model_validate(actor)
        self.workspace_id = WorkspaceId.model_validate(workspace_id)
        self.db = db

    def workspaces(self, caller: ManagedCaller) -> tuple[str, ...]:
        if not self._trusted_caller(caller):
            return ()
        return (str(self.workspace_id.root),)

    def allows(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, operation: Operation
    ) -> bool:
        return bool(self.queues(caller, workspace_id, operation))

    def queues(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, operation: Operation
    ) -> tuple[QueueRef, ...]:
        """Return the bounded intersection of current publication and live catalog.

        Any malformed or oversized head/catalog result denies the complete set;
        no partial prefix can make a hidden queue or backend cursor observable.
        """
        try:
            if not self._trusted_caller(caller):
                return ()
            workspace_id = WorkspaceId.model_validate(workspace_id)
            if workspace_id != self.workspace_id:
                return ()
            operation = Operation(operation)
            if operation.value not in _MODEL_OPERATIONS:
                return ()
            with self.db.connect():
                selected = self._selected_queues(operation)
                if not selected:
                    return ()
                return self._intersect_live_catalog(caller, operation, selected)
        except Exception:
            return ()

    def _trusted_caller(self, caller: ManagedCaller) -> bool:
        try:
            if not isinstance(caller, ManagedCaller) or caller.worker_id is not None:
                return False
            validated = ManagedCaller.model_validate(caller)
            return validated.actor == self.actor
        except Exception:
            return False

    def _selected_queues(self, operation: Operation) -> dict[str, QueueRef]:
        workspace = self.workspace_id
        heads = self.db.select(
            FoundryDeploymentHead,
            "SELECT * FROM foundry_deployment_head WHERE workspace_id=? "
            "ORDER BY deployment_id LIMIT ?",
            [str(workspace.root), MAX_CURRENT_DEPLOYMENTS + 1],
        )
        if len(heads) > MAX_CURRENT_DEPLOYMENTS:
            raise AccessDenied("model queue publication unavailable")

        selected: dict[str, QueueRef] = {}
        entries_seen = 0
        repository = self.deployments._repository
        for head in heads:
            if head.workspace_id != str(workspace.root):
                raise AccessDenied("model queue publication unavailable")
            deployment_id = DeploymentId.model_validate(head.deployment_id)
            current = repository.current(workspace, deployment_id)
            if current is None or current.revision.ref.deployment_id != deployment_id:
                raise AccessDenied("model queue publication unavailable")
            published_queues = (
                current.revision.specification.model_published_work_item_queues
            )
            for entry in published_queues:
                entries_seen += 1
                if entries_seen > MAX_PUBLICATION_QUEUE_ENTRIES:
                    raise AccessDenied("model queue publication unavailable")
                if operation.value not in entry.operations:
                    continue
                queue = QueueRef(
                    workspace_id=workspace,
                    deployment=current.revision.ref,
                    queue_id=entry.queue_id,
                )
                key = _queue_key(queue)
                if key in selected:
                    raise AccessDenied("model queue publication unavailable")
                selected[key] = queue
                if len(selected) > MAX_PUBLISHED_QUEUES:
                    raise AccessDenied("model queue publication unavailable")
        return selected

    def _intersect_live_catalog(
        self,
        caller: ManagedCaller,
        operation: Operation,
        selected: dict[str, QueueRef],
    ) -> tuple[QueueRef, ...]:
        cursor: str | None = None
        seen_cursors: set[str] = set()
        pages = 0
        rows_seen = 0
        bytes_seen = 0
        visible: dict[str, QueueRef] = {}
        required = OPERATION_PERMISSION[operation]

        while True:
            if pages >= MAX_CATALOG_SCAN_PAGES:
                raise AccessDenied("managed queue catalog unavailable")
            command = Queues(
                operation="queues.list",
                workspace_id=self.workspace_id,
                cursor=cursor,
                limit=100,
            )
            raw = self.port.call(caller, command)
            if inspect.isawaitable(raw):
                close = getattr(raw, "close", None)
                if callable(close):
                    close()
                raise AccessDenied("synchronous managed queue catalog required")
            encoded = json.dumps(
                raw, ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
            bytes_seen += len(encoded)
            if (
                len(encoded) > MAX_CATALOG_SCAN_BYTES
                or bytes_seen > MAX_CATALOG_SCAN_BYTES
            ):
                raise AccessDenied("managed queue catalog exceeds its bound")
            page = QueuePage.model_validate_json(encoded)
            pages += 1
            rows_seen += len(page.queues)
            if rows_seen > MAX_CATALOG_SCAN_ROWS:
                raise AccessDenied("managed queue catalog exceeds its bound")
            for view in page.queues:
                key = _queue_key(view.queue)
                if key not in selected:
                    continue
                if (
                    Permission.READ not in view.permissions
                    or required not in view.permissions
                ):
                    continue
                if key in visible:
                    raise AccessDenied("duplicate managed queue catalog entry")
                visible[key] = selected[key]

            next_cursor = page.next_cursor
            if next_cursor is None:
                break
            if (
                not isinstance(next_cursor, str)
                or not next_cursor
                or len(next_cursor.encode("utf-8")) > MAX_BACKEND_CURSOR_BYTES
                or next_cursor in seen_cursors
                or rows_seen >= MAX_CATALOG_SCAN_ROWS
            ):
                raise AccessDenied("managed queue catalog pagination unavailable")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

        return tuple(visible[key] for key in sorted(visible))
