"""The retained source build wrapper must emit a valid pinned RCC task boundary."""
import importlib.util
import json
import shlex
import sys
from pathlib import Path


def test_handoff_build_has_required_tasks_and_preserves_source_boundary(
    tmp_path, monkeypatch
):
    root = Path(__file__).resolve().parents[2]
    path = root / "docs/program/evidence/actions-next-327/recovery-handoff-20261025/extension-handoff/build_candidate.py"
    spec = importlib.util.spec_from_file_location("handoff_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "wheels"
    monkeypatch.setattr(
        sys, "argv", [str(path), "--source", str(source), "--output", str(output)]
    )
    monkeypatch.setattr(
        module.subprocess,
        "check_output",
        lambda *args, **kwargs: "f094faf5d2eabbef0a159a7fabb4983a59a8e56c\n",
    )
    descriptors = []

    def run(command, **kwargs):
        assert command[:2] == ["rcc", "run"]
        assert command[-3:] == ["--dev", "-t", "Build"]
        descriptor = json.loads(Path(command[command.index("-r") + 1]).read_text())
        descriptors.append(descriptor)
        assert descriptor["tasks"]["Build"] == descriptor["devTasks"]["Build"]
        assert descriptor["artifactsDir"]
        assert descriptor["environmentConfigs"] == [str(source / "developer/setup.yaml")]
        inner = shlex.split(descriptor["tasks"]["Build"]["shell"])
        assert inner[-1] == "--inside-rcc"
        assert inner[inner.index("--source") + 1] == str(source)
        assert inner[inner.index("--output") + 1] == str(output)
        assert kwargs == {"cwd": source, "check": True}

    monkeypatch.setattr(module.subprocess, "run", run)
    module.main()
    assert len(descriptors) == 1
