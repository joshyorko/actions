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
