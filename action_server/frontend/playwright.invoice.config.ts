import { defineConfig } from "@playwright/test";

export default defineConfig({
    testDir: "./apps/canvas-view",
    testMatch: "invoice-runtime.spec.ts",
    fullyParallel: false,
    workers: 1,
    timeout: 45_000,
    outputDir: process.env.CANVAS_TEMPLATE_TEST_OUTPUT,
    use: { browserName: "chromium" },
});
