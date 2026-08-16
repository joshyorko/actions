/* eslint-disable import/no-extraneous-dependencies */
import { expect, test, type Page } from "@playwright/test";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const output = join(root, "reports/product-evidence");
const sourceSha = execFileSync("git", ["rev-parse", "HEAD"], {
  encoding: "utf8",
}).trim();
const artifactSha = createHash("sha256")
  .update(readFileSync(join(root, "dist/index.html")))
  .digest("hex");
const records: Array<Record<string, unknown>> = [];

const capture = async (
  page: Page,
  route: string,
  state: string,
  theme: "light" | "dark",
  viewport: { width: number; height: number },
) => {
  await page.setViewportSize(viewport);
  await page.addInitScript((value) => {
    localStorage.setItem("view-settings", JSON.stringify({ theme: value }));
  }, theme);
  await page.goto(route, { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(new RegExp(`${route.replaceAll("/", "\\/")}$`));
  const expected =
    state === "loaded"
      ? route === "/"
        ? "Ready for the next run"
        : route === "/actions"
          ? "Action Packages"
          : route.startsWith("/actions/")
            ? "Run action"
            : route === "/runs"
              ? "Run History"
              : "Run #"
      : state === "empty"
        ? "No actions available yet"
        : state === "loading"
          ? "Loading actions..."
          : state === "degraded"
            ? "Artifacts"
            : "Unable to load action packages";
  await expect(page.locator("body")).toContainText(expected);
  if (viewport.width === 390) {
    const menu = page.getByRole("button", { name: "Open Runtime menu" });
    await menu.click();
    await expect(page.getByTestId("mobile-menu-backdrop")).toHaveClass(
      /visible/,
    );
    await expect(
      page.getByRole("button", { name: "Close Runtime menu" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Close Runtime menu" }).click();
    await expect(menu).toBeFocused();
  }
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.keyboard.press("Tab");
  const screenshot = `reports/product-evidence/${route.slice(1).replaceAll("/", "-")}-${state}-${theme}-${viewport.width}x${viewport.height}.png`;
  await page.screenshot({
    path: join(root, screenshot),
    animations: "disabled",
    caret: "hide",
    fullPage: true,
  });
  records.push({
    schema: 1,
    source_sha: sourceSha,
    artifact_sha256: artifactSha,
    route,
    viewport,
    theme,
    fixture: "runtime-product-evidence-v1",
    state,
    claim: `Runtime ${route} rendered fixture-backed ${state} data`,
    screenshot,
  });
};

test.beforeEach(async ({ context, page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  page.on("pageerror", (error) => {
    throw error;
  });
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      !message.text().includes("status of 500") &&
      !message.text().includes("status of 503")
    ) {
      throw new Error(`Unexpected browser console error: ${message.text()}`);
    }
  });
  page.on("requestfailed", (request) => {
    throw new Error(`Unexpected failed request: ${request.url()}`);
  });
  await context.addCookies([
    { name: "product-evidence", value: "ready", url: "http://127.0.0.1:4174" },
  ]);
  await page.addInitScript(() => {
    class StableWebSocket {
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor() {
        queueMicrotask(() => this.onopen?.());
      }
      send() {}
      close() {
        this.onclose?.();
      }
    }
    Object.defineProperty(window, "WebSocket", { value: StableWebSocket });
  });
});

test("captures the loading product state", async ({ context, page }) => {
  await context.clearCookies();
  await context.addCookies([
    {
      name: "product-evidence",
      value: "loading",
      url: "http://127.0.0.1:4174",
    },
  ]);
  await capture(page, "/actions", "loading", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions", "loading", "light", {
    width: 390,
    height: 844,
  });
});

test.afterAll(() => {
  records.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  mkdirSync(output, { recursive: true });
  writeFileSync(
    join(output, `${sourceSha}.json`),
    `${JSON.stringify({ schema: 1, source_sha: sourceSha, artifact_sha256: artifactSha, fixture: "runtime-product-evidence-v1", records }, null, 2)}\n`,
  );
});

test("captures loaded desktop and mobile product routes", async ({ page }) => {
  await capture(page, "/", "loaded", "light", { width: 1440, height: 900 });
  await capture(page, "/", "loaded", "dark", { width: 1440, height: 900 });
  await capture(page, "/", "loaded", "light", { width: 390, height: 844 });
  await capture(page, "/actions", "loaded", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions", "loaded", "light", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions", "loaded", "light", {
    width: 390,
    height: 844,
  });
  await capture(page, "/actions/action-sum", "loaded", "light", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions/action-sum", "loaded", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions/action-sum", "loaded", "light", {
    width: 390,
    height: 844,
  });
  await capture(page, "/runs", "loaded", "light", { width: 1440, height: 900 });
  await capture(page, "/runs", "loaded", "dark", { width: 390, height: 844 });
  await capture(page, "/runs/run-failed", "loaded", "light", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/runs/run-failed", "loaded", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/runs/run-failed", "loaded", "light", {
    width: 390,
    height: 844,
  });
  await capture(page, "/logs/run-failed", "loaded", "dark", {
    width: 390,
    height: 844,
  });
  await capture(page, "/artifacts/run-passed", "loaded", "light", {
    width: 390,
    height: 844,
  });
});

test("captures empty and API error product states", async ({
  context,
  page,
}) => {
  await context.clearCookies();
  await context.addCookies([
    { name: "product-evidence", value: "empty", url: "http://127.0.0.1:4174" },
  ]);
  await capture(page, "/actions", "empty", "light", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions", "empty", "light", {
    width: 390,
    height: 844,
  });
  await context.clearCookies();
  await context.addCookies([
    { name: "product-evidence", value: "error", url: "http://127.0.0.1:4174" },
  ]);
  await capture(page, "/actions", "error", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions", "error", "light", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions", "error", "light", {
    width: 390,
    height: 844,
  });
  await context.clearCookies();
  await context.addCookies([
    {
      name: "product-evidence",
      value: "unavailable",
      url: "http://127.0.0.1:4174",
    },
  ]);
  await capture(page, "/actions", "unavailable", "light", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions", "unavailable", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions", "unavailable", "light", {
    width: 390,
    height: 844,
  });
  await context.clearCookies();
  await context.addCookies([
    {
      name: "product-evidence",
      value: "degraded",
      url: "http://127.0.0.1:4174",
    },
  ]);
  await capture(page, "/artifacts/run-passed", "degraded", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/artifacts/run-passed", "degraded", "light", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/artifacts/run-passed", "degraded", "light", {
    width: 390,
    height: 844,
  });
});
