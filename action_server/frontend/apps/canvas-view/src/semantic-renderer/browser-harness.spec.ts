// eslint-disable-next-line import/no-extraneous-dependencies
import { expect, test } from "@playwright/test";

test("renders and dispatches a synthetic component form in a browser", async ({
    page,
}, testInfo) => {
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

    await page.screenshot({
        path: testInfo.outputPath("component-harness.png"),
        fullPage: true,
    });
});

for (const width of [320, 1280]) {
    test(`keeps wide results within the page at ${width}px`, async ({
        page,
    }, testInfo) => {
        await page.setViewportSize({ width, height: 900 });
        await page.goto("/src/semantic-renderer/browser-harness.html");
        const region = page.getByRole("region", {
            name: "Synthetic operations records",
        });
        await expect(region).toBeVisible();
        expect(
            await region
                .getByRole("columnheader")
                .first()
                .evaluate((element) => element.getBoundingClientRect().width),
        ).toBeGreaterThanOrEqual(128);
        expect(
            await region
                .getByRole("columnheader")
                .first()
                .evaluate((element) => element.getBoundingClientRect().height),
        ).toBeLessThanOrEqual(72);
        expect(
            await page.evaluate(() => document.documentElement.scrollWidth),
        ).toBe(width);
        await page.getByRole("textbox", { name: "Search term" }).focus();
        await page.keyboard.press("Tab");
        await expect(
            page.getByRole("button", { name: "Search synthetic records" }),
        ).toBeFocused();
        await page.keyboard.press("Tab");
        await expect(region).toBeFocused();
        if (width === 320) {
            expect(
                await region.evaluate(
                    (element) => element.scrollWidth > element.clientWidth,
                ),
            ).toBe(true);
            await page.keyboard.press("ArrowRight");
            await expect
                .poll(() => region.evaluate((element) => element.scrollLeft))
                .toBeGreaterThan(0);
        }
        await page.screenshot({
            path: testInfo.outputPath(`wide-results-${width}.png`),
            fullPage: true,
        });
    });
}

test("announces pending work and a response without dispatch on mount", async ({
    page,
}, testInfo) => {
    await page.goto(
        "/src/semantic-renderer/browser-harness.html?scenario=loading",
    );
    const form = page.getByRole("region", {
        name: "Search synthetic records",
        exact: true,
    });
    await expect(form.getByRole("button")).toHaveText(
        "Search synthetic records",
    );
    await expect(page.getByTestId("synthetic-dispatch-count")).toHaveText("0");
    await form.getByRole("textbox").fill("pending");
    await form.getByRole("button").click();
    await expect(page.getByTestId("synthetic-dispatch-count")).toHaveText("1");
    await page.screenshot({
        path: testInfo.outputPath("form-loading.png"),
        fullPage: true,
    });
    await expect(form.locator("form")).toHaveAttribute("aria-busy", "true");
    await expect(form.getByRole("status")).toHaveText(
        "Search synthetic records: working…",
    );
    await expect(form.getByRole("textbox")).toBeDisabled();
    await expect(form.getByRole("button")).toBeDisabled();
    await page
        .getByRole("button", { name: "Complete synthetic request" })
        .click();
    await expect(form.locator("form")).toHaveAttribute("aria-busy", "false");
    await expect(form.getByRole("status")).toHaveText(
        "Search synthetic records: response received.",
    );
    await expect(form.getByRole("cell")).toContainText("pending");
});

for (const scenario of ["error", "empty"]) {
    test(`shows truthful ${scenario} results and permits retry`, async ({
        page,
    }, testInfo) => {
        await page.goto(
            `/src/semantic-renderer/browser-harness.html?scenario=${scenario}`,
        );
        const form = page.getByRole("region", {
            name: "Search synthetic records",
            exact: true,
        });
        await form.getByRole("textbox").fill("example");
        await form.getByRole("button").click();
        if (scenario === "error") {
            await expect(form.getByRole("alert")).toHaveText(
                "Unable to complete this action. Try again.",
            );
            await expect(form.getByRole("status")).toHaveText("");
        } else {
            await expect(
                form.getByRole("status", { name: "Synthetic search results" }),
            ).toHaveText("No results to display.");
        }
        await expect(form.getByRole("button")).toBeEnabled();
        await expect(page.getByTestId("synthetic-dispatch-count")).toHaveText(
            "1",
        );
        await form.getByRole("button").click();
        await expect(page.getByTestId("synthetic-dispatch-count")).toHaveText(
            "2",
        );
        await expect(form.getByRole("button")).toBeEnabled();
        await page.screenshot({
            path: testInfo.outputPath(`form-${scenario}.png`),
            fullPage: true,
        });
    });
}
