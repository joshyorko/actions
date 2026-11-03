"""Atomic authorization guard for exact model-published Work Item queues."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from typing import cast, get_args

from pydantic import JsonValue

from actions.server._models import RUN_ID_COUNTER
from actions.server.deployments.ids import DeploymentId, WorkspaceId
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    AccessDenied,
    ModelPublishedWorkItemOperation,
    StoredDeploymentRevision,
)
from actions.server.managed_work_items.contracts import (
    ManagedCaller,
    Permission,
    QueueRef,
    QueueView,
)
from actions.server.run_outputs.service import (
    _lock_workspace,
    _private_diagnostics,
    _returning,
    _transaction,
)

MAX_MODEL_QUEUE_CALLBACK_RESULT_BYTES = 512 * 1024
MAX_MODEL_QUEUE_SCAN_ROWS = 2048
_MODEL_QUEUE_OPERATIONS = frozenset(get_args(ModelPublishedWorkItemOperation))
DomainQueueCall = Callable[
    [ManagedCaller, QueueRef, ModelPublishedWorkItemOperation],
    dict[str, JsonValue],
]
DomainQueueScan = Callable[[ManagedCaller], tuple[list[QueueView], str]]


class ModelWorkItemPublicationGuard:
    """Run one exact model queue operation under current publication locks.

    The caller must come from trusted model authentication and be workerless.
    This guard verifies only immutable publication; the domain callback remains
    responsible for rechecking the caller's live Work Item grants. The callback
    must be synchronous and bounded, and its JSON result is byte-capped here.
    """

    def __init__(self, deployments: FoundryDeploymentService):
        if not isinstance(deployments, FoundryDeploymentService):
            raise TypeError("canonical Deployment service required")
        self.deployments = deployments
        self.db = deployments._repository._db

    def call(
        self,
        caller: ManagedCaller,
        queue: QueueRef,
        operation: ModelPublishedWorkItemOperation,
        domain_call: DomainQueueCall,
    ) -> dict[str, JsonValue]:
        """Check current exact publication and invoke the domain port atomically.

        Call this from a synchronous worker thread. ``domain_call`` runs in the
        same DB connection and transaction as current-head resolution. Request
        DTO validation and request-size limits belong to the transport.
        """
        if not isinstance(caller, ManagedCaller) or caller.worker_id is not None:
            raise AccessDenied("model Work Item caller unavailable or not authorized")
        caller = ManagedCaller.model_validate(caller)
        queue = QueueRef.model_validate(queue)
        if (
            not isinstance(operation, str)
            or operation not in _MODEL_QUEUE_OPERATIONS
            or not callable(domain_call)
        ):
            raise AccessDenied("model Work Item publication unavailable")
        operation = cast(ModelPublishedWorkItemOperation, operation)
        _private_diagnostics(self.db)

        with self.db.connect(), _transaction(self.db):
            self._lock_admission_workspace(queue.workspace_id)
            current = self.deployments._repository.current(
                queue.workspace_id, queue.deployment.deployment_id
            )
            if current is None or current.revision.ref != queue.deployment:
                raise AccessDenied("current model queue publication required")
            published_queues = (
                current.revision.specification.model_published_work_item_queues
            )
            selected = [
                entry for entry in published_queues if entry.queue_id == queue.queue_id
            ]
            if len(selected) != 1 or operation not in selected[0].operations:
                raise AccessDenied("model queue operation is not published")

            result = domain_call(caller, queue, operation)
            if inspect.isawaitable(result):
                close = getattr(result, "close", None)
                if callable(close):
                    close()
                raise AccessDenied("synchronous managed domain call required")
            if not isinstance(result, dict):
                raise AccessDenied("bounded managed domain result required")
            try:
                encoded = json.dumps(
                    result,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            except (TypeError, ValueError):
                raise AccessDenied("JSON managed domain result required") from None
            if len(encoded) > MAX_MODEL_QUEUE_CALLBACK_RESULT_BYTES:
                raise AccessDenied("managed domain result exceeds its bound")
            return result

    def list_queues(
        self,
        caller: ManagedCaller,
        workspace_id: WorkspaceId,
        domain_scan: DomainQueueScan,
        *,
        deployment_id: DeploymentId | None = None,
    ) -> tuple[tuple[QueueView, ...], str]:
        """Scan bounded domain pages and filter current published queues atomically.

        The synchronous scan callback must consume every opaque backend cursor
        itself and return only its bounded typed QueueView rows and database
        timestamp. It runs under the same connection and transaction as current
        head checks; client pagination happens after this filtering step.
        """
        if not isinstance(caller, ManagedCaller) or caller.worker_id is not None:
            raise AccessDenied("model Work Item caller unavailable or not authorized")
        caller = ManagedCaller.model_validate(caller)
        workspace_id = WorkspaceId.model_validate(workspace_id)
        if deployment_id is not None:
            deployment_id = DeploymentId.model_validate(deployment_id)
        if not callable(domain_scan):
            raise AccessDenied("bounded managed queue scan required")
        _private_diagnostics(self.db)

        with self.db.connect(), _transaction(self.db):
            self._lock_admission_workspace(workspace_id)
            scanned = domain_scan(caller)
            if inspect.isawaitable(scanned):
                close = getattr(scanned, "close", None)
                if callable(close):
                    close()
                raise AccessDenied("synchronous managed queue scan required")
            if (
                not isinstance(scanned, tuple)
                or len(scanned) != 2
                or not isinstance(scanned[0], list)
                or len(scanned[0]) > MAX_MODEL_QUEUE_SCAN_ROWS
            ):
                raise AccessDenied("bounded managed queue scan required")
            rows, server_time_ms = scanned
            if (
                not isinstance(server_time_ms, str)
                or not server_time_ms.isascii()
                or not server_time_ms.isdigit()
                or len(server_time_ms) > 20
            ):
                raise AccessDenied("managed queue timestamp unavailable")

            current_by_deployment: dict[str, StoredDeploymentRevision | None] = {}
            visible: dict[str, QueueView] = {}
            for raw in rows:
                if not isinstance(raw, QueueView):
                    raise AccessDenied("typed managed queue view required")
                view = QueueView.model_validate(raw)
                queue = view.queue
                if queue.workspace_id != workspace_id:
                    raise AccessDenied("managed queue scan scope changed")
                if (
                    deployment_id is not None
                    and queue.deployment.deployment_id != deployment_id
                ):
                    raise AccessDenied("managed queue scan scope changed")
                deployment_key = str(queue.deployment.deployment_id.root)
                if deployment_key not in current_by_deployment:
                    current_by_deployment[deployment_key] = (
                        self.deployments._repository.current(
                            workspace_id, queue.deployment.deployment_id
                        )
                    )
                current = current_by_deployment[deployment_key]
                if current is None or current.revision.ref != queue.deployment:
                    continue
                published_queues = (
                    current.revision.specification.model_published_work_item_queues
                )
                selected = [
                    entry
                    for entry in published_queues
                    if entry.queue_id == queue.queue_id
                ]
                if (
                    len(selected) != 1
                    or "queues.list" not in selected[0].operations
                    or Permission.READ not in view.permissions
                ):
                    continue
                key = json.dumps(
                    queue.model_dump(mode="json"),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                if key in visible:
                    raise AccessDenied("duplicate managed queue view")
                visible[key] = view

            ordered = tuple(visible[key] for key in sorted(visible))
            try:
                encoded = json.dumps(
                    {
                        "queues": [view.model_dump(mode="json") for view in ordered],
                        "server_time_ms": server_time_ms,
                    },
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            except (TypeError, ValueError):
                raise AccessDenied("JSON managed queue scan required") from None
            if len(encoded) > MAX_MODEL_QUEUE_CALLBACK_RESULT_BYTES:
                raise AccessDenied("managed queue scan exceeds its bound")
            return ordered, server_time_ms

    def _lock_admission_workspace(self, workspace_id: WorkspaceId) -> None:
        """Acquire Counter then Workspace before reading current publication."""
        if not self.db.in_transaction():
            raise RuntimeError("model queue publication requires a transaction")
        if not _returning(
            self.db,
            "UPDATE counter SET value=value WHERE id=? RETURNING id",
            [RUN_ID_COUNTER],
        ):
            raise AccessDenied("Run counter unavailable")
        workspace_id = WorkspaceId.model_validate(workspace_id)
        _lock_workspace(self.db, str(workspace_id.root))
