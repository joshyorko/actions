"""Read-only Canvas library and stale Runtime-instance reconciliation."""

from __future__ import annotations

import asyncio
import json
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from actions.server.foundry.discovery import (
    CanvasLibraryApp,
    CanvasLibraryDiscovery,
    CanvasLibrarySnapshot,
    DiscoveryError,
    InstanceState,
    ServerInfo,
    read_server_info,
    register_or_attach_server_info,
    reconcile_server_info,
    remove_server_info,
    write_server_info,
)

if TYPE_CHECKING:
    from actions.server.foundry.mcp import CanvasCaller


def _caller(
    workspace_id: str | None = None,
    principal_id: str | None = None,
    audience: str = "model",
):
    mcp = pytest.importorskip(
        "actions.server.foundry.mcp",
        reason="Runtime MCP dependencies are unavailable in this checkout",
    )
    from actions.server.run_outputs.types import Actor

    return mcp.CanvasCaller(
        actor=Actor(principal_id=principal_id or str(uuid4())),
        workspace_id=workspace_id or str(uuid4()),
        audience=audience,
    )


def _app(
    app_id: str = "catalog", visibility: tuple[str, ...] = ("model", "app")
) -> CanvasLibraryApp:
    pytest.importorskip(
        "actions.canvas_contract",
        reason="the public CanvasSpec contract is staged separately in #100",
    )
    return CanvasLibraryApp(
        app_id=app_id,
        title="Local catalog",
        revision_id="revision-1",
        summary="Search local records.",
        spec={
            "schemaVersion": "actions.canvas-spec/v1",
            "title": "Local catalog",
            "visibility": list(visibility),
            "bindingIds": ["search"],
            "root": {
                "type": "stack",
                "id": "main",
                "children": [
                    {
                        "type": "form",
                        "id": "search-form",
                        "bindingId": "search",
                        "submitLabel": "Search",
                        "fields": [
                            {
                                "name": "query",
                                "label": "Search",
                                "type": "text",
                                "required": True,
                            }
                        ],
                    }
                ],
            },
        },
    )


def _snapshot(caller, apps=(), current_app_id=None):
    return CanvasLibrarySnapshot(
        workspace_id=caller.workspace_id,
        principal_id=caller.actor.principal_id,
        apps=tuple(apps),
        current_app_id=current_app_id,
    )


class _Reader:
    def __init__(self, snapshot: CanvasLibrarySnapshot):
        self.snapshot = snapshot
        self.calls: list[CanvasCaller] = []

    async def read_library(self, caller: CanvasCaller) -> CanvasLibrarySnapshot:
        self.calls.append(caller)
        return self.snapshot


def test_canvas_open_empty_library_is_read_only_and_has_text_fallback():
    caller = _caller()
    reader = _Reader(_snapshot(caller))
    launcher = CanvasLibraryDiscovery(reader)

    reply = asyncio.run(launcher.open(caller, {}))

    assert reader.calls == [caller]
    assert reply.model_result == {
        "status": "empty",
        "appCount": 0,
        "currentAppId": None,
    }
    assert reply.view_state == {
        "apps": [],
        "currentApp": None,
        "empty": True,
        "emptyMessage": (
            "No apps are available to you yet. Create one with canvas_create."
        ),
    }
    assert "available to you" in reply.summary
    assert "canvas_create" in reply.summary
    assert "query" not in reply.summary.casefold()


def test_canvas_open_projects_only_the_callers_current_library():
    caller = _caller()
    selected = _app("workspace-app")
    reader = _Reader(_snapshot(caller, (selected,), current_app_id="workspace-app"))

    reply = asyncio.run(CanvasLibraryDiscovery(reader).open(caller, {}))

    assert reader.calls == [caller]
    assert caller.workspace_id not in reply.summary
    assert reply.model_result == {
        "status": "ready",
        "appCount": 1,
        "currentAppId": "workspace-app",
    }
    assert reply.view_state is not None
    assert reply.view_state["currentApp"]["appId"] == "workspace-app"
    assert reply.view_state["apps"][0]["spec"]["schemaVersion"] == (
        "actions.canvas-spec/v1"
    )


def test_canvas_open_filters_apps_and_selection_by_authenticated_audience():
    model_caller = _caller()
    app_only = _app("app-only", ("app",))
    model_only = _app("model-only", ("model",))
    shared = _app("shared", ("model", "app"))
    snapshot = _snapshot(
        model_caller,
        (app_only, model_only, shared),
        current_app_id="app-only",
    )
    model_reply = asyncio.run(
        CanvasLibraryDiscovery(_Reader(snapshot)).open(model_caller, {})
    )
    app_caller = _caller(
        workspace_id=model_caller.workspace_id,
        principal_id=model_caller.actor.principal_id,
        audience="app",
    )
    app_reply = asyncio.run(
        CanvasLibraryDiscovery(_Reader(snapshot)).open(app_caller, {})
    )

    assert model_reply.model_result == {
        "status": "ready",
        "appCount": 2,
        "currentAppId": None,
    }
    assert [app["appId"] for app in model_reply.view_state["apps"]] == [
        "model-only",
        "shared",
    ]
    assert "app-only" not in str(model_reply.view_state)
    assert app_reply.model_result == {
        "status": "ready",
        "appCount": 2,
        "currentAppId": "app-only",
    }
    assert [app["appId"] for app in app_reply.view_state["apps"]] == [
        "app-only",
        "shared",
    ]


def test_canvas_open_empty_visible_library_does_not_claim_no_apps_exist():
    caller = _caller()
    reader = _Reader(_snapshot(caller, (_app("app-only", ("app",)),)))

    reply = asyncio.run(CanvasLibraryDiscovery(reader).open(caller, {}))

    assert reply.model_result == {
        "status": "empty",
        "appCount": 0,
        "currentAppId": None,
    }
    assert "available to you" in reply.summary


@pytest.mark.parametrize("arguments", [{"query": "records"}, {"create": True}, []])
def test_canvas_open_rejects_any_input_before_reading_state(arguments):
    caller = _caller()
    reader = _Reader(_snapshot(caller))
    with pytest.raises(DiscoveryError, match="empty input"):
        asyncio.run(CanvasLibraryDiscovery(reader).open(caller, arguments))
    assert reader.calls == []


def test_canvas_library_current_app_must_be_in_visible_workspace_snapshot():
    with pytest.raises(DiscoveryError, match="visible library"):
        CanvasLibrarySnapshot(
            workspace_id=str(uuid4()),
            principal_id=str(uuid4()),
            apps=(_app(),),
            current_app_id="other-workspace-app",
        )


def test_canvas_open_rejects_a_reader_response_for_another_actor_or_workspace():
    caller = _caller()
    wrong_scope = CanvasLibrarySnapshot(
        workspace_id=str(uuid4()),
        principal_id=caller.actor.principal_id,
    )
    reader = _Reader(wrong_scope)

    with pytest.raises(DiscoveryError, match="caller scope"):
        asyncio.run(CanvasLibraryDiscovery(reader).open(caller, {}))
    assert reader.calls == [caller]


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://user:password@localhost:8080/mcp",
        "https://example.invalid:8080/mcp",
        "https://127.0.0.1:8080/mcp?token=secret",
        "http://localhost:8080/secret-token",
    ],
)
def test_server_discovery_never_records_credentials_or_remote_endpoints(endpoint):
    with pytest.raises(DiscoveryError, match="loopback endpoint"):
        ServerInfo(
            instance_id=str(uuid4()),
            process_id=123,
            process_start_time=100.0,
            started_at=101.0,
            transports=("http",),
            endpoints=(endpoint,),
            capabilities=("canvas",),
        )


def _server_info(process_id: int = 123) -> ServerInfo:
    return ServerInfo(
        instance_id=str(uuid4()),
        process_id=process_id,
        process_start_time=100.0,
        started_at=101.0,
        transports=("stdio",),
        endpoints=(),
        capabilities=("canvas", "mcp-apps"),
    )


class _ProcessProbe:
    def __init__(self, result: bool | None):
        self.result = result

    def matches(self, process_id: int, process_start_time: float) -> bool | None:
        assert process_id == 123
        assert process_start_time == 100.0
        return self.result


def test_server_info_roundtrips_atomically_with_private_file_mode(tmp_path: Path):
    info = _server_info()
    write_server_info(tmp_path, info)

    loaded = read_server_info(tmp_path)

    assert loaded == info
    document = json.loads((tmp_path / "server-info.json").read_text())
    assert document["schemaVersion"] == 1
    assert document["instanceId"] == info.instance_id
    assert document["transports"] == ["stdio"]
    assert document["endpoints"] == []
    assert "secret" not in json.dumps(document).casefold()
    if os.name != "nt":
        assert stat.S_IMODE((tmp_path / "server-info.json").stat().st_mode) == 0o600


def test_reconciliation_detects_live_unhealthy_and_inaccessible_processes(tmp_path):
    info = _server_info()
    write_server_info(tmp_path, info)

    live = reconcile_server_info(
        tmp_path,
        process_probe=_ProcessProbe(True),
        health_probe=lambda _: True,
    )
    no_health_probe = reconcile_server_info(tmp_path, process_probe=_ProcessProbe(True))
    unhealthy = reconcile_server_info(
        tmp_path,
        process_probe=_ProcessProbe(True),
        health_probe=lambda _: False,
    )
    unknown = reconcile_server_info(tmp_path, process_probe=_ProcessProbe(None))

    assert live.state is InstanceState.HEALTHY
    assert no_health_probe.state is InstanceState.UNKNOWN
    assert unhealthy.state is InstanceState.UNHEALTHY
    assert unknown.state is InstanceState.UNKNOWN
    assert read_server_info(tmp_path) == info


@pytest.mark.parametrize("probe", [_ProcessProbe(False), _ProcessProbe(None)])
def test_stale_process_record_is_removed_only_when_identity_is_known_dead(
    tmp_path: Path, probe
):
    info = _server_info()
    write_server_info(tmp_path, info)

    result = reconcile_server_info(tmp_path, process_probe=probe)

    if isinstance(probe.result, bool) and not probe.result:
        assert result.state is InstanceState.STALE
        assert not (tmp_path / "server-info.json").exists()
    else:
        assert result.state is InstanceState.UNKNOWN
        assert read_server_info(tmp_path) == info


def test_restart_can_replace_a_crashed_instance_without_touching_other_data(
    tmp_path: Path,
):
    old = _server_info()
    write_server_info(tmp_path, old)
    (tmp_path / "apps").mkdir()
    (tmp_path / "apps" / "retained.txt").write_text("keep", encoding="utf-8")

    stale = reconcile_server_info(tmp_path, process_probe=_ProcessProbe(False))
    replacement = _server_info(process_id=124)
    write_server_info(tmp_path, replacement)

    assert stale.state is InstanceState.STALE
    assert read_server_info(tmp_path) == replacement
    assert (tmp_path / "apps" / "retained.txt").read_text(encoding="utf-8") == "keep"


def test_registration_attaches_idempotently_to_a_healthy_instance(tmp_path: Path):
    existing = _server_info()
    replacement = _server_info(process_id=124)
    write_server_info(tmp_path, existing)

    result = register_or_attach_server_info(
        tmp_path,
        replacement,
        process_probe=_ProcessProbe(True),
        health_probe=lambda _: True,
    )

    assert result.state is InstanceState.HEALTHY
    assert result.info == existing
    assert read_server_info(tmp_path) == existing


def test_registration_replaces_only_a_confirmed_dead_instance(tmp_path: Path):
    crashed = _server_info()
    replacement = _server_info(process_id=124)
    write_server_info(tmp_path, crashed)

    result = register_or_attach_server_info(
        tmp_path,
        replacement,
        process_probe=_ProcessProbe(False),
    )

    assert result.state is InstanceState.HEALTHY
    assert result.info == replacement
    assert read_server_info(tmp_path) == replacement


@pytest.mark.parametrize(
    ("process_probe", "health_probe", "state"),
    [
        (_ProcessProbe(None), None, InstanceState.UNKNOWN),
        (_ProcessProbe(True), None, InstanceState.UNKNOWN),
        (_ProcessProbe(True), lambda _: False, InstanceState.UNHEALTHY),
    ],
)
def test_registration_refuses_ambiguous_or_unhealthy_instances(
    tmp_path: Path, process_probe, health_probe, state
):
    existing = _server_info()
    replacement = _server_info(process_id=124)
    write_server_info(tmp_path, existing)

    with pytest.raises(DiscoveryError, match=state.value):
        register_or_attach_server_info(
            tmp_path,
            replacement,
            process_probe=process_probe,
            health_probe=health_probe,
        )

    assert read_server_info(tmp_path) == existing


def test_shutdown_removes_only_the_matching_instance_record(tmp_path: Path):
    first = _server_info()
    replacement = _server_info(process_id=124)
    write_server_info(tmp_path, first)
    write_server_info(tmp_path, replacement)

    assert not remove_server_info(tmp_path, first.instance_id)
    assert read_server_info(tmp_path) == replacement
    assert remove_server_info(tmp_path, replacement.instance_id)
    assert read_server_info(tmp_path) is None


def test_malformed_server_info_is_retained_and_fails_closed(tmp_path: Path):
    path = tmp_path / "server-info.json"
    path.write_text('{"schemaVersion": 99}', encoding="utf-8")

    result = reconcile_server_info(tmp_path, process_probe=_ProcessProbe(False))

    assert result.state is InstanceState.INVALID
    assert path.exists()
