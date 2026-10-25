"""Runner refusal evidence, separate from installed lifecycle acceptance."""
import asyncio
import importlib.metadata
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

import actions.server


def test_editable_source_origin_fails_before_any_server_or_task(tmp_path, monkeypatch):
    assert not Path(actions.server.__file__).resolve().is_relative_to(Path(sys.prefix))
    scripts = Path(__file__).parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "lane_b_lifecycle", scripts / "lane_b_installed_knowledge_lifecycle.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = dict(
        installed_python=sys.executable,
        installed_prefix=sys.prefix,
        expected_versions={
            name: importlib.metadata.version(name)
            for name in ("actions-runtime", "actions-core")
        },
        source_checkpoint="synthetic-refusal-test",
        output_root=str(tmp_path / "receipts"),
        datadir=str(tmp_path),
        runtime_profile=str(tmp_path),
        task_policy=str(tmp_path),
        workspace_id=str(uuid4()),
        page_limit=1,
        expected_hits=[],
    )
    runner = module.Lifecycle(manifest)
    assert asyncio.run(runner.run()) == 1
    receipt = json.loads((runner.root / "receipt.json").read_bytes())
    assert receipt["stages"]["installed_origin"] == "FAIL"
    assert receipt["error_type"] == "ValueError"
    assert receipt["tasks"] == []
    assert all(
        status == "NOT_RUN"
        for stage, status in receipt["stages"].items()
        if stage != "installed_origin"
    )
    assert runner.process is None
    assert not list(runner.root.glob("*.log"))
    assert runner.key not in (runner.root / "receipt.json").read_text()


def test_build_preflight_failure_retains_receipt_without_installing(tmp_path):
    script = Path(__file__).parents[2] / "scripts/lane_b_build_installed.py"
    spec = importlib.util.spec_from_file_location("lane_b_build", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", str(source)], check=True, capture_output=True)
    (source / "dirty.txt").write_text("owned untracked fixture")
    destination = tmp_path / "build"
    with pytest.raises(ValueError):
        module.build(
            SimpleNamespace(repo=source, destination=destination, source_sha="unused")
        )
    receipt = json.loads((destination / "receipt.json").read_bytes())
    assert receipt["status"] == "FAIL"
    assert receipt["commands"] == []
    assert not (destination / "consumer").exists()


@pytest.mark.parametrize(
    "mode", ["valid", "missing", "different_terminal", "different_snapshot"]
)
def test_retained_ingestion_never_replaces_missing_or_changed_task(
    tmp_path, monkeypatch, mode
):
    scripts = Path(__file__).parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "lane_b_resume", scripts / "lane_b_installed_knowledge_lifecycle.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    invocation = {
        "mode": "detached",
        "snapshot": {"deployment": "original"},
        "inputs": {},
        "idempotencyKey": "retained-key",
    }
    terminal = {"taskId": "retained-task", "status": "completed"}
    invocation_file, terminal_file = (
        tmp_path / "invocation.json",
        tmp_path / "terminal.json",
    )
    invocation_file.write_text(json.dumps(invocation))
    terminal_file.write_text(json.dumps(terminal))
    runner = object.__new__(module.Lifecycle)
    runner.m = {
        "retained_ingestion": {
            "invocation_file": str(invocation_file),
            "terminal_file": str(terminal_file),
        }
    }
    calls = []

    async def connect(callback):
        return await callback(None)

    async def request(session, *, task_id):
        calls.append(("read", task_id))
        if mode == "missing":
            raise ValueError("Task unavailable")
        return (
            terminal
            if mode != "different_terminal"
            else {**terminal, "taskId": "other"}
        )

    async def invoke(session, args):
        calls.append(("invoke", args))
        return terminal

    runner.connect, runner.request, runner.invoke = connect, request, invoke
    snapshot = (
        invocation["snapshot"]
        if mode != "different_snapshot"
        else {"deployment": "other"}
    )
    if mode == "valid":
        assert asyncio.run(runner.retained_ingestion(snapshot)) == (
            invocation,
            terminal,
        )
        assert calls == [("read", "retained-task"), ("invoke", invocation)]
    else:
        with pytest.raises(ValueError):
            asyncio.run(runner.retained_ingestion(snapshot))
        assert not any(call[0] == "invoke" for call in calls)


@pytest.mark.parametrize("with_app_session", [True, False])
def test_canvas_keeps_mcp_session_for_both_roles(
    tmp_path, monkeypatch, with_app_session
):
    scripts = Path(__file__).parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "lane_b_canvas", scripts / "lane_b_installed_knowledge_lifecycle.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runner = object.__new__(module.Lifecycle)
    runner.m = {
        role: {"app_id": role + "-app", "binding_id": role + "-binding"}
        for role in ("ingestion", "search")
    }
    runner.app_sessions = {}
    calls = []

    class Session:
        async def call_tool(self, name, arguments):
            calls.append((self, name, arguments))
            role = arguments["appId"].removesuffix("-app")
            if name == "canvas_inspect":
                return SimpleNamespace(
                    is_error=False,
                    structured_content={
                        "invocationDescriptors": [
                            {"bindingId": role + "-binding", "snapshot": {"role": role}}
                        ]
                    },
                )
            assert name == "canvas_get"
            meta = {
                "actions.canvas": {
                    "spec": {
                        "nodes": [{"type": "artifact", "bindingId": role + "-binding"}]
                    }
                }
            }
            if with_app_session:
                meta["actions.appSession"] = {"token": role + "-synthetic-token"}
            return SimpleNamespace(is_error=False, meta=meta)

    session = Session()
    assert asyncio.run(runner.canvas(session)) == {
        "ingestion": {"role": "ingestion"},
        "search": {"role": "search"},
    }
    assert calls == [
        (session, name, {"appId": role + "-app"})
        for role in ("ingestion", "search")
        for name in ("canvas_inspect", "canvas_get")
    ]
    assert runner.app_sessions == (
        {role: role + "-synthetic-token" for role in ("ingestion", "search")}
        if with_app_session
        else {}
    )
