// Operate the real loopback demo page. No intercepted or fixture HTTP answers.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";
import { chromium } from "@playwright/test";

const { values } = parseArgs({
    options: {
        url: { type: "string" },
        out: { type: "string" },
        resume: { type: "boolean", default: false },
    },
});
const origin = new URL(values.url);
assert.equal(origin.protocol, "http:");
assert.equal(origin.hostname, "127.0.0.1");
assert.ok(path.isAbsolute(values.out));
await mkdir(values.out, { recursive: true });
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
});
const page = await context.newPage();
const errors = [],
    external = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("request", (request) => {
    if (
        !request.url().startsWith("blob:") &&
        new URL(request.url()).origin !== origin.origin
    )
        external.push(request.url());
});
try {
    await page.goto(origin.origin, { waitUntil: "networkidle" });
    const frame = page.frameLocator("iframe");
    await frame.getByRole("heading", { name: "Invoice results" }).waitFor();
    await frame
        .getByRole("rowheader", { name: "Northstar Synthetic Supply" })
        .waitFor();
    for (const source of [
        "INV-1001",
        "PO-2001",
        "LED-3001",
        "INV-1002",
        "PO-2002",
        "INV-1003",
        "LED-3004",
    ])
        assert.ok((await frame.locator("table").innerText()).includes(source));
    await page.screenshot({
        path: path.join(values.out, "before-review.png"),
        fullPage: true,
    });
    const before = await (
        await page.request.get(origin.origin + "/owned-demo/state")
    ).json();
    if (!values.resume) {
        assert.equal(before.review_state, "not offered");
        assert.equal(before.worker_run_id, null);
        await frame
            .getByRole("button", { name: "Review these results" })
            .click();
        await frame
            .getByRole("button", { name: "Approve these results" })
            .waitFor();
        await page.screenshot({
            path: path.join(values.out, "exact-result-review.png"),
            fullPage: true,
        });
        await frame
            .getByRole("button", { name: "Approve these results" })
            .click();
        await frame
            .getByText("Approved. Work item created.", { exact: true })
            .waitFor();
    } else {
        assert.equal(before.review_state, "approved");
    }
    await page
        .getByRole("button", {
            name: "Run approved reconciliation",
            exact: true,
        })
        .click();
    await page.waitForFunction(
        () =>
            document
                .querySelector("#run-state")
                ?.textContent?.includes("completed:"),
        undefined,
        { timeout: 120000 },
    );
    await frame
        .getByRole("button", { name: "Review these results" })
        .click()
        .catch(() => {});
    await frame.getByRole("button", { name: "Check execution result" }).click();
    await frame
        .getByRole("button", { name: "Download execution result" })
        .waitFor();
    const downloadWait = page.waitForEvent("download");
    await frame
        .getByRole("button", { name: "Download execution result" })
        .click();
    await (await downloadWait).saveAs(path.join(values.out, "execution.json"));
    const after = await (
        await page.request.get(origin.origin + "/owned-demo/state")
    ).json();
    const data = JSON.parse(
        await readFile(path.join(values.out, "execution.json"), "utf8"),
    );
    assert.equal(data.task.reconciliation.matched, 1);
    assert.equal(data.task.reconciliation.discrepant, 3);
    assert.equal(data.task.fence.run_id, after.worker_run_id);
    assert.equal(data.task.binding.handle, after.handle);
    assert.equal(
        data.task.binding.scope.application.revision_id,
        after.application_revision,
    );
    assert.equal(after.run_count, 2);
    if (values.resume) {
        assert.equal(after.worker_run_id, before.worker_run_id);
        assert.equal(after.attempt_count, before.attempt_count);
    }
    assert.deepEqual(external, []);
    assert.deepEqual(errors, []);
    await page.screenshot({
        path: path.join(
            values.out,
            values.resume ? "restarted-result.png" : "executed-result.png",
        ),
        fullPage: true,
    });
    const receipt = {
        status: "PASS",
        host: "real loopback HTTP E2, automated explicit clicks; not authenticated ChatGPT E1",
        url: origin.origin,
        before,
        after,
        rcc: data.rcc_receipt,
        reconciliation: data.task.reconciliation,
        artifact_sha256: createHash("sha256")
            .update(await readFile(path.join(values.out, "execution.json")))
            .digest("hex"),
        external_requests: external,
        browser_errors: errors,
    };
    await writeFile(
        path.join(values.out, "receipt.json"),
        JSON.stringify(receipt, null, 2) + "\n",
    );
    process.stdout.write(
        JSON.stringify({
            status: "PASS",
            run_id: after.worker_run_id,
            evidence: values.out,
        }) + "\n",
    );
} finally {
    await context.close();
    await browser.close();
}
