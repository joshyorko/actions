import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";

import {
    Client,
    StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";
import { expect, test } from "@playwright/test";

const resourcePath = process.env.CANVAS_TEMPLATE_RESOURCE_PATH;
const runtimeUrl = process.env.CANVAS_RUNTIME_MCP_URL;
const resourceUri = "ui://action-canvas/v1/canvas.html?query-fixture=0.1";

if (!resourcePath || !runtimeUrl) {
    throw new Error(
        "Canvas template acceptance requires resource and Runtime paths.",
    );
}

const resourceHtml = await readFile(resourcePath, "utf8");
const moduleSource = resourceHtml.match(
    /<script type="module">([\s\S]*?)<\/script>/u,
)?.[1];
if (!moduleSource)
    throw new Error("Canvas template resource has no inline module.");
const moduleHash = createHash("sha256").update(moduleSource).digest("base64");

test("packaged Canvas template calls its real Runtime Action", async ({
    page,
}) => {
    const client = new Client(
        { name: "canvas-template-acceptance", version: "0.1.0" },
        { capabilities: {} },
    );
    let server: ReturnType<typeof createServer> | undefined;
    try {
        await client.connect(
            new StreamableHTTPClientTransport(new URL(runtimeUrl)),
        );

        const listed = await client.listTools();
        const searchTool = listed.tools.find(
            (tool) => tool.name === "canvas_fixture_search",
        );
        expect(searchTool?._meta?.ui).toEqual({
            resourceUri,
            visibility: ["model", "app"],
        });
        const resource = await client.readResource({ uri: resourceUri });
        const textContent = resource.contents.find(
            (content) => "text" in content,
        );
        expect(
            textContent && "mimeType" in textContent && textContent.mimeType,
        ).toBe("text/html;profile=mcp-app");
        expect(
            textContent && "text" in textContent ? textContent.text : null,
        ).toBe(resourceHtml);

        const toolCalls: string[] = [];
        const externalRequests: string[] = [];
        const hostHtml = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Canvas template host</title></head>
<body><iframe title="Canvas Query" src="/view"></iframe>
<script>
const frame = document.querySelector("iframe");
const origin = window.location.origin;
function send(method, params) {
  frame.contentWindow.postMessage({jsonrpc:"2.0", method, params}, origin);
}
window.addEventListener("message", async (event) => {
  if (event.source !== frame.contentWindow || event.origin !== origin) return;
  const message = event.data;
  if (!message || message.jsonrpc !== "2.0") return;
  if (message.method === "ui/initialize" && typeof message.id === "number") {
    frame.contentWindow.postMessage({jsonrpc:"2.0", id:message.id, result:{
      protocolVersion:message.params.protocolVersion,
      hostCapabilities:{serverTools:{}},
      hostInfo:{name:"local-template-test-host", version:"0.1.0"},
      hostContext:{theme:"light", locale:"en-US"}
    }}, origin);
  } else if (message.method === "ui/notifications/initialized") {
    send("ui/notifications/tool-input", {arguments:{query:"alpha"}});
  } else if (message.method === "tools/call" && typeof message.id === "number") {
    try {
      const response = await fetch("/__runtime_tool_call", {
        method:"POST", headers:{"content-type":"application/json"},
        body:JSON.stringify({name:message.params.name, arguments:message.params.arguments ?? {}})
      });
      const result = await response.json();
      frame.contentWindow.postMessage({jsonrpc:"2.0", id:message.id, result}, origin);
    } catch {
      frame.contentWindow.postMessage({jsonrpc:"2.0", id:message.id,
        error:{code:-32603, message:"Runtime tool call failed."}}, origin);
    }
  }
});
</script></body></html>`;
        server = createServer((request, response) => {
            if (request.url === "/") {
                response.writeHead(200, {
                    "content-type": "text/html; charset=utf-8",
                });
                response.end(hostHtml);
            } else if (request.url === "/view") {
                response.writeHead(200, {
                    "content-type": "text/html; charset=utf-8",
                    "content-security-policy": `default-src 'none'; script-src 'sha256-${moduleHash}'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'`,
                });
                response.end(resourceHtml);
            } else {
                response.writeHead(404);
                response.end();
            }
        });
        await new Promise<void>((resolve) =>
            server!.listen(0, "127.0.0.1", resolve),
        );
        const address = server.address();
        if (!address || typeof address === "string")
            throw new Error("Host server did not bind.");
        const hostOrigin = `http://127.0.0.1:${address.port}`;

        await page.route("**/*", async (route) => {
            const url = new URL(route.request().url());
            if (url.origin !== hostOrigin) {
                externalRequests.push(url.href);
                return route.abort();
            }
            if (url.pathname === "/__runtime_tool_call") {
                const body = route.request().postDataJSON() as {
                    name: string;
                    arguments?: Record<string, unknown>;
                };
                toolCalls.push(body.name);
                const result = await client.callTool({
                    name: body.name,
                    arguments: body.arguments ?? {},
                });
                return route.fulfill({
                    status: 200,
                    contentType: "application/json",
                    body: JSON.stringify(result),
                });
            }
            return route.continue();
        });

        await page.goto(hostOrigin);
        const frame = page.frameLocator("iframe[title='Canvas Query']");
        await expect(frame.locator("#query-input")).toHaveValue("alpha");
        await frame
            .getByRole("button", { name: "Search", exact: true })
            .click();
        await expect(
            frame.getByRole("rowheader", { name: "Alpha guide" }),
        ).toBeVisible();
        await expect(
            frame.getByRole("rowheader", { name: "Alpha checklist" }),
        ).toBeVisible();

        await frame.locator("#query-input").fill("unmatched-query");
        await frame
            .getByRole("button", { name: "Search", exact: true })
            .click();
        await expect(
            frame.getByText("No records matched that query."),
        ).toBeVisible();
        await expect(
            frame.getByRole("button", { name: "Check artifact status" }),
        ).toHaveCount(0);
        expect(toolCalls).toEqual([
            "canvas_fixture_search",
            "canvas_fixture_search",
        ]);
        expect(externalRequests).toEqual([]);
    } finally {
        await client.close();
        if (server?.listening) {
            await new Promise<void>((resolve, reject) =>
                server!.close((error) => (error ? reject(error) : resolve())),
            );
        }
    }
});
