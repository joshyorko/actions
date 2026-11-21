"""Default-off authenticated projection beside managed Work Items."""

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from actions.server.managed_work_items.api import Authenticate, ManagedError
from actions.server.managed_work_items.contracts import API_PREFIX, ManagedCaller
from actions.server.run_outputs.service import AccessDenied

from .models import Value
from .openai import ProviderFailure
from .work_items import ClaimedDecisionService, ClaimedEvaluation, ClaimedReceipt


class Resolve(Value):
    receipt: ClaimedReceipt
    evaluation: ClaimedEvaluation
    decision: Literal["approve", "reject"]


def create_router(
    service: ClaimedDecisionService | None, authenticate: Authenticate | None
) -> APIRouter:
    router = APIRouter(prefix=API_PREFIX + "/decisions")

    def error(code, status):
        return JSONResponse(
            status_code=status,
            content={
                "schema_version": "actions.claimed-decision/v1",
                "error": {"code": code},
            },
        )

    async def invoke(request, operation, receipt_id=None):
        if service is None or authenticate is None:
            return error("unconfigured", 503)
        try:
            try:
                caller = await authenticate(request)
                if not isinstance(caller, ManagedCaller):
                    return error("not_authenticated", 401)
            except Exception:
                return error("not_authenticated", 401)
            if operation == "read":
                result = await run_in_threadpool(service.status, caller, receipt_id)
            else:
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 65536:
                        return error("request_too_large", 413)
                if operation == "evaluate":
                    command = ClaimedEvaluation.model_validate_json(body)
                    result = await run_in_threadpool(service.evaluate, caller, command)
                else:
                    command = Resolve.model_validate_json(body)
                    result = await run_in_threadpool(
                        service.resolve,
                        caller,
                        command.receipt,
                        command.evaluation,
                        command.decision,
                    )
            return JSONResponse(result.model_dump(mode="json"))
        except (ValueError, ValidationError):
            return error("invalid_request", 422)
        except ManagedError as exc:
            return error(exc.code, exc.STATUSES[exc.code])
        except AccessDenied:
            return error("forbidden", 403)
        except ProviderFailure as exc:
            code = (
                "evaluation_uncertain"
                if str(exc) == "evaluation_uncertain"
                else "provider_unavailable"
            )
            return error(code, 409 if code == "evaluation_uncertain" else 503)
        except Exception:
            return error("storage_unavailable", 503)

    @router.post("/evaluate")
    async def evaluate(request: Request):
        return await invoke(request, "evaluate")

    @router.post("/resolve")
    async def resolve(request: Request):
        return await invoke(request, "resolve")

    @router.get("/{receipt_id}")
    async def read(request: Request, receipt_id: str):
        if len(receipt_id) != 64 or any(
            c not in "0123456789abcdef" for c in receipt_id
        ):
            return error("invalid_request", 422)
        return await invoke(request, "read", receipt_id)

    return router
