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
