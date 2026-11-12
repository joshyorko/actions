// eslint-disable-next-line import/no-extraneous-dependencies
import { defineConfig } from "@playwright/test";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const harnessUrl = "http://127.0.0.1:4182";
const harnessRoot = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(harnessRoot, "../../../..");

export default defineConfig({
    testDir: ".",
    testMatch: "browser-harness.spec.ts",
    outputDir: "/tmp/semantic-renderer-playwright-results",
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
            "npm run dev -- --mode canvas --host 127.0.0.1 --port 4182 --strictPort",
        cwd: frontendRoot,
        url: `${harnessUrl}/src/semantic-renderer/browser-harness.html`,
        reuseExistingServer: false,
        timeout: 30_000,
    },
});
