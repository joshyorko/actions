import { defineConfig } from "@playwright/test";

export default defineConfig({
    testDir: "./apps/canvas-view",
    testMatch: "canvas-template-runtime.spec.ts",
    fullyParallel: false,
    workers: 1,
    outputDir:
        process.env.CANVAS_TEMPLATE_TEST_OUTPUT ??
        "/tmp/canvas-template-playwright",
    use: {
        browserName: "chromium",
        launchOptions: process.env.CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
            ? {
                  executablePath:
                      process.env.CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
              }
            : undefined,
    },
});
