"""Prepare owned installed Knowledge apps through public CLI/MCP only.

Run using the candidate consumer Python -I after its wheel origins and prepared
RCC artifact have been independently verified. This prepares real generated
Actions but does not claim ingestion/search/download acceptance; the emitted
private manifest is input to lane_b_installed_knowledge_lifecycle.py.
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
import urllib.request
from pathlib import Path
from uuid import uuid4


def require(value):
    if not value:
        raise ValueError("installed fixture assertion failed")


class Fixture:
    def __init__(self, args):
        self.args = args
        self.root = args.root.resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.empty = self.root / "empty"
        self.empty.mkdir()
        self.data = self.root / "datadir"
        self.profile = self.root / "profile.json"
        self.policy = self.root / "task-policy.json"
        self.key = secrets.token_urlsafe(32)
        self.process = self.reader = None
        self.receipt = {
            "status": "RUNNING",
            "stage": "preflight",
            "commands": [],
            "calls": [],
            "execution": "NOT_RUN",
        }
        self.env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(
                ("PYTHON", "ACTIONS_", "ACTION_SERVER_", "ROBOCORP_", "RC_")
            )
            and k != "VIRTUAL_ENV"
        }
        self.env.update(ROBOTS_HOME=str(self.root / "robots-home"), OMP_NUM_THREADS="1")

    def save(self):
        (self.root / "receipt.json").write_text(
            json.dumps(self.receipt, indent=2) + "\n"
        )

    def sanitized(self, value):
        if isinstance(value, dict):
            return {
                k: "[redacted]"
                if k.lower() in {"token", "authorization", "api_key", "password"}
                else self.sanitized(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.sanitized(v) for v in value]
        return (
            value.replace(self.key, "[redacted]") if isinstance(value, str) else value
        )

    def start(self, profile=False):
        self.server_log = self.data / "server_log.txt"
        self.log_offset = (
            self.server_log.stat().st_size if self.server_log.exists() else 0
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        env = dict(self.env)
        if profile:
            env.update(
                ACTIONS_FOUNDRY_EXECUTION_PROFILE=str(self.profile),
                ACTIONS_FOUNDRY_TASK_POLICY=str(self.policy),
            )
        self.process = subprocess.Popen(
            [
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
                str(self.data),
                "--actions-sync=false",
                "--api-key",
                self.key,
            ],
            cwd=self.empty,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        process = self.process

        def drain():
            with (
                self.root
                / ("server-profile.log" if profile else "server-bootstrap.log")
            ).open("wb") as stream:
                for line in iter(process.stdout.readline, b""):
                    stream.write(line.replace(self.key.encode(), b"[redacted]"))

        self.reader = threading.Thread(target=drain, daemon=True)
        self.reader.start()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            require(process.poll() is None)
            try:
                req = urllib.request.Request(
                    self.url + "/api/managed-work-items/v1/schema",
                    headers={"Authorization": "Bearer " + self.key},
                )
                with opener.open(req, timeout=2) as response:
                    if response.status == 200:
                        return
            except OSError:
                pass
            time.sleep(0.2)
        raise TimeoutError("startup")

    def stop(self):
        if self.process is None:
            return
        process, self.process = self.process, None
        forced = False
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                forced = True
                process.kill()
                process.wait(timeout=10)
        self.reader.join(timeout=10)
        with self.server_log.open("rb") as stream:
            stream.seek(self.log_offset)
            log = stream.read(4 * 1024 * 1024 + 1)
        complete = (
            b"Application shutdown complete." in log
            and b"Application shutdown failed." not in log
        )
        self.receipt.setdefault("shutdowns", []).append(
            dict(
                returncode=process.returncode,
                forced=forced,
                lifecycle_complete=complete,
            )
        )
        require(
            not forced
            and not self.reader.is_alive()
            and process.returncode in (0, -15)
            and len(log) <= 4 * 1024 * 1024
            and complete
        )

    async def connect(self, function):
        import httpx2
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async with httpx2.AsyncClient(
            headers={"Authorization": "Bearer " + self.key},
            timeout=360,
            trust_env=False,
        ) as http:
            async with streamable_http_client(
                self.url + "/mcp", http_client=http
            ) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.discover()
                    return await asyncio.wait_for(function(session), 600)

    async def call(self, session, name, arguments):
        index = len(self.receipt["calls"])
        (self.root / f"mcp-{index:02d}-request.json").write_text(
            json.dumps(self.sanitized({"tool": name, "arguments": arguments}), indent=2)
        )
        result = await session.call_tool(name, arguments, read_timeout_seconds=360)
        self.receipt["calls"].append(dict(tool=name, is_error=result.is_error))
        (self.root / f"mcp-{index:02d}.json").write_text(
            json.dumps(
                self.sanitized(result.model_dump(mode="json", by_alias=True)), indent=2
            )
        )
        self.save()
        require(not result.is_error)
        return result

    def cli(self, command, value, dry=False):
        require(self.process is None)
        index = len(self.receipt["commands"])
        path = self.root / f"request-{index:02d}.json"
        path.write_text(json.dumps(value))
        argv = [
            sys.executable,
            "-I",
            "-m",
            "actions.server",
            command,
            "--datadir",
            str(self.data),
            "--request",
            str(path),
        ]
        if dry:
            argv.append("--dry-run")
        entry = dict(
            command=command, operation=value["operation"], dry_run=dry, status="RUNNING"
        )
        self.receipt["commands"].append(entry)
        self.save()
        result = subprocess.run(
            argv, cwd=self.empty, env=self.env, capture_output=True, timeout=60
        )
        for label, data in (("stdout", result.stdout), ("stderr", result.stderr)):
            (self.root / f"cli-{index:02d}.{label}").write_bytes(
                data.replace(self.key.encode(), b"[redacted]")
            )
        entry.update(
            status="PASS" if result.returncode == 0 else "FAIL", exit=result.returncode
        )
        self.save()
        result.check_returncode()
        return json.loads(result.stdout)

    def provider(self, operation, **fields):
        request = dict(
            schema_version="actions.local-provider-setup/v1",
            operation=operation,
            request_id=str(uuid4()),
            workspace_id=self.workspace,
            **fields,
        )
        preview = self.cli("providers-local", request, True)
        if operation == "grant-owner":
            request["expected_grants_digest"] = preview["expected_grants_digest"]
        if operation == "configure-host":
            request["expected_catalog"] = preview["expected_catalog"]
        actual = self.cli("providers-local", request)
        require(self.cli("providers-local", request) == actual)
        return actual

    def authorize(self, operation, target, **fields):
        request = dict(
            schema_version="actions.local-authorization/v1",
            operation=operation,
            target=target,
            request_id=str(uuid4()),
            workspace_id=self.workspace,
            runtime_profile=str(self.profile),
            **fields,
        )
        preview = self.cli("authorize-local", request, True)
        request["expected_grants_digest"] = preview["expected_grants_digest"]
        actual = self.cli("authorize-local", request)
        require(not actual["dryRun"] and self.cli("authorize-local", request)["replay"])

    def configure(self):
        from actions.server.data_queries.knowledge_values import (
            KnowledgeCollectionRef,
            KnowledgeRevisionSpec,
        )
        from actions.server.deployments.ids import (
            PolicyId,
            PolicyRevisionId,
            ProviderProfileId,
            ProviderProfileRevisionId,
            ProviderProfileRevisionRef,
            WorkerProfileId,
            WorkerProfileRevisionId,
            WorkerProfileRevisionRef,
            WorkspaceId,
            WorkspacePolicyRevisionRef,
        )
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
        from actions.server.foundry.runtime_profile import RuntimeExecutionProfile

        with sqlite3.connect(
            (self.data / "server.db").as_uri() + "?mode=ro", uri=True
        ) as db:
            rows = db.execute(
                "SELECT result_json FROM foundry_request WHERE operation='runtime.bootstrap'"
            ).fetchall()
        require(len(rows) == 1)
        self.workspace = json.loads(rows[0][0])["workspace_id"]
        ws = WorkspaceId(self.workspace)
        profile = RuntimeExecutionProfile(
            schema_version="actions.runtime-rcc-profile/v1",
            admission="trusted-developer-execution",
            prepared_receipt=str(self.args.prepared.resolve()),
            worker_id=str(uuid4()),
            worker=WorkerProfileRevisionRef(
                workspace_id=ws,
                worker_profile_id=WorkerProfileId(uuid4()),
                revision_id=WorkerProfileRevisionId("sha256:" + "1" * 64),
            ),
            policy=WorkspacePolicyRevisionRef(
                workspace_id=ws,
                policy_id=PolicyId(uuid4()),
                revision_id=PolicyRevisionId("sha256:" + "2" * 64),
            ),
            output_provider=ProviderProfileRevisionRef(
                workspace_id=ws,
                provider_profile_id=ProviderProfileId(uuid4()),
                revision_id=ProviderProfileRevisionId("sha256:" + "3" * 64),
            ),
        )
        self.profile.write_text(profile.model_dump_json(indent=2))
        self.policy.write_text(
            json.dumps(
                dict(
                    schema_version="actions.runtime-task-policy/v1",
                    policy_id="lane-b-installed/v1",
                    ttl_ms=3600000,
                    poll_interval_ms=50,
                )
            )
        )
        self.authorize("authorize-generated-source", "generated-source")
        self.provider("grant-owner", permissions=["provider.register"])
        objects, files, self.expected = [], [], []
        for name, text in (
            ("doc_a", "owned alpha"),
            ("doc_b", "owned beta"),
            ("doc_c", "owned gamma"),
        ):
            raw = text.encode()
            path = self.root / (name + ".txt")
            path.write_bytes(raw)
            objects.append(
                SourceObject(
                    name=name,
                    digest="sha256:" + hashlib.sha256(raw).hexdigest(),
                    size=len(raw),
                )
            )
            files.append(dict(name=name, path=str(path)))
            document_id = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps([name, 0], separators=(",", ":")).encode()
                ).hexdigest()
            )
            self.expected.append(
                dict(id=document_id, source=name, ordinal=0, text=text, values={})
            )
        source = SourceManifest(kind="knowledge", objects=tuple(objects))
        self.provider(
            "import-source", source=source.model_dump(mode="json"), files=files
        )
        self.operations = (
            BindingOperation(
                name="documents.ingest/v1",
                effect="write",
                parameters=(),
                result=(BindingField(name="result_json", kind="string"),),
                max_rows=20,
                max_bytes=65536,
                timeout_ms=30000,
            ),
            BindingOperation(
                name="documents.search/v1",
                effect="read",
                parameters=tuple(
                    BindingField(name=name, kind=kind)
                    for name, kind in (
                        ("ingestion_handle", "string"),
                        ("query", "string"),
                        ("offset", "integer"),
                        ("limit", "integer"),
                    )
                ),
                result=(BindingField(name="result_json", kind="string"),),
                max_rows=20,
                max_bytes=65536,
                timeout_ms=30000,
            ),
        )
        descriptor = ProviderDescriptor(
            workspace_id=ws,
            provider_profile_id=ProviderProfileId(uuid4()),
            source_revision=source.revision_id,
            kind="knowledge",
            operations=self.operations,
        )
        self.provider(
            "register-revision", descriptor=descriptor.model_dump(mode="json")
        )
        self.reference = descriptor.reference.model_dump(mode="json")
        self.provider(
            "grant-owner",
            provider=self.reference,
            permissions=[
                "provider.manage",
                "provider.inspect",
                "knowledge.read",
                "execute",
                "deploy",
            ],
        )
        collection = KnowledgeCollectionRef(workspace_id=ws, collection_id=str(uuid4()))
        self.provider(
            "grant-owner",
            knowledge_collection=collection.model_dump(mode="json"),
            permissions=["knowledge.read", "knowledge.manage"],
        )
        definition = KnowledgeRevisionSpec(
            workspace_id=ws,
            collection_id=collection.collection_id,
            source_revision=source.revision_id,
        )
        self.provider(
            "register-knowledge-definition",
            provider=self.reference,
            knowledge_definition=definition.model_dump(mode="json"),
        )
        config = ProviderHostConfig(
            schema_version="actions.local-provider-config/v2",
            provider=descriptor.reference,
            source_revision=source.revision_id,
            host=KnowledgeDuckDBHost(revision=definition.reference),
        )
        self.provider("configure-host", config=config.model_dump(mode="json"))
        require(
            self.provider(
                "provision-knowledge-host", config=config.model_dump(mode="json")
            )["readiness"]
            == "provisioned-not-ingested"
        )

    async def create(self, session):
        reply = await self.call(
            session,
            "canvas_create",
            dict(title="Installed Knowledge lifecycle", idempotencyKey="lane-b-create"),
        )
        self.app = reply.structured_content["applicationId"]
        self.first = reply.structured_content["revisionId"]
        self.spec = reply.meta["actions.canvas"]["spec"]
        await self.call(
            session,
            "canvas_release",
            dict(
                appId=self.app,
                candidateRevision=self.first,
                expectedActive=None,
                idempotencyKey="lane-b-empty-release",
            ),
        )

    async def author(self, session):
        source = '''from actions import action, knowledge

@action
def ingest_documents(note: str = "owned fixture") -> dict:
    """Ingest the explicitly bound owned document collection."""
    return knowledge.ingest("ingestion_documents", "documents.ingest/v1")

@action
def search_documents(ingestion_handle: str, query: str, offset: int, limit: int) -> dict:
    """Search a canonically published ingestion with bounded explicit paging."""
    return knowledge.search("search_documents", "documents.search/v1", ingestion_handle=ingestion_handle, query=query, offset=offset, limit=limit)
'''
        test = """import unittest
from generated_actions import ingest_documents, search_documents
class TestEntrypoints(unittest.TestCase):
    def test_entrypoints(self):
        self.assertTrue(callable(ingest_documents))
        self.assertTrue(callable(search_documents))
"""
        self.spec["bindingIds"] = ["ingestion", "search"]
        children = []
        for binding in self.spec["bindingIds"]:
            names = (
                [("note", "text", False)]
                if binding == "ingestion"
                else [
                    ("ingestion_handle", "text", True),
                    ("query", "text", True),
                    ("offset", "integer", True),
                    ("limit", "integer", True),
                ]
            )
            children.extend(
                [
                    dict(
                        type="form",
                        id=binding + "_form",
                        bindingId=binding,
                        submitLabel="Run " + binding,
                        fields=[
                            dict(name=n, label=n.replace("_", " "), type=t, required=r)
                            for n, t, r in names
                        ],
                    ),
                    dict(type="status", id=binding + "_status", bindingId=binding),
                    dict(
                        type="artifact",
                        id=binding + "_artifact",
                        bindingId=binding,
                        label="Inspect " + binding,
                    ),
                ]
            )
        self.spec["root"] = dict(type="stack", id="main", children=children)
        actions = []
        for name, requirement_id, operation in zip(
            ("ingest_documents", "search_documents"),
            ("ingestion_documents", "search_documents"),
            self.operations,
        ):
            actions.append(
                dict(
                    actionName=name,
                    logicalRequirements=[
                        dict(
                            id=requirement_id,
                            kind="knowledge",
                            operations=[operation.model_dump(mode="json")],
                            invocations=[
                                dict(
                                    operation=operation.name,
                                    inputs=[
                                        dict(parameter=p.name, input=p.name)
                                        for p in operation.parameters
                                    ],
                                )
                            ],
                        )
                    ],
                )
            )
        result = await self.call(
            session,
            "canvas_apply",
            dict(
                appId=self.app,
                expectedBase=self.first,
                spec=self.spec,
                bindings=[
                    dict(bindingId=b, capabilityId="action." + a)
                    for b, a in (
                        ("ingestion", "ingest_documents"),
                        ("search", "search_documents"),
                    )
                ],
                backend=dict(
                    logicalName="Installed Knowledge actions",
                    actions=actions,
                    files=[
                        dict(
                            path="package.yaml", content=self.args.package.read_text()
                        ),
                        dict(path="generated_actions.py", content=source),
                        dict(path="tests/test_actions.py", content=test),
                    ],
                ),
                dataBindings=[
                    dict(
                        bindingId=b,
                        requirementId=b + "_documents",
                        provider=self.reference,
                    )
                    for b in ("ingestion", "search")
                ],
                idempotencyKey="lane-b-knowledge-apply",
            ),
        )
        require(
            all(
                result.structured_content[key] == "passed"
                for key in ("buildStatus", "importStatus", "testStatus")
            )
        )
        self.revision = result.structured_content["revisionId"]
        await self.call(
            session,
            "canvas_release",
            dict(
                appId=self.app,
                candidateRevision=self.revision,
                expectedActive=self.first,
                idempotencyKey="lane-b-knowledge-release",
            ),
        )

    def run(self):
        try:
            import actions
            import actions.server

            require(
                sys.flags.isolated == 1
                and Path(sys.prefix).resolve() == self.args.expected_prefix.resolve()
            )
            require(
                all(
                    Path(p)
                    .resolve()
                    .is_relative_to(self.args.expected_prefix.resolve())
                    for p in (actions.__file__, actions.server.__file__)
                )
            )
            versions = {
                name: importlib.metadata.version(name)
                for name in ("actions-runtime", "actions-core")
            }
            require(
                versions == {"actions-runtime": "1.1.0a39", "actions-core": "1.1.0a4"}
            )
            require(shutil.disk_usage(self.root).free >= 5 * 1024**3)
            self.receipt.update(
                versions=versions,
                source_checkpoint=self.args.source_checkpoint,
                stage="bootstrap",
            )
            self.start()
            asyncio.run(self.connect(self.create))
            self.stop()
            self.receipt["stage"] = "operator"
            self.configure()
            self.receipt["stage"] = "authoring"
            self.start(profile=True)
            asyncio.run(self.connect(self.author))
            self.stop()
            self.receipt["stage"] = "authorization"
            self.authorize(
                "authorize-exact-deployment",
                "deployment",
                deployment=dict(
                    workspace_id=self.workspace,
                    deployment_id=self.app,
                    revision_id=self.revision,
                ),
                run_permissions=["execute", "read", "cancel"],
                queue_permissions=[
                    "work_items.read",
                    "work_items.enqueue",
                    "work_items.claim",
                    "work_items.complete",
                    "work_items.cancel",
                    "work_items.artifact.read",
                ],
            )
            manifest = dict(
                installed_python=sys.executable,
                installed_prefix=str(self.args.expected_prefix.resolve()),
                expected_versions=versions,
                source_checkpoint=self.args.source_checkpoint,
                datadir=str(self.data),
                runtime_profile=str(self.profile),
                task_policy=str(self.policy),
                workspace_id=self.workspace,
                ingestion=dict(app_id=self.app, binding_id="ingestion"),
                search=dict(app_id=self.app, binding_id="search"),
                query="owned",
                page_limit=2,
                expected_hits=self.expected,
                max_bytes=1048576,
                output_root=str(self.root / "lifecycle"),
            )
            (self.root / "lifecycle-manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n"
            )
            self.receipt.update(
                status="PASS",
                stage="prepared",
                application_id=self.app,
                revision_id=self.revision,
            )
        except BaseException as error:
            self.receipt.update(status="FAIL", error_type=type(error).__name__)
        finally:
            try:
                self.stop()
            except BaseException as error:
                self.receipt.update(
                    status="FAIL", cleanup_error_type=type(error).__name__
                )
            self.save()
        return 0 if self.receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-prefix", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--source-checkpoint", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    sys.exit(Fixture(args).run())
