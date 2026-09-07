/* global Buffer, URL, process, setTimeout, clearTimeout */
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
const knownRunIds = new Set(runs.map((run) => run.id));
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
const delayed = (req, res, value) => {
  const timer = setTimeout(() => send(res, 200, value), 10_000);
  const release = () => clearTimeout(timer);
  req.once("aborted", release);
  res.once("close", release);
  return timer;
};
const reject = (res, status, message) => send(res, status, { detail: message });
const MAX_REQUEST_BODY_BYTES = 64 * 1024;
const bodyAdmissionError = (status, detail) => ({ status, detail });
const contentLengthValues = (req) =>
  req.rawHeaders.reduce((values, header, index) => {
    if (header.toLowerCase() === "content-length")
      values.push(req.rawHeaders[index + 1]);
    return values;
  }, []);
const admitEmptyRequestBody = (req) => {
  const lengths = contentLengthValues(req);
  if (lengths.length > 1 && new Set(lengths).size > 1)
    return Promise.resolve(
      bodyAdmissionError(400, "Contradictory Content-Length headers"),
    );
  const rawLength = lengths[0] ?? req.headers["content-length"];
  if (rawLength !== undefined && !/^\d+$/.test(rawLength))
    return Promise.resolve(
      bodyAdmissionError(400, "Malformed Content-Length header"),
    );
  const expected = rawLength === undefined ? undefined : Number(rawLength);
  if (expected !== undefined && !Number.isSafeInteger(expected))
    return Promise.resolve(
      bodyAdmissionError(400, "Malformed Content-Length header"),
    );
  if (expected !== undefined && expected > MAX_REQUEST_BODY_BYTES)
    return Promise.resolve(
      bodyAdmissionError(
        413,
        `Request body exceeds ${MAX_REQUEST_BODY_BYTES / 1024} KiB`,
      ),
    );
  return new Promise((resolve) => {
    let received = 0;
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      req.off("data", onData);
      req.off("end", onEnd);
      req.off("aborted", onAborted);
      req.off("error", onError);
      resolve(result);
    };
    const onData = (chunk) => {
      received += chunk.length;
      if (received > MAX_REQUEST_BODY_BYTES)
        finish(
          bodyAdmissionError(
            413,
            `Request body exceeds ${MAX_REQUEST_BODY_BYTES / 1024} KiB`,
          ),
        );
    };
    const onEnd = () =>
      finish(
        expected !== undefined && expected !== received
          ? bodyAdmissionError(
              400,
              "Content-Length does not match request body",
            )
          : received === 0
            ? null
            : bodyAdmissionError(
                400,
                "Only an empty request body is supported",
              ),
      );
    const onAborted = () =>
      finish(bodyAdmissionError(400, "The request body was aborted"));
    const onError = () =>
      finish(bodyAdmissionError(400, "The request body could not be read"));
    req.on("data", onData);
    req.once("end", onEnd);
    req.once("aborted", onAborted);
    req.once("error", onError);
    req.resume();
  });
};
const rejectBody = (req, res, status, message) => {
  if (res.destroyed || res.writableEnded) return;
  const body = JSON.stringify({ detail: message });
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
    Connection: "close",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body, () => req.destroy());
};
const dispatchRequest = (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const state = mode(req);
  if (req.method === "GET" && url.pathname === "/config" && !url.search)
    return send(res, 200, {
      expose_url: "",
      auth_enabled: false,
      version: "fixture-v1",
      mtime_uuid: "fixture-v1",
    });
  if (
    req.method === "GET" &&
    url.pathname === "/api/actionPackages" &&
    !url.search &&
    state === "loading"
  )
    return delayed(req, res, actions);
  if (
    req.method === "GET" &&
    url.pathname === "/api/actionPackages" &&
    !url.search
  )
    return state === "error"
      ? send(res, 500, {
          detail: "Fixture API error: action packages unavailable.",
        })
      : send(res, 200, state === "empty" ? [] : actions);
  if (
    req.method === "GET" &&
    url.pathname === "/api/runs" &&
    [...url.searchParams.keys()].every((key) => key === "run_type") &&
    url.searchParams.getAll("run_type").length <= 1 &&
    state === "loading"
  )
    return delayed(req, res, runs);
  if (
    req.method === "GET" &&
    url.pathname === "/api/runs" &&
    [...url.searchParams.keys()].every((key) => key === "run_type") &&
    url.searchParams.getAll("run_type").length <= 1
  )
    return state === "error"
      ? send(res, 500, { detail: "Fixture API error: runs unavailable." })
      : send(res, 200, state === "empty" ? [] : runs);
  const runId = url.pathname.match(/^\/api\/runs\/([^/]+)/)?.[1];
  if (runId && !knownRunIds.has(runId) && !url.search)
    return reject(
      res,
      404,
      `Unsupported fixture request: ${req.method} ${url.pathname}${url.search}`,
    );
  if (
    req.method === "GET" &&
    /^\/api\/runs\/[^/]+\/artifacts$/.test(url.pathname) &&
    !url.search
  )
    return send(res, 200, state === "empty" ? [] : artifactList);
  if (
    req.method === "GET" &&
    /^\/api\/runs\/[^/]+\/artifacts\/text-content$/.test(url.pathname) &&
    url.searchParams.getAll("artifact_names").length === 1 &&
    url.searchParams.get("artifact_names") === "__action_server_output.txt"
  )
    return send(res, 200, state === "empty" ? {} : artifactText);
  if (
    req.method === "GET" &&
    /^\/api\/runs\/[^/]+\/artifacts\/(result\.json|nested%2Ftrace\.txt)$/.test(
      url.pathname,
    ) &&
    !url.search
  )
    return send(res, 200, '{"result":5}\n', "application/octet-stream");
  if (
    req.method === "GET" &&
    /^\/api\/runs\/[^/]+\/log\.html$/.test(url.pathname) &&
    !url.search
  )
    return send(
      res,
      200,
      "<!doctype html><title>Fixture log</title><pre>deterministic-v1</pre>",
      "text/html",
    );
  if (
    req.method === "GET" &&
    url.pathname === "/api/analytics/summary" &&
    !url.search
  )
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
  if (req.method === "GET" && url.pathname === "/api/ws" && !url.search)
    return send(res, 426, { detail: "WebSocket upgrade required" });
  if (
    req.method === "GET" &&
    url.pathname === "/api/work-items" &&
    [...url.searchParams.keys()].every(
      (key) => key === "limit" || key === "state",
    ) &&
    url.searchParams.getAll("limit").length === 1 &&
    url.searchParams.get("limit") === "1000"
  )
    return send(res, 200, []);
  if (
    req.method === "GET" &&
    url.pathname === "/api/work-items" &&
    [...url.searchParams.keys()].every(
      (key) => key === "limit" || key === "state",
    ) &&
    url.searchParams.getAll("limit").length === 1 &&
    url.searchParams.get("limit") === "10" &&
    url.searchParams.getAll("state").length === 1 &&
    url.searchParams.get("state") === "PENDING"
  )
    return send(res, 200, []);
  if (
    req.method === "GET" &&
    url.pathname === "/api/work-items/stats" &&
    !url.search
  )
    return send(res, 200, { total: 0, pending: 0, completed: 0, failed: 0 });
  if (
    req.method === "GET" &&
    /^\/api\/runs\/[^/]+$/.test(url.pathname) &&
    !url.search
  )
    return send(
      res,
      200,
      runs.find((run) => url.pathname.endsWith(run.id)) || runs[0],
    );
  if (url.pathname.startsWith("/api/") || url.pathname === "/config")
    return reject(
      res,
      404,
      `Unsupported fixture request: ${req.method} ${url.pathname}${url.search}`,
    );
  if (req.method !== "GET" || url.search)
    return reject(
      res,
      404,
      `Unsupported fixture request: ${req.method} ${url.pathname}${url.search}`,
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
};
const server = createServer((req, res) => {
  admitEmptyRequestBody(req)
    .then((error) => {
      if (error) return rejectBody(req, res, error.status, error.detail);
      dispatchRequest(req, res);
    })
    .catch(() =>
      rejectBody(req, res, 400, "The request body could not be read"),
    );
});
server.on("clientError", (error, socket) => {
  if (!socket.writable) return socket.destroy();
  const detail =
    error.code === "HPE_UNEXPECTED_CONTENT_LENGTH"
      ? "Contradictory Content-Length headers"
      : error.code === "HPE_INVALID_EOF_STATE"
        ? "The request body was aborted"
        : error.code === "HPE_INVALID_CONTENT_LENGTH"
          ? "Malformed or negative Content-Length header"
          : "Malformed request headers";
  const body = JSON.stringify({ detail });
  socket.end(
    `HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`,
  );
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
