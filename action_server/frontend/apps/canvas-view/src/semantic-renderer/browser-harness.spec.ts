// eslint-disable-next-line import/no-extraneous-dependencies
import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const harnessRoot = path.dirname(fileURLToPath(import.meta.url));

test("renders and dispatches a synthetic component form in a browser", async ({
    page,
}) => {
    await page.goto("/src/semantic-renderer/browser-harness.html");

    await expect(
        page.getByText(
            "Component harness · synthetic data · not Runtime-hosted or ChatGPT E1",
        ),
    ).toBeVisible();
    await page.getByRole("textbox", { name: "Search term" }).fill("example");
    await page
        .getByRole("button", { name: "Search synthetic records" })
        .click();

    await expect(
        page.getByRole("cell", {
            name: "Synthetic result for “example”",
        }),
    ).toBeVisible();

    const screenshotPath = path.join(
        harnessRoot,
        "artifacts",
        "component-harness.png",
    );
    await mkdir(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({
        path: screenshotPath,
        fullPage: true,
    });
});
