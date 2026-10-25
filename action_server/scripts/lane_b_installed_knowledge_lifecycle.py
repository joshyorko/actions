"""Draft installed Knowledge lifecycle acceptance; operator setup is prerequisite.

Run with prepared package-local Poetry. A private manifest supplies installed_python,
installed_prefix, expected_versions (actions-runtime/actions-core), source_checkpoint,
datadir, runtime_profile, task_policy, workspace_id, ingestion/search (app_id,
binding_id), query, page_limit, expected_hits, and output_root. Apps, generated
Packages, provider stores, exact grants and semantic artifact controls must already
exist in the owned stopped datadir. This runner does not provision or authorize them.
No installed execution has been qualified merely by compiling this draft.

Optional retained_ingestion supplies invocation_file and terminal_file from a
completed Task. Continuation checks the live snapshot and exact terminal before
downloading outputs; it never creates a replacement ingestion on mismatch/expiry.
Optional output_http_probes enables ordinary authenticated readback/denial probes.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

from qualify_lane_b_installed_knowledge import validate_restart

STAGES = ("installed_origin", "canvas", "ingestion", "pages", "restart", "replay")


def require(value):
    if not value:
        raise ValueError("lifecycle assertion failed")


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)
    elif isinstance(value, str) and value.startswith("{"):
        try:
            yield from objects(json.loads(value))
        except ValueError:
            pass


class Lifecycle:
    def __init__(self, manifest):
        self.m = manifest
        self.root = Path(manifest["output_root"]).resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        require(shutil.disk_usage(self.root).free >= 1024**3)
        self.empty = self.root / "empty"
        self.empty.mkdir()
        self.key = secrets.token_urlsafe(32)
        self.process = self.drain = None
        self.app_sessions = {}
        self.receipt = {
            "status": "RUNNING",
            "scope": "preprovisioned installed lifecycle",
            "setup": "operator/authoring prerequisite, not performed",
            "source_checkpoint": manifest["source_checkpoint"],
            "source_binding": "operator assertion; wheel source equivalence unverified",
            "stages": dict.fromkeys(STAGES, "NOT_RUN"),
            "tasks": [],
            "negative_authorization_cancel": "NOT_RUN",
            "grant_revocation": "NOT_RUN",
            "product_export_operation": "NOT_AVAILABLE; downloaded pages are not a dedicated export API",
        }
        self.env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("PYTHON", "ACTIONS_", "ROBOCORP_", "RC_"))
            and k != "VIRTUAL_ENV"
        }
        self.env.update(
            ACTIONS_FOUNDRY_EXECUTION_PROFILE=str(
                Path(manifest["runtime_profile"]).resolve()
            ),
            ACTIONS_FOUNDRY_TASK_POLICY=str(Path(manifest["task_policy"]).resolve()),
            ROBOTS_HOME=str(self.root / "robots-home"),
            OMP_NUM_THREADS="1",
        )
        self.timeout = manifest.get("timeout_seconds", 180)
        self.max_bytes = manifest.get("max_bytes", 1048576)
        require(
            isinstance(self.timeout, int)
            and not isinstance(self.timeout, bool)
            and 1 <= self.timeout <= 600
        )
        require(
            isinstance(self.max_bytes, int)
            and not isinstance(self.max_bytes, bool)
            and 1 <= self.max_bytes <= 16777216
        )
        require(
            isinstance(manifest["page_limit"], int)
            and not isinstance(manifest["page_limit"], bool)
            and 1 <= manifest["page_limit"] <= 100
        )
        require(
            isinstance(manifest["expected_hits"], list)
            and len(manifest["expected_hits"]) <= 10000
        )
        UUID(manifest["workspace_id"])
        for key in ("datadir", "runtime_profile", "task_policy", "installed_python"):
            require(Path(manifest[key]).is_absolute() and Path(manifest[key]).exists())

    def origin(self):
        code = (
            "import importlib,importlib.metadata as m,json,sys;"
            "print(json.dumps({'prefix':sys.prefix,'versions':{n:m.version(n) "
            "for n in ['actions-runtime','actions-core']},'origins':{n:"
            "importlib.import_module(n).__file__ for n in ['actions.server','actions']}}))"
        )
        result = subprocess.run(
            [self.m["installed_python"], "-I", "-c", code],
            cwd=self.empty,
            env=self.env,
            capture_output=True,
            timeout=30,
            check=True,
        )
        value = json.loads(result.stdout)
        prefix = Path(self.m["installed_prefix"]).resolve()
        require(Path(value["prefix"]).resolve() == prefix)
        require(value["versions"] == self.m["expected_versions"])
        require(
            all(
                Path(p).resolve().is_relative_to(prefix)
                for p in value["origins"].values()
            )
        )
        self.receipt["installed"] = value

    async def start(self, label):
        self.shutdown_complete = self.shutdown_failed = False
        self.server_log = Path(self.m["datadir"]) / "server_log.txt"
        self.server_log_offset = (
            self.server_log.stat().st_size if self.server_log.exists() else 0
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        self.process = await asyncio.create_subprocess_exec(
            self.m["installed_python"],
            "-I",
            "-m",
            "actions.server",
            "start",
            "--address",
            "127.0.0.1",
            "--port",
            str(port),
            "--datadir",
            self.m["datadir"],
            "--actions-sync=false",
            "--api-key",
            self.key,
            cwd=self.empty,
            env=self.env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        async def drain():
            with (self.root / (label + ".log")).open("wb") as stream:
                while line := await self.process.stdout.readline():
                    self.shutdown_complete |= b"Application shutdown complete." in line
                    self.shutdown_failed |= b"Application shutdown failed." in line
                    stream.write(line.replace(self.key.encode(), b"[redacted]"))

        self.drain = asyncio.create_task(drain())
        import httpx2

        async with httpx2.AsyncClient(headers=self.headers(), timeout=2) as client:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                require(self.process.returncode is None)
                try:
                    response = await client.get(
                        self.url + "/api/managed-work-items/v1/schema"
                    )
                    if response.status_code == 200:
                        return
                except httpx2.HTTPError:
                    pass
                await asyncio.sleep(0.2)
        raise TimeoutError("startup")

    def headers(self):
        return {"Authorization": "Bearer " + self.key}

    async def stop(self):
        if self.process is None:
            return
        process, drain = self.process, self.drain
        forced = False
        try:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), 30)
                except asyncio.TimeoutError:
                    forced = True
                    process.kill()
                    await process.wait()
            await drain
            if self.server_log.exists():
                with self.server_log.open("rb") as stream:
                    stream.seek(self.server_log_offset)
                    lifecycle = stream.read(4 * 1024 * 1024 + 1)
                require(len(lifecycle) <= 4 * 1024 * 1024)
                self.shutdown_complete |= b"Application shutdown complete." in lifecycle
                self.shutdown_failed |= b"Application shutdown failed." in lifecycle
            require(
                not forced
                and process.returncode in (0, -15)
                and self.shutdown_complete
                and not self.shutdown_failed
            )
        finally:
            self.receipt.setdefault("shutdowns", []).append(
                {
                    "returncode": process.returncode,
                    "forced": forced,
                    "lifespan_complete": self.shutdown_complete,
                    "lifespan_failed": self.shutdown_failed,
                }
            )
            self.process = self.drain = None

    async def connect(self, callback):
        import httpx2
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async with httpx2.AsyncClient(
            headers=self.headers(), timeout=self.timeout
        ) as http:
            async with streamable_http_client(
                self.url + "/mcp", http_client=http
            ) as streams:
                async with ClientSession(
                    streams[0],
                    streams[1],
                    extensions={"io.modelcontextprotocol/tasks": {}},
                ) as session:
                    found = await session.discover()
                    require(
                        "io.modelcontextprotocol/tasks"
                        in (found.capabilities.extensions or {})
                    )
                    return await asyncio.wait_for(callback(session), self.timeout)

    async def canvas(self, session):
        snapshots = {}
        for role in ("ingestion", "search"):
            app = self.m[role]
            reply = await session.call_tool("canvas_inspect", {"appId": app["app_id"]})
            require(not reply.is_error)
            matches = [
                d
                for d in reply.structured_content["invocationDescriptors"]
                if d["bindingId"] == app["binding_id"]
            ]
            require(len(matches) == 1)
            snapshots[role] = matches[0]["snapshot"]
            opened = await session.call_tool("canvas_get", {"appId": app["app_id"]})
            require(not opened.is_error)
            session = opened.meta.get("actions.appSession", {})
            if session.get("token"):
                self.app_sessions[role] = session["token"]
            spec = opened.meta["actions.canvas"]["spec"]
            require(
                any(
                    n.get("type") == "artifact"
                    and n.get("bindingId") == app["binding_id"]
                    for n in objects(spec)
                )
            )
        return snapshots

    async def request(self, session, *, args=None, task_id=None):
        from mcp.types import CallToolRequestParams, Request, RequestParams
        from pydantic import TypeAdapter

        class Params(RequestParams):
            taskId: str

        class NamedRequest(Request):
            name_param = "taskId"

        request = (
            NamedRequest(method="tasks/get", params=Params(taskId=task_id))
            if task_id
            else Request(
                method="tools/call",
                params=CallToolRequestParams(name="capability_invoke", arguments=args),
            )
        )
        return await session.send_request(request, TypeAdapter(dict))

    async def invoke(self, session, args):
        created = await self.request(session, args=args)
        require(created["resultType"] == "task" and "result" not in created)
        task = created["taskId"]
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            current = await self.request(session, task_id=task)
            if current["status"] == "completed":
                terminal = current["result"]["structuredContent"]
                require(terminal["state"] == "completed" and terminal["runId"] == task)
                require(bool(terminal["attemptId"]))
                return current
            require(current["status"] == "working")
            await asyncio.sleep(0.25)
        raise TimeoutError("task")

    async def artifacts(self, terminal):
        import httpx2

        values = []
        async with httpx2.AsyncClient(
            headers=self.headers(), timeout=30, trust_env=False, follow_redirects=False
        ) as client:
            for output in terminal["result"]["structuredContent"]["outputs"]:
                handle = output["handle"]
                require(re.fullmatch(r"art_[A-Za-z0-9_-]{22}", handle))
                url = f"{self.url}/api/workspaces/{self.m['workspace_id']}/outputs/{handle}"
                async with client.stream("GET", url) as response:
                    self.receipt.setdefault("artifact_http", []).append(
                        {
                            "route": "/api/workspaces/{workspace_id}/outputs/{handle}",
                            "status": response.status_code,
                        }
                    )
                    response.raise_for_status()
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        require(len(raw) <= self.max_bytes)
                try:
                    decoded = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    continue
                values.append((bytes(raw), decoded))
                if self.m.get("output_http_probes") and any(
                    obj.get("version")
                    in ("actions.knowledge-ingestion/v1", "actions.knowledge-search/v1")
                    for obj in objects(decoded)
                ):
                    from lane_b_installed_output_http import (
                        OutputHttpFailure,
                        OutputHttpProbe,
                    )

                    probe = OutputHttpProbe(
                        self.url,
                        self.key,
                        self.m["workspace_id"],
                        handle,
                        bytes(raw),
                        app_session=self.app_sessions.get("search"),
                    )
                    try:
                        receipt = await probe.qualify()
                    except OutputHttpFailure as exc:
                        self.receipt.setdefault("output_denials", []).append(
                            exc.receipt
                        )
                        raise
                    self.receipt.setdefault("output_denials", []).append(receipt)
        return values

    async def retained_ingestion(self, snapshot):
        retained = self.m["retained_ingestion"]
        args = json.loads(Path(retained["invocation_file"]).read_bytes())
        terminal = json.loads(Path(retained["terminal_file"]).read_bytes())
        require(args["mode"] == "detached" and args["snapshot"] == snapshot)
        require(args["inputs"] == {} and bool(args["idempotencyKey"]))
        # Read first: a missing/expired Task must not silently become a new Run.
        current = await self.connect(
            lambda session: self.request(session, task_id=terminal["taskId"])
        )
        require(current == terminal)
        replay = await self.connect(lambda session: self.invoke(session, args))
        require(replay == terminal)
        return args, terminal

    async def run(self):
        stage = "installed_origin"
        try:
            self.origin()
            self.receipt["stages"][stage] = "PASS"
            stage = "canvas"
            await self.start("before")
            snapshots = await self.connect(self.canvas)
            self.receipt["stages"][stage] = "PASS"
            calls = []

            async def execute(role, inputs, key):
                args = dict(
                    mode="detached",
                    snapshot=snapshots[role],
                    inputs=inputs,
                    idempotencyKey="lane-b-" + self.root.name + "-" + key,
                )
                raw = json.dumps(args, sort_keys=True, separators=(",", ":")).encode()
                (self.root / (key + "-invocation.json")).write_bytes(raw)
                self.receipt.setdefault("invocations", []).append(
                    {
                        "file": key + "-invocation.json",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                )
                terminal = await self.connect(lambda s: self.invoke(s, args))
                (self.root / (key + "-terminal.json")).write_text(
                    json.dumps(terminal, indent=2)
                )
                calls.append((args, terminal))
                result = terminal["result"]["structuredContent"]
                self.receipt["tasks"].append(
                    {k: result[k] for k in ("runId", "attemptId")}
                )
                return await self.artifacts(terminal)

            stage = "ingestion"
            if self.m.get("retained_ingestion"):
                args, terminal = await self.retained_ingestion(snapshots["ingestion"])
                calls.append((args, terminal))
                self.receipt["retained_ingestion"] = "EXACT_REPLAY"
                outputs = await self.artifacts(terminal)
            else:
                outputs = await execute("ingestion", {}, "ingest")
            ingestions = [
                o
                for _, value in outputs
                for o in objects(value)
                if o.get("version") == "actions.knowledge-ingestion/v1"
            ]
            require(len(ingestions) == 1)
            handle = ingestions[0]["corpusHandle"]
            self.receipt["stages"][stage] = "PASS"
            stage = "pages"
            before = []
            for offset in range(
                0, max(1, len(self.m["expected_hits"])), self.m["page_limit"]
            ):
                outputs = await execute(
                    "search",
                    dict(
                        ingestion_handle=handle,
                        query=self.m["query"],
                        offset=offset,
                        limit=self.m["page_limit"],
                    ),
                    f"page-{offset}",
                )
                pages = [
                    raw
                    for raw, value in outputs
                    if isinstance(value, dict)
                    and value.get("version") == "actions.knowledge-search/v1"
                ]
                require(len(pages) == 1)
                (self.root / f"before-page-{len(before)}.json").write_bytes(pages[0])
                before.extend(pages)
            self.receipt["stages"][stage] = "PASS"
            stage = "restart"
            await self.stop()
            await self.start("after")
            require(await self.connect(self.canvas) == snapshots)
            self.receipt["stages"][stage] = "PASS"
            stage = "replay"
            after = []
            for index, (args, terminal) in enumerate(calls):
                replay = await self.connect(lambda s: self.invoke(s, args))
                require(replay == terminal)
                outputs = await self.artifacts(replay)
                if index:
                    pages = [
                        raw
                        for raw, value in outputs
                        if isinstance(value, dict)
                        and value.get("version") == "actions.knowledge-search/v1"
                    ]
                    require(len(pages) == 1)
                    (self.root / f"after-page-{len(after)}.json").write_bytes(pages[0])
                    after.extend(pages)
            self.receipt["pages"] = validate_restart(
                before, after, self.m["expected_hits"], max_bytes=self.max_bytes
            )
            await self.stop()
            self.receipt["stages"][stage] = "PASS"
            self.receipt["status"] = "PASS"
        except BaseException as exc:
            self.receipt.update(status="FAIL", error_type=type(exc).__name__)
            self.receipt["stages"][stage] = "FAIL"
        finally:
            try:
                await self.stop()
            except BaseException as exc:
                self.receipt.update(
                    status="FAIL", cleanup_error_type=type(exc).__name__
                )
            (self.root / "receipt.json").write_text(
                json.dumps(self.receipt, indent=2) + "\n"
            )
        return 0 if self.receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    sys.exit(asyncio.run(Lifecycle(json.loads(args.manifest.read_bytes())).run()))
