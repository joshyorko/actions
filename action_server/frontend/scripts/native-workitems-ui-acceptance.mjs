import assert from "node:assert/strict";
import { chromium } from "@playwright/test";

const input = JSON.parse(
    await new Promise((resolve) => {
        let value = "";
        process.stdin.setEncoding("utf8");
        process.stdin.on("data", (chunk) => (value += chunk));
        process.stdin.on("end", () => resolve(value));
    }),
);
const target = new URL(input.origin);
let phase = input.stage;
let browserContext;
let lastStatus = null;
const evidence = {};
const responses = [];

function safeErrorSummary(error) {
    let message = String(error?.message || error?.name || "unknown browser error");
    for (const sensitiveValue of [input.api_key, input.profile, target.origin]) {
        if (sensitiveValue) message = message.replaceAll(sensitiveValue, "[REDACTED]");
    }
    message = message
        .replace(/(?:[A-Za-z]:\\|\/)\S+/g, "[PATH]")
        .replace(/\b[A-Za-z0-9+/_=-]{32,}\b/g, "[REDACTED]");
    return message.slice(0, 320);
}

async function narrowViewport(page) {
    await page.setViewportSize({ width: 320, height: 640 });
    return page.evaluate(() => ({
        viewportWidth: window.innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        bodyWidth: document.body.scrollWidth,
    }));
}

async function signIn(page) {
    page.on("response", (response) => {
        const path = new URL(response.url()).pathname;
        if (
            ["/browser-session", "/api/work-items", "/api/work-items/stats"].includes(
                path,
            )
        ) {
            responses.push({ path, status: response.status() });
        }
    });
    phase = "runtime_http_preflight";
    const configResponse = await fetch(`${target.origin}/config`);
    evidence.runtimeConfigStatus = configResponse.status;
    assert.equal(configResponse.status, 200);
    phase = "sign_in_navigation";
    await page.goto(`${target.origin}/work-items`, {
        waitUntil: "networkidle",
    });
    phase = "sign_in_form";
    await page.getByLabel("API key", { exact: true }).fill(input.api_key);
    phase = "sign_in_submit";
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    phase = "sign_in_authenticated_surface";
    await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
}

async function normal() {
    phase = "browser_launch";
    browserContext = await chromium.launchPersistentContext(input.profile, {
        headless: true,
        viewport: { width: 320, height: 640 },
    });
    phase = "browser_page_setup";
    const page = browserContext.pages()[0] || (await browserContext.newPage());
    page.setDefaultTimeout(15_000);
    await signIn(page);

    phase = "empty_queue";
    const empty = await page.evaluate(async () => {
        const response = await fetch("/api/work-items");
        return { status: response.status, body: await response.json() };
    });
    lastStatus = empty.status;
    assert.equal(empty.status, 200);
    assert.deepEqual(empty.body.items, []);
    await page
        .getByRole("heading", { name: "No work items yet", exact: true })
        .waitFor();
    evidence.emptyQueue = { httpStatus: empty.status, total: empty.body.total };
    evidence.emptyNarrowWidth = await narrowViewport(page);
    assert.ok(evidence.emptyNarrowWidth.documentWidth <= 320);

    phase = "keyboard_create_dialog";
    const createTrigger = page.getByRole("button", {
        name: "Create First Item",
        exact: true,
    });
    evidence.createTriggerSemantics = await createTrigger.evaluate((element) => ({
        ariaHaspopup: element.getAttribute("aria-haspopup"),
        ariaExpanded: element.getAttribute("aria-expanded"),
        outerHtml: element.outerHTML,
    }));
    assert.equal(evidence.createTriggerSemantics.ariaHaspopup, "dialog");
    phase = "keyboard_reopen_create_dialog";
    await createTrigger.focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    await dialog.waitFor();
    evidence.createDialogBounds = await page.evaluate(() => {
        const rect = document
            .querySelector('[role="dialog"]')
            ?.getBoundingClientRect();
        return rect
            ? {
                  viewportWidth: window.innerWidth,
                  left: rect.left,
                  right: rect.right,
                  width: rect.width,
              }
            : null;
    });
    assert.ok(evidence.createDialogBounds);
    assert.ok(evidence.createDialogBounds.left >= 0);
    assert.ok(
        evidence.createDialogBounds.right <=
            evidence.createDialogBounds.viewportWidth,
    );
    await page.keyboard.press("Escape");
    await dialog.waitFor({ state: "hidden" });
    const restoredFocus = await page.evaluate(() => {
        const active = document.activeElement;
        return {
            tagName: active?.tagName || "",
            id: active?.id || "",
            role: active?.getAttribute("role") || "",
            ariaLabel: active?.getAttribute("aria-label") || "",
            text: active instanceof HTMLElement ? active.innerText.trim() : "",
        };
    });
    evidence.dialogEscapeFocus = restoredFocus;
    evidence.dialogEscapeRestoresFocus =
        restoredFocus.tagName === "BUTTON" &&
        restoredFocus.text === "Create First Item";
    assert.equal(evidence.dialogEscapeRestoresFocus, true);

    await createTrigger.focus();
    await page.keyboard.press("Enter");
    await dialog.waitFor();
    phase = "fill_create_item";
    await page.getByLabel("Queue Name", { exact: true }).fill("default");
    await page
        .getByLabel("Payload (JSON)", { exact: true })
        .fill('{"synthetic":"native-workitems-ui"}');
    await page.getByRole("button", { name: "Create", exact: true }).focus();
    await page.keyboard.press("Enter");
    phase = "submit_create_item";
    await dialog.waitFor({ state: "hidden" });
    await page.getByRole("heading", { name: "Work Items", exact: true }).waitFor();

    phase = "populated_queue";
    const populated = await page.evaluate(async () => {
        const response = await fetch("/api/work-items");
        return { status: response.status, body: await response.json() };
    });
    lastStatus = populated.status;
    assert.equal(populated.status, 200);
    assert.equal(populated.body.total, 1);
    const item = populated.body.items[0];
    assert.equal(item.queue_name, "default");
    assert.equal(item.state, "PENDING");
    assert.deepEqual(item.payload, { synthetic: "native-workitems-ui" });
    evidence.populatedQueue = {
        httpStatus: populated.status,
        total: populated.body.total,
        state: item.state,
        queueName: item.queue_name,
        createdInDatadirBackend: true,
    };

    phase = "keyboard_item_detail";
    const viewDetails = page.getByRole("button", {
        name: "View details",
        exact: true,
    });
    await viewDetails.focus();
    await page.keyboard.press("Enter");
    await page
        .getByText(`Work Item: ${item.id.slice(0, 8)}`, { exact: true })
        .waitFor();
    const detail = page.getByRole("dialog");
    evidence.detailReadback = {
        visible: true,
        payloadVisible:
            (await detail
                .getByText("native-workitems-ui", { exact: false })
                .count()) > 0,
        stateVisible:
            (await detail.getByText("PENDING", { exact: true }).count()) > 0,
    };
    assert.equal(evidence.detailReadback.payloadVisible, true);
    assert.equal(evidence.detailReadback.stateVisible, true);
    await page
        .getByRole("button", { name: "Close", exact: true })
        .last()
        .click();
    await detail.waitFor({ state: "hidden" });

    phase = "narrow_populated";
    evidence.populatedNarrowWidth = await narrowViewport(page);
    assert.ok(evidence.populatedNarrowWidth.documentWidth <= 320);

    evidence.browserVersion = browserContext.browser()?.version() || "unknown";
    await browserContext.close();
    browserContext = undefined;
    return evidence;
}

async function storageUnavailable() {
    phase = "browser_launch";
    browserContext = await chromium.launchPersistentContext(input.profile, {
        headless: true,
        viewport: { width: 320, height: 640 },
    });
    phase = "browser_page_setup";
    const page = browserContext.pages()[0] || (await browserContext.newPage());
    page.setDefaultTimeout(15_000);
    await signIn(page);

    phase = "storage_unavailable";
    const response = await page.evaluate(async () => {
        const result = await fetch("/api/work-items");
        return { status: result.status, body: await result.json() };
    });
    lastStatus = response.status;
    assert.equal(response.status, 503);
    assert.equal(response.body.detail.code, "work_items_storage_unavailable");
    await page
        .getByRole("heading", {
            name: "Work Items storage unavailable",
            exact: true,
        })
        .waitFor();
    await page.getByRole("button", { name: "Retry", exact: true }).waitFor();
    evidence.storageUnavailable = {
        httpStatus: response.status,
        code: response.body.detail.code,
        retryVisible: true,
        rawPathExposed: /workitems\.db|datadir/i.test(
            await page.locator("body").innerText(),
        ),
    };
    assert.equal(evidence.storageUnavailable.rawPathExposed, false);
    evidence.storageNarrowWidth = await narrowViewport(page);
    assert.ok(evidence.storageNarrowWidth.documentWidth <= 320);
    await browserContext.close();
    browserContext = undefined;
    return evidence;
}

async function authorizationDenied() {
    phase = "browser_launch";
    browserContext = await chromium.launchPersistentContext(input.profile, {
        headless: true,
        viewport: { width: 320, height: 640 },
    });
    phase = "browser_page_setup";
    const page = browserContext.pages()[0] || (await browserContext.newPage());
    page.setDefaultTimeout(15_000);
    await signIn(page);

    phase = "authorization_session_fixture";
    const cookiesBefore = await browserContext.cookies(target.origin);
    const hadBrowserSessionCookie = cookiesBefore.some(
        (cookie) => cookie.name === "actions_browser_session",
    );
    assert.equal(hadBrowserSessionCookie, true);
    await browserContext.clearCookies({ name: "actions_browser_session" });
    const cookiesAfter = await browserContext.cookies(target.origin);
    evidence.browserSessionCookieRemoved = !cookiesAfter.some(
        (cookie) => cookie.name === "actions_browser_session",
    );
    assert.equal(evidence.browserSessionCookieRemoved, true);

    phase = "authorization_denied_request";
    const denied = await page.evaluate(async () => {
        const response = await fetch("/api/work-items");
        return { status: response.status, body: await response.text() };
    });
    lastStatus = denied.status;
    assert.equal(denied.status, 403);
    assert.equal(denied.body, "Invalid or missing API Key");

    phase = "authorization_sign_in_recovery";
    await page.getByLabel("API key", { exact: true }).waitFor();
    evidence.protectedWorkItemsHidden =
        (await page
            .getByRole("heading", { name: "Work Items", exact: true })
            .count()) === 0;
    assert.equal(evidence.protectedWorkItemsHidden, true);
    evidence.signInRecoveryVisible =
        (await page
            .getByRole("button", { name: "Sign in", exact: true })
            .count()) === 1;
    assert.equal(evidence.signInRecoveryVisible, true);
    evidence.packageYamlInstructionVisible = /package\.yaml/i.test(
        await page.locator("body").innerText(),
    );
    assert.equal(evidence.packageYamlInstructionVisible, false);

    await page.getByLabel("API key", { exact: true }).fill(input.api_key);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
    await page
        .getByRole("heading", { name: "Work Items", exact: true })
        .waitFor();

    phase = "authorization_reauthenticated_readback";
    const recovered = await page.evaluate(async () => {
        const response = await fetch("/api/work-items");
        return { status: response.status, body: await response.json() };
    });
    lastStatus = recovered.status;
    assert.equal(recovered.status, 200);
    assert.equal(recovered.body.total, 1);
    assert.equal(recovered.body.items[0].state, "PENDING");
    assert.deepEqual(recovered.body.items[0].payload, {
        synthetic: "native-workitems-ui",
    });
    evidence.reauthenticatedQueueReadback = {
        httpStatus: recovered.status,
        total: recovered.body.total,
        state: recovered.body.items[0].state,
        payload: recovered.body.items[0].payload,
    };
    evidence.responses = responses.slice(-8);
    evidence.narrowWidth = await narrowViewport(page);
    assert.ok(evidence.narrowWidth.documentWidth <= 320);

    evidence.browserVersion = browserContext.browser()?.version() || "unknown";
    await browserContext.close();
    browserContext = undefined;
    return evidence;
}

try {
    let states;
    if (input.stage === "normal") {
        states = await normal();
    } else if (input.stage === "storage-error") {
        states = await storageUnavailable();
    } else if (input.stage === "authorization-denied") {
        states = await authorizationDenied();
    } else {
        throw new Error("unknown acceptance stage");
    }
    process.stdout.write(
        `${JSON.stringify({ status: "PASS", stage: input.stage, states })}\n`,
    );
} catch (error) {
    process.stdout.write(
        `${JSON.stringify({
            status: "FAIL",
            stage: input.stage,
            phase,
            httpStatus: lastStatus,
            errorType: error.name,
            errorSummary: safeErrorSummary(error),
            browserErrorCode:
                /net::ERR_[A-Z_]+/.exec(String(error.message))?.[0] || null,
            responses: responses.slice(-16),
            states: evidence,
        })}\n`,
    );
    process.exitCode = 1;
} finally {
    if (browserContext) await browserContext.close().catch(() => undefined);
}
