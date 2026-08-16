import { createHash } from "node:crypto";
import { createReadStream, existsSync, readFileSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const dist = join(root, "dist");
const port = Number(process.env.PRODUCT_EVIDENCE_PORT || 4174);
const schema = JSON.stringify({
  type: "object",
  properties: { message: { type: "string" } },
});
const actions = [
  {
    id: "pkg-calculator",
    name: "Evidence Calculator Package",
    version: "1.0.0",
    actions: [
      {
        id: "action-sum",
        action_package_id: "pkg-calculator",
        name: "sum",
        docs: "Adds two values for a real input-schema example.",
        enabled: true,
        file: "calculator.py",
        lineno: 12,
        input_schema: schema,
        output_schema: schema,
      },
      {
        id: "action-long",
        action_package_id: "pkg-calculator",
        name: "A deliberately long action name for responsive evidence review",
        docs: "Long names exercise the actual Actions table.",
        enabled: true,
        file: "calculator.py",
        lineno: 20,
        input_schema: schema,
        output_schema: schema,
      },
    ],
  },
  {
    id: "pkg-greeter",
    name: "Evidence Greeter Package",
    version: "2.0.0",
    actions: [
      {
        id: "action-greet",
        action_package_id: "pkg-greeter",
        name: "greet",
        docs: "Greets a named user.",
        enabled: true,
        file: "greeter.py",
        lineno: 8,
        input_schema: schema,
        output_schema: schema,
      },
      {
        id: "action-disabled",
        action_package_id: "pkg-greeter",
        name: "disabled",
        docs: "Disabled action is not shown as runnable.",
        enabled: false,
        file: "greeter.py",
        lineno: 18,
        input_schema: schema,
        output_schema: schema,
      },
    ],
  },
];
const runs = [
  {
    id: "run-passed",
    status: 2,
    action_id: "action-sum",
    start_time: "2026-01-02T03:04:05.000Z",
    run_time: 1.25,
    inputs: '{"a":2,"b":3}',
    result: '{"sum":5}',
    numbered_id: 104,
    run_type: "action",
    action_name: "sum",
  },
  {
    id: "run-failed",
    status: 3,
    action_id: "action-greet",
    start_time: "2026-01-03T03:04:05.000Z",
    run_time: 2.5,
    inputs: '{"name":"Failure review"}',
    result: null,
    error_message: "Fixture failure: greeting service rejected the input.",
    numbered_id: 103,
    run_type: "action",
    action_name: "greet",
  },
  {
    id: "run-running",
    status: 1,
    action_id: "action-long",
    start_time: "2026-01-04T03:04:05.000Z",
    run_time: null,
    inputs: '{"message":"still running"}',
    result: null,
    numbered_id: 102,
    run_type: "action",
    action_name:
      "A deliberately long action name for responsive evidence review",
  },
  {
    id: "run-cancelled",
    status: 4,
    action_id: "action-sum",
    start_time: "2026-01-05T03:04:05.000Z",
    run_time: 0.75,
    inputs: '{"a":8,"b":13}',
    result: null,
    numbered_id: 101,
    run_type: "action",
    action_name: "sum",
  },
  {
    id: "run-robot",
    status: 2,
    action_id: "action-greet",
    start_time: "2026-01-06T03:04:05.000Z",
    run_time: 3.75,
    inputs: "{}",
    result: null,
    numbered_id: 100,
    run_type: "robot",
    robot_package_path: "fixture/robot",
    robot_task_name: "Evidence robot task",
  },
];
const artifactList = [
  { name: "result.json", size_in_bytes: 128 },
  { name: "nested/trace.txt", size_in_bytes: 512 },
];
const artifactText = {
  "__action_server_output.txt":
    "Fixture run output\npassed: true\ntrace: deterministic-v1\n",
};
const send = (res, status, value, type = "application/json") => {
  res.writeHead(status, { "Content-Type": type, "Cache-Control": "no-store" });
  res.end(type === "application/json" ? JSON.stringify(value) : value);
};
const mode = (req) =>
  (req.headers.cookie || "").match(/product-evidence=([^;]+)/)?.[1] || "ready";
const delayed = (res, value) => setTimeout(() => send(res, 200, value), 10_000);
const server = createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const state = mode(req);
  if (url.pathname === "/config")
    return send(res, 200, {
      expose_url: "",
      auth_enabled: false,
      version: "fixture-v1",
      mtime_uuid: "fixture-v1",
    });
  if (url.pathname === "/api/actionPackages" && state === "loading")
    return delayed(res, actions);
  if (url.pathname === "/api/actionPackages")
    return state === "error" || state === "unavailable"
      ? send(res, state === "unavailable" ? 503 : 500, {
          detail:
            state === "unavailable"
              ? "Fixture runtime unavailable: action packages cannot be reached."
              : "Fixture API error: action packages unavailable.",
        })
      : send(res, 200, state === "empty" ? [] : actions);
  if (
    (url.pathname === "/api/runs" || url.pathname.startsWith("/api/runs?")) &&
    state === "loading"
  )
    return delayed(res, runs);
  if (url.pathname === "/api/runs" || url.pathname.startsWith("/api/runs?"))
    return state === "error" || state === "unavailable"
      ? send(res, state === "unavailable" ? 503 : 500, {
          detail:
            state === "unavailable"
              ? "Fixture runtime unavailable: runs cannot be reached."
              : "Fixture API error: runs unavailable.",
        })
      : send(res, 200, state === "empty" ? [] : runs);
  if (
    url.pathname.startsWith("/api/runs/") &&
    url.pathname.endsWith("/artifacts")
  )
    return send(res, 200, state === "empty" ? [] : artifactList);
  if (
    url.pathname.startsWith("/api/runs/") &&
    url.pathname.endsWith("/artifacts/text-content")
  )
    return send(res, 200, state === "empty" ? {} : artifactText);
  if (
    url.pathname.startsWith("/api/runs/") &&
    url.pathname.endsWith("/log.html")
  )
    return send(
      res,
      200,
      "<!doctype html><title>Fixture log</title><pre>deterministic-v1</pre>",
      "text/html",
    );
  if (url.pathname.startsWith("/api/analytics/"))
    return send(
      res,
      200,
      url.pathname.endsWith("summary")
        ? {
            total_runs: 5,
            success_rate: 0.4,
            avg_duration_ms: 2062,
            runs_today: 5,
          }
        : [],
    );
  if (url.pathname === "/api/ws")
    return send(res, 426, { detail: "WebSocket upgrade required" });
  if (url.pathname.startsWith("/api/runs/"))
    return send(
      res,
      200,
      runs.find((run) => url.pathname.endsWith(run.id)) || runs[0],
    );
  const requested = normalize(
    join(dist, url.pathname === "/" ? "index.html" : url.pathname),
  );
  const file =
    requested.startsWith(dist) &&
    existsSync(requested) &&
    statSync(requested).isFile()
      ? requested
      : join(dist, "index.html");
  if (!existsSync(file))
    return send(
      res,
      500,
      "Runtime dist is missing; run npm run build:runtime first.",
      "text/plain",
    );
  res.writeHead(200, {
    "Content-Type": extname(file) === ".html" ? "text/html" : "text/javascript",
  });
  createReadStream(file).pipe(res);
});
server.listen(port, "127.0.0.1");
process.on("SIGTERM", () => {
  server.closeAllConnections?.();
  server.close(() => process.exit(0));
});
process.stdout.write(
  `fixture=runtime-product-evidence-v1 port=${port} dist_sha256=${createHash(
    "sha256",
  )
    .update(readFileSync(join(dist, "index.html")))
    .digest("hex")}\n`,
);
