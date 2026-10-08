/** Exercise the shipped Runtime with synthetic input; stdout is a bounded receipt. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const input = JSON.parse(readFileSync(0, "utf8"));
const target = new URL(input.origin);
assert.equal(target.hostname, "127.0.0.1");
assert.equal(target.protocol, "http:");
let phase = "launch";
let lastStatus = null;
let browser;
let result;
try {
    browser = await chromium.launch({
        headless: true,
        ...(input.browser_executable
            ? { executablePath: input.browser_executable }
            : {}),
    });
    const context = await browser.newContext();
    const page = await context.newPage();
    page.setDefaultTimeout(15_000);
    page.setDefaultNavigationTimeout(30_000);
    let pageErrors = 0;
    let externalRequests = 0;
    page.on("pageerror", () => {
        pageErrors += 1;
    });
    await context.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== target.origin) {
            externalRequests += 1;
            await route.abort();
        } else if (
            input.negative_control &&
            url.pathname === "/api/work-items" &&
            route.request().method() === "GET"
        ) {
            await route.fulfill({
                status: 403,
                contentType: "application/json",
                body: '{"detail":"synthetic negative control"}',
            });
        } else {
            await route.continue();
        }
    });
    const request = async (path, expectedStatus) => {
        const response = await page.evaluate(async (path) => {
            const response = await fetch(path);
            return { status: response.status, body: await response.json() };
        }, path);
        lastStatus = response.status;
        assert.equal(response.status, expectedStatus);
        return response.body;
    };

    phase = "sign_in";
    await page.goto(`${target.origin}/work-items`, {
        waitUntil: "networkidle",
    });
    await page.getByLabel("API key", { exact: true }).fill(input.api_key);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
    phase = "empty_queue";
    const empty = await request("/api/work-items", 200);
    assert.equal(empty.total, 0);
    assert.deepEqual(empty.items, []);

    phase = "session_cookie";
    const session = (await context.cookies()).find(
        (cookie) => cookie.name === "actions_browser_session",
    );
    assert.ok(session);
    assert.equal(session.httpOnly, true);
    assert.equal(session.sameSite, "Strict");
    assert.equal(
        await page.evaluate(() =>
            document.cookie.includes("actions_browser_session="),
        ),
        false,
    );
    assert.equal(
        await page.evaluate(
            (key) => Object.values(localStorage).join("").includes(key),
            input.api_key,
        ),
        false,
    );

    phase = "websocket_echo";
    await page.evaluate(
        () =>
            new Promise((resolve, reject) => {
                const socket = new WebSocket(`ws://${location.host}/api/ws`);
                const timer = setTimeout(() => {
                    socket.close();
                    reject(new Error("echo timeout"));
                }, 5000);
                socket.onopen = () =>
                    socket.send(
                        JSON.stringify({
                            event: "echo",
                            data: "synthetic-native-probe",
                        }),
                    );
                socket.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        if (
                            message.event !== "echo" ||
                            message.data !== "synthetic-native-probe"
                        )
                            return;
                        clearTimeout(timer);
                        socket.close();
                        resolve(true);
                    } catch {
                        clearTimeout(timer);
                        socket.close();
                        reject(new Error("invalid echo"));
                    }
                };
                socket.onerror = () => {
                    clearTimeout(timer);
                    socket.close();
                    reject(new Error("echo connection failed"));
                };
            }),
    );

    phase = "create_list_detail";
    await page
        .getByRole("button", {
            name: /Create First Item|Create Item/,
            exact: true,
        })
        .click();
    await page.getByLabel("Queue Name", { exact: true }).fill("default");
    await page
        .getByLabel("Payload (JSON)", { exact: true })
        .fill('{"synthetic":"native-browser-acceptance"}');
    await page.getByRole("button", { name: "Create", exact: true }).click();
    await page
        .getByText("native-browser-acceptance", { exact: false })
        .first()
        .waitFor();
    const list = await request("/api/work-items", 200);
    assert.equal(list.total, 1);
    assert.equal(list.items.length, 1);
    const item = list.items[0];
    assert.equal(item.state, "PENDING");
    assert.equal(item.queue_name, "default");
    assert.deepEqual(item.payload, { synthetic: "native-browser-acceptance" });
    await page
        .getByRole("row")
        .filter({ hasText: "native-browser-acceptance" })
        .click();
    await page
        .getByText(`Work Item: ${item.id.substring(0, 8)}`, { exact: true })
        .waitFor();
    await page.keyboard.press("Escape");

    phase = "logout";
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await page.getByLabel("API key", { exact: true }).waitFor();
    // The auth middleware deliberately emits plain text, so check status only here.
    lastStatus = await page.evaluate(
        async () => (await fetch("/api/work-items")).status,
    );
    assert.equal(lastStatus, 403);
    phase = "browser_errors";
    assert.equal(pageErrors, 0);
    assert.equal(externalRequests, 0);
    result = {
        status: "PASS",
        browser: "chromium",
        browser_version: browser.version(),
        item_id: item.id,
        checks: [
            "sign_in",
            "empty_queue",
            "http_only_cookie",
            "no_key_in_local_storage",
            "authenticated_websocket_echo",
            "create_list_detail",
            "logout",
            "no_page_errors",
            "no_external_requests",
        ],
    };
} catch (error) {
    // Do not dump Playwright errors, headers, cookies, keys or page contents.
    result = {
        status: "FAIL",
        phase,
        http_status: lastStatus,
        error_type: error.name,
    };
} finally {
    if (browser) {
        try {
            await browser.close();
        } catch {
            result = { status: "FAIL", phase: "browser_cleanup" };
        }
    }
}
process.stdout.write(`${JSON.stringify(result)}\n`);
process.exitCode = result.status === "PASS" ? 0 : 1;
