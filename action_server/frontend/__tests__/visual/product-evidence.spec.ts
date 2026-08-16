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
let expectedHttpStatuses = new Set<number>();

const capture = async (
  page: Page,
  route: string,
  state: string,
  theme: "light" | "dark",
  viewport: { width: number; height: number },
  options: {
    expected?: string;
    claim?: string;
    state_details?: string;
    openMobileMenu?: boolean;
    openRunDialog?: boolean;
  } = {},
) => {
  expectedHttpStatuses =
    state === "error"
      ? new Set([500])
      : state === "unavailable"
        ? new Set([503])
        : new Set();
  await page.setViewportSize(viewport);
  await page.addInitScript((value) => {
    localStorage.setItem("view-settings", JSON.stringify({ theme: value }));
  }, theme);
  await page.goto(route, { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(new RegExp(`${route.replaceAll("/", "\\/")}$`));
  const expected =
    options.expected ??
    (state === "loaded"
      ? route === "/actions"
        ? "Action Packages"
        : route === "/runs"
          ? "Run History"
          : route === "/overview"
            ? "Execution console"
            : "Run #"
      : state === "empty"
        ? "No actions available yet"
        : state === "loading"
          ? "Loading actions..."
          : "Unable to load action packages");
  await expect(page.locator("body")).toContainText(expected);
  if (options.openRunDialog) {
    await page.getByRole("button", { name: "Run action" }).first().click();
    await expect(page.getByRole("dialog")).toContainText("Run");
  }
  if (options.openMobileMenu) {
    await page.getByRole("button", { name: "Open Runtime navigation" }).click();
    await expect(
      page.getByRole("button", { name: "Close Runtime navigation" }),
    ).toBeVisible();
    expect(
      await page.evaluate(() => {
        const scrim = document.querySelector<HTMLElement>(
          ".runtime-mobile-scrim",
        );
        const sidebar = document.querySelector<HTMLElement>(".sidebar.open");
        const rect = scrim?.getBoundingClientRect();
        return Boolean(
          scrim &&
          sidebar &&
          rect &&
          rect.width >= window.innerWidth &&
          rect.height >= window.innerHeight &&
          document.documentElement.scrollWidth <= window.innerWidth,
        );
      }),
    ).toBe(true);
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
    fullPage: false,
  });
  const pngSha256 = createHash("sha256")
    .update(readFileSync(join(root, screenshot)))
    .digest("hex");
  const provenance = await page.evaluate(() => ({
    user_agent: navigator.userAgent,
    font_family: getComputedStyle(document.body).fontFamily,
    document_fonts: document.fonts?.status ?? "unavailable",
  }));
  records.push({
    schema: 2,
    source_sha: sourceSha,
    artifact_sha256: artifactSha,
    route,
    viewport,
    theme,
    fixture: "runtime-product-evidence-v1",
    state,
    state_details: options.state_details ?? state,
    claim:
      options.claim ?? `Runtime ${route} rendered fixture-backed ${state} data`,
    screenshot,
    png_sha256: pngSha256,
    browser: "Playwright Chromium",
    os: process.platform,
    node: process.version,
    provenance,
  });
};

test.beforeEach(async ({ context, page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  page.on("pageerror", (error) => {
    throw error;
  });
  page.on("console", (message) => {
    const status = message.text().match(/status of (\d{3})/)?.[1];
    if (
      message.type() === "error" &&
      !(status && expectedHttpStatuses.has(Number(status)))
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
});

test.afterAll(() => {
  records.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  mkdirSync(output, { recursive: true });
  writeFileSync(
    join(output, `${sourceSha}.json`),
    `${JSON.stringify({ schema: 2, source_sha: sourceSha, artifact_sha256: artifactSha, fixture: "runtime-product-evidence-v1", records }, null, 2)}\n`,
  );
});

test("captures loaded desktop and mobile product routes", async ({ page }) => {
  await capture(page, "/overview", "loaded", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(page, "/actions", "loaded", "dark", {
    width: 1440,
    height: 900,
  });
  await capture(
    page,
    "/actions",
    "action-detail-execute",
    "light",
    { width: 1440, height: 900 },
    {
      expected: "Action Packages",
      claim:
        "Runtime action detail and execute form are connected to the fixture-backed action catalog",
      openRunDialog: true,
    },
  );
  await capture(page, "/runs", "loaded", "light", { width: 1440, height: 900 });
  await capture(page, "/logs/run-failed", "loaded", "dark", {
    width: 390,
    height: 844,
  });
  await capture(page, "/artifacts/run-passed", "loaded", "light", {
    width: 390,
    height: 844,
  });
  await capture(
    page,
    "/actions",
    "loaded-menu-open",
    "dark",
    {
      width: 390,
      height: 844,
    },
    {
      expected: "Action Packages",
      state_details: "loaded with mobile navigation open",
      openMobileMenu: true,
    },
  );
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
  await context.clearCookies();
  await context.addCookies([
    { name: "product-evidence", value: "error", url: "http://127.0.0.1:4174" },
  ]);
  await capture(page, "/actions", "error", "dark", {
    width: 1440,
    height: 900,
  });
  await context.clearCookies();
  await context.addCookies([
    {
      name: "product-evidence",
      value: "unavailable",
      url: "http://127.0.0.1:4174",
    },
  ]);
  await capture(
    page,
    "/actions",
    "unavailable",
    "light",
    {
      width: 390,
      height: 844,
    },
    { expected: "Unable to load action packages:" },
  );
});
