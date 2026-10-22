import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";

import {
    Client,
    StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";
import { expect, test } from "@playwright/test";
import { z } from "zod";

const runtimeUrl = z.string().url().parse(process.env.CANVAS_RUNTIME_MCP_URL);
const resourceUri = z.string().parse(process.env.CANVAS_INVOICE_RESOURCE_URI);
const handle = z.string().parse(process.env.CANVAS_INVOICE_HANDLE);
const resourceHtml = await readFile(
    z.string().parse(process.env.CANVAS_TEMPLATE_RESOURCE_PATH),
    "utf8",
);
const moduleSource = resourceHtml.match(
    /<script type="module">([\s\S]*?)<\/script>/u,
)?.[1];
if (!moduleSource) throw new Error("Missing built module.");
const moduleHash = createHash("sha256").update(moduleSource).digest("base64");
const headers = {
    Authorization: "Bearer installation-key",
    "X-Fixture-Credential": "app-secret",
    "X-Test-Credential": "server-held-reader-secret",
};

test("real invoice tool resource view paging export and reopen", async ({
    page,
}) => {
    const client = new Client(
        { name: "local-invoice-e2-host", version: "0.1.0" },
        { capabilities: {} },
    );
    const calls: string[] = [];
    const downloads: string[] = [];
    const external: string[] = [];
    let exportDigest: string | null = null;
    let exportSize: number | null = null;
    try {
        await client.connect(
            new StreamableHTTPClientTransport(new URL(runtimeUrl), {
                requestInit: { headers },
            }),
        );
        const resource = await client.readResource({ uri: resourceUri });
        const text = resource.contents.find((content) => "text" in content);
        expect(text && "text" in text ? text.text : null).toBe(resourceHtml);
        const initial = await client.callTool({
            name: "invoice_result",
            arguments: { handle },
        });
        expect(initial.isError).not.toBe(true);
        expect(initial.structuredContent).not.toHaveProperty("rows");

        await page.exposeFunction(
            "actualInvoiceTool",
            async (value: unknown) => {
                const request = z
                    .object({
                        name: z.enum([
                            "invoice_result_page",
                            "invoice_result_export",
                            "invoice_review_offer",
                            "invoice_review_decide",
                        ]),
                        arguments: z.record(z.string(), z.unknown()),
                    })
                    .parse(value);
                calls.push(request.name);
                const result = await client.callTool(request);
                if (request.name === "invoice_result_export") {
                    const descriptor = z
                        .object({ digest: z.string(), size: z.number() })
                        .parse(result._meta?.["actions.invoiceExport"]);
                    exportDigest = descriptor.digest;
                    exportSize = descriptor.size;
                }
                return result;
            },
        );
        await page.exposeFunction(
            "actualInvoiceDownload",
            async (value: unknown) => {
                const request = z
                    .object({
                        contents: z
                            .array(z.object({ uri: z.string().url() }))
                            .length(1),
                    })
                    .parse(value);
                const uri = new URL(request.contents[0].uri);
                expect(uri.origin).toBe(new URL(runtimeUrl).origin);
                expect(uri.pathname).toMatch(
                    new RegExp(`/outputs/${handle}$`, "u"),
                );
                const response = await fetch(uri, { headers });
                expect(response.status).toBe(200);
                expect(response.headers.get("cache-control")).toBe("no-store");
                const bytes = Buffer.from(await response.arrayBuffer());
                expect(bytes.length).toBe(exportSize);
                expect(
                    "sha256:" +
                        createHash("sha256").update(bytes).digest("hex"),
                ).toBe(exportDigest);
                const lines = bytes
                    .toString("utf8")
                    .trim()
                    .split("\n")
                    .map((line) =>
                        z
                            .object({ invoice_id: z.string() })
                            .parse(JSON.parse(line)),
                    );
                expect(lines.map((line) => line.invoice_id)).toEqual([
                    "inv-001",
                    "inv-002",
                ]);
                downloads.push(
                    createHash("sha256").update(bytes).digest("hex"),
                );
                return {};
            },
        );

        // This is an explicit local host simulation. All tool and download
        // answers come from the real Runtime socket, never fixture responses.
        const hostOrigin = "http://127.0.0.1:39817";
        const host = `<!doctype html><html><body><iframe title="Invoice Canvas" src="/view"></iframe><script>
const frame = document.querySelector('iframe');
window.addEventListener('message', async event => {
  if (event.source !== frame.contentWindow || event.origin !== location.origin) return;
  const message = event.data;
  const reply = result => frame.contentWindow.postMessage({jsonrpc:'2.0', id:message.id, result}, location.origin);
  if (message.method === 'ui/initialize') reply({protocolVersion:message.params.protocolVersion, hostCapabilities:{serverTools:{},downloadFile:{}}, hostInfo:{name:'explicit-local-e2-host',version:'0.1.0'},hostContext:{theme:'light'}});
  else if (message.method === 'ui/notifications/initialized') {
    frame.contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-input',params:{arguments:{handle:${JSON.stringify(handle)}}}}, location.origin);
    frame.contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:${JSON.stringify(initial)}}, location.origin);
  } else if (message.method === 'tools/call') reply(await window.actualInvoiceTool(message.params));
  else if (message.method === 'ui/download-file') reply(await window.actualInvoiceDownload(message.params));
});
</script></body></html>`;
        await page.route("**/*", async (route) => {
            const url = new URL(route.request().url());
            if (url.origin !== hostOrigin) {
                external.push(url.origin);
                return route.abort();
            }
            if (url.pathname === "/")
                return route.fulfill({ contentType: "text/html", body: host });
            if (url.pathname === "/view")
                return route.fulfill({
                    contentType: "text/html",
                    headers: {
                        "Content-Security-Policy": `default-src 'none'; script-src 'sha256-${moduleHash}'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'`,
                    },
                    body: resourceHtml,
                });
            return route.abort();
        });
        await page.goto(hostOrigin);
        const view = page.frameLocator("iframe");
        await expect(
            view.getByRole("heading", { name: "Invoice results" }),
        ).toBeVisible();
        await expect(
            view.getByRole("rowheader", { name: "North" }),
        ).toBeVisible();
        await expect(view.getByRole("textbox")).toHaveCount(0);
        await view.getByRole("button", { name: "Next page" }).click();
        await expect(
            view.getByRole("rowheader", { name: "South" }),
        ).toBeVisible();
        await view.getByRole("button", { name: "Export invoices" }).click();
        await expect.poll(() => downloads.length).toBe(1);
        await page.reload();
        await expect(
            view.getByRole("rowheader", { name: "North" }),
        ).toBeVisible();
        expect(calls).toEqual(["invoice_result_page", "invoice_result_export"]);
        await view
            .getByRole("button", { name: "Review these results" })
            .click();
        await expect(
            view.getByText(/including rows beyond this page/),
        ).toBeVisible();
        expect(calls).not.toContain("invoice_review_decide");
        await view
            .getByRole("button", { name: "Approve these results" })
            .click();
        await expect(
            view.getByText("Approved. Work item created."),
        ).toBeVisible();
        await page.reload();
        await view
            .getByRole("button", { name: "Review these results" })
            .click();
        await expect(
            view.getByText("Approved. Work item created."),
        ).toBeVisible();
        expect(calls).toEqual([
            "invoice_result_page",
            "invoice_result_export",
            "invoice_review_offer",
            "invoice_review_decide",
            "invoice_review_offer",
        ]);
        expect(external).toEqual([]);
        await writeFile(
            z.string().parse(process.env.CANVAS_INVOICE_BROWSER_RECEIPT),
            JSON.stringify(
                {
                    evidence: "E2-local-host-simulation-not-ChatGPT",
                    resourceUri,
                    htmlSha256: createHash("sha256")
                        .update(resourceHtml)
                        .digest("hex"),
                    tools: calls,
                    downloadedSha256: downloads,
                    exportDigest,
                    exportSize,
                    externalRequests: external,
                    reopenSameHandle: true,
                    explicitExactResultReview: true,
                    reopenApprovedReceipt: true,
                },
                null,
                2,
            ) + "\n",
        );
    } finally {
        await client.close();
    }
});
