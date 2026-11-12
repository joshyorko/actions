"""Bounded authenticated transport for the versioned managed domain port.

This router never opens a database or falls back to legacy local Work Items.
The integrator must inject the real SQL domain service and trusted auth resolver.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool

from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.ids import WorkspaceId

from .contracts import (
    API_PREFIX,
    CONTRACT_VERSION,
    OPERATION_PERMISSION,
    RESULT_MODELS,
    Claim,
    Command,
    Complete,
    ManagedCaller,
    ManagedWorkItemsPort,
    Operation,
    Queues,
    Renew,
    public_contract_schema,
)

MAX_BYTES = 512 * 1024
Authenticate = Callable[[Request], Awaitable[ManagedCaller | None]]
_COMMAND: TypeAdapter[Command] = TypeAdapter(Command)


class ManagedError(Exception):
    """A safe, closed error code from the canonical domain implementation."""

    STATUSES = {
        "forbidden": 403,
        "not_found": 404,
        "stale_claim": 409,
        "changed_input": 409,
        "approval_required": 409,
        "blocked_uncertain_effect": 409,
        "unsupported_operation": 409,
        "unconfigured": 503,
        "storage_unavailable": 503,
    }

    def __init__(self, code: str):
        if code not in self.STATUSES:
            raise ValueError("unknown managed error code")
        self.code = code
        super().__init__(code)


def _error(code: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"schema_version": CONTRACT_VERSION, "error": {"code": code}},
    )


def create_router(
    service: ManagedWorkItemsPort | None, authenticate: Authenticate | None
) -> APIRouter:
    """No configured identity/domain service means unavailable, never trusted-local."""
    router = APIRouter(prefix=API_PREFIX)

    async def caller(request: Request):
        if authenticate is None:
            return _error("unconfigured", 503)
        try:
            identity = await authenticate(request)
            if not isinstance(identity, ManagedCaller):
                return _error("not_authenticated", 401)
            return ManagedCaller.model_validate(identity)
        except Exception:
            return _error("not_authenticated", 401)

    @router.get("/schema")
    async def schema(request: Request):
        identity = await caller(request)
        if isinstance(identity, JSONResponse):
            return identity
        return JSONResponse(public_contract_schema())

    @router.get("/capabilities")
    async def capabilities(request: Request, workspace_id: str):
        identity = await caller(request)
        if isinstance(identity, JSONResponse):
            return identity
        if service is None:
            return _error("unconfigured", 503)
        try:
            workspace = WorkspaceId.model_validate(workspace_id)
            result = await run_in_threadpool(service.capabilities, identity, workspace)
            if result.workspace_id != workspace:
                return _error("storage_unavailable", 503)
            return JSONResponse(result.model_dump(mode="json"))
        except (ValueError, ValidationError):
            return _error("invalid_request", 422)
        except ManagedError as error:
            return _error(error.code, error.STATUSES[error.code])
        except Exception:
            return _error("storage_unavailable", 503)

    @router.post("/operations")
    async def operation(request: Request):
        identity = await caller(request)
        if isinstance(identity, JSONResponse):
            return identity
        if service is None:
            return _error("unconfigured", 503)
        try:
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BYTES:
                    return _error("request_too_large", 413)
                chunks.append(chunk)
            command = _COMMAND.validate_json(canonicalize_json(b"".join(chunks)))
            workspace = (
                command.workspace_id
                if isinstance(command, Queues)
                else command.queue.workspace_id
            )
            available = await run_in_threadpool(
                service.capabilities, identity, workspace
            )
            if available.workspace_id != workspace:
                return _error("storage_unavailable", 503)
            name = Operation(command.operation)
            if OPERATION_PERMISSION[name] not in available.permissions:
                return _error("forbidden", 403)
            if isinstance(command, (Claim, Renew, Complete)):
                if identity.worker_id is None:
                    return _error("forbidden", 403)
                if (
                    isinstance(command, (Renew, Complete))
                    and command.claim.owner_id != identity.worker_id
                ):
                    return _error("forbidden", 403)
            if name not in available.operations:
                return _error("unsupported_operation", 409)
            result = await run_in_threadpool(service.call, identity, command)
            if inspect.isawaitable(result):
                raise TypeError("managed port must be synchronous")
            if not isinstance(result, dict):
                return _error("storage_unavailable", 503)
            try:
                result = (
                    RESULT_MODELS[name]
                    .model_validate_json(
                        json.dumps(result, ensure_ascii=False, allow_nan=False)
                    )
                    .model_dump(mode="json")
                )
            except (ValueError, ValidationError, TypeError):
                raise ManagedError("storage_unavailable") from None
            envelope = {
                "schema_version": CONTRACT_VERSION,
                "operation": name.value,
                "runtime_version": available.runtime_version,
                "result": result,
            }
            encoded = json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode(
                "utf-8"
            )
            if len(encoded) > MAX_BYTES or not isinstance(result, dict):
                return _error("storage_unavailable", 503)
            return JSONResponse(envelope)
        except (ValueError, ValidationError):
            return _error("invalid_request", 422)
        except ManagedError as error:
            return _error(error.code, error.STATUSES[error.code])
        except Exception:
            # The client receives no provider paths, SQL or exception details.
            return _error("storage_unavailable", 503)

    return router
