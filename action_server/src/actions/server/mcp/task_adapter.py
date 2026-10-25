"""Current Task extension adapter over authenticated common Run services."""
from __future__ import annotations

import copy
from typing import Any

import anyio
from mcp import MCPError

from actions.server.mcp.task_wire import (
    TASK_EXTENSION,
    DetachedInvocation,
    TaskParams,
    TaskUpdateParams,
    require_current_tasks,
    task_result,
)
from actions.server.run_outputs.task_service import TaskHostUnavailable, TaskService


class TaskMcpAdapter:
    """Explicit host injection; never creates a worker, policy or permission."""

    def __init__(self, canvas, service: TaskService):
        if canvas is None or not isinstance(service, TaskService):
            raise ValueError("configured Canvas and Task service required")
        self.canvas, self.service = canvas, service

    def install(self, server) -> None:
        server.extensions[TASK_EXTENSION] = {}
        server.add_request_handler("tasks/get", TaskParams, self.get)
        server.add_request_handler("tasks/cancel", TaskParams, self.cancel)
        server.add_request_handler("tasks/update", TaskUpdateParams, self.update)

    async def _caller(self, ctx, task_id=None):
        # Authenticate before revealing protocol or task-specific information.
        caller = await self.canvas.principal(ctx)
        if caller is None or caller.audience != "model" or caller.scope is not None:
            raise MCPError(-32602, "Task unavailable")
        require_current_tasks(ctx, task_id=task_id)
        return caller

    async def _run(self, operation, *arguments):
        def invoke():
            try:
                with self.service.db.connect():
                    return operation(*arguments)
            except TaskHostUnavailable:
                raise MCPError(-32603, "Task host unavailable") from None
            except (PermissionError, ValueError, TypeError, KeyError):
                raise MCPError(-32602, "Task unavailable") from None
            except Exception:
                raise MCPError(-32603, "Task service unavailable") from None

        return await anyio.to_thread.run_sync(invoke)

    async def create(self, ctx, params):
        caller = await self._caller(ctx)
        if getattr(params, "task", None) is not None:
            raise MCPError(-32602, "Legacy task parameters are unavailable")
        try:
            invocation = DetachedInvocation.model_validate(params.arguments)
        except ValueError:
            raise MCPError(-32602, "Invalid detached invocation") from None
        snapshot = await self._run(
            self.service.create,
            caller.actor,
            caller.workspace_id,
            invocation.snapshot,
            invocation.inputs,
            invocation.idempotency_key,
        )
        return task_result(snapshot, creation=True)

    async def get(self, ctx, params: TaskParams):
        caller = await self._caller(ctx, params.task_id)
        snapshot = await self._run(
            self.service.get, caller.actor, caller.workspace_id, params.task_id
        )
        return task_result(snapshot)

    async def cancel(self, ctx, params: TaskParams):
        caller = await self._caller(ctx, params.task_id)
        await self._run(
            self.service.cancel, caller.actor, caller.workspace_id, params.task_id
        )
        return {"resultType": "complete"}

    async def update(self, ctx, params: TaskUpdateParams):
        caller = await self._caller(ctx, params.task_id)
        await self._run(
            self.service.update,
            caller.actor,
            caller.workspace_id,
            params.task_id,
            params.input_responses,
        )
        return {"resultType": "complete"}

    async def tools(self, ctx, tools):
        try:
            await self._caller(ctx)
        except MCPError:
            return tools
        result = []
        for tool in tools:
            if tool.name != "capability_invoke":
                result.append(tool)
                continue
            original = copy.deepcopy(tool.input_schema)
            detached = DetachedInvocation.model_json_schema(by_alias=True)

            # Namespace local references before sharing the two root schemas.
            def rename(value: Any):
                if isinstance(value, dict):
                    return {
                        key: (
                            "#/$defs/ActionsTask_" + item.removeprefix("#/$defs/")
                            if key == "$ref"
                            and isinstance(item, str)
                            and item.startswith("#/$defs/")
                            else rename(item)
                        )
                        for key, item in value.items()
                    }
                if isinstance(value, list):
                    return [rename(item) for item in value]
                return value

            detached = rename(detached)
            definitions = original.pop("$defs", {})
            for key, value in detached.pop("$defs", {}).items():
                key = "ActionsTask_" + key
                if key in definitions:
                    raise ValueError("Task schema definition collision")
                definitions[key] = value
            schema = {
                "type": "object",
                "oneOf": [original, detached],
                "$defs": definitions,
            }
            result.append(tool.model_copy(update={"input_schema": schema}))
        return result
