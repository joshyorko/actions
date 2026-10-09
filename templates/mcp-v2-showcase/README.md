# MCP v2 Showcase

This small project demonstrates the core, stateless MCP surface exposed by
Action Server. It uses a fixed local catalog; it does not call a product service
or an external API.

## Start the project

Create the project from Action Server's embedded template bundle:

```bash
action-server new --name mcp-demo --template mcp-v2-showcase
cd mcp-demo
action-server start
```

Project creation uses the embedded template bundle and does not fetch template
metadata or archives. Resolving Python and package dependencies for startup is a
separate step and may use the configured package index.

## Exercise the MCP endpoint

In another terminal, run the standard-library client:

```bash
python examples/mcp_client.py --base-url http://localhost:8080/mcp
```

The client sends independent requests using MCP `2026-07-28`: `server/discover`,
the tools/resources/resource-templates/prompts catalogs, a typed tool call, a
direct resource read, a resource-template read, and a prompt request. Each POST
has a fresh request ID and `X-Request-ID`; the server's catalog revision is a
fingerprint of registered tools, resources, templates, and prompts, not of
changing resource contents or tool results. Catalogs are immediately stale
(`ttlMs=0`) and privately scoped (`cacheScope=private`).

The `lookup_demo_item` tool returns structured content. An unknown ID uses the
fixed message `No demo item matches this ID.`; the message does not reflect the
supplied ID. The tool and resources read only static data.

The endpoint is stateless: requests do not use `initialize`/`initialized` or a
session header. This is the core MCP protocol; it does not include MCP Apps,
Canvas, `ui://` resources, or durable Tasks.

## Open and close the GET/SSE channel

```bash
python examples/open_close_sse.py --base-url http://localhost:8080/mcp
```

This example checks that the streamable HTTP event stream can open and closes
it immediately with a finite timeout. It does not claim that the server emits
tool-progress events. `/sse` is not part of this protocol surface.

Run the deterministic local actions tests with `pytest tests`.
