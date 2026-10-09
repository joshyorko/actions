import { defineConfig } from "@playwright/test";

export default defineConfig({
    testDir: "./apps/canvas-view",
    testMatch: "host-harness.spec.ts",
    use: { browserName: "chromium", baseURL: "http://127.0.0.1:4180" },
    webServer: {
        command:
            "npm run dev -- --mode canvas --host 127.0.0.1 --port 4180 --strictPort",
        url: "http://127.0.0.1:4180/host-harness.html",
        reuseExistingServer: !process.env.CI,
        timeout: 30_000,
    },
});
