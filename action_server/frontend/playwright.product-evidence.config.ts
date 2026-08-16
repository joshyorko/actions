/* eslint-disable import/no-extraneous-dependencies */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./__tests__/visual",
  testMatch: "product-evidence.spec.ts",
  timeout: 60_000,
  fullyParallel: false,
  expect: { timeout: 15_000 },
  use: {
    baseURL: "http://127.0.0.1:4175",
    headless: true,
    locale: "en-US",
    timezoneId: "UTC",
    colorScheme: "dark",
    deviceScaleFactor: 1,
    screenshot: "off",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command:
      "PRODUCT_EVIDENCE_PORT=4175 node scripts/product-evidence-server.mjs",
    url: "http://127.0.0.1:4175/config",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
