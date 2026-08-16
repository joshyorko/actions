/* eslint-disable import/no-extraneous-dependencies */
import { expect, test, type Page } from "@playwright/test";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const root = process.cwd();
const output = join(root, "reports/product-evidence");
const sourceSha = execFileSync("git", ["rev-parse", "HEAD"], {
  encoding: "utf8",
}).trim();
const runtimeSha = createHash("sha256")
  .update(readFileSync(join(root, "dist/index.html")))
  .digest("hex");
const records: Array<Record<string, unknown>> = [];
const runtimeOrigin = "http://127.0.0.1:4175";

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
      ? route === "/actions"
        ? "Action Packages"
        : route === "/runs"
          ? "Run History"
          : "Run #"
      : state === "empty"
        ? "No actions available yet"
        : state === "loading"
          ? "Loading actions..."
          : "Unable to load action packages";
  await expect(page.locator("body")).toContainText(expected);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.keyboard.press("Tab");
  const screenshot = `${route.slice(1).replaceAll("/", "-")}-${state}-${theme}-${viewport.width}x${viewport.height}.png`;
  const screenshotPath = join(output, screenshot);
  await page.screenshot({
    path: screenshotPath,
    animations: "disabled",
    caret: "hide",
    fullPage: true,
  });
  records.push({
    schema: 1,
    source_sha: sourceSha,
    artifact_sha256: runtimeSha,
    route,
    viewport,
    theme,
    fixture: "runtime-product-evidence-v1",
    state,
    claim: `Runtime ${route} rendered fixture-backed ${state} data`,
    screenshot,
    screenshot_sha256: createHash("sha256")
      .update(readFileSync(screenshotPath))
      .digest("hex"),
    browser: "chromium",
    os: process.platform,
    node: process.version,
    font_stack: "system-ui, sans-serif",
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
      !message.text().includes("status of 500")
    ) {
      throw new Error(`Unexpected browser console error: ${message.text()}`);
    }
  });
  page.on("requestfailed", (request) => {
    throw new Error(`Unexpected failed request: ${request.url()}`);
  });
  page.on("request", (request) => {
    const requestUrl = new URL(request.url());
    if (requestUrl.hostname !== "127.0.0.1" || requestUrl.port !== "4175") {
      throw new Error(
        `Unexpected external request: ${request.method()} ${request.url()}`,
      );
    }
  });
  page.on("response", (response) => {
    if (response.status() === 404) {
      throw new Error(`Unexpected local 404: ${response.url()}`);
    }
  });
  await context.addCookies([
    { name: "product-evidence", value: "ready", url: runtimeOrigin },
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
      url: runtimeOrigin,
    },
  ]);
  await capture(page, "/actions", "loading", "dark", {
    width: 1440,
    height: 900,
  });
  page.removeAllListeners("requestfailed");
  await page.close();
});

test("rejects drifted Runtime and legacy client requests", async ({
  request,
}) => {
  const actionPackages = await (
    await request.get("/api/actionPackages")
  ).json();
  expect(actionPackages).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        id: expect.any(String),
        name: expect.any(String),
        version: expect.any(String),
        actions: expect.arrayContaining([
          expect.objectContaining({
            id: expect.any(String),
            name: expect.any(String),
          }),
        ]),
      }),
    ]),
  );
  const runtimeRuns = await (await request.get("/api/runs")).json();
  expect(runtimeRuns).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        id: expect.any(String),
        status: expect.any(Number),
        run_type: expect.any(String),
      }),
    ]),
  );
  const artifacts = await (
    await request.get("/api/runs/run-passed/artifacts")
  ).json();
  expect(artifacts).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        name: expect.any(String),
        size_in_bytes: expect.any(Number),
      }),
    ]),
  );
  const artifactText = await (
    await request.get(
      "/api/runs/run-failed/artifacts/text-content?artifact_names=__action_server_output.txt",
    )
  ).json();
  expect(artifactText).toEqual({
    "__action_server_output.txt": expect.any(String),
  });
  for (const response of [
    await request.get("/api/runs?unexpected=1"),
    await request.post("/api/actionPackages", { data: {} }),
    await request.get("/api/runs/run-passed/artifacts/text-content"),
    await request.get("/api/runs/run-passed/artifacts/result.json?download=1"),
  ]) {
    expect(response.status()).toBe(404);
    expect((await response.json()).detail).toContain(
      "Unsupported fixture request",
    );
  }
});

test.afterAll(() => {
  records.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  if (records.length !== 7) return;
  for (const record of records) {
    const screenshot = String(record.screenshot);
    if (
      screenshot !== relative(output, resolve(output, screenshot)) ||
      screenshot.includes("..")
    )
      throw new Error(
        `Manifest screenshot path is not a relative child: ${screenshot}`,
      );
    const screenshotPath = join(output, screenshot);
    if (!existsSync(screenshotPath))
      throw new Error(`Missing screenshot: ${screenshot}`);
    const hash = createHash("sha256")
      .update(readFileSync(screenshotPath))
      .digest("hex");
    if (hash !== record.screenshot_sha256)
      throw new Error(`Screenshot hash mismatch: ${screenshot}`);
    for (const key of [
      "source_sha",
      "artifact_sha256",
      "route",
      "viewport",
      "theme",
      "state",
      "fixture",
      "claim",
      "browser",
      "os",
      "node",
      "font_stack",
    ])
      if (!(key in record))
        throw new Error(`Incomplete manifest record: ${key}`);
  }
  mkdirSync(output, { recursive: true });
  writeFileSync(
    join(output, `${sourceSha}.json`),
    `${JSON.stringify({ schema: 1, source_sha: sourceSha, artifact_sha256: runtimeSha, fixture: "runtime-product-evidence-v1", records }, null, 2)}\n`,
  );
});

test("captures loaded desktop and mobile product routes", async ({ page }) => {
  await capture(page, "/actions", "loaded", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/runs", "loaded", "light", { width: 1440, height: 900 });
  await capture(page, "/logs/run-failed", "loaded", "dark", {
    width: 390,
    height: 844,
  });
  await capture(page, "/artifacts/run-passed", "loaded", "light", {
    width: 390,
    height: 844,
  });
  const artifactLink = page.getByRole("link", { name: "Download" }).first();
  await expect(artifactLink).toHaveAttribute(
    "href",
    "/api/runs/run-passed/artifacts/result.json",
  );
  await artifactLink.click({ noWaitAfter: true });
});

test("captures empty and API error product states", async ({
  context,
  page,
}) => {
  await context.clearCookies();
  await context.addCookies([
    { name: "product-evidence", value: "empty", url: runtimeOrigin },
  ]);
  await capture(page, "/actions", "empty", "light", {
    width: 1440,
    height: 900,
  });
  await context.clearCookies();
  await context.addCookies([
    { name: "product-evidence", value: "error", url: runtimeOrigin },
  ]);
  await capture(page, "/actions", "error", "dark", {
    width: 1440,
    height: 900,
  });
});
