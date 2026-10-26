import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import {
    Client,
    StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";

const CANVAS_RESOURCE_URI =
    "ui://action-canvas/v1/canvas.html?query-fixture=0.1";
const HARNESS_ORIGIN = `http://127.0.0.1:${process.env.CANVAS_HARNESS_PORT ?? "4180"}`;

const builtCanvasResource = await readFile(
    new URL("../../dist-canvas/index.html", import.meta.url),
    "utf8",
);
const inlineModule = builtCanvasResource.match(
    /<script type="module">([\s\S]*?)<\/script>/u,
)?.[1];
if (!inlineModule)
    throw new Error("Built Canvas resource has no inline module.");
const moduleHash = createHash("sha256").update(inlineModule).digest("base64");
const semanticFixture: unknown = JSON.parse(
    await readFile(
        new URL(
            "./src/semantic-renderer/fixtures/canvas-spec-v1.fixture.json",
            import.meta.url,
        ),
        "utf8",
    ),
);

test("official MCP Apps bridge handles fixture calls and host context lifecycle", async ({
    page,
}) => {
    const externalRequests: string[] = [];
    await page.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== HARNESS_ORIGIN) {
            externalRequests.push(url.href);
            return route.abort();
        }
        if (url.pathname === "/index.html") {
            return route.fulfill({
                status: 200,
                contentType: "text/html; charset=utf-8",
                headers: {
                    "Content-Security-Policy": `default-src 'none'; script-src 'sha256-${moduleHash}'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'`,
                },
                body: builtCanvasResource,
            });
        }
        return route.continue();
    });
    await page.goto("/host-harness.html");
    const frame = page.frameLocator("iframe[title='Canvas query fixture']");
    await expect(page.locator("#host-protocol")).toHaveText("2026-01-26");
    await expect(frame.locator("#query-input")).toHaveValue("alpha");
    await expect(frame.getByTestId("mcp-host-theme")).toHaveText("light");
    await expect(frame.locator("html")).toHaveAttribute("data-theme", "light");
    await expect(frame.locator("html")).toHaveCSS("color-scheme", "light");
    await expect(frame.getByTestId("mcp-host-locale")).toHaveText("en-US");
    await expect(frame.getByTestId("mcp-tool-result-state")).toHaveText(
        "success",
    );
    await frame.getByRole("button", { name: "Search", exact: true }).click();
    await expect(
        frame.getByRole("rowheader", { name: "Alpha guide" }),
    ).toBeVisible();
    await expect(
        frame.getByRole("rowheader", { name: "Alpha checklist" }),
    ).toBeVisible();
    await frame.getByRole("button", { name: "Check artifact status" }).click();
    await expect(frame.getByText("Result artifact is ready.")).toBeVisible();
    await page.getByRole("button", { name: "Replace with beta" }).click();
    await expect(frame.locator("#query-input")).toHaveValue("beta");
    await expect(
        frame.getByRole("rowheader", { name: "Alpha guide" }),
    ).toHaveCount(0);
    await frame.getByRole("button", { name: "Search", exact: true }).click();
    await expect(
        frame.getByText("No records matched that query."),
    ).toBeVisible();
    await page.getByRole("button", { name: "Replace host context" }).click();
    await expect(frame.getByTestId("mcp-host-theme")).toHaveText("dark");
    await expect(frame.getByTestId("mcp-host-locale")).toHaveText("fr-FR");
    await expect(frame.locator("html")).toHaveAttribute("data-theme", "dark");
    await expect(frame.locator("html")).toHaveCSS("color-scheme", "dark");
    await page.evaluate((spec) => {
        const target = document.querySelector<HTMLIFrameElement>(
            "iframe[title='Canvas query fixture']",
        );
        target?.contentWindow?.postMessage(
            {
                jsonrpc: "2.0",
                method: "ui/notifications/tool-result",
                params: {
                    content: [],
                    _meta: { "actions.canvas": { preview: true, spec } },
                },
            },
            window.location.origin,
        );
    }, semanticFixture);
    await expect(frame.locator(".semantic-form")).toBeVisible();
    for (const appearance of [
        {
            theme: "light",
            background: "#ffffff",
            text: "#182230",
            computedBackground: "rgb(255, 255, 255)",
            computedText: "rgb(24, 34, 48)",
        },
        {
            theme: "dark",
            background: "#121212",
            text: "#eeeeee",
            computedBackground: "rgb(18, 18, 18)",
            computedText: "rgb(238, 238, 238)",
        },
    ]) {
        await page.evaluate((styles) => {
            const target = document.querySelector<HTMLIFrameElement>(
                "iframe[title='Canvas query fixture']",
            );
            target?.contentWindow?.postMessage(
                {
                    jsonrpc: "2.0",
                    method: "ui/notifications/host-context-changed",
                    params: {
                        theme: styles.theme,
                        styles: {
                            variables: {
                                "--color-background-primary": styles.background,
                                "--color-text-primary": styles.text,
                            },
                        },
                    },
                },
                window.location.origin,
            );
        }, appearance);
        await expect(frame.locator("html")).toHaveAttribute(
            "data-theme",
            appearance.theme,
        );
        await expect(frame.locator("html")).toHaveCSS(
            "color-scheme",
            appearance.theme,
        );
        await expect(frame.locator("html")).toHaveCSS(
            "--color-background-primary",
            appearance.background,
        );
        await expect(frame.locator("html")).toHaveCSS(
            "--color-text-primary",
            appearance.text,
        );
        await expect(frame.locator(".semantic-form")).toHaveCSS(
            "background-color",
            appearance.computedBackground,
        );
        await expect(frame.locator(".semantic-form")).toHaveCSS(
            "color",
            appearance.computedText,
        );
    }
    await page.getByRole("button", { name: "Remount view" }).click();
    await expect(frame.locator("#query-input")).toHaveValue("alpha");
    await expect(
        frame.getByRole("rowheader", { name: "Alpha guide" }),
    ).toHaveCount(0);
    await expect(frame.getByTestId("mcp-host-theme")).toHaveText("light");
    await expect(frame.locator("html")).toHaveAttribute("data-theme", "light");
    await expect(frame.locator("html")).toHaveCSS("color-scheme", "light");
    expect(
        await frame
            .locator("html")
            .evaluate((root) =>
                root.style.getPropertyValue("--color-background-primary"),
            ),
    ).toBe("");
    await expect(frame.getByText("must-not-render")).toHaveCount(0);
    expect(externalRequests).toEqual([]);
});

test("official bridge keeps unbroken semantic text within a narrow host viewport", async ({
    page,
}) => {
    const externalRequests: string[] = [];
    await page.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== HARNESS_ORIGIN) {
            externalRequests.push(url.href);
            return route.abort();
        }
        if (url.pathname === "/index.html") {
            return route.fulfill({
                status: 200,
                contentType: "text/html; charset=utf-8",
                headers: {
                    "Content-Security-Policy": `default-src 'none'; script-src 'sha256-${moduleHash}'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'`,
                },
                body: builtCanvasResource,
            });
        }
        return route.continue();
    });
    await page.goto("/host-harness.html");
    const frame = page.frameLocator("iframe[title='Canvas query fixture']");
    await expect(page.locator("#host-protocol")).toHaveText("2026-01-26");
    await expect(frame.locator("#query-input")).toHaveValue("alpha");

    // The width belongs to the fixture host. The Canvas resource keeps its
    // original CSS, script hash, and strict response policy.
    await page
        .locator("iframe[title='Canvas query fixture']")
        .evaluate((element) => {
            element.style.width = "300px";
        });
    const longText = "W".repeat(455);
    const spec = {
        schemaVersion: "actions.canvas-spec/v1",
        title: "Narrow viewport text fallback",
        visibility: ["model", "app"],
        bindingIds: [],
        root: {
            type: "stack",
            id: "narrow-text-root",
            children: [{ type: "text", id: "unbroken-text", text: longText }],
        },
    };
    await page.evaluate((fixtureSpec) => {
        const target = document.querySelector<HTMLIFrameElement>(
            "iframe[title='Canvas query fixture']",
        );
        target?.contentWindow?.postMessage(
            {
                jsonrpc: "2.0",
                method: "ui/notifications/tool-result",
                params: {
                    content: [],
                    _meta: {
                        "actions.canvas": { preview: true, spec: fixtureSpec },
                    },
                },
            },
            window.location.origin,
        );
    }, spec);
    const paragraph = frame.locator(".semantic-stack p");
    await expect(paragraph).toHaveText(longText);

    const measurements = await frame.locator("body").evaluate((body) => {
        const paragraphElement = body.querySelector(".semantic-stack p");
        const documentElement = body.ownerDocument.documentElement;
        if (!paragraphElement)
            throw new Error("Semantic text paragraph is missing.");
        return {
            bodyScrollWidth: body.scrollWidth,
            bodyClientWidth: body.clientWidth,
            documentScrollWidth: documentElement.scrollWidth,
            documentClientWidth: documentElement.clientWidth,
            paragraphScrollWidth: paragraphElement.scrollWidth,
            paragraphClientWidth: paragraphElement.clientWidth,
            paragraphText: paragraphElement.textContent,
        };
    });
    expect(measurements.paragraphText).toBe(longText);
    expect(measurements.bodyScrollWidth).toBeLessThanOrEqual(
        measurements.bodyClientWidth,
    );
    expect(measurements.documentScrollWidth).toBeLessThanOrEqual(
        measurements.documentClientWidth,
    );
    expect(measurements.paragraphScrollWidth).toBeLessThanOrEqual(
        measurements.paragraphClientWidth,
    );
    expect(externalRequests).toEqual([]);
});

test("official bridge renders a real Runtime Action result", async ({
    page,
}) => {
    const runtimeUrl = process.env.CANVAS_RUNTIME_MCP_URL;
    test.skip(!runtimeUrl, "Requires the Action Server process fixture.");
    if (!runtimeUrl) return;

    const client = new Client(
        { name: "canvas-runtime-acceptance", version: "0.1.0" },
        { capabilities: {} },
    );
    await client.connect(
        new StreamableHTTPClientTransport(new URL(runtimeUrl)),
    );
    try {
        const listedTools = await client.listTools();
        const searchTool = listedTools.tools.find(
            (tool) => tool.name === "canvas_fixture_search",
        );
        expect(searchTool?._meta?.ui).toEqual({
            resourceUri: CANVAS_RESOURCE_URI,
            visibility: ["model", "app"],
        });

        const resource = await client.readResource({
            uri: CANVAS_RESOURCE_URI,
        });
        const viewContent = resource.contents.find(
            (content) => "text" in content,
        );
        expect(
            viewContent && "mimeType" in viewContent && viewContent.mimeType,
        ).toBe("text/html;profile=mcp-app");
        expect(
            viewContent && "text" in viewContent ? viewContent.text : null,
        ).toBe(builtCanvasResource);

        const externalRequests: string[] = [];
        await page.route("**/*", async (route) => {
            const url = new URL(route.request().url());
            if (url.origin !== HARNESS_ORIGIN) {
                externalRequests.push(url.href);
                return route.abort();
            }
            if (url.pathname === "/index.html") {
                return route.fulfill({
                    status: 200,
                    contentType: "text/html; charset=utf-8",
                    headers: {
                        "Content-Security-Policy": `default-src 'none'; script-src 'sha256-${moduleHash}'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'`,
                    },
                    body:
                        viewContent && "text" in viewContent
                            ? viewContent.text
                            : "",
                });
            }
            return route.continue();
        });
        await page.route("**/__runtime_tool_call", async (route) => {
            const request = route.request().postDataJSON() as {
                name?: string;
                arguments?: Record<string, unknown>;
            };
            if (!request.name) {
                return route.fulfill({
                    status: 400,
                    body: "Missing tool name",
                });
            }
            const result = await client.callTool({
                name: request.name,
                arguments: request.arguments ?? {},
            });
            return route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify(result),
            });
        });

        await page.goto("/host-harness.html?runtime=1");
        const frame = page.frameLocator("iframe[title='Canvas query fixture']");
        await expect(page.locator("#host-protocol")).toHaveText("2026-01-26");
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
        await frame
            .getByRole("button", { name: "Check artifact status" })
            .click();
        await expect(
            frame.getByText("Result artifact is ready."),
        ).toBeVisible();
        expect(externalRequests).toEqual([]);
    } finally {
        await client.close();
    }
});
