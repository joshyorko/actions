/* eslint-disable import/no-extraneous-dependencies */
import { expect, test, type Page } from "@playwright/test";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { request as httpRequest } from "node:http";
import { connect } from "node:net";
import { join, relative, resolve } from "node:path";

const root = process.cwd();
const output = join(
  root,
  process.env.PRODUCT_EVIDENCE_OUTPUT_DIR || "reports/product-evidence",
);
const sourceSha = execFileSync("git", ["rev-parse", "HEAD"], {
  encoding: "utf8",
}).trim();
const runtimeSha = createHash("sha256")
  .update(readFileSync(join(root, "dist/index.html")))
  .digest("hex");
const canvasArtifactSha = createHash("sha256")
  .update(readFileSync(join(root, "dist-canvas/artifact-manifest.json")))
  .update("\n")
  .update(readFileSync(join(root, "dist-canvas/sbom.json")))
  .digest("hex");
const records: Array<Record<string, unknown>> = [];
const runtimeOrigin = "http://127.0.0.1:4175";
type Body = string | Buffer | readonly (string | Buffer)[];

const boundedHttpRequest = (
  path: string,
  headers: Record<string, string>,
  body: Body = "",
  chunked = false,
) =>
  new Promise<{ status: number; body: string }>((resolveProbe, reject) => {
    let settled = false;
    const finish = (callback: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      callback();
    };
    const client = httpRequest(
      {
        host: "127.0.0.1",
        port: 4175,
        path,
        method: "GET",
        headers,
      },
      (response) => {
        const chunks: Buffer[] = [];
        response.on("data", (chunk: Buffer) => chunks.push(chunk));
        response.on("end", () =>
          finish(() =>
            resolveProbe({
              status: response.statusCode || 0,
              body: Buffer.concat(chunks).toString(),
            }),
          ),
        );
      },
    );
    const timer = setTimeout(() => {
      client.destroy();
      finish(() => reject(new Error(`HTTP body probe timed out: ${path}`)));
    }, 900);
    client.once("error", (error) => finish(() => reject(error)));
    if (chunked) {
      for (const chunk of Array.isArray(body) ? body : [body])
        client.write(chunk);
      client.end();
    } else {
      client.end(body as string | Buffer);
    }
  });

const boundedRawRequest = (raw: string) =>
  new Promise<string>((resolveProbe, reject) => {
    let settled = false;
    let response = "";
    const socket = connect(4175, "127.0.0.1");
    const finish = (callback: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      socket.destroy();
      callback();
    };
    const timer = setTimeout(() => {
      finish(() => reject(new Error("Raw body probe timed out")));
    }, 900);
    socket.once("connect", () => socket.end(raw));
    socket.on("data", (chunk) => {
      response += chunk.toString();
    });
    socket.once("close", () => finish(() => resolveProbe(response)));
    socket.once("error", (error) => finish(() => reject(error)));
  });

const responseDetail = (body: string) => JSON.parse(body).detail as string;
const rawStatus = (response: string) =>
  Number(response.match(/^HTTP\/1\.1 (\d+)/)?.[1] || 0);

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
    canvas_artifact_sha256: canvasArtifactSha,
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
    await request.get("/api/runs/run-unknown/artifacts"),
    await request.get("/api/runs/run-unknown"),
    await request.get("/api/analytics/unknown-resource"),
  ]) {
    expect(response.status()).toBe(404);
    expect((await response.json()).detail).toContain(
      "Unsupported fixture request",
    );
  }
  for (const response of [
    await request.get("/api/runs?unexpected=1"),
    await request.post("/api/actionPackages"),
    await request.get("/api/runs/run-passed/artifacts/text-content"),
    await request.get("/api/runs/run-passed/artifacts/result.json?download=1"),
  ]) {
    expect(response.status()).toBe(404);
    expect((await response.json()).detail).toContain(
      "Unsupported fixture request",
    );
  }
  expect(
    await boundedHttpRequest("/config", { "Content-Length": "0" }),
  ).toMatchObject({ status: 200 });
  for (const probe of [
    await boundedHttpRequest("/config", { "Content-Length": "1" }, "x"),
    await boundedHttpRequest("/api/runs", { "Content-Length": "1" }, "x"),
    await boundedHttpRequest(
      "/config",
      { "Transfer-Encoding": "chunked" },
      "x",
      true,
    ),
    await boundedHttpRequest(
      "/not-a-real-static-route.js",
      { "Content-Length": "1" },
      "x",
    ),
  ]) {
    expect(probe.status).toBe(400);
    expect(responseDetail(probe.body)).toContain("empty request body");
  }
  const oversized = await boundedHttpRequest(
    "/config",
    { "Content-Length": String(65 * 1024) },
    Buffer.alloc(65 * 1024, 97),
  );
  expect(oversized.status).toBe(413);
  expect(responseDetail(oversized.body)).toContain("64 KiB");
  const streamedOverflow = await boundedHttpRequest(
    "/config",
    { "Transfer-Encoding": "chunked" },
    [Buffer.alloc(64 * 1024, 98), "x"],
    true,
  );
  expect(streamedOverflow.status).toBe(413);
  expect(responseDetail(streamedOverflow.body)).toContain("64 KiB");
  for (const raw of [
    "GET /config HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: nope\r\nConnection: close\r\n\r\n",
    "GET /config HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: -1\r\nConnection: close\r\n\r\n",
    "GET /config HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 1\r\nContent-Length: 2\r\nConnection: close\r\n\r\nx",
  ]) {
    const response = await boundedRawRequest(raw);
    expect(rawStatus(response)).toBe(400);
    expect(response).toContain("Content-Length");
  }
  const aborted = await boundedRawRequest(
    "GET /config HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 2\r\nConnection: close\r\n\r\nx",
  );
  expect(rawStatus(aborted)).toBe(400);
  expect(aborted).toContain("request body was aborted");
});

test.afterAll(() => {
  records.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  if (records.length !== 7)
    throw new Error(
      `Product-evidence manifest requires exactly seven records; got ${records.length}`,
    );
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
      "canvas_artifact_sha256",
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
    `${JSON.stringify({ schema: 1, source_sha: sourceSha, artifact_sha256: runtimeSha, canvas_artifact_sha256: canvasArtifactSha, fixture: "runtime-product-evidence-v1", records }, null, 2)}\n`,
  );
});

test("captures loaded desktop and mobile product routes", async ({
  page,
  request,
}) => {
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
  const [download, response] = await Promise.all([
    page.waitForEvent("download"),
    request.get("/api/runs/run-passed/artifacts/result.json"),
    artifactLink.click({ noWaitAfter: true }),
  ]);
  expect(download.suggestedFilename()).toBe("result.json");
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toBe("application/octet-stream");
  expect((await response.body()).toString()).toBe('{"result":5}\n');
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
