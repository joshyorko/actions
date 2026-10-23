"""Real common SQL authoring: edits are durable but activation stays explicit."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import (
    _ExecutionPort,
    _PackagePort,
    _refs,
    _runtime_database,
)

from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.foundry.authoring_values import (
    AuthoringAccessDenied,
    AuthoringConflict,
)
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryDeploymentHead,
    FoundryDeploymentRevision,
    FoundryPackageRevision,
    FoundryRequest,
)
from actions.server.foundry.sql_authoring import SqlAuthoringAuthority
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def _fingerprint(value):
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def _spec(title):
    return json.dumps(
        {
            "schemaVersion": "actions.canvas-spec/v1",
            "title": title,
            "visibility": ["model", "app"],
            "bindingIds": [],
            "root": {"type": "stack", "id": "main", "children": []},
        }
    ).encode()


def _authority(db, refs):
    repository = FoundryRepository(db)
    auth = SqlFoundryAuthorization(db)
    deployment = FoundryDeploymentService(
        repository, _PackagePort(refs), auth, _ExecutionPort()
    )
    return SqlAuthoringAuthority(repository, deployment, auth)


def _grant(db, refs, actor):
    grant = FoundryAccessGrant(
        str(uuid4()),
        str(refs.workspace.root),
        actor.principal_id,
        "workspace",
        str(refs.workspace.root),
        json.dumps(
            [
                "inspect_library",
                "create_application",
                "read_application",
                "apply_revision",
                "inspect_application",
                "release_application",
                "deploy",
            ]
        ),
    )
    with db.transaction():
        db.insert(grant)
    return grant


def _create(authority, refs, actor, key="create"):
    return authority.create(
        actor,
        refs.workspace,
        _spec("Blank app"),
        request_fingerprint=_fingerprint("create"),
        idempotency_key=key,
    )


def test_durable_draft_release_revise_rollback_and_restart(database_location):
    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        authority = _authority(db, refs)
        assert authority.open(actor, refs.workspace) == ()
        first = _create(authority, refs, actor)
        assert not first.active
        assert db.all(FoundryDeploymentHead) == []
        second = authority.apply(
            actor,
            refs.workspace,
            first.application_id,
            first.ref,
            _spec("Edited app"),
            (),
            (),
            None,
            None,
            _fingerprint("apply"),
            idempotency_key="apply",
        )
        assert authority.current(actor, refs.workspace, first.application_id) is None
        assert (
            authority.latest(actor, refs.workspace, first.application_id).ref
            == second.ref
        )
        with pytest.raises(AuthoringConflict):
            authority.release(
                actor,
                refs.workspace,
                first.application_id,
                first.ref,
                None,
                _fingerprint("stale-release"),
                idempotency_key="stale",
            )
        released = authority.release(
            actor,
            refs.workspace,
            first.application_id,
            second.ref,
            None,
            _fingerprint("release"),
            idempotency_key="release",
        )
        assert released.ref == second.ref and released.active
        assert (
            authority.release(
                actor,
                refs.workspace,
                first.application_id,
                second.ref,
                None,
                _fingerprint("release"),
                idempotency_key="release",
            ).ref
            == second.ref
        )
        authority.rollback(
            actor,
            refs.workspace,
            first.application_id,
            first.ref,
            second.ref,
            _fingerprint("rollback"),
            idempotency_key="rollback",
        )
        assert (
            authority.current(actor, refs.workspace, first.application_id).ref
            == first.ref
        )
        assert (
            authority.latest(actor, refs.workspace, first.application_id).ref
            == second.ref
        )
        assert len(db.all(FoundryDeploymentRevision)) == 2
        assert len(db.all(FoundryRequest)) == len(db.all(FoundryAudit)) == 4
        assert db.all(FoundryPackageRevision) == []
    restarted = Database(database_location)
    with restarted.connect():
        restarted.initialize(get_all_model_classes())
        authority = _authority(restarted, refs)
        assert (
            authority.current(actor, refs.workspace, first.application_id).ref
            == first.ref
        )
        assert (
            authority.latest(actor, refs.workspace, first.application_id).ref
            == second.ref
        )
        assert (
            len(
                authority.inspect(actor, refs.workspace, first.application_id).revisions
            )
            == 2
        )


def test_authorization_and_revocation_apply_to_receipt_replay(database_location):
    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    denied = Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        grant = _grant(db, refs, actor)
        authority = _authority(db, refs)
        first = _create(authority, refs, actor)
        with pytest.raises(AuthoringAccessDenied):
            authority.get(denied, refs.workspace, first.application_id, first.ref)
        with db.transaction():
            db.execute("DELETE FROM foundry_access_grant WHERE id=?", [grant.id])
        with pytest.raises(AuthoringAccessDenied):
            authority.lookup_request(
                actor, refs.workspace, "create", "create", _fingerprint("create")
            )
        with pytest.raises(AuthoringAccessDenied):
            authority.release(
                actor,
                refs.workspace,
                first.application_id,
                first.ref,
                None,
                _fingerprint("release"),
                idempotency_key="release",
            )
        assert db.all(FoundryDeploymentHead) == []
        assert len(db.all(FoundryRequest)) == len(db.all(FoundryAudit)) == 1


def test_concurrent_create_delivery_returns_one_durable_app(database_location):
    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        barrier = Barrier(2)

        def deliver(_):
            connection = Database(database_location)
            with connection.connect():
                connection.initialize(get_all_model_classes())
                barrier.wait(timeout=20)
                return _create(_authority(connection, refs), refs, actor)

        with ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(deliver, range(2)))
        assert values[0].ref == values[1].ref
        assert values[0].application_id == values[1].application_id
        assert len(db.all(FoundryDeploymentRevision)) == 1
        assert len(db.all(FoundryRequest)) == len(db.all(FoundryAudit)) == 1
        assert db.all(FoundryDeploymentHead) == []


def test_stage_audit_failure_rolls_back_and_same_delivery_recovers(
    database_location, monkeypatch
):
    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        authority = _authority(db, refs)
        append = authority.repository._append_audit

        def interrupt(*args, **kwargs):
            raise RuntimeError("owned failure before audit")

        monkeypatch.setattr(authority.repository, "_append_audit", interrupt)
        with pytest.raises(RuntimeError, match="owned failure"):
            _create(authority, refs, actor)
        assert (
            db.all(FoundryDeploymentRevision)
            == db.all(FoundryRequest)
            == db.all(FoundryAudit)
            == []
        )
        monkeypatch.setattr(authority.repository, "_append_audit", append)
        first = _create(authority, refs, actor)
        assert (
            authority.get(actor, refs.workspace, first.application_id).ref == first.ref
        )


def test_genuine_mcp_sdk_authors_and_reconnects_to_common_sql(database_location):
    """Protocol + real SQL proof; static sentinel is not a rendered View/E1."""
    import asyncio

    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    from actions.server.foundry.authoring import FoundryAuthoring
    from actions.server.foundry.mcp import MODEL_TOOLS, URI, CanvasCaller, CanvasMcp
    from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))

    class BackendUnavailable:
        def __getattr__(self, name):
            raise AssertionError("UI-only authoring must not use backend ports")

    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        authority = _authority(db, refs)
        auth = SqlFoundryAuthorization(db)
        unavailable = BackendUnavailable()
        port = FoundryAuthoring(authority, auth, unavailable, unavailable, unavailable)

        async def authenticate(context):
            request = context.request
            audience = request.headers.get("x-owned-audience") if request else None
            if audience not in {"model", "app"}:
                return None
            return CanvasCaller(actor, str(refs.workspace.root), audience)

        async def connect(check, audience="model"):
            canvas = CanvasMcp(
                port, authenticate, "<html>protocol-only owned sentinel</html>"
            )
            helper = McpServerSetupHelper(canvas_foundry=canvas)
            application = helper.server.streamable_http_app(
                streamable_http_path="/mcp",
                json_response=True,
                stateless_http=True,
                transport_security=helper.transport_security,
            )
            async with application.router.lifespan_context(application):
                async with httpx2.AsyncClient(
                    transport=httpx2.ASGITransport(app=application),
                    base_url="http://127.0.0.1:8000",
                    headers={"x-owned-audience": audience},
                ) as http:
                    async with streamable_http_client(
                        "http://127.0.0.1:8000/mcp", http_client=http
                    ) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
                            await session.discover()
                            return await check(session)

        async def first_session(session):
            tools = (await session.list_tools()).tools
            assert {tool.name for tool in tools} == MODEL_TOOLS
            assert all(tool.meta["ui"]["resourceUri"] == URI for tool in tools)
            resource = await session.read_resource(URI)
            assert resource.contents[0].mime_type == "text/html;profile=mcp-app"
            empty = await session.call_tool("canvas_open", {})
            assert not empty.is_error and empty.structured_content["applications"] == []
            created = await session.call_tool(
                "canvas_create", {"idempotencyKey": "sdk-create"}
            )
            assert not created.is_error
            app_id = created.structured_content["applicationId"]
            first_id = created.structured_content["revisionId"]
            spec = created.meta["actions.canvas"]["spec"]
            spec["title"] = "SDK-authored useful app"
            applied = await session.call_tool(
                "canvas_apply",
                {
                    "appId": app_id,
                    "expectedBase": first_id,
                    "spec": spec,
                    "bindings": [],
                    "idempotencyKey": "sdk-apply",
                },
            )
            assert not applied.is_error
            second_id = applied.structured_content["revisionId"]
            released = await session.call_tool(
                "canvas_release",
                {
                    "appId": app_id,
                    "candidateRevision": second_id,
                    "expectedActive": None,
                    "idempotencyKey": "sdk-release",
                },
            )
            assert not released.is_error and released.structured_content["active"]
            return app_id, first_id, second_id, spec

        app_id, first_id, second_id, spec = asyncio.run(connect(first_session))

        async def second_session(session):
            reopened = await session.call_tool("canvas_get", {"appId": app_id})
            assert reopened.structured_content["revisionId"] == second_id
            replay = await session.call_tool(
                "canvas_apply",
                {
                    "appId": app_id,
                    "expectedBase": first_id,
                    "spec": spec,
                    "bindings": [],
                    "idempotencyKey": "sdk-apply",
                },
            )
            assert (
                not replay.is_error
                and replay.structured_content["revisionId"] == second_id
            )
            stale = await session.call_tool(
                "canvas_apply",
                {
                    "appId": app_id,
                    "expectedBase": first_id,
                    "spec": spec,
                    "bindings": [],
                    "idempotencyKey": "sdk-stale",
                },
            )
            assert stale.is_error
            changed = dict(spec, title="Changed duplicate")
            conflict = await session.call_tool(
                "canvas_apply",
                {
                    "appId": app_id,
                    "expectedBase": first_id,
                    "spec": changed,
                    "bindings": [],
                    "idempotencyKey": "sdk-apply",
                },
            )
            assert conflict.is_error
            rollback = await session.call_tool(
                "canvas_release",
                {
                    "appId": app_id,
                    "rollbackTo": first_id,
                    "expectedActive": second_id,
                    "idempotencyKey": "sdk-rollback",
                },
            )
            assert (
                not rollback.is_error
                and rollback.structured_content["revisionId"] == first_id
            )

        asyncio.run(connect(second_session))

        async def wrong_audience(session):
            denied = await session.call_tool(
                "canvas_create", {"idempotencyKey": "app-must-not-create"}
            )
            assert denied.is_error

        asyncio.run(connect(wrong_audience, "app"))
        assert len(db.all(FoundryDeploymentRevision)) == 2
        assert len(db.all(FoundryAudit)) == len(db.all(FoundryRequest)) == 4
        assert db.all(FoundryPackageRevision) == []


def test_same_supplied_fingerprint_cannot_hide_changed_stage_input(database_location):
    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        authority = _authority(db, refs)
        first = _create(authority, refs, actor)
        with pytest.raises(AuthoringConflict):
            authority.create(
                actor,
                refs.workspace,
                _spec("Changed internal input"),
                request_fingerprint=_fingerprint("create"),
                idempotency_key="create",
            )
        assert len(db.all(FoundryDeploymentRevision)) == 1
        assert (
            authority.get(actor, refs.workspace, first.application_id).ref == first.ref
        )


def test_fresh_interpreter_reauthorizes_and_reopens_exact_active_revision(
    database_location,
):
    import os
    import subprocess
    import sys

    refs = _refs()
    actor = Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        authority = _authority(db, refs)
        first = _create(authority, refs, actor)
        authority.release(
            actor,
            refs.workspace,
            first.application_id,
            first.ref,
            None,
            _fingerprint("release"),
            idempotency_key="release",
        )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.update(
        ACTIONS_OWNED_FOUNDRY_DB=str(database_location),
        ACTIONS_OWNED_FOUNDRY_ACTOR=actor.model_dump_json(),
        ACTIONS_OWNED_FOUNDRY_REF=first.ref.model_dump_json(),
    )
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import json, os
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.deployments.ids import DeploymentRevisionRef
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.foundry.sql_authoring import SqlAuthoringAuthority
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.types import Actor
ref=DeploymentRevisionRef.model_validate_json(os.environ['ACTIONS_OWNED_FOUNDRY_REF'])
actor=Actor.model_validate_json(os.environ['ACTIONS_OWNED_FOUNDRY_ACTOR'])
db=Database(os.environ['ACTIONS_OWNED_FOUNDRY_DB'])
with db.connect():
    db.initialize(get_all_model_classes())
    repository=FoundryRepository(db)
    auth=SqlFoundryAuthorization(db)
    # UI-only readback must never invoke backend interfaces.
    service=FoundryDeploymentService(repository, object(), auth, object())
    authority=SqlAuthoringAuthority(repository, service, auth)
    current=authority.current(actor, ref.workspace_id, ref.deployment_id)
    assert current.ref == ref and current.active
    print(json.dumps({'revision': current.ref.revision_id.root, 'history': len(authority.inspect(actor, ref.workspace_id, ref.deployment_id).revisions)}))
""",
        ],
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    assert json.loads(result.stdout) == {
        "revision": first.ref.revision_id.root,
        "history": 1,
    }
