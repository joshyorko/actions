"""Drive the ordinary Robot task across persistent SDK storage and process restart."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "examples" / "decisions_robot"


def run_robot(state, output):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robot",
            "--outputdir",
            str(output),
            "--variable",
            "STATE_DIR:" + str(state),
            str(EXAMPLE / "tasks.robot"),
        ],
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((state / "summary.json").read_text())


def test_robot_persists_three_typed_decisions_and_replays_in_fresh_process(tmp_path):
    state = tmp_path / "state"
    first = run_robot(state, tmp_path / "first")
    assert first["provider_calls_this_process"] == 3
    assert first["persisted_decisions"] == first["inputs"] == 3
    assert first["source_state"] == "PENDING"
    assert first["provider"] == "synthetic-document/v1"
    second = run_robot(state, tmp_path / "second")
    assert second["provider_calls_this_process"] == 0
    assert second["persisted_decisions"] == 3


def demo_class():
    spec = importlib.util.spec_from_file_location(
        "decision_robot_demo", EXAMPLE / "DecisionsDemo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DecisionsDemo


def test_robot_refuses_changed_protected_input(tmp_path):
    demo = demo_class()()
    demo.open_demo(str(tmp_path))
    item = demo.get_synthetic_work_item("invoice")
    demo.decide_work_item(item)
    demo.adapter.save_payload(item, {"document_type": "credit_note"})
    with pytest.raises(ValueError, match="protected input changed"):
        demo.decide_work_item(item)
    assert demo.calls == 1


def test_robot_does_not_retry_interrupted_inference(tmp_path):
    demo = demo_class()()
    demo.open_demo(str(tmp_path))
    item = demo.get_synthetic_work_item("invoice")

    class FailingProvider:
        def evaluate(self, request):
            raise RuntimeError("synthetic interruption")

    demo.provider = FailingProvider()
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        demo.decide_work_item(item)
    reopened = demo_class()()
    reopened.open_demo(str(tmp_path))
    with pytest.raises(ValueError, match="evaluation uncertain"):
        reopened.decide_work_item(item)
    assert reopened.calls == 0
    reopened.source_should_remain_pending(item)


def test_robot_rejects_changed_provider_scope(tmp_path):
    demo = demo_class()()
    demo.open_demo(str(tmp_path))
    item = demo.get_synthetic_work_item("invoice")
    demo.decide_work_item(item)
    demo.provider_id = "same-model/different-project"
    with pytest.raises(ValueError, match="protected input changed"):
        demo.decide_work_item(item)
    assert demo.calls == 1
