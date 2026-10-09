import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

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

test("official MCP Apps bridge handles fixture calls and host context lifecycle", async ({
    page,
}) => {
    const externalRequests: string[] = [];
    await page.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== "http://127.0.0.1:4180") {
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
    await page.getByRole("button", { name: "Remount view" }).click();
    await expect(frame.locator("#query-input")).toHaveValue("alpha");
    await expect(
        frame.getByRole("rowheader", { name: "Alpha guide" }),
    ).toHaveCount(0);
    await expect(frame.getByTestId("mcp-host-theme")).toHaveText("light");
    await expect(frame.getByText("must-not-render")).toHaveCount(0);
    expect(externalRequests).toEqual([]);
});
