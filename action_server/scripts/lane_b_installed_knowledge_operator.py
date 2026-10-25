"""Qualify installed a38 Knowledge operator provisioning, never generated execution.

Run with the installed consumer Python using -I. All mutations use public MCP or
stopped-local providers-local CLI; the sole SQL read discovers the saved Workspace.
No ingestion, search, generated Python, RCC execution or Task acceptance is claimed.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4


def require(condition):
    if not condition:
        raise ValueError("operator qualification assertion failed")


def qualify(root, prefix):
    root = root.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    data, empty = root / "datadir", root / "empty"
    empty.mkdir()
    key = secrets.token_urlsafe(32)
    process = reader = None
    shutdown = {"complete": False, "failed": False}
    receipt = {
        "status": "RUNNING",
        "scope": "installed operator provisioning only",
        "generated_ingestion": "NOT_RUN",
        "search": "NOT_RUN",
        "tasks": "NOT_RUN",
        "commands": [],
        "stage": "preflight",
    }
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(
            ("PYTHON", "ACTIONS_", "ACTION_SERVER_", "ROBOCORP_", "RC_")
        )
        and name != "VIRTUAL_ENV"
    }
    env.update(ROBOTS_HOME=str(root / "robots-home"), OMP_NUM_THREADS="1")

    def save():
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def stop():
        nonlocal process
        if process is None:
            return
        forced = False
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                forced = True
                process.kill()
                process.wait(timeout=10)
        reader.join(timeout=10)
        lifecycle = (data / "server_log.txt").read_text()
        shutdown["complete"] |= "Application shutdown complete." in lifecycle
        shutdown["failed"] |= "Application shutdown failed." in lifecycle
        receipt["shutdown"] = dict(
            shutdown, returncode=process.returncode, forced=forced
        )
        process = None
        require(
            not forced
            and not reader.is_alive()
            and shutdown["complete"]
            and not shutdown["failed"]
        )

    try:
        require(sys.flags.isolated == 1)
        require(Path(sys.prefix).resolve() == prefix.resolve())
        receipt["disk_free_bytes"] = shutil.disk_usage(root).free
        require(receipt["disk_free_bytes"] >= 1024**3)
        import actions
        import actions.server

        versions = {
            name: importlib.metadata.version(name)
            for name in ("actions-runtime", "actions-core")
        }
        require(versions == {"actions-runtime": "1.1.0a38", "actions-core": "1.1.0a3"})
        origins = {"runtime": actions.server.__file__, "core": actions.__file__}
        require(
            all(
                Path(path).resolve().is_relative_to(prefix.resolve())
                for path in origins.values()
            )
        )
        receipt.update(versions=versions, origins=origins, stage="bootstrap")
        save()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        command = [
            sys.executable,
            "-I",
            "-m",
            "actions.server",
            "start",
            "--address",
            "127.0.0.1",
            "--port",
            str(port),
            "--datadir",
            str(data),
            "--actions-sync=false",
            "--api-key",
            key,
        ]
        process = subprocess.Popen(
            command,
            cwd=empty,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        def drain():
            with (root / "server.log").open("wb") as output:
                for line in iter(process.stdout.readline, b""):
                    shutdown["complete"] |= b"Application shutdown complete." in line
                    shutdown["failed"] |= b"Application shutdown failed." in line
                    output.write(line.replace(key.encode(), b"[redacted]"))

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        deadline = time.monotonic() + 60
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while True:
            require(process.poll() is None)
            try:
                request = urllib.request.Request(
                    url + "/api/managed-work-items/v1/schema",
                    headers={"Authorization": "Bearer " + key},
                )
                with opener.open(request, timeout=2) as response:
                    require(response.status == 200)
                break
            except (OSError, ValueError):
                if time.monotonic() >= deadline:
                    raise TimeoutError("startup") from None
                time.sleep(0.2)

        async def bootstrap():
            import httpx2
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            async with httpx2.AsyncClient(
                headers={"Authorization": "Bearer " + key}, timeout=30, trust_env=False
            ) as http:
                async with streamable_http_client(
                    url + "/mcp", http_client=http
                ) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.discover()
                        result = await session.call_tool(
                            "canvas_create",
                            {
                                "title": "Lane B Knowledge operator fixture",
                                "idempotencyKey": "lane-b-owner-bootstrap",
                            },
                        )
                        require(not result.is_error)
                        receipt["application_id"] = result.structured_content[
                            "applicationId"
                        ]

        asyncio.run(asyncio.wait_for(bootstrap(), timeout=45))
        diagnostic = urllib.request.Request(
            url
            + "/api/workspaces/00000000-0000-0000-0000-000000000001/outputs/art_AAAAAAAAAAAAAAAAAAAAAA",
            data=b"",
            method="POST",
            headers={"Authorization": "Bearer " + key},
        )
        route = {
            "method": "POST",
            "path_template": "/api/workspaces/{workspace_id}/outputs/{handle}",
            "scope": "route registration diagnostic only; not artifact authorization or download",
        }
        try:
            with opener.open(diagnostic, timeout=5) as response:
                route["http_status"] = response.status
        except urllib.error.HTTPError as error:
            route["http_status"] = error.code
        except OSError as error:
            route["error_type"] = type(error).__name__
        receipt["output_route_diagnostic"] = route
        stop()
        with sqlite3.connect(
            (data / "server.db").as_uri() + "?mode=ro", uri=True
        ) as db:
            rows = db.execute(
                "SELECT result_json FROM foundry_request WHERE operation='runtime.bootstrap'"
            ).fetchall()
            require(len(rows) == 1)
            workspace = json.loads(rows[0][0])["workspace_id"]
        receipt.update(workspace_id=workspace, stage="operator")
        from actions.server.data_queries.knowledge_values import (
            KnowledgeCollectionRef,
            KnowledgeRevisionSpec,
        )
        from actions.server.deployments.ids import ProviderProfileId, WorkspaceId
        from actions.server.deployments.logical_bindings import (
            BindingField,
            BindingOperation,
        )
        from actions.server.deployments.provider_registry import (
            ProviderDescriptor,
            SourceManifest,
            SourceObject,
        )
        from actions.server.foundry.provider_config import (
            KnowledgeDuckDBHost,
            ProviderHostConfig,
        )

        def cli(value, dry=False):
            index = len(receipt["commands"])
            path = root / f"request-{index:02d}.json"
            path.write_text(json.dumps(value))
            args = [
                sys.executable,
                "-I",
                "-m",
                "actions.server",
                "providers-local",
                "--datadir",
                str(data),
                "--request",
                str(path),
            ]
            if dry:
                args.append("--dry-run")
            entry = {
                "operation": value["operation"],
                "dry_run": dry,
                "argv": args,
                "status": "RUNNING",
            }
            receipt["commands"].append(entry)
            save()
            result = subprocess.run(
                args, cwd=empty, env=env, capture_output=True, timeout=60
            )
            for label, raw in (("stdout", result.stdout), ("stderr", result.stderr)):
                (root / f"command-{index:02d}.{label}").write_bytes(
                    raw.replace(key.encode(), b"[redacted]")
                )
            entry.update(
                exit=result.returncode,
                status="PASS" if result.returncode == 0 else "FAIL",
            )
            save()
            result.check_returncode()
            return json.loads(result.stdout)

        def request(operation, **fields):
            return dict(
                schema_version="actions.local-provider-setup/v1",
                operation=operation,
                request_id=str(uuid4()),
                workspace_id=workspace,
                **fields,
            )

        def execute(value, *, readiness=None):
            preview = cli(value, True)
            if value["operation"] == "grant-owner":
                value["expected_grants_digest"] = preview["expected_grants_digest"]
            if value["operation"] == "configure-host":
                value["expected_catalog"] = preview["expected_catalog"]
            actual = cli(value)
            require(cli(value) == actual)
            if readiness:
                require(actual["readiness"] == readiness)
            return value, actual

        execute(request("grant-owner", permissions=["provider.register"]))
        objects, files = [], []
        for index, text in enumerate(
            ("Owned alpha document", "Owned beta document", "Owned gamma document")
        ):
            name, raw = f"document-{index}", text.encode("utf-8")
            path = root / (name + ".txt")
            path.write_bytes(raw)
            objects.append(
                SourceObject(
                    name=name,
                    digest="sha256:" + hashlib.sha256(raw).hexdigest(),
                    size=len(raw),
                )
            )
            files.append(dict(name=name, path=str(path)))
        source = SourceManifest(kind="knowledge", objects=tuple(objects))
        execute(
            request("import-source", source=source.model_dump(mode="json"), files=files)
        )
        descriptor = ProviderDescriptor(
            workspace_id=WorkspaceId(workspace),
            provider_profile_id=ProviderProfileId(str(uuid4())),
            source_revision=source.revision_id,
            kind="knowledge",
            operations=(
                BindingOperation(
                    name="documents.search/v1",
                    effect="read",
                    parameters=(BindingField(name="query", kind="string"),),
                    result=(BindingField(name="text", kind="string"),),
                    max_rows=20,
                    max_bytes=65536,
                    timeout_ms=1000,
                ),
            ),
        )
        execute(
            request("register-revision", descriptor=descriptor.model_dump(mode="json"))
        )
        provider = descriptor.reference.model_dump(mode="json")
        execute(
            request(
                "grant-owner",
                provider=provider,
                permissions=["provider.manage", "provider.inspect", "knowledge.read"],
            )
        )
        collection = KnowledgeCollectionRef(
            workspace_id=WorkspaceId(workspace), collection_id=str(uuid4())
        )
        execute(
            request(
                "grant-owner",
                knowledge_collection=collection.model_dump(mode="json"),
                permissions=["knowledge.read", "knowledge.manage"],
            )
        )
        definition = KnowledgeRevisionSpec(
            workspace_id=WorkspaceId(workspace),
            collection_id=collection.collection_id,
            source_revision=source.revision_id,
        )
        definition_request, defined = execute(
            request(
                "register-knowledge-definition",
                provider=provider,
                knowledge_definition=definition.model_dump(mode="json"),
            ),
            readiness="metadata-only",
        )
        config = ProviderHostConfig(
            schema_version="actions.local-provider-config/v2",
            provider=descriptor.reference,
            source_revision=source.revision_id,
            host=KnowledgeDuckDBHost(revision=definition.reference),
        )
        execute(
            request("configure-host", config=config.model_dump(mode="json")),
            readiness="configured-not-probed",
        )
        provision_request, provisioned = execute(
            request("provision-knowledge-host", config=config.model_dump(mode="json")),
            readiness="provisioned-not-ingested",
        )
        receipt["stage"] = "fresh_process_replay"
        require(cli(definition_request) == defined)
        require(cli(provision_request) == provisioned)
        inspected = cli(
            request("inspect", knowledge_collection=collection.model_dump(mode="json"))
        )
        require(inspected["knowledge_collection"] == collection.model_dump(mode="json"))
        require(inspected["readiness"] == "not-probed")
        receipt.update(
            status="PASS",
            stage="complete",
            readiness="provisioned-not-ingested",
            source_revision=source.revision_id,
            knowledge_revision=definition.reference.model_dump(mode="json"),
        )
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__)
    finally:
        try:
            stop()
        except BaseException as error:
            receipt.update(status="FAIL", cleanup_error_type=type(error).__name__)
        save()
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-prefix", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    sys.exit(qualify(args.root, args.expected_prefix))
