import { defineConfig } from "@playwright/test";

const harnessPort = process.env.CANVAS_HARNESS_PORT ?? "4180";
const harnessUrl = `http://127.0.0.1:${harnessPort}`;
const runtimeAcceptance = Boolean(process.env.CANVAS_RUNTIME_MCP_URL);

export default defineConfig({
    testDir: "./apps/canvas-view",
    testMatch: "host-harness.spec.ts",
    use: {
        browserName: "chromium",
        baseURL: harnessUrl,
        launchOptions: process.env.CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
            ? {
                  executablePath:
                      process.env.CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
              }
            : undefined,
    },
    webServer: {
        command:
            `npm run dev -- --mode canvas --host 127.0.0.1 --port ${harnessPort} --strictPort`,
        url: `${harnessUrl}/host-harness.html`,
        reuseExistingServer: runtimeAcceptance ? false : !process.env.CI,
        timeout: 30_000,
    },
});
