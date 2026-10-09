"""Live Runtime browser coverage for Origin and ambient-session boundaries."""

import concurrent.futures
import importlib.util
import json
import logging
import os
import shutil
import socket
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path

import pytest


def _run_browser_harness(command, input_data, *, process_owner, timeout_seconds, cwd):
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=cwd, prefix="browser-input-", delete=False
    ) as input_file:
        json.dump(input_data, input_file)
        input_path = Path(input_file.name)
    env = os.environ.copy()
    env["ACTIONS_BROWSER_ACCEPTANCE_INPUT"] = str(input_path)
    try:
        return process_owner.run_owned_process(
            command, timeout_seconds=timeout_seconds, env=env, cwd=cwd
        )
    finally:
        input_path.unlink(missing_ok=True)


@pytest.mark.integration_test
def test_browser_harness_deadline_reaps_owned_descendant(tmp_path):
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "verify_dakota_rcc_acceptance.py"
    )
    spec = importlib.util.spec_from_file_location("browser_process_owner", script)
    assert spec is not None and spec.loader is not None
    process_owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(process_owner)
    child_pid_file = tmp_path / "child.pid"
    node = shutil.which("node")
    assert node is not None, "RCC Node.js is required for owned-tree timeout coverage"
    input_data = {
        "runtime_origin": "http://127.0.0.1:1",
        "force_hang_after_browser_launch": True,
        "process_pid_file": str(child_pid_file),
    }
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    started = time.monotonic()

    import psutil

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _run_browser_harness,
            [node, "--input-type=module", "-e", _BROWSER_SCRIPT],
            input_data,
            process_owner=process_owner,
            timeout_seconds=15,
            cwd=frontend,
        )
        browser_processes = []
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not browser_processes:
            if child_pid_file.exists():
                node_pid = int(child_pid_file.read_text())
                try:
                    descendants = psutil.Process(node_pid).children(recursive=True)
                    for child in descendants:
                        try:
                            if any(
                                "chrome" in part.lower() for part in child.cmdline()
                            ):
                                if child.status() != psutil.STATUS_ZOMBIE:
                                    browser_processes.append(child)
                        except psutil.NoSuchProcess:
                            continue
                except psutil.Error:
                    pass
            if not browser_processes:
                time.sleep(0.05)
        assert (
            browser_processes
        ), "forced hang never exposed an owned Chromium descendant"
        with pytest.raises(subprocess.TimeoutExpired):
            future.result(timeout=25)

    assert time.monotonic() - started < 30
    deadline = time.monotonic() + 3
    remaining_processes = list(browser_processes)
    while remaining_processes and time.monotonic() < deadline:
        still_running = []
        for process in remaining_processes:
            try:
                status = process.status()
            except psutil.NoSuchProcess:
                continue
            if status != psutil.STATUS_ZOMBIE:
                still_running.append(process)
        remaining_processes = still_running
        if remaining_processes:
            time.sleep(0.05)
    assert not remaining_processes, (
        "owned Chromium descendants remained live after the harness deadline: "
        f"{[process.pid for process in remaining_processes]}"
    )


_BROWSER_SCRIPT = textwrap.dedent(
    r"""
    import assert from "node:assert/strict";
    import { request as httpRequest } from "node:http";
    import { readFileSync, writeFileSync } from "node:fs";
    import { chromium } from "@playwright/test";

    const input = JSON.parse(readFileSync(process.env.ACTIONS_BROWSER_ACCEPTANCE_INPUT, "utf8"));
    const target = new URL(input.runtime_origin);
    const requests = [];
    let phase = "launch";
    let diagnostics = {};
    let browser;
    const runtimeRequest = ({ method, origin, cookie, preflightMethod, path = input.probe_paths.backend }) => new Promise((resolve, reject) => {
        const headers = { Origin: origin };
        if (cookie) headers.Cookie = cookie;
        if (preflightMethod) {
            headers["Access-Control-Request-Method"] = preflightMethod;
            headers["Access-Control-Request-Headers"] = "content-type,x-origin-acceptance";
        }
        let deadline;
        const request = httpRequest({
            hostname: target.hostname,
            family: target.hostname === "localhost" ? 4 : undefined,
            port: Number(target.port),
            path,
            method,
            headers,
        }, (response) => {
            response.setTimeout(10000, () => response.destroy(new Error("Runtime response deadline exceeded")));
            response.resume();
            response.on("end", () => {
                clearTimeout(deadline);
                resolve(response.statusCode);
            });
            response.on("error", (error) => {
                clearTimeout(deadline);
                reject(error);
            });
        });
        deadline = setTimeout(() => request.destroy(new Error("Runtime request deadline exceeded")), 10000);
        request.on("error", (error) => {
            clearTimeout(deadline);
            reject(error);
        });
        request.end(method === "POST" ? "{}" : undefined);
    });
    try {
        browser = await chromium.launch({
            headless: true,
        });
        if (input.force_hang_after_browser_launch) {
            writeFileSync(input.process_pid_file, String(process.pid));
            await new Promise(() => {});
        }
        const context = await browser.newContext();
        const page = await context.newPage();
        page.on("requestfailed", (request) => {
            diagnostics.requestFailures ??= [];
            const url = new URL(request.url());
            diagnostics.requestFailures.push({
                method: request.method(),
                path: url.pathname,
                error: request.failure()?.errorText,
            });
        });
        page.setDefaultTimeout(15000);
        context.on("request", (request) => {
            const url = new URL(request.url());
            if (url.origin === target.origin && url.pathname.startsWith("/api/")) {
                requests.push({
                    method: request.method(),
                    headers: request.headers(),
                    path: url.pathname,
                });
            }
        });
        await context.route("**/*", async (route) => {
            if (new URL(route.request().url()).origin === target.origin) {
                await route.continue();
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: "text/html",
                    body: "<!doctype html><title>Origin fixture</title>",
                });
            }
        });
        phase = "same_origin_auth_rejections";
        await page.goto(`${target.origin}/`);
        const missingAuth = await page.evaluate(async () => (await fetch("/api/runs", { signal: AbortSignal.timeout(10000) })).status);
        assert.equal(missingAuth, 403);

        phase = "browser_session_sign_in";
        await page.goto(`${target.origin}/work-items`, { waitUntil: "networkidle" });
        await page.getByLabel("API key", { exact: true }).fill(input.api_key);
        await page.getByRole("button", { name: "Sign in", exact: true }).click();
        await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
        const sameOrigin = await page.evaluate(async () => (await fetch("/api/runs", { signal: AbortSignal.timeout(10000) })).status);
        assert.equal(sameOrigin, 200);
        const cookie = (await context.cookies()).find((item) => item.name === "actions_browser_session");
        assert.ok(cookie && cookie.httpOnly && cookie.sameSite === "Strict");
        diagnostics.sessionCookie = {
            domain: cookie.domain,
            sameSite: cookie.sameSite,
            secure: cookie.secure,
            targetHost: target.hostname,
            allowedHost: new URL(input.allowed_origin).hostname,
        };
        const cookieHeader = `${cookie.name}=${cookie.value}`;

        phase = "wrong_bearer_with_session";
        const wrongBearer = await page.evaluate(async () => (await fetch("/api/runs", { headers: { Authorization: "Bearer wrong" }, signal: AbortSignal.timeout(10000) })).status);
        assert.equal(wrongBearer, 403);

        const fetchFromOrigin = async (origin, method, path) => {
            await page.goto(origin);
            assert.equal(await page.evaluate(() => location.origin), origin);
            const probe = `${target.origin}${path}`;
            return page.evaluate(async ({ probe, method }) => {
                try {
                    const response = await fetch(probe, {
                        method,
                        credentials: "include",
                        signal: AbortSignal.timeout(10000),
                        ...(method === "POST" ? { headers: { "Content-Type": "application/json", "X-Origin-Acceptance": "probe" }, body: "{}" } : {}),
                    });
                    return { outcome: "response", status: response.status, allowOrigin: response.headers.get("access-control-allow-origin") };
                } catch (error) {
                    return { outcome: error.name === "TypeError" ? "blocked" : "error", error: error.name };
                }
            }, { probe, method });
        };

        phase = "allowed_origin_nonpreflight";
        await page.goto(input.allowed_origin);
        assert.equal(await page.evaluate(() => location.origin), input.allowed_origin);
        const allowedGet = await fetchFromOrigin(input.allowed_origin, "GET", input.probe_paths.allowed);
        diagnostics.allowedGet = allowedGet;
        assert.equal(allowedGet.outcome, "blocked");
        const allowedGetRequest = requests.find((item) => item.method === "GET" && item.path === input.probe_paths.allowed && item.headers.origin === input.allowed_origin);
        diagnostics.allowedGetRequest = {
            found: Boolean(allowedGetRequest),
            ambient_cookie_sent: Boolean(allowedGetRequest?.headers.cookie?.includes("actions_browser_session=")),
        };
        assert.ok(allowedGetRequest?.headers.cookie?.includes("actions_browser_session="));
        const allowedGetStatus = await runtimeRequest({
            method: "GET",
            origin: input.allowed_origin,
            cookie: cookieHeader,
            path: input.probe_paths.backend,
        });
        assert.equal(allowedGetStatus, 403);

        phase = "allowed_origin_preflight";
        const allowedPost = await fetchFromOrigin(input.allowed_origin, "POST", input.probe_paths.allowed);
        assert.equal(allowedPost.outcome, "blocked");
        assert.ok(requests.some((item) => item.method === "POST" && item.path === input.probe_paths.allowed && item.headers.origin === input.allowed_origin && item.headers.cookie?.includes("actions_browser_session=")));
        const allowedPreflightStatus = await runtimeRequest({
            method: "OPTIONS",
            origin: input.allowed_origin,
            preflightMethod: "POST",
        });
        const allowedPostStatus = await runtimeRequest({
            method: "POST",
            origin: input.allowed_origin,
            cookie: cookieHeader,
        });
        assert.equal(allowedPreflightStatus, 200);
        assert.equal(allowedPostStatus, 403);

        phase = "denied_origin_matrix";
        for (const [index, origin] of input.denied_origins.entries()) {
            const path = input.probe_paths.denied[index];
            const before = requests.length;
            const get = await fetchFromOrigin(origin, "GET", path);
            assert.equal(get.outcome, "blocked");
            assert.ok(requests.slice(before).some((item) => item.method === "GET" && item.path === path && item.headers.origin === origin));
            const getStatus = await runtimeRequest({ method: "GET", origin, cookie: cookieHeader });
            assert.equal(getStatus, 403);
            const postStatus = await runtimeRequest({
                method: "POST",
                origin,
                cookie: cookieHeader,
            });
            assert.equal(postStatus, 403);

            const postStart = requests.length;
            const post = await fetchFromOrigin(origin, "POST", path);
            assert.equal(post.outcome, "blocked");
            diagnostics[`deniedPost${index}`] = {
                browser_request_observed: requests.slice(postStart).some((item) => item.method === "POST" && item.path === path && item.headers.origin === origin),
            };
            const preflightStatus = await runtimeRequest({ method: "OPTIONS", origin, preflightMethod: "POST" });
            assert.equal(preflightStatus, 400);
        }

        phase = "null_origin_matrix";
        await page.goto(input.allowed_origin);
        const nullProbe = `${target.origin}${input.probe_paths.null}`;
        const nullOrigin = await page.evaluate(async (probe) => {
            const frame = document.createElement("iframe");
            frame.sandbox = "allow-scripts";
            const frameLoaded = new Promise((resolve, reject) => {
                const timer = setTimeout(() => reject(new Error("sandbox frame load timeout")), 5000);
                frame.addEventListener("load", () => {
                    clearTimeout(timer);
                    resolve();
                }, { once: true });
            });
            frame.srcdoc = `<script>
                const probe = ${JSON.stringify(probe)};
                const send = async (method) => {
                    try {
                        const response = await fetch(probe, {
                            method,
                            credentials: "include",
                            signal: AbortSignal.timeout(10000),
                            ...(method === "POST" ? { headers: { "Content-Type": "application/json", "X-Origin-Acceptance": "probe" }, body: "{}" } : {}),
                        });
                        parent.postMessage({ method, outcome: "response", status: response.status }, "*");
                    } catch (error) {
                        parent.postMessage({ method, outcome: error.name === "TypeError" ? "blocked" : "error", error: error.name }, "*");
                    }
                };
                addEventListener("message", (event) => void send(event.data));
            <\/script>`;
            document.body.append(frame);
            await frameLoaded;
            const run = (method) => new Promise((resolve) => {
                const timer = setTimeout(() => {
                    removeEventListener("message", listener);
                    resolve({ method, outcome: "timeout" });
                }, 12000);
                const listener = (event) => {
                    if (event.source !== frame.contentWindow || event.data?.method !== method) return;
                    removeEventListener("message", listener);
                    clearTimeout(timer);
                    resolve(event.data);
                };
                addEventListener("message", listener);
                frame.contentWindow.postMessage(method, "*");
            });
            return [await run("GET"), await run("POST")];
        }, nullProbe);
        assert.deepEqual(nullOrigin.map((item) => item.outcome), ["blocked", "blocked"]);
        const nullRequests = requests.filter((item) => item.headers.origin === "null");
        assert.ok(nullRequests.some((item) => item.method === "GET" && item.path === input.probe_paths.null));
        const nullGetStatus = await runtimeRequest({
            method: "GET",
            origin: "null",
            cookie: cookieHeader,
            path: input.probe_paths.backend,
        });
        const nullPostStatus = await runtimeRequest({
            method: "POST",
            origin: "null",
            cookie: cookieHeader,
            path: input.probe_paths.backend,
        });
        const nullPreflightStatus = await runtimeRequest({
            method: "OPTIONS",
            origin: "null",
            preflightMethod: "POST",
            path: input.probe_paths.backend,
        });
        assert.equal(nullGetStatus, 403);
        assert.equal(nullPostStatus, 403);
        assert.equal(nullPreflightStatus, 400);

        phase = "no_secret_in_browser_urls_or_diagnostics";
        assert.equal(page.url().includes(input.api_key), false);
        assert.equal(JSON.stringify(requests).includes(input.api_key), false);
        process.stdout.write(JSON.stringify({
            status: "PASS",
            browser: browser.version(),
            session_mode: "HttpOnly SameSite=Strict browser session",
            browser_requests: requests.map((item) => ({
                method: item.method,
                path: item.path,
                origin: item.headers.origin ?? null,
                content_type: item.headers["content-type"] ?? null,
                acceptance_header: item.headers["x-origin-acceptance"] ?? null,
                session_cookie_sent: Boolean(item.headers.cookie?.includes("actions_browser_session=")),
            })),
            browser_request_failures: diagnostics.requestFailures ?? [],
            matrix: {
                allowed_origin: { browser_cookie: true, get: allowedGetStatus, preflight: allowedPreflightStatus, post: allowedPostStatus, script_read: "CORS-blocked" },
                denied_origins: input.denied_origins.length,
                null_origin: { get: nullGetStatus, preflight: nullPreflightStatus, post: nullPostStatus },
                auth_without_session: missingAuth,
                wrong_bearer_with_session_cookie: wrongBearer,
            },
        }) + "\n");
    } catch (error) {
        diagnostics.network = {
            requests: requests.map((item) => ({
                method: item.method,
                origin: item.headers.origin ?? null,
                has_session_cookie: Boolean(item.headers.cookie?.includes("actions_browser_session=")),
                path: item.path,
            })),
        };
        process.stdout.write(JSON.stringify({
            status: "FAIL",
            phase,
            error_type: error.name,
            error_message: String(error.message ?? error).replaceAll(input.api_key ?? "\u0000", "[redacted]").slice(0, 500),
            diagnostics,
        }) + "\n");
        process.exitCode = 1;
    } finally {
        if (browser) await browser.close();
    }
    """,
).strip()


def _free_loopback_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@pytest.mark.integration_test
def test_live_runtime_browser_origin_and_ambient_session_matrix(
    action_server_process, monkeypatch
):
    node = shutil.which("node")
    if node is None:
        pytest.fail("RCC Node.js is required for real-browser acceptance")

    monkeypatch.setattr(
        logging.getLogger("actions.server._robo_utils.process"),
        "level",
        logging.WARNING,
    )
    action_server_process.SHOW_OUTPUT = False
    browser_origin = f"http://127.0.0.1:{_free_loopback_port()}"
    action_server_process.start(
        db_file="browser-origin.db",
        additional_args=[
            "--api-key=test-key",
            "--address=127.0.0.1",
            f"--cors-allow-origin={browser_origin}",
        ],
    )
    runtime_origin = f"http://{action_server_process.host}:{action_server_process.port}"
    input_data = {
        "runtime_origin": runtime_origin,
        "allowed_origin": browser_origin,
        "denied_origins": [
            f"http://localhost:{_free_loopback_port()}",
            f"http://127.0.0.1.evil.invalid:{_free_loopback_port()}",
        ],
        "probe_paths": {
            "allowed": "/api/__origin_acceptance_allowed__",
            "denied": [
                "/api/__origin_acceptance_denied_loopback__",
                "/api/__origin_acceptance_denied_lookalike__",
            ],
            "null": "/api/__origin_acceptance_null__",
            "backend": "/api/__origin_acceptance_backend__",
        },
        "api_key": "test-key",
    }
    process_owner_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "verify_dakota_rcc_acceptance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "browser_process_owner", process_owner_path
    )
    assert spec is not None and spec.loader is not None
    process_owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(process_owner)
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    try:
        completed = _run_browser_harness(
            [node, "--input-type=module", "-e", _BROWSER_SCRIPT],
            input_data,
            process_owner=process_owner,
            timeout_seconds=180,
            cwd=frontend,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"Browser harness exceeded its owned-process deadline: {exc}")
    try:
        receipt = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        pytest.fail("Browser harness returned no bounded JSON receipt")
    assert completed.returncode == 0 and receipt["status"] == "PASS", json.dumps(
        receipt, sort_keys=True
    )
    assert "test-key" not in action_server_process.get_stdout()
    assert "test-key" not in action_server_process.get_stderr()
