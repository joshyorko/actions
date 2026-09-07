import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

from mcp.types import (
    CallToolResult,
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
CATALOG_REVISION_META_KEY = "actions.catalogRevision"
CATALOG_TTL_MS = 0
CATALOG_CACHE_SCOPE = "private"
OutputSchemaKind = Literal["string", "object", "wrap-in-result-object"]


@dataclass
class ActionInfo:
    func: Callable
    action: Any
    display_name: str
    doc_desc: str
    output_schema_kind: OutputSchemaKind
    mcp_meta: dict[str, Any] | None


@dataclass
class _McpCatalog:
    tools: list[Tool]
    tool_name_to_action_info: dict[str, ActionInfo]
    resources: dict[str, Resource]
    resource_to_action_info: dict[str, ActionInfo]
    resource_templates: list[ResourceTemplate]
    resource_template_to_action_info: dict[str, ActionInfo]
    prompts: list[Prompt]
    prompt_name_to_action_info: dict[str, ActionInfo]


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
        catalog = self._catalog
        return ListToolsResult(
            tools=list(catalog.tools), **self._catalog_result_metadata(catalog)
        )

    async def _call_tool(self, ctx: Any, params: Any):
        catalog = self._catalog
        try:
            from actions.server._actions_run import IInternalFuncAPI

            headers, cookies = self._request_values(ctx)
            action_info = catalog.tool_name_to_action_info[params.name]
            func: IInternalFuncAPI = action_info.func
            result = await func(
                response_handler=McpResponseHandler(),
                inputs=params.arguments or {},
                headers=headers,
                cookies=cookies,
            )
            if action_info.output_schema_kind == "string":
                return CallToolResult(
                    content=[TextContent(type="text", text=result)],
                    _meta=action_info.mcp_meta,
                )
            if action_info.output_schema_kind == "object":
                return CallToolResult(
                    content=[], structured_content=result, _meta=action_info.mcp_meta
                )
            if action_info.output_schema_kind == "wrap-in-result-object":
                return CallToolResult(
                    content=[],
                    structured_content={"result": result},
                    _meta=action_info.mcp_meta,
                )
            raise ValueError(
                f"Unknown output schema kind: {action_info.output_schema_kind}"
            )
        except Exception:
            log.exception("Error calling tool %s", params.name)
            raise

    async def _list_resources(self, _ctx: Any, _params: Any) -> ListResourcesResult:
        catalog = self._catalog
        return ListResourcesResult(
            resources=sorted(catalog.resources.values(), key=lambda item: str(item.uri)),
            **self._catalog_result_metadata(catalog),
        )

    async def _list_resource_templates(
        self, _ctx: Any, _params: Any
    ) -> ListResourceTemplatesResult:
        catalog = self._catalog
        return ListResourceTemplatesResult(
            resource_templates=sorted(
                catalog.resource_templates, key=lambda item: item.uri_template
            ),
            **self._catalog_result_metadata(catalog),
        )

    async def _read_resource(self, ctx: Any, params: Any) -> ReadResourceResult:
        catalog = self._catalog
        uri = str(params.uri)
        action_info = catalog.resource_to_action_info.get(uri)
        mime_type = None
        inputs: dict[str, Any] = {}
        if action_info:
            resource = catalog.resources.get(params.uri)
            mime_type = resource.mime_type if resource else None
        else:
            for template in catalog.resource_templates:
                found_params = self._resource_template_matches(
                    template.uri_template, uri
                )
                if found_params:
                    mime_type = template.mime_type
                    inputs = found_params
                    action_info = catalog.resource_template_to_action_info[
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
            _meta=action_info.mcp_meta,
            contents=[
                TextResourceContents(
                    uri=uri, text=text, mime_type=mime_type or default_mime
                )
            ],
        )

    async def _list_prompts(self, _ctx: Any, _params: Any) -> ListPromptsResult:
        catalog = self._catalog
        return ListPromptsResult(
            prompts=list(catalog.prompts), **self._catalog_result_metadata(catalog)
        )

    @property
    def catalog_revision(self) -> str:
        return self._catalog_revision(self._catalog)

    @staticmethod
    def _catalog_revision(catalog: _McpCatalog) -> str:
        catalog = {
            "prompts": [
                item.model_dump(by_alias=True, mode="json", exclude_none=True)
                for item in sorted(catalog.prompts, key=lambda item: item.name)
            ],
            "resources": [
                item.model_dump(by_alias=True, mode="json", exclude_none=True)
                for item in sorted(
                    catalog.resources.values(), key=lambda item: str(item.uri)
                )
            ],
            "resourceTemplates": [
                item.model_dump(by_alias=True, mode="json", exclude_none=True)
                for item in sorted(
                    catalog.resource_templates, key=lambda item: item.uri_template
                )
            ],
            "tools": [
                item.model_dump(by_alias=True, mode="json", exclude_none=True)
                for item in sorted(catalog.tools, key=lambda item: item.name)
            ],
        }
        canonical = json.dumps(catalog, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _catalog_result_metadata(self, catalog: _McpCatalog | None = None) -> dict[str, Any]:
        if catalog is None:
            catalog = self._catalog
        return {
            "_meta": {CATALOG_REVISION_META_KEY: self._catalog_revision(catalog)},
            "ttlMs": CATALOG_TTL_MS,
            "cacheScope": CATALOG_CACHE_SCOPE,
        }

    async def _get_prompt(self, ctx: Any, params: Any) -> GetPromptResult:
        catalog = self._catalog
        action_info = catalog.prompt_name_to_action_info[params.name]
        headers, cookies = self._request_values(ctx)
        result = await action_info.func(
            response_handler=McpResponseHandler(),
            inputs=params.arguments or {},
            headers=headers,
            cookies=cookies,
        )
        return GetPromptResult(
            _meta=action_info.mcp_meta,
            description=action_info.doc_desc,
            messages=[
                PromptMessage(
                    role="user", content=TextContent(type="text", text=result)
                )
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
        catalog = self._catalog
        options = json.loads(action.options) if action.options else {}
        mcp_meta = options.get("_meta")
        if mcp_meta is not None and not isinstance(mcp_meta, dict):
            raise ValueError(f"MCP _meta for {action.name} must be an object")
        kind = options.get("kind", "action")
        if kind == "resource":
            uri = options.get("uri")
            if not uri:
                raise ValueError(f"Resource {action.name} has no URI")
            if "{" in uri and "}" in uri:
                if uri in catalog.resource_template_to_action_info:
                    raise ValueError(f"duplicate resource template URI: {uri}")
                catalog.resource_templates.append(
                    ResourceTemplate(
                        uri_template=uri,
                        name=action.name,
                        description=doc_desc,
                        mime_type=options.get("mime_type"),
                        _meta=mcp_meta,
                    )
                )
                catalog.resource_template_to_action_info[uri] = ActionInfo(
                    func, action, display_name, doc_desc, "string", mcp_meta
                )
                catalog.resource_templates.sort(key=lambda item: item.uri_template)
            else:
                resource_uri = uri
                if resource_uri in catalog.resources:
                    raise ValueError(f"duplicate resource URI: {resource_uri}")
                catalog.resources[resource_uri] = Resource(
                    uri=resource_uri,
                    name=action.name,
                    description=doc_desc,
                    mime_type=options.get("mime_type"),
                    size=options.get("size"),
                    _meta=mcp_meta,
                )
                catalog.resource_to_action_info[uri] = ActionInfo(
                    func, action, display_name, doc_desc, "string", mcp_meta
                )
            return
        if kind == "prompt":
            if action.name in catalog.prompt_name_to_action_info:
                raise ValueError(f"duplicate prompt name: {action.name}")
            schema = json.loads(action.input_schema)
            required = schema.get("required", [])
            catalog.prompts.append(
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
                    _meta=mcp_meta,
                )
            )
            catalog.prompt_name_to_action_info[action.name] = ActionInfo(
                func, action, display_name, doc_desc, "string", mcp_meta
            )
            catalog.prompts.sort(key=lambda item: item.name)
            return

        if action.name in catalog.tool_name_to_action_info:
            raise ValueError(f"duplicate tool name: {action.name}")
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
        catalog.tools.append(
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
                _meta=mcp_meta,
            )
        )
        catalog.tool_name_to_action_info[action.name] = ActionInfo(
            func, action, display_name, doc_desc, output_schema_kind, mcp_meta
        )
        catalog.tools.sort(key=lambda item: item.name)

    def replace_catalog(self, replacement: "McpServerSetupHelper") -> None:
        """Atomically publish a fully built catalog for the persistent server."""
        catalog = replacement._catalog
        self._catalog = catalog
        self._tools = catalog.tools
        self._tool_name_to_action_info = catalog.tool_name_to_action_info
        self._resources = catalog.resources
        self._resource_to_action_info = catalog.resource_to_action_info
        self._resource_templates = catalog.resource_templates
        self._resource_template_to_action_info = catalog.resource_template_to_action_info
        self._prompts = catalog.prompts
        self._prompt_name_to_action_info = catalog.prompt_name_to_action_info

    def unregister_actions(self) -> None:
        self._init_state()

    def _init_state(self) -> None:
        self._catalog = _McpCatalog([], {}, {}, {}, [], {}, [], {})
        self._tools = self._catalog.tools
        self._tool_name_to_action_info = self._catalog.tool_name_to_action_info
        self._resources = self._catalog.resources
        self._resource_to_action_info = self._catalog.resource_to_action_info
        self._resource_templates = self._catalog.resource_templates
        self._resource_template_to_action_info = self._catalog.resource_template_to_action_info
        self._prompts = self._catalog.prompts
        self._prompt_name_to_action_info = self._catalog.prompt_name_to_action_info
