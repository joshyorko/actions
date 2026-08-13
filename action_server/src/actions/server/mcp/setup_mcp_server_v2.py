import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Literal

from mcp.types import (
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    ReadResourceResult,
    Resource,
    ResourceTemplate,
    TextContent,
    TextResourceContents,
    Tool,
    ToolAnnotations,
)

log = logging.getLogger(__name__)
OutputSchemaKind = Literal["string", "object", "wrap-in-result-object"]


@dataclass
class ActionInfo:
    func: Callable
    action: Any
    display_name: str
    doc_desc: str
    output_schema_kind: OutputSchemaKind


class McpResponseHandler:
    def set_run_id(self, run_id: str):
        pass

    def set_async_completion(self):
        pass


class McpServerSetupHelper:
    def __init__(self) -> None:
        from mcp.server import Server

        self._init_state()
        self.server = Server(
            "Action Server",
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
            on_list_resources=self._list_resources,
            on_list_resource_templates=self._list_resource_templates,
            on_read_resource=self._read_resource,
            on_list_prompts=self._list_prompts,
            on_get_prompt=self._get_prompt,
        )

    @staticmethod
    def _request_values(ctx: Any) -> tuple[dict[str, str], dict[str, str]]:
        request = ctx.request
        if request is None:
            return {}, {}
        return dict(request.headers), dict(request.cookies)

    async def _list_tools(self, _ctx: Any, _params: Any) -> ListToolsResult:
        return ListToolsResult(tools=list(self._tools))

    async def _call_tool(self, ctx: Any, params: Any):
        try:
            from actions.server._actions_run import IInternalFuncAPI

            headers, cookies = self._request_values(ctx)
            action_info = self._tool_name_to_action_info[params.name]
            func: IInternalFuncAPI = action_info.func
            result = await func(
                response_handler=McpResponseHandler(),
                inputs=params.arguments or {},
                headers=headers,
                cookies=cookies,
            )
            if action_info.output_schema_kind == "string":
                return {"content": [TextContent(type="text", text=result)]}
            if action_info.output_schema_kind == "object":
                return {"content": [], "structured_content": result}
            if action_info.output_schema_kind == "wrap-in-result-object":
                return {"content": [], "structured_content": {"result": result}}
            raise ValueError(f"Unknown output schema kind: {action_info.output_schema_kind}")
        except Exception:
            log.exception("Error calling tool %s", params.name)
            raise

    async def _list_resources(self, _ctx: Any, _params: Any) -> ListResourcesResult:
        return ListResourcesResult(resources=list(self._resources.values()))

    async def _list_resource_templates(
        self, _ctx: Any, _params: Any
    ) -> ListResourceTemplatesResult:
        return ListResourceTemplatesResult(resource_templates=list(self._resource_templates))

    async def _read_resource(self, ctx: Any, params: Any) -> ReadResourceResult:
        uri = str(params.uri)
        action_info = self._resource_to_action_info.get(uri)
        mime_type = None
        inputs: dict[str, Any] = {}
        if action_info:
            resource = self._resources.get(params.uri)
            mime_type = resource.mime_type if resource else None
        else:
            for template in self._resource_templates:
                found_params = self._resource_template_matches(template.uri_template, uri)
                if found_params:
                    mime_type = template.mime_type
                    inputs = found_params
                    action_info = self._resource_template_to_action_info[
                        template.uri_template
                    ]
                    break
        if not action_info:
            raise ValueError(f"No resource found for URI: {uri}")
        headers, cookies = self._request_values(ctx)
        result = await action_info.func(
            response_handler=McpResponseHandler(),
            inputs=inputs,
            headers=headers,
            cookies=cookies,
        )
        if isinstance(result, str):
            text = result
            default_mime = "text/plain"
        elif isinstance(result, bytes):
            text = result.decode()
            default_mime = "application/octet-stream"
        else:
            text = json.dumps(result, indent=2)
            default_mime = "application/json"
        return ReadResourceResult(
            contents=[
                TextResourceContents(
                    uri=uri, text=text, mime_type=mime_type or default_mime
                )
            ]
        )

    async def _list_prompts(self, _ctx: Any, _params: Any) -> ListPromptsResult:
        return ListPromptsResult(prompts=list(self._prompts))

    async def _get_prompt(self, ctx: Any, params: Any) -> GetPromptResult:
        action_info = self._prompt_name_to_action_info[params.name]
        headers, cookies = self._request_values(ctx)
        result = await action_info.func(
            response_handler=McpResponseHandler(),
            inputs=params.arguments or {},
            headers=headers,
            cookies=cookies,
        )
        return GetPromptResult(
            description=action_info.doc_desc,
            messages=[
                PromptMessage(role="user", content=TextContent(type="text", text=result))
            ],
        )

    def _resource_template_matches(
        self, uri_template: str, uri: str
    ) -> dict[str, Any] | None:
        pattern = uri_template.replace("{", "(?P<").replace("}", ">[^/]+)")
        match = re.match(f"^{pattern}$", uri)
        return match.groupdict() if match else None

    def register_action(
        self,
        func: Callable,
        action_package: Any,
        action: Any,
        display_name: str,
        doc_desc: str,
    ) -> None:
        options = json.loads(action.options) if action.options else {}
        kind = options.get("kind", "action")
        if kind == "resource":
            uri = options.get("uri")
            if not uri:
                raise ValueError(f"Resource {action.name} has no URI")
            if "{" in uri and "}" in uri:
                self._resource_templates.append(
                    ResourceTemplate(
                        uri_template=uri,
                        name=action.name,
                        description=doc_desc,
                        mime_type=options.get("mime_type"),
                    )
                )
                self._resource_template_to_action_info[uri] = ActionInfo(
                    func, action, display_name, doc_desc, "string"
                )
            else:
                resource_uri = uri
                self._resources[resource_uri] = Resource(
                    uri=resource_uri,
                    name=action.name,
                    description=doc_desc,
                    mime_type=options.get("mime_type"),
                    size=options.get("size"),
                )
                self._resource_to_action_info[uri] = ActionInfo(
                    func, action, display_name, doc_desc, "string"
                )
            return
        if kind == "prompt":
            schema = json.loads(action.input_schema)
            required = schema.get("required", [])
            self._prompts.append(
                Prompt(
                    name=action.name,
                    description=doc_desc,
                    arguments=[
                        PromptArgument(
                            name=name,
                            description=prop.get("description"),
                            required=name in required,
                        )
                        for name, prop in schema.get("properties", {}).items()
                    ],
                )
            )
            self._prompt_name_to_action_info[action.name] = ActionInfo(
                func, action, display_name, doc_desc, "string"
            )
            return

        output_schema = json.loads(action.output_schema)
        if output_schema.get("type") == "string":
            output_schema_kind: OutputSchemaKind = "string"
            use_output_schema = None
        elif output_schema.get("type") == "object":
            output_schema_kind = "object"
            use_output_schema = output_schema
        else:
            output_schema_kind = "wrap-in-result-object"
            use_output_schema = {
                "type": "object",
                "properties": {"result": output_schema},
                "required": ["result"],
            }
        self._tools.append(
            Tool(
                name=action.name,
                description=doc_desc,
                input_schema=json.loads(action.input_schema),
                output_schema=use_output_schema,
                annotations=ToolAnnotations(
                    title=options.get("title") or display_name,
                    read_only_hint=options.get("read_only_hint", False),
                    destructive_hint=options.get("destructive_hint", True),
                    idempotent_hint=options.get("idempotent_hint", False),
                    open_world_hint=options.get("open_world_hint", True),
                ),
            )
        )
        self._tool_name_to_action_info[action.name] = ActionInfo(
            func, action, display_name, doc_desc, output_schema_kind
        )

    def unregister_actions(self) -> None:
        self._init_state()

    def _init_state(self) -> None:
        self._tools: list[Tool] = []
        self._tool_name_to_action_info: dict[str, ActionInfo] = {}
        self._resources: dict[str, Resource] = {}
        self._resource_to_action_info: dict[str, ActionInfo] = {}
        self._resource_templates: list[ResourceTemplate] = []
        self._resource_template_to_action_info: dict[str, ActionInfo] = {}
        self._prompts: list[Prompt] = []
        self._prompt_name_to_action_info: dict[str, ActionInfo] = {}
