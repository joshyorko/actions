/** Bounded browser readback of large synthetic stored results in a real Runtime. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";
const input = JSON.parse(readFileSync(0, "utf8"));
const origin = new URL(input.origin);
assert.equal(origin.hostname, "127.0.0.1");
let browser;
let phase = "launch";
try {
    browser = await chromium.launch({
        headless: true,
        ...(input.browser_executable
            ? { executablePath: input.browser_executable }
            : {}),
    });
    const context = await browser.newContext();
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    await page.addInitScript(() => {
        window.__nativeHistorySockets = [];
        const Original = window.WebSocket;
        window.WebSocket = class extends Original {
            constructor(...args) {
                super(...args);
                window.__nativeHistorySockets.push(this);
            }
        };
    });
    const errors = [];
    const requests = [];
    const responses = [];
    const summaries = [];
    await context.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== origin.origin || url.pathname === "/api/runs") {
            errors.push("unexpected_unbounded_or_external_request");
            await route.abort();
        } else {
            requests.push(url.pathname + url.search);
            await route.continue();
        }
    });
    page.on("pageerror", () => errors.push("page_error"));
    page.on("response", (response) => {
        if (new URL(response.url()).pathname === "/api/runs/summary") {
            responses.push(
                (async () => {
                    assert.equal(response.status(), 200);
                    const data = await response.body();
                    assert.ok(data.length < 1024 * 1024);
                    const rows = JSON.parse(data.toString());
                    assert.ok(rows.length <= 200);
                    for (const row of rows) {
                        assert.equal("result" in row, false);
                        assert.equal("inputs" in row, false);
                    }
                    summaries.push({ count: rows.length, bytes: data.length });
                })(),
            );
        }
    });
    phase = "login";
    await page.goto(input.origin + "/runs", { waitUntil: "networkidle" });
    await page.getByLabel("API key", { exact: true }).fill(input.api_key);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    phase = "first_page";
    await page
        .getByText("Loaded 200 runs, newest first.", { exact: true })
        .waitFor();
    phase = "pagination";
    await page
        .getByRole("button", { name: "Load older runs", exact: true })
        .click();
    await page
        .getByText(`Showing all ${input.run_count} runs.`, { exact: true })
        .waitFor();
    phase = "reconnect";
    const initialRequests = requests.length;
    const refreshedPage = page.waitForResponse(
        (response) =>
            new URL(response.url()).pathname === "/api/runs/summary" &&
            new URL(response.url()).searchParams.get("offset") === "200",
    );
    await page.evaluate(() => {
        const socket = window.__nativeHistorySockets.find(
            (socket) => socket.readyState === WebSocket.OPEN,
        );
        if (!socket || !socket.url.endsWith("/api/ws/summary"))
            throw Error("missing summary socket");
        socket.close();
    });
    await page.waitForFunction(
        () =>
            window.__nativeHistorySockets.length >= 2 &&
            window.__nativeHistorySockets.at(-1).readyState === WebSocket.OPEN,
    );
    await refreshedPage;
    await page
        .getByText(`Showing all ${input.run_count} runs.`, { exact: true })
        .waitFor();
    assert.ok(
        requests
            .slice(initialRequests)
            .some((path) => path.includes("/api/runs/summary")),
    );
    await Promise.all(responses);
    assert.ok(summaries.some((value) => value.count === 200));
    assert.ok(summaries.some((value) => value.count === input.run_count - 200));
    assert.deepEqual(errors, []);
    console.log(
        JSON.stringify({
            status: "PASS",
            browser: browser.version(),
            checks: [
                "bounded_history",
                "pagination",
                "reconnect_cache_refresh",
                "no_legacy_list_request",
            ],
            summaries,
        }),
    );
} catch {
    console.log(JSON.stringify({ status: "FAIL", phase }));
    process.exitCode = 1;
} finally {
    if (browser) await browser.close();
}
